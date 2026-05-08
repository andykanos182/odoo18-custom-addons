# DEVELOPMENT NOTES — AndykaNoz Self Pickup Option 1
# Module: andykanoz_self_pickup_option_1
# Metode: Override Email Template (Ringan)
# Author: AndykaNoz
# Odoo Version: 18.0 Community (Docker)
# Last Updated: 2026-03-25
# AI Assistant: Claude Opus 4.6

---

## STATUS PENGEMBANGAN

### ✅ Fitur yang Sudah Selesai
- Toggle "Diantar ke Alamat Saya" / "Ambil Sendiri di Toko" di checkout
- Info alamat toko + link Google Maps + link telepon saat pilih Self Pickup
- Carrier Self Pickup tersimpan ke Sales Order via RPC
- Portal Sales Order: Kode Pengambilan, Status, Instruksi, Alamat Toko, WhatsApp
- Portal Sales Order: Last Delivery Orders disembunyikan untuk Self Pickup
- Override email: saat Validate delivery order Self Pickup → kirim email
  "Pesanan Siap Diambil" (bukan "Pesanan Telah Dikirim")
- Email berisi: kode pengambilan, instruksi, alamat toko, link Maps, telepon

### Struktur Module
```
andykanoz_self_pickup_option_1/
├── __manifest__.py
├── __init__.py
├── DEVELOPMENT_NOTES.md
├── data/
│   ├── delivery_carrier_data.xml    ← Carrier "Ambil Sendiri" (Rp 0)
│   └── mail_template_data.xml      ← Email template "Pesanan Siap Diambil"
├── models/
│   ├── __init__.py
│   ├── delivery_carrier.py         ← Field is_self_pickup
│   └── stock_picking.py            ← Override button_validate → email Self Pickup
└── views/
    ├── delivery_carrier_view.xml    ← Field is_self_pickup di form
    └── checkout_self_pickup_template.xml ← Checkout toggle + Portal section
```

---

## RENCANA PENGEMBANGAN MASA DEPAN

### Opsi 2: Operation Type Terpisah
- Module: `andykanoz_self_pickup_option_2` (atau nama yang disepakati)
- Tujuan: Menu "Self Pickup Orders" terpisah di Inventory
- Detail lengkap: lihat DEVELOPMENT_NOTES.md di module andykanoz_self_pickup

---

*Catatan ini dibuat oleh Claude Opus 4.6 pada 2026-03-25*
