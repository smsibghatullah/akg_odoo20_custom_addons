# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

AKGD_TEMPLATE = 'akg_delivery_slip_report.report_deliveryslip_akg'
AKGD_STANDARD_TEMPLATE = 'stock.report_deliveryslip'
AKGD_XMLIDS = ['stock.action_report_delivery']


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _akgd_apply_report(self):
        """Point the standard Delivery Slip action(s) to the AKG template + paper format.

        Found by xml id AND by standard template name. Called from
        data/report_action.xml (every install / upgrade).
        """
        paperformat = self.env.ref('akg_doc_reports.paperformat_akgr', raise_if_not_found=False)
        reports = self.browse()
        for xmlid in AKGD_XMLIDS:
            report = self.env.ref(xmlid, raise_if_not_found=False)
            if report:
                reports |= report
        reports |= self.search([('model', '=', 'stock.picking'),
                                ('report_name', '=', AKGD_STANDARD_TEMPLATE)])
        if not reports:
            _logger.warning(
                'akg_delivery_slip_report: no Delivery Slip print action found. '
                'stock.picking reports: %s',
                [(r.id, r.name, r.report_name) for r in self.search([('model', '=', 'stock.picking')])])
            return True
        for report in reports:
            vals = {}
            if report.report_name != AKGD_TEMPLATE:
                vals['report_name'] = AKGD_TEMPLATE
                if 'report_file' in report._fields:  # removed in Odoo 20
                    vals['report_file'] = AKGD_TEMPLATE
            if paperformat and report.paperformat_id != paperformat:
                vals['paperformat_id'] = paperformat.id
            if vals:
                _logger.info('akg_delivery_slip_report: %s (%s) -> %s',
                             report.name, report.report_name, AKGD_TEMPLATE)
                report.write(vals)
        return True

    # Safety net: whoever renders the standard delivery slip gets the AKG one.
    def _render_template(self, template, values=None):
        if template == AKGD_STANDARD_TEMPLATE:
            model = (values or {}).get('doc_model') or (self.model if len(self) == 1 else False)
            if model == 'stock.picking':
                template = AKGD_TEMPLATE
        return super()._render_template(template, values=values)
