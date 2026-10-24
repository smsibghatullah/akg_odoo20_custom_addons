# -*- coding: utf-8 -*-
from . import models

REPORT_MAP = {
    'account.account_invoices': 'account.report_invoice_with_payments',
    'account.account_invoices_without_payment': 'account.report_invoice',
}


def uninstall_hook(env):
    """Give the standard print actions back their original templates."""
    for xmlid, original in REPORT_MAP.items():
        report = env.ref(xmlid, raise_if_not_found=False)
        if report:
            vals = {'report_name': original}
            if 'report_file' in report._fields:  # removed in Odoo 20
                vals['report_file'] = original
            report.write(vals)
