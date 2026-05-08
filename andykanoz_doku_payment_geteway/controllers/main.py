# -*- coding: utf-8 -*-
"""
DOKU Payment Gateway - HTTP Controllers

Routes:
- POST /payment/doku/webhook       → DOKU notification handler (signed)
- GET  /payment/doku/return        → Customer return after payment
- GET  /payment/doku/pending/<id>  → Tokopedia-style pending page (Strategy 2)
- POST /payment/doku/cancel/<id>   → Cancel pending payment

Reference:
- https://developers.doku.com/accept-payments/doku-checkout/integration-guide/simulate-payment-and-notification
- https://jokul.doku.com/docs/docs/http-notification/http-notification-best-practice/
"""
import json
import logging
import pprint

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from ..const import WEBHOOK_NOTIFICATION_URL
from ..utils.signature import DokuSignature

_logger = logging.getLogger(__name__)


class DokuPaymentController(http.Controller):
    """Controller for DOKU Payment Gateway webhooks, returns, and pending page."""

    _webhook_url = '/payment/doku/webhook'
    _return_url = '/payment/doku/return'
    _pending_url = '/payment/doku/pending'
    _cancel_url = '/payment/doku/cancel'

    # ==========================================
    # WEBHOOK NOTIFICATION (from DOKU server)
    # ==========================================
    @http.route(
        _webhook_url,
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def doku_webhook(self, **kwargs):
        """Handle webhook notifications from DOKU."""
        # ==========================================
        # STEP 1: Read raw body
        # ==========================================
        raw_body_bytes = request.httprequest.data
        raw_body_str = raw_body_bytes.decode('utf-8') if raw_body_bytes else ''

        headers = request.httprequest.headers
        client_id_header = headers.get('Client-Id', '')
        request_id_header = headers.get('Request-Id', '')
        timestamp_header = headers.get('Request-Timestamp', '')
        signature_header = headers.get('Signature', '')

        _logger.info(
            "DOKU Webhook received:\n"
            "Client-Id: %s\nRequest-Id: %s\nRequest-Timestamp: %s\n"
            "Signature: %s\nBody: %s",
            client_id_header,
            request_id_header,
            timestamp_header,
            (signature_header[:30] + '...') if len(signature_header) > 30 else signature_header,
            raw_body_str[:1000],
        )

        # ==========================================
        # STEP 2: Parse JSON
        # ==========================================
        try:
            data = json.loads(raw_body_str) if raw_body_str else {}
        except json.JSONDecodeError as e:
            _logger.error("DOKU Webhook: Invalid JSON: %s", str(e))
            return request.make_json_response(
                {'status': 'error', 'message': 'Invalid JSON'}, status=400
            )

        # ==========================================
        # STEP 3: Find transaction
        # ==========================================
        order_data = data.get('order', {})
        invoice_number = order_data.get('invoice_number')

        if not invoice_number:
            _logger.warning("DOKU Webhook: Missing invoice_number")
            return request.make_json_response(
                {'status': 'error', 'message': 'Missing invoice_number'}, status=400
            )

        tx = request.env['payment.transaction'].sudo().search([
            ('doku_invoice_number', '=', invoice_number),
            ('provider_code', '=', 'doku'),
        ], limit=1)

        if not tx:
            _logger.warning(
                "DOKU Webhook: No transaction found for invoice_number=%s",
                invoice_number
            )
            return request.make_json_response(
                {'status': 'error', 'message': 'Transaction not found'}, status=404
            )

        # ==========================================
        # STEP 4: Verify signature
        # ==========================================
        provider = tx.provider_id
        if not provider.doku_secret_key:
            _logger.error(
                "DOKU Webhook: Provider has no secret_key for tx %s",
                tx.reference
            )
            return request.make_json_response(
                {'status': 'error', 'message': 'Provider not configured'}, status=500
            )

        if client_id_header and provider.doku_client_id:
            if client_id_header != provider.doku_client_id:
                _logger.warning(
                    "DOKU Webhook: Client-Id mismatch for tx %s. Got %s",
                    tx.reference, client_id_header
                )
                return request.make_json_response(
                    {'status': 'error', 'message': 'Client-Id mismatch'}, status=401
                )

        signer = DokuSignature(
            client_id=provider.doku_client_id,
            secret_key=provider.doku_secret_key,
        )

        is_valid = signer.verify_webhook_signature(
            received_signature=signature_header,
            target_path=WEBHOOK_NOTIFICATION_URL,
            raw_body=raw_body_str,
            request_id=request_id_header,
            timestamp=timestamp_header,
        )

        if not is_valid:
            _logger.warning(
                "DOKU Webhook: Invalid signature for tx %s (invoice %s)",
                tx.reference, invoice_number
            )
            tx.sudo().doku_webhook_count += 1
            return request.make_json_response(
                {'status': 'error', 'message': 'Invalid signature'}, status=401
            )

        _logger.info("DOKU Webhook: Signature verified for tx %s", tx.reference)

        # ==========================================
        # STEP 5: Process notification
        # ==========================================
        try:
            tx.sudo()._process_doku_notification(data)
        except Exception as e:
            _logger.exception(
                "DOKU Webhook: Error processing notification for tx %s: %s",
                tx.reference, str(e)
            )
            return request.make_json_response({
                'status': 'received',
                'message': 'Acknowledged but processing error logged',
                'invoice_number': invoice_number,
            })

        return request.make_json_response({
            'status': 'success',
            'invoice_number': invoice_number,
            'transaction_state': tx.state,
        })

    # ==========================================
    # RETURN URL (after customer payment)
    # ==========================================
    @http.route(
        _return_url,
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
        save_session=False,
    )
    def doku_return(self, **kwargs):
        """
        Handle customer return after payment at DOKU hosted page.

        Strategy 2 Modification:
        - If transaction is still PENDING (customer didn't complete payment),
          redirect to our custom Tokopedia-style pending page instead of
          the generic /payment/status page.
        - If transaction is DONE / ERROR / CANCEL, use Odoo's default flow.
        """
        _logger.info(
            "DOKU Return URL accessed with params:\n%s",
            pprint.pformat(kwargs)
        )

        reference = kwargs.get('reference')
        if reference:
            tx = request.env['payment.transaction'].sudo().search([
                ('reference', '=', reference),
                ('provider_code', '=', 'doku'),
            ], limit=1)

            if tx:
                _logger.info(
                    "DOKU Return: Transaction %s state=%s",
                    tx.reference, tx.state
                )

                # Sync status immediately on return.
                # Webhook from DOKU may arrive before or simultaneously with customer
                # returning. Syncing here catches "already paid" cases so we can
                # redirect straight to /payment/status instead of the pending page.
                if tx.state in ('draft', 'pending'):
                    try:
                        tx.sudo()._doku_sync_status()
                    except Exception:
                        _logger.warning(
                            "DOKU Return: Could not sync status for tx %s on return",
                            tx.reference, exc_info=True
                        )

                # Strategy 2: Redirect pending/draft tx to custom pending page
                if tx.state in ('draft', 'pending'):
                    return request.redirect(f'{self._pending_url}/{tx.id}')

        # Default: redirect to standard payment status page
        return request.redirect('/payment/status')

    # ==========================================
    # PENDING PAYMENT PAGE (Strategy 2 - Semi Tokopedia)
    # ==========================================
    @http.route(
        f'{_pending_url}/<int:tx_id>',
        type='http',
        auth='public',
        methods=['GET'],
        website=True,
    )
    def doku_pending_page(self, tx_id, **kwargs):
        """
        Render Tokopedia-style pending payment page.

        Access control:
        - Must be the partner who owns the transaction, OR
        - Must have a valid access token (for guest portal access), OR
        - Logged in as internal user (admin/manager)
        """
        try:
            tx = request.env['payment.transaction'].sudo().browse(tx_id).exists()
        except (AccessError, MissingError):
            return request.redirect('/my/orders')

        if not tx or tx.provider_code != 'doku':
            _logger.warning("DOKU Pending: Invalid tx_id %s", tx_id)
            return request.redirect('/my/orders')

        # Access control check
        user = request.env.user
        is_authorized = False

        if user.has_group('base.group_user'):
            # Internal users (admin, salespeople) can view any transaction
            is_authorized = True
        elif user.partner_id and tx.partner_id:
            # Logged-in customer viewing their own transaction
            if user.partner_id == tx.partner_id:
                is_authorized = True
            else:
                # Check parent partner relationship (company → contact)
                if user.partner_id.commercial_partner_id == tx.partner_id.commercial_partner_id:
                    is_authorized = True

        # Check access token from kwargs (for portal guest access)
        access_token = kwargs.get('access_token')
        if not is_authorized and access_token:
            # Validate token against linked sale order
            sale_order = tx.sale_order_ids[:1] if hasattr(tx, 'sale_order_ids') else None
            if sale_order and sale_order.access_token == access_token:
                is_authorized = True

        if not is_authorized:
            _logger.warning(
                "DOKU Pending: Unauthorized access attempt to tx %s by user %s",
                tx.reference, user.login
            )
            return request.redirect('/my/orders')

        # Lazy Auto Cancel check if expired
        now = fields.Datetime.now()
        if tx.state in ('draft', 'pending') and tx.doku_expired_at and tx.doku_expired_at < now:
            try:
                tx._doku_sync_status()
                if tx.state in ('draft', 'pending'):
                    tx._set_canceled(state_message=_("Otomatis dibatalkan karena batas waktu pembayaran habis."))
            except Exception:
                pass

        # If transaction is no longer pending/draft, redirect to status page
        if tx.state not in ('draft', 'pending'):
            _logger.info(
                "DOKU Pending: Tx %s is in state %s, redirecting to status",
                tx.reference, tx.state
            )
            return request.redirect('/payment/status')

        # Render the pending page
        values = {
            'transaction': tx,
            'cancel_url': f'{self._cancel_url}/{tx.id}',
        }
        return request.render(
            'andykanoz_doku_payment_geteway.doku_pending_payment_page',
            values
        )

    # ==========================================
    # AJAX STATUS CHECK (for pending page polling)
    # ==========================================
    @http.route(
        '/payment/doku/check-status/<int:tx_id>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def doku_check_status(self, tx_id, **kwargs):
        """
        JSON endpoint polled by the pending page every few seconds.

        Syncs status with DOKU API if still pending, then returns current
        transaction state so the frontend can auto-redirect when done.

        Returns: {"state": "<odoo_state>"}
        States: draft | pending | done | cancel | error
        """
        try:
            tx = request.env['payment.transaction'].sudo().browse(tx_id).exists()
        except Exception:
            return request.make_json_response({'state': 'not_found'}, status=404)

        if not tx or tx.provider_code != 'doku':
            return request.make_json_response({'state': 'not_found'}, status=404)

        # Sync with DOKU API if still waiting
        if tx.state in ('draft', 'pending'):
            try:
                tx._doku_sync_status()
            except Exception:
                _logger.warning(
                    "DOKU check-status: sync failed for tx %s", tx_id, exc_info=True
                )

        return request.make_json_response({'state': tx.state})

    # ==========================================
    # CANCEL PENDING PAYMENT
    # ==========================================
    @http.route(
        f'{_cancel_url}/<int:tx_id>',
        type='http',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def doku_cancel_payment(self, tx_id, **kwargs):
        """
        Cancel a pending DOKU payment.

        Note: DOKU Checkout (Hosted Page) does not have a generic
        "cancel session" API endpoint. The session will auto-expire
        on DOKU's side based on payment_due_date. We just mark the
        Odoo transaction as cancelled so customer can create a new one.
        """
        try:
            tx = request.env['payment.transaction'].sudo().browse(tx_id).exists()
        except (AccessError, MissingError):
            return request.redirect('/my/orders')

        if not tx or tx.provider_code != 'doku':
            return request.redirect('/my/orders')

        # Same authorization check as pending page
        user = request.env.user
        is_authorized = False

        if user.has_group('base.group_user'):
            is_authorized = True
        elif user.partner_id and tx.partner_id:
            if user.partner_id == tx.partner_id:
                is_authorized = True
            elif user.partner_id.commercial_partner_id == tx.partner_id.commercial_partner_id:
                is_authorized = True

        if not is_authorized:
            _logger.warning(
                "DOKU Cancel: Unauthorized cancel attempt for tx %s by user %s",
                tx.reference, user.login
            )
            return request.redirect('/my/orders')

        # Only cancel pending/draft transactions
        if tx.state not in ('draft', 'pending'):
            _logger.info(
                "DOKU Cancel: Tx %s already in state %s, no action",
                tx.reference, tx.state
            )
            return request.redirect('/my/orders')

        # Mark transaction as cancelled
        try:
            tx._set_canceled(state_message=_(
                "Cancelled by customer from pending payment page."
            ))
            _logger.info("DOKU Cancel: Tx %s cancelled by customer", tx.reference)
        except Exception as e:
            _logger.exception(
                "DOKU Cancel: Error cancelling tx %s: %s",
                tx.reference, str(e)
            )

        # Redirect to portal orders page
        return request.redirect('/my/orders')
