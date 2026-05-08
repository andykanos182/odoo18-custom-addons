# -*- coding: utf-8 -*-
"""
DOKU Payment Provider Model

Extends payment.provider to add DOKU-specific configuration fields
and methods for DOKU Checkout (Hosted Page) integration.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

from ..const import (
    DOKU_API_URLS,
    SUPPORTED_CURRENCIES,
    SUPPORTED_COUNTRIES,
    DEFAULT_PAYMENT_METHOD_CODES,
)

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    # ==========================================
    # PROVIDER REGISTRATION
    # ==========================================
    code = fields.Selection(
        selection_add=[('doku', "DOKU")],
        ondelete={'doku': 'set default'},
    )

    # ==========================================
    # DOKU CREDENTIALS (SANDBOX)
    # ==========================================
    doku_client_id = fields.Char(
        string="Sandbox Client ID",
        help="The Client ID provided by DOKU Sandbox Dashboard.",
        groups='base.group_system',
    )

    doku_secret_key = fields.Char(
        string="Sandbox Secret Key",
        help="The Secret Key provided by DOKU Sandbox Dashboard. Used for HMAC-SHA256.",
        groups='base.group_system',
    )

    doku_merchant_code = fields.Char(
        string="Sandbox Merchant Code",
        help="Your unique Sandbox Merchant Code (Mall ID) provided by DOKU.",
        groups='base.group_system',
    )

    # ==========================================
    # DOKU CREDENTIALS (PRODUCTION)
    # ==========================================
    doku_live_client_id = fields.Char(
        string="Production Client ID",
        help="The Client ID provided by DOKU Live Dashboard.",
        groups='base.group_system',
    )

    doku_live_secret_key = fields.Char(
        string="Production Secret Key",
        help="The Secret Key provided by DOKU Live Dashboard. Used for HMAC-SHA256.",
        groups='base.group_system',
    )

    doku_live_merchant_code = fields.Char(
        string="Production Merchant Code",
        help="Your unique Production Merchant Code (Mall ID) provided by DOKU.",
        groups='base.group_system',
    )

    # ==========================================
    # DOKU CONFIGURATION
    # ==========================================
    doku_environment = fields.Selection(
        selection=[
            ('sandbox', "Sandbox (Testing)"),
            ('production', "Production (Live)"),
        ],
        string="DOKU Environment",
        default='sandbox',
        compute='_compute_doku_environment',
        store=True,
        readonly=True,
        help="This is automatically synced with the Odoo provider state.\n"
             "Sandbox: Use for testing with simulated transactions.\n"
             "Production: Use for real transactions (requires production credentials).",
    )

    @api.depends('state')
    def _compute_doku_environment(self):
        for provider in self:
            if provider.code == 'doku':
                provider.doku_environment = 'production' if provider.state == 'enabled' else 'sandbox'
            else:
                provider.doku_environment = False

    doku_payment_expiry_minutes = fields.Integer(
        string="Payment Expiry (Minutes)",
        default=60,
        help="Default expiry time for payment in minutes. "
             "After this period, unpaid transactions will be marked as expired.",
    )

    doku_webhook_url = fields.Char(
        string="Webhook Notification URL",
        compute='_compute_doku_webhook_url',
        help="Copy this URL to DOKU Dashboard > Configuration > Notification URL.",
    )

    doku_return_url = fields.Char(
        string="Return URL",
        compute='_compute_doku_webhook_url',
        help="Copy this URL to DOKU Dashboard > Configuration > Return URL.",
    )

    # ==========================================
    # PAYMENT METHOD ENABLEMENT
    # ==========================================
    doku_enable_qris = fields.Boolean(
        string="Enable QRIS",
        default=True,
        help="Enable QRIS payment method (scan QR code).",
    )

    doku_enable_va = fields.Boolean(
        string="Enable Virtual Account",
        default=True,
        help="Enable Virtual Account (Bank Transfer) payment method.",
    )

    doku_enable_ewallet = fields.Boolean(
        string="Enable E-Wallet",
        default=True,
        help="Enable E-Wallet payments (OVO, DANA, GoPay, ShopeePay, LinkAja).",
    )

    # ==========================================
    # COMPUTED FIELDS
    # ==========================================
    @api.depends('code')
    def _compute_doku_webhook_url(self):
        """Compute the webhook and return URLs for DOKU configuration."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for provider in self:
            if provider.code == 'doku':
                provider.doku_webhook_url = f"{base_url}/payment/doku/webhook"
                provider.doku_return_url = f"{base_url}/payment/doku/return"
            else:
                provider.doku_webhook_url = False
                provider.doku_return_url = False

    # ==========================================
    # API URL HELPER
    # ==========================================
    def _get_doku_api_url(self):
        """Return the DOKU API base URL based on environment setting."""
        self.ensure_one()
        if self.code != 'doku':
            return False
        return DOKU_API_URLS.get(self.doku_environment, DOKU_API_URLS['sandbox'])

    # ==========================================
    # FEATURE SUPPORT
    # ==========================================
    def _get_supported_currencies(self):
        """Override to filter currencies supported by DOKU (IDR only)."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'doku':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """
        Override of `payment` to return the default payment method codes for DOKU.

        These codes are used by Odoo's `setup_provider()` helper to auto-link
        the matching `payment.method` records to this provider via
        `payment_method_ids`.

        Pattern verified against payment_xendit (Odoo Enterprise official module).
        """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'doku':
            return default_codes
        return DEFAULT_PAYMENT_METHOD_CODES

    # ==========================================
    # VALIDATION
    # ==========================================
    @api.constrains('code', 'doku_client_id', 'doku_secret_key', 'doku_merchant_code', 'state')
    def _check_doku_credentials(self):
        """Ensure DOKU credentials are set when provider is enabled."""
        for provider in self:
            if provider.code != 'doku' or provider.state == 'disabled':
                continue

            missing = []
            if not provider.doku_client_id:
                missing.append("Client ID")
            if not provider.doku_secret_key:
                missing.append("Secret Key")
            if not provider.doku_merchant_code:
                missing.append("Merchant Code")

            if missing:
                raise ValidationError(_(
                    "DOKU Payment Provider requires the following credentials: %(fields)s.\n"
                    "Please fill them in or set the provider state to 'Disabled'.",
                    fields=", ".join(missing)
                ))

    # ==========================================
    # ONCHANGE
    # ==========================================

    # ==========================================
    # ACTIONS (Buttons)
    # ==========================================
    def action_doku_test_connection(self):
        """
        Test the connection to DOKU API with current credentials.

        This performs a real API call to DOKU to verify:
        - Credentials are correct (Client ID, Secret Key, Merchant Code)
        - HMAC-SHA256 signature generation works
        - Network connectivity to DOKU API
        - Environment URL is reachable

        Strategy:
        We attempt to create a test payment with minimal amount.
        - If we get a valid payment URL back → credentials work ✅
        - If we get 401/403 → credentials are wrong ❌
        - If we get connection error → network/URL issue ❌

        Note: We cancel/ignore the test transaction immediately,
        no real payment is created on DOKU's side until customer pays.
        """
        self.ensure_one()
        if self.code != 'doku':
            raise UserError(_("This is not a DOKU provider."))

        # Validate credentials are filled
        missing = []
        if not self.doku_client_id:
            missing.append("Client ID")
        if not self.doku_secret_key:
            missing.append("Secret Key")
        if not self.doku_merchant_code:
            missing.append("Merchant Code")

        if missing:
            raise UserError(_(
                "Please fill in the following credentials first:\n%(fields)s",
                fields="\n".join(f"• {f}" for f in missing)
            ))

        # Import here to avoid circular imports at module load
        from ..utils.api_client import (
            DokuClient,
            DokuAuthenticationError,
            DokuValidationError,
            DokuTimeoutError,
            DokuAPIError,
        )

        # Initialize client
        try:
            client = DokuClient(
                client_id=self.doku_client_id,
                secret_key=self.doku_secret_key,
                merchant_code=self.doku_merchant_code,
                environment=self.doku_environment or 'sandbox',
            )
        except ValueError as e:
            return self._doku_notify_test_result(
                success=False,
                title=_("Configuration Error"),
                message=str(e),
            )

        # Try to create a minimal test payment
        # We use a unique invoice number with TEST- prefix and timestamp
        from datetime import datetime
        test_invoice = f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            response = client.create_payment(
                invoice_number=test_invoice,
                amount=10000,  # Rp 10.000 minimum test
                payment_due_date=5,  # 5 minutes (won't actually be paid)
            )

            # Check if we got a valid response with payment URL
            payment_url = (
                response.get('response', {})
                .get('payment', {})
                .get('url')
            )

            if payment_url:
                env_label = "Sandbox" if self.doku_environment == 'sandbox' else "Production"
                api_url = self._get_doku_api_url()

                return self._doku_notify_test_result(
                    success=True,
                    title=_("Connection Successful! ✅"),
                    message=_(
                        "DOKU API connection works correctly!\n\n"
                        "• Environment: %(env)s\n"
                        "• API URL: %(url)s\n"
                        "• Test Invoice: %(invoice)s\n"
                        "• Credentials: VALID\n\n"
                        "Your provider is ready to accept payments. "
                        "Don't forget to set the State to 'Enabled' or 'Test Mode'.",
                        env=env_label,
                        url=api_url,
                        invoice=test_invoice,
                    ),
                )
            else:
                return self._doku_notify_test_result(
                    success=False,
                    title=_("Unexpected Response"),
                    message=_(
                        "DOKU returned a response but no payment URL was found.\n\n"
                        "Response: %(response)s",
                        response=str(response)[:500],
                    ),
                )

        except DokuAuthenticationError as e:
            return self._doku_notify_test_result(
                success=False,
                title=_("Authentication Failed ❌"),
                message=_(
                    "DOKU rejected your credentials.\n\n"
                    "Possible causes:\n"
                    "• Wrong Client ID, Secret Key, or Merchant Code\n"
                    "• Credentials don't match the selected environment\n"
                    "  (Sandbox vs Production)\n"
                    "• Account not activated by DOKU\n\n"
                    "Error: %(error)s",
                    error=str(e),
                ),
            )

        except DokuValidationError as e:
            # Validation error from DOKU usually means credentials work
            # but the test payload had an issue. This still indicates
            # connection works.
            return self._doku_notify_test_result(
                success=True,
                title=_("Connection OK (with notes) ⚠️"),
                message=_(
                    "DOKU API responded - credentials appear to be valid, "
                    "but there was a payload validation issue.\n\n"
                    "This usually means the connection works but DOKU "
                    "wants specific data format.\n\n"
                    "Details: %(error)s",
                    error=str(e),
                ),
            )

        except DokuTimeoutError as e:
            return self._doku_notify_test_result(
                success=False,
                title=_("Connection Timeout ⏱️"),
                message=_(
                    "Could not reach DOKU API within timeout period.\n\n"
                    "Possible causes:\n"
                    "• Network/firewall issue on your server\n"
                    "• DOKU API is slow/down\n"
                    "• Internet connectivity problem\n\n"
                    "Error: %(error)s",
                    error=str(e),
                ),
            )

        except DokuAPIError as e:
            return self._doku_notify_test_result(
                success=False,
                title=_("Connection Failed ❌"),
                message=_(
                    "DOKU API returned an error.\n\n"
                    "Status Code: %(status)s\n"
                    "Error: %(error)s",
                    status=e.status_code or 'N/A',
                    error=str(e),
                ),
            )

        except Exception as e:
            _logger.exception("DOKU: Unexpected error during connection test")
            return self._doku_notify_test_result(
                success=False,
                title=_("Unexpected Error ❌"),
                message=_(
                    "An unexpected error occurred during the test.\n\n"
                    "Check Odoo logs for details.\n\n"
                    "Error: %(error)s",
                    error=str(e),
                ),
            )

    def _doku_notify_test_result(self, success, title, message):
        """Helper to display test connection result as notification."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if success else 'danger',
                'title': title,
                'message': message,
                'sticky': True,  # Keep visible until user dismisses
            },
        }
