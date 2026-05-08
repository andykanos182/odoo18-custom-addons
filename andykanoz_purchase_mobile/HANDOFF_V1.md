# HANDOFF V1 — andykanoz_purchase_mobile

**Status:** Planning / Pre-Implementation
**Created:** 21 April 2026
**Target:** Odoo 18 Community
**Module Path:** `D:\MyServer\Odoo18\Addons\andykanoz_purchase_mobile`

---

## 1. Module Identity

| Field | Value |
|---|---|
| Technical name | `andykanoz_purchase_mobile` |
| Display name | Purchase Mobile |
| Version | 18.0.1.0.0 |
| Category | Purchases |
| Target | Odoo 18 Community |
| Author | Andykanoz (Gopokaja) |
| Deployment | Docker on Windows host + Cloudflare Tunnel (`www.gopokaja.com` / `nitro.gopokaja.com`) |

---

## 2. Purpose

Menggantikan tampilan default purchase order Odoo di perangkat mobile (yang cluttered & menampilkan field `taxes` yang tidak relevan untuk Gopokaja) dengan halaman OWL Client Action standalone yang:

- Mobile-first, card-based, touch-friendly.
- Hanya menampilkan field yang dibutuhkan staff gudang: **Foto Produk, Qty, UoM, Packaging, Unit Price, Tanggal Expired, Subtotal**.
- Installable sebagai Progressive Web App (PWA) — seperti flow "Install App" POS Odoo — supaya muncul sebagai shortcut di home screen HP.
- Bisa create / edit draft PO, lalu confirm untuk konversi ke PO standar Odoo (flow receipt/invoice tetap mengikuti core Odoo).

---

## 3. Scope

### In Scope
- Create new Purchase Order (draft state).
- Edit existing draft Purchase Order.
- Line items dengan field: foto produk, qty, UoM, packaging, unit price, expected expiry date, subtotal.
- Vendor selection (single vendor per PO, lock setelah line pertama).
- Confirm PO → call `action_confirm` standar Odoo.
- PWA manifest + service worker untuk install-to-home-screen.
- Barcode scanner (camera) untuk tambah produk cepat (reuse pattern dari `andykanoz_quick_purchase`).

### Out of Scope (V1)
- Taxes display / editing — **sengaja disembunyikan**.
- Discount per line (bisa ditambahkan di V2).
- Approval workflow (pakai workflow Odoo standar setelah confirm).
- Receipt / bill / invoice — pakai form Odoo standar.
- Offline mode / optimistic UI tanpa internet (revisit di V2 kalau dibutuhkan).
- Multi-vendor per PO.

---

## 4. Decisions Locked In

Berikut keputusan yang sudah difinalisasi Andyka via chat (jangan diubah tanpa diskusi baru):

| # | Topik | Keputusan |
|---|---|---|
| A | Arsitektur | **Full custom OWL Client Action** (Opsi 2), bukan inherit form view standar |
| B | Expiry date | **Hybrid** — reuse flag `use_expiration_date` dari `product_expiry` (native), tambah field custom `x_expected_expiry_date` di `purchase.order.line`, propagate ke `stock.lot` saat receipt |
| C | Packaging | **Standard `product.packaging`** — pakai field `product_packaging_id` yang sudah ada di `purchase.order.line` Odoo 18 |
| D | Menu placement | Menu **"Purchase Mobile"** di bawah parent Purchase, **PWA-installable** seperti POS |
| E | Module name | `andykanoz_purchase_mobile` |
| F | Taxes | **Hidden** dari UI (line card dan footer total) |
| G | PO Sequence | **Custom sequence `MP00xxx`** — PO yang dibuat dari Purchase Mobile pakai prefix sendiri, bukan `PO00xxx` standar |

---

## 5. Expiry Strategy (Detail)

Hasil riset Odoo 18 Community:

- Odoo menyimpan `expiration_date` di model **`stock.lot`**, **bukan** di `purchase.order.line`.
- Field `use_expiration_date` ada di `product.template` (disediakan oleh module `product_expiry` yang bundled di Community).
- Bila `use_expiration_date = True` di product, product wajib tracking by lot/serial.
- Flow native: PO confirm → Receipt (stock.picking) created → saat validate receipt, user input Lot + expiration_date di popup detail line. Expiration date **bisa** auto-compute dari `product.expiration_time` (days after receipt).
- **Tidak ada** field expiry di `purchase.order.line` — makanya harus custom.

