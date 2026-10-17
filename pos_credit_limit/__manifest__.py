# -*- coding: utf-8 -*-
{
    'name': "POS Credit Limit",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        'description': 'This is a test description with path C:\\Users\\Example',

    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '20.0.1.0.0',

    'depends': ['base','point_of_sale'],

    'data': [
    ],

    'assets': {
        'point_of_sale.assets': [
            'pos_credit_limit/static/src/js/credit_limit_patch.js',
        ],
    },

    'demo': [
        'demo/demo.xml',
    ],
}
