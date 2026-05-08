# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    gmaps_link = fields.Char(
        string='Link Google Maps',
        related='partner_id.gmaps_link',
        readonly=True
    )

    gmaps_navigation_url = fields.Char(
        string='Link Navigation',
        compute='_compute_gmaps_navigation_url',
    )

    @api.depends('partner_id.partner_latitude', 'partner_id.partner_longitude', 'partner_id.gmaps_link')
    def _compute_gmaps_navigation_url(self):
        for picking in self:
            lat = picking.partner_id.partner_latitude
            lng = picking.partner_id.partner_longitude
            if lat and lng and (lat != 0 or lng != 0):
                picking.gmaps_navigation_url = (
                    'https://www.google.com/maps/dir/?api=1&destination=%s,%s' % (lat, lng)
                )
            elif picking.partner_id.gmaps_link:
                picking.gmaps_navigation_url = picking.partner_id.gmaps_link
            else:
                picking.gmaps_navigation_url = False

    def action_open_gmaps(self):
        self.ensure_one()

        if self.gmaps_navigation_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.gmaps_navigation_url,
                'target': 'new',
            }
        else:
            raise UserError("Customer belum memilih lokasi di peta.")
