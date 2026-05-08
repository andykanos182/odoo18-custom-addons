# DEVELOPMENT NOTES — AndykaNoz Custom Module
# Module: andyka_gemini_custom_module
# Author: AndykaNoz
# Odoo Version: 18.0 Community (Docker)
# Last Updated: 2026-03-15
# AI Assistants: Google Gemini (v1.0) → Claude Opus 4.6 (v2.2)

---

## 1. GAMBARAN UMUM

### Fitur Utama
1. **Peta Google Maps interaktif** di halaman:
   - `/my/account` (Portal My Details)
   - `/shop/address` (Checkout delivery/billing)
2. **Reverse geocoding** — klik peta → otomatis isi field alamat
3. **Tombol "Lokasi Saya"** — GPS browser
4. **Koordinat tersimpan** ke `res.partner` (`partner_latitude`, `partner_longitude`)
5. **Link Navigation** di Delivery Orders — URL navigasi dari koordinat
6. **Field "Link Maps"** di backend Contacts + Companies (mirroring via partner_id)
7. **Tombol Navigasi** di list view Delivery Orders

---

## 2. STRUKTUR MODULE

```
andyka_gemini_custom_module/
├── __manifest__.py
├── __init__.py
├── DEVELOPMENT_NOTES.md
│
├── controllers/
│   ├── __init__.py
│   ├── main.py              ← Checkout: inject API key + simpan koordinat
│   └── portal.py            ← Portal: inject API key + simpan koordinat
│
├── models/
│   ├── __init__.py
│   ├── res_partner.py       ← Field: gmaps_link
│   ├── res_company.py       ← Placeholder (Link Maps via res.partner)
│   └── stock_picking.py     ← Computed: gmaps_navigation_url + action
│
├── views/
│   ├── res_partner_view.xml       ← Link Maps di Contact form
│   ├── res_company_view.xml       ← Kosong (Link Maps dari partner)
│   ├── website_sale_templates.xml ← Peta Google Maps (checkout + portal)
│   └── stock_picking_view.xml     ← Link Navigation di Delivery Orders
│
├── static/src/css/
│   └── stock_picking.css          ← Placeholder
│
└── i18n/
    └── id.po                      ← Terjemahan Indonesia
```

---

## 3. MODULE TERKAIT

| Module | Fungsi | Status |
|--------|--------|--------|
| andyka_gemini_custom_module | Module utama (peta, link maps, navigasi) | ✅ Aktif |
| andyka_self_pickup | Self Pickup delivery method | Siap install |
| andyka_test_maps | Halaman test Leaflet + Google Maps | Opsional |
| andyka_website_sale_map_location_claude | Module lama (deprecated) | Bisa dihapus |

---

## 4. CATATAN PENTING

### Google Maps API Key
- Config: Settings → Integrations → Geolocation → Key
- Parameter: `base_geolocalize.google_map_api_key`
- API: Maps JavaScript API + Geocoding API

### base_geolocalize Reset
- Jika alamat berubah tanpa koordinat ikut di-write → koordinat reset ke 0
- Solusi: koordinat tetap di values dict, ikut write bersamaan

### Companies vs Contacts
- `res.company` mirroring `res.partner` via `partner_id`
- Field `gmaps_link` cukup di `res.partner`, otomatis muncul di Companies

### Deploy
```powershell
docker restart e9100216643c
# Lalu upgrade module di Odoo UI
```

---

*Dokumentasi oleh Claude Opus 4.6 — 2026-03-15*
