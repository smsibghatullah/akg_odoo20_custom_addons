# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_universal_credit_control = fields.Boolean("Enable Universal Credit Control", config_parameter="enable_universal_credit_control")
    force_universal_credit_control = fields.Boolean("Force Universal Credit Control", config_parameter="force_universal_credit_control")
    is_amount_credit_limit = fields.Boolean("Amount Credit Limit", config_parameter="cc_is_amount_credit_limit")
    credit_limit_amount = fields.Float("Credit Limit (Amount)", config_parameter="cc_credit_limit_amount")
    amount_tolerance = fields.Float("Tolerance (%)", config_parameter="cc_amount_tolerance")
    warning_amount = fields.Float("Warning at", config_parameter="cc_warning_amount")
    is_days_credit_limit = fields.Boolean("Days Credit Limit", config_parameter="cc_is_days_credit_limit")
    credit_limit_days = fields.Integer("Credit Limit (Days)", config_parameter="cc_credit_limit_days")
    days_tolerance = fields.Integer("Tolerance (Days)", config_parameter="cc_days_tolerance")
    warning_days = fields.Integer("Warning day", config_parameter="cc_warning_days")
    enable_warning = fields.Boolean("Enable Warning", config_parameter="cc_enable_warning")
    email_from = fields.Many2one("res.users", "Email From", config_parameter="cc_email_from", help="This user's email will be used to sent warning email.")

    @api.constrains("credit_limit_amount", "credit_limit_days",  "amount_tolerance", "days_tolerance", "warning_amount",
                    "warning_days")
    def amount_days_non_negative_check(self):
        invalid_field = False
        if self.enable_universal_credit_control:
            if self.is_amount_credit_limit:
                if self.credit_limit_amount < 0:
                    invalid_field = "Credit Limit (Amount)"
                if self.amount_tolerance < 0:
                    invalid_field = "%s, Tolerance" % invalid_field
            if self.is_days_credit_limit:
                if self.credit_limit_days < 0:
                    invalid_field = "%s, Credit Limit (Days)" % invalid_field
                if self.days_tolerance < 0:
                    invalid_field = "%s, Tolerance (Days)" % invalid_field
            if self.enable_warning:
                if self.warning_amount < 0:
                    invalid_field = "%s, Warning at" % invalid_field
                if self.warning_days < 0:
                    invalid_field = "%s, Warning day" % invalid_field
        if invalid_field:
            raise ValidationError(_("Value can not be Negative. Following field(s) has Negative Values : \n %s " % invalid_field))
