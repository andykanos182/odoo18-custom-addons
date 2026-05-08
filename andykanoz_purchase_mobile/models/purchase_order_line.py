# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    x_expected_expiry_date = fields.Date(
        string="Expected Expiry Date",
        help=(
            "Expected expiry date for this batch. "
            "In a later phase, this value will be propagated to the "
            "stock.lot.expiration_date when the receipt is validated. "
            "Input is optional; leave blank for non-perishable products."
        ),
    )
