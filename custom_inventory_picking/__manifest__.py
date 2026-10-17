# -*- coding: utf-8 -*-
{
    'name': "Custom Inventory Picking",

    'summary': "Set picking states",

    'description': """
Custom Inventory Module

    """,

    'author': "DSM (Dynamic Solution Maker)",
    'website': "http://www.dsmpk.com",

    'category': 'Inventory/Inventory',
    'license': 'LGPL-3',
    'version': '20.0.1.0.0',

    'depends': ['base', 'stock', 'sale_stock'],

    'data': [
        'views/views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