### Strategy untuk module ini

1. **Tambah field custom** `x_expected_expiry_date = fields.Date()` di `purchase.order.line`.
2. **UI conditional**: expiry input muncul di line card hanya kalau:
   - `product.product.use_expiration_date == True`, **ATAU**
   - `product.product` punya field custom `x_requires_expiry` yang user-set (fallback kalau `product_expiry` tidak ter-install).
3. **Propagation ke stock.lot**: override `stock.move.line._action_done()` (atau `_create_lot` helper) — saat receipt divalidasi, cari `purchase_line_id.x_expected_expiry_date`, assign ke `lot.expiration_date` yang baru dibuat.
4. **Graceful fallback**: cek `hasattr(self.env['product.template'], 'use_expiration_date')` saat loading. Kalau module `product_expiry` belum ter-install, UI tetap izinkan input expiry (simpan di `x_expected_expiry_date`), tapi skip propagation ke lot.
5. **Visual state di UI** (sesuai mockup chat):
   - Tanpa expiry / product non-perishable → badge **gray**: "Tanpa expired"
   - Expiry > 60 hari dari hari ini → badge **amber**: "Exp: DD Mmm YYYY"
   - Expiry ≤ 60 hari dari hari ini → badge **merah** + ⚠: "Exp: DD Mmm YYYY · dekat"
   - Threshold 60 hari konfigurable via `ir.config_parameter` `andykanoz_purchase_mobile.expiry_warning_days` (default 60).

---

## 6. Architecture Overview

Pola acuan: **`andykanoz_quick_purchase`** (yang Andyka sudah familiar).

```
┌────────────────────────────────────────────────────────────┐
│  Browser (Chrome Mobile / PWA shell)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  OWL Root: PurchaseMobileApp                         │  │
│  │  ├─ POList (daftar draft PO)                         │  │
│  │  └─ POEditor                                         │  │
│  │     ├─ VendorPicker (custom autocomplete)            │  │
│  │     ├─ LineCard[] (card per line — sesuai mockup)    │  │
│  │     ├─ ProductPicker (modal + barcode scan)          │  │
│  │     └─ Footer (Untaxed + Total)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                       ↕ JSON-RPC                           │
└────────────────────────────────────────────────────────────┘
                        ↕
┌────────────────────────────────────────────────────────────┐
│  Odoo Backend                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Controllers: /andykanoz_purchase_mobile/api/*       │  │
│  │  Models: purchase.order.line (ext),                  │  │
│  │          stock.move.line (ext for propagation)       │  │
│  │  Menu + ir.actions.client                            │  │
│  │  QWeb template: app shell + SW register              │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                        ↕
┌────────────────────────────────────────────────────────────┐
│  PWA Layer                                                 │
│  /andykanoz_purchase_mobile/manifest.json                  │
│  /andykanoz_purchase_mobile/service-worker.js              │
└────────────────────────────────────────────────────────────┘
```

### Deployment mode decision

**RECOMMENDED: Standalone PWA page** (bukan embedded dalam Odoo backend chrome).

Alasan:
- POS Odoo pakai pattern ini → ada precedent bagus.
- PWA install experience lebih bersih (full-screen, no Odoo topbar).
- Mobile-first feel lebih kuat.

Artinya: route `/andykanoz_purchase_mobile/app` render HTML template sendiri (bukan `web.webclient_bootstrap`), load OWL runtime minimal + komponen module. Auth tetap pakai session Odoo (redirect ke `/web/login` kalau belum login).

> **⚠ Perlu konfirmasi Andyka** — lihat Section 14 Q1.

---

## 7. Planned File Structure

