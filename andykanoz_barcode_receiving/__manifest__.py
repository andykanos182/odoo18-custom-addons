{
    'name': 'Andykanoz Barcode Receiving',
    'version': '18.0.2.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Receive incoming goods by scanning product barcodes on a full-screen page',
    'description': """
        Custom Barcode Receiving for Odoo 18 Community
        ================================================

        Modul ini menambahkan fitur penerimaan barang (Receipt) menggunakan
        barcode scanner pada halaman full-screen yang terpisah.

        FITUR UTAMA:
        - Halaman full-screen khusus untuk proses penerimaan barang
        - Support 3 metode scan: Hardware Scanner, Kamera HP, dan Input Manual
        - Daftar barang Pending (belum diterima) dan Received (sudah diterima)
        - Progress bar real-time
        - Support barcode produk dan barcode packaging (dus)
        - Kompatibel dengan Android dan iOS (iPhone/iPad)
        - Sound notification (sukses/error)

        CARA PAKAI:
        1. Buat Purchase Order → Confirm
        2. Buka Receipt yang terbuat otomatis (Inventory → Receipts)
        3. Pada form Receipt, klik tombol "Barcode Receiving"
           (tombol hanya muncul untuk Receipt berstatus Waiting/Ready)
        4. Di halaman Barcode Receiving:
           - Scan barcode menggunakan hardware scanner (USB/Bluetooth)
           - Atau klik tombol kamera untuk scan via HP
           - Atau ketik barcode manual lalu tekan Enter
        5. Setiap scan berhasil, item berpindah dari list Pending ke Received
        6. Setelah semua item diterima, klik "Validate" untuk konfirmasi

        CATATAN:
        - Pastikan produk sudah memiliki barcode di master produk
        - Scan per line: 1x scan = 1 line produk diterima penuh (qty = demand)
        - Barcode packaging (dus) juga bisa digunakan untuk scan
    """,
    'author': 'Andyka',
    'depends': ['stock', 'purchase', 'barcodes'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'andykanoz_barcode_receiving/static/src/scss/barcode_receiving.scss',
            'andykanoz_barcode_receiving/static/src/js/barcode_receiving_action.js',
            'andykanoz_barcode_receiving/static/src/xml/barcode_receiving_action.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
