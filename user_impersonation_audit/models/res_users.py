from odoo import SUPERUSER_ID, _, api, fields, models

from .common import GROUP_MANAGER

CONSENT_MODES = [
    ('default', 'Use the default from Settings'),
    ('never', 'Never ask'),
    ('notify', 'Notify only'),
    ('require', 'Require consent'),
]


class ResUsers(models.Model):
    _inherit = 'res.users'

    impersonation_consent = fields.Selection(
        CONSENT_MODES, 'Consent to be impersonated', default='default', required=True,
        help='Never ask: no question, no email. Notify only: the user gets an email when someone logs in as them. '
             'Require consent: the user must approve each request (or grant access from their preferences).')
    impersonation_protected = fields.Boolean(
        'Never impersonate', help='Nobody can log in as this user, whatever the policies say.')
    impersonation_grant_until = fields.Datetime(
        'Allow support access until', user_writeable=True,
        help='Until this time, support staff may log in as you without asking. Leave empty to be asked each time '
             '(only when your account requires consent).')
    impersonation_favorite_ids = fields.Many2many(
        'res.users', 'res_users_impersonation_favorite_rel', 'user_id', 'favorite_id',
        string='Favourite impersonation targets', groups='user_impersonation_audit.group_impersonation_user')
    impersonation_session_count = fields.Integer(compute='_compute_impersonation_session_count')
    impersonation_can_login_as = fields.Boolean(compute='_compute_impersonation_can_login_as')

    def _compute_impersonation_session_count(self):
        Session = self.env['user.impersonation.session']
        if not self.env.user.has_group(GROUP_MANAGER):
            self.impersonation_session_count = 0
            return
        counts = dict(Session._read_group([('target_id', 'in', self.ids)], ['target_id'], ['__count']))
        for user in self:
            user.impersonation_session_count = counts.get(user, 0)

    @api.depends_context('uid')
    def _compute_impersonation_can_login_as(self):
        me = self.env.user
        for user in self:
            user.impersonation_can_login_as = bool(
                user.id and user.active and user != me and user.id != SUPERUSER_ID and not user.impersonation_protected)

    def action_impersonation_login_as(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Log in as %s', self.name),
            'res_model': 'user.impersonation.wizard',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_target_id': self.id},
        }

    def action_impersonation_sessions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('user_impersonation_audit.action_impersonation_session')
        action['domain'] = [('target_id', '=', self.id)]
        action['context'] = {}
        return action


class ResGroups(models.Model):
    _inherit = 'res.groups'

    impersonation_protected = fields.Boolean(
        'Never impersonate members', help='Nobody can log in as a member of this group.')
