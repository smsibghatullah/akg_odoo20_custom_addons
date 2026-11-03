from datetime import datetime, timedelta

import pytz

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.user_impersonation_audit.models.common import get_config, set_config
from odoo.addons.user_impersonation_audit.models.impersonation_session import safe_local_url

from .common import ImpersonationCase


@tagged('post_install', '-at_install')
class TestImpersonationRules(ImpersonationCase):

    def check(self, impersonator, target, **kw):
        return self.env['user.impersonation.session']._uia_check(impersonator, target, **kw)

    def test_member_can_start_and_log_is_complete(self):
        log = self._start(self.agent, self.employee, reference='TCK-1', reason_category='access_test')
        self.assertEqual(log.state, 'active')
        self.assertEqual(log.impersonator_id, self.agent)
        self.assertEqual(log.target_id, self.employee)
        self.assertEqual(log.reference, 'TCK-1')
        self.assertEqual(log.reason_category, 'access_test')
        self.assertEqual(log.company_id, self.company)
        self.assertAlmostEqual((log.planned_end_date - log.start_date).total_seconds(), 3600, delta=2)
        self.assertEqual(log.landing_url, '/odoo')

    def test_non_member_is_refused(self):
        with self.assertRaises(AccessError):
            self._start(self.employee, self.portal)
        with self.assertRaises(AccessError):
            self._start(self.manager, self.employee)  # auditing does not allow impersonating

    def test_hard_blocks(self):
        root = self.env.ref('base.user_root')
        public = self.env.ref('base.public_user')
        archived = self._user('Old Timer', 'uia_old', [self.g_employee])
        archived.active = False
        for target in (root, public, archived, self.agent):
            with self.assertRaises(UserError, msg=target.login):
                self.check(self.agent, target)

    def test_admin_targets(self):
        admin2 = self._user('Second Admin', 'uia_admin2', [self.env.ref('base.group_system')])
        system_agent = self._user('Root Agent', 'uia_root_agent', [self.env.ref('base.group_system'), self.g_user])
        with self.assertRaises(UserError):
            self.check(system_agent, admin2)
        set_config(self.env, {'allow_admin_targets': True})
        self.check(system_agent, admin2)
        with self.assertRaises(UserError):  # a non-system impersonator still cannot
            self.check(self.agent, admin2)

    def test_no_privilege_climbing(self):
        self.check(self.agent, self.employee)  # fewer rights: allowed
        richer = self._user('Rich Rights', 'uia_rich', [self.g_employee, self.env.ref('base.group_allow_export')])
        with self.assertRaisesRegex(UserError, 'rights you do not have'):
            self.check(self.agent, richer)
        # a custom group without privilege still counts when it grants access rights
        secret = self.env['res.groups'].create({'name': 'UIA Secret Ledger', 'access_ids': [Command.create({
            'name': 'secret', 'model_id': self.env['ir.model']._get_id('res.country'), 'operation': 'r'})]})
        insider = self._user('Insider', 'uia_insider', [self.g_employee, secret])
        with self.assertRaisesRegex(UserError, 'UIA Secret Ledger'):
            self.check(self.agent, insider)
        flag = self.env['res.groups'].create({'name': 'UIA Feature Flag'})  # no access rights: ignored
        self.check(self.agent, self._user('Flagged', 'uia_flagged', [self.g_employee, flag]))

    def test_groups_implied_by_portal_are_not_extra_rights(self):
        # what website does: portal implies a group with access rights that internal users lack
        exposed = self.env['res.groups'].create({'name': 'UIA Exposed Models', 'access_ids': [Command.create({
            'name': 'exposed', 'model_id': self.env['ir.model']._get_id('res.country'), 'operation': 'r'})]})
        self.g_portal.implied_ids = [Command.link(exposed.id)]
        self.assertIn(exposed, self.portal.all_group_ids)
        self.check(self.agent, self.portal)
        # every group portal users get, whatever is installed (e.g. website), stays allowed
        self.assertFalse(self.env['user.impersonation.session']._uia_rights(self.portal))
        # a portal user with a genuinely extra group is still refused
        secret = self.env['res.groups'].create({'name': 'UIA Portal Extra', 'access_ids': [Command.create({
            'name': 'extra', 'model_id': self.env['ir.model']._get_id('res.lang'), 'operation': 'r'})]})
        rich_portal = self._user('Rich Portal', 'uia_rich_portal', [self.g_portal, secret])
        with self.assertRaisesRegex(UserError, 'UIA Portal Extra'):
            self.check(self.agent, rich_portal)
        # and an internal user with the portal-implied group is no escalation: every portal user has it
        self.check(self.agent, self._user('Exposed Emp', 'uia_exposed', [self.g_employee, exposed]))

    def test_portal_target_allowed(self):
        info = self.check(self.agent, self.portal)
        self.assertEqual(info['time_limit'], 60)
        log = self._start(self.agent, self.portal, landing_url='/odoo/contacts')
        self.assertIn(log.landing_url, ('/my', '/web/login_successful'), 'portal users land on the portal')
        self.assertTrue(log.target_share)

    def test_protected_user_and_group(self):
        self.employee.impersonation_protected = True
        with self.assertRaisesRegex(UserError, 'protected'):
            self.check(self.agent, self.employee)
        self.employee.impersonation_protected = False
        self.g_portal.impersonation_protected = True
        with self.assertRaisesRegex(UserError, 'protected'):
            self.check(self.agent, self.portal)

    def test_company_scope(self):
        other = self._user('Far Away', 'uia_far', [self.g_employee], companies=self.company_2)
        with self.assertRaisesRegex(UserError, 'companies'):
            self.check(self.agent, other)
        both = self._user('Both Companies', 'uia_both', [self.g_employee], companies=self.company | self.company_2)
        with self.assertRaisesRegex(UserError, 'Second Co'):  # would open the other company's data
            self.check(self.agent, both)
        self.agent.company_ids = [Command.link(self.company_2.id)]
        self.check(self.agent, both)
        self.check(self.agent, self.employee)  # a target in fewer companies is fine

    def test_reason_minimum_length(self):
        with self.assertRaisesRegex(UserError, 'at least 10'):
            self._start(self.agent, self.employee, reason='too short')
        set_config(self.env, {'min_reason_length': 3})
        self._start(self.agent, self.employee, reason='abc')

    def test_ip_allowlist(self):
        set_config(self.env, {'ip_allowlist': '10.0.0.0/8, 192.168.1.7'})
        self.check(self.agent, self.employee, ip='10.20.30.40')
        self.check(self.agent, self.employee, ip='192.168.1.7')
        with self.assertRaisesRegex(AccessError, 'network'):
            self.check(self.agent, self.employee, ip='192.168.1.8')

    def test_allowed_hours(self):
        self.agent.tz = 'UTC'
        set_config(self.env, {'hours_from': 8.0, 'hours_to': 18.0})
        noon = pytz.utc.localize(datetime(2026, 5, 4, 12, 0))
        night = pytz.utc.localize(datetime(2026, 5, 4, 22, 0))
        self.check(self.agent, self.employee, now=noon)
        with self.assertRaisesRegex(AccessError, 'between 08:00 and 18:00'):
            self.check(self.agent, self.employee, now=night)
        set_config(self.env, {'hours_from': 20.0, 'hours_to': 6.0})  # overnight window
        self.check(self.agent, self.employee, now=night)
        with self.assertRaises(AccessError):
            self.check(self.agent, self.employee, now=noon)

    def test_policies(self):
        Policy = self.env['user.impersonation.policy']
        helpdesk = self.env['res.groups'].create({'name': 'UIA Helpdesk'})
        self.agent.group_ids = [Command.link(helpdesk.id)]
        Policy.create({'name': 'Helpdesk on portal', 'impersonator_group_ids': [Command.link(helpdesk.id)],
                       'target_type': 'portal', 'time_limit': 15, 'force_read_only': True})
        info = self.check(self.agent, self.portal)
        self.assertEqual(info['time_limit'], 15)
        self.assertTrue(info['read_only_forced'])
        with self.assertRaisesRegex(AccessError, 'No impersonation policy'):
            self.check(self.agent, self.employee)
        log = self._start(self.agent, self.portal, read_only=False)
        self.assertTrue(log.read_only, 'policy forces read-only')
        self.assertEqual(log.policy_id.name, 'Helpdesk on portal')

    def test_policy_target_groups_companies_and_cap(self):
        Policy = self.env['user.impersonation.policy']
        policy = Policy.create({'name': 'Employees, second company', 'impersonator_group_ids': [Command.link(self.g_user.id)],
                                'target_group_ids': [Command.link(self.g_employee.id)],
                                'company_ids': [Command.link(self.company_2.id)], 'time_limit': 500})
        with self.assertRaises(AccessError):
            self.check(self.agent, self.employee)  # wrong company
        policy.company_ids = [Command.link(self.company.id)]
        self.assertEqual(self.check(self.agent, self.employee)['time_limit'], 120, 'capped by the hard maximum')
        with self.assertRaises(AccessError):
            self.check(self.agent, self.portal)  # not in target groups

    def test_consent_required(self):
        Consent = self.env['user.impersonation.consent']
        self.employee.impersonation_consent = 'require'
        with self.assertRaisesRegex(UserError, 'must approve'):
            self._start(self.agent, self.employee)
        consent = Consent.with_user(self.agent)._uia_request(self.employee, 'Need to check the dashboard')
        self.assertEqual(consent.state, 'pending')
        self.assertIn(self.employee.partner_id, consent.message_ids.partner_ids, 'the user is notified')
        self.assertEqual(Consent.with_user(self.agent)._uia_request(self.employee, 'Need to check again'), consent,
                         'no duplicate pending request')
        with self.assertRaises(AccessError):
            consent._uia_decide('approve', self.agent)  # only the target decides
        consent._uia_decide('approve', self.employee)
        self.assertEqual(consent.state, 'approved')
        with self.assertRaises(UserError):
            consent._uia_decide('refuse', self.employee)  # only once
        log = self._start(self.agent, self.employee)
        self.assertEqual(consent.state, 'used')
        self.assertEqual(log.consent_id, consent)
        log._uia_end('manual')
        with self.assertRaisesRegex(UserError, 'must approve'):
            self._start(self.agent, self.employee)  # consent is single use

    def test_consent_refused_and_grant(self):
        self.employee.impersonation_consent = 'require'
        consent = self.env['user.impersonation.consent'].with_user(self.agent)._uia_request(
            self.employee, 'Need to check the dashboard')
        consent.with_user(self.employee).action_refuse()
        self.assertEqual(consent.state, 'refused')
        with self.assertRaises(UserError):
            self._start(self.agent, self.employee)
        self.employee.with_user(self.employee).write(
            {'impersonation_grant_until': fields.Datetime.now() + timedelta(hours=2)})
        self._start(self.agent, self.employee)

    def test_default_consent_and_notify_mode(self):
        set_config(self.env, {'default_consent': 'require'})
        with self.assertRaises(UserError):
            self._start(self.agent, self.employee)
        self.employee.impersonation_consent = 'notify'
        log = self._start(self.agent, self.employee)
        mail = self.env['mail.mail'].search([('model', '=', 'user.impersonation.session'), ('res_id', '=', log.id)])
        self.assertEqual(mail.recipient_ids, self.employee.partner_id)

    def test_settings_roundtrip(self):
        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.uia_track_changes)
        settings.write({'uia_require_password': False, 'uia_track_changes': False, 'uia_idle_timeout': 0,
                        'uia_time_limit': 20, 'uia_max_time_limit': 40, 'uia_ip_allowlist': '10.0.0.0/8',
                        'uia_protected_user_ids': [Command.set(self.employee.ids)],
                        'uia_protected_group_ids': [Command.set(self.g_portal.ids)]})
        settings.execute()
        conf = get_config(self.env)
        self.assertFalse(conf['track_changes'], 'a default-True boolean can be switched off')
        self.assertEqual(conf['idle_timeout'], 0, 'zero survives')
        self.assertEqual((conf['time_limit'], conf['max_time_limit']), (20, 40))
        self.assertTrue(self.employee.impersonation_protected)
        self.assertTrue(self.g_portal.impersonation_protected)
        settings = self.env['res.config.settings'].create({})
        self.assertEqual(settings.uia_protected_user_ids, self.employee)
        self.assertFalse(settings.uia_track_changes)
        for bad in ({'uia_time_limit': 50, 'uia_max_time_limit': 40}, {'uia_ip_allowlist': 'not-an-ip'}):
            with self.assertRaises(ValidationError):
                self.env['res.config.settings'].create(bad).execute()

    def test_picker(self):
        Wizard = self.env['user.impersonation.wizard']
        other = self._user('Far Away', 'uia_far', [self.g_employee], companies=self.company_2)
        rows = Wizard.with_user(self.agent).uia_search_targets('uia_')
        ids = [r['id'] for r in rows]
        self.assertIn(self.employee.id, ids)
        self.assertNotIn(other.id, ids, 'other company hidden')
        self.assertNotIn(self.agent.id, ids, 'self hidden')
        self.assertTrue(next(r for r in rows if r['id'] == self.portal.id)['portal'])
        rows = Wizard.with_user(self.agent).uia_search_targets('', self.g_portal.id)
        self.assertEqual({r['id'] for r in rows} & {self.employee.id, self.portal.id}, {self.portal.id})
        self.assertTrue(Wizard.with_user(self.agent).uia_toggle_favorite(self.employee.id))
        self._start(self.agent, self.portal)._uia_end('manual')
        rows = Wizard.with_user(self.agent).uia_search_targets('uia_')
        self.assertEqual({r['id'] for r in rows[:2]}, {self.employee.id, self.portal.id}, 'favourites and recent first')
        self.assertTrue(next(r for r in rows if r['id'] == self.portal.id)['recent'])
        self.assertTrue(next(r for r in rows if r['id'] == self.employee.id)['favorite'])
        self.assertFalse(Wizard.with_user(self.agent).uia_toggle_favorite(self.employee.id))
        with self.assertRaises(AccessError):
            Wizard.with_user(self.employee).uia_search_targets('')
        self.assertTrue(Wizard.with_user(self.agent).uia_picker_groups())

    def test_picker_lists_only_users_that_can_be_started(self):
        Wizard = self.env['user.impersonation.wizard'].with_user(self.agent)
        richer = self._user('Rich Rights', 'uia_rich', [self.g_employee, self.env.ref('base.group_allow_export')])
        both = self._user('Both Companies', 'uia_both', [self.g_employee], companies=self.company | self.company_2)
        admin2 = self._user('Second Admin', 'uia_admin2', [self.env.ref('base.group_erp_manager')])
        prot = self._user('Prot Group', 'uia_prot', [self.g_employee, self.g_partner_manager])
        self.env['res.groups'].create({'name': 'UIA Protected', 'impersonation_protected': True,
                                       'user_ids': [Command.link(prot.id)]})
        candidates = self.env['res.users'].search([('login', '=like', 'uia_%')])
        listed = {r['id'] for r in Wizard.uia_search_targets('uia_', limit=100)}
        Session = self.env['user.impersonation.session']
        for user in candidates:
            try:
                Session._uia_check(self.agent, user)
                ok = True
            except (UserError, AccessError):
                ok = False
            self.assertEqual(user.id in listed, ok, user.login)
        self.assertFalse(listed & set((richer | both | admin2 | prot).ids))
        self.assertIn(self.employee.id, listed)
        # policies are applied too: a portal-only policy hides internal users
        self.env['user.impersonation.policy'].create({
            'name': 'Portal only', 'impersonator_group_ids': [Command.link(self.g_user.id)], 'target_type': 'portal'})
        listed = {r['id'] for r in Wizard.uia_search_targets('uia_', limit=100)}
        self.assertEqual(listed, {self.portal.id})

    def test_wizard_shows_target_and_blocks(self):
        Wizard = self.env['user.impersonation.wizard'].with_user(self.agent)
        wiz = Wizard.create({'target_id': self.employee.id, 'reason': 'Checking the employee menu'})
        self.assertEqual(wiz.target_company_id, self.company)
        self.assertIn('Role / User', wiz.target_groups)
        self.assertFalse(wiz.blocked_message)
        self.assertEqual(wiz.time_limit, 60)
        root_wiz = Wizard.create({'target_id': self.env.ref('base.user_root').id})
        self.assertIn('superuser', root_wiz.blocked_message)
        wiz2 = Wizard.with_context(active_model='res.users', active_ids=[self.portal.id]).create({})
        self.assertEqual(wiz2.target_id, self.portal)
        with self.assertRaises(UserError):
            Wizard.with_context(active_model='res.users', active_ids=[self.portal.id, self.employee.id]).default_get(['target_id'])

    def test_wizard_start_without_browser_session(self):
        wiz = self.env['user.impersonation.wizard'].with_user(self.agent).create(
            {'target_id': self.employee.id, 'reason': 'Checking the employee menu', 'reference': 'TCK-9'})
        with self.assertRaisesRegex(UserError, 'web browser'):
            wiz.action_start()
        self.assertFalse(self.env['user.impersonation.session'].search([('target_id', '=', self.employee.id)]))

    def test_safe_local_url(self):
        for bad in ('https://evil.example', '//evil.example', '/\\evil.example', '/\t/evil.example',
                    '/\n/evil.example', ' /odoo', 'javascript:alert(1)', ''):
            self.assertEqual(safe_local_url(bad, '/odoo'), '/odoo', repr(bad))
        self.assertEqual(safe_local_url('/odoo/contacts?view_type=list', '/odoo'), '/odoo/contacts?view_type=list')
