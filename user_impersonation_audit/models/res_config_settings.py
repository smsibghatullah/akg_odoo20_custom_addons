from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .common import PARAMS, get_config, set_config


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    uia_time_limit = fields.Integer('Session time limit (min)')
    uia_max_time_limit = fields.Integer('Hard maximum (min)')
    uia_idle_timeout = fields.Integer('Idle timeout (min)')
    uia_min_reason_length = fields.Integer('Minimum reason length')
    uia_read_only_default = fields.Boolean('Read-only by default')
    uia_allow_admin_targets = fields.Boolean('System administrators may impersonate administrators')
    uia_require_password = fields.Boolean('Ask for my password before starting')
    uia_default_consent = fields.Selection([('never', 'Never ask'), ('notify', 'Notify only'),
                                            ('require', 'Require consent')], 'Default consent')
    uia_notify_target = fields.Boolean('Email the user when a session starts')
    uia_notify_managers = fields.Boolean('Email impersonation managers when a session starts')
    uia_send_summary = fields.Boolean('Send an end-of-session summary to the user')
    uia_track_changes = fields.Boolean('Record field changes')
    uia_track_actions = fields.Boolean('Record opened menus and actions')
    uia_allow_extension = fields.Boolean('Allow one extension per session')
    uia_extension_minutes = fields.Integer('Extension (min)')
    uia_retention_days = fields.Integer('Keep logs for (days)')
    uia_ip_allowlist = fields.Char('Allowed networks')
    uia_hours_from = fields.Float('Allowed from')
    uia_hours_to = fields.Float('Allowed until')
    uia_protected_user_ids = fields.Many2many('res.users', string='Protected users',
                                              domain=[('share', '=', False)])
    uia_protected_group_ids = fields.Many2many('res.groups', string='Protected groups')

    @api.model
    def get_values(self):
        res = super().get_values()
        res.update({'uia_' + key: value for key, value in get_config(self.env).items()})
        res['uia_protected_user_ids'] = [(6, 0, self.env['res.users'].sudo().with_context(active_test=False).search(
            [('impersonation_protected', '=', True)]).ids)]
        res['uia_protected_group_ids'] = [(6, 0, self.env['res.groups'].sudo().search(
            [('impersonation_protected', '=', True)]).ids)]
        return res

    def set_values(self):
        super().set_values()
        self._uia_validate()
        set_config(self.env, {key: self['uia_' + key] for key in PARAMS})
        Users = self.env['res.users'].sudo().with_context(active_test=False)
        old = Users.search([('impersonation_protected', '=', True)])
        (old - self.uia_protected_user_ids).write({'impersonation_protected': False})
        (self.uia_protected_user_ids - old).write({'impersonation_protected': True})
        Groups = self.env['res.groups'].sudo()
        old = Groups.search([('impersonation_protected', '=', True)])
        (old - self.uia_protected_group_ids).write({'impersonation_protected': False})
        (self.uia_protected_group_ids - old).write({'impersonation_protected': True})

    def _uia_validate(self):
        if self.uia_time_limit < 1 or self.uia_max_time_limit < self.uia_time_limit:
            raise ValidationError(_('The time limit must be at least 1 minute and not above the hard maximum.'))
        if min(self.uia_idle_timeout, self.uia_min_reason_length, self.uia_extension_minutes,
               self.uia_retention_days) < 0:
            raise ValidationError(_('Durations and lengths cannot be negative.'))
        if not (0 <= self.uia_hours_from < 24 and 0 <= self.uia_hours_to < 24):
            raise ValidationError(_('Allowed hours must be between 00:00 and 23:59.'))
        try:
            self.env['user.impersonation.session']._uia_parse_networks(self.uia_ip_allowlist)
        except ValueError as e:
            raise ValidationError(_('Invalid network in the allowlist: %s', e)) from e
