{
    'name': 'POS Product Price on Tile',
    'version': '20.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Show the product price on every POS product tile',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_price_display/static/src/product_card_price.js',
            'pos_product_price_display/static/src/product_card_price.xml',
            'pos_product_price_display/static/src/product_card_price.scss',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
