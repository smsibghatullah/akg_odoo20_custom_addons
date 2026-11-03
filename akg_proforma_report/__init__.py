# -*- coding: utf-8 -*-
from . import models

STANDARD_XMLID = 'sale.action_report_pro_forma_invoice'
STANDARD_TEMPLATE = 'sale.report_saleorder_pro_forma'
OURS = 'akg_proforma_report.report_proforma_akg'


def uninstall_hook(env):
    """Give the standard Pro-Forma action its template and Print-menu entry back."""
    std = env.ref(STANDARD_XMLID, raise_if_not_found=False)
    if not std:
        return
    vals = {}
    if std.report_name == OURS:
        vals['report_name'] = STANDARD_TEMPLATE
        if 'report_file' in std._fields:
            vals['report_file'] = STANDARD_TEMPLATE
    if not std.binding_model_id:
        vals.update({
            'binding_model_id': env['ir.model']._get_id('sale.order'),
            'binding_type': 'report',
        })
    if vals:
        std.write(vals)
