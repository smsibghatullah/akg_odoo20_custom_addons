from odoo import models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def check_partner_credit_limit(self, partner_id, new_order_amount, is_non_cash_payment):
        partner = self.browse(partner_id)
        if partner.is_amount_credit_limit and is_non_cash_payment:
            current_due = partner.total_due_amount
            total = current_due + new_order_amount
            if total > partner.credit_limit_amount:
                return {'allowed': False}
        return {'allowed': True}


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        fields = result.get('fields', [])
        if 'is_amount_credit_limit' not in fields:
            fields.append('is_amount_credit_limit')
        result['fields'] = fields
        return result
