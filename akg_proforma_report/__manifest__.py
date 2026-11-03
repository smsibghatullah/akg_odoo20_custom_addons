# -*- coding: utf-8 -*-
{
    'name': 'AKG - Pro-Forma Invoice Report',
    'version': '20.0.1.0.0',
    'author': 'AKG Hardware',
    'category': 'Hidden',
    'summary': 'Pro-Forma Invoice PDF in the AKG layout (logo header, QR footer, Oswald-like look).',
    'description': """
Pro-Forma Invoice (sale.order) in the same AKG look as the Quotation / Order:
shared header (logo, company name, Tax ID, website), customer block, teal
"Pro-Forma Invoice # S0xxxx" title, info row, lines table, totals box, notes,
payment terms and the shared footer with QR.

The standard "PRO-FORMA Invoice" print action is pointed to this template on
every install / upgrade, and a safety net swaps the template at render time.
""",
    'license': 'LGPL-3',
    'depends': ['akg_doc_reports'],
    'data': [
        'views/report_proforma.xml',
        'data/report_action.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
