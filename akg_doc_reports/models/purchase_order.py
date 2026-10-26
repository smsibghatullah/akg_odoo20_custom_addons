# -*- coding: utf-8 -*-
from odoo import fields, models

from .common import chunk, first_field, tax_group_rows


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'akgr.report.mixin']

    def _akgr_is_rfq(self, force_rfq=False):
        self.ensure_one()
        return force_rfq or self.state in ('draft', 'sent', 'to approve')

    def _akgr_title(self, force_rfq=False):
        self.ensure_one()
        if self._akgr_is_rfq(force_rfq):
            return 'Request for Quotation #'
        return 'Purchase Order #'

    def _akgr_shipping_partner(self):
        self.ensure_one()
        partner = first_field(self, ['dest_address_id'])
        if not partner:
            picking_type = first_field(self, ['picking_type_id'])
            warehouse = picking_type and first_field(picking_type, ['warehouse_id'])
            partner = warehouse and warehouse.partner_id
        return partner or False

    def _akgr_info_rows(self, force_rfq=False):
        self.ensure_one()
        local = lambda dt: fields.Datetime.context_timestamp(self, dt).date() if dt else False
        items = []
        if self.user_id:
            items.append(('Purchase Representative', self.user_id.name, 'text'))
        if self._akgr_is_rfq(force_rfq):
            items.append(('Order Deadline', self.date_order, 'datetime'))
        else:
            items.append(('Order Date', local(first_field(self, ['date_approve']) or self.date_order), 'date'))
            items.append(('Expected Arrival', first_field(self, ['date_planned']), 'date'))
        if self.partner_ref:
            items.append(('Your Order Reference', self.partner_ref, 'text'))
        items = [i for i in items if i[1]]
        return chunk(items, 4)

    def _akgr_lines(self):
        self.ensure_one()
        rows = []
        for line in self.order_line.sorted(key=lambda l: (l.sequence, l.id)):
            dtype = line.display_type or False
            if dtype in ('line_section', 'line_note'):
                rows.append({'type': dtype, 'name': line.name})
                continue
            product = line.product_id
            uom = first_field(line, ['product_uom_id', 'product_uom'])
            taxes = first_field(line, ['tax_ids', 'taxes_id'])
            rows.append({
                'type': 'line',
                'name': line.name or (product and product.display_name) or '',
                'date_planned': first_field(line, ['date_planned']),
                'qty': first_field(line, ['product_qty'], 0.0),
                'uom': uom.name if uom else '',
                'price_unit': line.price_unit,
                'discount': first_field(line, ['discount'], 0.0),
                'taxes': ', '.join((t.description or t.name or '') for t in taxes) if taxes else '',
                'subtotal': line.price_subtotal,
            })
        return rows

    def _akgr_totals(self):
        self.ensure_one()
        entries = []
        for line in self.order_line.filtered(lambda l: not l.display_type):
            taxes = first_field(line, ['tax_ids', 'taxes_id'])
            qty = first_field(line, ['product_qty'], 0.0)
            entries.append((taxes, line.price_unit * (1 - (first_field(line, ['discount'], 0.0) or 0.0) / 100.0),
                            qty, line.product_id))
        try:
            rows = tax_group_rows(self.env, entries, self.currency_id, self.partner_id)
        except Exception:
            rows = []
        if not rows and self.amount_tax:
            rows = [{'name': 'Taxes', 'amount': self.amount_tax}]
        return {'untaxed': self.amount_untaxed, 'taxes': rows, 'total': self.amount_total,
                'show_untaxed': bool(rows)}

    def _akgr_notes(self):
        self.ensure_one()
        term = self.payment_term_id
        return {
            'payment': term.name if term else False,
            'notes': first_field(self, ['notes']) or False,
        }
