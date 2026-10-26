# -*- coding: utf-8 -*-
from odoo import fields, models

from .common import chunk, first_field, phone_of, tax_group_rows


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'akgr.report.mixin']

    def _akgr_title(self):
        self.ensure_one()
        if self.state in ('draft', 'sent'):
            return 'Quotation #'
        if self.state == 'cancel':
            return 'Cancelled Order #'
        return 'Order #'

    def _akgr_info_rows(self):
        self.ensure_one()
        local = lambda dt: fields.Datetime.context_timestamp(self, dt).date() if dt else False
        items = []
        if self.state in ('draft', 'sent'):
            items.append(('Quotation Date', local(self.date_order), 'date'))
            validity = first_field(self, ['validity_date'])
            if validity:
                items.append(('Expiration', validity, 'date'))
        else:
            items.append(('Order Date', local(self.date_order), 'date'))
        if self.user_id:
            items.append(('Salesperson', self.user_id.name, 'text'))
            items.append(('Mobile Number', phone_of(self.user_id.partner_id), 'text'))
        if self.client_order_ref:
            items.append(('Your Reference', self.client_order_ref, 'text'))
        # Rental app (optional)
        start = first_field(self, ['rental_start_date'])
        end = first_field(self, ['rental_return_date'])
        if start:
            items.append(('Pick-up', start, 'datetime'))
        if end:
            items.append(('Return', end, 'datetime'))
        if start or end:
            items.append(('Phone Number', phone_of(self.partner_id), 'text'))
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
            taxes = first_field(line, ['tax_ids', 'tax_id'])
            rows.append({
                'type': 'line',
                'name': line.name or (product and product.display_name) or '',
                'qty': first_field(line, ['product_uom_qty'], 0.0),
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
            taxes = first_field(line, ['tax_ids', 'tax_id'])
            qty = first_field(line, ['product_uom_qty'], 0.0)
            entries.append((taxes, line.price_unit * (1 - (first_field(line, ['discount'], 0.0) or 0.0) / 100.0),
                            qty, line.product_id))
        try:
            rows = tax_group_rows(self.env, entries, self.currency_id, self.partner_id)
        except Exception:
            rows = []
        if not rows and self.amount_tax:
            rows = [{'name': 'Taxes', 'amount': self.amount_tax}]
        return {'untaxed': self.amount_untaxed, 'taxes': rows, 'total': self.amount_total}

    def _akgr_notes(self):
        self.ensure_one()
        term = self.payment_term_id
        payment = False
        if term:
            payment = (term.note if 'note' in term._fields and term.note else
                       'Payment terms: %s' % term.name)
        return {'note': first_field(self, ['note']) or False, 'payment': payment}
