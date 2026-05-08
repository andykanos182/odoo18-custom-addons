# 🤝 HANDOFF DOCUMENT - STRATEGY 2 (Semi-Tokopedia Custom Page)

> **TO THE NEXT AI**: The project direction for this strategy is to create a more integrated e-commerce experience while still relying on **DOKU Checkout (Hosted Page)** for the actual payment processing. We will build a custom "Waiting for Payment" page in Odoo.

---

## 🎯 The Goal
We want to give the user a beautiful, Tokopedia-like "Pending Payment" page inside Odoo (e.g., `Gopokaja.com/payment/doku/pending`). However, because DOKU Hosted Page generates the actual VA number / QRIS, we will place a prominent "Lihat Instruksi Pembayaran" button on this custom page that opens DOKU.

## 🛠️ Implementation Plan

### Phase 1: Controller Creation (`controllers/main.py`)
1.  Create a new route: `@http.route('/payment/doku/pending/<int:tx_id>', type='http', auth='public', website=True)`.
2.  Fetch the `payment.transaction` record.
3.  Validate access (ensure the user is the owner of the transaction or has a valid access token).
4.  Pass transaction details (`amount`, `reference`, `doku_expired_at`, `doku_payment_url`) to the QWeb template.

### Phase 2: QWeb Template (`views/payment_doku_templates.xml`)
1.  Design a new template `andykanoz_doku_payment_geteway.pending_payment_page`.
2.  **UI Elements Required:**
    *   **Header**: "Menunggu Pembayaran" (Waiting for Payment).
    *   **Total Amount**: Formatted currency.
    *   **Countdown Timer**: A JavaScript snippet that counts down to `doku_expired_at`.
    *   **Call to Action**: A large, primary button "Lihat Nomor Rekening / QRIS".
    *   **Cancel Action (NEW)**: A secondary button or text link "Batalkan Pembayaran" (Cancel Payment).
3.  The Call to Action button must open `doku_payment_url` in a new tab (or an iframe modal if possible without CORS issues).

### Phase 3: Redirect Hook & Cancel Logic (`models/payment_transaction.py` & `controllers/main.py`)
1.  **Return URL Modification**: Currently, the Return URL (`/payment/doku/return`) probably redirects to `/payment/status`. If the transaction state is still `pending`, redirect them to our new `/payment/doku/pending/<tx_id>` route instead of the generic Odoo status page.
2.  **Cancel Payment Endpoint (NEW)**: Create a POST route (e.g., `/payment/doku/cancel/<tx_id>`). When the user clicks "Batalkan Pembayaran" on the pending page:
    *   Find the pending transaction.
    *   Change its state in Odoo to `cancel`.
    *   **Crucial:** Call the DOKU Void API (`/orders/v1/void` defined in `const.py`) to invalidate the payment link/VA on DOKU's side.
    *   Redirect the user back to the portal or checkout page so they can choose a different payment method.

### Phase 4: Customer Portal Integration
1.  Similar to Strategy 1, modify the `/my/orders` portal page.
2.  If the order is `pending` via DOKU, change the "Pay Now" button to point to our custom `/payment/doku/pending/<tx_id>` page.

## � Odoo Core Files to Analyze (For Developers/AI)
To implement this strategy, you will need to inspect or override these specific Odoo 18 core files:

1. **Portal "Pay Now" Button Override:**
   - File to inspect: `D:\MyServer\Odoo18\Source Code Odoo18\sale\views\sale_portal_templates.xml`
   - Target: Search for the `id="o_sale_portal_paynow"` button or the `<t t-if="sale_order._has_to_be_paid()">` logic.
   - Action: Use `<xpath>` in our `payment_doku_templates.xml` to inject our "Menunggu Pembayaran" button when `tx.state == 'pending'`.

2. **Payment Status Page Redirect:**
   - File to inspect: `D:\MyServer\Odoo18\Source Code Odoo18\payment\controllers\post_processing.py`
   - Target: The `@http.route('/payment/status')` controller and the QWeb template `payment.payment_status`.
   - Action: We don't necessarily override this core file. Instead, in our own `andykanoz_doku_payment_geteway/controllers/main.py` under the `/payment/doku/return` route, we intercept the flow. If the transaction is pending, we do a `request.redirect('/payment/doku/pending/...')` instead of forwarding them to `/payment/status`.

3. **Pending Page Layout (Base Template):**
   - File to inspect: `D:\MyServer\Odoo18\Source Code Odoo18\website\views\website_templates.xml` (or `portal\views\portal_templates.xml`).
   - Target: `<t t-call="website.layout">` or `<t t-call="portal.portal_layout">`.
   - Action: Wrap our new custom QWeb template inside one of these layouts so it inherits the Gopokaja website header and footer.
## ⚠️ Technical Pitfalls & Tips (Wajib Baca)
1. **How to find DOKU transactions in QWeb (Portal):**
   In `sale_portal_templates.xml`, Odoo only gives you the `sale_order` record. To check if a DOKU transaction is pending, you must use a filtered search in QWeb:
   ```xml
   <t t-set="doku_tx" t-value="sale_order.transaction_ids.filtered(lambda t: t.state == 'pending' and t.provider_code == 'doku')[:1]"/>
   <t t-if="doku_tx">
       <!-- Render Tokopedia-style button here -->
   </t>
   ```

2. **Intercepting the Return URL (`controllers/main.py`):**
   In the existing `doku_return` method, DO NOT just return `request.redirect('/payment/status')`.
   Fetch the transaction using the `reference` from kwargs. If `tx.state == 'pending'`, return `request.redirect('/payment/doku/pending/%s' % tx.id)`.

3. **Security (Access Rights):**
   In your new `/payment/doku/pending/<tx_id>` route, do NOT let anyone view the transaction just by changing the URL ID. 
   Use Odoo's built-in session monitoring or validate the user: `if tx.partner_id != request.env.user.partner_id:` (handle public portal tokens carefully).
## �💡 Benefits & Limitations
*   **Benefits**: Creates a branded, premium feel. Users see a countdown timer keeping them engaged. Easier to implement than full Direct API.
*   **Limitations**: The actual VA number or QR Code cannot be shown natively on the page. The user still has to click a button to view the DOKU-hosted instruction page.