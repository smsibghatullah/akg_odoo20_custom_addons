# -*- coding: utf-8 -*-
import base64
import io
import logging

from PIL import Image

from odoo import api, models
from odoo.tools import file_open

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

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
    def _akg_apply_company_layout(self):
        """Make 'Lines' the document layout of every company, so standard
        reports (delivery slip, etc.) use the inherited AKG header/footer too."""
        try:
            layout = self.env.ref('web.report_layout_lines', raise_if_not_found=False)
            if not layout and 'report.layout' in self.env:
                layout = self.env['report.layout'].search(
                    [('view_id.key', '=', 'web.external_layout_lines')], limit=1)
            if layout and 'external_report_layout_id' in self._fields:
                self.sudo().search([]).write({'external_report_layout_id': layout.id})
            else:
                _logger.warning('akg_report_layout: Lines layout record not found; '
                                'select it in Settings > Companies > Document Layout.')
        except Exception:
            _logger.warning('akg_report_layout: could not set the company layout', exc_info=True)
        return True
