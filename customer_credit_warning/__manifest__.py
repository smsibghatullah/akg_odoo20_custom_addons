# -*- coding: utf-8 -*-
{
    'name': "Customer Credit Warning",

    'summary': """
       Customer Credit Warning, Customer Due Payments, Customer Customer Due Payments in Sale Order, Sale Order Customer Credit Warning""",

    'description': """
       Customer Credit Warning, Customer Due Payments, Customer Customer Due Payments in Sale Order, Sale Order Customer Credit Warning """,

    'author': "Kaizen Principles",
    'website': 'https://erp-software.odoo-saudi.com/discount/',

    'category': 'Accounting',
    'version': '20.0.1.0.0',
    'license': 'OPL-1',

    # any module necessary for this one to work correctly
    'depends': ['base','account_accountant', 'sale'],

    # always loaded
    'data': [
        'views/sale_order.xml',
    ],

    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,

}
