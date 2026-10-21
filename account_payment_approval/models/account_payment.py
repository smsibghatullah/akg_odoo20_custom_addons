# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import  UserError


class AccountPayment(models.Model):
    """This class inherits model "account.payment" and adds required fields """
    _inherit = "account.payment"


    state = fields.Selection(selection_add=[
        ('waiting_approval', 'Waiting For Approval'),
        ('approved', 'Approved'),
    ],ondelete={'waiting_approval': 'set default','approved': 'set default'}, tracking=True)

    @api.model
    def _approval_get_param(self, key, default=False):
        """Read a system parameter in a way that works on every Odoo
        version. Newer Odoo 20 builds removed ``get_param`` from
        ``ir.config_parameter``, so fall back to other accessors and finally
        to a direct search on the model."""
        icp = self.env['ir.config_parameter'].sudo()
        for name in ('get_param', '_get_param'):
            getter = getattr(icp, name, None)
            if getter:
                try:
                    value = getter(key, default)
                except TypeError:
                    value = getter(key)
                return default if value is None else value
        param = icp.search([('key', '=', key)], limit=1)
        return param.value if param and param.value not in (None, '') \
            else default

    @api.model
    def _approval_get_int(self, key):
        """Return the parameter as int (0 when empty or invalid)."""
        try:
            return int(self._approval_get_param(key) or 0)
        except (TypeError, ValueError):
            return 0

    @api.model
    def _approval_get_float(self, key):
        """Return the parameter as float (0.0 when empty or invalid)."""
        try:
            return float(self._approval_get_param(key) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @api.model
    def _approval_enabled(self):
        """True when the 'Payment Approval' setting is switched on."""
        value = self._approval_get_param(
            'account_payment_approval.payment_approval')
        return str(value).strip().lower() not in ('', 'false', '0', 'none')

    def _compute_is_approve_person(self):
        """Set is_approve_person to True when the current user is the
        configured approving person and payment approval is enabled."""
        approval = self._approval_enabled()
        approver_id = self._approval_get_int(
            'account_payment_approval.approval_user_id')
        for payment in self:
            payment.is_approve_person = bool(
                approval and approver_id and self.env.user.id == approver_id)

    is_approve_person = fields.Boolean(string='Approving Person',
                                       compute=_compute_is_approve_person,
                                       help="Enable/disable if approving"
                                            " person.")

    def _is_pos_payment(self):
        """POS session payments are created and posted automatically while
        closing a session, so they must never wait for approval."""
        self.ensure_one()
        for fname in ('pos_session_id', 'pos_payment_method_id', 'pos_order_id'):
            if fname in self._fields and self[fname]:
                return True
        return bool(self.env.context.get('skip_payment_approval'))

    def action_post(self):
        """Allow posting payments after approval in Odoo."""
        payments = self
        for payment in payments:
            if payment.state == 'waiting_approval':
                raise UserError(_("Only a draft or approved payment can be posted."))
        payments_to_check = payments.filtered(
            lambda p: p.state == 'draft' and not p._is_pos_payment())
        for payment in payments_to_check:
            if not payment._check_payment_approval():
                return
        approved_payments = payments.filtered(lambda p: p.state == 'approved')
        if approved_payments:
            approved_payments.state = 'in_process'
        return super().action_post()

    def _check_payment_approval(self):
        """This function checks the payment approval if payment_amount grater
         than amount,then state changed to waiting_approval """
        self.ensure_one()
        if self.state == "draft" and not self._is_pos_payment():
            first_approval = self._approval_enabled()
            if first_approval:
                amount = self._approval_get_float(
                    'account_payment_approval.approval_amount')
                payment_currency_id = self._approval_get_int(
                    'account_payment_approval.approval_currency_id')
                payment_amount = self.amount
                if payment_currency_id:
                    if (self.currency_id and
                            self.currency_id.id != payment_currency_id):
                        currency_id = self.env['res.currency'].browse(
                            payment_currency_id)
                        payment_amount = self.currency_id._convert(
                            self.amount,
                            currency_id,
                            self.company_id,
                            self.date or fields.Date.today(),
                            round=True,
                        )
                if payment_amount > amount:
                    self.write({
                        'state': 'waiting_approval'
                    })
                    return False
        return True

    def approve_transfer(self):
        """This function changes state to approved state if approving person
         approves payment"""
        if self.is_approve_person:
            self.write({
                'state': 'approved'
            })

    def reject_transfer(self):
        """This function changes state to rejected state if approving person
                reject approval"""
        self.write({
            'state': 'rejected'
        })
