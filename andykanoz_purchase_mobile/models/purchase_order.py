# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    x_created_via_mobile = fields.Boolean(
        string="Created via Mobile",
        default=False,
        copy=False,
        index=True,
        help=(
            "Indicates this PO was created through the Purchase Mobile app, "
            "using the MP00xxx sequence instead of the standard PO sequence. "
            "Used for reporting and to route edit clicks back into the mobile "
            "app in later phases."
        ),
    )
