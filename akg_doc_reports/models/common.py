# -*- coding: utf-8 -*-
import re

from odoo import models

LANG_EN = 'en_US'
LANG_AR = 'ar_001'


def first_field(rec, names, default=False):
    """Value of the first field of `names` that exists on `rec`.
    Field names differ between Odoo versions (tax_id/tax_ids, product_uom/product_uom_id ...)."""
    for name in names:
        if name in rec._fields:
            return rec[name]
    return default


def phone_of(partner):
    for fname in ('mobile', 'phone'):
        if partner and fname in partner._fields and partner[fname]:
            return partner[fname]
    return False


def tax_group_rows(env, entries, currency, partner):
    """Tax summary grouped by tax group.

    entries: iterable of (taxes, unit_price_after_discount, quantity, product).
    Uses account.tax.compute_all, so it does not depend on the (version
    specific) structure of `tax_totals`.
    """
    totals = {}
    for taxes, price, qty, product in entries:
        if not taxes:
            continue
        res = taxes.compute_all(
            price, currency=currency, quantity=qty, product=product, partner=partner)
        for vals in res.get('taxes', []):
            group = env['account.tax'].browse(vals['id']).tax_group_id
            totals[group] = totals.get(group, 0.0) + vals['amount']
    rows = []
    for group, amount in sorted(
            totals.items(), key=lambda kv: (getattr(kv[0], 'sequence', 0), kv[0].id or 0)):
        name_en = group.with_context(lang=LANG_EN).name
        name_ar = group.with_context(lang=LANG_AR).name
        name = name_en if (not name_ar or name_ar == name_en) else '%s %s' % (name_en, name_ar)
        rows.append({'name': name, 'amount': amount})
    return rows


def chunk(items, size=4):
    return [items[i:i + size] for i in range(0, len(items), size)]


def barcode_svg_uri(value):
    """Code128 barcode as an SVG data URI (no PNG backend needed)."""
    if not value:
        return False
    try:
        import base64
        from reportlab.graphics import renderSVG
        from reportlab.graphics.barcode import createBarcodeDrawing
        drawing = createBarcodeDrawing(
            'Code128', value=str(value), barHeight=60, humanReadable=False, quiet=False)
        svg = renderSVG.drawToString(drawing)
        width, height = drawing.width, drawing.height
        svg = re.sub(r'<!DOCTYPE.*?>', '', svg, flags=re.S)
        svg = re.sub(r'viewBox="[^"]*"', 'viewBox="0 0 %s %s"' % (width, height), svg, count=1)
        svg = re.sub(r'preserveAspectRatio="[^"]*"', 'preserveAspectRatio="none"', svg, count=1)
        return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()
    except Exception:
        return False


class AkgrReportMixin(models.AbstractModel):
    _name = 'akgr.report.mixin'
    _description = 'AKG report helpers'

    def _akgr_lang(self):
        """Page language. Pages are always left-to-right, so an Arabic partner
        language must not flip the document to RTL."""
        self.ensure_one()
        partner = first_field(self, ['partner_id'])
        lang = (partner and partner.lang) or self.env.lang or LANG_EN
        return LANG_EN if lang.startswith('ar') else lang
