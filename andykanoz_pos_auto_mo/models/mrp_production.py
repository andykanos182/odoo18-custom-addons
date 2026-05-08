from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order',
        help='POS order that triggered this Manufacturing Order',
        index=True,
        copy=False,
    )
    pos_order_ref = fields.Char(
        related='pos_order_id.pos_reference',
        string='POS Reference',
        store=True,
    )
