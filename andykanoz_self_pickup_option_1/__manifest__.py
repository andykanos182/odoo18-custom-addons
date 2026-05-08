# -*- coding: utf-8 -*-
{
    'name': 'AndykaNoz Self Pickup (Option 1 - Email Override)',
    'version': '18.0.3.2.0',
    'category': 'MyCustom/Modules',
    'summary': 'Self Pickup dengan override email template — metode ringan tanpa operation type baru.',
    'description': """
Self Pickup Option 1: Override Email Template (Ringan)

Fitur:
- Toggle "Diantar ke Alamat Saya" / "Ambil Sendiri di Toko" di checkout
- Info jarak + biaya di dalam option "Diantar ke Alamat Saya"
- Info alamat toko di dalam option "Ambil Sendiri di Toko"
- Carrier Self Pickup tersimpan ke Sales Order via RPC
- Choose Delivery Method dan Billing Address disembunyikan (B2C)
- Button "View My Orders" di halaman confirmation dan payment status
- Portal Sales Order: Kode Pengambilan, Status, Instruksi, Alamat Toko, WhatsApp
- Portal Sales Order: Last Delivery Orders disembunyikan untuk Self Pickup
- Override email: saat Validate delivery order Self Pickup → kirim email "Pesanan Siap Diambil"
    """,
    'author': 'AndykaNoz',
    'website': 'https://www.gopokaja.com',
    'depends': [
        'website_sale',
        'delivery',
        'sale_stock',
        'payment',
        'base_geolocalize',
        'andykanoz_google_maps_peta',
    ],
    'data': [
        'data/delivery_carrier_data.xml',
        'data/mail_template_data.xml',
        'views/delivery_carrier_view.xml',
        'views/checkout_self_pickup_template.xml',
        'views/payment_status_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
