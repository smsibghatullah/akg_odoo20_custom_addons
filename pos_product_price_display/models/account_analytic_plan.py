from odoo import api, models


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    @api.model
    def _akg_sync_plan_columns(self):
        """Recreate the dynamic analytic columns / fields x_plan<ID>_id.

        Every analytic plan owns a stored field x_plan<ID>_id on account.analytic.line (created by Odoo when
        the plan is created). Plans copied by the migration have no such field, so posting a bill / invoice
        with an analytic account of that plan fails with:
            ValueError: Invalid field 'x_plan5_id' in 'account.analytic.line'
        Odoo's own sync creates every missing field and column, and does nothing when they all exist.
        """
        plans = self.sudo().with_context(active_test=False).search([])
        if plans:
            plans._sync_all_plan_column()
        return True
