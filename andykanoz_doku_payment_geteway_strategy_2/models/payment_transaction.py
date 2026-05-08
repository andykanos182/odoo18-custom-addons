# -*- coding: utf-8 -*-
"""
DOKU Payment Transaction Model

Extends payment.transaction to integrate with DOKU Checkout (Hosted Page).

Phase 4-5 Updates:
- Full webhook notification processing per DOKU spec
- Idempotent state transitions (handle duplicate webhooks)
- Auto-invoice validation (built-in via Odoo's _set_done)
- Cron jobs for auto-sync pending transactions
- Auto-expire old pending transactions

Reference:
- https://developers.doku.com/accept-payments/doku-checkout/integration-guide/backend-integration
- https://jokul.doku.com/docs/docs/http-notification/http-notification-best-practice/
"""
import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

from ..const import (
    DOKU_FRONTEND_JS,
    PAYMENT_STATUS_MAPPING,
    PAYMENT_CODE_QRIS,
    PAYMENT_CODES_VIRTUAL_ACCOUNT,
    PAYMENT_CODES_EWALLET,
)
from ..utils.api_client import (
    DokuClient,
    DokuAPIError,
)

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # ==========================================
    # DOKU TRANSACTION FIELDS
    # ==========================================
    doku_invoice_number = fields.Char(
        string="DOKU Invoice Number",
        help="Unique invoice number sent to DOKU. Generated from Odoo reference.",
        readonly=True,
        copy=False,
        index=True,
    )

    doku_payment_url = fields.Char(
        string="DOKU Payment URL",
        readonly=True,
        copy=False,
    )

    doku_token_id = fields.Char(
        string="DOKU Token ID",
        readonly=True,
        copy=False,
    )

    doku_session_id = fields.Char(
        string="DOKU Session ID",
        readonly=True,
        copy=False,
    )

    doku_payment_method = fields.Selection(
        selection=[
            ('qris', "QRIS"),
            ('virtual_account', "Virtual Account"),
            ('ewallet', "E-Wallet"),
            ('credit_card', "Credit Card"),
            ('convenience_store', "Convenience Store"),
            ('direct_debit', "Direct Debit"),
            ('paylater', "Pay Later"),
            ('unknown', "Unknown"),
        ],
        string="Payment Method Used",
        default='unknown',
        readonly=True,
        copy=False,
    )

    doku_payment_channel = fields.Char(
        string="Payment Channel",
        readonly=True,
        copy=False,
    )

    doku_acquirer = fields.Char(
        string="DOKU Acquirer",
        readonly=True,
        copy=False,
    )

    doku_va_number = fields.Char(
        string="Virtual Account Number",
        readonly=True,
        copy=False,
    )

    doku_qris_data = fields.Text(
        string="QRIS Data",
        readonly=True,
        copy=False,
    )

    # ==========================================
    # PAYMENT TIMING
    # ==========================================
    doku_expired_at = fields.Datetime(
        string="Payment Expiry",
        readonly=True,
        copy=False,
        index=True,
    )

    doku_paid_at = fields.Datetime(
        string="Paid At",
        readonly=True,
        copy=False,
    )

    # ==========================================
    # WEBHOOK TRACKING
    # ==========================================
    doku_webhook_count = fields.Integer(
        string="Webhook Count",
        default=0,
        readonly=True,
        copy=False,
    )

    doku_last_webhook_at = fields.Datetime(
        string="Last Webhook Received",
        readonly=True,
        copy=False,
    )

    doku_last_webhook_status = fields.Char(
        string="Last Webhook Status",
        readonly=True,
        copy=False,
    )

    doku_last_status_check_at = fields.Datetime(
        string="Last Status Check",
        readonly=True,
        copy=False,
        help="Last time the status was checked via API (manual or cron).",
    )

    # ==========================================
    # RAW API DATA (debugging)
    # ==========================================
    doku_request_data = fields.Text(
        string="Last API Request",
        readonly=True,
        copy=False,
        groups='base.group_system',
    )

    doku_response_data = fields.Text(
        string="Last API Response",
        readonly=True,
        copy=False,
        groups='base.group_system',
    )

    doku_last_webhook_data = fields.Text(
        string="Last Webhook Payload",
        readonly=True,
        copy=False,
        groups='base.group_system',
    )

    # ==========================================
    # ODOO PAYMENT FLOW OVERRIDES
    # ==========================================
    def _get_specific_rendering_values(self, processing_values):
        """Override to call DOKU API and return rendering values."""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'doku':
            return res

        try:
            response = self._doku_create_payment()
        except DokuAPIError as e:
            _logger.exception(
                "DOKU: Failed to create payment for transaction %s: %s",
                self.reference, str(e)
            )
            raise UserError(_(
                "Could not initiate payment with DOKU.\n\nError: %(error)s",
                error=str(e),
            )) from e

        response_data = response.get('response', {})
        payment_data = response_data.get('payment', {})

        payment_url = payment_data.get('url')
        if not payment_url:
            raise UserError(_(
                "DOKU did not return a payment URL. Please check logs and try again."
            ))

        self.write({
            'doku_payment_url': payment_url,
            'doku_token_id': payment_data.get('token_id'),
            'doku_session_id': response_data.get('order', {}).get('session_id'),
            'doku_response_data': str(response)[:5000],
        })

        environment = self.provider_id.doku_environment or 'sandbox'
        jokul_js_url = DOKU_FRONTEND_JS.get(environment, DOKU_FRONTEND_JS['sandbox'])

        return {
            'doku_payment_url': payment_url,
            'doku_jokul_js_url': jokul_js_url,
            'reference': self.reference,
            'return_url': '/payment/status',
        }

    # ==========================================
    # DOKU API METHODS
    # ==========================================
    def _doku_create_payment(self):
        """Call DOKU API to create payment session and get payment URL."""
        self.ensure_one()
        provider = self.provider_id

        invoice_number = self._doku_build_invoice_number()
        customer = self._doku_build_customer_dict()
        line_items = self._doku_build_line_items()

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        callback_url = f"{base_url}/payment/doku/return?reference={self.reference}"

        payment_method_types = self._doku_get_enabled_payment_methods()

        client = DokuClient(
            client_id=provider.doku_client_id,
            secret_key=provider.doku_secret_key,
            merchant_code=provider.doku_merchant_code,
            environment=provider.doku_environment or 'sandbox',
        )

        amount_int = int(round(self.amount))

        self.doku_invoice_number = invoice_number

        expiry_minutes = provider.doku_payment_expiry_minutes or 60
        self.doku_expired_at = fields.Datetime.now() + timedelta(minutes=expiry_minutes)

        request_log = {
            'invoice_number': invoice_number,
            'amount': amount_int,
            'payment_due_date': expiry_minutes,
            'payment_method_types': payment_method_types,
            'customer': customer,
            'line_items_count': len(line_items) if line_items else 0,
        }
        self.doku_request_data = str(request_log)[:5000]

        return client.create_payment(
            invoice_number=invoice_number,
            amount=amount_int,
            payment_due_date=expiry_minutes,
            customer=customer,
            line_items=line_items,
            payment_method_types=payment_method_types,
            callback_url=callback_url,
            callback_url_result=callback_url,
            auto_redirect=False,
        )

    def _doku_build_invoice_number(self):
        """Build DOKU-compatible invoice number from Odoo reference."""
        self.ensure_one()
        ref = self.reference or ''
        sanitized = ''.join(
            c if c.isalnum() or c in '-_' else '-'
            for c in ref
        )
        return sanitized[:30]

    def _doku_build_customer_dict(self):
        """Build customer object for DOKU API from partner_id."""
        self.ensure_one()
        if not self.partner_id:
            return None

        partner = self.partner_id
        customer = {}

        if partner.name:
            customer['name'] = partner.name[:255]
        if partner.email:
            customer['email'] = partner.email[:128]
        if partner.phone:
            phone = ''.join(c for c in (partner.phone or '') if c.isdigit())
            if phone:
                customer['phone'] = phone[:16]
        if partner.street:
            customer['address'] = partner.street[:400]
        if partner.zip:
            customer['postcode'] = str(partner.zip)
        if partner.state_id:
            customer['state'] = partner.state_id.name
        if partner.city:
            customer['city'] = partner.city
        if partner.country_id:
            customer['country'] = partner.country_id.code

        return customer if customer else None

    def _doku_build_line_items(self):
        """Build line_items array from sale order if available."""
        self.ensure_one()
        sale_orders = self.env['sale.order'].browse([])
        if hasattr(self, 'sale_order_ids') and self.sale_order_ids:
            sale_orders = self.sale_order_ids

        if not sale_orders:
            return None

        line_items = []
        for order in sale_orders:
            for line in order.order_line:
                if line.display_type:
                    continue
                line_items.append({
                    'id': str(line.product_id.id) if line.product_id else str(line.id),
                    'name': (line.product_id.name or line.name or '')[:255],
                    'quantity': int(line.product_uom_qty),
                    'price': int(round(line.price_unit)),
                })

        return line_items if line_items else None

    def _doku_get_enabled_payment_methods(self):
        """
        Get the specific payment method type chosen by the user in Odoo 
        and map it to the DOKU API's expected string.
        """
        self.ensure_one()
        from ..const import PAYMENT_METHODS_MAPPING
        
        # payment_method_id is automatically set by Odoo when user clicks "Pay Now"
        if not self.payment_method_id:
            return None
            
        odoo_pm_code = self.payment_method_id.code
        doku_pm_code = PAYMENT_METHODS_MAPPING.get(odoo_pm_code)
        
        # If we have a mapping, send it as a single-item list so DOKU 
        # bypasses its own selection screen and jumps straight to the instruction.
        if doku_pm_code:
            return [doku_pm_code]
            
        return None

    # ==========================================
    # WEBHOOK PROCESSING
    # ==========================================
    def _process_doku_notification(self, notification_data):
        """
        Process payment notification from DOKU webhook.

        IDEMPOTENT - safe to call multiple times for same event.
        """
        self.ensure_one()

        self.doku_webhook_count += 1
        self.doku_last_webhook_at = fields.Datetime.now()
        self.doku_last_webhook_data = str(notification_data)[:5000]

        transaction_data = notification_data.get('transaction', {}) or {}
        order_data = notification_data.get('order', {}) or {}
        service_data = notification_data.get('service', {}) or {}
        acquirer_data = notification_data.get('acquirer', {}) or {}
        channel_data = notification_data.get('channel', {}) or {}

        status = (transaction_data.get('status') or '').upper()
        self.doku_last_webhook_status = status

        self._doku_update_payment_method_info(
            service_data, acquirer_data, channel_data, notification_data
        )

        _logger.info(
            "DOKU: Processing notification for tx %s - status=%s, channel=%s, current_state=%s",
            self.reference, status, channel_data.get('id'), self.state
        )

        # Idempotency: skip if already done
        if self.state == 'done' and status == 'SUCCESS':
            _logger.info(
                "DOKU: Transaction %s already done, idempotent ack",
                self.reference
            )
            return True

        if status == 'SUCCESS':
            return self._doku_handle_success(transaction_data, order_data)
        elif status == 'FAILED':
            return self._doku_handle_failed(transaction_data, order_data)
        else:
            _logger.warning(
                "DOKU: Unknown notification status '%s' for tx %s",
                status, self.reference
            )
            return False

    def _doku_handle_success(self, transaction_data, order_data):
        """Handle SUCCESS notification from DOKU."""
        self.ensure_one()

        # Amount validation (security check)
        notification_amount = order_data.get('amount')
        if notification_amount is not None:
            tx_amount = int(round(self.amount))
            if int(notification_amount) != tx_amount:
                _logger.error(
                    "DOKU: Amount mismatch for tx %s! "
                    "Expected %d, got %d. NOT marking as done.",
                    self.reference, tx_amount, notification_amount
                )
                self._set_error(_(
                    "Amount mismatch in DOKU notification. "
                    "Expected %(expected)s, got %(received)s.",
                    expected=tx_amount,
                    received=notification_amount,
                ))
                return False

        # Set paid timestamp
        paid_date_str = transaction_data.get('date')
        if paid_date_str:
            try:
                paid_dt = datetime.strptime(paid_date_str, '%Y-%m-%dT%H:%M:%SZ')
                self.doku_paid_at = paid_dt
            except (ValueError, TypeError) as e:
                _logger.warning("DOKU: Could not parse paid_at date '%s': %s",
                                paid_date_str, str(e))
                self.doku_paid_at = fields.Datetime.now()
        else:
            self.doku_paid_at = fields.Datetime.now()

        original_request_id = transaction_data.get('original_request_id')
        if original_request_id and not self.provider_reference:
            self.provider_reference = original_request_id

        # This auto-handles: state=done, payment record creation,
        # invoice reconciliation, sale order confirmation, email
        self._set_done()

        _logger.info(
            "DOKU: Transaction %s marked as DONE successfully",
            self.reference
        )
        return True

    def _doku_handle_failed(self, transaction_data, order_data):
        """
        Handle FAILED notification - IGNORED for Checkout per DOKU spec.

        Customer can retry with different payment method.
        """
        self.ensure_one()
        _logger.info(
            "DOKU: FAILED notification for tx %s - IGNORED (customer may retry)",
            self.reference
        )
        return True

    def _doku_update_payment_method_info(self, service_data, acquirer_data,
                                          channel_data, full_notification):
        """Extract and store payment method details from notification."""
        self.ensure_one()

        channel_id = channel_data.get('id', '')
        service_id = service_data.get('id', '')
        acquirer_id = acquirer_data.get('id', '')

        if channel_id:
            self.doku_payment_channel = channel_id
        if acquirer_id:
            self.doku_acquirer = acquirer_id

        method_map = {
            'VIRTUAL_ACCOUNT': 'virtual_account',
            'EMONEY': 'ewallet',
            'QRIS': 'qris',
            'CREDIT_CARD': 'credit_card',
            'ONLINE_TO_OFFLINE': 'convenience_store',
            'DIRECT_DEBIT': 'direct_debit',
            'PEER_TO_PEER': 'paylater',
        }
        if service_id in method_map:
            self.doku_payment_method = method_map[service_id]
        elif channel_id == 'QRIS':
            self.doku_payment_method = 'qris'

        va_info = full_notification.get('virtual_account_info', {}) or {}
        if va_info.get('virtual_account_number'):
            self.doku_va_number = va_info['virtual_account_number']

    # ==========================================
    # CRON METHODS (Phase 5)
    # ==========================================
    @api.model
    def _cron_doku_check_pending_transactions(self):
        """
        Cron job: Check status of pending DOKU transactions.

        Runs every 15 minutes.
        Catches transactions that may have missed webhook notifications.

        Logic:
        - Find pending DOKU transactions less than 24 hours old
        - Skip if checked within last 5 minutes (avoid hammering API)
        - Call DOKU check_status API
        - Update transaction state if status returned
        """
        five_minutes_ago = fields.Datetime.now() - timedelta(minutes=5)
        twenty_four_hours_ago = fields.Datetime.now() - timedelta(hours=24)

        pending_txs = self.search([
            ('provider_code', '=', 'doku'),
            ('state', '=', 'pending'),
            ('doku_invoice_number', '!=', False),
            ('create_date', '>', twenty_four_hours_ago),
            '|',
            ('doku_last_status_check_at', '=', False),
            ('doku_last_status_check_at', '<', five_minutes_ago),
        ], limit=50)  # Process max 50 per run

        if not pending_txs:
            return True

        _logger.info(
            "DOKU Cron: Checking status of %d pending transactions",
            len(pending_txs)
        )

        for tx in pending_txs:
            try:
                tx._doku_sync_status()
            except Exception as e:
                _logger.warning(
                    "DOKU Cron: Failed to check status for tx %s: %s",
                    tx.reference, str(e)
                )
                # Don't break the cron, continue with next transaction
                continue

        return True

    @api.model
    def _cron_doku_expire_old_transactions(self):
        """
        Cron job: Mark expired DOKU pending transactions as cancelled.

        Runs every hour.
        Marks transactions as 'cancel' if expiry passed and still pending.
        """
        now = fields.Datetime.now()

        expired_txs = self.search([
            ('provider_code', '=', 'doku'),
            ('state', '=', 'pending'),
            ('doku_expired_at', '!=', False),
            ('doku_expired_at', '<', now),
        ], limit=100)

        if not expired_txs:
            return True

        _logger.info(
            "DOKU Cron: Expiring %d old pending transactions",
            len(expired_txs)
        )

        for tx in expired_txs:
            try:
                # Try one final status check before expiring
                # (in case it actually paid but webhook missed)
                tx._doku_sync_status()

                # If still pending, mark as cancelled
                if tx.state == 'pending':
                    tx._set_canceled(state_message=_(
                        "Payment expired (passed expiry time without confirmation)"
                    ))
                    _logger.info(
                        "DOKU: Expired transaction %s marked as cancelled",
                        tx.reference
                    )
            except Exception as e:
                _logger.warning(
                    "DOKU: Could not expire tx %s: %s",
                    tx.reference, str(e)
                )
                continue

        return True

    def _doku_sync_status(self):
        """
        Sync transaction status with DOKU API.

        Used by cron and manual button. Treats API response like webhook.
        """
        self.ensure_one()

        if self.provider_code != 'doku':
            return False
        if not self.doku_invoice_number:
            return False

        provider = self.provider_id
        if not provider.doku_client_id or not provider.doku_secret_key:
            _logger.warning("DOKU: Missing credentials for provider %s", provider.name)
            return False

        client = DokuClient(
            client_id=provider.doku_client_id,
            secret_key=provider.doku_secret_key,
            merchant_code=provider.doku_merchant_code,
            environment=provider.doku_environment or 'sandbox',
        )

        self.doku_last_status_check_at = fields.Datetime.now()

        try:
            response = client.check_payment_status(self.doku_invoice_number)
        except DokuAPIError as e:
            _logger.warning(
                "DOKU: Status check failed for tx %s: %s",
                self.reference, str(e)
            )
            return False

        # Process response as if it were a notification
        if response and isinstance(response, dict):
            try:
                self._process_doku_notification(response)
            except Exception as e:
                _logger.warning(
                    "DOKU: Could not process check_status response: %s",
                    str(e)
                )
                return False

        return True

    # ==========================================
    # ACTIONS (Buttons)
    # ==========================================
    def action_view_doku_payment(self):
        """Open the DOKU payment URL in a new tab."""
        self.ensure_one()
        if not self.doku_payment_url:
            raise ValidationError(_("No DOKU payment URL available for this transaction."))

        return {
            'type': 'ir.actions.act_url',
            'url': self.doku_payment_url,
            'target': 'new',
        }

    def action_check_doku_status(self):
        """Manually trigger a status check with DOKU API."""
        self.ensure_one()
        if self.provider_code != 'doku':
            return False

        if not self.doku_invoice_number:
            raise UserError(_("No DOKU invoice number for this transaction."))

        old_state = self.state
        success = self._doku_sync_status()

        if not success:
            raise UserError(_(
                "Failed to check status with DOKU. Check the logs for details."
            ))

        new_state = self.state
        state_changed = old_state != new_state

        message = _(
            "Status check complete.\n"
            "Previous state: %(old)s\n"
            "Current state: %(new)s\n"
            "%(changed_msg)s",
            old=dict(self._fields['state'].selection).get(old_state, old_state),
            new=dict(self._fields['state'].selection).get(new_state, new_state),
            changed_msg=_("✓ State updated!") if state_changed else _("(No change)"),
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if state_changed else 'info',
                'title': _("DOKU Status Check"),
                'message': message,
                'sticky': True,
            },
        }

    def _doku_cancel_payment(self):
        """Cancel payment and void transaction in DOKU API."""
        self.ensure_one()
        if self.provider_code != 'doku' or self.state != 'pending':
            return False

        if not self.doku_invoice_number:
            self._set_canceled("Canceled by user before DOKU invoice was generated.")
            return True

        provider = self.provider_id
        from ..utils.api_client import DokuClient
        client = DokuClient(
            client_id=provider.doku_client_id,
            secret_key=provider.doku_secret_key,
            merchant_code=provider.doku_merchant_code,
            environment=provider.doku_environment or 'sandbox',
        )

        try:
            # Note: The void API endpoint is defined in const.py as '/orders/v1/void'
            from ..const import DOKU_ENDPOINTS
            endpoint = DOKU_ENDPOINTS.get('void', '/orders/v1/void').lstrip('/')
            payload = {'invoice_number': self.doku_invoice_number}
            
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info("DOKU: Attempting to void transaction %s (Invoice: %s)", self.reference, self.doku_invoice_number)
            
            # Use raw request since api_client might not have a wrapper for void
            response = client._post(endpoint, payload)
            _logger.info("DOKU: Void response: %s", response)
            
        except Exception as e:
            # Even if DOKU fails (e.g., already expired, or not supported by channel),
            # we still cancel it locally to free up the Odoo order.
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning("DOKU: Failed to void transaction %s remotely: %s", self.reference, e)

        # Set transaction as canceled in Odoo
        self._set_canceled("Transaction canceled by user from Pending Page.")
        return True
