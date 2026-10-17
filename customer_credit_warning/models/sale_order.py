# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    accumulated_debit = fields.Float(
        string='Due Payments',
        required=False, compute='_compute_accumulated_due', store=True)

    def _get_higher_parent(self, partner):
        if not partner.parent_id:
            return []
        else:
            return [partner.parent_id] + self._get_higher_parent(partner.parent_id)

    @api.depends('partner_id')
    def _compute_accumulated_due(self):
        for order in self:
            accumulated = 0
            if order.partner_id:
                partners = [order.partner_id] + order._get_higher_parent(order.partner_id)
                partner = partners[-1]
                account_id = partner.property_account_receivable_id
                if account_id:
                    journal_items = self.env['account.move.line'].sudo().search([('partner_id', '=', partner.id), ('account_id', '=',account_id.id), ('parent_state', '=', 'posted')])
                    debit_sum = sum(journal_items.mapped('debit'))
                    credit_sum = sum(journal_items.mapped('credit'))
                    accumulated += debit_sum
                    accumulated -= credit_sum

            order.accumulated_debit = accumulated


