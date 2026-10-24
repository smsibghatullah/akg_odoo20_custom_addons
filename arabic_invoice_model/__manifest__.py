# -*- coding: utf-8 -*-
{
    'name': 'GCC - Arabic/English Invoice (AKG)',
    'version': '20.0.1.0.0',
    'author': 'AKG Hardware',
    'category': 'Accounting/Localizations',
    'summary': 'Bilingual Arabic/English tax invoice & delivery note for Odoo 20',
    'description': """
Bilingual (Arabic / English) customer invoice, ported from the Odoo 16 module.

* Does NOT xpath into core invoice templates (that is what broke the install on Odoo 20).
* Ships its own self-contained QWeb report and re-points the standard
  "Invoices" print actions (account.account_invoices and
  account.account_invoices_without_payment) to it.
* Works for invoices printed from the backend, e-mailed, and printed from the POS.
""",
    'license': 'LGPL-3',
    'depends': ['account', 'web'],
    'data': [
        'views/report_invoice.xml',
        'data/report_action.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
