---
description: 'Detailed knowledge and rules for andykanoz_doku_payment_geteway module — B2C marketplace payment strategy.'
applyTo: '**/andykanoz_doku_payment_geteway/**'
---

# DOKU Payment Gateway (Marketplace-Friendly Strategy)

This module integrates DOKU Checkout (Hosted Page) into Odoo 18, overriding Odoo's default B2B payment behavior to act like an Indonesian B2C Marketplace (e.g., Tokopedia/Shopee).

## 🛑 CRITICAL RULES (DO NOT BREAK)

1. **Strategy 2 (Semi-Tokopedia) is Active**:
   - Customers DO NOT stay on the Odoo payment page after creating a VA/QRIS. 
   - If they navigate back to Odoo, DO NOT let them create another VA. Hide the standard Odoo payment forms in `/shop/payment`, `/my/invoices/<id>`, and `/my/invoices/overdue` using XPath.
   - Show the yellow "Lanjutkan Pembayaran" (Resume Payment) banner instead.
2. **Never Expose `payment.transaction` without `sudo()` in Portals**:
   - Odoo restricts read access to `payment.transaction` for portal users. Always use `request.env['payment.transaction'].sudo().search(...)`.
   - **STRICTLY filter** by `partner_id` (`child_of` commercial_partner_id) to prevent data leaks.
3. **Auto-Clear Cart via Immediate Pending**:
   - We call `self._set_pending()` immediately after receiving the payment URL from DOKU. This forces Odoo to empty the eCommerce shopping cart. Do not change this to `draft`.
4. **Lazy Auto-Cancellation**:
   - Expired transactions (`doku_expired_at < now`) are cancelled lazily when the user visits the portal dashboard or the pending page. Do not remove this logic from `controllers/portal.py` or `controllers/main.py`.
5. **Hosted Page ONLY**:
   - We do NOT use DOKU Direct API to generate raw VA numbers. We rely on `doku_payment_url` and redirect the user.

## 🗺️ Module Architecture & Key Files

* **`models/payment_transaction.py`**: Core logic for API calls (`_doku_create_payment`), payload building, and Webhook processing (`_process_doku_notification`).
* **`controllers/main.py`**: Handles Webhook (`/payment/doku/webhook`), Return URL, Pending Page (`/payment/doku/pending/<id>`), and Cancel Action.
* **`controllers/portal.py`**: Injects pending payment counts into `/my/home` and provides the list view at `/my/doku/pending`.
* **`views/payment_doku_templates.xml`**: Contains the Tokopedia-style pending page (`doku_pending_payment_page`) and eCommerce checkout overrides.
* **`views/portal_templates.xml`**: Overrides Customer Portal `/my/orders`, `/my/invoices`, and `/my/invoices/overdue` to inject pending banners and hide native payment buttons.

## 🚀 Future Sprints Context (For AI Collaboration)
When building future B2C modules on top of this:
- **Auto-Cancel SO**: Needs a cron job to not only cancel the `payment.transaction` but also trigger `sale.order._action_cancel()` to release inventory locks.
- **Reviews/Logistics**: Keep them decoupled. Review models should link to `sale.order` when its state becomes `done` or `sale`.
