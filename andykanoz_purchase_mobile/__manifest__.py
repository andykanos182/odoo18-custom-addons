# -*- coding: utf-8 -*-
{
    'name': 'AndykaNoz - Purchase Mobile',
    'version': '18.0.1.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Mobile-first Purchase Order entry for Gopokaja',
    'description': """
Purchase Mobile
===============

Mobile-optimized Purchase Order entry page built as a standalone OWL client
application, installable as a Progressive Web App (PWA).

Phase 1 (Skeleton):
 * Menu entry "Purchase Mobile" under Purchase root
 * Standalone page at /andykanoz_purchase_mobile/app
 * Custom sequence MP00001+ for mobile-originated POs

Phase 2 (Backend Foundation):
 * Models: x_created_via_mobile (purchase.order),
          x_expected_expiry_date (purchase.order.line),
          x_requires_expiry (product.template)
 * JSON-RPC endpoints: vendors, products/search, pos/list, po/get
 * Config parameter: expiry_warning_days (default 60)
 * Graceful fallback when product_expiry module is not installed

Phase 3 (OWL Bootstrap):
 * Dedicated asset bundle 'andykanoz_purchase_mobile.assets_app'
 * Root OWL component PurchaseMobileApp (mounted on #app)
 * VendorPicker component (custom autocomplete, mousedown pattern)
 * POList component (read-only browse of draft POs)
 * Shared RPC service for JSON-RPC calls
 * SCSS stylesheet with pm-* prefix namespacing

Planned in later phases:
 * Card-based Line Items: photo, qty, UoM, packaging, unit price, expiry
 * Camera barcode scanning (BarcodeDetector API)
 * Hybrid expiry date handling (integrates with product_expiry)
 * Full PWA install flow (manifest + service worker)
""",
    'author': 'Andykanoz (Gopokaja)',
    'website': 'https://www.gopokaja.com',
    'depends': [
        'base',
        'purchase',
        'stock',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/ir_config_parameter.xml',
        'views/purchase_mobile_templates.xml',
        'views/purchase_mobile_action.xml',
        'views/purchase_mobile_menu.xml',
    ],
    'assets': {
        # Extend the standard frontend bundle directly.
        #
        # The monkey-patch that fixes the DuplicatedKeyError crash is in
        # `purchase_mobile_app.js` (top-of-file side effect), so no
        # separate pre-load file is needed. Listing order is the order
        # files appear in the bundle; Odoo loader resolves module
        # factories by dependency topology at runtime, so this order
        # only matters for the embedded side-effect patch.
        'web.assets_frontend': [
            'andykanoz_purchase_mobile/static/src/scss/**/*.scss',
            'andykanoz_purchase_mobile/static/src/js/services/**/*.js',
            'andykanoz_purchase_mobile/static/src/js/components/**/*.js',
            'andykanoz_purchase_mobile/static/src/js/purchase_mobile_app.js',
            'andykanoz_purchase_mobile/static/src/js/main.js',
            'andykanoz_purchase_mobile/static/src/xml/**/*.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
