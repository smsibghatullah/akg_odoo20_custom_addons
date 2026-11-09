# -*- coding: utf-8 -*-
{
    'name': 'AKG - Payment Receipt Report',
    'version': '20.0.1.1.0',
    'author': 'AKG Hardware',
    'category': 'Hidden',
    'summary': 'Payment Receipt / Refund Confirmation (account.payment) PDF in the AKG layout.',
    'description': """
Payment Receipt and Refund Confirmation in the same AKG look as the other reports:
shared header (logo, company name, Tax ID, website), teal title, payment info block
(date, customer, amount, method, memo), Invoice Date / Invoice Number / Reference / Amount
table with the "Due Amount for ..." rows, and the shared footer with QR.

Works for all payments: customer receipts, customer refunds (also POS refunds without a
reconciled invoice), vendor payments. The standard "Payment Receipt" print action is pointed
to this template and to the AKG paper format on every install / upgrade; a render-time swap
is the safety net.
""",
    'license': 'LGPL-3',
    'depends': ['account', 'akg_report_layout', 'akg_doc_reports'],
    'data': [
        'views/report_payment.xml',
        'data/report_action.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
