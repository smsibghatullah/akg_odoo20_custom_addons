# -*- coding: utf-8 -*-
from odoo import api, models

AKG_REPORTS = {
    # standard action               -> our template
    'account.account_invoices':
        'arabic_invoice_model.report_invoice_arabic_with_payments',
    'account.account_invoices_without_payment':
        'arabic_invoice_model.report_invoice_arabic',
}


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _akg_apply_arabic_invoice_reports(self):
        """Point the standard invoice print actions to the bilingual template.

        Called from data/report_action.xml, so it is re-applied on every
        install / upgrade of this module (after `-u account`, run
        `-u arabic_invoice_model` once more).
        """
        for xmlid, template in AKG_REPORTS.items():
            report = self.env.ref(xmlid, raise_if_not_found=False)
            if report and report.report_name != template:
                vals = {'report_name': template}
                if 'report_file' in report._fields:  # removed in Odoo 20
                    vals['report_file'] = template
                report.write(vals)
        return True
