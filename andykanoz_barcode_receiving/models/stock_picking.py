from odoo import api, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_open_barcode_receiving(self):
        """Open the full-screen barcode receiving page."""
        self.ensure_one()
        if self.picking_type_code != 'incoming':
            raise UserError(_("Barcode receiving is only available for receipts."))
        return {
            'type': 'ir.actions.client',
            'tag': 'andykanoz_barcode_receiving',
            'name': _("Barcode Receiving"),
            'params': {
                'picking_id': self.id,
            },
        }

    def get_barcode_receiving_data(self):
        """Return pending and received move data for the barcode receiving UI."""
        self.ensure_one()
        pending = []
        received = []
        for move in self.move_ids.filtered(lambda m: m.state != 'cancel'):
            demand = move.product_uom_qty
            done = move.quantity
            remaining = demand - done
            move_data = {
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_name': move.product_id.display_name,
                'product_barcode': move.product_id.barcode or '',
                'product_image': '/web/image/product.product/%d/image_128' % move.product_id.id,
                'uom_name': move.product_uom.name,
                'demand': demand,
                'done': done,
                'remaining': remaining,
            }
            if remaining > 0:
                pending.append(move_data)
            else:
                received.append(move_data)
        return {
            'picking_id': self.id,
            'picking_name': self.name,
            'partner_name': self.partner_id.display_name or '',
            'origin': self.origin or '',
            'state': self.state,
            'pending': pending,
            'received': received,
        }

    def process_barcode_scan(self, barcode):
        """Process a scanned barcode: find matching move and set quantity = demand."""
        self.ensure_one()

        # 1. Search by product barcode
        product = self.env['product.product'].search(
            [('barcode', '=', barcode)], limit=1
        )

        # 2. If not found, search by packaging barcode
        if not product:
            packaging = self.env['product.packaging'].search(
                [('barcode', '=', barcode)], limit=1
            )
            if packaging:
                product = packaging.product_id

        if not product:
            return {
                'success': False,
                'error': _("No product found for barcode: %s", barcode),
            }

        # 3. Find matching move in this picking that still has remaining qty
        matching_move = self.move_ids.filtered(
            lambda m: m.product_id.id == product.id
            and m.state != 'cancel'
            and m.quantity < m.product_uom_qty
        )

        if not matching_move:
            # Check if product exists in picking but already fully received
            fully_done = self.move_ids.filtered(
                lambda m: m.product_id.id == product.id
                and m.state != 'cancel'
                and m.quantity >= m.product_uom_qty
            )
            if fully_done:
                return {
                    'success': False,
                    'error': _("'%s' has already been fully received.", product.display_name),
                }
            return {
                'success': False,
                'error': _("'%s' is not in this receipt.", product.display_name),
            }

        # 4. Set quantity = demand (receive the full line)
        move = matching_move[0]
        move.quantity = move.product_uom_qty
        move.picked = True

        return {
            'success': True,
            'product_name': product.display_name,
            'move_id': move.id,
            'demand': move.product_uom_qty,
        }

    def action_validate_from_barcode(self):
        """Validate the picking from the barcode receiving page."""
        self.ensure_one()
        return self.button_validate()
