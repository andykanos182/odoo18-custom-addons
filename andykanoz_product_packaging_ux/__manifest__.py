# -*- coding: utf-8 -*-
{
    'name': 'AProduct Packaging UX',
    'version': '18.0.1.0.0',
    'category': 'MyCustom/Inventory',
    'summary': 'Enhanced UX for Product Packagings (Editable Tree, Mobile Kanban, Inline Tab)',
    'description': """
Product Packaging UX
====================
Enhances the product packaging management:
- Adds an inline "Packagings" tab in the Product Template form for quick data entry.
- Makes the Product Packaging tree view editable (bottom).
- Adds a Kanban view for Product Packaging, which is more mobile-friendly.
- Integrates the barcode camera widget from `andykanoz_product_checker` for easy scanning.
    """,
    'author': 'Andykanoz',
    'depends': [
        'product',
        'andykanoz_product_checker',  # Dependency to use the barcode_camera widget
    ],
    'data': [
        'views/product_packaging_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
