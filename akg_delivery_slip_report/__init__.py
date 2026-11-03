# -*- coding: utf-8 -*-
from . import models

STANDARD_TEMPLATE = 'stock.report_deliveryslip'
OURS = 'akg_delivery_slip_report.report_deliveryslip_akg'


def uninstall_hook(env):
    """Give the standard Delivery Slip action its original template back."""
    for report in env['ir.actions.report'].search([('report_name', '=', OURS)]):
        vals = {'report_name': STANDARD_TEMPLATE}
        if 'report_file' in report._fields:
            vals['report_file'] = STANDARD_TEMPLATE
        report.write(vals)
