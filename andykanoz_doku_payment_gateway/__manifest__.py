# -*- coding: utf-8 -*-
{
    'name': 'DOKU Payment Gateway',
    'version': '18.0.1.0.2',
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
* DOKU Checkout (Hosted Payment Page) with full redirect
* Tokopedia-style Pending Payment Page (Strategy 2)
* Live countdown timer to expiry
* Cancel Pending Payment from customer portal
* Auto-cancel pending DOKU transactions when the related sale order is cancelled
  (closes the customer-facing pending payment so the SO cancellation is reflected
  end-to-end; DOKU Checkout session will still expire naturally per Payment Expiry
  config since DOKU has no void-session API for Hosted Checkout)
* Orphan payment detection: if a SUCCESS webhook arrives for an already-cancelled
  sale order (race condition between SO cancel and DOKU session expiry), the
  transaction is logged at ERROR level and a prominent warning message is posted
  to both the transaction and sale order chatter, prompting admin to issue a
  manual refund via the DOKU Dashboard
* HMAC-SHA256 signature verification (incoming & outgoing)
* Sandbox & Production mode
* Webhook notification handler with idempotency
* Auto-reconciliation with invoice
* Auto-confirmation of sale orders
* Cron job for status sync
* Auto-expire old pending transactions
* Transaction logging & audit trail

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
        'account_payment', # For invoice portal payment inheritance
        'sale',     # For sale_order_portal_template inheritance
        'portal',   # For portal layout
        'website_sale', # For eCommerce checkout inheritance
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
        'views/portal_templates.xml',
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
