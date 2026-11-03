# -*- coding: utf-8 -*-
from . import models

ORIGINAL = 'sale.report_saleorder_pro_forma'
OURS = 'akg_proforma_report.report_proforma_akg'


def uninstall_hook(env):
    """Give the standard Pro-Forma print action its original template back."""
    for report in env['ir.actions.report'].search([('report_name', '=', OURS)]):
        vals = {'report_name': ORIGINAL}
        if 'report_file' in report._fields:
            vals['report_file'] = ORIGINAL
        report.write(vals)
