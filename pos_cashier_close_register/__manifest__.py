# -*- coding: utf-8 -*-
{
    'name': 'POS Cashier - Close Register',
    'version': '20.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Show the "Close Register" button to the cashier role (not only managers)',
    'description': """
With Employees / PIN login (pos_hr) the "Close Register" button of the POS
menu is only shown to the *manager* role.  This module also shows it to the
*cashier* role.
""",
    'depends': ['point_of_sale', 'pos_hr'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cashier_close_register/static/src/access_right.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
