# -*- coding: utf-8 -*-
{
    'name': 'Andykanoz - Product Internal Reference Generator',
    'version': '1.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Generates unique internal reference for new products.',
    'description': 'This module automatically generates a unique internal reference '
                   'for products when they are created, filling the default_code field.',
    'author': 'Andyka', # Ganti dengan nama Anda
    'website': 'https://www.gopokaja.com', # Ganti dengan website Anda
    'depends': ['product'],
    'data': [
        'data/product_sequence.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
