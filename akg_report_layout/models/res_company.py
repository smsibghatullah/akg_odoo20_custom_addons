# -*- coding: utf-8 -*-
import base64
import io
import logging
from functools import lru_cache

from PIL import Image

from odoo import api, models
from odoo.tools import file_open

_logger = logging.getLogger(__name__)

AKGR_FONT_FILES = (
    ('normal', 'akg_report_layout/static/src/fonts/Oswald-Regular-latin.ttf'),
    ('bold', 'akg_report_layout/static/src/fonts/Oswald-Bold-latin.ttf'),
)


@lru_cache(maxsize=1)
def _akgr_font_css_cached():
    css = ''
    for weight, path in AKGR_FONT_FILES:
        try:
            with file_open(path, 'rb') as f:
                data = base64.b64encode(f.read()).decode()
        except Exception:
            _logger.warning('akg_report_layout: font file %s not found', path)
            continue
        css += ("@font-face { font-family: 'Oswald'; font-weight: %s; font-style: normal; "
                "src: url(data:font/truetype;base64,%s) format('truetype'); }\n" % (weight, data))
    return css


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _akgr_font_css(self):
        """@font-face rules (Oswald Regular + Bold) as one string, read once per server process."""
        from markupsafe import Markup
        return Markup(_akgr_font_css_cached())

    def _akgr_logo_uri(self):
        """Logo re-encoded to PNG (old WebKit in wkhtmltopdf cannot draw WebP)."""
        self.ensure_one()
        raw = self.logo
        if not raw:
            return False
        try:
            if isinstance(raw, str):
                raw = raw.encode()
            raw = bytes(raw)
            if not raw.startswith((b'\x89PNG', b'\xff\xd8', b'GIF8', b'RIFF')):
                raw = base64.b64decode(raw)
            img = Image.open(io.BytesIO(raw)).convert('RGBA')
            if img.width > 480:
                img = img.resize((480, max(1, int(img.height * 480 / img.width))))
            out = io.BytesIO()
            img.save(out, format='PNG')
            return 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()
        except Exception:
            return False

    def _akgr_qr_uri(self):
        self.ensure_one()
        for path in ('akg_report_layout/static/src/img/qr_code.png',
                     'akg_doc_reports/static/src/img/qr_code.png',
                     'arabic_invoice_model/static/src/img/qr_code.png',
                     'bi_pos_customer_ref/static/src/img/qr_code.png'):
            try:
                with file_open(path, 'rb') as f:
                    return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
            except Exception:
                continue
        return False

    def _akgr_footer_vals(self):
        """Texts of the footer (ONE place for all reports). Edit here if they change."""
        self.ensure_one()
        cr = False
        for rec in (self, self.partner_id):
            if 'company_registry' in rec._fields and rec.company_registry:
                cr = cr or rec.company_registry
        return {
            'tax_card': '8458551',
            'cr_no': cr or '1/02236/9',
            'ar_name': 'روابي بوشر للتجارة والمقاولات ش ش و',
            'thank_en': 'Thank you !',
            'thank_ar': 'شكرًا لك',
        }

    @api.model
    def _akgr_force_paperformats(self):
        """Every AKG paper format: top margin 38 mm, header spacing 6 mm (= 32 mm for the repeating header),
        bottom 34 mm. Written on every update so a format edited by hand in a database cannot push
        the header over the document (header too low / overlapping the address block)."""
        # header_spacing differs per server: wkhtmltopdf draws the header line at (margin_top - spacing).
        # Default 6. If a server draws the header too low, set the system parameter
        # akg_report_layout.header_spacing (e.g. 38) - it survives every module update.
        raw = self.env['ir.config_parameter'].sudo().get_param('akg_report_layout.header_spacing')
        try:
            spacing = float(raw) if raw not in (False, None, '') else 6.0
        except ValueError:
            spacing = 6.0
        vals = {'format': 'A4', 'orientation': 'Portrait', 'margin_top': 38, 'margin_bottom': 34,
                'margin_left': 8, 'margin_right': 8, 'header_spacing': spacing, 'header_line': False, 'dpi': 90}
        for xmlid in ('akg_report_layout.paperformat_akg', 'akg_doc_reports.paperformat_akgr',
                      'arabic_invoice_model.paperformat_akg_invoice'):
            paper = self.env.ref(xmlid, raise_if_not_found=False)
            if paper:
                paper.sudo().write(vals)
        return True

    @api.model
    def _akg_apply_company_layout(self):
        """Select the 'Lines' document layout for every company.

        company.external_report_layout_id is a Many2one to **ir.ui.view**
        (the layout template itself), so the id written must be the view id of
        web.external_layout_lines - NOT a report.layout id.
        """
        try:
            view = self.env.ref('web.external_layout_lines', raise_if_not_found=False)
            if view and view._name == 'ir.ui.view' and 'external_report_layout_id' in self._fields:
                self.sudo().search([]).write({'external_report_layout_id': view.id})
            else:
                _logger.warning('akg_report_layout: web.external_layout_lines not found; '
                                'select the layout in Settings > Companies > Document Layout.')
        except Exception:
            _logger.warning('akg_report_layout: could not set the company layout', exc_info=True)
        return True
