# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

AKGP_TEMPLATE = 'akg_payment_receipt_report.report_payment_akg'
AKGP_STANDARD_TEMPLATE = 'account.report_payment_receipt'
AKGP_XMLIDS = ['account.action_report_payment_receipt']


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _akgp_apply_report(self):
        """Point the standard Payment Receipt action(s) to the AKG template + paper format.

        Found by xml id AND by standard template name. Called from
        data/report_action.xml (every install / upgrade).
        """
        paperformat = self.env.ref('akg_doc_reports.paperformat_akgr', raise_if_not_found=False)
        reports = self.browse()
        for xmlid in AKGP_XMLIDS:
            report = self.env.ref(xmlid, raise_if_not_found=False)
            if report:
                reports |= report
        reports |= self.search([('model', '=', 'account.payment'),
                                ('report_name', '=', AKGP_STANDARD_TEMPLATE)])
        if not reports:
            _logger.warning(
                'akg_payment_receipt_report: no Payment Receipt print action found. '
                'account.payment reports: %s',
                [(r.id, r.name, r.report_name) for r in self.search([('model', '=', 'account.payment')])])
            return True
        for report in reports:
            vals = {}
            if report.report_name != AKGP_TEMPLATE:
                vals['report_name'] = AKGP_TEMPLATE
                if 'report_file' in report._fields:  # removed in Odoo 20
                    vals['report_file'] = AKGP_TEMPLATE
            if paperformat and report.paperformat_id != paperformat:
                vals['paperformat_id'] = paperformat.id
            if vals:
                _logger.info('akg_payment_receipt_report: %s (%s) -> %s',
                             report.name, report.report_name, AKGP_TEMPLATE)
                report.write(vals)
        return True

    # Safety net: whoever renders the standard payment receipt gets the AKG one.
    def _render_template(self, template, values=None):
        if template == AKGP_STANDARD_TEMPLATE:
            model = (values or {}).get('doc_model') or (self.model if len(self) == 1 else False)
            if model == 'account.payment':
                template = AKGP_TEMPLATE
        return super()._render_template(template, values=values)
