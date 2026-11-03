# -*- coding: utf-8 -*-
{
    'name': 'AKG - Pro-Forma Invoice Report',
    'version': '20.0.1.1.0',
    'author': 'AKG Hardware',
    'category': 'Hidden',
    'summary': 'Pro-Forma Invoice PDF in the AKG layout, with its own Print menu entry.',
    'description': """
Pro-Forma Invoice (sale.order) in the same AKG look as the Quotation / Order:
shared header (logo, company name, Tax ID, website), customer block, teal
"Pro-Forma Invoice # S0xxxx" title, info row, lines table, totals box, notes,
payment terms and the shared footer with QR.

The module ships its OWN print action ("PRO-FORMA Invoice", bound to Sales
Orders, visible to every internal user), so the entry in the Print menu does not
depend on the standard action / the "Pro-Forma Invoice" setting.  The standard
action stays usable for e-mail templates (its template is swapped at render time).
""",
    'license': 'LGPL-3',
    'depends': ['sale', 'akg_doc_reports'],
    'data': [
        'views/report_proforma.xml',
        'data/report_action.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
