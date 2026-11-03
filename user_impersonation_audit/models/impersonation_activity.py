from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

OPERATIONS = [
    ('create', 'Created'),
    ('write', 'Changed'),
    ('unlink', 'Deleted'),
    ('message', 'Message'),
    ('action', 'Opened'),
]


class UserImpersonationActivity(models.Model):
    _name = 'user.impersonation.activity'
    _description = 'Impersonation Activity'
    _order = 'date desc, id desc'
    _rec_name = 'summary'

    session_id = fields.Many2one('user.impersonation.session', required=True, ondelete='cascade', index=True)
    impersonator_id = fields.Many2one(related='session_id.impersonator_id', store=True)
    target_id = fields.Many2one(related='session_id.target_id', store=True)
    company_id = fields.Many2one(related='session_id.company_id', store=True)
    date = fields.Datetime(required=True, default=fields.Datetime.now)
    operation = fields.Selection(OPERATIONS, required=True)
    model = fields.Char('Model', index=True)
    model_description = fields.Char('Document type')
    res_id = fields.Integer('Record ID')
    record_name = fields.Char('Record')
    summary = fields.Char()
    change_ids = fields.One2many('user.impersonation.change', 'activity_id', 'Field changes')
    change_count = fields.Integer('Fields', compute='_compute_change_count')
    operation_label = fields.Char(compute='_compute_change_count')

    def _compute_change_count(self):
        labels = dict(self._fields['operation']._description_selection(self.env))
        for rec in self:
            rec.change_count = len(rec.change_ids)
            rec.operation_label = labels.get(rec.operation, '')

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise AccessError(_('Impersonation records are written by the application only; they cannot be created, changed or deleted by hand.'))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            raise AccessError(_('Impersonation records are written by the application only; they cannot be created, changed or deleted by hand.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise AccessError(_('Impersonation records are written by the application only; they cannot be created, changed or deleted by hand.'))
        return super().unlink()

    def action_open_record(self):
        self.ensure_one()
        if not self.model or not self.res_id or self.model not in self.env or self.operation == 'unlink':
            raise UserError(_('There is no record to open.'))
        record = self.env[self.model].browse(self.res_id).exists()
        if not record:
            raise UserError(_('The record no longer exists.'))
        return {'type': 'ir.actions.act_window', 'res_model': self.model, 'res_id': self.res_id,
                'views': [(False, 'form')], 'target': 'current'}


class UserImpersonationChange(models.Model):
    _name = 'user.impersonation.change'
    _description = 'Impersonation Field Change'
    _order = 'id'
    _rec_name = 'field_description'

    activity_id = fields.Many2one('user.impersonation.activity', required=True, ondelete='cascade', index=True)
    session_id = fields.Many2one(related='activity_id.session_id', store=True)
    company_id = fields.Many2one(related='activity_id.company_id', store=True)
    field_name = fields.Char('Technical name')
    field_description = fields.Char('Field')
    old_value = fields.Text('Old value')
    new_value = fields.Text('New value')

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise AccessError(_('Impersonation records are written by the application only; they cannot be created, changed or deleted by hand.'))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            raise AccessError(_('Impersonation records are written by the application only; they cannot be created, changed or deleted by hand.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise AccessError(_('Impersonation records are written by the application only; they cannot be created, changed or deleted by hand.'))
        return super().unlink()
