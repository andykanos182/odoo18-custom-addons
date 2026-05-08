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

    # POST: Refund transaction
    'refund': '/orders/v1/refund',

    # POST: Void unsettled transaction
    'void': '/orders/v1/void',
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

# ==========================================
# PAYMENT METHOD CODES MAPPING (Odoo -> DOKU)
# ==========================================
# Maps Odoo core payment method codes to DOKU API's expected payment_method_types
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

# The codes of the Odoo payment methods to activate when DOKU is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    'qris',
    'bank_bca',
    'mandiri',
    'bank_permata',
    'bni',
    'bri',
    'cimb_niaga',
    'ovo',
    'dana',
    'shopeepay',
    'kredivo',
    'akulaku',
    'card',
}

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
# Will be verified against webhook documentation in Phase 4

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
# DOKU primarily supports Indonesian Rupiah for Indonesian merchants

SUPPORTED_CURRENCIES = ['IDR']
DEFAULT_CURRENCY = 'IDR'
SUPPORTED_COUNTRIES = ['ID']


# ==========================================
# REQUEST/RESPONSE CONFIGURATION
# ==========================================

# API request timeout (seconds)
API_TIMEOUT = 30

# Request retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2

# Default payment expiry (minutes)
# Range: 1 to 999999 (max length 6 digits per DOKU spec)
DEFAULT_PAYMENT_EXPIRY = 60
MIN_PAYMENT_EXPIRY = 1
MAX_PAYMENT_EXPIRY = 999999


# ==========================================
# DOKU REQUEST BODY CONSTRAINTS (from official docs)
# ==========================================

# Field max lengths (per DOKU specification)
MAX_LENGTH = {
    'invoice_number': 64,        # 30 if Credit Card is enabled (acquirer limit)
    'invoice_number_cc': 30,     # When Credit Card is in payment method
    'amount': 12,                # Max 12 digits (no decimal)
    'currency': 3,               # ISO 4217
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
# Endpoint paths (Odoo controller routes)

WEBHOOK_NOTIFICATION_URL = '/payment/doku/webhook'
WEBHOOK_RETURN_URL = '/payment/doku/return'

# Maximum webhook retry attempts
MAX_WEBHOOK_RETRIES = 5


# ==========================================
# SIGNATURE GENERATION (HMAC-SHA256)
# ==========================================
# Format: "HMACSHA256=" + base64(HMAC-SHA256(secret_key, signature_string))
# Detailed implementation will be done in Phase 3

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
