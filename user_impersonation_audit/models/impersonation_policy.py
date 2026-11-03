from odoo import fields, models


class UserImpersonationPolicy(models.Model):
    _name = 'user.impersonation.policy'
    _description = 'Impersonation Policy'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    impersonator_group_ids = fields.Many2many(
        'res.groups', 'user_impersonation_policy_impersonator_rel', 'policy_id', 'group_id',
        string='Who (groups)', required=True,
        help='Members of any of these groups may use this policy. They also need the "Log in as other users" right.')
    target_group_ids = fields.Many2many(
        'res.groups', 'user_impersonation_policy_target_rel', 'policy_id', 'group_id',
        string='Whom (groups)', help='Users in any of these groups can be impersonated. Leave empty for any user.')
    target_type = fields.Selection([('all', 'Internal and portal users'), ('internal', 'Internal users only'),
                                    ('portal', 'Portal users only')], string='User type', default='all', required=True)
    company_ids = fields.Many2many('res.company', string='Companies',
                                   help='Target users must belong to one of these companies. Leave empty for all companies.')
    time_limit = fields.Integer('Time limit (min)', help='0 uses the time limit from Settings. Never above the hard maximum.')
    force_read_only = fields.Boolean('Force read-only', help='Sessions started under this policy are always read-only.')
    note = fields.Text()

    def _matches(self, impersonator, target):
        self.ensure_one()
        if not (impersonator.all_group_ids & self.impersonator_group_ids):
            return False
        if self.target_group_ids and not (target.all_group_ids & self.target_group_ids):
            return False
        if self.target_type == 'internal' and target.share or self.target_type == 'portal' and not target.share:
            return False
        if self.company_ids and not (target.company_ids & self.company_ids):
            return False
        return True

