# -*- coding: utf-8 -*-
{
    'name': 'DOKU Payment Gateway',
    'version': '18.0.1.0.0',
    'category': 'MyCustom/Modules',
    'sequence': 350,
    'summary': 'Payment Provider: DOKU Checkout (QRIS, Virtual Account, E-wallet)',
    'description': """
DOKU Payment Gateway Integration for Odoo 18
=============================================

This module integrates DOKU Payment Gateway with Odoo 18 using DOKU Checkout (Hosted Page).

Supported Payment Methods:
--------------------------
* QRIS (Quick Response Code Indonesian Standard)
* Virtual Account (BCA, BRI, Mandiri, BNI, Permata, etc.)
* E-Wallet (OVO, DANA, ShopeePay, LinkAja, DOKU Wallet)

Features:
---------
* DOKU Checkout (Hosted Payment Page) with Pop-up Overlay
* HMAC-SHA256 signature verification (incoming & outgoing)
* Sandbox & Production mode
* Webhook notification handler with idempotency
* Auto-reconciliation with invoice
* Auto-confirmation of sale orders
* Cron job for status sync
* Auto-expire old pending transactions
* Transaction logging & audit trail
* Multi-currency support (IDR primary)

DOKU Dashboard URLs:
--------------------
* Sandbox (Testing): https://sandbox.doku.com/bo/login
* Production (Live): https://dashboard.doku.com/bo/dashboard

DOKU Developer Documentation:
-----------------------------
* Main Docs: https://developers.doku.com
* DOKU Checkout Guide: https://developers.doku.com/accept-payments/doku-checkout
* Payment Simulator: https://sandbox.doku.com/integration/simulator/

Author: Andyka
""",
    'author': 'Andyka',
    'website': 'https://www.doku.com',
    'license': 'LGPL-3',
    'depends': [
        'payment',
        'account',
        'sale',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Views & Templates (Loaded first so data records can reference them)
        'views/payment_doku_templates.xml',

        # Data
        'data/payment_provider_data.xml',
        'data/ir_cron_data.xml',

        # Views
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'views/doku_menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'external_dependencies': {
        'python': ['requests'],
    },
    'images': ['static/description/icon.png'],
}
