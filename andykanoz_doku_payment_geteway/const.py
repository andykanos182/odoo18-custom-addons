# -*- coding: utf-8 -*-
"""
Constants for DOKU Payment Gateway integration.

All values verified against official DOKU documentation:
https://developers.doku.com/accept-payments/doku-checkout

Last verified: April 30, 2026
"""

# ==========================================
# DOKU API ENDPOINTS (Official)
# ==========================================
# Source: https://developers.doku.com/accept-payments/doku-checkout/integration-guide/backend-integration

DOKU_API_URLS = {
    'sandbox': 'https://api-sandbox.doku.com',
    'production': 'https://api.doku.com',
}

# DOKU Checkout (Hosted Page) endpoints
DOKU_ENDPOINTS = {
    # POST: Create payment & get payment.url
    'create_payment': '/checkout/v1/payment',

    # GET: Check transaction status
    # Will be updated in Phase 3 with correct endpoint from official docs
    'check_status': '/orders/v1/status/{invoice_number}',

    # POST: Refund transaction (Credit Card only)
    # Reference: https://developers.doku.com/accept-payments/direct-api/non-snap/cards/refund
    'refund_credit_card': '/cancellation/credit-card/refund',

    # NOTE: There is NO generic "Void Hosted Checkout" endpoint.
    # For DOKU Checkout (Hosted Page), the session auto-expires after
    # `payment.payment_due_date` minutes. We just mark the Odoo transaction
    # as cancelled and let DOKU's session expire naturally.
}

# Frontend JS library URL (still uses 'jokul' branding from DOKU's previous name)
DOKU_FRONTEND_JS = {
    'sandbox': 'https://sandbox.doku.com/jokul-checkout-js/v1/jokul-checkout-1.0.0.js',
    'production': 'https://checkout.doku.com/jokul-checkout-js/v1/jokul-checkout-1.0.0.js',
}


# ==========================================
# PAYMENT METHOD CODES (Official from DOKU)
# ==========================================
# Source: DOKU Backend Integration documentation
# These are the EXACT codes accepted by DOKU API in payment.payment_method_types

# QRIS
PAYMENT_CODE_QRIS = 'QRIS'

# Virtual Accounts (Bank Transfer)
PAYMENT_CODES_VIRTUAL_ACCOUNT = [
    'VIRTUAL_ACCOUNT_BCA',
    'VIRTUAL_ACCOUNT_BANK_MANDIRI',
    'VIRTUAL_ACCOUNT_BANK_SYARIAH_MANDIRI',
    'VIRTUAL_ACCOUNT_BRI',
    'VIRTUAL_ACCOUNT_BNI',
    'VIRTUAL_ACCOUNT_BANK_PERMATA',
    'VIRTUAL_ACCOUNT_BANK_CIMB',
    'VIRTUAL_ACCOUNT_BANK_DANAMON',
    'VIRTUAL_ACCOUNT_DOKU',
    'VIRTUAL_ACCOUNT_BNC',
    'VIRTUAL_ACCOUNT_BTN',
    'VIRTUAL_ACCOUNT_MAYBANK',
    'VIRTUAL_ACCOUNT_SINARMAS',
]

# E-Wallets
PAYMENT_CODES_EWALLET = [
    'EMONEY_OVO',
    'EMONEY_DANA',
    'EMONEY_SHOPEEPAY',
    'EMONEY_LINKAJA',
    'EMONEY_DOKU',
]

# Credit Card
PAYMENT_CODE_CREDIT_CARD = 'CREDIT_CARD'

# Direct Debit
PAYMENT_CODES_DIRECT_DEBIT = [
    'DIRECT_DEBIT_BRI',
    'DIRECT_DEBIT_CIMB',
    'DIRECT_DEBIT_ALLO',
]

# Convenience Store (Online to Offline)
PAYMENT_CODES_CONVENIENCE_STORE = [
    'ONLINE_TO_OFFLINE_ALFA',      # Alfamart
    'ONLINE_TO_OFFLINE_INDOMARET',  # Indomaret
]

