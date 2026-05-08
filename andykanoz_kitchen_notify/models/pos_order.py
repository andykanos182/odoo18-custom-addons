import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    kitchen_order_ids = fields.One2many(
        'kitchen.order',
        'pos_order_id',
        string='Kitchen Orders',
    )

    def action_pos_order_paid(self):
        """After the POS order is paid:
          1. Let pos_auto_mo create MOs (via super).
          2. Create one kitchen.order per line that has a BoM (matches
             the same skip rule as pos_auto_mo — no BoM = no kitchen card).
          3. Link each kitchen.order to its corresponding MO.
          4. Fire one push notification per POS order.
        """
        res = super().action_pos_order_paid()
        for order in self:
            try:
                order._andykanoz_create_kitchen_orders()
                order._andykanoz_send_kitchen_push()
            except Exception as e:
                # Never block payment on a kitchen notify failure.
                _logger.exception(
                    "kitchen_notify: failed for POS order %s: %s", order.name, e,
                )
        return res

    def _andykanoz_create_kitchen_orders(self):
        """Create kitchen.order rows for each POS line that has an active BoM.

        Links to the parent MO created by pos_auto_mo (not sub-MOs — kitchen
        staff only see the finished product they are cooking, not the
        pre-cooked components).
        """
        self.ensure_one()
        Bom = self.env['mrp.bom']
        KitchenOrder = self.env['kitchen.order']

        # Build a lookup: product_id -> parent MO created for this POS order.
        # We only want parent MOs (those whose product matches a POS line),
        # not recursive sub-MOs for semi-finished components.
        pos_line_product_ids = self.lines.mapped('product_id').ids
        mo_by_product = {}
        for mo in self.mo_ids:
            if mo.product_id.id in pos_line_product_ids and mo.product_id.id not in mo_by_product:
                mo_by_product[mo.product_id.id] = mo

        for line in self.lines:
            product = line.product_id
            if line.qty <= 0:
                continue
            # Match the same skip rule as pos_auto_mo: only products with a BoM.
            bom = Bom._bom_find(
                product,
                company_id=self.company_id.id,
                bom_type='normal',
            ).get(product)
            if not bom:
                continue

            KitchenOrder.create({
                'pos_order_id': self.id,
                'production_id': mo_by_product.get(product.id, False) and mo_by_product[product.id].id or False,
                'product_id': product.id,
                'product_name': product.display_name,
                'qty': line.qty,
                'status': 'waiting',
                'order_time': fields.Datetime.now(),
                'note': line.note if hasattr(line, 'note') else '',
            })

    def _andykanoz_send_kitchen_push(self):
        """Send one push notification summarizing the whole POS order."""
        self.ensure_one()
        kitchen_lines = self.kitchen_order_ids.filtered(lambda k: k.status == 'waiting')
        if not kitchen_lines:
            return  # nothing to cook, no push

        items = [
            f"{int(k.qty) if k.qty == int(k.qty) else k.qty}x {k.product_name}"
            for k in kitchen_lines
        ]
        body = " • ".join(items)
        if len(body) > 180:
            body = body[:177] + "..."

        payload = {
            'title': f"🔔 Order baru #{self.pos_reference or self.name}",
            'body': body,
            'url': '/kitchen',
            'pos_order_id': self.id,
            'timestamp': fields.Datetime.to_string(fields.Datetime.now()),
        }
        self.env['kitchen.vapid'].send_push_to_all(payload)
