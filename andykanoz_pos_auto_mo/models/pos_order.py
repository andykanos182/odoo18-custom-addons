import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    mo_ids = fields.One2many(
        'mrp.production',
        'pos_order_id',
        string='Manufacturing Orders',
    )
    mo_count = fields.Integer(
        string='MO Count',
        compute='_compute_mo_count',
    )

    def _compute_mo_count(self):
        for order in self:
            order.mo_count = len(order.mo_ids)

    # ------------------------------------------------------------------
    # Override payment flow
    # ------------------------------------------------------------------
    def _order_fields(self, ui_order):
        # Keep default behaviour; hook is here in case we need it later.
        return super()._order_fields(ui_order)

    def action_pos_order_paid(self):
        """Standard hook called when a POS order transitions to 'paid'."""
        res = super().action_pos_order_paid()
        for order in self:
            try:
                order._andykanoz_create_mos()
            except Exception as e:
                # Don't block the payment if MO creation fails — just log.
                # Cashier shouldn't be stuck because of a BoM issue.
                _logger.exception(
                    "andykanoz_pos_auto_mo: failed to create MO for POS order %s: %s",
                    order.name, e,
                )
        return res

    # ------------------------------------------------------------------
    # MO creation logic
    # ------------------------------------------------------------------
    def _andykanoz_create_mos(self):
        """Create a Manufacturing Order for each POS line whose product has an active BoM.

        Products without a BoM are skipped (sold as-is from stock).
        Sub-MOs for semi-finished components are created only if stock is insufficient.
        """
        self.ensure_one()
        MrpProduction = self.env['mrp.production']
        Bom = self.env['mrp.bom']

        for line in self.lines:
            product = line.product_id
            qty = line.qty
            if qty <= 0:
                continue

            # _bom_find returns a dict {product: bom}; empty if none.
            bom = Bom._bom_find(
                product,
                company_id=self.company_id.id,
                bom_type='normal',
            ).get(product)
            if not bom:
                # No BoM → standard Odoo stock sale, nothing to manufacture.
                continue

            mo = self._andykanoz_create_single_mo(product, qty, bom)
            _logger.info(
                "andykanoz_pos_auto_mo: created MO %s for POS order %s (product %s, qty %s)",
                mo.name, self.name, product.display_name, qty,
            )

            # Walk the BoM tree for sub-MOs (pre-cooked components get skipped
            # automatically by the stock check).
            self._andykanoz_create_sub_mos(bom, qty)

    def _andykanoz_create_single_mo(self, product, qty, bom):
        """Create and confirm one MO for the given product/qty/bom."""
        MrpProduction = self.env['mrp.production']
        vals = {
            'product_id': product.id,
            'product_qty': qty,
            'product_uom_id': product.uom_id.id,
            'bom_id': bom.id,
            'date_start': fields.Datetime.now(),
            'pos_order_id': self.id,
            'origin': self.name,
            'company_id': self.company_id.id,
        }
        mo = MrpProduction.create(vals)
        # _onchange_* equivalents: make sure moves/workorders are populated.
        mo._onchange_move_raw()
        mo._onchange_workorder_ids()
        # Auto-confirm so it lands in the kitchen queue straight away.
        mo.action_confirm()
        return mo

    def _andykanoz_create_sub_mos(self, parent_bom, parent_qty):
        """Recursively create sub-MOs for semi-finished components when stock is insufficient.

        Logic per component:
          1. Skip if component has no active BoM (it's a raw material).
          2. Compute required qty = component qty in BoM * parent_qty / bom qty.
          3. Check on-hand (free_qty) of the component.
          4. If free_qty >= required → skip (pre-cooked / pre-prepared, will be
             consumed from stock by the parent MO).
          5. Otherwise create a sub-MO for the shortfall and recurse.
        """
        Bom = self.env['mrp.bom']

        for bom_line in parent_bom.bom_line_ids:
            component = bom_line.product_id
            # Respect BoM line filters (variants etc.)
            if bom_line._skip_bom_line(component):
                continue

            sub_bom = Bom._bom_find(
                component,
                company_id=self.company_id.id,
                bom_type='normal',
            ).get(component)
            if not sub_bom:
                continue  # raw material, purchased or stocked as-is

            required_qty = bom_line.product_qty * (parent_qty / parent_bom.product_qty)

            # free_qty = on-hand minus reserved. Good proxy for "can I consume this now?".
            free_qty = component.with_context(
                warehouse_id=self._andykanoz_get_warehouse().id
            ).free_qty
            if free_qty >= required_qty:
                # Pre-cooked / pre-prepared in sufficient quantity — no sub-MO needed.
                _logger.info(
                    "andykanoz_pos_auto_mo: skipping sub-MO for %s (free_qty=%s >= required=%s)",
                    component.display_name, free_qty, required_qty,
                )
                continue

            shortfall = required_qty - free_qty
            sub_mo = self._andykanoz_create_single_mo(component, shortfall, sub_bom)
            _logger.info(
                "andykanoz_pos_auto_mo: created sub-MO %s for %s (shortfall %s)",
                sub_mo.name, component.display_name, shortfall,
            )

            # Recurse deeper for nested multi-level BoMs.
            self._andykanoz_create_sub_mos(sub_bom, shortfall)

    def _andykanoz_get_warehouse(self):
        """Resolve the warehouse for stock checks — prefer the POS config warehouse,
        fall back to the company default."""
        self.ensure_one()
        picking_type = self.config_id.picking_type_id
        if picking_type and picking_type.warehouse_id:
            return picking_type.warehouse_id
        wh = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id)], limit=1
        )
        if not wh:
            raise UserError(_("No warehouse configured for company %s") % self.company_id.name)
        return wh

    # ------------------------------------------------------------------
    # Smart button
    # ------------------------------------------------------------------
    def action_view_mos(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('mrp.mrp_production_action')
        action['domain'] = [('pos_order_id', '=', self.id)]
        action['context'] = {'default_pos_order_id': self.id}
        return action
