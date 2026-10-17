{
    'name': 'Point of Sale Wise Inventory Dashboard',
    'version': '20.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Point of Sale wise dashboard showing Receipts, Internal Transfers, Delivery Orders and POS Orders',
    'description': """
Point of Sale Wise Inventory Dashboard
=======================================
- Ek dashboard screen jo Inventory app mein har (currently active) Point
  of Sale ke liye ek column show karta hai - sirf utne columns jitne
  Point of Sale > Configuration > Point of Sale mein maujood hain.
- Har POS column ke andar 2 cards hote hain:
    1. Delivery Orders - is chain se filter hota hai:
       stock.picking.pos_order_id -> pos.order -> session_id
       -> pos.session -> config_id
    2. Internal Transfers - us POS ke DEFAULT WAREHOUSE se filter hota
       hai (pos.config.picking_type_id.warehouse_id), kyunke Internal
       Transfer par pos_order_id reliably populate nahi hota.
- Har card par "TO PROCESS" count aur Waiting / Late / Back Orders
  breakdown show hota hai, bilkul Odoo ke native Inventory overview ki
  tarah.
- Kisi bhi count/stat par click karne se usi filter ke sath us POS ke
  records ka list (tree) view khul jata hai.
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': ['stock', 'point_of_sale'],
    'data': [
        'security/ir.access.csv',
        'views/pos_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pos_dashboard/static/src/scss/pos_dashboard.scss',
            'pos_dashboard/static/src/js/pos_dashboard.js',
            'pos_dashboard/static/src/xml/pos_dashboard_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
