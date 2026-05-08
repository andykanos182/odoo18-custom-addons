# -*- coding: utf-8 -*-
{
    'name': 'AndykaNoz Distance Shipping',
    'version': '18.0.2.1.0',
    'category': 'MyCustom/Modules',
    'summary': 'Distance-based delivery pricing via Google Distance Matrix API.',
    'description': """
Distance-based delivery pricing using GPS coordinates.

Features:
- New delivery type: "Based on Distance (GPS)"
- Calculate distance via Google Distance Matrix API (driving) or Routes API (motorcycle)
- Pricing formula: base_fee + ((distance - threshold) x per_km_fee)
- Maximum delivery distance (beyond this, delivery not available)
- Delivery distance (km) saved to Sales Order for reporting
- Configuration in Settings → Integrations → Distance Shipping
- Per-carrier configuration in Shipping Methods form
- Travel mode: Motorcycle (TWO_WHEELER) or Car (driving)

Default pricing:
- 0-3 km → Rp 8,000 (flat)
- 3-5 km → Rp 8,000 + ((distance - 3) x Rp 2,500)
- >5 km → Not available

Prerequisites:
- Module andykanoz_google_maps_peta must be installed (for customer coordinates)
- Google Maps API Key set in Settings → Integrations → Geolocation
- Google Distance Matrix API enabled in Google Cloud Console
- Google Routes API enabled (for motorcycle mode)
- Store coordinates set in Company Contact (Partner Assignment)
- Customer coordinates set via map in /my/account or /shop/address
    """,
    'author': 'AndykaNoz',
    'website': 'https://www.gopokaja.com',
    'depends': [
        'delivery',
        'sale',
        'base_geolocalize',
        'website_sale',
        'andykanoz_google_maps_peta',
    ],
    'data': [
        'data/delivery_carrier_data.xml',
        'views/delivery_carrier_view.xml',
        'views/sale_order_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
