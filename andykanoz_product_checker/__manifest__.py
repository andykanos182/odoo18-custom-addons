# -*- coding: utf-8 -*-
{
    'name': 'Andykanoz - Product Checker',
    'version': '18.0.1.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Scan & check product availability, price, and stock',
    'description': """
Product Checker
===============
A dedicated backend page to scan/search products and view:
- Large product image
- Cost & Sales Price (with pricelist selection)
- Stock on hand
- Category & Ecommerce info

If product not found, offers quick-create form.
    """,
    'author': 'Andyka',
    'depends': [
        'base',
        'product',
        'stock',
        'website_sale',
        'point_of_sale',
        'andykanoz_gemini_integration_auto_edit',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_checker_views.xml',
        'views/product_checker_menu.xml',
        'views/product_template_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'andykanoz_product_checker/static/src/js/zxing_barcode_polyfill.js',
            'andykanoz_product_checker/static/src/js/product_checker.js',
            'andykanoz_product_checker/static/src/js/product_titlecase_button.js',
            'andykanoz_product_checker/static/src/js/barcode_camera_widget.js',
            'andykanoz_product_checker/static/src/xml/product_checker.xml',
            'andykanoz_product_checker/static/src/xml/barcode_camera_widget.xml',
            'andykanoz_product_checker/static/src/scss/product_checker.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
