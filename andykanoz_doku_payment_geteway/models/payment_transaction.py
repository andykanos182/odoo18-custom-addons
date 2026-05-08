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

=============================================================================
CATATAN PENTING — Alur State Sale Order (ditemukan 2026-05-02)
=============================================================================
Alur BENAR yang sudah diverifikasi via test payment nyata:

  sale.order: draft → sent → sale

  1. draft  : State awal SO dari website checkout.
  2. sent   : Odoo core otomatis memanggil action_quotation_sent() ketika
              _set_pending() dipanggil (saat DOKU URL dibuat). State ini
              SEMENTARA dan NORMAL — bukan error.
  3. sale   : Dikonfirmasi otomatis oleh Odoo core melalui:
              _set_done() → _reconcile_after_done()
              → _check_amount_and_confirm_order() → _action_confirm()
              Ini terjadi saat webhook DOKU masuk dengan status SUCCESS.

Bukti bahwa flow berjalan benar:
- Invoice otomatis terbuat dan ter-validasi (state: Dibayar)
- Delivery order otomatis terbuat (state: Persiapan)
- Manufacturing order otomatis terbuat (state: Dikonfirmasi)
- Semua record terbuat walaupun ada jeda waktu antara _set_pending()
  dan _set_done() (tergantung kecepatan webhook DOKU).

Jangan salah diagnosis "Quotation Sent" sebagai bug — itu hanya snapshot
sementara yang terlihat jika backend dicek sebelum webhook masuk.
=============================================================================