```
andykanoz_purchase_mobile/
├── __init__.py
├── __manifest__.py
├── README.md
├── HANDOFF_V1.md                           ← dokumen ini
│
├── models/
│   ├── __init__.py
│   ├── purchase_order_line.py              # x_expected_expiry_date
│   ├── product_template.py                 # x_requires_expiry fallback
│   └── stock_move_line.py                  # propagate expiry ke lot
│
├── controllers/
│   ├── __init__.py
│   ├── main.py                             # JSON-RPC endpoints
│   └── pwa.py                              # manifest.json + service-worker.js
│
├── views/
│   ├── purchase_mobile_action.xml          # ir.actions.client
│   ├── purchase_mobile_menu.xml            # menu di bawah Purchase
│   └── purchase_mobile_templates.xml       # QWeb: app shell HTML
│
├── security/
│   └── ir.model.access.csv
│
├── data/
│   ├── ir_config_parameter.xml             # default expiry_warning_days = 60
│   └── ir_sequence.xml                     # sequence MP00001+ untuk PO dari mobile
│
└── static/
    ├── description/
    │   ├── icon.png
    │   └── index.html
    │
    ├── src/
    │   ├── js/
    │   │   ├── purchase_mobile_app.js       # root component + registry
    │   │   ├── services/
    │   │   │   ├── rpc_service.js           # wrapper JSON-RPC
    │   │   │   └── state_store.js           # reactive state (useState pattern)
    │   │   └── components/
    │   │       ├── po_list.js
    │   │       ├── po_editor.js
    │   │       ├── line_card.js
    │   │       ├── product_picker.js
    │   │       ├── vendor_picker.js         # reuse pattern dari quick_purchase
    │   │       ├── qty_stepper.js
    │   │       ├── expiry_input.js
    │   │       └── barcode_scanner.js       # reuse pattern dari quick_purchase
    │   │
    │   ├── xml/
    │   │   ├── purchase_mobile_app.xml
    │   │   └── components/
    │   │       ├── po_list.xml
    │   │       ├── po_editor.xml
    │   │       ├── line_card.xml
    │   │       ├── product_picker.xml
    │   │       ├── vendor_picker.xml
    │   │       ├── qty_stepper.xml
    │   │       ├── expiry_input.xml
    │   │       └── barcode_scanner.xml
    │   │
    │   └── scss/
    │       └── purchase_mobile.scss
    │
    └── pwa/
        ├── icon-192.png
        ├── icon-512.png
        └── (manifest.json + sw.js dynamically served via controller)
```

---

## 8. Models (Backend)

### 8.0 `purchase.order` — sequence handling

PO yang dibuat via Purchase Mobile pakai sequence custom `andykanoz.purchase.mobile` (prefix `MP`). Implementasi di controller saat create:

```python
# controllers/main.py (excerpt)
name = request.env['ir.sequence'].next_by_code('andykanoz.purchase.mobile') or '/'
po = request.env['purchase.order'].create({
    'name': name,
    'partner_id': vendor_id,
    'x_created_via_mobile': True,  # flag untuk identifikasi
    ...
})
```

Field `x_created_via_mobile` (Boolean) ditambah di `purchase.order` untuk:
- Tracking / reporting (filter PO yang lahir dari mobile).
- Optional: conditional logic di UI backend (misal tombol "Edit di Mobile" yang buka langsung ke app).

Sequence record (`data/ir_sequence.xml`):

```xml
<record id="seq_andykanoz_purchase_mobile" model="ir.sequence">
    <field name="name">Purchase Mobile Order</field>
    <field name="code">andykanoz.purchase.mobile</field>
    <field name="prefix">MP</field>
    <field name="padding">5</field>
    <field name="number_next">1</field>
    <field name="number_increment">1</field>
</record>
```

Hasil: `MP00001`, `MP00002`, dst.

### 8.1 `purchase.order.line` — extend

```python
# models/purchase_order_line.py
from odoo import fields, models

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    x_expected_expiry_date = fields.Date(
        string="Expected Expiry Date",
        help="Tanggal kadaluarsa yang diharapkan untuk batch produk ini. "
             "Akan dipropagasi ke stock.lot saat receipt divalidasi."
    )
```

**Catatan:**
- Field `product_packaging_id` dan `product_packaging_qty` sudah ada di Odoo 18 `purchase.order.line` → **tidak perlu ditambah**.
- Jangan bikin field baru untuk UoM / unit price / qty — sudah standar.

### 8.2 `product.template` — optional fallback

