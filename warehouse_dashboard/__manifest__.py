{
    'name': 'Warehouse Wise Inventory Dashboard',
    'version': '20.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Warehouse wise dashboard showing Delivery Orders, Internal Transfers and POS Orders',
    'description': """
Warehouse Wise Inventory Dashboard
===================================
- Ek dashboard screen jo Inventory app mein har Warehouse ke liye group wise
  card show karta hai.
- Har warehouse card ke andar 3 tiles hote hain:
    1. Delivery Orders
    2. Internal Transfers
    3. POS Orders
- Har tile par count show hota hai (jo records abhi "Done" state mein nahi
  hain, matlab pending / ready / waiting records).
- Count par click karne se us warehouse ke us type ke records ka tree
  (list) view khul jata hai.
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': ['stock', 'point_of_sale'],
    'data': [
        'security/ir.access.csv',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'warehouse_dashboard/static/src/scss/warehouse_dashboard.scss',
            'warehouse_dashboard/static/src/js/warehouse_dashboard.js',
            'warehouse_dashboard/static/src/xml/warehouse_dashboard_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
