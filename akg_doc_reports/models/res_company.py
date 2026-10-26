# -*- coding: utf-8 -*-
import base64
import io

from PIL import Image

from odoo import models
from odoo.tools import file_open

from .common import first_field


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
        for path in ('akg_doc_reports/static/src/img/qr_code.png',
                     'arabic_invoice_model/static/src/img/qr_code.png',
                     'bi_pos_customer_ref/static/src/img/qr_code.png'):
            try:
                with file_open(path, 'rb') as f:
                    return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
            except Exception:
                continue
        return False

    def _akgr_footer_vals(self):
        """Texts of the footer. Edit here if they change."""
        self.ensure_one()
        cr = False
        for rec in (self, self.partner_id):
            cr = cr or first_field(rec, ['company_registry'])
        return {
            'tax_card': '8458551',
            'cr_no': cr or '1/02236/9',
            'ar_name': 'روابي بوشر للتجارة والمقاولات ش ش و',
            'thank_en': 'Thank you !',
            'thank_ar': 'شكرًا لك',
        }
