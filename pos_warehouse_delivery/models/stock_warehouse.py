# -*- coding: utf-8 -*-
from odoo import api, models


class StockWarehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = ['stock.warehouse', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config=None):
        """Warehouses of the POS company.

        Tolerant to the different signatures / data shapes used by the
        pos.load.mixin across versions: (data) or (data, config), and
        data['pos.config'] being a recordset or {'data': [...]}.
        """
        company_id = False
        try:
            if config is not None and hasattr(config, 'company_id'):
                company_id = config.company_id.id
            else:
                cfg = data.get('pos.config') if hasattr(data, 'get') else None
                if isinstance(cfg, dict):
                    company_id = cfg['data'][0]['company_id']
                    if isinstance(company_id, (list, tuple)):
                        company_id = company_id[0]
                elif cfg:
                    company_id = cfg.company_id.id
        except (KeyError, IndexError, AttributeError, TypeError):
            company_id = False
        # No company found -> let the record rules restrict the result
        return [('company_id', '=', company_id)] if company_id else []

    @api.model
    def _load_pos_data_fields(self, config=None):
        return ['id', 'name', 'code']
