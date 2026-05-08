# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_distance_km = fields.Float(
        string='Delivery Distance (km)',
        digits=(10, 2),
        readonly=True,
        copy=False,
        help='Distance between store and customer delivery address, calculated via Google Distance Matrix API.',
    )
