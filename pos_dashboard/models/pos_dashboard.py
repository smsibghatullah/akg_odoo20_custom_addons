# -*- coding: utf-8 -*-
from odoo import models, api, fields
from collections import defaultdict


class PosDashboard(models.AbstractModel):
    _name = 'pos.dashboard'
    _description = 'Point of Sale Wise Inventory Dashboard'

    def _empty_stats(self):
        return {'to_process': 0, 'waiting': 0, 'late': 0, 'backorders': 0}

    def _accumulate(self, bucket, rec, now):
        # rec is already guaranteed "not done/cancel" by the search domain
        bucket['to_process'] += 1
        if rec['state'] in ('confirmed', 'waiting'):
            bucket['waiting'] += 1
        if rec['scheduled_date'] and rec['scheduled_date'] < now:
            bucket['late'] += 1
        if rec['backorder_id']:
            bucket['backorders'] += 1

    def _merge(self, cfg_ids, buckets):
        merged = self._empty_stats()
        for c in cfg_ids:
            b = buckets.get(c)
            if b:
                for k in merged:
                    merged[k] += b[k]
        return merged

    @api.model
    def get_dashboard_data(self):
        PosConfig = self.env['pos.config'].sudo()
        now = fields.Datetime.now()

        # The REAL, currently active POS list - only these become columns.
        active_configs = PosConfig.search([])
        active_names = {}
        for c in active_configs:
            active_names.setdefault((c.name or '').strip(), c.id)

        if not active_names:
            return []

        # ALL pos.config records (including archived/duplicate ones with
        # the same name), so historical Delivery Orders under an old
        # duplicate config still count under the correct active column.
        all_configs = PosConfig.with_context(active_test=False).search([])
        name_to_all_ids = defaultdict(list)
        for c in all_configs:
            name_to_all_ids[(c.name or '').strip()].append(c.id)

        # Each POS's default warehouse, via its operation type
        # (pos.config.picking_type_id.warehouse_id) - used ONLY for
        # Internal Transfers.
        name_to_warehouse_ids = defaultdict(set)
        for c in all_configs:
            name = (c.name or '').strip()
            if c.picking_type_id and c.picking_type_id.warehouse_id:
                name_to_warehouse_ids[name].add(c.picking_type_id.warehouse_id.id)

        # ============================================================
        # DELIVERY ORDERS - unchanged: matched via pos_order_id chain
        # ============================================================
        Picking = self.env['stock.picking'].sudo()
        deliveries = Picking.search_read(
            domain=[
                ('picking_type_id.code', '=', 'outgoing'),
                ('state', 'not in', ('done', 'cancel')),
                ('pos_order_id', '!=', False),
            ],
            fields=['state', 'scheduled_date', 'backorder_id', 'pos_order_id'],
        )

        order_ids = list({r['pos_order_id'][0] for r in deliveries})
        order_session_map = {}
        if order_ids:
            for o in self.env['pos.order'].sudo().browse(order_ids).read(['session_id']):
                if o['session_id']:
                    order_session_map[o['id']] = o['session_id'][0]

        session_ids = list(set(order_session_map.values()))
        session_config_map = {}
        if session_ids:
            for s in self.env['pos.session'].sudo().browse(session_ids).read(['config_id']):
                if s['config_id']:
                    session_config_map[s['id']] = s['config_id'][0]

        order_config_map = {}
        for order_id, session_id in order_session_map.items():
            cfg_id = session_config_map.get(session_id)
            if cfg_id:
                order_config_map[order_id] = cfg_id

        delivery_buckets = {}
        for d in deliveries:
            cfg_id = order_config_map.get(d['pos_order_id'][0])
            if not cfg_id:
                continue
            bucket = delivery_buckets.setdefault(cfg_id, self._empty_stats())
            self._accumulate(bucket, d, now)

        # ============================================================
        # INTERNAL TRANSFERS - matched via each POS's default warehouse
        # ============================================================
        all_warehouse_ids = list({wh for whs in name_to_warehouse_ids.values() for wh in whs})

        internal_buckets_by_wh = {}
        if all_warehouse_ids:
            internals = Picking.search_read(
                domain=[
                    ('picking_type_id.code', '=', 'internal'),
                    ('state', 'not in', ('done', 'cancel')),
                    ('picking_type_id.warehouse_id', 'in', all_warehouse_ids),
                ],
                fields=['state', 'scheduled_date', 'backorder_id', 'picking_type_id'],
            )
            # Resolve picking_type_id -> warehouse_id in bulk
            type_ids = list({r['picking_type_id'][0] for r in internals if r['picking_type_id']})
            type_warehouse_map = {}
            if type_ids:
                for t in self.env['stock.picking.type'].sudo().browse(type_ids).read(['warehouse_id']):
                    if t['warehouse_id']:
                        type_warehouse_map[t['id']] = t['warehouse_id'][0]

            for rec in internals:
                if not rec['picking_type_id']:
                    continue
                wh_id = type_warehouse_map.get(rec['picking_type_id'][0])
                if not wh_id:
                    continue
                bucket = internal_buckets_by_wh.setdefault(wh_id, self._empty_stats())
                self._accumulate(bucket, rec, now)

        # ============================================================
        # BUILD RESULT: one column per active POS name
        # ============================================================
        result = []
        for name in sorted(active_names.keys()):
            cfg_ids = name_to_all_ids.get(name, [active_names[name]])
            delivery_stats = self._merge(cfg_ids, delivery_buckets)

            wh_ids = name_to_warehouse_ids.get(name, set())
            internal_stats = self._empty_stats()
            for wh_id in wh_ids:
                b = internal_buckets_by_wh.get(wh_id)
                if b:
                    for k in internal_stats:
                        internal_stats[k] += b[k]

            operations = [
                {'code': 'outgoing', 'label': 'Deliveries', 'icon': 'fa-truck', **delivery_stats},
                {'code': 'internal', 'label': 'Transfers', 'icon': 'fa-exchange', **internal_stats},
            ]

            result.append({
                'pos_name': name,
                'config_ids': cfg_ids,
                'warehouse_ids': list(wh_ids),
                'operations': operations,
            })

        return result
