# -*- coding: utf-8 -*-
from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _action_done(self):
        """Propagate x_expected_expiry_date from purchase.order.line to
        stock.lot when a receipt (or any move from a PO) is validated.

        Flow:
            user creates PO via Purchase Mobile with expiry date on line
            → user confirms PO (state=purchase) → receipt created
            → user validates receipt in desktop Odoo → stock.move.line
              gets done → a stock.lot is created
            → this override copies the PO line's expiry date into the
              newly created lot's expiration_date field.

        Compatibility:
          - product_expiry module INSTALLED: stock.lot.expiration_date
            exists and is typically auto-computed from
            product.expiration_time. We override that compute result
            with the more-specific PO-line value (batch-specific date
            wins over product default).
          - product_expiry module NOT INSTALLED: expiration_date field
            doesn't exist on stock.lot. We detect this via hasattr check
            and skip propagation silently. The x_expected_expiry_date
            is still persisted on the PO line for reporting, but has no
            downstream effect (graceful degradation per HANDOFF_V1 §5).

        Edge cases handled:
          - Move line not from a PO → skipped (no purchase_line_id).
          - PO line has no x_expected_expiry_date → skipped.
          - No lot on the move line (tracking='none') → skipped.
          - Move lines merged or deleted during super()._action_done()
            → mapping is captured BEFORE super() by move-line id, then
            survivors are re-browsed after.
        """
        # Capture (ml.id -> expected_expiry_date) BEFORE super(),
        # because stock.move.line records can be merged or unlinked
        # during _action_done (Odoo consolidates identical lines).
        ml_to_expected = {}
        for ml in self:
            po_line = ml.move_id.purchase_line_id
            if po_line and po_line.x_expected_expiry_date:
                ml_to_expected[ml.id] = po_line.x_expected_expiry_date

        res = super()._action_done()

        # Graceful degrade: skip silently if product_expiry isn't
        # installed. Detected by absence of expiration_date field on
        # stock.lot (the field is added by product_expiry).
        Lot = self.env['stock.lot']
        if 'expiration_date' not in Lot._fields:
            return res

        for ml_id, expected_date in ml_to_expected.items():
            ml = self.browse(ml_id).exists()
            if not ml or not ml.lot_id:
                continue
            lot = ml.lot_id
            # The PO-line date is more specific than
            # product.expiration_time default, so it wins. If the user
            # wanted a different date per-batch at receipt time, they
            # shouldn't have filled it in at PO time.
            if lot.expiration_date != expected_date:
                lot.write({'expiration_date': expected_date})

        return res
