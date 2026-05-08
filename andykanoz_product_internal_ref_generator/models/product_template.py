# -*- coding: utf-8 -*-

from odoo import models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_generate_internal_reference(self):
        for template in self:
            if not template.default_code:
                # Generate a temporary internal reference for sequence generation
                template.default_code = self.env['ir.sequence'].next_by_code('product.internal.ref')
        return True
