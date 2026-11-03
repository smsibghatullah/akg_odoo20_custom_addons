import contextlib
from unittest.mock import patch

from odoo import Command
from odoo.tests import TransactionCase

from odoo.addons.user_impersonation_audit.models.common import GROUP_MANAGER, GROUP_USER, set_config

MODELS = 'odoo.addons.user_impersonation_audit.models'


class ImpersonationCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['user.impersonation.policy'].search([]).active = False  # demo policies
        cls.company = cls.env.ref('base.main_company')
        cls.company_2 = cls.env['res.company'].create({'name': 'Second Co'})
        cls.g_user = cls.env.ref(GROUP_USER)
        cls.g_manager = cls.env.ref(GROUP_MANAGER)
        cls.g_employee = cls.env.ref('base.group_user')
        cls.g_portal = cls.env.ref('base.group_portal')
        cls.g_partner_manager = cls.env.ref('base.group_partner_manager')
        set_config(cls.env, {'require_password': False, 'min_reason_length': 10, 'default_consent': 'never',
                             'ip_allowlist': '', 'hours_from': 0.0, 'hours_to': 0.0,
                             'allow_admin_targets': False, 'notify_target': False, 'notify_managers': False,
                             'send_summary': False, 'track_changes': True, 'track_actions': True,
                             'time_limit': 60, 'max_time_limit': 120, 'read_only_default': False})
        cls.agent = cls._user('Agent Smith', 'uia_agent', [cls.g_user, cls.g_partner_manager])
        cls.manager = cls._user('Manager Moss', 'uia_manager', [cls.g_manager])
        cls.employee = cls._user('Emma Employee', 'uia_employee', [cls.g_employee, cls.g_partner_manager])
        cls.portal = cls._user('Paul Portal', 'uia_portal', [cls.g_portal])
        cls.admin = cls.env.ref('base.user_admin')
        cls.admin.group_ids = [Command.link(cls.g_user.id)]

    @classmethod
    def _user(cls, name, login, groups, companies=None):
        companies = companies or cls.company
        return cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': name, 'login': login, 'email': '%s@example.com' % login, 'password': login + '_pwd_123',
            'group_ids': [Command.set([g.id for g in groups])],
            'company_id': companies[0].id, 'company_ids': [Command.set(companies.ids)],
        })

    def _start(self, impersonator, target, reason='Customer cannot open the invoice', **kw):
        return self.env['user.impersonation.session'].with_user(impersonator)._uia_start(target, reason, **kw)

    @contextlib.contextmanager
    def impersonating(self, session, read_only=False):
        """Simulate the HTTP session of an impersonated browser for ORM-level hooks."""
        imp = {'log_id': session.id, 'real_uid': session.impersonator_id.id, 'target_uid': session.target_id.id,
               'read_only': read_only}
        with patch(MODELS + '.base.current_impersonation', return_value=imp), \
                patch(MODELS + '.mail_thread.current_impersonation', return_value=imp):
            yield imp
