# DEVELOPMENT NOTES — AndykaNoz Distance Shipping
# Module: andykanoz_distance_shipping
# Author: AndykaNoz
# Odoo Version: 18.0 Community (Docker)
# Last Updated: 2026-03-26
# AI Assistant: Claude Opus 4.6

---

## 1. GAMBARAN UMUM

### Tujuan
Menghitung biaya pengiriman berdasarkan jarak GPS antara toko dan customer
menggunakan Google Distance Matrix API.

### Rumus Biaya (Default)
```
Jika jarak ≤ 3 km → Rp 8.000 (biaya flat/base fee)
Jika jarak > 3 km dan ≤ 5 km → Rp 8.000 + ((jarak - 3) × Rp 2.500)
Jika jarak > 5 km → Tidak melayani delivery
```

### Contoh Perhitungan
- 2 km → Rp 8.000
- 3 km → Rp 8.000
- 4 km → Rp 10.500
- 5 km → Rp 13.000
- 6 km → ❌ Tidak tersedia

---

## 2. ENVIRONMENT

### Docker
- Container ID: e9100216643c
- Odoo: 18.0 Community
- Port: localhost:8018
- Domain: www.gopokaja.com

### API
- Google Distance Matrix API (harus diaktifkan di Google Cloud Console)
- API Key: Settings → Integrations → Geolocation → Key
- Config parameter: `base_geolocalize.google_map_api_key`

### Koordinat
- Toko: dari `res.company` → `partner_id.partner_latitude/longitude`
- Customer: dari `res.partner` → `partner_latitude/longitude`
  (disimpan via peta di /my/account dan /shop/address oleh module andykanoz_google_maps_peta)

---

## 3. STRUKTUR MODULE

```
andykanoz_distance_shipping/
├── __manifest__.py
├── __init__.py
├── DEVELOPMENT_NOTES.md
├── data/
│   └── delivery_carrier_data.xml     ← Carrier default "Pengiriman GoPoKaja"
├── models/
│   ├── __init__.py
│   ├── delivery_carrier.py           ← Delivery type "distance" + rumus biaya + Google API
│   └── res_config_settings.py        ← 4 field konfigurasi di Settings
└── views/
    ├── delivery_carrier_view.xml      ← Form konfigurasi per-carrier
    └── res_config_settings_views.xml  ← UI Settings (2 record):
                                         1. Hapus distance_shipping_params dari dalam Geolocation
                                         2. Buat setting box terpisah di antara Geolocation dan reCAPTCHA
```

---

## 4. DELIVERY TYPE: "distance"

### Pattern Odoo Delivery Provider
Odoo delivery carrier menggunakan pattern `<type>_rate_shipment` untuk hitung biaya.
Module ini menambahkan delivery_type = "distance" dengan method:

| Method | Fungsi |
|--------|--------|
| `distance_rate_shipment(order)` | Hitung biaya kirim berdasarkan jarak GPS |
| `distance_send_shipping(pickings)` | Required interface (no-op) |
| `distance_get_tracking_link(picking)` | Required interface (returns False) |
| `distance_cancel_shipment(pickings)` | Required interface |

### Alur `distance_rate_shipment()`:
```
1. Ambil koordinat toko (company.partner_id.lat/lng)
2. Ambil koordinat customer (order.partner_shipping_id.lat/lng)
3. Panggil Google Distance Matrix API → dapat jarak dalam km
4. Cek jarak vs max_km → jika lebih, return error
5. Hitung biaya berdasarkan rumus
6. Return {success: True, price: biaya, warning: "Jarak: X km"}
```

---

## 5. KONFIGURASI

### Settings → Integrations (Global)
Posisi: Setting box terpisah di antara "Geolocation" dan "reCAPTCHA"

| Parameter | Config Key | Default |
|-----------|-----------|---------|
| Base Fee (Rp) | andykanoz_distance_shipping.base_fee | 8000 |
| Threshold (km) | andykanoz_distance_shipping.threshold_km | 3.0 |
| Fee per KM (Rp) | andykanoz_distance_shipping.per_km_fee | 2500 |
| Max Distance (km) | andykanoz_distance_shipping.max_km | 5.0 |

### Per-Carrier (Shipping Methods form)
Saat delivery_type = "distance", muncul group konfigurasi:
- Base Fee, Threshold, Fee per KM, Max Distance
- Nilai per-carrier override nilai global Settings

### Settings View XML (2 record):
1. `res_config_settings_view_form_distance_shipping`
   - Inherit: `base_geolocalize.res_config_settings_view_form`
   - Fungsi: Hapus `distance_shipping_params` yang lama dari dalam Geolocation
2. `res_config_settings_view_form_distance_shipping_box`
   - Inherit: `base_setup.res_config_settings_view_form`
   - Fungsi: Buat setting box terpisah → xpath `//div[@id='recaptcha']` position="before"

---

## 6. MODULE TERKAIT

| Module | Fungsi | Dependency |
|--------|--------|------------|
| andykanoz_google_maps_peta | Peta Google Maps (portal + backend) | Menyimpan koordinat customer |
| andykanoz_self_pickup_option_1 | Self Pickup checkout + email | - |
| andykanoz_distance_shipping | Biaya kirim berdasarkan jarak | Koordinat dari module peta |

---

## 7. PRASYARAT

- [x] Google Maps API Key sudah diisi di Settings → Integrations → Geolocation
- [x] Google Distance Matrix API sudah diaktifkan di Google Cloud Console
- [x] Koordinat toko sudah diset di Contact Company (Partner Assignment)
- [x] Module andykanoz_google_maps_peta terinstall (untuk customer set koordinat via peta)

---

## 8. CARA DEPLOY

```powershell
docker restart e9100216643c
# Lalu upgrade/install module di Odoo UI
```

---

## 9. CATATAN PENTING

### Jika customer belum set koordinat
- Delivery method "distance" akan return error: "Silakan pilih lokasi Anda di peta terlebih dahulu"
- Customer harus set lokasi via peta di /my/account atau /shop/address

### Biaya dibulatkan
- Biaya dibulatkan ke ratusan terdekat (round to nearest 100)

### Gratis ongkir
- Tidak ada gratis ongkir otomatis berdasarkan total belanja
- Gratis ongkir hanya via voucher/kupon (fitur bawaan Odoo)

---

*Catatan ini dibuat oleh Claude Opus 4.6 pada 2026-03-26*
