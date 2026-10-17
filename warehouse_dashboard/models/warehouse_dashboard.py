# -*- coding: utf-8 -*-
from odoo import models, api, fields
from datetime import datetime, time


class WarehouseDashboard(models.AbstractModel):
    _name = 'warehouse.dashboard'
    _description = 'Point of Sale Wise Inventory Dashboard'

    # Operation types shown as cards inside every Point of Sale column,
    # computed on the warehouse linked to that POS (via its operation type),
    # in the same order as Odoo's native Inventory overview.
    _OPERATIONS = [
        ('incoming', 'Receipts', 'fa-arrow-circle-down'),
        ('internal', 'Internal Transfers', 'fa-exchange'),
        ('outgoing', 'Delivery Orders', 'fa-truck'),
    ]

    def _get_picking_stats(self, warehouse, code):
        Picking = self.env['stock.picking'].sudo()
        base = [
            ('picking_type_id.warehouse_id', '=', warehouse.id),
            ('picking_type_id.code', '=', code),
        ]
        now = fields.Datetime.now()

        to_process = Picking.search_count(base + [('state', 'not in', ('done', 'cancel'))])
        waiting = Picking.search_count(base + [('state', 'in', ('confirmed', 'waiting'))])
        late = Picking.search_count(base + [
            ('state', 'not in', ('done', 'cancel')),
            ('scheduled_date', '<', now),
        ])
        backorders = Picking.search_count(base + [
            ('state', 'not in', ('done', 'cancel')),
            ('backorder_id', '!=', False),
        ])

        return {
            'to_process': to_process,
            'waiting': waiting,
            'late': late,
            'backorders': backorders,
        }

    @api.model
    def get_dashboard_data(self):
        if 'pos.config' not in self.env:
            return []

        Pos = self.env.get('pos.order')
        configs = self.env['pos.config'].sudo().search([])
        result = []

        for cfg in configs:
            warehouse = cfg.picking_type_id.warehouse_id

            operations = []
            if warehouse:
                for code, label, icon in self._OPERATIONS:
                    stats = self._get_picking_stats(warehouse, code)
                    operations.append({
                        'code': code,
                        'label': label,
                        'icon': icon,
                        **stats,
                    })

            pos_to_process = 0
            pos_today = 0
            if Pos is not None:
                PosSudo = Pos.sudo()
                # "Ready" POS orders = paid but not yet posted/invoiced,
                # i.e. still need to be processed further.
                pos_base = [
                    ('session_id.config_id', '=', cfg.id),
                    ('state', '=', 'paid'),
                ]
                pos_to_process = PosSudo.search_count(pos_base)

                today_start = fields.Datetime.to_string(
                    datetime.combine(fields.Date.context_today(self), time.min))
                pos_today = PosSudo.search_count(pos_base + [('date_order', '>=', today_start)])

            result.append({
                'pos_id': cfg.id,
                'pos_name': cfg.name,
                'warehouse_id': warehouse.id if warehouse else False,
                'warehouse_name': warehouse.name if warehouse else '',
                'operations': operations,
                'pos_to_process': pos_to_process,
                'pos_today': pos_today,
            })

        return result
