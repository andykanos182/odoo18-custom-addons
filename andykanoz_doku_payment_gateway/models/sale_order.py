# -*- coding: utf-8 -*-
"""
Sale Order extension for DOKU Payment Gateway

When a sale order is cancelled in Odoo (customer abandons checkout, staff
voids the quotation, scheduled cleanup, etc.), any related DOKU payment
transactions still in draft/pending must also be cancelled. Otherwise the
DOKU Checkout session remains scannable until `doku_payment_expiry_minutes`
elapses, which means a customer could still pay a QRIS code for an order
that no longer exists.

DOKU Checkout (Hosted Page) does NOT expose a "void session" REST endpoint,
so we cannot tell DOKU to invalidate the QR. The best we can do at the
gateway level is wait for natural session expiry. At the Odoo level we
ensure:

  * The customer portal no longer shows "Pending Payment" for the cancelled SO.
  * If the webhook later arrives with SUCCESS (race condition where the
    customer pays during the brief window between SO cancel and DOKU session
    expiry), the orphan-payment guard in
    payment_transaction._doku_handle_success will detect it, log loudly,
    and post a message to chatter for manual refund via DOKU dashboard.
"""
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_cancel(self):
        """
        Propagate SO cancellation to pending DOKU transactions.

        Runs the standard cancel logic first, then cancels any DOKU
        transaction tied to this order that is still draft/pending.

        Recursion safety: the existing override of
        payment.transaction._set_canceled also iterates sale_order_ids and
        calls _action_cancel on each. By the time that runs, the orders are
        already in 'cancel' state (super() above ran first), and we filter
        for txs in 'draft'/'pending' only — so the second pass finds no
        pending txs and terminates cleanly.
        """
        res = super()._action_cancel()

        # Find DOKU transactions still awaiting payment for these orders.
        # `transaction_ids` is the standard Many2many on sale.order pointing
        # to payment.transaction.
        pending_doku_txs = self.transaction_ids.filtered(
            lambda t: t.state in ('draft', 'pending')
                      and t.provider_code == 'doku'
        )

        if pending_doku_txs:
            _logger.info(
                "DOKU: Cancelling %d pending transaction(s) due to SO cancellation: %s",
                len(pending_doku_txs),
                pending_doku_txs.mapped('reference'),
            )
            # sudo() because the user cancelling the SO may not have
            # write access on payment.transaction.
            pending_doku_txs.sudo()._set_canceled(state_message=_(
                "Pesanan Odoo dibatalkan; pembayaran DOKU otomatis dibatalkan. "
                "Sesi DOKU Checkout akan kedaluwarsa secara alami sesuai "
                "konfigurasi Payment Expiry."
            ))

        return res
