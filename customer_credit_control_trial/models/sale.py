# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        # 'is_ceo' is a custom field that may not exist on res.users
        is_ceo = getattr(self.env.user, 'is_ceo', False)
        if is_ceo:
            return super().action_confirm()
        if self.partner_id.is_amount_credit_limit:
            current_amount = self.amount_total + self.partner_id.total_due_amount
            if current_amount > self.partner_id.credit_limit_amount :
                raise ValidationError(
                    _("Customer Credit Limit Reached, You can not confirm sale orders of this customer unless previous "
                      "dues are cleared."))

        if self.partner_id.is_days_credit_limit or self.partner_id.is_enable_warning or self.partner_id.amount_tolerance:
            ctx = dict(self.env.context)
            wiz_name = "Trial App Warning!!"
            wiz_message = ("Days Credit Control and Enable Warnings are not part of this Trial App. Kindly Purchase "
                           "Main App 'Customer Credit Control' for access. Configuration are given here to just give "
                           "you the idea what we offer in main app. To continue confirming sale order, uncheck Days "
                           "Credit Control and Enable Warnings in partner form.")
            ctx.update({
                "default_name": wiz_name,
                "default_message": wiz_message
            })
            return {
                'name': _('Warning'),
                'view_mode': 'form',
                'res_model': 'warning.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx
            }
        return super().action_confirm()

    def create_warning_mail(self, email_from, partner_to, subject, email_body):
        warning_mail_obj = self.env["warning.mail"]
        email_values = {
            'mail_user': email_from.id,
            'partner_id': partner_to.id,
            'mail_subject': subject,
            'mail_body': email_body,
            'sale_order_id': self.id,
            'is_send_warning_mail': True,
            'is_warning_mail_sent': False
        }
        if partner_to.parent_id:
            email_values.update({
                "partner_ids": [(4, partner_to.parent_id.id)]
            })
        return warning_mail_obj.create(email_values)
