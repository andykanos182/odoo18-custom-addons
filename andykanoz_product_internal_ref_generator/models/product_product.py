# -*- coding: utf-8 -*-

from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('default_code'):
                # Generate a temporary internal reference for sequence generation
                vals['default_code'] = self.env['ir.sequence'].next_by_code('product.internal.ref') or 'New'
        
        products = super(ProductProduct, self).create(vals_list)

        for product in products:
            if product.default_code and 'New' in product.default_code: # Check if it's the temporary sequence or if the sequence failed
                # Update with the actual sequence after product ID is known
                product.default_code = self.env['ir.sequence'].next_by_code('product.internal.ref')
        return products

    def action_generate_internal_reference(self):
        for product in self:
            if not product.default_code:
                product.default_code = self.env['ir.sequence'].next_by_code('product.internal.ref')
        return True
