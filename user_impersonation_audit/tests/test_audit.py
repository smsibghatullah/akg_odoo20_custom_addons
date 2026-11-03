from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from odoo.addons.user_impersonation_audit.models.common import is_implicit_write, set_config

from .common import ImpersonationCase


@tagged('post_install', '-at_install')
class TestImpersonationAudit(ImpersonationCase):

    def setUp(self):
        super().setUp()
        self.log = self._start(self.agent, self.employee)
        self.partner = self.env['res.partner'].create({'name': 'Acme Test', 'phone': '111'})

    def test_field_changes_are_recorded(self):
        with self.impersonating(self.log):
            self.partner.with_user(self.employee).write({'phone': '222', 'name': 'Acme Renamed', 'comment': '<p>x</p>'})
        act = self.log.activity_ids.filtered(lambda a: a.operation == 'write')
        self.assertEqual(len(act), 1)
        self.assertEqual((act.model, act.res_id, act.record_name), ('res.partner', self.partner.id, 'Acme Renamed'))
        changes = {c.field_name: (c.old_value, c.new_value) for c in act.change_ids}
        self.assertEqual(changes['phone'], ('111', '222'))
        self.assertEqual(changes['name'], ('Acme Test', 'Acme Renamed'))
        self.assertEqual(self.log.change_count, 1)
        action = act.action_open_record()
        self.assertEqual((action['res_model'], action['res_id']), ('res.partner', self.partner.id))

    def test_create_unlink_and_unchanged_write(self):
        with self.impersonating(self.log):
            Partner = self.env['res.partner'].with_user(self.employee)
            new = Partner.create({'name': 'Made While Impersonating'})
            self.partner.with_user(self.employee).write({'phone': '111'})  # no real change
            new.unlink()
        ops = self.log.activity_ids.mapped('operation')
        self.assertEqual(sorted(ops), ['create', 'unlink'])
        self.assertIn('Made While Impersonating', self.log.activity_ids.mapped('record_name'))

    def test_technical_and_implicit_writes_skipped(self):
        with self.impersonating(self.log):
            self.env['res.users.settings'].with_user(self.employee)._find_or_create_for_user(self.employee)
            self.env['ir.attachment'].with_user(self.employee).sudo().create({'name': 'report.pdf', 'raw': b'x'})
        self.assertFalse(self.log.activity_ids)
        partner = self.env['res.partner']
        self.assertTrue(is_implicit_write(partner, {'access_token': 'abc'}), 'portal access token')
        self.assertFalse(is_implicit_write(partner, {'access_token': 'abc', 'phone': '1'}))
        self.assertFalse(is_implicit_write(partner, {}))

    def test_sudo_writes_on_behalf_of_the_user_are_recorded(self):
        # e.g. the portal address form writes the partner with sudo()
        with self.impersonating(self.log):
            self.partner.with_user(self.employee).sudo().write({'phone': '333'})
        self.assertEqual(self.log.activity_ids.change_ids.mapped('new_value'), ['333'])

    def test_tracking_can_be_switched_off(self):
        set_config(self.env, {'track_changes': False})
        with self.impersonating(self.log):
            self.partner.with_user(self.employee).write({'phone': '444'})
        self.assertFalse(self.log.activity_ids)

    def test_read_only_blocks_orm(self):
        with self.impersonating(self.log, read_only=True):
            Partner = self.env['res.partner'].with_user(self.employee)
            with self.assertRaisesRegex(UserError, 'Read-only'):
                Partner.create({'name': 'Blocked'})
            with self.assertRaisesRegex(UserError, 'Read-only'):
                self.partner.with_user(self.employee).write({'phone': '999'})
            with self.assertRaisesRegex(UserError, 'Read-only'):
                self.partner.with_user(self.employee).unlink()
            with self.assertRaisesRegex(UserError, 'Read-only'):
                self.partner.with_user(self.employee).message_post(body='hello')
            with self.assertRaisesRegex(UserError, 'Read-only'):  # the chatter controller posts with sudo()
                self.partner.with_user(self.employee).sudo().message_post(body='hello')
            # framework messages under another author still work (OdooBot welcome on first load)
            odoobot = self.env.ref('base.partner_root')
            self.partner.with_user(self.employee).sudo().message_post(body='Welcome', author_id=odoobot.id)
            # sudo() made by a controller on the user's behalf is blocked too
            with self.assertRaisesRegex(UserError, 'Read-only'):
                self.partner.with_user(self.employee).sudo().write({'street': 'Changed Street 1'})
            with self.assertRaisesRegex(UserError, 'Read-only'):
                self.env['res.partner'].with_user(self.employee).sudo().create({'name': 'Blocked too'})
            # framework bookkeeping while browsing still works (portal tokens, report attachments)
            self.env['ir.attachment'].with_user(self.employee).sudo().create({'name': 'report.pdf', 'raw': b'x'})
            with self.assertRaisesRegex(UserError, 'Read-only'):
                self.env['ir.attachment'].with_user(self.employee).create({'name': 'upload.txt', 'raw': b'x'})
            # reading, wizards (transient) and the real user's own work are not blocked
            self.partner.with_user(self.employee).read(['name'])
            self.env['user.impersonation.wizard'].with_user(self.agent).create({'target_id': self.portal.id})
            self.partner.with_user(self.agent).write({'phone': '555'})
        self.assertEqual(self.partner.phone, '555')

    def test_credentials_never_changed(self):
        with self.impersonating(self.log):
            for vals in ({'password': 'new-pass-123'}, {'impersonation_grant_until': fields.Datetime.now()},
                         {'impersonation_consent': 'never'}):
                with self.assertRaisesRegex(UserError, 'cannot be changed'):
                    self.employee.with_user(self.employee).write(vals)
            with self.assertRaisesRegex(UserError, 'cannot be changed'):
                self.employee.with_user(self.employee).sudo().write({'password': 'new-pass-123'})

    def test_messages_signed_by_real_user(self):
        with self.impersonating(self.log):
            msg = self.partner.with_user(self.employee).message_post(body='Checked the address', message_type='comment')
        self.assertEqual(msg.author_id, self.agent.partner_id)
        act = self.log.activity_ids.filtered(lambda a: a.operation == 'message')
        self.assertEqual(act.res_id, self.partner.id)

    def test_append_only(self):
        for user in (self.manager, self.agent, self.admin):
            with self.assertRaises(AccessError):
                self.log.with_user(user).write({'reason': 'tampered'})
            with self.assertRaises(AccessError):
                self.log.with_user(user).unlink()
            with self.assertRaises(AccessError):
                self.env['user.impersonation.session'].with_user(user).create({
                    'impersonator_id': user.id, 'target_id': self.employee.id, 'company_id': self.company.id,
                    'reason': 'fake session entry'})
        with self.impersonating(self.log):
            self.partner.with_user(self.employee).write({'phone': '777'})
        act = self.log.activity_ids
        with self.assertRaises(AccessError):
            act.with_user(self.manager).write({'summary': 'x'})
        with self.assertRaises(AccessError):
            act.change_ids.with_user(self.manager).unlink()
        self.assertEqual(self.log.reason, 'Customer cannot open the invoice')

    def test_record_rules(self):
        Session = self.env['user.impersonation.session']
        other_agent = self._user('Other Agent', 'uia_agent2', [self.g_user])
        other_log = self._start(other_agent, self.portal)
        self.assertEqual(Session.with_user(self.agent).search([]), self.log, 'agents see their own sessions')
        with self.assertRaises(AccessError):
            Session.with_user(self.employee).search([])  # targets have no access
        self.assertEqual(Session.with_user(self.manager).search([('id', 'in', (self.log | other_log).ids)]),
                         self.log | other_log)
        far_manager = self._user('Far Manager', 'uia_far_mgr', [self.g_manager], companies=self.company_2)
        self.assertFalse(Session.with_user(far_manager).search([('id', 'in', (self.log | other_log).ids)]),
                         'managers only see sessions of their companies')

    def test_force_end(self):
        with self.assertRaises(AccessError):
            self.log.with_user(self.agent).action_force_end()
        self.log.with_user(self.manager).action_force_end()
        self.assertEqual((self.log.state, self.log.end_reason, self.log.ended_by_id),
                         ('ended', 'forced', self.manager))
        self.assertGreaterEqual(self.log.duration, 0)

    def test_silent_note_on_target(self):
        msgs = self.env['mail.message'].search([('model', '=', 'res.partner'), ('res_id', '=', self.employee.partner_id.id)])
        note = msgs.filtered(lambda m: 'logged in as this user' in (m.body or ''))
        self.assertEqual(len(note), 1)
        self.assertEqual(note.subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(note.author_id, self.agent.partner_id)
        self.assertFalse(note.notification_ids, 'no inbox or email notification')

    def test_notifications_and_summary(self):
        self.log._uia_end('manual')
        Mail = self.env['mail.mail']
        set_config(self.env, {'notify_target': True, 'notify_managers': True, 'send_summary': True})
        log = self._start(self.agent, self.portal)
        mails = Mail.search([('model', '=', 'user.impersonation.session'), ('res_id', '=', log.id)])
        self.assertTrue(self.portal.partner_id | self.manager.partner_id <= mails.recipient_ids)
        self.assertNotIn(self.agent.partner_id, mails.recipient_ids)
        self.env['user.impersonation.activity'].create({'session_id': log.id, 'operation': 'write', 'model': 'res.partner',
                                        'res_id': self.partner.id, 'record_name': 'Acme Test', 'summary': 'Phone'})
        log._uia_end('manual')
        summary = Mail.search([('model', '=', 'user.impersonation.session'), ('res_id', '=', log.id)]) - mails
        self.assertEqual(summary.recipient_ids, self.portal.partner_id)
        self.assertIn('Acme Test', summary.body_html)

    def test_cron_expires_and_purges(self):
        Session = self.env['user.impersonation.session'].sudo()
        self.log.write({'start_date': fields.Datetime.now() - timedelta(hours=3),
                        'planned_end_date': fields.Datetime.now() - timedelta(hours=2)})
        old = self._start(self.agent, self.portal)
        old._uia_end('manual')
        old.write({'end_date': fields.Datetime.now() - timedelta(days=400),
                   'start_date': fields.Datetime.now() - timedelta(days=400, hours=1)})
        set_config(self.env, {'retention_days': 365})
        Session._cron_housekeeping()
        self.assertEqual((self.log.state, self.log.end_reason), ('ended', 'expired'))
        self.assertFalse(old.exists())
        set_config(self.env, {'retention_days': 0})
        self.log.write({'end_date': fields.Datetime.now() - timedelta(days=4000)})
        Session._cron_housekeeping()
        self.assertTrue(self.log.exists(), '0 keeps logs forever')

    def test_user_form_helpers(self):
        self.assertTrue(self.employee.with_user(self.agent).impersonation_can_login_as)
        self.assertFalse(self.agent.with_user(self.agent).impersonation_can_login_as)
        action = self.employee.action_impersonation_login_as()
        self.assertEqual(action['context']['default_target_id'], self.employee.id)
        self.assertEqual(self.employee.with_user(self.manager).impersonation_session_count, 1)
        self.assertEqual(self.employee.action_impersonation_sessions()['domain'], [('target_id', '=', self.employee.id)])
        # the user can grant support access from their preferences
        self.employee.with_user(self.employee).write({'impersonation_grant_until': fields.Datetime.now()})
        with self.assertRaises(AccessError):
            self.employee.with_user(self.employee).write({'impersonation_protected': True})

    def test_read_only_blocks_saved_filters(self):
        with self.impersonating(self.log, read_only=True):
            with self.assertRaisesRegex(UserError, 'Read-only'):
                self.env['ir.filters'].with_user(self.employee).create(
                    {'name': 'My filter', 'model_id': 'res.partner', 'user_ids': [self.employee.id]})

    def test_read_only_allows_print_flags(self):
        """Printing a delivery slip marks it printed: allowed in read-only, real edits still refused."""
        if 'stock.picking' not in self.env:
            self.skipTest('stock not installed')
        picking = self.env['stock.picking'].search([('state', '=', 'assigned')], limit=1)
        if not picking:
            self.skipTest('no ready transfer in this database')
        group = self.env.ref('stock.group_stock_user')
        self.employee.group_ids = [Command.link(group.id)]
        self.log.target_id.invalidate_recordset()
        with self.impersonating(self.log, read_only=True):
            pdf = self.env['ir.actions.report'].with_user(self.employee)._render_qweb_pdf(
                'stock.action_report_picking', picking.ids)
            self.assertTrue(pdf[0])
            with self.assertRaisesRegex(UserError, 'Read-only'):
                picking.with_user(self.employee).write({'printed': True, 'origin': 'changed'})
        self.assertTrue(picking.printed)
