# -*- coding: utf-8 -*-
import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('distance', 'Based on Distance (GPS)')],
        ondelete={'distance': 'set default'},
    )

    # === Konfigurasi Distance Shipping (default values on carrier record) ===
    distance_base_fee = fields.Float(
        string='Base Fee (Flat)',
        default=8000,
        help='Biaya dasar pengiriman untuk jarak di bawah threshold. Default: Rp 8.000',
    )
    distance_threshold_km = fields.Float(
        string='Distance Threshold (km)',
        default=3.0,
        help='Jarak threshold dalam km. Di bawah ini dikenakan biaya flat (base fee). Default: 3 km',
    )
    distance_per_km_fee = fields.Float(
        string='Fee per KM (above threshold)',
        default=2500,
        help='Biaya per km untuk jarak di atas threshold. Default: Rp 2.500/km',
    )
    distance_max_km = fields.Float(
        string='Max Distance (km)',
        default=5.0,
        help='Jarak maksimum yang dilayani. Lebih dari ini tidak tersedia. Default: 5 km',
    )
    distance_travel_mode = fields.Selection(
        [('driving', 'Mobil'), ('TWO_WHEELER', 'Motor')],
        string='Travel Mode',
        default='TWO_WHEELER',
        help='Mode transportasi untuk perhitungan jarak. Motor = rute motor, Mobil = rute mobil.',
    )

    def _get_distance_config(self):
        """
        Ambil parameter konfigurasi distance shipping.
        Prioritas: Settings (ir.config_parameter) → Carrier record (sebagai fallback/default).

        Logika:
        - Jika nilai di Settings > 0 → pakai nilai Settings.
        - Jika nilai di Settings = 0 atau belum diset → pakai nilai dari carrier record.
        - Ini memungkinkan admin mengubah parameter di Settings → General → Integrations,
          dan perubahan langsung berlaku di checkout tanpa perlu edit carrier record.
        """
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()

        # Baca dari ir.config_parameter (Settings)
        settings_base_fee = float(ICP.get_param('andykanoz_distance_shipping.base_fee', '0'))
        settings_threshold = float(ICP.get_param('andykanoz_distance_shipping.threshold_km', '0'))
        settings_per_km = float(ICP.get_param('andykanoz_distance_shipping.per_km_fee', '0'))
        settings_max_km = float(ICP.get_param('andykanoz_distance_shipping.max_km', '0'))
        settings_travel_mode = ICP.get_param('andykanoz_distance_shipping.travel_mode', '')

        # Fallback ke carrier record jika Settings = 0 atau kosong
        base_fee = settings_base_fee if settings_base_fee > 0 else self.distance_base_fee
        threshold_km = settings_threshold if settings_threshold > 0 else self.distance_threshold_km
        per_km_fee = settings_per_km if settings_per_km > 0 else self.distance_per_km_fee
        max_km = settings_max_km if settings_max_km > 0 else self.distance_max_km
        travel_mode = settings_travel_mode if settings_travel_mode else (
            self.distance_travel_mode or 'TWO_WHEELER'
        )

        _logger.info(
            "[Distance Shipping] Config → base_fee=%.0f, threshold=%.1f km, "
            "per_km=%.0f, max=%.1f km, mode=%s (source: %s)",
            base_fee, threshold_km, per_km_fee, max_km, travel_mode,
            'Settings' if settings_base_fee > 0 else 'Carrier record'
        )

        return {
            'base_fee': base_fee,
            'threshold_km': threshold_km,
            'per_km_fee': per_km_fee,
            'max_km': max_km,
            'travel_mode': travel_mode,
        }

    def distance_rate_shipment(self, order):
        """
        Hitung biaya pengiriman berdasarkan jarak GPS antara warehouse dan customer.
        Menggunakan Google Distance Matrix API.
        Simpan jarak ke sale.order.delivery_distance_km.
        """
        self.ensure_one()

        # Validasi carrier match address
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _('This delivery method is not available for this address.'),
                'warning_message': False,
            }

        # Ambil koordinat toko (warehouse/company)
        company = order.company_id or self.env.company
        store_lat = company.partner_id.partner_latitude
        store_lng = company.partner_id.partner_longitude

        if not store_lat or not store_lng:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _('Store coordinates not set. Please contact admin.'),
                'warning_message': False,
            }

        # Ambil koordinat customer
        customer = order.partner_shipping_id
        cust_lat = customer.partner_latitude
        cust_lng = customer.partner_longitude

        if not cust_lat or not cust_lng:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _('Please select your location on the map first.'),
                'warning_message': False,
            }

        # Ambil konfigurasi dari Settings (prioritas) atau Carrier record (fallback)
        config = self._get_distance_config()
        travel_mode = config['travel_mode']

        # Hitung jarak via Google API
        distance_km = self._get_distance_google(
            store_lat, store_lng, cust_lat, cust_lng, travel_mode
        )

        if distance_km is None:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _('Failed to calculate distance. Check connection or API Key.'),
                'warning_message': False,
            }

        mode_label = 'motorcycle' if travel_mode == 'TWO_WHEELER' else 'car'
        _logger.info(
            "[Distance Shipping] Store: (%s, %s) → Customer: (%s, %s) = %.2f km (mode: %s)",
            store_lat, store_lng, cust_lat, cust_lng, distance_km, mode_label
        )

        # Simpan jarak ke sale.order
        try:
            order.sudo().write({'delivery_distance_km': round(distance_km, 2)})
        except Exception as e:
            _logger.warning("[Distance Shipping] Could not save distance to order: %s", str(e))

        # Cek jarak maksimum (dari config)
        if distance_km > config['max_km']:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _(
                    'Sorry, your location (%.1f km) exceeds the maximum delivery distance (%.1f km).'
                ) % (distance_km, config['max_km']),
                'warning_message': False,
            }

        # Hitung biaya (dari config)
        if distance_km <= config['threshold_km']:
            price = config['base_fee']
        else:
            extra_km = distance_km - config['threshold_km']
            price = config['base_fee'] + (extra_km * config['per_km_fee'])

        # Bulatkan ke ratusan terdekat
        price = round(price / 100) * 100

        _logger.info(
            "[Distance Shipping] Distance: %.2f km → Price: Rp %.0f (mode: %s)",
            distance_km, price, mode_label
        )

        return {
            'success': True,
            'price': price,
            'error_message': False,
            'warning_message': _('Delivery distance: %.1f km') % distance_km,
        }

    def _get_distance_google(self, origin_lat, origin_lng, dest_lat, dest_lng, travel_mode='TWO_WHEELER'):
        """
        Hitung jarak menggunakan Google API.
        Return jarak dalam km, atau None jika gagal.
        """
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'base_geolocalize.google_map_api_key', ''
        )

        if not api_key:
            _logger.error("[Distance Shipping] Google Maps API Key not found.")
            return None

        try:
            if travel_mode == 'TWO_WHEELER':
                return self._get_distance_google_routes_api(
                    origin_lat, origin_lng, dest_lat, dest_lng, api_key, travel_mode
                )
            else:
                return self._get_distance_google_matrix_api(
                    origin_lat, origin_lng, dest_lat, dest_lng, api_key, travel_mode
                )
        except Exception as e:
            _logger.error("[Distance Shipping] Exception: %s", str(e))
            return None

    def _get_distance_google_matrix_api(self, origin_lat, origin_lng, dest_lat, dest_lng, api_key, mode='driving'):
        """Distance Matrix API — for driving mode."""
        url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
        params = {
            'origins': '%s,%s' % (origin_lat, origin_lng),
            'destinations': '%s,%s' % (dest_lat, dest_lng),
            'mode': mode,
            'language': 'id',
            'key': api_key,
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('status') != 'OK':
            _logger.error("[Distance Shipping] Matrix API error: %s", data.get('status'))
            return None

        rows = data.get('rows', [])
        if not rows or not rows[0].get('elements'):
            return None

        element = rows[0]['elements'][0]
        if element.get('status') != 'OK':
            _logger.error("[Distance Shipping] Element status: %s", element.get('status'))
            return None

        distance_meters = element['distance']['value']
        return distance_meters / 1000.0

    def _get_distance_google_routes_api(self, origin_lat, origin_lng, dest_lat, dest_lng, api_key, travel_mode='TWO_WHEELER'):
        """Google Routes API (computeRoutes) — supports TWO_WHEELER for motorcycle."""
        url = 'https://routes.googleapis.com/directions/v2:computeRoutes'
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': 'routes.distanceMeters',
        }
        body = {
            'origin': {
                'location': {
                    'latLng': {'latitude': origin_lat, 'longitude': origin_lng}
                }
            },
            'destination': {
                'location': {
                    'latLng': {'latitude': dest_lat, 'longitude': dest_lng}
                }
            },
            'travelMode': travel_mode,
        }

        response = requests.post(url, json=body, headers=headers, timeout=10)
        data = response.json()

        routes = data.get('routes', [])
        if not routes:
            _logger.error("[Distance Shipping] Routes API: no routes found. Response: %s", data)
            _logger.info("[Distance Shipping] Fallback to Distance Matrix API (driving)")
            return self._get_distance_google_matrix_api(
                origin_lat, origin_lng, dest_lat, dest_lng, api_key, 'driving'
            )

        distance_meters = routes[0].get('distanceMeters', 0)
        return distance_meters / 1000.0

    def distance_send_shipping(self, pickings):
        """Required by Odoo delivery provider interface."""
        res = []
        for picking in pickings:
            res.append({
                'exact_price': 0,
                'tracking_number': False,
            })
        return res

    def distance_get_tracking_link(self, picking):
        """Required by Odoo delivery provider interface."""
        return False

    def distance_cancel_shipment(self, pickings):
        """Required by Odoo delivery provider interface."""
        raise UserError(_('Cancellation is not required for Distance Shipping.'))
