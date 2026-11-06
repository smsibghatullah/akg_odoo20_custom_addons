# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    ship_later = fields.Boolean(string='Ship Later', default=False)
    ship_later_date = fields.Datetime(string='Ship Later Date')

    @api.model
    def _load_pos_data_fields(self, config):
        # The POS UI only sends/receives the fields listed here, so our
        # fields must be added for them to be saved with the order.
        fields_list = super()._load_pos_data_fields(config)
        for name in ('warehouse_id', 'ship_later', 'ship_later_date'):
            if name not in fields_list:
                fields_list.append(name)
        return fields_list

    @api.model
    def get_existing_lots(self, company_id, config_id, product_id,
                          warehouse_id=None, all_warehouses=False):
        """Lots with stock, filtered by warehouse.

        * ``warehouse_id``: lots with positive net stock in the internal
          locations of that warehouse.
        * ``all_warehouses`` (the "None" warehouse choice): lots with positive net
          stock in ANY internal location (all warehouses together).
        * neither: standard pos_stock behaviour.
        Same result shape as pos_stock.get_existing_lots.
        """
        warehouse = self.env['stock.warehouse'].browse(warehouse_id).exists() if warehouse_id else None
        if not warehouse and not all_warehouses:
            return super().get_existing_lots(company_id, config_id, product_id)

        self.check_access('read')
        domain = [
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id),
            ('product_id', '=', product_id),
            ('lot_id', '!=', False),
        ]
        if warehouse:
            locations = (
                warehouse.view_location_id.child_internal_location_ids
                | warehouse.lot_stock_id.child_internal_location_ids
            )
            domain.append(('location_id', 'in', locations.ids))
        else:
            domain.append(('location_id.usage', '=', 'internal'))

        groups = self.sudo().env['stock.quant']._read_group(
            domain=domain,
            groupby=['lot_id'],
            aggregates=['quantity:sum'],
        )
        has_expiration = 'expiration_date' in self.env['stock.lot']._fields
        result = []
        for lot, total_quantity in groups:
            # net stock must be positive (negative / empty lots are hidden)
            if lot and total_quantity > 0:
                result.append({
                    'id': lot.id,
                    'name': lot.name,
                    'product_qty': total_quantity,
                    'expiration_date': lot.expiration_date if has_expiration else False,
                })
        return result
