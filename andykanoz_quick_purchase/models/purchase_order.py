# -*- coding: utf-8 -*-
from odoo import models, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_open_quick_purchase(self):
        self.ensure_one()
        lines_data = []
        for line in self.order_line:
            uom_options = []
            uom_category_id = False
            if line.product_id.uom_id.category_id:
                uom_category_id = line.product_id.uom_id.category_id.id
                uoms = self.env['uom.uom'].search([('category_id', '=', uom_category_id)])
                for u in uoms:
                    uom_options.append({'id': u.id, 'name': u.name})

            lines_data.append({
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.display_name,
                'default_code': line.product_id.default_code or "",
                'barcode': line.product_id.barcode or "",
                'qty': line.product_qty,
                'uom_id': line.product_uom.id,
                'uom_category_id': uom_category_id,
                'uom_options': uom_options,
                'price_unit': line.price_unit,
                'discount_amount': 0.0, # Natively not supported on purchase.order.line without discount module
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'andykanoz_quick_purchase.QuickPurchase',
            'params': {
                'init_po_name': self.name,
                'init_partner_id': self.partner_id.id,
                'init_partner_name': self.partner_id.display_name,
                'init_lines': lines_data,
            }
        }
