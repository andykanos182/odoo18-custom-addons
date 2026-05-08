# -*- coding: utf-8 -*-
{
    'name': 'AndykaNoz (Custom Google Maps & Peta)',
    'version': '18.0.3.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Google Maps interaktif di portal, checkout, backend Contacts, dan Delivery Orders.',
    'description': """
Modul ini menambahkan:
- Peta Google Maps interaktif di halaman /shop/address dan /my/account (portal/frontend)
- Peta Google Maps interaktif di backend Contacts → Partner Assignment (OWL widget)
  * Drag marker untuk update Lat/Long otomatis
  * Klik peta untuk pindah marker
  * Tombol "Lokasi Saya" (GPS browser)
- Reverse geocoding: klik peta → otomatis isi field alamat (portal/checkout)
- Koordinat tersimpan ke res.partner (partner_latitude, partner_longitude)
- Link Navigation otomatis di Delivery Orders dari koordinat
- Sembunyikan Company Name dan VAT Number di portal (B2C mode)
- Label "Phone / WhatsApp" di portal
    """,
    'author': 'AndykaNoz',
    'website': 'https://www.gopokaja.com',
    'depends': [
        'base',
        'contacts',
        'website_sale',
        'stock',
        'base_geolocalize',
    ],
    'data': [
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/website_sale_templates.xml',
        'views/stock_picking_view.xml',
        'views/portal_hide_b2b_fields.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'andykanoz_google_maps_peta/static/src/js/gmap_widget.js',
            'andykanoz_google_maps_peta/static/src/xml/gmap_widget.xml',
            'andykanoz_google_maps_peta/static/src/css/stock_picking.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