# Peer-to-Peer / Pay Later
PAYMENT_CODES_PAYLATER = [
    'PEER_TO_PEER_AKULAKU',
    'PEER_TO_PEER_KREDIVO',
    'PEER_TO_PEER_INDODANA',
]

# Other channels
PAYMENT_CODES_OTHER = [
    'JENIUS_PAY',
    'OCTO_CLICKS',
    'EPAY_BRI',
    'KLIKPAY_BCA',
    'PERMATA_NET',
    'DANAMON_ONLINE_BANKING',
]

# Bank display names for UI dropdown (VA payment methods)
VA_BANK_DISPLAY = {
    'VIRTUAL_ACCOUNT_BCA': 'BCA',
    'VIRTUAL_ACCOUNT_BANK_MANDIRI': 'Mandiri',
    'VIRTUAL_ACCOUNT_BANK_SYARIAH_MANDIRI': 'Mandiri Syariah',
    'VIRTUAL_ACCOUNT_BRI': 'BRI',
    'VIRTUAL_ACCOUNT_BNI': 'BNI',
    'VIRTUAL_ACCOUNT_BANK_PERMATA': 'Permata',
    'VIRTUAL_ACCOUNT_BANK_CIMB': 'CIMB Niaga',
    'VIRTUAL_ACCOUNT_BANK_DANAMON': 'Danamon',
    'VIRTUAL_ACCOUNT_DOKU': 'DOKU',
    'VIRTUAL_ACCOUNT_BNC': 'BNC',
    'VIRTUAL_ACCOUNT_BTN': 'BTN',
    'VIRTUAL_ACCOUNT_MAYBANK': 'Maybank',
    'VIRTUAL_ACCOUNT_SINARMAS': 'Sinarmas',
}

# E-Wallet display names for UI dropdown
EWALLET_DISPLAY = {
    'EMONEY_OVO': 'OVO',
    'EMONEY_DANA': 'DANA',
    'EMONEY_SHOPEEPAY': 'ShopeePay',
    'EMONEY_LINKAJA': 'LinkAja',
    'EMONEY_DOKU': 'DOKU Wallet',
}


# ==========================================
# DOKU PAYMENT STATUS MAPPING
# ==========================================
# Maps DOKU notification statuses to Odoo payment.transaction states

PAYMENT_STATUS_MAPPING = {
    # Success statuses → Odoo 'done'
    'success': 'done',
    'paid': 'done',
    'settled': 'done',
    'SUCCESS': 'done',

    # Pending statuses → Odoo 'pending'
    'pending': 'pending',
    'PENDING': 'pending',

    # Failed statuses → Odoo 'error'
    'failed': 'error',
    'FAILED': 'error',

    # Cancelled / Expired → Odoo 'cancel'
    'expired': 'cancel',
    'EXPIRED': 'cancel',
    'cancelled': 'cancel',
    'CANCELLED': 'cancel',
    'voided': 'cancel',
    'VOIDED': 'cancel',
    'refunded': 'cancel',
    'REFUNDED': 'cancel',
}


# ==========================================
# CURRENCY & COUNTRY
# ==========================================
SUPPORTED_CURRENCIES = ['IDR']
DEFAULT_CURRENCY = 'IDR'
SUPPORTED_COUNTRIES = ['ID']


# ==========================================
# DEFAULT PAYMENT METHOD CODES (Odoo Core)
# ==========================================
# Lowercase string codes that match `payment.method.code` records in Odoo 18 core.
# These are auto-linked to the DOKU provider via setup_provider() helper
# called in post_init_hook. (Pattern from payment_xendit module.)
#
# IMPORTANT: Naming is INCONSISTENT in Odoo core:
#   - Some banks use 'bank_' prefix: bank_bca, bank_permata
#   - Others don't: mandiri, bni, bri, cimb_niaga
# These codes MUST exactly match existing payment.method records.

