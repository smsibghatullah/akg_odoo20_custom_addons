# -*- coding: utf-8 -*-
import logging
from collections import defaultdict

from odoo import models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_line_warehouse(self, line):
        """Warehouse used to deliver a line: line > refunded line > POS default."""
        config = self.config_id
        return (
            line.warehouse_id
            or line.refunded_orderline_id.warehouse_id
            or config.default_warehouse_id
            or config.picking_type_id.warehouse_id
        )

    def _create_order_picking(self):
        """One delivery order per warehouse (and per ship-later / immediate)."""
        self.ensure_one()
        if not self.config_id.enable_warehouse_delivery:
            return super()._create_order_picking()
        if self.picking_ids:
            return

        Picking = self.env['stock.picking']
        groups = defaultdict(lambda: self.env['pos.order.line'])
        for line in self.lines:
            warehouse = self._get_line_warehouse(line)
            if not warehouse:
                continue
            ship_later = bool(line.ship_later and line.qty > 0 and not self.is_refund)
            groups[(warehouse, ship_later)] |= line

        all_pickings = Picking
        for (warehouse, ship_later), lines in groups.items():
            picking_type = warehouse.pos_type_id or warehouse.out_type_id
            if not picking_type:
                _logger.warning('No operation type found for warehouse %s', warehouse.name)
                continue
            destination_id = (
                self.partner_id.property_stock_customer.id
                or picking_type.default_location_dest_id.id
            )
            if ship_later:
                pickings = self._create_ship_later_picking(picking_type, destination_id, lines)
            else:
                pickings = Picking._create_picking_from_pos_order_lines(
                    destination_id, lines, picking_type, self.partner_id)
            vals = {
                'pos_session_id': self.session_id.id,
                'pos_order_id': self.id,
                'origin': self.name,
            }
            pickings.write(vals)
            pickings.backorder_ids.write(vals)
            all_pickings |= pickings
        if self.is_refund:
            # Refund orders: the delivery (return) is ALWAYS done, whatever the
            # ship-later checkbox says.
            all_pickings |= self.picking_ids
            all_pickings._akgr_force_done()
        return all_pickings

    def _create_ship_later_picking(self, picking_type, destination_id, lines):
        """Delivery order left open (not done) with the chosen scheduled date."""
        Picking = self.env['stock.picking']
        stockable = lines.filtered(lambda l: l.product_id.type == 'consu' and l.qty > 0)
        if not stockable:
            return Picking
        picking = Picking.create(Picking._prepare_picking_vals(
            self.partner_id, picking_type,
            picking_type.default_location_src_id.id, destination_id))
        grouped = stockable.grouped(
            lambda l: (l.product_id.id, tuple(sorted(l.attribute_value_ids.ids))))
        move_vals = [
            picking._prepare_stock_move_vals(group_lines[0], group_lines)
            for group_lines in grouped.values()
        ]
        moves = self.env['stock.move'].create(move_vals)
        moves._action_confirm()
        moves._action_assign()
        dates = [d for d in stockable.mapped('ship_later_date') if d]
        if dates:
            picking.scheduled_date = min(dates)
        return picking
