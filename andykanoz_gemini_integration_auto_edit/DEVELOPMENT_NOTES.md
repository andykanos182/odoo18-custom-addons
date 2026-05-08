# Module Context & Development Notes: AndykaNoz Gemini Integration Auto Edit

## Deskripsi Module
Module ini digunakan untuk menghapus background gambar produk dan menggantinya dengan background putih secara otomatis menggunakan API **Gemini AI**.
Mendukung eksekusi single product (lewat form view) maupun bulk action (lewat list view) hingga 50 produk sekaligus.

## Fitur Utama
1. **Single Action:** Tombol **Auto White BG** pada Form View produk.
2. **Bulk Action:** Opsi **Auto White BG (Bulk)** pada menu Actions di List View (memproses multiple produk di background).
3. **Background Job System:** Bulk action berjalan sebagai background job menggunakan Cron dan memberi notifikasi progres ke frontend secara real-time via Odoo Bus.
4. **Systray Icon & Progress Dialog:** Terdapat ikon di navbar (systray) untuk memantau status job yang sedang berjalan dan dialog progres ketika batch dimulai.
5. **Quota Management:** Terdapat pengaturan API key dan batasan kuota harian (daily limit) di menu Settings > General Settings untuk menghindari over-limit dari API Gemini.

## Dependensi
Module ini membutuhkan modul standar Odoo berikut:
- **product**: Modul core untuk integrasi ke model product.template.
- **base_setup**: Diperlukan untuk inject pengaturan Gemini ke dalam General Settings.
- **bus**: Digunakan untuk mengirimkan real-time update dari backend ke OWL frontend.
- **web**: Standard dependency untuk asset frontend OWL.
- **mail**: Untuk kebutuhan messaging / tracking error secara internal.

## Penggunaan (Usage)
1. Dapatkan **Gemini API Key** secara gratis di https://aistudio.google.com/apikey.
2. Masuk ke Odoo dengan hak akses Administrator.
3. Buka **Settings > General Settings > Integrations**.
4. Masukkan Gemini API Key dan atur **Daily Quota Limit** (misal 100).
5. Masuk ke modul Inventory/Sales dan buka menu Products.
6. Buka salah satu produk yang memiliki gambar, lalu klik tombol **Auto White BG**.
7. Atau centang beberapa produk dari list view, lalu klik menu **Action > Auto White BG (Bulk)** untuk memproses massal.

## Halaman dan View Terkait
- **Product Form View:** Penambahan button Auto White BG. (iews/product_template_views.xml)
- **Product Action (List View):** Wizard untuk eksekusi bulk action dari menu action. (iews/andykanoz_batch_edit_wizard_views.xml)
- **Settings View:** Kolom isian API Key dan Quota Limit di General Settings. (iews/res_config_settings_views.xml)
- **Job Monitoring View:** Menu khusus di Settings > Technical untuk melihat history Batch Edit Job. (iews/andykanoz_batch_edit_job_views.xml)

## Konsep Teknis (Backend & Frontend OWL)
- **Background Cron:** Job cron dijalankan dengan XML ID ir_cron_process_batch_jobs.
- **Controllers:** /andykanoz_gemini_integration_auto_edit/get_active_job & /cancel_job untuk membaca dan membatalkan status.
- **Service OWL:** Menerima broadcast dari bus Odoo channel ndykanoz_gemini_integration_auto_edit.job_update (static/src/js/batch_edit_service.js).
