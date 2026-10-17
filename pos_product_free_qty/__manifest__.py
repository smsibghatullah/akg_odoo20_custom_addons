{
    'name': 'POS Product Info - Free Quantity',
    'version': '20.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Show Free to Use Quantity (Free Qty) per warehouse in the POS Product Information popup',
    'description': """
POS Product Info - Free Quantity
=================================

Adds a **Free Qty** column to the *Inventory* section of the Product
Information popup in Point of Sale (the popup you open by clicking the
info "i" icon next to a product on the POS screen).

Free Qty = On Hand Quantity - Reserved Quantity, i.e. the same
"Free to Use Quantity" shown on the product form and in the
Replenishment wizard (stock.replenishment.option).

It is computed per warehouse, exactly like the existing "Units
available" and "forecasted" columns, so cashiers can see at a glance
how much stock is actually free to sell in each warehouse.

Compatibility
-------------
Built and tested against Odoo 17.0 Point of Sale. If you are on a
different Odoo version, the asset bundle name in __manifest__.py
('point_of_sale._assets_pos') and/or the CSS classes used in the XML
xpath may need small adjustments -- see the comments in
static/src/xml/product_info_popup.xml.
""",
    'author': 'Custom Development',
    'depends': ['point_of_sale', 'stock'],
    'data': [],
    'assets': {
        'point_of_sale.assets': [
            'pos_product_free_qty/static/src/xml/product_info_popup.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
