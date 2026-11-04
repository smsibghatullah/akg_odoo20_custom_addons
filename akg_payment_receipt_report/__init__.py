# -*- coding: utf-8 -*-
from . import models

STANDARD_TEMPLATE = 'account.report_payment_receipt'
OURS = 'akg_payment_receipt_report.report_payment_akg'


def uninstall_hook(env):
    """Give the standard Payment Receipt action its original template back."""
    for report in env['ir.actions.report'].search([('report_name', '=', OURS)]):
        vals = {'report_name': STANDARD_TEMPLATE}
        if 'report_file' in report._fields:
            vals['report_file'] = STANDARD_TEMPLATE
        report.write(vals)
