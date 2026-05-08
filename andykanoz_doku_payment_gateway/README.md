# DOKU Payment Gateway for Odoo 18

[![Version](https://img.shields.io/badge/version-18.0.1.0.0-blue.svg)]()
[![License](https://img.shields.io/badge/license-LGPL--3-green.svg)]()
[![Status](https://img.shields.io/badge/status-PRODUCTION%20READY%20%E2%9C%85-success.svg)]()

DOKU Payment Gateway integration for Odoo 18 using **DOKU Checkout (Hosted Page)**.

## 🎉 Module Status: COMPLETE!

All 5 phases are done. Ready for sandbox testing & production deployment.

| Phase | Status |
|-------|--------|
| Phase 1: Foundation Setup | ✅ DONE |
| Phase 2: Payment Methods | ✅ DONE |
| Phase 3: API Integration | ✅ DONE |
| Phase 4: Webhooks & Reconciliation | ✅ DONE |
| Phase 5: Polish & Production Ready | ✅ DONE |

## ✨ Features

### Payment Methods
- ✅ **QRIS** - Quick Response Code Indonesian Standard
- ✅ **Virtual Account** - 13 banks (BCA, BRI, Mandiri, BNI, Permata, CIMB, BSI, Danamon, BTN, Maybank, Sinarmas, BNC, DOKU)
- ✅ **E-Wallet** - OVO, DANA, ShopeePay, LinkAja, DOKU Wallet

### Core Features
- 🔒 Secure DOKU Checkout (Hosted Page) with **Pop-up overlay**
- 🔐 **HMAC-SHA256 signature** verification (incoming & outgoing)
- 🌐 Sandbox & Production environments
- 🔔 **Verified webhook** handler with idempotency
- 💰 **Auto-reconciliation** with invoices
- 🛒 **Auto-confirmation** of sale orders
- 📊 Comprehensive transaction logging & audit trail
- 🛡️ Amount validation (security check)

### Phase 5 Additions
- ⏰ **Cron job**: Auto-check pending transactions every 15 min
- 🗓️ **Cron job**: Auto-expire old pending transactions every hour
- 📋 **Dedicated menu**: "DOKU Payment → Transactions" with filters
- 🔄 **Manual sync**: "Check Status" button on transaction form
- 📈 **Reporting**: Group by status, method, acquirer, customer
- 🚀 **Production deployment guide** included

## 📁 Module Structure

```
andykanoz_doku_payment_geteway/
├── __init__.py
├── __manifest__.py
├── const.py                        # API endpoints, payment codes
├── hooks.py                        # Install/uninstall hooks
├── README.md                       # This file
├── TESTING_GUIDE.md                # Sandbox testing guide
├── PRODUCTION_DEPLOYMENT.md        # Production deployment guide
│
├── models/
│   ├── payment_provider.py        # DOKU provider config
│   └── payment_transaction.py     # Transaction + webhook + cron
│
├── controllers/
│   └── main.py                     # Webhook with signature verify
│
├── views/
│   ├── payment_provider_views.xml  # Configuration UI
│   ├── payment_transaction_views.xml
│   ├── payment_doku_templates.xml  # Pop-up overlay frontend
│   └── doku_menu_views.xml         # DOKU Payment menu
│
├── data/
│   ├── payment_provider_data.xml
│   └── ir_cron_data.xml            # Scheduled jobs
│
├── security/
│   └── ir.model.access.csv
│
└── utils/
    ├── signature.py                # HMAC-SHA256 sign + verify
    └── api_client.py               # DOKU API wrapper
```

## 🚀 Quick Start

### 1. Installation
```bash
docker compose restart odoo18
```
Then in Odoo: **Apps → DOKU Payment Gateway → Upgrade**

### 2. Configuration
**Accounting → Configuration → Payment Providers → DOKU**
- Environment: Sandbox
- Fill in Merchant Code, Client ID, Secret Key
- Enable payment methods
- State: Test Mode

### 3. Set Webhook URL in DOKU Dashboard
```
Notification URL: https://nitro.gopokaja.com/payment/doku/webhook
Return URL: https://nitro.gopokaja.com/payment/doku/return
```

### 4. Test
See **TESTING_GUIDE.md** for detailed test scenarios.

### 5. Go Live
See **PRODUCTION_DEPLOYMENT.md** for production deployment.

## 📚 Documentation

- 📘 [Testing Guide](TESTING_GUIDE.md) - Complete sandbox testing scenarios
- 🚀 [Production Deployment](PRODUCTION_DEPLOYMENT.md) - Step-by-step prod deploy
- 📋 [Phase 1-3 Testing](PHASE_3_TESTING.md) - Earlier phase testing notes

## 📚 Official DOKU References

- [DOKU Checkout](https://developers.doku.com/accept-payments/doku-checkout)
- [Backend Integration](https://developers.doku.com/accept-payments/doku-checkout/integration-guide/backend-integration)
- [Frontend Integration](https://developers.doku.com/accept-payments/doku-checkout/integration-guide/frontend-integration)
- [Signature Generation](https://developers.doku.com/get-started-with-doku-api/signature-component/non-snap/signature-component-from-request-header)
- [Webhook Best Practices](https://jokul.doku.com/docs/docs/http-notification/http-notification-best-practice/)
- [DOKU Sandbox Demo](https://sandbox.doku.com/demo/checkout-api)
- [Payment Simulator](https://sandbox.doku.com/integration/simulator/)

## 🔐 Security Features

| Feature | Status |
|---------|--------|
| HMAC-SHA256 signature on outgoing requests | ✅ |
| HMAC-SHA256 verification on incoming webhooks | ✅ |
| Constant-time signature comparison (anti timing attack) | ✅ |
| Amount validation (anti tampering) | ✅ |
| Client-Id verification | ✅ |
| Idempotent webhook processing | ✅ |
| Secret Key encrypted in database | ✅ |
| Sensitive data masked in logs | ✅ |

## 👤 Author

Andyka

## 📝 License

LGPL-3

---

**Module Version**: 18.0.1.0.0
**Last Updated**: April 30, 2026
**Status**: Production Ready ✅
