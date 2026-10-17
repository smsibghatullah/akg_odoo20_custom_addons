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