```python
# models/product_template.py
from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_requires_expiry = fields.Boolean(
        string="Requires Expiry Input on Purchase",
        help="Centang jika product butuh input tanggal expired di Purchase Mobile, "
             "meskipun tidak tracking by lot. Akan di-override otomatis ke True "
             "jika use_expiration_date aktif."
    )
```

### 8.3 `stock.move.line` — propagate expiry ke lot

```python
# models/stock_move_line.py
from odoo import models
from odoo.tools import float_is_zero

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _create_and_assign_production_lot(self):
        # override / extend existing lot creation to set expiration_date
        # from linked purchase.order.line.x_expected_expiry_date
        ...
```

> Detail implementasi propagasi — cek source `product_expiry/models/stock_production_lot.py` dulu untuk tahu hook yang tepat. Kemungkinan override `_action_done` di `stock.move.line`.

---

## 9. Controllers — JSON-RPC Endpoints

Semua endpoint di-mount di prefix `/andykanoz_purchase_mobile`, auth=`user`, type=`json`, csrf=`False`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/andykanoz_purchase_mobile/app` | Render app shell HTML (public-facing, redirect login kalau belum auth) |
| POST | `/andykanoz_purchase_mobile/api/vendors` | `name_search` partners dengan context `res_partner_search_mode='supplier'` (pattern dari quick_purchase fix) |
| POST | `/andykanoz_purchase_mobile/api/products/search` | Search by barcode / default_code / name, return list dengan photo, uoms, packagings, requires_expiry |
| POST | `/andykanoz_purchase_mobile/api/products/detail` | Full detail single product (kalau perlu lazy-load) |
| POST | `/andykanoz_purchase_mobile/api/pos/list` | List draft PO milik user (atau semua, tergantung group) |
| POST | `/andykanoz_purchase_mobile/api/po/get` | Get single PO + semua line |
| POST | `/andykanoz_purchase_mobile/api/po/save` | Create atau update draft PO (body: po_id nullable, vendor_id, lines[]). **Saat create baru, name pakai sequence `andykanoz.purchase.mobile` (prefix `MP`)** |
| POST | `/andykanoz_purchase_mobile/api/po/confirm` | Call `action_confirm()` di PO |
| POST | `/andykanoz_purchase_mobile/api/po/delete` | Unlink draft PO |
| GET | `/andykanoz_purchase_mobile/manifest.json` | Serve PWA manifest dinamis |
| GET | `/andykanoz_purchase_mobile/service-worker.js` | Serve SW JS dinamis (bisa inject cache version) |

### Price lookup untuk produk baru ditambahkan

Reuse three-tier fallback dari `andykanoz_quick_purchase`:
1. Recent `purchase.order.line` dari vendor yang sama (sorted by `create_date desc`, limit 1).
2. `product.supplierinfo` (`seller_ids`) untuk vendor itu.
3. `product.standard_price`.

---

## 10. OWL Component Tree (Detail)

```
PurchaseMobileApp (root, useState: view, currentPoId, vendor, lines[], products cache)
├── [view == 'list']
│   └── POList
│       ├── POListHeader ("New PO" button → view='editor', currentPoId=null)
│       └── POListItem[] (tap → view='editor', currentPoId=item.id)
│
└── [view == 'editor']
    └── POEditor
        ├── EditorHeader (back, PO ref, state, save btn, confirm btn)
        ├── VendorPicker (locked after first line)
        │   └── CustomAutocomplete (input + dropdown, t-on-mousedown pattern)
        ├── LineCard[]
        │   ├── ProductThumb (product.image_128 atau placeholder)
        │   ├── ProductNameRow (name + subtotal)
        │   ├── ExpiryBadge (conditional, 3 states)
        │   ├── DetailsGrid (2×2)
        │   │   ├── QtyStepper + UoMSelect
        │   │   ├── PackagingSelect
        │   │   ├── UnitPriceInput
        │   │   └── SubtotalReadout
        │   └── RemoveBtn (swipe atau icon x)
        ├── AddLineButton → opens ProductPicker modal
        ├── ProductPicker (modal)
        │   ├── SearchInput (debounced)
        │   ├── BarcodeScannerButton (camera)
        │   └── ResultList → tap = add line
        └── Footer (Untaxed: xxx, Total: xxx — no tax breakdown)
