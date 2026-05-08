# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    distance_shipping_base_fee = fields.Float(
        string='Base Fee (Flat)',
        config_parameter='andykanoz_distance_shipping.base_fee',
        default=8000,
        help='Biaya dasar pengiriman untuk jarak di bawah threshold. Default: Rp 8.000',
    )
    distance_shipping_threshold_km = fields.Float(
        string='Distance Threshold (km)',
        config_parameter='andykanoz_distance_shipping.threshold_km',
        default=3.0,
        help='Jarak threshold. Di bawah ini dikenakan biaya flat. Default: 3 km',
    )
    distance_shipping_per_km_fee = fields.Float(
        string='Fee per KM (above threshold)',
        config_parameter='andykanoz_distance_shipping.per_km_fee',
        default=2500,
        help='Biaya per km di atas threshold. Default: Rp 2.500/km',
    )
    distance_shipping_max_km = fields.Float(
        string='Max Delivery Distance (km)',
        config_parameter='andykanoz_distance_shipping.max_km',
        default=5.0,
        help='Jarak maksimum pengiriman. Default: 5 km',
    )
    distance_shipping_travel_mode = fields.Selection(
        [('driving', 'Mobil'), ('TWO_WHEELER', 'Motor')],
        string='Default Travel Mode',
        config_parameter='andykanoz_distance_shipping.travel_mode',
        default='TWO_WHEELER',
        help='Mode transportasi untuk perhitungan jarak via Google Distance Matrix API.',
    )
