# 🎓 SKILL: DOKU Dynamic QRIS for Odoo 18 POS

> **Use case**: Implementing Dynamic QRIS as a POS payment method in Odoo 18 — cashier-initiated, customer-scans-on-screen flow, with real-time payment confirmation via polling + webhook reconciliation.
>
> **Module target**: `andykanoz_doku_payment_geteway` (existing module — POS feature to be added)
>
> **Companion skills** (read in order):
> 1. [`XENDIT_PAYMENT_PROVIDER_PATTERN.md`](./XENDIT_PAYMENT_PROVIDER_PATTERN.md) — generic Odoo 18 payment provider patterns (web)
> 2. [`DOKU_DEVELOPMENT_SKILL.md`](./DOKU_DEVELOPMENT_SKILL.md) — DOKU API + workflow conventions
> 3. **THIS FILE** — POS-specific Dynamic QRIS pattern
>
> **Reference implementation**: Odoo's `pos_paytm` module at `D:\MyServer\Odoo18\Source Code Odoo18\pos_paytm\` is the canonical pattern for dynamic-QR-based POS payments. PayTM (India) and DOKU QRIS (Indonesia) share nearly identical UX: cashier triggers QR generation → customer scans → backend polls payment status. **Study `pos_paytm` first** — this skill is essentially "pos_paytm adapted for DOKU".

---

## 📑 Contents

