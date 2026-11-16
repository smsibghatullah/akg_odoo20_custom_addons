from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_landed_cost(self):
        """Paying in the POS (or any stock operation done by a user without Inventory rights) reads the
        landed cost lines of the moves to value them. The cashier is not allowed to read those records:
            AccessError: You are not allowed to access 'Valuation Adjustment Line'
            (stock.valuation.adjustment.lines) records - allowed for: Inventory / Administrator.
        Landed costs are only used to value the move, so they are read with sudo (nothing is exposed).
        """
        return super(StockMove, self.sudo())._get_landed_cost()
