# -*- coding: utf-8 -*-
{
    'name': "bi_pos_customer_ref",
    'summary': "Customer reference on POS orders/invoices, price lock groups, QR code on reports",
    'description': """
        - Customer Reference button on the POS order, copied to the invoice and printed on it.
        - Groups to allow / forbid editing unit price and discount on sale order lines.
        - Company QR code on report footers.
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Sales/Point of Sale',
    'license': 'LGPL-3',
    'version': '20.0.1.0.0',
    'depends': ['point_of_sale', 'account', 'l10n_sa', 'sale_management', 'sales_team'],
    'data': [
        'security/security.xml',
        'views/templates.xml',
        'views/views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'bi_pos_customer_ref/static/src/app/customer_reference.js',
            'bi_pos_customer_ref/static/src/app/customer_reference.xml',
        ],
    },
    'installable': True,
}
