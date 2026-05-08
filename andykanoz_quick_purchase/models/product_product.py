# -*- coding: utf-8 -*-
from odoo import models, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_last_purchase_price(self, partner_id=None):
        """Return the most relevant purchase price for this product.

        Strategy (in order):
          1. Most recent purchase.order.line for this product from the
             given vendor (state in purchase/done).
          2. Any seller_ids entry matching the vendor (price field).
          3. The product's standard_price (cost) as last resort.

        :param partner_id: res.partner id of the vendor (int) or None.
        :return: float price (in product UoM, in company currency).
        """
        self.ensure_one()
        price = 0.0

        # 1. Last PO line from this vendor
        if partner_id:
            domain = [
                ("product_id", "=", self.id),
                ("order_id.partner_id", "=", partner_id),
                ("state", "in", ("purchase", "done")),
            ]
            last_line = self.env["purchase.order.line"].search(
                domain, order="date_order desc, id desc", limit=1
            )
            if last_line:
                return last_line.price_unit

        # 2. Vendor pricelist (seller_ids)
        if partner_id:
            seller = self.seller_ids.filtered(
                lambda s: s.partner_id.id == partner_id
            )[:1]
            if seller and seller.price:
                return seller.price

        # Any seller (no vendor restriction)
        if self.seller_ids:
            first = self.seller_ids[:1]
            if first.price:
                return first.price

        # 3. standard_price
        return self.standard_price or 0.0
