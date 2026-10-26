# -*- coding: utf-8 -*-
from odoo import api, models

AKGR_REPORTS = {
    'sale.action_report_saleorder': 'akg_doc_reports.report_saleorder_akg',
    'purchase.action_report_purchase_order': 'akg_doc_reports.report_purchaseorder_akg',
    'purchase.report_purchase_quotation': 'akg_doc_reports.report_purchasequotation_akg',
    'stock.action_report_picking': 'akg_doc_reports.report_picking_akg',
}


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _akgr_apply_reports(self):
        """Point the standard print actions to the AKG templates and paper format.
        Called from data/report_action.xml (every install / upgrade). After
        upgrading sale / purchase / stock run `-u akg_doc_reports` once more."""
        paperformat = self.env.ref('akg_doc_reports.paperformat_akgr', raise_if_not_found=False)
        for xmlid, template in AKGR_REPORTS.items():
            report = self.env.ref(xmlid, raise_if_not_found=False)
            if not report:
                continue
            vals = {}
            if report.report_name != template:
                vals['report_name'] = template
                if 'report_file' in report._fields:  # removed in Odoo 20
                    vals['report_file'] = template
            if paperformat and report.paperformat_id != paperformat:
                vals['paperformat_id'] = paperformat.id
            if vals:
                report.write(vals)
        return True
