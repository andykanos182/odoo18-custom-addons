---
name: odoo18-barcode-camera
description: 'Use when: The user wants to add a barcode or QR code camera scanner widget to an Odoo 18 module, or use a device camera to scan barcodes in an OWL view, including draggable floating buttons.'
---

# Odoo 18 Barcode Camera Scanner Implementation

Skill ini memberikan panduan dan standar (SOP) bagi Agen untuk mengimplementasikan fitur pemindaian Barcode via Kamera (OWL component) pada Odoo 18. Skill ini mengambil referensi dari arsitektur terbaru yang kokoh di modul `andykanoz_scaner_barcode_inventory`.

Fitur ini mencakup 2 tipe implementasi:
1. **Form Field Widget**: Tombol kamera di dalam field input form.
2. **Draggable Floating Action Button (FAB)**: Tombol kamera mengambang untuk auto-trigger fitur Search (pencarian) global di list/kanban view.

## Aturan Utama (Guidelines)

### 1. Form Field Widget (`widget`)
Untuk mengubah input teks biasa (Char) menjadi input dengan tombol scanner kamera, selalu gunakan atribut `widget="andykanoz_barcode_scanner"`.
```xml
<!-- Contoh penerapan pada form view -->
<field name="barcode" widget="andykanoz_barcode_scanner" placeholder="Scan Barcode..."/>
```

### 2. Draggable Floating Search Button
Tombol mengambang (FAB) yang digunakan untuk melakukan pencarian barcode secara langsung di Odoo *Search View*.
- **Registrasi Komponen**: Diregistrasikan ke `main_components` agar di-render secara global.
- **Visibilitas (Router)**: Menggunakan `useService("router")` mengecek `this.router.current.hash.model` agar tombol HANYA muncul di model tertentu (misal: `product.template`).
- **Drag & Drop**: Menggunakan pointer events (`onPointerDown`, `onPointerMove`, `onPointerUp`) untuk menggeser posisi koordinat absolut (`state.position.x` & `y`).
- **Trigger Pencarian**: Komponen akan mencari class `.o_searchview_input` secara DOM, mem-focus, menset nilai, men-trigger event `input`, dan kemudian men-trigger event `keydown` (Enter) untuk memulai pencarian.

### 3. Re-implementasi Standalone (Jika diminta membuat ulang di modul terpisah)
Jika pengguna meminta membuat ulang dari awal tanpa dependensi ke `andykanoz_scaner_barcode_inventory`, agen **wajib** meniru pola berikut:
- **Polyfill (iOS Support)**: Wajib menyertakan `zxing_barcode_polyfill.js` sebagai fallback untuk iOS/Safari karena API `window.BarcodeDetector` belum didukung penuh.
- **State & UI**: Kelola state kamera seperti `showModal`, `torchSupported`, `torchOn`, dan `cameraFacing` menggunakan `useState`. Pastikan menggunakan design SCSS dengan animasi yang halus.
- **Update Record / Search**:
  - Untuk Form Field: Perbarui field menggunakan `this.props.record.update({ [this.props.name]: value });`
  - Untuk Global Search: Tuliskan/simulasikan input Enter ke elemen `.o_searchview_input` DOM.
- **Keamanan (HTTPS)**: Ingatkan pengguna di kode bahwa fitur `getUserMedia` kamera hanya berjalan jika Odoo diakses menggunakan protokol `https://` atau di `localhost`.

## Lokasi Referensi Kode (Source of Truth)
Agen **wajib membaca** file-file ini menggunakan *file reader* jika pengguna meminta pembuatan ulang fitur (Standalone):
- **Polyfill (Penting!)**: `andykanoz_scaner_barcode_inventory/static/src/js/zxing_barcode_polyfill.js`
- **Form Field JS & XML**: `andykanoz_scaner_barcode_inventory/static/src/js/barcode_scanner_field.js` dan `.../xml/barcode_scanner_field.xml`
- **Floating Button JS & XML**: `andykanoz_scaner_barcode_inventory/static/src/js/search_barcode_scanner.js` dan `.../xml/search_barcode_scanner.xml`
- **Styling (SCSS)**: `andykanoz_scaner_barcode_inventory/static/src/scss/barcode_scanner.scss`

## Langkah Eksekusi (Jika Skill ini dipicu)
1. Tanyakan kepada pengguna: *"Apakah Anda ingin menambahkan scanner di **Form Field** (widget) atau menambahkan **Floating Search Button** (FAB)?"*
2. Tanyakan juga: *"Apakah Anda ingin menghubungkan (depend) ke modul `andykanoz_scaner_barcode_inventory` atau membuat komponennya secara independen (standalone) di modul Anda?"*
3. Baca file referensi di atas berdasarkan pilihan pengguna, lalu terapkan kodenya dengan penyesuaian *namespace* sesuai nama modul yang baru.
