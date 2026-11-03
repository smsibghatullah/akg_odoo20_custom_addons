# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

AKGPF_TEMPLATE = 'akg_proforma_report.report_proforma_akg'
AKGPF_XMLIDS = ['sale.action_report_pro_forma_invoice']


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _akgpf_apply_report(self):
        """Point every sale.order Pro-Forma print action to the AKG template.

        Found by xml id AND by report name (anything containing pro_forma /
        proforma), so it still works if another module added its own action.
        Called from data/report_action.xml (every install / upgrade).
        """
        paperformat = self.env.ref('akg_doc_reports.paperformat_akgr', raise_if_not_found=False)
        reports = self.browse()
        for xmlid in AKGPF_XMLIDS:
            report = self.env.ref(xmlid, raise_if_not_found=False)
            if report:
                reports |= report
        reports |= self.search([
            ('model', '=', 'sale.order'),
            ('report_type', 'in', ('qweb-pdf', 'qweb-html')),
            '|', ('report_name', 'ilike', 'pro_forma'), ('report_name', 'ilike', 'proforma'),
        ])
        if not reports:
            _logger.warning(
                'akg_proforma_report: no Pro-Forma print action found. Enable '
                'Settings > Sales > Pro-Forma Invoice, then upgrade this module. '
                'sale.order reports: %s',
                [(r.id, r.name, r.report_name) for r in self.search([('model', '=', 'sale.order')])])
            return True
        for report in reports:
            vals = {}
            if report.report_name != AKGPF_TEMPLATE:
                vals['report_name'] = AKGPF_TEMPLATE
                if 'report_file' in report._fields:  # removed in Odoo 20
                    vals['report_file'] = AKGPF_TEMPLATE
            if paperformat and report.paperformat_id != paperformat:
                vals['paperformat_id'] = paperformat.id
            if vals:
                _logger.info('akg_proforma_report: %s (%s) -> %s', report.name, report.report_name, AKGPF_TEMPLATE)
                report.write(vals)
        return True

    # Safety net: whatever action prints a sale.order through a standard
    # pro-forma template, the AKG pro-forma template is rendered.
    def _render_template(self, template, values=None):
        if isinstance(template, str) and template != AKGPF_TEMPLATE:
            low = template.lower()
            model = (values or {}).get('doc_model') or (self.model if len(self) == 1 else False)
            if model == 'sale.order' and ('pro_forma' in low or 'proforma' in low) \
                    and not template.startswith('akg_'):
                template = AKGPF_TEMPLATE
        return super()._render_template(template, values=values)
