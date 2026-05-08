# -*- coding: utf-8 -*-
"""
DOKU Payment Gateway - HTTP Controllers

Handles webhook notifications from DOKU and customer return URLs.

Phase 4 (Current): Full webhook processing with signature verification

Reference:
- https://developers.doku.com/accept-payments/doku-checkout/integration-guide/simulate-payment-and-notification
- https://dashboard.doku.com/docs/docs/http-notification/http-notification/
- https://jokul.doku.com/docs/docs/http-notification/http-notification-best-practice/
"""
import json
import logging
import pprint

from odoo import http
from odoo.http import request

from ..const import WEBHOOK_NOTIFICATION_URL
from ..utils.signature import DokuSignature

_logger = logging.getLogger(__name__)


class DokuPaymentController(http.Controller):
    """Controller for DOKU Payment Gateway webhooks and returns."""

    _webhook_url = '/payment/doku/webhook'
    _return_url = '/payment/doku/return'

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
        """
        Handle webhook notifications from DOKU.

        Flow:
        1. Read raw body (CRITICAL for signature verification)
        2. Parse JSON
        3. Find transaction by invoice_number
        4. Verify HMAC-SHA256 signature using merchant's secret key
        5. Process notification (idempotent)
        6. Return 200 OK or appropriate error

        Per DOKU best practices:
        - For Checkout integration, IGNORE 'FAILED' status (customer can retry)
        - Be idempotent (same event can come multiple times)
        - Parse JSON in non-strict mode (allow extra fields)
        - Always return 200 for success, 401 for invalid signature
        """
        # ==========================================
        # STEP 1: Read raw body (must be raw bytes for signature)
        # ==========================================
        raw_body_bytes = request.httprequest.data
        raw_body_str = raw_body_bytes.decode('utf-8') if raw_body_bytes else ''

        # Get request headers
        headers = request.httprequest.headers
        client_id_header = headers.get('Client-Id', '')
        request_id_header = headers.get('Request-Id', '')
        timestamp_header = headers.get('Request-Timestamp', '')
        signature_header = headers.get('Signature', '')

        _logger.info(
            "DOKU Webhook received:\n"
            "Client-Id: %s\n"
            "Request-Id: %s\n"
            "Request-Timestamp: %s\n"
            "Signature: %s\n"
            "Body: %s",
            client_id_header,
            request_id_header,
            timestamp_header,
            signature_header[:30] + '...' if len(signature_header) > 30 else signature_header,
            raw_body_str[:1000],  # Truncate for logging
        )

        # ==========================================
        # STEP 2: Parse JSON
        # ==========================================
        try:
            data = json.loads(raw_body_str) if raw_body_str else {}
        except json.JSONDecodeError as e:
            _logger.error("DOKU Webhook: Invalid JSON: %s", str(e))
            return request.make_json_response(
                {'status': 'error', 'message': 'Invalid JSON'},
                status=400
            )

        # ==========================================
        # STEP 3: Find transaction by invoice_number
        # ==========================================
        order_data = data.get('order', {})
        invoice_number = order_data.get('invoice_number')

        if not invoice_number:
            _logger.warning("DOKU Webhook: Missing invoice_number in payload")
            return request.make_json_response(
                {'status': 'error', 'message': 'Missing invoice_number'},
                status=400
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
                {'status': 'error', 'message': 'Transaction not found'},
                status=404
            )

        # ==========================================
        # STEP 4: Verify signature
        # ==========================================
        provider = tx.provider_id
        if not provider.doku_secret_key:
            _logger.error(
                "DOKU Webhook: Provider has no secret_key configured for tx %s",
                tx.reference
            )
            return request.make_json_response(
                {'status': 'error', 'message': 'Provider not configured'},
                status=500
            )

        # Optional: Verify Client-Id matches our merchant
        if client_id_header and provider.doku_client_id:
            if client_id_header != provider.doku_client_id:
                _logger.warning(
                    "DOKU Webhook: Client-Id mismatch for tx %s. "
                    "Got %s, expected %s",
                    tx.reference, client_id_header, provider.doku_client_id
                )
                return request.make_json_response(
                    {'status': 'error', 'message': 'Client-Id mismatch'},
                    status=401
                )

        # Verify HMAC-SHA256 signature
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
                "DOKU Webhook: Invalid signature for tx %s (invoice %s). "
                "This could be a security issue or signature mismatch.",
                tx.reference, invoice_number
            )
            # Increment counter for tracking
            tx.sudo().doku_webhook_count += 1
            return request.make_json_response(
                {'status': 'error', 'message': 'Invalid signature'},
                status=401
            )

        _logger.info(
            "DOKU Webhook: Signature verified successfully for tx %s",
            tx.reference
        )

        # ==========================================
        # STEP 5: Process notification (idempotent)
        # ==========================================
        try:
            tx.sudo()._process_doku_notification(data)
        except Exception as e:
            _logger.exception(
                "DOKU Webhook: Error processing notification for tx %s: %s",
                tx.reference, str(e)
            )
            # Return 200 to DOKU even on processing error to prevent retries
            # The error is logged for our investigation
            return request.make_json_response({
                'status': 'received',
                'message': 'Acknowledged but processing error logged',
                'invoice_number': invoice_number,
            })

        # ==========================================
        # STEP 6: Return 200 OK
        # ==========================================
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

        We don't update transaction state here - that's done via webhook
        which is the trusted source. We just redirect customer to status page.

        :param dict kwargs: Query parameters from DOKU callback
        :return: Redirect response to /payment/status
        """
        _logger.info(
            "DOKU Return URL accessed with params:\n%s",
            pprint.pformat(kwargs)
        )

        # Try to find transaction from query params (for logging only)
        reference = kwargs.get('reference')
        if reference:
            tx = request.env['payment.transaction'].sudo().search([
                ('reference', '=', reference),
                ('provider_code', '=', 'doku'),
            ], limit=1)

            if tx:
                _logger.info(
                    "DOKU Return: Transaction %s state=%s "
                    "(webhook will update if not already done)",
                    tx.reference, tx.state
                )

        # Redirect to standard payment status page
        # Odoo's payment_status route shows the appropriate UI based on state
        return request.redirect('/payment/status')
