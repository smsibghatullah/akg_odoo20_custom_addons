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

    # `last_line.uom_id._compute_price(...)` (purchase supplier price lookup) and
    # `line.uom_id._compute_quantity(...)` crash with "Expected singleton: uom.uom()"
    # when a migrated line has no UoM. With no unit we assume the amount is already
    # in the target unit (the real fix is to fill the missing uom_id, see README).
    def _compute_price(self, price, to_unit):
        if not self:
            return price
        return super()._compute_price(price, to_unit)

    def _compute_quantity(self, qty, to_unit, *args, **kwargs):
        if not self:
            return qty
        return super()._compute_quantity(qty, to_unit, *args, **kwargs)
