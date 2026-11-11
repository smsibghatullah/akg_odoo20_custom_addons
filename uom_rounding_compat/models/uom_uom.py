# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_compare, float_is_zero, float_round


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

    # ------------------------------------------------------------------
    # Empty-UoM safety net.
    # Migrated purchase/sale lines can have no UoM; standard code then calls
    # `line.uom_id.compare(...)` on an EMPTY recordset and crashes with
    # "Expected singleton: uom.uom()" (e.g. when opening bills / refunds).
    # For an empty recordset we fall back to the "Product Unit" precision.
    # ------------------------------------------------------------------
    def _compat_digits(self):
        return self.env['decimal.precision'].precision_get('Product Unit')

    def compare(self, value1, value2, *args, **kwargs):
        if not self:
            return float_compare(value1, value2, precision_digits=self._compat_digits())
        return super().compare(value1, value2, *args, **kwargs)

    def is_zero(self, value, *args, **kwargs):
        if not self:
            return float_is_zero(value, precision_digits=self._compat_digits())
        return super().is_zero(value, *args, **kwargs)

    def round(self, value, rounding_method='HALF-UP', *args, **kwargs):
        if not self:
            return float_round(value, precision_digits=self._compat_digits(),
                               rounding_method=rounding_method)
        return super().round(value, rounding_method, *args, **kwargs)
