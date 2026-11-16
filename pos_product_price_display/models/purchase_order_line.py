from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _get_stock_move_price_unit(self, at_date=False):
        """Standard code divides by self.uom_id.factor, which is 0 for migrated lines whose unit has a
        broken factor (or no unit): receiving / creating a backorder then fails with ZeroDivisionError.
        In that case the line is treated as being in the product's own unit (no conversion)."""
        self.ensure_one()
        if not self.uom_id.factor or not self.product_id.uom_id.factor:
            if not at_date:
                at_date = fields.Date.today()
            order = self.order_id
            price_unit = self.price_unit_discounted
            if self.tax_ids:
                qty = self.product_qty or 1
                price_unit = self.tax_ids.compute_all(
                    price_unit,
                    currency=order.currency_id,
                    quantity=qty,
                    product=self.product_id,
                    partner=order.partner_id,
                    rounding_method="round_globally",
                )["total_void"]
                price_unit = price_unit / qty
            if order.currency_id != order.company_id.currency_id:
                price_unit = order.currency_id._convert(
                    price_unit, order.company_id.currency_id, self.company_id, at_date, round=False)
            return price_unit
        return super()._get_stock_move_price_unit(at_date=at_date)
