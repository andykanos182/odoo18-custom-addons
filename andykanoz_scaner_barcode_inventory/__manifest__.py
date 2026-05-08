{
    'name': 'Andykanoz Inventory Barcode Scanner',
    'version': '1.0',
    'category': 'MyCustom/Modules',
    'summary': 'Add camera barcode scanner button to product barcode field',
    'description': """
        This module adds a camera icon button next to the barcode field in the product form.
        Clicking the button opens a camera scanner to scan barcodes directly into the field.
    """,
    'author': 'Andyka',
    'depends': ['product', 'stock'],
    'data': [
        'views/product_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'andykanoz_scaner_barcode_inventory/static/src/js/barcode_scanner_field.js',
            'andykanoz_scaner_barcode_inventory/static/src/xml/barcode_scanner_field.xml',
            'andykanoz_scaner_barcode_inventory/static/src/scss/barcode_scanner.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
