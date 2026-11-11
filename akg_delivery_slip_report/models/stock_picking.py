# -*- coding: utf-8 -*-
from odoo import models

from odoo.addons.akg_doc_reports.models.common import first_field, phone_of, uom_of


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _akgd_vat_label(self):
        """'VAT' / 'Tax ID' label of the company's country (default VAT)."""
        self.ensure_one()
        company = self.company_id
        label = False
        for rec in (getattr(company, 'account_fiscal_country_id', False), company.country_id):
            label = label or (rec and getattr(rec, 'vat_label', False))
        return label or 'VAT'

    def _akgd_moves(self):
        self.ensure_one()
        moves = first_field(self, ['move_ids', 'move_ids_without_package']) or self.env['stock.move']
        return moves.sorted(key=lambda m: (m.sequence, m.id))

    def _akgd_customer(self):
        """Customer (sale order partner when there is one, else the picking partner)."""
        self.ensure_one()
        sale = first_field(self, ['sale_id'])
        return (sale and sale.partner_id) or self.partner_id

    def _akgd_warehouse_partner(self):
        """Address of the warehouse the goods leave from (shown instead of the delivery address).

        Order: operation type warehouse -> source location warehouse -> company partner.
        """
        self.ensure_one()
        warehouse = self.picking_type_id.warehouse_id
        if not warehouse:
            warehouse = first_field(self.location_id, ['warehouse_id'])
        partner = warehouse.partner_id if warehouse else False
        return partner or self.company_id.partner_id

    # kept so old templates calling the previous name do not break
    def _akgd_delivery_partner(self):
        return self._akgd_warehouse_partner()

    def _akgd_phone(self, partner):
        return phone_of(partner)

    def _akgd_info_rows(self):
        self.ensure_one()
        date_done = first_field(self, ['date_done'])
        shipping = date_done if (self.state == 'done' and date_done) else self.scheduled_date
        items = [
            ('Order', self.origin, 'text'),
            ('Shipping Date', shipping, 'datetime'),
        ]
        items = [i for i in items if i[1]]
        return [items] if items else []

    def _akgd_lines(self):
        self.ensure_one()
        rows = []
        for move in self._akgd_moves():
            product = move.product_id
            name = product.display_name or move.name or ''
            extra = first_field(move, ['description_picking'])
            if extra and extra not in name:
                name = '%s\n%s' % (name, extra)
            uom = uom_of(move, product.uom_id)
            lots = []
            if 'move_line_ids' in move._fields and 'lot_id' in self.env['stock.move.line']._fields:
                lots = [l for l in move.move_line_ids.mapped('lot_id.name') if l]
            rows.append({
                'name': name,
                'ordered': first_field(move, ['product_uom_qty'], 0.0),
                'delivered': first_field(move, ['quantity', 'quantity_done'], 0.0),
                'uom': uom.name if uom else '',
                'lots': ', '.join(lots),
            })
        return rows
