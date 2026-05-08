# Development Notes: AndykaNoz Quick Purchase Entry

File ini berisi dokumentasi arsitektur dan alur kerja (workflow) dari module `andykanoz_quick_purchase` untuk mempermudah pemahaman dan pengembangan lebih lanjut (customization) di Odoo 18.

---

## 📦 1. Gambaran Umum Module
- **Nama Module:** AndykaNoz Quick Purchase Entry (`andykanoz_quick_purchase`)
- **Tujuan Utama:** Menyediakan antarmuka (UI) satu halaman khusus berbasis Odoo Web Library (OWL) yang sangat dioptimalkan untuk entri data *Purchase Order* (PO) secara cepat menggunakan **Scanner Barcode** atau **Kamera Perangkat**. 
- **Use Case:** Didesain khusus untuk alur belanja cepat (contoh: *Gopokaja workflow* dimana 1 sesi belanja = 1 vendor seperti Indogrosir).
- **Dependensi Utama:** `base`, `web`, `purchase`, `product`, `uom`.

---

## 🧩 2. Arsitektur & Komponen Utama

Module ini menggunakan pola **SPA (Single Page Application)** yang mem-bypass standard form view Odoo untuk menawarkan UX yang lebih cepat, kemudian di-submit untuk membuat `purchase.order` standar.

### A. Backend (Python / Models)
1. **`quick.purchase.session` (`models/quick_purchase_session.py`)**
   - **Fungsi:** Menyimpan state draft/sesi belanja pengguna ke database. Ini memastikan jika user merefresh browser atau mati listrik, data belanja yang belum disubmit menjadi PO tidak hilang.
   - **Cara Kerja:** Menyimpan array data belanjaan sebagai JSON string (`lines_json`).
2. **`product.product` (`models/product_product.py`)**
   - **Override:** Menambahkan method `get_last_purchase_price(partner_id)`.
   - **Fungsi:** Mencari harga beli historis paling akurat untuk auto-fill harga saat scan. Urutan prioritas: Harga PO terakhir dari vendor tersebut -> Harga di Pricelist Vendor -> Harga Standar/Cost produk.
3. **`purchase.order` (`models/purchase_order.py`)**
   - **Fungsi:** Menambahkan action client (`action_open_quick_purchase`) agar PO existing bisa dibuka kembali menggunakan UI Quick Purchase.

### B. Jembatan Komunikasi (Controllers)
1. **`controllers/main.py`**
   - Bertindak sebagai API JSON-RPC backend yang dikonsumsi oleh OWL Frontend.
   - **Route Utama:**
     - `/andykanoz_quick_purchase/search_product`: Endpoint pencarian pintar (Barcode -> Internal Reference/SKU -> Nama).
     - `/andykanoz_quick_purchase/get_vendors`: Dropdown pencarian vendor.
     - `/andykanoz_quick_purchase/create_po`: Finalisasi, mengubah session UI JSON menjadi baris `purchase.order.line` Odoo yang asli.

### C. Frontend (OWL - JS & XML)
1. **`static/src/js/quick_purchase.js`**
   - Jantung utama module. Mengontrol state aplikasi (menggunakan `useState`).
   - Fitur kompleks yang ditangani JS ini:
     - Manajemen tab sesi draft paralel (Bisa buka banyak draft belanja sekaligus).
     - Scanner input loop & integrasi hardware kamera (*Barcode Detector API*).
     - Validasi duplikasi line (jika barang di-scan dua kali, hanya *Quantity* yang bertambah).
2. **`static/src/xml/quick_purchase.xml`**
   - Template struktur visual aplikasi. Terdiri dari *Session Bar*, *Header (Vendor)*, *Scan Input*, *List Keranjang Belanja*, dan *Quick Create Product Modal*.

---

## 🔄 3. Alur Kerja Aplikasi (Workflow)

1. **Pembuatan Sesi:** User membuka menu *Quick Purchase Entry*, UI langsung membuat "New Draft" session.
2. **Kunci Vendor:** User wajib memilih 1 Vendor. Saat produk pertama ditambahkan ke keranjang, Vendor akan **di-lock** untuk sesi tersebut.
3. **Proses Scanning:**
   - User melakukan scan barcode (via scanner gun yang otomatis trigger 'Enter' atau menggunakan tombol kamera).
   - *Client* menembak ke controller `search_product`.
   - Jika ketemu: Masuk ke list belanja, otomatis cari harga terakhir dari vendor ini.
   - Jika **tidak ketemu**: Akan muncul popup **Quick Create Modal** agar user bisa langsung membuat master produk baru di tempat (nama, barcode, harga beli, kategori) tanpa harus pindah halaman.
4. **Finalisasi:** User menekan "Create Purchase Order". Controller membuat record di tabel `purchase.order` beserta line-nya, lalu me-redirect layar Odoo user masuk ke form tampilan standar PO tersebut.

---

## 💡 4. Insight Penting untuk Pengembangan Lanjutan (Customization)

- **Menambahkan Field Baru pada Line Belanja:** 
  Jika Anda perlu menambah field baru (misal: *Expired Date*), Anda harus menambahkan field tersebut di 3 tempat secara sekuensial:
  1. Di *state object* JS (struktur `lines` di dalam `quick_purchase.js`).
  2. Di tampilan tabel UI (`quick_purchase.xml`).
  3. Saat mapping data di Controller `create_po` (di `main.py` untuk di-inject ke `purchase.order.line`).
- **Debugging UI / OWL:** Module ini sangat reaktif (state-driven). Developer sebelumnya telah menambahkan utilitas debug di `setup()` (menangkap event `unhandledrejection` dan `error` ke console logger `[QP-DEBUG]`). Selalu buka F12 Browser Console ketika men-debug UI module ini.
- **Batasan Asli Odoo:** Pada file Python, disebutkan bahwa `discount_amount` (diskon nominal per baris) belum disupport secara native di purchase order tanpa module tambahan (Odoo standar hanya menggunakan diskon persentase). Logic kalkulasinya sekarang dihandle oleh Javascript lalu dikonversi secara matematis menjadi presentase.

