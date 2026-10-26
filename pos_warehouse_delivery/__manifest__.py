# -*- coding: utf-8 -*-
{
    'name': 'POS Warehouse Delivery Orders',
    'version': '20.0.1.1.0',
    'category': 'Point of Sale',
    'summary': 'Warehouse dropdown per POS orderline + warehouse-wise delivery orders',
    'depends': ['point_of_sale', 'pos_stock'],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_warehouse_delivery/static/src/app/services/pos_store.js',
            'pos_warehouse_delivery/static/src/app/components/orderline.js',
            'pos_warehouse_delivery/static/src/app/components/orderline.xml',
            'pos_warehouse_delivery/static/src/app/screens/ticket_screen.js',
            'pos_warehouse_delivery/static/src/app/screens/ticket_screen.xml',
            'pos_warehouse_delivery/static/src/scss/pos_wh.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
