# -*- coding: utf-8 -*-
import base64

from odoo import models, _
from odoo.tools import file_open

LANG_EN = 'en_US'
LANG_AR = 'ar_001'

_MIME_BY_PREFIX = (
    ('/9j/', 'image/jpeg'),
    ('iVBOR', 'image/png'),
    ('R0lGOD', 'image/gif'),
    ('UklGR', 'image/webp'),
    ('PHN2Zy', 'image/svg+xml'),
    ('PD94b', 'image/svg+xml'),
)


def _b64_to_data_uri(value):
    """base64 (bytes or str) -> data: URI. Own helper because
    odoo.tools.image_data_uri is not importable from odoo.tools in Odoo 20."""
    if not value:
        return False
    if isinstance(value, (bytes, bytearray)):
        value = bytes(value).decode('ascii')
    elif not isinstance(value, str):
        value = str(value)
    mime = next((m for prefix, m in _MIME_BY_PREFIX if value.startswith(prefix)), 'image/png')
    return 'data:%s;base64,%s' % (mime, value)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Helpers below only READ data and use getattr / _fields checks, so the
    # report keeps printing even if a field is renamed in a later version.
    # No fields are (re)defined here: `narration` must NOT be redefined on Odoo 20.

    def _akg_report_lang(self):
        self.ensure_one()
        return self.partner_id.lang or self.env.lang or LANG_EN

    def _akg_invoice_titles(self):
        """(english, arabic) document title."""
        self.ensure_one()
        mt, st = self.move_type, self.state
        if mt == 'out_invoice':
            if st == 'draft':
                return _("Draft Invoice"), 'مسودة فاتورة'
            if st == 'cancel':
                return _("Cancelled Invoice"), 'فاتورة ملغاة'
            return "Tax Invoice & Delivery Note", 'فاتورة ضريبية أمر تسليم'
        if mt == 'out_refund':
            return _("Credit Note"), 'إشعار دائن'
        if mt == 'in_refund':
            return _("Vendor Credit Note"), 'إشعار مدين'
        if mt == 'in_invoice':
            return _("Vendor Bill"), 'فاتورة المورد'
        return _("Receipt"), 'إيصال'

    @staticmethod
    def _akg_phone_of(partner):
        for fname in ('mobile', 'phone'):
            if partner and fname in partner._fields and partner[fname]:
                return partner[fname]
        return False

    def _akg_customer_phone(self):
        self.ensure_one()
        return self._akg_phone_of(self.partner_id)

    def _akg_salesperson_phone(self):
        self.ensure_one()
        user = self.invoice_user_id
        return self._akg_phone_of(user.partner_id) if user else False

    def _akg_customer_reference(self):
        """Field added by bi_pos_customer_ref (if installed)."""
        self.ensure_one()
        return getattr(self, 'customer_reference', False) or False

    def _akg_payment_lines(self):
        """[{'date': ..., 'amount': ...}] of reconciled payments."""
        self.ensure_one()
        widget = getattr(self.sudo(), 'invoice_payments_widget', False) or {}
        content = widget.get('content') if isinstance(widget, dict) else []
        return [
            {'date': vals.get('date'), 'amount': vals.get('amount')}
            for vals in (content or [])
        ]

    def _akg_tax_group_lines(self):
        """VAT summary computed from the tax lines (independent of the
        `tax_totals` structure, which changes between Odoo versions)."""
        self.ensure_one()
        totals = {}
        for line in self.line_ids.filtered('tax_line_id'):
            group = line.tax_line_id.tax_group_id
            totals[group] = totals.get(group, 0.0) + line.amount_currency
        result = []
        for group, amount in sorted(
                totals.items(),
                key=lambda kv: (getattr(kv[0], 'sequence', 0), kv[0].id or 0)):
            name_en = group.with_context(lang=LANG_EN).name
            name_ar = group.with_context(lang=LANG_AR).name
            result.append({
                'name': name_en,
                'name_ar': name_ar if name_ar != name_en else False,
                'amount': abs(amount),
            })
        return result

    def _akg_notes(self):
        """Translatable notes shown under the totals, as English/Arabic pairs."""
        self.ensure_one()

        def tr(rec, fname, lang):
            if rec and fname in rec._fields:
                return rec.with_context(lang=lang)[fname] or False
            return False

        def pair(rec, fname):
            en, ar = tr(rec, fname, LANG_EN), tr(rec, fname, LANG_AR)
            return {'en': en, 'ar': ar if ar != en else False}

        inco = self.invoice_incoterm_id if 'invoice_incoterm_id' in self._fields else False
        return {
            'term': pair(self.invoice_payment_term_id, 'note'),
            'narration': pair(self, 'narration'),
            'fiscal': pair(self.fiscal_position_id, 'note'),
            'incoterm_en': inco and "%s - %s" % (
                inco.code, inco.with_context(lang=LANG_EN).name) or False,
            'incoterm_ar': inco and "%s - %s" % (
                inco.code, inco.with_context(lang=LANG_AR).name) or False,
        }

    def _akg_logo_uri(self):
        """Company logo as data URI: no HTTP fetch needed by wkhtmltopdf."""
        self.ensure_one()
        try:
            return _b64_to_data_uri(self.company_id.logo)
        except Exception:
            return False

    def _akg_qr_uri(self):
        """QR image embedded as data URI (shipped with this module; falls back
        to the copy in bi_pos_customer_ref)."""
        self.ensure_one()
        for path in ('arabic_invoice_model/static/src/img/qr_code.png',
                     'bi_pos_customer_ref/static/src/img/qr_code.png'):
            try:
                with file_open(path, 'rb') as f:
                    return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
            except Exception:
                continue
        return False

    @staticmethod
    def _akg_first_value(records, fname):
        """First non-empty value of `fname` among records that have that field."""
        for rec in records:
            if rec and fname in rec._fields and rec[fname]:
                return rec[fname]
        return False

    def _akg_cr_no(self):
        """Commercial registration number (field location differs by version)."""
        self.ensure_one()
        company = self.company_id
        return (self._akg_first_value(
            (company, company.partner_id), 'company_registry') or '1/02236/9')

    def _akg_company_footer(self):
        self.ensure_one()
        return self._akg_first_value((self.company_id,), 'report_footer')

    def _akg_vat_label(self):
        self.ensure_one()
        country = self._akg_first_value((self.company_id,), 'account_fiscal_country_id')
        label = country and 'vat_label' in country._fields and country.vat_label
        return label or 'Tax ID'
