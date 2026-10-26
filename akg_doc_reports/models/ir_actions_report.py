# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# (model, standard templates, xml ids of the standard actions, our template)
AKGR_TARGETS = [
    ('sale.order', ['sale.report_saleorder'], ['sale.action_report_saleorder'],
     'akg_doc_reports.report_saleorder_akg'),
    ('purchase.order', ['purchase.report_purchaseorder'], ['purchase.action_report_purchase_order'],
     'akg_doc_reports.report_purchaseorder_akg'),
    ('purchase.order', ['purchase.report_purchasequotation'], ['purchase.report_purchase_quotation'],
     'akg_doc_reports.report_purchasequotation_akg'),
    ('stock.picking', ['stock.report_picking'], ['stock.action_report_picking'],
     'akg_doc_reports.report_picking_akg'),
]


AKGR_SALE_TEMPLATE = 'akg_doc_reports.report_saleorder_akg'
AKGR_RECEIPT_TEMPLATE = 'akg_doc_reports.report_saleorder_receipt_akg'
AKGR_EXTRA_TEMPLATE = 'akg_doc_reports.report_saleorder_extra_akg'
AKGR_RECEIPT_WORDS = ('receipt', 'delivery', 'return', 'pickup', 'pick-up')
# PDF file names: Quotation - S001 / Order - S001 / Delivery or Return Receipt - S001
AKGR_NAME_ORDER = ("(object.state in ('draft', 'sent') and 'Quotation - %s' or 'Order - %s')"
                   " % (object.name or '').replace('/', '_')")
AKGR_NAME_RECEIPT = "'Delivery or Return Receipt - %s' % (object.name or '').replace('/', '_')"


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _akgr_apply_reports(self):
        """Point the standard print actions to the AKG templates and paper format.

        Actions are found by xml id AND by their standard template name, so
        every action that prints the standard report is covered (e.g. the
        extra "PDF Quote" action added by sale_pdf_quote_builder).
        Called from data/report_action.xml (every install / upgrade).
        """
        paperformat = self.env.ref('akg_doc_reports.paperformat_akgr', raise_if_not_found=False)
        main_sale_reports = self.browse()
        for model, originals, xmlids, template in AKGR_TARGETS:
            reports = self.browse()
            for xmlid in xmlids:
                report = self.env.ref(xmlid, raise_if_not_found=False)
                if report:
                    reports |= report
            reports |= self.search([('model', '=', model), ('report_name', 'in', originals)])
            if not reports:
                _logger.warning(
                    'akg_doc_reports: no print action found for %s (%s). Reports of that model: %s',
                    model, originals,
                    [(r.id, r.name, r.report_name) for r in self.search([('model', '=', model)])])
                continue
            if model == 'sale.order':
                main_sale_reports |= reports
            for report in reports:
                vals = {}
                if report.report_name != template:
                    vals['report_name'] = template
                    if 'report_file' in report._fields:  # removed in Odoo 20
                        vals['report_file'] = template
                if paperformat and report.paperformat_id != paperformat:
                    vals['paperformat_id'] = paperformat.id
                if vals:
                    _logger.info('akg_doc_reports: %s (%s) -> %s', report.name, report.report_name, template)
                    report.write(vals)

        # ---- other sale.order print actions (rental receipt, custom ...) ----
        # IMPORTANT: every action needs its OWN report_name. The download
        # controller finds the action by report_name to build the PDF file name,
        # so two actions sharing one report_name get the wrong file name.
        so_main = main_sale_reports
        if so_main:
            main = self.env.ref('sale.action_report_saleorder', raise_if_not_found=False)
            if main and main.print_report_name != AKGR_NAME_ORDER:
                main.write({'print_report_name': AKGR_NAME_ORDER})
        others = self.search([
            ('model', '=', 'sale.order'),
            ('report_type', 'in', ('qweb-pdf', 'qweb-html')),
            ('report_name', 'not ilike', 'pro_forma'),
            ('report_name', 'not ilike', 'proforma'),
        ]) - so_main
        for report in others:
            is_receipt = any(w in (report.name or '').lower() for w in AKGR_RECEIPT_WORDS)
            _logger.warning('akg_doc_reports: extra sale.order action id=%s name=%r report_name=%s receipt=%s',
                            report.id, report.name, report.report_name, is_receipt)
            vals = {}
            if is_receipt:
                if report.report_name != AKGR_RECEIPT_TEMPLATE:
                    vals['report_name'] = AKGR_RECEIPT_TEMPLATE
                if report.print_report_name != AKGR_NAME_RECEIPT:
                    vals['print_report_name'] = AKGR_NAME_RECEIPT
            elif report.report_name == AKGR_SALE_TEMPLATE:
                # was pointed to the main template by an earlier version of this module
                vals['report_name'] = AKGR_EXTRA_TEMPLATE
            elif not report.report_name.startswith('akg_doc_reports.'):
                continue  # keeps its own name; rendered through the AKG template by the hook below
            if 'report_name' in vals and 'report_file' in report._fields:
                vals['report_file'] = vals['report_name']
            if paperformat and report.paperformat_id != paperformat:
                vals['paperformat_id'] = paperformat.id
            if vals:
                report.write(vals)
        return True

    # ------------------------------------------------------------------
    # Safety net for the Sales Order / Quotation print.
    #
    # In Odoo 20 the sale order can be printed through more than one action
    # (sale, sale_renting, sale_pdf_quote_builder, e-mail / portal ...).  Some
    # of them still point to a standard template, so the print came out in the
    # plain Odoo 20 layout.  Every PDF/HTML render goes through
    # _render_template(), so we swap the template right there: whatever action
    # prints a sale.order, the AKG template is the one rendered.
    # ------------------------------------------------------------------
    def _akgr_swap_template(self, template):
        if (isinstance(template, str) and len(self) == 1 and self.model == 'sale.order'
                and not template.startswith('akg_doc_reports.')
                and 'pro_forma' not in template and 'proforma' not in template):
            is_receipt = any(w in (self.name or '').lower() for w in AKGR_RECEIPT_WORDS)
            new = AKGR_RECEIPT_TEMPLATE if is_receipt else AKGR_SALE_TEMPLATE
            _logger.warning('akg_doc_reports: sale.order render %s -> %s', template, new)
            return new
        return template

    def _render_template(self, template, values=None):
        return super()._render_template(self._akgr_swap_template(template), values=values)
