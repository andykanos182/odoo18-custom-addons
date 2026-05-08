# Analisa dan Rencana Pengembangan: POS Upsell & Cross-Sell

## 1. Analisa Product Configurator Modal (Attribute Selection)
Modal yang Anda lampirkan (`Attribute selection`) adalah modal bawaan Odoo POS yang muncul saat kita memilih produk yang memiliki beberapa varian (atribut seperti Ukuran, Rasa, Jenis Daging, dll). 
Di Odoo 18, komponen ini ditangani oleh `ProductConfiguratorPopup`.

### Komponen Utama Pembentuk Modal:
1. **XML Template (`product_configurator_popup.xml`)**:
   - Memiliki `<Dialog>` dengan `title.translate="Attribute selection"`.
   - Menampilkan `ProductInfoBanner` (Nama Produk, Harga, VAT) yang dirender di bagian atas (`section-product-info-title`).
   - Loop melalui `attribute_line_ids` produk, dan memanggil komponen spesifik berdasarkan tampilannya (contoh: `<RadioProductAttribute>`, `<SelectProductAttribute>`, `<ColorProductAttribute>`).

2. **JavaScript Controller (`product_configurator_popup.js`)**:
   - Class `ProductConfiguratorPopup` yang mewarisi `Component` OWL.
   - Menyimpan `state.payload` yang mencatat nilai atribut yang dipilih user.
   - Fungsi `confirm()` akan mengumpulkan kombinasi atribut, lalu mengirimkannya kembali (`getPayload`) ke layar utama (`ProductScreen`) agar Odoo POS tahu `product.product` (varian spesifik) mana yang sebenarnya harus dimasukkan ke dalam keranjang.

---

## 2. Analisa Upsell & Cross-Sell (Optional / Accessory Products)
Dari gambar yang dilampirkan, fitur **Optional Products** dan **Accessory Products** adalah fitur bawaan eCommerce / Sales Odoo:
- **Optional Products (`optional_product_ids`)**: Muncul sebagai sugesti saat customer memasukkan produk ke keranjang (Add to Cart). Tujuannya untuk cross-sell langsung (misal: Beli Laptop -> Ditawari Garansi atau Mouse).
- **Accessory Products (`accessory_product_ids`)**: Muncul saat customer me-review keranjang sebelum pembayaran.

### Tujuan Pengembangan Kita
Kita akan mereplikasi logika "Optional Products" ini ke dalam Point of Sale. 
Alur kerja yang diharapkan:
1. Kasir tap produk utama (misal: "Paket Hemat Burger").
2. Jika produk utama punya atribut (varian), muncul `ProductConfiguratorPopup` seperti biasa.
3. Setelah varian dipilih **ATAU** jika produk tidak punya varian, kita cek: *Apakah produk ini memiliki `optional_product_ids`?*
4. Jika ADA, kita **munculkan Popup Baru (misal: `PosCrossSellPopup`)** yang menampilkan daftar produk opsional.
5. Kasir bisa dengan cepat klik "Add" untuk menambahkan produk opsional tersebut ke pesanan pelanggan, lalu klik "Confirm" untuk menutup popup.

---

## 3. Rencana Teknis Pengembangan (Roadmap)

### Langkah 1: Backend (Python & XML)
1. **Extend `product.template` (jika belum ada)**: Memastikan field `optional_product_ids` dan `accessory_product_ids` bisa dibaca oleh module Point of Sale. (Biasanya field ini ada dari module `website_sale` atau `sale_management`, kita bisa menjadikannya field yang di-load oleh POS).
2. **Load Field ke POS Session**: Menggunakan `pos.session` _loader untuk memasukkan `optional_product_ids` ke model `product.product` / `product.template` di data JavaScript POS.

### Langkah 2: Frontend (OWL Component - XML)
1. Membuat template `pos_cross_sell_popup.xml`:
   - Struktur akan mirip dengan modal Attribute Selection (`<Dialog>`).
   - Memiliki judul "Suggested Products" atau "Beli Juga?".
   - Menampilkan daftar produk opsional dalam bentuk grid/list yang rapi.
   - Tombol "Add" pada setiap produk opsional.
   - Tombol "Skip / Continue" di bagian bawah untuk lanjut tanpa menambah opsi.

### Langkah 3: Frontend (OWL Component - JS)
1. Membuat `pos_cross_sell_popup.js`:
   - Extend dari `@web/core/dialog/dialog`.
   - Fungsi ketika klik "Add" akan memanggil metode keranjang POS untuk memasukkan produk tambahan tersebut.
2. **Hook (Patch) `ProductScreen` atau `Order` model**:
   - Patch fungsi `addProductToCurrentOrder` atau saat klik produk di `ProductScreen.js`.
   - Logika: `await super.addProductToCurrentOrder(...)` -> lalu cek `if (product.optional_product_ids.length > 0)` -> Munculkan `PosCrossSellPopup`.

### Catatan Penting untuk Odoo 18:
- Odoo 18 sangat ketat soal props (OWL 2 strict props). Jadi saat memanggil popup baru lewat `this.env.services.dialog.add(PosCrossSellPopup, { ... })`, pastikan semua props terdefinisi di `static props`.
- Data `product` di frontend Odoo 18 berada di `this.pos.models['product.product']` atau `this.pos.models['product.template']`.

File ini dapat digunakan sebagai acuan saat kita akan mulai melakukan coding implementasinya.
