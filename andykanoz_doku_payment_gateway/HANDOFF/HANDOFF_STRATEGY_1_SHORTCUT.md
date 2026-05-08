# 🤝 HANDOFF DOCUMENT - STRATEGY 1 (Shortcut - DOKU Checkout Resume)

> **TO THE NEXT AI**: The project direction for this strategy is to enhance the UX of "Pending Payments" without changing the core backend API. We will continue using **DOKU Checkout (Hosted Page)**. The goal is to provide a "Resume Payment" button in Odoo's customer portal.

---

## 🎯 The Goal
Currently, if a customer closes the DOKU payment page without paying, Odoo shows a generic "Pay Now" button on the portal (`/my/orders`). Clicking it creates a *new* transaction.
We want to replace that button with a **"Lanjutkan Pembayaran"** (Resume Payment) button that simply re-opens the existing `doku_payment_url`.

## 🛠️ Implementation Plan

### Phase 1: Identify Target Template
1.  Locate Odoo's core portal template that renders the "Pay Now" button on the Sale Order portal view (usually inside `sale.portal_my_orders` or `sale.sale_order_portal_template`).
2.  Find where the transaction state is evaluated (e.g., `tx_state == 'pending'`).

### Phase 2: Extend the Portal Template (`views/payment_doku_templates.xml`)
1.  Create an XPath override (using `inherit_id`) targeting the payment button area.
2.  Add a condition: `if transaction.provider_code == 'doku' and transaction.state == 'pending' and transaction.doku_payment_url`.
3.  If true, render a custom button:
    ```html
    <a t-att-href="transaction.doku_payment_url" class="btn btn-warning">
        <i class="fa fa-arrow-right"/> Lanjutkan Pembayaran (DOKU)
    </a>
    ```
4.  Ensure the default Odoo "Pay Now" logic is hidden when this condition is met to prevent duplicate transactions.

### Phase 3: Transaction Model Cleanup
1.  Verify that `doku_payment_url` is reliably saved and accessible in the portal context.
2.  (Optional but recommended) Ensure `doku_expired_at` is used. If the current time is past `doku_expired_at`, hide the resume button and let Odoo's default flow create a new transaction.

## 💡 Benefits & Limitations
*   **Benefits**: Extremely fast to implement. High stability. No changes to API logic.
*   **Limitations**: The user must still leave the Odoo website to view their Virtual Account number or QRIS barcode on DOKU's hosted page.