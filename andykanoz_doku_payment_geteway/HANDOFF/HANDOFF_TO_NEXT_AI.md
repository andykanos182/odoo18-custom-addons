# 🤝 HANDOFF DOCUMENT - DOKU PAYMENT GATEWAY

> **TO THE NEXT AI**: This module aims to provide a marketplace-friendly (B2C) payment experience within Odoo 18. We are using **DOKU Checkout (Hosted Page)**.

## ✅ Current Status: PHASE 2 COMPLETED
Strategy 2 (Semi-Tokopedia) is fully implemented. Keranjang otomatis kosong, Lazy Auto-Cancel aktif, Banner Lanjutkan Pembayaran muncul di Checkout dan Halaman Faktur (Invoice) untuk mencegah duplikasi VA.

**Recently Added**: Auto-Cancel SO & Stock Release is now active. When a DOKU transaction is cancelled (either lazily or via cron), the linked `sale.order` is automatically cancelled (`_action_cancel()`), and inventory stock is released.

## 🚀 Next Sprint
1. Logistic Tracking Timeline.
2. Review & Rating.
