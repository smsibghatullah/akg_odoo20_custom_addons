# -*- coding: utf-8 -*-
from odoo import fields, models

from .common import barcode_svg_uri, chunk, first_field


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'akgr.report.mixin']

    def _akgr_barcode_uri(self):
        self.ensure_one()
        return barcode_svg_uri(self.name)

    def _akgr_note(self):
        self.ensure_one()
        return first_field(self, ['note']) or False

    def _akgr_code(self):
        self.ensure_one()
        return self.picking_type_id.code if self.picking_type_id else False

    def _akgr_warehouse_partner(self):
        self.ensure_one()
        warehouse = self.picking_type_id.warehouse_id if self.picking_type_id else False
        return (warehouse and warehouse.partner_id) or self.company_id.partner_id

    def _akgr_partner_label(self):
        self.ensure_one()
        code = self._akgr_code()
        if code == 'incoming':
            return 'Vendor Address:'
        if code == 'outgoing':
            return 'Customer Address:'
        return 'Partner Address:'

    def _akgr_state_label(self):
        self.ensure_one()
        sel = dict(self._fields['state']._description_selection(self.env))
        return sel.get(self.state, self.state)

    def _akgr_info_rows(self):
        self.ensure_one()
        items = [
            ('Order', self.origin, 'text'),
            ('Status', self._akgr_state_label(), 'text'),
            ('Scheduled Date', self.scheduled_date, 'datetime'),
        ]
        date_done = first_field(self, ['date_done'])
        if self.state == 'done' and date_done:
            items.append(('Date Done', date_done, 'datetime'))
        return chunk([i for i in items if i[1]], 4)

    def _akgr_lines(self):
        self.ensure_one()
        moves = first_field(self, ['move_ids', 'move_ids_without_package']) or self.env['stock.move']
        rows = []
        for move in moves.sorted(key=lambda m: (m.sequence, m.id)):
            product = move.product_id
            name = product.display_name or move.name or ''
            extra = first_field(move, ['description_picking'])
            if extra and extra not in name:
                name = '%s\n%s' % (name, extra)
            demand = first_field(move, ['product_uom_qty'], 0.0)
            done = first_field(move, ['quantity', 'quantity_done'], 0.0)
            qty = (done or demand) if self.state == 'done' else (demand or done)
            uom = first_field(move, ['product_uom_id', 'product_uom'])
            lots = []
            if 'move_line_ids' in move._fields and 'lot_id' in self.env['stock.move.line']._fields:
                lots = [l for l in move.move_line_ids.mapped('lot_id.name') if l]
            rows.append({
                'name': name,
                'qty': qty,
                'uom': uom.name if uom else '',
                'from': move.location_id.display_name,
                'to': move.location_dest_id.display_name,
                'lots': ', '.join(lots),
            })
        return rows
