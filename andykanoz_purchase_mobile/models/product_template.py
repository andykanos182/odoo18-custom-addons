# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_requires_expiry = fields.Boolean(
        string="Requires Expiry on Purchase Mobile",
        default=False,
        help=(
            "Tick this if the Purchase Mobile app should ask for an expiry "
            "date when this product is added to a PO, even if it isn't "
            "tracked by lot/serial. "
            "If the product_expiry module is installed and use_expiration_date "
            "is active on this product, expiry input is enabled automatically "
            "regardless of this flag."
        ),
    )