Reference:
- https://developers.doku.com/accept-payments/doku-checkout/integration-guide/backend-integration
- https://jokul.doku.com/docs/docs/http-notification/http-notification-best-practice/
"""
import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

from ..const import (
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


# Whitelist of characters accepted by DOKU API in text fields (customer.name,
# customer.address, customer.city, customer.state, line_items[].name, etc.).
# Source: DOKU's own 400 Bad Request validation message:
#   "Invalid character, allowed only a-z A-Z 0-9 . - / + , = _ : ' @ %"
# Space is also accepted by DOKU in practice (required for multi-word names
# and addresses) even though it's not literally listed in that message.
# Any character outside this set will be replaced with a space by
# `_doku_sanitize_text` to avoid HTTP 400 from DOKU.
_DOKU_ALLOWED_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    ".-/+,=_:'@% "
)


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
        
        # Mark transaction as pending immediately since DOKU already generated the payment instruction (VA/QRIS)
        self._set_pending(state_message="Menunggu pembayaran melalui DOKU.")

        # Note: Using full redirect strategy (decided by user).
        # The redirect_form template just submits to doku_payment_url.
        return {
            'doku_payment_url': payment_url,
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
        """
        Build DOKU-compatible invoice number from Odoo reference.

        DOKU rules:
        - Must be unique per merchant (DOKU rejects duplicates with 400 Bad Request)
        - Max 30 chars (safe for Credit Card channel)
        - Alphanumeric + hyphens/underscores only

        Strategy: sanitize + truncate. If we already have a doku_invoice_number
        from a previous attempt (e.g. user retried after a network error),
        we reuse it so DOKU sees the same record.
        """
        self.ensure_one()

        # Reuse existing invoice number if we already created one for this tx.
        # This avoids accidentally creating multiple DOKU records for one Odoo tx.
        if self.doku_invoice_number:
            return self.doku_invoice_number

        ref = self.reference or ''
        sanitized = ''.join(
            c if c.isalnum() or c in '-_' else '-'
            for c in ref
        )
        return sanitized[:30]

    @staticmethod
    def _doku_sanitize_text(value):
        """
        Strip characters that DOKU's API does not accept in text fields.

        DOKU returns HTTP 400 with the message
            "Invalid character, allowed only a-z A-Z 0-9 . - / + , = _ : ' @ %"
        whenever any text field (customer name/address/city/state, line item
        name, etc.) contains a character outside that whitelist. Common
        offenders in Indonesian Odoo data: parentheses, ampersand, hash, and
        square brackets in product names and addresses.

        This helper:
          * replaces every disallowed character with a space (keeps word
            boundaries intact),
          * collapses runs of whitespace and trims edges,
          * returns None if the input is empty/falsy or becomes empty after
            sanitization (so callers can skip the field entirely).
        """
        if not value:
            return None
        cleaned = ''.join(
            c if c in _DOKU_ALLOWED_CHARS else ' '
            for c in str(value)
        )
        cleaned = ' '.join(cleaned.split())
        return cleaned or None

    def _doku_build_customer_dict(self):
        """
        Build customer object for DOKU API from partner_id.

        Defensive: ensures DOKU's expected format and never sends empty/invalid
        values that could trigger a "Bad Request" validation error.
        """
        self.ensure_one()
        if not self.partner_id:
            return None

        partner = self.partner_id
        customer = {}

        # Name: REQUIRED in DOKU spec, fallback to a safe default
        sanitized_name = self._doku_sanitize_text(partner.name)
        if sanitized_name:
            customer['name'] = sanitized_name[:255]
        else:
            customer['name'] = "Customer"

        # Email: optional but recommended
        if partner.email and '@' in partner.email:
            customer['email'] = partner.email.strip()[:128]

        # Phone: REQUIRED by DOKU API (returns 400 "customer.phone is missing
        # or null" if not sent). Digits only, prefer country-code prefix.
        # DOKU accepts "628xxxxxxxx" or "08xxxxxxxx" — avoid the "+" character.
        #
        # Fallback chain: tx snapshot -> partner mobile -> partner phone ->
        # commercial partner (parent) phone -> company phone. If all empty,
        # use a syntactically valid Indonesian placeholder so the API call
        # succeeds, but log a WARNING so admins can fix the data-quality
        # issue (e.g. enable "Phone required" in Website checkout settings).
        raw_phone = (
            getattr(self, 'partner_phone', None)
            or partner.mobile
            or partner.phone
            or (partner.commercial_partner_id.mobile
                if partner.commercial_partner_id else None)
            or (partner.commercial_partner_id.phone
                if partner.commercial_partner_id else None)
            or self.company_id.partner_id.phone
            or self.company_id.partner_id.mobile
            or ''
        )
        phone_digits = ''.join(c for c in raw_phone if c.isdigit())
        if not phone_digits or len(phone_digits) < 9:
            _logger.warning(
                "DOKU: No valid phone for tx %s (partner=%s, raw=%r). "
                "Falling back to placeholder. Consider enabling "
                "'Phone required' in Website checkout to prevent this.",
                self.reference, partner.display_name, raw_phone,
            )
            # Indonesian Telkomsel-format placeholder (12 digits, valid prefix).
            phone_digits = '081200000000'
        # Normalize prefix: leading "0" or "62" -> keep; otherwise prepend "62".
        if phone_digits.startswith('0') or phone_digits.startswith('62'):
            customer['phone'] = phone_digits[:16]
        else:
            customer['phone'] = ('62' + phone_digits)[:16]

        # Address fields (all optional). All free-text fields run through the
        # DOKU character whitelist sanitizer to avoid 400 errors from chars
        # like '(', ')', '&', '#' that commonly appear in Indonesian data.
        sanitized_address = self._doku_sanitize_text(partner.street)
        if sanitized_address:
            customer['address'] = sanitized_address[:400]
        if partner.zip and str(partner.zip).strip():
            customer['postcode'] = str(partner.zip).strip()
        sanitized_city = self._doku_sanitize_text(partner.city)
        if sanitized_city:
            customer['city'] = sanitized_city
        if partner.state_id and partner.state_id.name:
            sanitized_state = self._doku_sanitize_text(partner.state_id.name)
            if sanitized_state:
                customer['state'] = sanitized_state
        # Country: ISO 3166-1 alpha-2 (e.g. "ID")
        if partner.country_id and partner.country_id.code:
            customer['country'] = partner.country_id.code
        else:
            # Default to Indonesia since DOKU is Indonesian
            customer['country'] = 'ID'

        return customer

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
                # Sanitize the product/line name against DOKU's character
                # whitelist. Product names like "Coffee Beans (250g) [Premium]"
                # would otherwise trigger a 400 error from the API.
                raw_name = line.product_id.name or line.name or ''
                clean_name = self._doku_sanitize_text(raw_name) or 'Item'
                line_items.append({
                    'id': str(line.product_id.id) if line.product_id else str(line.id),
                    'name': clean_name[:255],
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

    def _set_canceled(self, state_message=None, extra_allowed_states=()):
        """Override to auto-cancel related sale orders when transaction is cancelled."""
        txs_to_process = super()._set_canceled(state_message, extra_allowed_states)
        for tx in txs_to_process:
            if tx.provider_code == 'doku':
                # Cancel related sales orders
                sale_orders = getattr(tx, 'sale_order_ids', self.env['sale.order'])
                for order in sale_orders:
                    if order.state in ('draft', 'sent'):
                        order._action_cancel()
                        order.message_post(body=_(
                            "Pesanan otomatis dibatalkan karena batas waktu pembayaran DOKU telah habis "
                            "atau dibatalkan oleh pengguna."
                        ))
        return txs_to_process

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

        # Orphan-payment guard: detect SUCCESS for already-cancelled SO(s).
        # DOKU Checkout has no API to void a session, so a QRIS code remains
        # scannable until the configured Payment Expiry elapses. If the
        # customer pays AFTER the SO was cancelled in Odoo (race window
        # between cancel and DOKU expiry), the money has actually arrived in
        # the DOKU account and must be refunded manually. We still allow
        # _set_done() below so the receipt is recorded in Odoo, but we log
        # loudly and post a chatter message so admins act on it.
        sale_orders = getattr(self, 'sale_order_ids', self.env['sale.order'])
        cancelled_sos = sale_orders.filtered(lambda so: so.state == 'cancel')
        if cancelled_sos:
            warning_message = _(
                "PERHATIAN: Pembayaran DOKU SUKSES diterima untuk pesanan "
                "yang sudah dibatalkan: %(refs)s. "
                "Dana sudah masuk ke akun DOKU Anda — lakukan REFUND MANUAL "
                "dari Dashboard DOKU. Transaksi Odoo tetap ditandai 'done' "
                "untuk mencatat penerimaan dana, namun tidak otomatis "
                "ter-rekonsiliasi karena pesanan terkait sudah dibatalkan.",
                refs=', '.join(cancelled_sos.mapped('name')),
            )
            _logger.error(
                "DOKU ORPHAN PAYMENT: tx %s succeeded but linked SO(s) %s "
                "are CANCELLED. Manual refund required via DOKU dashboard.",
                self.reference, cancelled_sos.mapped('name'),
            )
            # Post to the transaction's chatter (visible on tx form view).
            self.message_post(
                body=warning_message,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            # Also notify on each cancelled SO chatter.
            for so in cancelled_sos:
                so.message_post(body=warning_message)

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

        # _set_done() menangani semua secara otomatis via Odoo core:
        #   state=done, buat payment record, reconcile invoice,
        #   konfirmasi sale order (draft/sent → sale), kirim email.
        # SO dikonfirmasi lewat _check_amount_and_confirm_order() yang
        # membutuhkan tx.amount == order.amount_total (exact match).
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
