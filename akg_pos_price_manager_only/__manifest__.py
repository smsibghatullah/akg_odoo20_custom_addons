# -*- coding: utf-8 -*-
{
    'name': 'AKG - POS Price Control: managers only',
    'version': '20.0.1.1.1',
    'category': 'Sales/Point of Sale',
    'summary': 'With "Price Control" ON only the POS manager can change a price; the Price button is disabled for everybody else.',
    'description': """
POS > Settings > Pricing > "Price Control" (restrict_price_control).

Standard Odoo 20 gives an employee the role "manager" whenever his linked USER is in the POS Manager
group - even if the employee is listed as Cashier in the POS settings. So cashiers kept a working Price
button. This module decides by the POS settings instead:

  * employee listed under "Manager"                         -> may change prices
  * employee listed under Cashier / Supervised / Restrictive -> Price button disabled (even if his user is a POS manager)
  * employee in no list: manager only if his user is in the POS Manager group (standard rule)
  * without "Log in with Employees": the logged-in user must be in the POS Manager group (standard rule)

The Price button is greyed out and a click is blocked with a message. Works per POS (each POS has its own
"Price Control" switch).

Also: settling a quotation/sale order that contains lot/serial tracked products no longer crashes
(static/src/app/settle_so_tracked_fix.js).
""",
    'depends': ['point_of_sale', 'pos_hr', 'pos_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'akg_pos_price_manager_only/static/src/**/*',
        ],
    },
    'author': 'AKG Hardware',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
