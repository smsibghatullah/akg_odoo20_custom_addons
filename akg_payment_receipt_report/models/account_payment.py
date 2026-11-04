# -*- coding: utf-8 -*-
from odoo import models

from odoo.addons.akg_doc_reports.models.common import first_field

# Decimals shown for amounts on the receipt (the existing AKG receipt shows 4, e.g. 538.3350 OMR).
AKGP_DIGITS = 4
AKGP_DATE_FORMAT = '%d/%m/%Y'


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ------------------------------------------------------------------ helpers
    def _akgp_date(self, value):
        return value.strftime(AKGP_DATE_FORMAT) if value else ''

    def _akgp_money(self, amount, currency=None):
        self.ensure_one()
        currency = currency or self.currency_id or self.company_id.currency_id
        amount = amount or 0.0
        if abs(amount) < 0.5 * 10 ** -AKGP_DIGITS:
            amount = 0.0
        return '%s %s' % (format(amount, ',.%df' % AKGP_DIGITS), currency.name or '')

    def _akgp_memo(self):
        self.ensure_one()
        return first_field(self, ['memo', 'ref']) or ''

    def _akgp_title(self):
        """Payment Receipt / Refund Confirmation / Payment Confirmation."""
        self.ensure_one()
        customer = self.partner_type == 'customer'
        if self.payment_type == 'inbound':
            return 'Payment Receipt' if customer else 'Refund Receipt'
        return 'Refund Confirmation' if customer else 'Payment Confirmation'

    def _akgp_partner_label(self):
        self.ensure_one()
        return 'Customer' if self.partner_type == 'customer' else 'Vendor'

    # ------------------------------------------------------------------ info block
    def _akgp_info_rows(self):
        self.ensure_one()
        method = first_field(self, ['payment_method_line_id', 'payment_method_id'])
        left = [
            ('Payment Date', self._akgp_date(self.date), 'text'),
            ('%s' % self._akgp_partner_label(), self.partner_id.name or '', 'text'),
            ('Payment Amount', self._akgp_money(self.amount), 'text'),
        ]
        right = [
            ('Payment Method', (method.name if method else '') or '', 'text'),
            ('Memo', self._akgp_memo(), 'text'),
        ]
        left = [i for i in left if i[1]]
        right = [i for i in right if i[1]]
        rows = []
        for idx in range(max(len(left), len(right))):
            row = []
            if idx < len(left):
                row.append(left[idx])
            if idx < len(right):
                row.append(right[idx])
            rows.append(row)
        return rows

    # ------------------------------------------------------------------ table
    def _akgp_reconciled(self):
        """[(invoice move, amount in payment currency)] of the invoices this payment settled."""
        self.ensure_one()
        result = []
        if not self.move_id:
            return result
        pay_lines = self.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
        found = []
        for partial in pay_lines.matched_debit_ids:       # payment line is the credit side
            found.append((partial, partial.debit_move_id, partial.credit_amount_currency))
        for partial in pay_lines.matched_credit_ids:      # payment line is the debit side
            found.append((partial, partial.credit_move_id, partial.debit_amount_currency))
        for partial, counterpart, amount in sorted(found, key=lambda f: f[0].id):
            move = counterpart.move_id
            if move == self.move_id or not move.is_invoice(include_receipts=True):
                continue
            result.append((move, amount))
        return result

    def _akgp_lines(self):
        """Rows of the table: invoice / payment / due amount (same pattern as the standard receipt)."""
        self.ensure_one()
        pay_cur = self.currency_id or self.company_id.currency_id
        memo = self._akgp_memo()
        rows = []
        reconciled = self._akgp_reconciled()
        for move, amount in reconciled:
            rows.append({
                'kind': 'invoice',
                'date': self._akgp_date(move.invoice_date or move.date),
                'number': move.name or '',
                'reference': move.ref or move.payment_reference or '',
                'amount': self._akgp_money(move.amount_total, move.currency_id),
            })
            rows.append({
                'kind': 'payment',
                'date': self._akgp_date(self.date),
                'number': self.name or '',
                'reference': memo,
                'amount': self._akgp_money(-amount, pay_cur),
            })
            rows.append({
                'kind': 'due',
                'date': '',
                'number': 'Due Amount for %s' % (move.name or ''),
                'reference': '',
                'amount': self._akgp_money(move.amount_residual, move.currency_id),
            })
        if not reconciled:
            # e.g. POS refunds / advance payments: no invoice reconciled, still show the payment itself
            rows.append({
                'kind': 'payment',
                'date': self._akgp_date(self.date),
                'number': self.name or '',
                'reference': memo,
                'amount': self._akgp_money(self.amount, pay_cur),
            })
        return rows
