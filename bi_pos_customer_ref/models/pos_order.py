# -*- coding: utf-8 -*-
import base64
from io import BytesIO

import qrcode

from odoo import _, api, fields, models

QR_LINK = "https://linktr.ee/akg_hardware"


def _akg_qr_png():
    """Return the base64 encoded PNG of the company QR code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=3,
        border=4,
    )
    qr.add_data(QR_LINK)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue())


class AccountMove(models.Model):
    _inherit = 'account.move'

    customer_reference = fields.Char(string='Customer Reference')
    qr_code = fields.Binary("QR Code", compute='_compute_qr_code_akg')

    # NOTE: the original method was called `_generate_qr_code`, which silently overrode the
    # core account.move._generate_qr_code(silent_errors) used by the invoice report.
    def _compute_qr_code_akg(self):
        png = _akg_qr_png()
        for move in self:
            move.qr_code = png

    def _l10n_gcc_get_invoice_title(self):
        """Official hook of l10n_gcc_invoice (Saudi/GCC bilingual invoice title)."""
        self.ensure_one()
        if self.move_type == 'out_invoice' and self.state == 'posted' and self.pos_order_ids:
            if (self.env.context.get('lang') or '').startswith('ar'):
                return 'فاتورة ضريبية أمر تسليم'
            return _("Tax Invoice & Delivery Note")
        return super()._l10n_gcc_get_invoice_title()


class PosOrder(models.Model):
    _inherit = 'pos.order'

    customer_reference = fields.Char(string='Customer Reference')

    # Odoo 20: `_order_fields` and `_create_invoice(move_vals)` no longer exist. The invoice
    # values are built in `_prepare_invoice_vals`, so the reference is simply added there
    # (this also removes the 70-line copy of the core cash-rounding logic of Odoo 16).
    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        reference = next((o.customer_reference for o in self if o.customer_reference), False)
        if reference:
            vals['customer_reference'] = reference
        return vals


class ResCountry(models.Model):
    _inherit = 'res.country'

    qr_code_akg = fields.Binary("QR Code", compute='_compute_qr_code_akg')

    def _compute_qr_code_akg(self):
        png = _akg_qr_png()
        for country in self:
            country.qr_code_akg = png


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    qr_code_akg = fields.Binary("QR Code", compute='_compute_qr_code_akg', store=True)

    @api.depends('company_id')
    def _compute_qr_code_akg(self):
        png = _akg_qr_png()
        for layout in self:
            layout.qr_code_akg = png


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Odoo 20 does not allow `groups` on inherited view records, so the unit price / discount
    # lock is driven by this per-user flag instead.
    can_edit_unit_price = fields.Boolean(compute='_compute_can_edit_unit_price')

    @api.depends_context('uid')
    def _compute_can_edit_unit_price(self):
        allowed = self.env.user.has_group('bi_pos_customer_ref.group_can_edit_unit_price')
        for order in self:
            order.can_edit_unit_price = allowed
