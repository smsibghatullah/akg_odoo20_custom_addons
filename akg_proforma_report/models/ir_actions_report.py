# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

AKGPF_TEMPLATE = 'akg_proforma_report.report_proforma_akg'
AKGPF_ACTION = 'akg_proforma_report.action_report_proforma_akg'
AKGPF_STANDARD = 'sale.action_report_pro_forma_invoice'


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _akgpf_apply_report(self):
        """Make sure our Pro-Forma action is bound to Sales Orders (Print menu).

        Called from data/report_action.xml on every install / upgrade.
        * our own action (data/report_action.xml) is the Print-menu entry;
        * the standard Pro-Forma action is un-bound from the menu (so there is no
          duplicate entry) but kept for e-mail templates - the template swap
          below renders the AKG layout for it too.
        """
        ours = self.env.ref(AKGPF_ACTION, raise_if_not_found=False)
        if not ours:
            _logger.warning('akg_proforma_report: action %s not found', AKGPF_ACTION)
            return True
        if not ours.binding_model_id:
            ours.write({
                'binding_model_id': self.env['ir.model']._get_id('sale.order'),
                'binding_type': 'report',
            })
        std = self.env.ref(AKGPF_STANDARD, raise_if_not_found=False)
        if std and std.binding_model_id:
            std.write({'binding_model_id': False})
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
