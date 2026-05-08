# 🤝 HANDOFF DOCUMENT - Pending Payment Handling Strategies

> **TO THE NEXT AI**: This document outlines the architectural strategies for handling "Pending Payments" (e.g., waiting for Virtual Account transfer) in Odoo 18 with the DOKU Payment Gateway. The user (Andyka) wants a user-friendly checkout experience similar to Tokopedia. Read this carefully to understand the options before implementing.

---

## 🛑 The Core Problem
Odoo 18's default e-commerce flow does not have a dedicated "Pending Payment" page with countdowns or Virtual Account (VA) instructions. 
Currently, after a user selects a payment method and is redirected to DOKU Checkout:
1. If the user closes the DOKU page without paying, the Odoo transaction state remains `pending`.
2. When the user visits their Odoo portal (`/my/orders`), Odoo shows a generic "Pay Now" button.
3. Clicking "Pay Now" often creates a *new* transaction instead of resuming the previous one, leading to duplicate transactions and confusion.

## 💡 The 3 Strategies for Implementation

We have identified three approaches to solve this, ranging from the easiest to the most complex (most "Tokopedia-like").

### 🟢 STRATEGY 1: The Shortcut Approach (Resume via DOKU Link)
**Difficulty**: Easy
**Recommended for**: Quick deployment, high stability.

**Concept**: 
We keep using **DOKU Checkout (Hosted Page)**. Odoo doesn't know the actual VA number, it only knows the `doku_payment_url` which leads to the DOKU page where the VA number is displayed.

**Implementation Steps**:
1. Modify Odoo's Customer Portal view (`sale.portal_my_orders` or similar).
2. If the order has a `pending` transaction linked to DOKU, hide Odoo's default "Pay Now" button.
3. Inject a custom button: **"Lanjutkan Pembayaran / Lihat Instruksi"**.
4. This button directly opens the `self.doku_payment_url` saved in the transaction record.
5. The user is redirected back to DOKU's hosted page, which intelligently resumes their session and shows the same VA number/QR code.

**Pros**: Minimal code changes, relies on DOKU's robust UI.
**Cons**: User leaves Odoo's domain again to see the instructions.

---

### 🟡 STRATEGY 2: The Semi-Tokopedia Approach (Custom Odoo Pending Page)
**Difficulty**: Medium
**Recommended for**: Better UX while keeping the stability of Hosted Checkout.

**Concept**:
We keep using **DOKU Checkout (Hosted Page)**, but we build a custom "Waiting for Payment" page inside Odoo to make the UX feel more integrated.

**Implementation Steps**:
1. Create a custom Odoo controller/route (e.g., `/payment/doku/pending/<tx_id>`).
2. Build an Odoo web template for this route featuring a Tokopedia-style layout (Order Summary, Countdown Timer based on `doku_expired_at`).
3. Since we still don't have the actual VA number in Odoo's database (DOKU Hosted Page generates it), we place a prominent button: **"Lihat Nomor VA / QRIS"**.
4. Clicking this button opens an `iframe` or a new tab pointing to `doku_payment_url`.
5. Redirect the user to this custom Odoo page automatically after they generate the payment in DOKU (via Return URL).

**Pros**: Feels like a premium e-commerce site; keeps user mostly on Odoo.
**Cons**: The actual payment numbers are still hidden behind a button click.

---

### 🔴 STRATEGY 3: The Full Tokopedia Approach (Migrate to Direct API)
**Difficulty**: Hard / Very Complex
**Recommended for**: Ultimate UX control, assuming high development resources.

**Concept**:
We completely abandon the current "DOKU Checkout (Redirect/Hosted Page)" architecture. We rewrite the integration using **DOKU Direct API** (Server-to-Server).

**Implementation Steps**:
1. Change the API payload to request specific Direct API endpoints (e.g., `/bca-virtual-account/v2/payment-code`).
2. Parse the DOKU response to extract the *actual* `virtual_account_number` or `qr_string`.
3. Save these specific values into new fields in `payment.transaction` (e.g., `doku_va_number`, `doku_qris_string`).
4. Build a comprehensive "Pending Payment" Odoo page that natively renders the VA number, copy button, QR Code image (using a JS library or Python qrcode), and countdown timer.
5. Build custom input forms in Odoo for Credit Card (requires PCI-DSS compliance handling or tokenization).

**Pros**: Perfect UX. User never leaves the Odoo website. Exactly like Tokopedia.
**Cons**: 
- Massive development effort.
- Must design and maintain UI for every single payment method (BCA VA looks different from Mandiri VA, QRIS needs image generation, E-Wallets need deep-linking logic).
- Harder to maintain if DOKU updates their API.

---

## 🎯 Current Status & Next Steps

Currently, the module is built using the **Hosted Page / Checkout** architecture, which aligns with Strategies 1 and 2. 

**Wait for Andyka's decision** on which strategy to pursue before writing any code. If Strategy 1 or 2 is chosen, the next step is extending the Odoo Portal views. If Strategy 3 is chosen, a massive refactor of `_doku_create_payment` is required.