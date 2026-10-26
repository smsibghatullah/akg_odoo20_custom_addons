# -*- coding: utf-8 -*-
from . import models

# our template -> standard template to restore
OURS_TO_ORIGINAL = {
    'akg_doc_reports.report_saleorder_akg': 'sale.report_saleorder',
    'akg_doc_reports.report_purchaseorder_akg': 'purchase.report_purchaseorder',
    'akg_doc_reports.report_purchasequotation_akg': 'purchase.report_purchasequotation',
    'akg_doc_reports.report_picking_akg': 'stock.report_picking',
}


def uninstall_hook(env):
    """Give the standard print actions their original templates back."""
    for ours, original in OURS_TO_ORIGINAL.items():
        for report in env['ir.actions.report'].search([('report_name', '=', ours)]):
            vals = {'report_name': original}
            if 'report_file' in report._fields:
                vals['report_file'] = original
            report.write(vals)
