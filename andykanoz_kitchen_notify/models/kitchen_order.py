import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class KitchenOrder(models.Model):
    """Flat kitchen-display record linked to a POS order line and its MO.

    Hybrid source of truth:
      - UI reads/writes kitchen.order (simple, fast).
      - Status changes sync both ways with mrp.production so cook_tracking
        (future module) and the Manufacturing app stay consistent.
    """
    _name = 'kitchen.order'
    _description = 'Kitchen Order (Display)'
    _order = 'order_time asc, id asc'
    _rec_name = 'product_name'

    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    pos_order_ref = fields.Char(
        related='pos_order_id.pos_reference',
        string='POS Reference',
        store=True,
    )
    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        ondelete='set null',
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    product_name = fields.Char(
        string='Product Name',
        required=True,
        help='Snapshot of product name at order time (in case product is renamed later)',
    )
    qty = fields.Float(string='Quantity', required=True, default=1.0)
    status = fields.Selection(
        [
            ('waiting', 'Menunggu'),
            ('cooking', 'Sedang Dimasak'),
            ('done', 'Selesai'),
        ],
        string='Status',
        default='waiting',
        required=True,
        index=True,
    )
    order_time = fields.Datetime(
        string='Order Time',
        default=fields.Datetime.now,
        required=True,
    )
    cook_start_time = fields.Datetime(string='Cook Start Time')
    done_time = fields.Datetime(string='Done Time')
    note = fields.Char(string='Note')

    # ------------------------------------------------------------------
    # Status transitions — sync with mrp.production
    # ------------------------------------------------------------------
    def action_start_cooking(self):
        for rec in self:
            rec.write({
                'status': 'cooking',
                'cook_start_time': fields.Datetime.now(),
            })
            rec._sync_mo_start()
        return True

    def action_mark_done(self):
        for rec in self:
            rec.write({
                'status': 'done',
                'done_time': fields.Datetime.now(),
            })
            rec._sync_mo_done()
        return True

    def action_reset_to_waiting(self):
        for rec in self:
            rec.write({
                'status': 'waiting',
                'cook_start_time': False,
                'done_time': False,
            })
        return True

    def _sync_mo_start(self):
        """When user starts cooking, move the linked MO to 'progress' if possible."""
        self.ensure_one()
        mo = self.production_id
        if not mo:
            return
        try:
            if mo.state == 'confirmed':
                # mrp.production doesn't have a clean 'action_start', but writing
                # state='progress' works and is what Odoo does internally when
                # the first work order begins.
                mo.write({'state': 'progress'})
        except Exception as e:
            _logger.warning(
                "kitchen_notify: failed to sync MO %s to progress: %s", mo.name, e,
            )

    def _sync_mo_done(self):
        """When user marks done, complete the MO (produce all + validate)."""
        self.ensure_one()
        mo = self.production_id
        if not mo:
            return
        try:
            if mo.state not in ('done', 'cancel'):
                # Set produced qty then validate.
                mo.qty_producing = mo.product_qty
                mo._onchange_producing()
                mo.button_mark_done()
        except Exception as e:
            # Don't block the kitchen UI if MO validation fails (e.g. missing
            # component stock). The kitchen.order is still marked done — user
            # can fix the MO separately in the Manufacturing app.
            _logger.warning(
                "kitchen_notify: failed to mark MO %s done: %s. "
                "Kitchen order is still marked done; resolve MO manually.",
                mo.name, e,
            )

    # ------------------------------------------------------------------
    # Helpers for the JSON API
    # ------------------------------------------------------------------
    def _to_kitchen_json(self):
        """Serialize for the Kitchen Display frontend."""
        self.ensure_one()
        return {
            'id': self.id,
            'pos_order_id': self.pos_order_id.id,
            'pos_ref': self.pos_order_ref or self.pos_order_id.name or '',
            'product_name': self.product_name,
            'qty': self.qty,
            'status': self.status,
            'order_time': fields.Datetime.to_string(self.order_time) if self.order_time else '',
            'note': self.note or '',
        }