1. [Strategic Overview](#-section-1-strategic-overview)
2. [DOKU SNAP API for QRIS](#-section-2-doku-snap-api-for-qris)
3. [Odoo 18 POS Payment Architecture](#-section-3-odoo-18-pos-payment-architecture)
4. [Module File Structure](#-section-4-module-file-structure)
5. [Backend Implementation](#-section-5-backend-implementation)
6. [Frontend Implementation](#-section-6-frontend-implementation)
7. [Payment Flow & Polling](#-section-7-payment-flow--polling)
8. [Webhook Handling](#-section-8-webhook-handling)
9. [UX & Display Considerations](#-section-9-ux--display-considerations)
10. [Testing Approach](#-section-10-testing-approach)
11. [Critical Gotchas](#-section-11-critical-gotchas)
12. [Implementation Checklist](#-implementation-checklist)
13. [References](#-references)

---

## 🎯 Section 1: Strategic Overview

### 1.1 Why Dynamic QRIS (Not Static) for POS

| Criterion | Static QRIS | Dynamic QRIS | Winner for POS |
|-----------|-------------|--------------|----------------|
| Amount handling | Customer types amount | Pre-filled by system | ✅ Dynamic |
| Per-transaction tracking | ❌ Cannot match payment to order | ✅ Unique reference per QR | ✅ Dynamic |
| Cashier workflow | Manual reconciliation needed | Auto-reconcile via webhook | ✅ Dynamic |
| Use case fit | Self-service tip jar | Restaurant/retail counter | ✅ Dynamic |

**Conclusion**: F&B operations like Gopokaja **must** use Dynamic QRIS to match payments to specific POS orders. Static QRIS is for fixed-amount or self-determined-amount scenarios that don't need order-level reconciliation.

---

### 1.2 Why Direct API (Not DOKU Checkout) for POS

DOKU provides three QRIS integration paths:

| Path | Best For | POS Suitability |
|------|----------|-----------------|
| **Payment Link** (no-integration) | Email/WhatsApp invoicing | ❌ Manual link sharing |
| **DOKU Checkout** (hosted page) | Web e-commerce | ❌ Redirects user away from POS |
| **Direct API (SNAP)** | Custom front-ends, **POS systems** | ✅ Full control over UX |

DOKU's own documentation states:
> *"Direct API is ideal for businesses with custom front-end environments or POS systems that require full control over the checkout experience."*

For POS, we need:
- QR rendered ON the POS screen (or customer-facing display)
- No browser redirect
- Real-time payment confirmation
- Cashier ability to cancel/retry
- → **Direct API is the only fit**

---

### 1.3 The Reference Pattern: `pos_paytm`

PayTM is India's QR-based payment leader. Their Odoo integration (`pos_paytm`) solves the exact same UX problem we have with QRIS:

1. Cashier confirms order amount
2. Backend calls payment provider API → gets QR code
3. POS displays QR on screen
4. Customer scans with their phone
5. POS polls payment status every 5 seconds
6. On success → finalize order
7. On cancel/timeout → retry option

**This skill mirrors `pos_paytm`'s structure 1:1**, with DOKU SNAP API substituted for PayTM's API.

---

## 🌐 Section 2: DOKU SNAP API for QRIS

> ⚠️ **CRITICAL**: DOKU has TWO API generations. QRIS Direct API uses **SNAP (Standar Nasional Open API Pembayaran)** — Bank Indonesia's national standard — which is **DIFFERENT** from the older DOKU Checkout API. **SNAP uses HMAC-SHA512, NOT HMAC-SHA256.** Do not reuse `utils/signature.py` from the existing DOKU Checkout integration.

### 2.1 Two API Generations Compared

| Aspect | DOKU Checkout (Legacy) | DOKU SNAP (QRIS) |
|--------|------------------------|------------------|
| Auth | HMAC-SHA256 per request | HMAC-SHA512 + Bearer token |
| Token flow | None (API key in signature) | 2-step: Get Token → Use token |
| Endpoint base | `/checkout/v1/payment` | `/snap-adapter/b2b2c/v1.0/qr/...` |
| Used by | Web payment provider (existing) | POS QRIS (new — this skill) |
| Signature inputs | `Client-Id`, `Request-Id`, `Request-Timestamp`, `Request-Target`, `Digest` | `HTTPMethod`, `EndpointUrl`, `AccessToken`, body hash, `TimeStamp` |

**Implication**: Need a NEW signature module — `utils/signature_snap.py` — alongside the existing `utils/signature.py`.

---

### 2.2 SNAP Authentication Flow (2-Step)

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Get B2B Access Token                                    │
│   POST /authorization/v1/access-token/b2b                       │
│   ↓                                                             │
│   { "responseCode": "2007300", "accessToken": "Bearer xxx",     │
│     "tokenType": "Bearer", "expiresIn": "899" }                 │
│                                                                 │
│ Step 2: Generate QRIS (using token from Step 1)                 │
│   POST /snap-adapter/b2b2c/v1.0/qr/qr-mpm-payment              │
│   Headers:                                                      │
│     Authorization: Bearer <accessToken>                         │
│     X-PARTNER-ID: <Client ID>                                   │
│     X-TIMESTAMP: <ISO 8601>                                     │
│     X-EXTERNAL-ID: <unique UUID>                                │
│     X-SIGNATURE: <HMAC-SHA512>                                  │
│     CHANNEL-ID: <merchant channel>                              │
└─────────────────────────────────────────────────────────────────┘
```

**Token caching strategy**:
- Token valid ~15 min (`expiresIn: 899` seconds)
- Cache in `ir.config_parameter` with expiry timestamp
- Refresh ~60s before expiry to avoid race conditions

---

### 2.3 SNAP Signature Formula (HMAC-SHA512)

```python
import hmac
import hashlib
import base64

def snap_generate_signature(client_secret, http_method, endpoint_url,
                             access_token, request_body, timestamp):
    """
    DOKU SNAP signature for B2B2C requests.

    Formula:
      stringToSign = HTTPMethod + ":" + EndpointUrl + ":" + AccessToken + ":"
                   + Lowercase(HexEncode(SHA-256(minify(RequestBody)))) + ":"
                   + TimeStamp
      signature = Base64(HMAC-SHA512(clientSecret, stringToSign))
    """
    # Step 1: Hash the minified body with SHA-256, hex-encode, lowercase
    minified_body = json.dumps(request_body, separators=(',', ':'))
    body_hash = hashlib.sha256(minified_body.encode('utf-8')).hexdigest().lower()

    # Step 2: Build stringToSign
    string_to_sign = f"{http_method}:{endpoint_url}:{access_token}:{body_hash}:{timestamp}"

    # Step 3: HMAC-SHA512 with secret, then base64
    raw_sig = hmac.new(
        client_secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha512
    ).digest()

    return base64.b64encode(raw_sig).decode('utf-8')
```

**Verify against**: https://developers.doku.com/accept-payments/direct-api/snap/integration-guide/qris

---

### 2.4 Generate Dynamic QRIS Endpoint

**Endpoint**: `POST /snap-adapter/b2b2c/v1.0/qr/qr-mpm-payment`

**Request body**:
```json
{
  "partnerReferenceNo": "POS-{config_id}-{order_id}-{timestamp}",
  "amount": {
    "value": "10000.00",
    "currency": "IDR"
  },
  "additionalInfo": {
    "merchantId": "<MID from DOKU dashboard>",
    "terminalId": "<TID, optional>",
    "validityPeriod": "2026-05-07T15:30:00+07:00"
  }
}
```

**Key field rules**:
- `partnerReferenceNo`: must be unique per request (idempotency); max 64 chars, alphanumeric + hyphens
- `amount.value`: STRING (not number!); always 2 decimal places ("10000.00", not 10000)
- `amount.currency`: always `"IDR"` for QRIS
- `validityPeriod`: when QR expires; recommend 5-10 min for POS

**Response (success)**:
```json
{
  "responseCode": "2004800",
  "responseMessage": "Request has been processed successfully",
  "referenceNo": "DOKU-INV-2026050700001",
  "partnerReferenceNo": "POS-1-42-1715040000",
  "qrContent": "00020101021226530012COM.DOKU.WWW...6304F6EA",
  "transactionAmount": { "value": "10000.00", "currency": "IDR" },
  "additionalInfo": {
    "pointOfInitiationMethodDescription": "DYNAMIC",
    "expiredDate": "2026-05-07T15:30:00+07:00"
  }
}
```

The `qrContent` field is the EMV-format QR string. Render it as a QR image client-side using a JS library (e.g., `qrcode-generator`).

---

### 2.5 Inquiry Status Endpoint (for Polling)

**Endpoint**: `POST /snap-adapter/b2b2c/v1.0/qr/qr-mpm-query`

**Request body**:
```json
{
  "originalPartnerReferenceNo": "POS-1-42-1715040000",
  "serviceCode": "47",
  "additionalInfo": {
    "merchantId": "<MID>"
  }
}
```

**Response statuses** (in `latestTransactionStatus`):

| Code | Meaning | Map to Odoo |
|------|---------|-------------|
| `00` | SUCCESS — payment received | `done` |
| `01` | INITIATED — QR generated, not yet scanned | `pending` |
| `03` | PENDING — customer scanned, processing | `pending` |
| `06` | EXPIRED | `cancel` |
| `07` | FAILED | `error` |
| `09` | CANCELED | `cancel` |

**Polling cadence**: Every 5 seconds (matches `pos_paytm` `REQUEST_TIMEOUT = 5000`). Stop polling after success, error, cancel, or 10-minute timeout.

---

## 🏗️ Section 3: Odoo 18 POS Payment Architecture

> **Verified from**: `D:\MyServer\Odoo18\Source Code Odoo18\pos_paytm\` — official Odoo Enterprise module.

### 3.1 The Three Pillars

A POS payment terminal integration in Odoo 18 has exactly three components:

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Backend Model (Python)                                    │
│    models/pos_payment_method.py                              │
│    - Inherit pos.payment.method                              │
│    - Add provider-specific fields (credentials, config)      │
│    - Override _get_payment_terminal_selection() to add option│
│    - Add RPC methods callable from frontend                  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. Frontend Payment Interface (JS/OWL)                       │
│    static/src/js/payment_doku_qris.js                        │
│    - Extend PaymentInterface from @point_of_sale             │
│    - Implement send_payment_request(uuid)                    │
│    - Implement send_payment_cancel(order, uuid)              │
│    - Implement polling logic                                 │
│                                                              │
│    static/src/js/model.js                                    │
│    - register_payment_method("doku_qris", PaymentDokuQris)   │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. Configuration View (XML)                                  │
│    views/pos_payment_method_views.xml                        │
│    - Inherit pos_payment_method_view_form                    │
│    - xpath after use_payment_terminal field                  │
│    - Make all fields invisible/required based on selection   │
└──────────────────────────────────────────────────────────────┘
```

That's it. No POSbox, no IoT box, no terminal hardware needed for QRIS — the QR is rendered on the existing POS screen.

---

### 3.2 The `_get_payment_terminal_selection()` Extension Point

This is THE official Odoo 18 way to register a new payment terminal:

```python
# models/pos_payment_method.py
class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [
            ('doku_qris', 'DOKU QRIS')
        ]
```

After this, `('doku_qris', 'DOKU QRIS')` appears in the "Use a Payment Terminal" dropdown on the POS Payment Method form (the screen shown in your screenshot).

---

### 3.3 The `register_payment_method()` Frontend Hook

```javascript
// static/src/js/model.js
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentDokuQris } from "@andykanoz_doku_payment_geteway/js/payment_doku_qris";

register_payment_method("doku_qris", PaymentDokuQris);
```

The first argument MUST exactly match the selection key from `_get_payment_terminal_selection()`. Mismatch = silent failure (POS won't know which JS class handles your terminal).

---

### 3.4 `PaymentInterface` Lifecycle Methods

When a cashier clicks "Send" on a DOKU QRIS payment line, Odoo calls these methods in sequence:

| Method | Called When | Must Return |
|--------|-------------|-------------|
| `send_payment_request(uuid)` | Cashier clicks Send | `Promise<bool>` — true on success |
| `send_payment_cancel(order, uuid)` | Cashier clicks Cancel | `Promise<bool>` |
| `send_payment_reversal(uuid)` | Refund flow (rare for QRIS) | `Promise<bool>` |
| `set_most_recent_status(...)` | Status updates from server | (helper) |

The `paymentLine.set_payment_status(status)` controls UI state:

| Status | UI Effect |
|--------|-----------|
| `"waiting"` | Default initial state |
| `"waitingCard"` | "Waiting for card/scan" indicator |
| `"waitingCancel"` | Cancel in progress |
| `"done"` | ✅ Payment confirmed |
| `"force_done"` | ⚠️ Manually forced (escape hatch) |
| `"retry"` | Reset to allow new attempt |
| `"timeout"` | Timed out |

For DOKU QRIS, the typical sequence:
- Initial → `"waitingCard"` (show QR, polling active)
- Customer pays → `"done"` (auto-finalize)
- Customer doesn't pay / cancels → `"retry"` or `"timeout"`

---

## 📁 Section 4: Module File Structure

Add these files to the existing `andykanoz_doku_payment_geteway` module — **do not create a separate module**:

```
andykanoz_doku_payment_geteway/
├── __manifest__.py                              # MODIFY: add depends + assets
├── models/
│   ├── __init__.py                              # MODIFY: import new file
│   ├── payment_provider.py                      # (existing — web)
│   ├── payment_transaction.py                   # (existing — web)
│   ├── pos_payment_method.py                    # ✨ NEW: POS extension
│   └── pos_payment.py                           # ✨ NEW (optional): pos.payment fields
├── controllers/
│   ├── __init__.py                              # (existing)
│   ├── main.py                                  # MODIFY: add POS webhook route
│   └── portal.py                                # (existing)
├── utils/
│   ├── __init__.py                              # MODIFY
│   ├── signature.py                             # (existing — HMAC-SHA256, web)
│   ├── signature_snap.py                        # ✨ NEW: HMAC-SHA512 for SNAP
│   ├── api_client.py                            # (existing — web)
│   └── api_client_snap.py                       # ✨ NEW: SNAP API client
├── static/
│   ├── description/icon.png                     # (existing)
│   └── src/
│       ├── js/
│       │   ├── payment_doku_qris.js             # ✨ NEW: PaymentInterface
│       │   ├── model.js                         # ✨ NEW: register_payment_method
│       │   └── PaymentScreen.js                 # ✨ NEW: pending payment patch
│       ├── xml/
│       │   └── payment_doku_qris.xml            # ✨ NEW: QR display popup template
│       └── scss/
│           └── payment_doku_qris.scss           # ✨ NEW: QR popup styling
└── views/
    ├── pos_payment_method_views.xml             # ✨ NEW: form inherit
    └── (existing files unchanged)
```

**Why same module?** DOKU credentials (Client ID, Secret) are shared between web and POS. Splitting modules would require duplicate config or cross-module dependency.

---

## 🐍 Section 5: Backend Implementation

### 5.1 Manifest Updates

```python
# __manifest__.py (snippet)
{
    'name': "DOKU Payment Gateway",
    'version': '18.0.2.0.0',  # Bump major minor for POS feature
    'category': 'MyCustom/Modules',  # ← Standing rule
    'depends': [
        'payment',          # existing
        'account',          # existing
        'website_sale',     # existing
        'point_of_sale',    # ✨ NEW for POS feature
    ],
    'data': [
        # ... existing entries ...
        'views/pos_payment_method_views.xml',  # ✨ NEW
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'andykanoz_doku_payment_geteway/static/src/js/payment_doku_qris.js',
            'andykanoz_doku_payment_geteway/static/src/js/model.js',
            'andykanoz_doku_payment_geteway/static/src/js/PaymentScreen.js',
            'andykanoz_doku_payment_geteway/static/src/xml/payment_doku_qris.xml',
            'andykanoz_doku_payment_geteway/static/src/scss/payment_doku_qris.scss',
        ],
    },
}
```

**Critical**: The asset bundle name `point_of_sale._assets_pos` is fixed by Odoo — do not improvise.

---

### 5.2 `models/pos_payment_method.py` Skeleton

```python
# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..utils.api_client_snap import DokuSnapClient

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    # ─── Configuration fields ──────────────────────────────────────
    doku_qris_mid = fields.Char(
        string="DOKU Merchant ID (MID)",
        help="Merchant ID assigned by DOKU for QRIS service",
        groups='point_of_sale.group_pos_manager',
    )
    doku_qris_tid = fields.Char(
        string="DOKU Terminal ID (TID)",
        help="Terminal ID, optional",
        groups='point_of_sale.group_pos_manager',
    )
    doku_qris_test_mode = fields.Boolean(
        string="DOKU Test Mode",
        default=True,
        help="Use sandbox endpoint (api-sandbox.doku.com) when enabled",
    )
    doku_qris_validity_minutes = fields.Integer(
        string="QR Validity (minutes)",
        default=10,
        help="How long the generated QR remains valid before expiring",
    )

    # ─── Selection extension ───────────────────────────────────────
    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [
            ('doku_qris', 'DOKU QRIS')
        ]

    # ─── Validation ────────────────────────────────────────────────
    @api.constrains('use_payment_terminal')
    def _check_doku_qris_currency(self):
        for record in self:
            if record.use_payment_terminal == 'doku_qris':
                if record.company_id.currency_id.name != 'IDR':
                    raise UserError(_(
                        "DOKU QRIS only supports IDR currency. "
                        "Current company currency: %s"
                    ) % record.company_id.currency_id.name)
```

**Note**: Credentials (`Client ID`, `Secret Key`) are read from the existing `payment.provider` record (DOKU web provider) — no need to duplicate them on `pos.payment.method`. Use `env['payment.provider'].search([('code', '=', 'doku')], limit=1)` to fetch.

---

### 5.3 RPC Methods (Called from Frontend)

These methods are called via `pos.data.silentCall("pos.payment.method", "<method>", [...])` from JS:

```python
class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'
    # ... fields above ...

    def doku_qris_generate(self, amount, partner_reference_no):
        """Generate Dynamic QRIS for a POS order.

        :param float amount: order total in IDR (no decimals — IDR has no cents)
        :param str partner_reference_no: unique reference (max 64 chars)
        :return dict: {'qrContent': '...', 'referenceNo': '...', 'expiresAt': '...'}
                      or {'error': '...'} on failure
        """
        self.ensure_one()
        if self.use_payment_terminal != 'doku_qris':
            return {'error': _("Not a DOKU QRIS payment method")}

        client = DokuSnapClient(
            env=self.env,
            test_mode=self.doku_qris_test_mode,
            mid=self.doku_qris_mid,
        )
        try:
            result = client.create_qris_payment(
                amount=amount,
                partner_reference_no=partner_reference_no,
                validity_minutes=self.doku_qris_validity_minutes,
            )
            return {
                'qrContent': result['qrContent'],
                'referenceNo': result['referenceNo'],
                'expiresAt': result['additionalInfo'].get('expiredDate'),
            }
        except Exception as e:
            _logger.exception("DOKU QRIS generation failed")
            return {'error': str(e)}

    def doku_qris_fetch_status(self, partner_reference_no):
        """Poll DOKU for payment status.

        :param str partner_reference_no: the ref used in doku_qris_generate
        :return dict: {'status': 'success'|'pending'|'expired'|'failed',
                       'paid_at': '...', 'doku_ref': '...'} or {'error': '...'}
        """
        self.ensure_one()
        client = DokuSnapClient(
            env=self.env,
            test_mode=self.doku_qris_test_mode,
            mid=self.doku_qris_mid,
        )
        try:
            result = client.query_qris_status(partner_reference_no)
            status_code = result.get('latestTransactionStatus')
            return {
                'status': self._doku_qris_map_status(status_code),
                'doku_ref': result.get('originalReferenceNo'),
                'paid_at': result.get('transactionDateTime'),
                'raw': result,
            }
        except Exception as e:
            _logger.exception("DOKU QRIS status query failed")
            return {'error': str(e)}

    @staticmethod
    def _doku_qris_map_status(code):
        return {
            '00': 'success',
            '01': 'pending',
            '03': 'pending',
            '06': 'expired',
            '07': 'failed',
            '09': 'canceled',
        }.get(code, 'pending')
```

**Important**: IDR has no cents. Frontend will send `amount` as integer (e.g., `10000`), backend formats as `"10000.00"` for the API.

---

## 🎨 Section 6: Frontend Implementation

### 6.1 `static/src/js/payment_doku_qris.js` Skeleton

Adapted directly from `pos_paytm/static/src/js/payment_paytm.js`:

```javascript
import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const POLL_INTERVAL_MS = 5000;       // 5 seconds — same as pos_paytm
const MAX_POLL_DURATION_MS = 600000; // 10 minutes max polling

export class PaymentDokuQris extends PaymentInterface {
    /**
     * @override
     * Triggered when cashier clicks "Send" on the payment line.
     */
    async send_payment_request(uuid) {
        await super.send_payment_request(...arguments);
        const order = this.pos.get_order();
        const paymentLine = order?.get_selected_paymentline();

        // Build unique reference: POS{configId}-{orderUuid}-{retry}
        const retry = this._retryCountUtility(order.uuid);
        const partnerRef = this._buildPartnerReference(order, retry);
        const amount = Math.round(paymentLine.amount); // IDR has no decimals

        // Step 1: Request QR generation from backend
        const qrData = await this._generateQR(amount, partnerRef);
        if (!qrData || qrData.error) {
            paymentLine.set_payment_status("force_done");
            this._incrementRetry(order.uuid);
            return false;
        }

        // Step 2: Stash QR data on payment line for the popup to read
        paymentLine.doku_qr_content = qrData.qrContent;
        paymentLine.doku_partner_ref = partnerRef;
        paymentLine.doku_expires_at = qrData.expiresAt;
        paymentLine.set_payment_status("waitingCard");

        // Step 3: Trigger QR popup display (custom OWL component)
        // The popup component will read paymentLine.doku_qr_content

        // Step 4: Begin polling
        const result = await this._pollPaymentStatus(partnerRef);
        if (result) {
            this._retryCountUtility(order.uuid, true); // remove retry counter
            return true;
        } else {
            this._incrementRetry(order.uuid);
            return false;
        }
    }

    async send_payment_cancel(order, uuid) {
        await super.send_payment_cancel(...arguments);
        const paymentLine = this.pos.get_order()?.get_selected_paymentline();
        paymentLine.set_payment_status("retry");
        this._incrementRetry(order.uuid);
        clearTimeout(this.pollTimeout);
        return true;
    }
```

---

### 6.2 Polling Logic (continued)

```javascript
    async _pollPaymentStatus(partnerRef) {
        const startTime = Date.now();

        return new Promise((resolve) => {
            const tick = async () => {
                const paymentLine = this.pos.get_order()?.get_selected_paymentline();

                // Stop conditions
                if (!paymentLine || paymentLine.payment_status === "retry") {
                    return resolve(false);
                }
                if (Date.now() - startTime > MAX_POLL_DURATION_MS) {
                    paymentLine.set_payment_status("timeout");
                    return resolve(false);
                }

                try {
                    const data = await this.pos.data.silentCall(
                        "pos.payment.method",
                        "doku_qris_fetch_status",
                        [[this.payment_method_id.id], partnerRef]
                    );
                    if (data?.error) throw new Error(data.error);

                    if (data.status === "success") {
                        paymentLine.transaction_id = data.doku_ref;
                        paymentLine.payment_date = data.paid_at;
                        return resolve(true);
                    } else if (["expired", "failed", "canceled"].includes(data.status)) {
                        paymentLine.set_payment_status("retry");
                        this._showError(
                            _t("Payment %s. Please retry.", data.status),
                            _t("DOKU QRIS")
                        );
                        return resolve(false);
                    } else {
                        // Still pending — schedule next poll
                        this.pollTimeout = setTimeout(tick, POLL_INTERVAL_MS);
                    }
                } catch (error) {
                    this._showError(error.message, _t("DOKU QRIS Status Error"));
                    paymentLine.set_payment_status("force_done");
                    return resolve(false);
                }
            };
            tick();  // start immediately
        });
    }
```

---

### 6.3 Helper Methods

```javascript
    async _generateQR(amount, partnerRef) {
        try {
            const data = await this.pos.data.silentCall(
                "pos.payment.method",
                "doku_qris_generate",
                [[this.payment_method_id.id], amount, partnerRef]
            );
            if (data?.error) throw new Error(data.error);
            return data;
        } catch (error) {
            this._showError(error.message, _t("DOKU QRIS Generation Error"));
            return null;
        }
    }

    _buildPartnerReference(order, retry) {
        const config = this.pos.config.id;
        const uuid = order.uuid.replace(/-/g, "").substring(0, 16);
        const ts = Math.floor(Date.now() / 1000);
        let ref = `POS${config}-${uuid}-${ts}`;
        if (retry > 0) ref += `R${retry}`;
        return ref.substring(0, 64); // DOKU max 64 chars
    }

    // Retry counter, persisted in localStorage (same pattern as pos_paytm)
    _retryCountUtility(uuid, remove = false) {
        const key = `doku_qris_retry_${uuid}`;
        if (remove) {
            localStorage.removeItem(key);
        } else {
            return parseInt(localStorage.getItem(key) || "0", 10);
        }
    }
    _incrementRetry(uuid) {
        const key = `doku_qris_retry_${uuid}`;
        const cur = parseInt(localStorage.getItem(key) || "0", 10);
        localStorage.setItem(key, cur + 1);
    }

    _showError(error, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("DOKU QRIS Error"),
            body: error?.toString() || _t("Unknown error"),
        });
    }
}
```

---

### 6.4 `static/src/js/model.js` (Registration)

```javascript
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentDokuQris } from "@andykanoz_doku_payment_geteway/js/payment_doku_qris";

register_payment_method("doku_qris", PaymentDokuQris);
```

The `@andykanoz_doku_payment_geteway` import alias is auto-generated by Odoo based on module name.

---

### 6.5 `static/src/js/PaymentScreen.js` (Pending Payment Patch)

Direct adaptation from `pos_paytm/static/src/js/PaymentScreen.js`:

```javascript
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            // If user navigated away mid-payment and came back, force-done any
            // stale DOKU QRIS payment lines so they don't block UI
            const stale = this.currentOrder.payment_ids.find(
                (line) =>
                    line.payment_method_id.use_payment_terminal === "doku_qris" &&
                    !line.is_done() &&
                    line.get_payment_status() !== "pending"
            );
            if (stale) {
                stale.set_payment_status("force_done");
            }
        });
    },
});
```

This handles edge cases like browser refresh, tab change, or POS session re-open during a pending QR payment.

---

## 🔄 Section 7: Payment Flow & Polling

### 7.1 End-to-End Sequence

```
Cashier                  POS Frontend           Odoo Backend            DOKU API           Customer
──────                   ─────────────          ─────────────           ────────           ────────
  │                          │                       │                      │                 │
  │ Click "Send" on QRIS line│                       │                      │                 │
  ├─────────────────────────▶│                       │                      │                 │
  │                          │ silentCall(           │                      │                 │
  │                          │  doku_qris_generate)  │                      │                 │
  │                          ├──────────────────────▶│                      │                 │
  │                          │                       │ Get B2B Token        │                 │
  │                          │                       ├─────────────────────▶│                 │
  │                          │                       │ ◀─────────token──────┤                 │
  │                          │                       │ POST qr-mpm-payment  │                 │
  │                          │                       ├─────────────────────▶│                 │
  │                          │                       │ ◀──────qrContent─────┤                 │
  │                          │ ◀──{qrContent, ref}───┤                      │                 │
  │  📱 QR appears on screen │                       │                      │                 │
  │ ◀────────────────────────┤                       │                      │                 │
  │                          │                       │                      │  Customer scans │
  │                          │ Poll every 5s         │                      │ ◀───────────────┤
  │                          │ silentCall(           │                      │  Pays via app   │
  │                          │  doku_qris_fetch)     │                      │ ────────────────┤
  │                          ├──────────────────────▶│                      │                 │
  │                          │                       │ POST qr-mpm-query    │                 │
  │                          │                       ├─────────────────────▶│                 │
  │                          │                       │ ◀──status: 01────────┤  (still pending)│
  │                          │ ◀──{status: pending}──┤                      │                 │
  │                          │                       │                      │                 │
  │                          │   ... (repeat) ...    │                      │                 │
  │                          │                       │                      │                 │
  │                          │ Poll                  │                      │                 │
  │                          ├──────────────────────▶│                      │                 │
  │                          │                       │ POST qr-mpm-query    │                 │
  │                          │                       ├─────────────────────▶│                 │
  │                          │                       │ ◀──status: 00────────┤  (paid!)        │
  │                          │ ◀──{status: success}──┤                      │                 │
  │  ✅ "Payment received"   │                       │                      │                 │
  │ ◀────────────────────────┤                       │                      │                 │
  │                          │                       │                      │                 │
  │ Click "Validate"         │                       │                      │                 │
  ├─────────────────────────▶│                       │                      │                 │
  │  Order finalized         │                       │                      │                 │
  ▼                          ▼                       ▼                      ▼                 ▼
```

---

### 7.2 Polling Strategy Trade-offs

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Poll every 5s | Simple, matches `pos_paytm` | ~6 RPC calls/min, 30 calls/order | ✅ Use this |
| Poll every 1s | Snappier UX | 60 calls/min — may hit DOKU rate limits | ❌ Too aggressive |
| Use `bus.bus` push | Real-time, no polling | Requires webhook → broadcast pipeline; complex | ⏸️ Phase 2 |
| WebSocket | Real-time | Not native to Odoo POS | ❌ Out of scope |

**Recommendation**: Start with 5-second polling (proven by `pos_paytm`). Add webhook-driven `bus.bus` push as Phase 2 enhancement if cashiers complain about latency.

---

## 🔔 Section 8: Webhook Handling

### 8.1 Why Webhook + Polling (Not Just One)?

| Failure Mode | Polling Catches? | Webhook Catches? |
|--------------|------------------|------------------|
| Network glitch on POS device | ❌ (POS offline) | ✅ |
| DOKU API outage during poll | ❌ | ✅ (delivered later) |
| POS browser closed mid-payment | ❌ | ✅ |
| Cashier walks away | ❌ | ✅ |
| Webhook URL unreachable | ✅ | ❌ |

**Conclusion**: Use BOTH. Webhook is the source of truth for payment state in DB; polling is for live UI feedback. If webhook arrives first, the next poll sees the already-updated state and finalizes.

---

### 8.2 POS Webhook Controller

Add to `controllers/main.py`:

```python
import json
import logging
from odoo import http
from odoo.http import request
from odoo.tools import consteq
from werkzeug.exceptions import Forbidden

from ..utils.signature_snap import verify_snap_signature

_logger = logging.getLogger(__name__)


class DokuQrisPosWebhookController(http.Controller):
    _qris_pos_webhook_url = '/payment/doku/qris_pos/webhook'

    @http.route(
        _qris_pos_webhook_url,
        type='http', methods=['POST'], auth='public', csrf=False
    )
    def doku_qris_pos_webhook(self):
        """Receive payment notification from DOKU for POS QRIS transactions."""
        raw_body = request.httprequest.get_data(as_text=True)
        headers = request.httprequest.headers

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError:
            _logger.warning("DOKU QRIS webhook: invalid JSON")
            return request.make_json_response({'status': 'invalid'}, status=200)

        # Verify HMAC-SHA512 signature
        try:
            verify_snap_signature(
                env=request.env,
                headers=headers,
                raw_body=raw_body,
                expected_target=self._qris_pos_webhook_url,
            )
        except Forbidden:
            _logger.warning("DOKU QRIS webhook: signature verification failed")
            # Return 200 anyway — don't trigger DOKU retry storms
            return request.make_json_response({'status': 'rejected'}, status=200)

        # Find related pos.payment via partnerReferenceNo
        partner_ref = data.get('originalPartnerReferenceNo') or data.get('partnerReferenceNo')
        if not partner_ref:
            return request.make_json_response({'status': 'missing_ref'}, status=200)

        request.env['pos.payment'].sudo()._process_doku_qris_webhook(partner_ref, data)
        return request.make_json_response({'status': 'accepted'}, status=200)
```

---

### 8.3 `pos.payment` Model Extension

Optional model `models/pos_payment.py` to record DOKU-specific fields:

```python
from odoo import fields, models, api


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    doku_partner_ref = fields.Char("DOKU Reference", help="partnerReferenceNo sent to DOKU")
    doku_transaction_ref = fields.Char("DOKU Transaction ID", help="referenceNo returned by DOKU")
    doku_qr_content = fields.Text("QR Content", help="EMV QR string from DOKU")
    doku_qris_status = fields.Char("DOKU Status", help="Latest known DOKU transaction status")
    doku_paid_at = fields.Datetime("Paid At")

    @api.model
    def _process_doku_qris_webhook(self, partner_ref, payload):
        """Update pos.payment state based on DOKU webhook payload."""
        payment = self.search([('doku_partner_ref', '=', partner_ref)], limit=1)
        if not payment:
            # POS may not have written the row yet (race condition)
            # → log and let polling pick it up later
            return

        status_code = payload.get('latestTransactionStatus')
        payment.doku_qris_status = status_code
        if status_code == '00':
            payment.doku_paid_at = fields.Datetime.now()
            payment.doku_transaction_ref = payload.get('originalReferenceNo')
            # bus.bus broadcast (Phase 2): notify POS UI
            # payment.config_id._notify(...)
```

---

## 🎨 Section 9: UX & Display Considerations

### 9.1 QR Display Popup

The QR must appear in a modal/popup on the POS payment screen. Recommended pattern:

```
┌──────────────────────────────────────────┐
│   DOKU QRIS Payment                      │
│   ──────────────────────                 │
│                                          │
│      ┌────────────────┐                  │
│      │                │                  │
│      │   [QR CODE]    │   ← 300×300px    │
│      │                │      minimum     │
│      └────────────────┘                  │
│                                          │
│   Amount: Rp 50.000                      │
│   Expires in: 09:43                      │
│                                          │
│   ⏳ Waiting for payment...              │
│                                          │
│   [ Cancel ]    [ Force Done ]           │
└──────────────────────────────────────────┘
```

**Required UI elements**:
- QR code rendered from `qrContent` (use `qrcode-generator` lib or canvas)
- Amount display in IDR formatted (`Rp 50.000` not `50000.00`)
- Countdown timer to expiry
- Status indicator (pending/checking/success animation)
- Cancel button (calls `send_payment_cancel`)
- Force-done button (admin-only escape hatch)

---

### 9.2 QR Rendering Library

Odoo POS doesn't bundle a QR library by default. Options:

| Option | Pros | Cons |
|--------|------|------|
| `qrcode-generator` (npm, ~10KB) | Pure JS, no deps | Need to bundle |
| Server-side render to PNG | Works everywhere | Extra round-trip |
| `qrcode` from CDN | Easiest | External dep, offline-unfriendly |

**Recommendation**: Bundle `qrcode-generator` in the module's static assets. POS may run on tablets with intermittent connectivity — local rendering is more reliable.

---

### 9.3 Customer-Facing Display (Optional Phase 2)

For tablet-based POS (Andyka uses Samsung Galaxy Tab S8 for staff), the cashier-side screen may not be customer-facing. Solutions:

1. **Flip tablet to customer**: Simplest; QR popup must be readable upside-down or rotatable
2. **Customer Display module**: Use Odoo's `pos_customer_display` to show QR on second screen
3. **Print QR on receipt**: Backup option; receipt printer prints the QR — slower UX

---

## 🧪 Section 10: Testing Approach

### 10.1 Sandbox Setup

Before any real testing:

1. ✅ DOKU sandbox credentials configured in `payment.provider` (Client ID, Secret Key)
2. ✅ `pos.payment.method` created with `use_payment_terminal = 'doku_qris'`, MID set, `doku_qris_test_mode = True`
3. ✅ Webhook URL whitelisted in DOKU sandbox dashboard: `https://nitro.gopokaja.com/payment/doku/qris_pos/webhook`
4. ✅ Cloudflare Tunnel verified online: `curl https://nitro.gopokaja.com/web/health`
5. ✅ POS config has the DOKU QRIS payment method added

---

### 10.2 Manual Test Checklist

**Happy path**:
- [ ] Cashier creates order, total > 0 IDR
- [ ] Selects DOKU QRIS payment method
- [ ] Clicks Send → QR appears within 3s
- [ ] Sandbox simulator (or DOKU test app) scans + pays
- [ ] POS shows ✅ within 10s of payment
- [ ] Order finalizes correctly
- [ ] `pos.payment` record has `doku_partner_ref`, `doku_transaction_ref`, `doku_paid_at`

**Edge cases**:
- [ ] Cashier cancels mid-payment → polling stops, line resets to retry state
- [ ] QR expires (10 min, no scan) → status becomes "timeout", retry available
- [ ] Customer pays after QR expired → DOKU should reject (verify webhook says expired)
- [ ] Network drops during polling → graceful error, retry available
- [ ] Browser refresh during pending payment → stale lines force-done on remount
- [ ] Webhook arrives before next poll → next poll sees success, finalizes UI
- [ ] Webhook signature invalid → rejected silently (logs only), no UI effect

---

## 🚨 Section 11: Critical Gotchas

### Gotcha 1: SHA-512 vs SHA-256 Confusion

**Symptom**: API returns `401 Invalid Signature` even though existing DOKU Checkout signing works.

**Cause**: Reusing `utils/signature.py` (HMAC-SHA256, used by DOKU Checkout). SNAP API requires HMAC-SHA512.

**Fix**: Create separate `utils/signature_snap.py`. DO NOT import or modify the existing `signature.py` — it serves the web payment provider correctly.

---

### Gotcha 2: IDR Has No Decimal Currency

**Symptom**: API rejects amount `100.50`, or shows wrong amount on customer's banking app.

**Cause**: IDR has no cents (no fractional rupiah). DOKU API expects `"value": "10000.00"` format BUT the value before the decimal must be a whole rupiah amount.

**Fix**: In backend, always:
```python
amount_str = "{:.2f}".format(int(round(amount)))  # "10000.00"
```
In frontend, `Math.round(paymentLine.amount)` before sending to backend.

---

### Gotcha 3: Token Expiry Mid-Polling

**Symptom**: First few polls work, then suddenly all fail with 401.

**Cause**: B2B token expired (`expiresIn: 899` ≈ 15 minutes). Backend `DokuSnapClient` cached the expired token.

**Fix**: Cache token with explicit expiry timestamp; refresh ~60s before expiry:
```python
token_record = ICP.get_param('doku.snap.token')
expires_at = float(ICP.get_param('doku.snap.token_expires', '0'))
if not token_record or time.time() > expires_at - 60:
    # Refresh token
    ...
```

---

### Gotcha 4: `partnerReferenceNo` Collision Across POS Sessions

**Symptom**: DOKU returns "duplicate reference" error.

**Cause**: Same order UUID retried after a long gap, OR multiple POS terminals using same prefix.

**Fix**: Include `pos.config.id` AND timestamp in reference. Format: `POS{configId}-{shortUuid}-{epoch}`. Add `R{n}` suffix for retries.

---

### Gotcha 5: localStorage Survives POS Session End

**Symptom**: Old retry counters from previous days clutter localStorage.

**Cause**: `pos_paytm` pattern uses raw `order.uuid` as key, never cleaned up.

**Fix**: On POS session close, sweep `doku_qris_retry_*` keys from localStorage. Or accept the bloat (it's tiny).

---

### Gotcha 6: Webhook Race Condition with Polling

**Symptom**: Order finalizes twice or shows inconsistent state.

**Cause**: Webhook arrives, marks `pos.payment` as paid. Polling sees this on next tick, also tries to mark paid.

**Fix**: Make `_process_doku_qris_webhook` idempotent — check if already paid before updating. Polling reads current state and accepts whatever's there.

---

### Gotcha 7: POS Must Depend on `point_of_sale`

**Symptom**: `KeyError: 'pos.payment.method'` on module install.

**Cause**: Forgot to add `'point_of_sale'` to `__manifest__.py` `depends`.

**Fix**: Add it. Also remember Docker restart + module upgrade are required when changing `depends`.

---

### Gotcha 8: Asset Bundle Path Must Match Module Name

**Symptom**: JS file shows in network tab as 404, OR `register_payment_method` never runs.

**Cause**: Asset path in manifest doesn't match actual folder name (typo in `andykanoz_doku_payment_geteway` vs `andykanoz_doku_payment_gateway`).

**Fix**: Module folder name has typo `geteway` (not `gateway`). All asset paths and JS imports MUST use the typo'd version. Don't "fix" the typo without coordinated rename of folder + manifest + all imports.

---

## 📋 Implementation Checklist

### Phase A — Foundation (Backend)
- [ ] Add `point_of_sale` to `__manifest__.py` depends
- [ ] Create `utils/signature_snap.py` (HMAC-SHA512)
- [ ] Create `utils/api_client_snap.py` (Get Token + QRIS endpoints)
- [ ] Cache B2B token in `ir.config_parameter` with expiry
- [ ] Create `models/pos_payment_method.py` (extend selection + RPC methods)
- [ ] Create `models/pos_payment.py` (DOKU fields + webhook handler)
- [ ] Update `models/__init__.py` to import new files
- [ ] Add POS webhook route in `controllers/main.py`
- [ ] Bump module version to `18.0.2.0.0`

### Phase B — Configuration View
- [ ] Create `views/pos_payment_method_views.xml`
- [ ] Add view to manifest `data` list
- [ ] Verify form shows DOKU fields when `use_payment_terminal == 'doku_qris'`
- [ ] Verify currency constraint works (IDR only)

### Phase C — Frontend
- [ ] Create `static/src/js/payment_doku_qris.js` (PaymentInterface extension)
- [ ] Create `static/src/js/model.js` (`register_payment_method`)
- [ ] Create `static/src/js/PaymentScreen.js` (pending payment patch)
- [ ] Create `static/src/xml/payment_doku_qris.xml` (QR popup template)
- [ ] Create `static/src/scss/payment_doku_qris.scss` (popup styling)
- [ ] Add QR rendering library (e.g., `qrcode-generator`)
- [ ] Add all to `__manifest__.py` `assets.point_of_sale._assets_pos`

### Phase D — Sandbox Testing
- [ ] Configure DOKU sandbox credentials in `payment.provider`
- [ ] Configure POS payment method (MID, test mode = True)
- [ ] Whitelist webhook URL in DOKU sandbox dashboard
- [ ] Verify Cloudflare Tunnel up
- [ ] Run happy path test
- [ ] Run all edge-case tests from §10.2

### Phase E — Production Readiness
- [ ] Switch `doku_qris_test_mode` to False on production
- [ ] Update webhook URL to `https://www.gopokaja.com/payment/doku/qris_pos/webhook`
- [ ] Whitelist production webhook in DOKU production dashboard
- [ ] Smoke test with small real transaction
- [ ] Document for Gopokaja staff

---

## 📚 References

### Internal
- **`pos_paytm` source** — `D:\MyServer\Odoo18\Source Code Odoo18\pos_paytm\` — canonical pattern, study this first
- **`pos_razorpay`** — alternate dynamic-QR reference if pos_paytm questions arise
- **`l10n_test_pos_qr_payment`** — Odoo's QR payment test module
- **Existing DOKU module** — `D:\MyServer\Odoo18\Addons\andykanoz_doku_payment_geteway\` — has the web provider already set up, including credentials we reuse
- **[`XENDIT_PAYMENT_PROVIDER_PATTERN.md`](./XENDIT_PAYMENT_PROVIDER_PATTERN.md)** — generic Odoo 18 payment provider patterns
- **[`DOKU_DEVELOPMENT_SKILL.md`](./DOKU_DEVELOPMENT_SKILL.md)** — DOKU API reference (HMAC-SHA256 web flow) + workflow conventions

### DOKU Documentation
- **QRIS Overview**: https://docs.doku.com/accept-payments/no-integration-products/qris
- **Direct API Hub**: https://developers.doku.com/accept-payments/direct-api
- **SNAP QRIS Integration Guide**: https://developers.doku.com/accept-payments/direct-api/snap/integration-guide/qris
- **DOKU Dashboard**: https://dashboard.doku.com/

**🚨 STANDING RULE**: Always re-fetch DOKU docs before writing/modifying API logic. Specs change without notice.

### Odoo Documentation
- **POS Payment Methods**: https://www.odoo.com/documentation/18.0/applications/sales/point_of_sale/payment_methods.html
- **POS Payment Terminals**: https://www.odoo.com/documentation/18.0/applications/sales/point_of_sale/payment_methods/terminals.html

---

## 🎬 Quickstart for Future Sessions

When starting a new session to work on DOKU QRIS POS:

1. **Read this skill** — full pass to refresh context
2. **Re-fetch DOKU SNAP QRIS docs** via web_fetch — verify endpoints/signatures haven't changed
3. **Check `pos_paytm` source** for any pattern questions — it is the ground truth
4. **Verify Cloudflare Tunnel** is up if doing webhook testing
5. **Pick a phase** from §Implementation Checklist and stick to it (don't bundle phases)
6. **Follow standing rules** — filesystem-first, explain before edit, wait for confirmation, surgical edits

---

**Created**: 2026-05-07
**Created by**: Claude (per Andyka's request after providing official DOKU QRIS docs)
**Status**: Foundation pattern — UNTESTED. Verify each section against actual DOKU sandbox responses before relying on details.
**Confidence levels**:
- ✅ HIGH: Odoo POS architecture (verified from `pos_paytm` source code)
- ✅ HIGH: General SNAP signature formula (from search results of DOKU docs)
- ⚠️ MEDIUM: Exact field names in API request/response (verify against DOKU sandbox)
- ⚠️ MEDIUM: Status code mapping (verify against actual DOKU webhooks)
- ⚠️ LOW: QR rendering library choice (no Odoo-specific recommendation found)
**Next update**: After first sandbox test — refine §2.4, §2.5, §11 with actual observed behavior