DEFAULT_PAYMENT_METHOD_CODES = {
    # QRIS (Bank Indonesia QR standard)
    'qris',

    # Bank Transfer / Virtual Account
    'bank_bca',
    'mandiri',
    'bank_permata',
    'bni',
    'bri',
    'cimb_niaga',

    # E-Wallet
    'ovo',
    'dana',
    'shopeepay',

    # Pay Later (BNPL)
    'kredivo',
    'akulaku',

    # Credit/Debit Card (generic)
    'card',
}

# Mapping from Odoo core payment method codes to DOKU API payment method types
PAYMENT_METHODS_MAPPING = {
    'qris': 'QRIS',
    'bank_bca': 'VIRTUAL_ACCOUNT_BCA',
    'mandiri': 'VIRTUAL_ACCOUNT_BANK_MANDIRI',
    'bank_permata': 'VIRTUAL_ACCOUNT_BANK_PERMATA',
    'bni': 'VIRTUAL_ACCOUNT_BNI',
    'bri': 'VIRTUAL_ACCOUNT_BRI',
    'cimb_niaga': 'VIRTUAL_ACCOUNT_BANK_CIMB',
    'ovo': 'EMONEY_OVO',
    'dana': 'EMONEY_DANA',
    'shopeepay': 'EMONEY_SHOPEEPAY',
    'kredivo': 'PEER_TO_PEER_KREDIVO',
    'akulaku': 'PEER_TO_PEER_AKULAKU',
    'card': 'CREDIT_CARD',
}


# ==========================================
# REQUEST/RESPONSE CONFIGURATION
# ==========================================
API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2

# Default payment expiry (minutes)
DEFAULT_PAYMENT_EXPIRY = 60
MIN_PAYMENT_EXPIRY = 1
MAX_PAYMENT_EXPIRY = 999999


# ==========================================
# DOKU REQUEST BODY CONSTRAINTS (from official docs)
# ==========================================
MAX_LENGTH = {
    'invoice_number': 64,        # 30 if Credit Card is enabled (acquirer limit)
    'invoice_number_cc': 30,
    'amount': 12,
    'currency': 3,
    'language': 2,
    'customer_id': 50,
    'customer_name': 255,
    'customer_last_name': 16,
    'customer_email': 128,
    'customer_phone': 16,
    'customer_address': 400,
    'request_id': 128,
    'line_item_name': 255,
    'line_item_id': 64,
}


# ==========================================
# WEBHOOK / NOTIFICATION
# ==========================================
WEBHOOK_NOTIFICATION_URL = '/payment/doku/webhook'
WEBHOOK_RETURN_URL = '/payment/doku/return'

# Custom Pending Payment Page (Strategy 2 - Semi Tokopedia)
PENDING_PAYMENT_URL = '/payment/doku/pending'
CANCEL_PAYMENT_URL = '/payment/doku/cancel'

MAX_WEBHOOK_RETRIES = 5


# ==========================================
# SIGNATURE GENERATION (HMAC-SHA256)
# ==========================================
SIGNATURE_ALGORITHM = 'HMACSHA256'
SIGNATURE_PREFIX = 'HMACSHA256='


# ==========================================
# REFERENCES (Official Documentation)
# ==========================================
DOCS_URLS = {
    'main': 'https://developers.doku.com/accept-payments/doku-checkout',
    'backend_integration': 'https://developers.doku.com/accept-payments/doku-checkout/integration-guide/backend-integration',
    'frontend_integration': 'https://developers.doku.com/accept-payments/doku-checkout/integration-guide/frontend-integration',
    'simulate_payment': 'https://developers.doku.com/accept-payments/doku-checkout/integration-guide/simulate-payment-and-notification',
    'signature': 'https://developers.doku.com/accept-payments/get-started-with-doku-api/signature-component/non-snap/signature-component-from-request-header',
    'supported_payment_methods': 'https://developers.doku.com/accept-payments/doku-checkout/supported-payment-methods',
    'demo': 'https://sandbox.doku.com/demo/checkout-api',
}
