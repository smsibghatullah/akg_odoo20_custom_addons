import hashlib
import re
import time

from odoo import Command
from odoo.http.session import session_store
from odoo.tests import HttpCase, JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.user_impersonation_audit.models.common import GROUP_MANAGER, GROUP_USER, SESSION_KEY, set_config


@tagged('post_install', '-at_install')
class TestImpersonationHttp(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['user.impersonation.policy'].search([]).active = False
        set_config(cls.env, {'require_password': False, 'min_reason_length': 10, 'default_consent': 'never',
                             'ip_allowlist': '', 'hours_from': 0.0, 'hours_to': 0.0, 'time_limit': 60,
                             'max_time_limit': 90, 'extension_minutes': 20, 'allow_extension': True,
                             'idle_timeout': 30, 'track_changes': True, 'track_actions': True,
                             'read_only_default': False})
        g_user, g_manager = cls.env.ref(GROUP_USER), cls.env.ref(GROUP_MANAGER)
        employee = cls.env.ref('base.group_user')
        cls.agent = cls._user('Http Agent', 'uia_http_agent',
                              [g_user, cls.env.ref('base.group_partner_manager')])
        cls.agent2 = cls._user('Second Agent', 'uia_http_agent2', [g_user])
        cls.employee = cls._user('Http Employee', 'uia_http_employee', [employee, cls.env.ref('base.group_partner_manager')])
        cls.portal = cls._user('Http Portal', 'uia_http_portal', [cls.env.ref('base.group_portal')])
        cls.manager = cls._user('Http Manager', 'uia_http_manager', [g_manager])
        cls.partner = cls.env['res.partner'].create({'name': 'Http Partner', 'phone': '100'})

    @classmethod
    def _user(cls, name, login, groups):
        return cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': name, 'login': login, 'password': login, 'email': login + '@example.com',
            'group_ids': [Command.set([g.id for g in groups])]})

    # helpers ---------------------------------------------------------------
    def _rpc_start(self, target, read_only=False, landing='/odoo/action-base.action_res_users', back='/odoo/settings'):
        wiz = self.env['user.impersonation.wizard'].with_user(self.uid_user).create({
            'target_id': target.id, 'reason': 'Reproduce the reported problem', 'read_only': read_only,
            'landing_url': landing, 'return_url': back})
        return self.make_jsonrpc_request('/web/dataset/call_button', {
            'model': 'user.impersonation.wizard', 'method': 'action_start', 'args': [[wiz.id]], 'kwargs': {}})

    def _session(self):
        return session_store().get(self.opener.cookies['session_id'])

    def _login_agent(self, user=None):
        self.uid_user = user or self.agent
        self.authenticate(self.uid_user.login, self.uid_user.login)
        self.old_sid = self.opener.cookies['session_id']

    def _log(self, target):
        return self.env['user.impersonation.session'].search([('target_id', '=', target.id)], limit=1)

    def _return(self):
        """Click Return: the GET page only shows a button, the switch is a POST with the CSRF token."""
        page = self.url_open('/impersonation/return')
        self.assertEqual(page.status_code, 200)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        return self.url_open('/impersonation/return', data={'csrf_token': token}, allow_redirects=False)

    def _has(self, module):
        return bool(self.env['ir.module.module'].search_count([('name', '=', module), ('state', '=', 'installed')]))

    def _patch_session(self, **values):
        sess = self._session()
        sess[SESSION_KEY] = dict(sess[SESSION_KEY], **values)
        session_store().save(sess)

    # tests -----------------------------------------------------------------
    def _call(self, model, method, args, kwargs=None):
        return self.make_jsonrpc_request('/web/dataset/call_kw/%s/%s' % (model, method), {
            'model': model, 'method': method, 'args': args, 'kwargs': kwargs or {}})

    def test_switch_and_return(self):
        self._login_agent()
        sess = self._session()
        sess['identity-check-last'] = time.time()  # the agent recently re-entered their password
        session_store().save(sess)
        action = self._rpc_start(self.employee)
        self.assertEqual(action, {'type': 'ir.actions.act_url', 'url': '/odoo/action-base.action_res_users',
                                  'target': 'self'})
        sess = self._session()
        self.assertEqual(sess.uid, self.employee.id, 'the browser session now belongs to the target')
        self.assertNotEqual(self.opener.cookies['session_id'], self.old_sid, 'session id rotated like a login')
        self.assertEqual(sess[SESSION_KEY]['real_uid'], self.agent.id)
        self.assertNotIn('identity-check-last', sess, "the target's account never inherits the password check")
        info = self.make_jsonrpc_request('/web/session/get_session_info')
        self.assertEqual(info['uid'], self.employee.id)
        self.assertEqual(info['impersonation']['target_name'], 'Http Employee')
        self.assertEqual(info['impersonation']['real_name'], 'Http Agent')
        self.assertFalse(info['impersonation_can_start'])
        log = self._log(self.employee)
        self.assertEqual(log.session_hash, hashlib.sha256(self.old_sid.encode()).hexdigest())
        stored = ' '.join(str(v) for v in log.read()[0].values())
        self.assertNotIn(self.old_sid, stored, 'the raw session id is never stored')
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertTrue(log.user_agent)

        res = self._return()
        self.assertEqual(res.status_code, 303)
        self.assertTrue(res.headers['Location'].endswith('/odoo/settings'))
        self.assertEqual(self._session().uid, self.agent.id)
        self.assertNotIn(SESSION_KEY, self._session())
        self.assertIn('identity-check-last', self._session(), 'the real session is given back as it was')
        log.invalidate_recordset()
        self.assertEqual((log.state, log.end_reason), ('ended', 'manual'))
        self.assertTrue(self.make_jsonrpc_request('/web/session/get_session_info')['impersonation_can_start'])

    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_no_nested_impersonation(self):
        self._login_agent()
        self._rpc_start(self.agent2)  # agent2 can impersonate too, but not from inside a session
        self.uid_user = self.agent2
        with self.assertRaises(JsonRpcException):
            self._rpc_start(self.employee)
        self.assertFalse(self._log(self.employee))

    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_read_only_blocks_rpc(self):
        self._login_agent()
        self._rpc_start(self.employee, read_only=True)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request('/web/dataset/call_kw/res.partner/write', {
                'model': 'res.partner', 'method': 'write', 'args': [[self.partner.id], {'phone': '999'}], 'kwargs': {}})
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.phone, '100')
        # the web client still loads for a user who never logged in (onboarding writes are allowed)
        self.assertEqual(self.url_open('/odoo').status_code, 200)
        self.assertEqual(self.url_open('/odoo/discuss').status_code, 200)
        self.assertTrue(self.make_jsonrpc_request('/web/session/get_session_info')['impersonation']['read_only'])

    def test_return_from_read_only_session(self):
        self._login_agent()
        self._rpc_start(self.employee, read_only=True)
        res = self._return()
        self.assertEqual(res.status_code, 303)
        self.assertEqual(self._session().uid, self.agent.id)
        self.assertEqual(self._log(self.employee).end_reason, 'manual')

    def test_writes_tracked_over_rpc(self):
        self._login_agent()
        self._rpc_start(self.employee)
        self.make_jsonrpc_request('/web/dataset/call_kw/res.partner/write', {
            'model': 'res.partner', 'method': 'write', 'args': [[self.partner.id], {'phone': '200'}], 'kwargs': {}})
        change = self._log(self.employee).activity_ids.change_ids
        self.assertEqual((change.field_name, change.old_value, change.new_value), ('phone', '100', '200'))

    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_api_calls_refused(self):
        set_config(self.env, {'require_password': False})
        wiz = self.env['user.impersonation.wizard'].with_user(self.agent).create(
            {'target_id': self.employee.id, 'reason': 'Reproduce the reported problem'})
        try:
            self.xmlrpc_object.execute_kw(self.env.cr.dbname, self.agent.id, 'uia_http_agent',
                                          'user.impersonation.wizard', 'action_start', [[wiz.id]])
            failed = False
        except Exception as e:  # xmlrpc Fault
            failed = 'web browser' in str(e)
        self.assertTrue(failed)
        self.assertFalse(self._log(self.employee))

    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_password_check_required(self):
        set_config(self.env, {'require_password': True})
        self._login_agent()
        action = self._rpc_start(self.employee)
        self.assertEqual(action['res_model'], 'res.users.identitycheck')
        self.assertFalse(self._log(self.employee))
        self.assertEqual(self._session().uid, self.agent.id)

    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_timeout_returns_to_real_user(self):
        self._login_agent()
        self._rpc_start(self.employee)
        self._patch_session(expires=time.time() - 1)
        # no assertRaises here: it wraps the call in a savepoint that would roll back the log update
        try:
            self.make_jsonrpc_request('/web/session/get_session_info')
            code = None
        except JsonRpcException as e:
            code = e.code
        self.assertEqual(code, 100, 'the web client sees an expired session and reloads')
        self.assertEqual(self._session().uid, self.agent.id)
        log = self._log(self.employee)
        self.assertEqual((log.state, log.end_reason), ('ended', 'timeout'))

    def test_idle_timeout(self):
        self._login_agent()
        self._rpc_start(self.employee)
        self._patch_session(last_seen=time.time() - 31 * 60)
        res = self.url_open('/odoo', allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertEqual(self._session().uid, self.agent.id)
        self.assertEqual(self._log(self.employee).end_reason, 'idle')

    def test_forced_end_by_manager(self):
        self._login_agent()
        self._rpc_start(self.employee)
        self._log(self.employee).with_user(self.manager).action_force_end()
        res = self.url_open('/odoo', allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertEqual(self._session().uid, self.agent.id)
        log = self._log(self.employee)
        self.assertEqual((log.end_reason, log.ended_by_id), ('forced', self.manager))

    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_extend_once_within_hard_maximum(self):
        self._login_agent()
        self._rpc_start(self.employee)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request('/impersonation/extend', {'reason': 'short'})
        res = self.make_jsonrpc_request('/impersonation/extend', {'reason': 'Customer still on the phone'})
        self.assertAlmostEqual(res['remaining'], 80 * 60, delta=5)
        log = self._log(self.employee)
        self.assertTrue(log.extended)
        self.assertAlmostEqual((log.planned_end_date - log.start_date).total_seconds(), 80 * 60, delta=5)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request('/impersonation/extend', {'reason': 'Customer still on the phone'})
        self._patch_session(extended=False, expires=self._session()[SESSION_KEY]['started'] + 85 * 60)
        res = self.make_jsonrpc_request('/impersonation/extend', {'reason': 'Customer still on the phone'})
        self.assertLessEqual(res['remaining'], 90 * 60, 'never above the hard maximum')

    def test_actions_logged(self):
        self._login_agent()
        self._rpc_start(self.employee)
        action = self.env.ref('base.action_res_users')
        self.make_jsonrpc_request('/web/action/load', {'action_id': action.id})
        act = self._log(self.employee).activity_ids.filtered(lambda a: a.operation == 'action')
        self.assertEqual(act.summary, action.name)

    def test_screens_logged_once(self):
        self._login_agent()
        self._rpc_start(self.employee)
        spec = {'display_name': {}}
        for _i in range(2):  # the same screen twice is recorded once
            self._call('res.partner', 'web_search_read', [[('id', '=', self.partner.id)], spec])
        self._call('res.partner', 'web_read', [[self.partner.id], spec])
        acts = self._log(self.employee).activity_ids.filtered(lambda a: a.operation == 'action').sorted('id')
        self.assertEqual(acts.mapped('res_id'), [0, self.partner.id])
        self.assertEqual(acts[1].record_name, 'Http Partner')
        set_config(self.env, {'track_actions': False})
        self._call('res.users', 'web_search_read', [[], spec])
        self.assertEqual(len(self._log(self.employee).activity_ids), 2)

    def test_logout_ends_session(self):
        self._login_agent()
        self._rpc_start(self.employee)
        page = self.url_open('/impersonation/return')  # the page carries a token for the current session id
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        self.url_open('/web/session/logout', method='POST', data={'csrf_token': token}, allow_redirects=False)
        self.assertEqual(self._log(self.employee).end_reason, 'logout')

    def test_real_account_changed_means_logout(self):
        self._login_agent()
        self._rpc_start(self.employee)
        self.agent.password = 'changed-meanwhile'
        res = self._return()
        self.assertTrue(res.headers['Location'].endswith('/web/login'))
        self.assertFalse(self._session().uid)

    def test_portal_target_and_frontend_banner(self):
        self._login_agent()
        action = self._rpc_start(self.portal)
        self.assertEqual(self._session().uid, self.portal.id)
        self.assertNotIn('/odoo', action['url'])
        consent = self.env['user.impersonation.consent'].create({
            'requester_id': self.agent2.id, 'target_id': self.employee.id, 'company_id': self.env.company.id,
            'access_token': 'tok-123', 'reason': 'Check something'})
        page = self.url_open('/impersonation/consent/%s/approve?token=tok-123' % consent.id).text
        self.assertIn('o_uia_banner_frontend', page)
        self.assertIn('/impersonation/return', page)
        self.assertIn('Http Portal', page)
        self.assertEqual(consent.state, 'pending', 'the impersonator cannot answer for anyone')

    def test_consent_route(self):
        consent = self.env['user.impersonation.consent'].create({
            'requester_id': self.agent.id, 'target_id': self.employee.id, 'company_id': self.env.company.id,
            'access_token': 'tok-456', 'reason': 'Check something'})
        self.authenticate('uia_http_employee', 'uia_http_employee')
        self.assertEqual(self.url_open('/impersonation/consent/%s/approve?token=bad' % consent.id).status_code, 404)
        self.assertEqual(self.url_open('/impersonation/consent/%s/maybe?token=tok-456' % consent.id).status_code, 404)
        page = self.url_open('/impersonation/consent/%s/approve?token=tok-456' % consent.id)
        self.assertEqual(page.status_code, 200)
        self.assertIn('Access allowed', page.text)
        consent.invalidate_recordset()
        self.assertEqual(consent.state, 'approved')
        self.authenticate('uia_http_agent2', 'uia_http_agent2')
        consent2 = self.env['user.impersonation.consent'].create({
            'requester_id': self.agent.id, 'target_id': self.employee.id, 'company_id': self.env.company.id,
            'access_token': 'tok-789', 'reason': 'Check something'})
        page = self.url_open('/impersonation/consent/%s/refuse?token=tok-789' % consent2.id)
        self.assertIn('Nothing changed', page.text)
        self.assertEqual(consent2.state, 'pending')

    # abuse attempts ----------------------------------------------------------
    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_non_member_cannot_start_over_rpc(self):
        self.authenticate('uia_http_employee', 'uia_http_employee')
        attempts = [
            ('user.impersonation.session', '_uia_start', [self.agent2.id, 'Trying the private method directly']),
            ('user.impersonation.session', '_uia_switch_to_target', [[], '/odoo']),
            ('user.impersonation.wizard', 'create', [{'target_id': self.portal.id, 'reason': 'Not allowed at all'}]),
            ('user.impersonation.wizard', 'uia_search_targets', ['']),
            ('user.impersonation.session', 'create', [{'impersonator_id': self.employee.id,
                                                       'target_id': self.portal.id, 'reason': 'Forged entry',
                                                       'company_id': self.env.company.id}]),
        ]
        for model, method, args in attempts:
            with self.assertRaises(JsonRpcException, msg=method):
                self._call(model, method, args)
        self.assertEqual(self._session().uid, self.employee.id)
        self.assertNotIn(SESSION_KEY, self._session())
        self.assertFalse(self._log(self.portal))

    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_member_cannot_reach_admin_over_rpc(self):
        self._login_agent()
        with self.assertRaises(JsonRpcException):
            self._rpc_start(self.env.ref('base.user_admin'))
        with self.assertRaises(JsonRpcException):
            self._rpc_start(self.env.ref('base.user_root'))
        self.assertEqual(self._session().uid, self.agent.id)
        self.assertFalse(self.env['user.impersonation.session'].search([('impersonator_id', '=', self.agent.id)]))

    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_impersonated_session_cannot_tamper(self):
        self._login_agent()
        self._rpc_start(self.employee)
        log = self._log(self.employee)
        with self.assertRaises(JsonRpcException):  # the target's session cannot rewrite the trail
            self._call('user.impersonation.session', 'write', [[log.id], {'state': 'ended', 'reason': 'x'}])
        with self.assertRaises(JsonRpcException):  # nor grant itself standing access
            self._call('res.users', 'write', [[self.employee.id], {'impersonation_grant_until': '2099-01-01 00:00:00'}])
        with self.assertRaises(JsonRpcException):  # nor set a password on the target account
            self._call('res.users', 'write', [[self.employee.id], {'password': 'owned-now-123'}])
        self.employee.invalidate_recordset()
        self.assertFalse(self.employee.impersonation_grant_until)
        self.assertEqual(self._log(self.employee).state, 'active')

    @mute_logger('odoo.http', 'odoo.addons.rpc.controllers.xmlrpc')
    def test_expired_session_cannot_be_extended(self):
        self._login_agent()
        self._rpc_start(self.employee)
        self._patch_session(expires=time.time() - 1)
        try:
            self.make_jsonrpc_request('/impersonation/extend', {'reason': 'Trying to revive the session'})
            code = None
        except JsonRpcException as e:
            code = e.code
        self.assertEqual(code, 100)
        self.assertEqual(self._session().uid, self.agent.id)
        self.assertFalse(self._log(self.employee).extended)

    def test_return_url_cannot_leave_the_site(self):
        self._login_agent()
        self._rpc_start(self.employee, landing='//evil.example/x', back='/\t/evil.example')
        res = self._return()
        self.assertNotIn('evil', res.headers['Location'])
        self.assertTrue(res.headers['Location'].endswith('/odoo'))

    def test_backend_banner_and_picker(self):
        self.browser_js('/odoo', """(async () => {
            const wait = (sel) => new Promise((ok, ko) => {
                let n = 0;
                const t = setInterval(() => {
                    if (document.querySelector(sel)) { clearInterval(t); ok(); }
                    else if (++n > 100) { clearInterval(t); ko(new Error('missing ' + sel)); }
                }, 100);
            });
            await wait('.o_uia_picker_toggle');
            console.log('test successful');
        })().catch((e) => console.error(e.message));""", login='uia_http_agent', timeout=60)
        self._login_agent()
        self._rpc_start(self.employee)
        self.browser_js('/odoo', """(async () => {
            const wait = (sel) => new Promise((ok, ko) => {
                let n = 0;
                const t = setInterval(() => {
                    if (document.querySelector(sel)) { clearInterval(t); ok(); }
                    else if (++n > 100) { clearInterval(t); ko(new Error('missing ' + sel)); }
                }, 100);
            });
            await wait('.o_uia_banner .o_uia_return');
            const text = document.querySelector('.o_uia_banner').textContent;
            if (!text.includes('Http Employee') || !/\\d\\d:\\d\\d/.test(text)) { throw new Error('bad banner: ' + text); }
            if (document.querySelector('.o_uia_picker_toggle')) { throw new Error('no picker while impersonating'); }
            if (!document.body.classList.contains('o_uia_active')) { throw new Error('body offset missing'); }
            console.log('test successful');
        })().catch((e) => console.error(e.message));""", cookies={'session_id': self.opener.cookies['session_id']}, timeout=60)

    # QA regressions ------------------------------------------------------------
    @mute_logger('odoo.http')
    def test_return_needs_post_with_csrf(self):
        self._login_agent()
        self._rpc_start(self.employee)
        page = self.url_open('/impersonation/return')
        self.assertIn('o_uia_return_confirm', page.text)
        self.assertEqual(self._session().uid, self.employee.id, 'a plain link does not switch accounts')
        res = self.url_open('/impersonation/return', data={'csrf_token': 'forged'}, allow_redirects=False)
        self.assertNotEqual(res.status_code, 303)
        self.assertEqual(self._session().uid, self.employee.id, 'no switch without a valid CSRF token')
        self.assertEqual(self._return().status_code, 303)
        self.assertEqual(self._session().uid, self.agent.id)

    def test_frontend_pages_render_with_installed_modules(self):
        """Consent answer and return pages use web.frontend_layout: they must render whatever is
        installed (with website they need the website context)."""
        consent = self.env['user.impersonation.consent'].create({
            'requester_id': self.agent.id, 'target_id': self.employee.id, 'company_id': self.env.company.id,
            'access_token': 'tok-web', 'reason': 'Check something'})
        self.authenticate('uia_http_employee', 'uia_http_employee')
        page = self.url_open('/impersonation/consent/%s/refuse?token=tok-web' % consent.id)
        self.assertEqual(page.status_code, 200)
        self.assertIn('Access refused', page.text)
        if self._has('website'):
            self.assertIn('data-website-id', page.text, 'rendered through the website layout')

    def test_portal_target_with_installed_groups(self):
        """Groups every portal user gets (website implies some to portal) are not 'extra rights'."""
        self._login_agent()
        self._rpc_start(self.portal)
        self.assertEqual(self._session().uid, self.portal.id)
        self.assertEqual(self._return().status_code, 303)

    def test_uninstall_logs_impersonated_browser_out(self):
        self._login_agent()
        self._rpc_start(self.employee)
        self.url_open('/odoo/discuss')  # first request after the switch records the browser
        log = self._log(self.employee)
        sid = self.opener.cookies['session_id']
        self.assertEqual(log.sudo().session_identifier, sid[:42])
        self.env['user.impersonation.session']._uia_end_all_on_uninstall()
        self.assertFalse(log.exists(), 'trail dropped so demo users can be removed')
        self.assertFalse(session_store().get(sid).uid, 'the browser is logged out, not left as the target')