```

### Reactive state

- Pakai `useState` + `useSubEnv` untuk share store.
- State shape:
  ```js
  {
    view: 'list' | 'editor',
    currentPo: { id, name, state, vendor_id, lines: [...] } | null,
    productCache: Map<product_id, product_detail>,
    ui: { saving: false, confirming: false, productPickerOpen: false, scannerOpen: false },
  }
  ```

---

## 11. PWA Setup

### 11.1 `manifest.json` (served via controller)

```json
{
  "name": "Gopokaja Purchase Mobile",
  "short_name": "Purchase",
  "start_url": "/andykanoz_purchase_mobile/app",
  "scope": "/andykanoz_purchase_mobile/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#ffffff",
  "theme_color": "#1a2332",
  "icons": [
    { "src": "/andykanoz_purchase_mobile/static/pwa/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/andykanoz_purchase_mobile/static/pwa/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

### 11.2 `service-worker.js`

- Scope: `/andykanoz_purchase_mobile/`
- Strategy:
  - App shell (HTML, JS, CSS, icons) → **cache-first**, versioned.
  - API calls (`/api/*`) → **network-only** (tidak ada offline mode di V1).
- Cache version constant `SW_VERSION = 'v1'` — bump manual saat deploy.

### 11.3 Cache busting

- Pattern sama seperti `andykanoz_kitchen_notify`: append `?v=SW_VERSION` di query string SW registration URL untuk bypass Cloudflare Tunnel aggressive caching.
- Contoh di HTML template:
  ```html
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/andykanoz_purchase_mobile/service-worker.js?v=1', {
        scope: '/andykanoz_purchase_mobile/'
      });
    }
  </script>
  ```

### 11.4 Install flow (user)

1. Buka `https://nitro.gopokaja.com/andykanoz_purchase_mobile/app` di Chrome Android.
2. Login Odoo (redirect + kembali).
3. Chrome auto-prompt "Add Purchase to Home Screen" setelah beberapa detik interaksi (kalau manifest valid).
4. User tap → shortcut muncul di home screen dengan icon Gopokaja.
5. Tap shortcut → open standalone mode (tanpa address bar).

---

## 12. Menu & Action

### 12.1 `ir.actions.client`

```xml
<record id="action_purchase_mobile" model="ir.actions.act_url">
    <field name="name">Purchase Mobile</field>
    <field name="url">/andykanoz_purchase_mobile/app</field>
    <field name="target">self</field>
</record>
```

> Pakai `act_url` (bukan `ir.actions.client`) supaya klik menu langsung navigate ke URL standalone, bukan render dalam webclient. Ini pattern POS.

### 12.2 Menu entry

```xml
<menuitem
    id="menu_purchase_mobile"
    name="Purchase Mobile"
    parent="purchase.menu_purchase_root"
    action="action_purchase_mobile"
    sequence="5"/>
```

Parent `purchase.menu_purchase_root` adalah menu root "Purchase" di home Odoo.

---

## 13. Implementation Phases

| Phase | Deliverable | Est. effort |
|---|---|---|
| **1** | Module skeleton: `__manifest__`, `__init__`, menu, action, hello-world HTML template. Install & menu muncul. | Small |
| **2** | Models: `x_expected_expiry_date`, `x_requires_expiry`. Controllers: vendors, products/search, pos/list, po/get. Test via curl/Postman. | Medium |
| **3** | OWL app shell + `PurchaseMobileApp` root + `POList` view (read-only list) + `VendorPicker` custom autocomplete. | Medium |
| **4** | `POEditor` + `LineCard` matching mockup (qty stepper, UoM, packaging, unit price, subtotal). `ProductPicker` modal. | Large |
| **5** | Expiry integration: conditional input, badge states, `stock.move.line` propagation ke lot. | Medium |
| **6** | `po/save` + `po/confirm` endpoints + save UX + error handling. | Medium |
| **7** | PWA: manifest, service worker, icon assets, install flow test di Chrome Android. | Small |
| **8** | Barcode scanner (reuse dari `quick_purchase`). SCSS polish. End-to-end test via Cloudflare tunnel. | Small-Medium |

Setelah setiap phase: commit + deploy + smoke test oleh Andyka sebelum lanjut.

---

## 14. Open Questions — Butuh Keputusan Andyka

| # | Pertanyaan | Rekomendasi Claude |
|---|---|---|
| Q1 | Mode deployment: **standalone page** (no Odoo chrome, mirip POS) atau **backend-embedded** (di dalam webclient Odoo)? | **Standalone** — lebih sesuai untuk PWA install experience |
| Q2 | Threshold "near expiry" untuk badge merah: 60 hari? Atau configurable di setting? | Default 60 hari, **configurable** via `ir.config_parameter` |
| Q3 | Siapa yang boleh akses Purchase Mobile? Group `purchase.group_purchase_user` saja, atau bikin group baru? | Group Odoo standar `purchase.group_purchase_user` |
| Q4 | Barcode scanner camera di V1 atau defer ke V2? | **V1** — reuse pattern quick_purchase, effort kecil |
| Q5 | Offline mode / draft di localStorage kalau tidak ada internet? | **Tidak di V1** — tambah complexity, revisit nanti |
| Q6 | Default packaging saat add line: pre-select pertama atau kosong? | Pre-select packaging pertama kalau produk punya packagings |
| Q7 | Vendor lock: setelah line pertama ditambah, vendor di-lock (tidak bisa diubah)? Atau bisa diubah dengan konfirmasi? | Lock setelah line pertama (pattern quick_purchase), user harus hapus semua line dulu untuk ganti vendor |
| Q8 | Nama PO dari sequence Odoo standar (`PO00xxx`) atau sequence custom (`MP00xxx`)? | ✅ **CONFIRMED: Custom sequence `MP00xxx`** — supaya jelas bedanya PO dari mobile vs desktop. Butuh `ir.sequence` record baru di `data/ir_sequence.xml` |

---

## 15. Risks & Dependencies

| Risk | Mitigation |
|---|---|
| Module `product_expiry` belum ter-install | Detect via `hasattr`, fallback ke `x_requires_expiry` custom flag, skip lot propagation |
| Cloudflare Tunnel cache aggressive SW & manifest | Bust dengan `?v=SW_VERSION` query param, set `Cache-Control: no-cache` di response header controller |
| Service Worker scope mismatch (trailing slash) | Scope harus persis `/andykanoz_purchase_mobile/`, start_url `/andykanoz_purchase_mobile/app` — verify di DevTools Application tab |
| OWL `t-on-change` inline arrow handler bug (sudah ditemui di modul sebelumnya) | Pakai method handler explicit, jangan inline arrow |
| Product tanpa `image_128` → thumbnail kosong | Fallback ke SVG placeholder generik |
| `purchase_line_id` tidak selalu ada di `stock.move.line` | Guard dengan `if self.move_id.purchase_line_id`, skip kalau bukan dari PO |
| Barcode scanner kompatibilitas browser (iOS Safari gak support BarcodeDetector) | Fallback ke manual search input (sama seperti quick_purchase) |

---

## 16. Testing Checklist (untuk diisi per phase)

### Smoke tests (Phase 1)
- [ ] Module install clean di dev DB
- [ ] Menu "Purchase Mobile" muncul di bawah parent Purchase
- [ ] Klik menu → navigate ke `/andykanoz_purchase_mobile/app`
- [ ] Tampil app shell (hello world)

### Backend tests (Phase 2)
- [ ] Field `x_expected_expiry_date` ada di `purchase.order.line`
- [ ] Endpoint `/api/vendors` return list supplier
- [ ] Endpoint `/api/products/search` return hits dengan photo & packagings
- [ ] Endpoint `/api/pos/list` return draft PO user

### Functional tests (Phase 4-6)
- [ ] Create PO baru dari zero → pilih vendor → tambah 3 line → save → status Draft
- [ ] Edit draft PO existing → update qty → save → persist
- [ ] Confirm PO → state berubah `purchase`, receipt ter-create
- [ ] Expiry field muncul hanya untuk produk dengan `use_expiration_date=True` atau `x_requires_expiry=True`
- [ ] Badge merah muncul untuk expiry < 60 hari, amber > 60 hari, gray kalau tidak ada
- [ ] Receipt validate → `stock.lot.expiration_date` ter-set dari `x_expected_expiry_date`

### PWA tests (Phase 7)
- [ ] `manifest.json` valid (Lighthouse PWA audit)
- [ ] Service worker terregister (DevTools → Application → Service Workers)
- [ ] Cache app shell berisi file yang diharapkan
- [ ] "Add to Home Screen" prompt muncul di Chrome Android
- [ ] Launch dari home screen → standalone mode (no address bar)

### Production tests
- [ ] Akses via `https://nitro.gopokaja.com/andykanoz_purchase_mobile/app` berhasil
- [ ] Login Odoo → redirect kembali ke app
- [ ] Install ke home screen dari Cloudflare Tunnel URL
- [ ] Bust cache saat deploy versi baru (bump SW_VERSION)

---

## 17. Next Steps

1. **Andyka review handoff ini + jawab Section 14 Q1–Q8**.
2. Setelah konfirmasi, Claude bikin **Phase 1 skeleton** (module installable dengan menu + hello-world page).
3. Verifikasi Phase 1 di dev → lanjut Phase 2.
4. Jika ada perubahan scope / keputusan major di tengah jalan → **bikin HANDOFF_V2.md**, jangan edit V1.

---

## 18. Critical Discoveries (Phase 3 Debug)

Selama implementasi Phase 3, kami menemukan bahwa Odoo 18 standalone page **tidak boleh** pakai OWL's raw `mount()` dari `@odoo/owl`. Pola yang benar:

```javascript
import { whenReady } from "@odoo/owl";
import { mountComponent } from "@web/env";
import { MyRootComponent } from "./my_root";

whenReady(async () => {
    const rootEl = document.getElementById("app");
    if (!rootEl) return;
    await mountComponent(MyRootComponent, rootEl, {
        props: { /* ... */ },
        dev: true,
        name: "MyApp",
    });
});
```

`mountComponent` dari `@web/env` internal handle:
- `makeEnv()` + `await startServices(env)` — wire up service registry
- `getTemplate` dari `@web/core/templates`
- `translateFn` (the `_t` function) dari `@web/core/l10n/translation`
- `warnIfNoStaticProps: true`

Tanpa ini, mount() akan **hang silently** setelah semua `setup()` component selesai — no error, no resolution. Gejala: console log `Owl is running in 'dev' mode` tapi tidak ada render, DOM kosong. Component `setup()` fire tapi `onMounted` tidak pernah fire.

**Template-prop callback pattern**: gunakan `.bind` suffix, bukan inline arrow:

```xml
<!-- WRONG (tidak error tapi tidak always work) -->
<VendorPicker onSelect="(v) => this.onVendorSelected(v)"/>

<!-- CORRECT -->
<VendorPicker onSelect.bind="onVendorSelected"/>
```

**Asset bundle**: pakai `web.assets_frontend` langsung, jangan bikin custom bundle dengan `('include', 'web.assets_frontend')` — custom bundle tidak auto-register XML templates ke global registry.

**Import**: `getTemplate` harus dari `@web/core/templates`, **bukan** `templates` dari `@web/core/assets` (yang latter tidak exist di Odoo 18).

**Duplicate mount guard**: `main.js` di `web.assets_frontend` bisa di-parse >1x per page. Tambah idempotency guard via `dataset`:
```javascript
if (rootEl.dataset.pmMounted === "1") return;
rootEl.dataset.pmMounted = "1";
```

---

## 19. Referensi Internal

Pattern & code reuse dari module Gopokaja existing:
- **`andykanoz_quick_purchase`** — arsitektur OWL Client Action, JSON-RPC controllers, barcode scanner, vendor picker custom autocomplete (t-on-mousedown fix), price three-tier fallback
- **`andykanoz_kitchen_notify`** — PWA service worker pattern, Cloudflare Tunnel cache busting via `?v=SW_VERSION`
- **`andykanoz_product_checker`** — product search, photo display, ecommerce categories

Pattern Odoo core:
- `addons/point_of_sale/` — standalone PWA page pattern (QWeb template yang bootstrap OWL di luar webclient)
- `addons/product_expiry/` — flag `use_expiration_date` dan integrasi `stock.lot.expiration_date`

---

*End of HANDOFF V1*
