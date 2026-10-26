# -*- coding: utf-8 -*-
from . import models

# standard action -> (template installed by this module, template to restore)
REPORT_MAP = {
    'sale.action_report_saleorder': 'sale.report_saleorder',
    'purchase.action_report_purchase_order': 'purchase.report_purchaseorder',
    'purchase.report_purchase_quotation': 'purchase.report_purchasequotation',
    'stock.action_report_picking': 'stock.report_picking',
}


def uninstall_hook(env):
    """Give the standard print actions their original templates back."""
    for xmlid, original in REPORT_MAP.items():
        report = env.ref(xmlid, raise_if_not_found=False)
        if report:
            vals = {'report_name': original}
            if 'report_file' in report._fields:
                vals['report_file'] = original
            report.write(vals)
