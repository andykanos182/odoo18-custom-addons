from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    dynamic_pricelist_price = fields.Float(
        string='Pricelist Price',
        compute='_compute_dynamic_price',
    )
    dynamic_profit = fields.Float(
        string='Profit',
        compute='_compute_dynamic_price',
    )

    @api.depends_context('pricelist')
    @api.depends('list_price')
    def _compute_dynamic_price(self):
        pricelist_id = self.env.context.get('pricelist')
        pricelist = False
        if pricelist_id:
            pricelist = self.env['product.pricelist'].browse(int(pricelist_id))
            if not pricelist.exists():
                pricelist = False
        for rec in self:
            if pricelist:
                price = pricelist._get_product_price(rec, 1.0)
            else:
                price = rec.list_price
            rec.dynamic_pricelist_price = price
            # standard_price in Odoo 18 is JSONB — read via mapped or direct
            cost = rec.standard_price or 0.0
            rec.dynamic_profit = price - cost


class ProductProduct(models.Model):
    _inherit = 'product.product'

    dynamic_pricelist_price = fields.Float(
        string='Pricelist Price',
        compute='_compute_dynamic_price',
    )
    dynamic_profit = fields.Float(
        string='Profit',
        compute='_compute_dynamic_price',
    )

    @api.depends_context('pricelist')
    @api.depends('lst_price')
    def _compute_dynamic_price(self):
        pricelist_id = self.env.context.get('pricelist')
        pricelist = False
        if pricelist_id:
            pricelist = self.env['product.pricelist'].browse(int(pricelist_id))
            if not pricelist.exists():
                pricelist = False
        for rec in self:
            tmpl = rec.product_tmpl_id
            if pricelist:
                # Try variant-level pricing first, fallback to template if needed
                try:
                    price = pricelist._get_product_price(rec, 1.0)
                except Exception:
                    try:
                        price = pricelist._get_product_price(tmpl, 1.0)
                    except Exception:
                        price = rec.lst_price
            else:
                price = rec.lst_price
            rec.dynamic_pricelist_price = price
            cost = rec.standard_price or 0.0
            rec.dynamic_profit = price - cost
