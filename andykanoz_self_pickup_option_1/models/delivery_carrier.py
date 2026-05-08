# -*- coding: utf-8 -*-
from odoo import models, fields


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    is_self_pickup = fields.Boolean(
        string='Self Pickup',
        default=False,
        help='Jika dicentang, carrier ini akan diperlakukan sebagai opsi '
             'ambil sendiri (Self Pickup) dan dipisahkan dari delivery methods biasa.',
    )
