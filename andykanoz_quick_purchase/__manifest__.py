# -*- coding: utf-8 -*-
{
    'name': 'AndykaNoz Quick Purchase Entry',
    'version': '18.0.5.0.0',
    'summary': 'Scanner-friendly fast purchase order entry for single-vendor sessions',
    'description': """
Quick Purchase Entry
====================
A dedicated single-page UI for entering purchase orders quickly with a
barcode scanner. Built for the Gopokaja workflow where one shopping trip =
one vendor (e.g. Indogrosir).

Features
--------
* Single-vendor session, locked after first line
* Big barcode/SKU/name input, auto-focused for scanner workflow
* Scan again = qty +1 (no duplicate rows)
* Auto-fill price from last purchase from this vendor
  (fallback: seller_ids -> standard_price)
* Per-line discount in nominal Rupiah (auto-converted to %)
* Quick-Create Product modal with 6 fields when barcode unknown
* "Create Purchase Order" generates a draft PO and opens it for review

Author: Andyka for Gopokaja
Helped By Claude & Gemini
    """,
    'author': 'Andyka (Gopokaja)',
    'website': 'https://www.gopokaja.com',
    'category': 'MyCustom/Modules',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'purchase',
        'product',
        'uom',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/quick_purchase_action.xml',
        'views/quick_purchase_menu.xml',
        'views/purchase_order_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'andykanoz_quick_purchase/static/src/scss/quick_purchase.scss',
            'andykanoz_quick_purchase/static/src/js/quick_purchase.js',
            'andykanoz_quick_purchase/static/src/xml/quick_purchase.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
