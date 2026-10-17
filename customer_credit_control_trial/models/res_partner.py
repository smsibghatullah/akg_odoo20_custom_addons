# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_amount_credit_limit = fields.Boolean("Amount Credit Limit")
    credit_limit_amount = fields.Float("Credit Limit (Amount)")
    amount_tolerance = fields.Float("Tolerance (%)")
    warning_amount = fields.Float("Warning at")
    is_days_credit_limit = fields.Boolean("Days Credit Limit")
    credit_limit_days = fields.Integer("Credit Limit (Days)")
    days_tolerance = fields.Integer("Tolerance (Days)")
    warning_days = fields.Integer("Warning day")
    total_due_amount = fields.Float("Total Due Amount", compute="_get_total_due_amount", store=False)
    is_enable_warning = fields.Boolean("Enable Warnings")

    @api.constrains("credit_limit_amount", "credit_limit_days", "amount_tolerance", "days_tolerance", "warning_amount",
                    "warning_days")
    def amount_days_non_negative_check(self):
        invalid_field = False
        if self.is_amount_credit_limit:
            if self.credit_limit_amount < 0:
                invalid_field = "Credit Limit (Amount)"
            if self.amount_tolerance < 0:
                invalid_field = "%s, Tolerance" % invalid_field
            if self.warning_amount < 0:
                invalid_field = "%s, Warning at" % invalid_field

        if self.is_days_credit_limit:
            if self.credit_limit_days < 0:
                invalid_field = "%s, Credit Limit (Days)" % invalid_field
            if self.days_tolerance < 0:
                invalid_field = "%s, Tolerance (Days)" % invalid_field
            if self.warning_days < 0:
                invalid_field = "%s, Warning day" % invalid_field

        if invalid_field:
            raise ValidationError(_("Value can not be Negative. Following field(s) has Negative Values : \n %s " % invalid_field))

    def _get_total_due_amount(self):
        invoice_obj = self.env["account.move"]
        for record in self:
            record.total_due_amount = 0
            invoice_ids = invoice_obj.search([
                ("partner_id", "=", record.id),
                ("amount_residual", ">", 0),
            ])
            record.total_due_amount = sum(invoice_ids.mapped('amount_residual'))
