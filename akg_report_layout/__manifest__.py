# -*- coding: utf-8 -*-
{
    'name': 'AKG - Common Report Header / Footer',
    'version': '20.0.1.3.4',
    'author': 'AKG Hardware',
    'category': 'Hidden',
    'summary': 'One shared AKG header/footer for every PDF report (inherits web.external_layout_lines).',
    'description': """
Single source of the AKG report header (logo, company name, Tax ID, website) and
footer (website, Tax Card, CR no., Arabic name, Thank you, QR).

* Inherits ``web.external_layout_lines`` so every standard Odoo report printed with
  that layout gets the same header/footer.
* Provides ``akg_report_layout.akg_header`` / ``akg_footer`` / ``akg_css`` which
  akg_doc_reports (Quotation, PO/RFQ, Picking) and arabic_invoice_model
  (Invoice / Vendor Bill) call, so all reports are identical at top and bottom.
""",
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
        'data/paperformat.xml',
        'views/layout.xml',
        'data/layout_apply.xml',
    ],
    'installable': True,
    'application': False,
}
