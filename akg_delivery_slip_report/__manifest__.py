# -*- coding: utf-8 -*-
{
    'name': 'AKG - Delivery Slip Report',
    'version': '20.0.1.1.1',
    'author': 'AKG Hardware',
    'category': 'Hidden',
    'summary': 'Delivery Slip (stock.picking) PDF in the AKG layout.',
    'description': """
Delivery Slip in the same AKG look as the other reports: shared header (logo,
company name, Tax ID, website), Customer Address / Warehouse Address blocks,
teal picking reference as title, Order + Shipping Date row, Product / Ordered /
Delivered table (and Lot/Serial when used) and the shared footer with QR.

The standard "Delivery Slip" print action is pointed to this template and to the
AKG paper format on every install / upgrade; a render-time swap is the safety net.
""",
    'license': 'LGPL-3',
    'depends': ['stock', 'akg_doc_reports'],
    'data': [
        'views/report_delivery.xml',
        'data/report_action.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
