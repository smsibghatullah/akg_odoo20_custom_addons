# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_warehouse_delivery = fields.Boolean(
        string='Enable Warehouse-wise Delivery Orders',
        default=True,
    )
    default_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Default Warehouse',
        help='Default warehouse to pre-select on POS order lines.',
    )
    allow_ship_later = fields.Boolean(
        string='Allow Ship Later',
        default=False,
        help='Show a scheduled delivery date field on POS orderlines. '
             'The delivery order stays open with the chosen date as scheduled date.',
    )

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        # Make sure our config fields reach the POS UI even if the core
        # config field list is explicit (empty list = all fields).
        fields_list = super()._load_pos_data_fields(*args, **kwargs)
        if fields_list:
            for name in ('enable_warehouse_delivery', 'default_warehouse_id',
                         'allow_ship_later'):
                if name not in fields_list:
                    fields_list.append(name)
        return fields_list


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, *args, **kwargs):
        models_to_load = super()._load_pos_data_models(*args, **kwargs)
        # Warehouses are needed by the POS UI (orderline dropdown) and as
        # relation target of pos.order.line.warehouse_id / pos.config.default_warehouse_id
        if 'stock.warehouse' not in models_to_load:
            models_to_load.append('stock.warehouse')
        return models_to_load
