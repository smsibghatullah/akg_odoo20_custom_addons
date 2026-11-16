{
    'name': 'POS Product Price on Tile',
    'version': '20.0.1.5.0',
    'category': 'Point of Sale',
    'summary': 'Show the product price on every POS product tile',
    'depends': ['point_of_sale', 'account_edi_ubl_cii', 'purchase_stock', 'pos_sale_stock', 'stock_landed_costs'],
    'data': [
        'security/ir.access.csv',
        'data/fix_analytic_plan_columns.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_price_display/static/src/product_card_price.js',
            'pos_product_price_display/static/src/product_card_price.xml',
            'pos_product_price_display/static/src/product_card_price.scss',
            'pos_product_price_display/static/src/pos_settle_so_fix.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
