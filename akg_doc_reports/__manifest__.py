# -*- coding: utf-8 -*-
{
    'name': 'AKG - Quotation / Order / RFQ / Picking Reports (Odoo 16 look)',
    'version': '20.0.1.0.1',
    'author': 'AKG Hardware',
    'category': 'Hidden',
    'summary': 'Sales order/quotation, purchase order/RFQ and picking operations '
               'reports with the Odoo 16 AKG layout (header, footer, fonts).',
    'description': """
Self-contained report templates (own header / footer / inline CSS, no xpath on core
templates) for:

* Quotation / Sales Order        (sale.action_report_saleorder)
* Purchase Order / RFQ           (purchase.action_report_purchase_order,
                                  purchase.report_purchase_quotation)
* Picking Operations             (stock.action_report_picking)

The picking barcode is drawn as SVG, so the report works even when reportlab's
PNG backend (rlPyCairo / _rl_renderPM) is not installed.
""",
    'license': 'LGPL-3',
    'depends': ['web', 'sale', 'purchase', 'stock'],
    'data': [
        'data/paperformat.xml',
        'views/report_common.xml',
        'views/report_sale.xml',
        'views/report_purchase.xml',
        'views/report_picking.xml',
        'data/report_action.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
