# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UomUom(models.Model):
    _inherit = 'uom.uom'

    rounding = fields.Float(
        string='Rounding Precision (compat)',
        compute='_compute_rounding_compat',
        digits=0,
        help='Compatibility only: derived from the "Product Unit" decimal precision.',
    )

    @api.depends_context('company')
    def _compute_rounding_compat(self):
        digits = self.env['decimal.precision'].precision_get('Product Unit')
        value = 10 ** -digits
        for uom in self:
            uom.rounding = value
