# -*- coding: utf-8 -*-
from odoo import models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_auto_white_background(self):
        for product in self:
            if product.product_tmpl_id:
                product.product_tmpl_id.action_auto_white_background()
                product.image_1920 = product.product_tmpl_id.image_1920
        return True

    def action_auto_professional_edit(self):
        for product in self:
            if product.product_tmpl_id:
                product.product_tmpl_id.action_auto_professional_edit()
                product.image_1920 = product.product_tmpl_id.image_1920
        return True
