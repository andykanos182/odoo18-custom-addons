from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'
    gmaps_link = fields.Char(string='Link Google Maps')
    
