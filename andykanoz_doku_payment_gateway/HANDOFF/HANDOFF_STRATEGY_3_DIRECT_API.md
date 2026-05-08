# 🤝 HANDOFF DOCUMENT - STRATEGY 3 (Direct API Migration)

> **TO THE NEXT AI**: The project direction has shifted. The user (Andyka) wants to completely implement **Strategy 3 (Full Tokopedia UX)** using **DOKU Direct API**. We are moving away from DOKU Checkout (Hosted Page). 
> **Immediate Focus: QRIS.** Do not implement Cards or E-Wallets until QRIS is 100% working natively in Odoo.

---

## 📚 Documentation Analysis & Requirements

Based on the provided links, here is the technical breakdown of what is required to migrate from Hosted Checkout to Direct API.

### 1. SNAP vs NON-SNAP Architecture (CRITICAL)
DOKU uses two different API standards:
*   **Non-SNAP**: DOKU's legacy/standard API (used for Cards, some E-Wallets). Uses `HMAC-SHA256` for signatures.
*   **SNAP (Standard Nasional Open API Pembayaran)**: Mandated by Bank Indonesia. **QRIS uses SNAP.**
    *   SNAP requires a completely different authentication flow.
    *   It typically requires generating an `Access Token` first (B2B) using Asymmetric Cryptography (**RSA-SHA256** with Private/Public Keys).
    *   Transaction signatures use **HMAC-SHA512** (different from our current HMAC-SHA256).
    *   *Action Required*: We must overhaul `utils/api_client.py` and `utils/signature.py` to support the BI SNAP standard.

### 2. QRIS Integration (CURRENT FOCUS)
*Reference: https://developers.doku.com/accept-payments/direct-api/snap/integration-guide/qris*
*   **Generate QRIS**: Odoo will call the SNAP QRIS endpoint. DOKU will return a `qrData` or `qrContent` string (the actual EMVCo standard string).
*   **Displaying the QR**: Odoo must generate the QR Code image itself. We will use a JavaScript library (e.g., `qrcode.js` or OWL equivalent) or Python's `qrcode` to render this string visually on a custom Odoo "Pending Payment" page.
*   **Query & Cancel QRIS**: We need to implement endpoints in Odoo to check the status or cancel the QR manually.
*   **Notification**: The webhook payload for SNAP QRIS will look different from Checkout. We need to parse SNAP notifications.

### 3. Credit Cards (Future Phase)
*Reference: https://developers.doku.com/accept-payments/direct-api/non-snap/cards/*
*   Since Odoo is not PCI-DSS certified, we **cannot** process raw card numbers through our Python backend (Host-to-Host).
*   We must use **DOKU JS Integration** or **Payment Page Integration** for cards. DOKU JS allows the customer to enter card details safely directly to DOKU's server, returning a token to Odoo.
*   Tokenization and Mastercard ABU (Automatic Billing Updater) are advanced features for subscriptions.

### 4. E-Wallets (Future Phase)
*Reference: https://developers.doku.com/accept-payments/direct-api/non-snap/e-wallet/ovo-push-payment*
*   OVO Push Payment means the user enters their OVO Phone Number in Odoo. Odoo sends it to DOKU, and the user's OVO app receives a push notification to pay.
*   Requires building a custom form in Odoo asking for "Phone Number".

---

## 🛠️ Step-by-Step Action Plan for QRIS (Direct API)

### Phase 1: Preparation & Keys
1.  Verify if the user's DOKU Dashboard has generated SNAP Asymmetric Keys (Private Key). This is mandatory for SNAP QRIS.
2.  Add a new configuration field in `payment.provider` for `doku_private_key`.

### Phase 2: API & Signature Refactor
1.  Update `utils/signature.py` to handle BI SNAP signatures (Asymmetric RSA256 for token generation, Symmetric HMAC512 for transactions).
2.  Create a SNAP-compliant API request function in `utils/api_client.py`.

### Phase 3: Transaction Logic Overhaul
1.  Modify `models/payment_transaction.py`.
2.  When `self.payment_method_id.code == 'qris'`, route the API call to `_doku_create_qris_snap()`.
3.  Instead of saving `doku_payment_url`, save `doku_qris_string` returned by the API.

### Phase 4: Custom Odoo "Pending Payment" Page
1.  Create an Odoo Controller (`controllers/main.py`) to serve `/payment/doku/pending/<tx_id>`.
2.  Create an Odoo QWeb Template (`views/payment_doku_templates.xml`) that looks like Tokopedia's waiting page.
3.  Inject the `doku_qris_string` into the template and use a JS library to draw the QR box natively on screen.
4.  Add a countdown timer based on `transaction.doku_expired_at`.

### Phase 5: Webhook Updates
1.  Update the webhook controller to accept and verify BI SNAP Notification headers (`X-TIMESTAMP`, `X-SIGNATURE`).

---

**Do not execute any of the code changes until the user gives the explicit command to start Phase 1.**