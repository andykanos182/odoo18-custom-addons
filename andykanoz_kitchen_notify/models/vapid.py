"""VAPID key management and push notification sender."""
import base64
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    from pywebpush import webpush, WebPushException
    _HAS_PYWEBPUSH = True
except ImportError:
    _HAS_PYWEBPUSH = False
    _logger.warning(
        "andykanoz_kitchen_notify: pywebpush not installed. "
        "Push notifications disabled. Install with: pip install pywebpush"
    )

try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


PARAM_PUBLIC = 'kitchen.vapid_public_key'
PARAM_PRIVATE = 'kitchen.vapid_private_key'
PARAM_EMAIL = 'kitchen.vapid_email'
DEFAULT_EMAIL = 'mailto:admin@gopokaja.com'


class KitchenVapid(models.AbstractModel):
    """Helpers to generate VAPID keys and send push notifications."""
    _name = 'kitchen.vapid'
    _description = 'Kitchen VAPID / Web Push Helper'

    @api.model
    def ensure_vapid_keys(self):
        """Create a VAPID keypair if none exists yet."""
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(PARAM_PUBLIC) and ICP.get_param(PARAM_PRIVATE):
            return

        if not _HAS_CRYPTO:
            _logger.error(
                "kitchen_notify: cannot generate VAPID keys — cryptography library missing"
            )
            return

        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()

        private_numbers = private_key.private_numbers()
        private_bytes = private_numbers.private_value.to_bytes(32, 'big')
        private_b64 = base64.urlsafe_b64encode(private_bytes).rstrip(b'=').decode('ascii')

        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        public_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode('ascii')

        ICP.set_param(PARAM_PUBLIC, public_b64)
        ICP.set_param(PARAM_PRIVATE, private_b64)
        if not ICP.get_param(PARAM_EMAIL):
            ICP.set_param(PARAM_EMAIL, DEFAULT_EMAIL)

        _logger.info("kitchen_notify: generated new VAPID keypair")

    @api.model
    def get_public_key(self):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM_PUBLIC, '')

    @api.model
    def send_push_to_all(self, payload):
        """Send a push notification to every active subscription.

        Returns the number of successfully delivered pushes. Detailed errors
        are logged at INFO/WARNING level — check Odoo log for 'kitchen_notify'.
        """
        if not _HAS_PYWEBPUSH:
            _logger.warning("kitchen_notify: push skipped (pywebpush not installed)")
            return 0

        ICP = self.env['ir.config_parameter'].sudo()
        private_key = ICP.get_param(PARAM_PRIVATE)
        email = ICP.get_param(PARAM_EMAIL) or DEFAULT_EMAIL
        if not private_key:
            _logger.warning("kitchen_notify: no VAPID private key configured")
            return 0

        subs = self.env['kitchen.push.subscription'].sudo().search([
            ('is_active', '=', True),
        ])
        _logger.info("kitchen_notify: sending push to %d active subscriptions", len(subs))
        if not subs:
            return 0

        vapid_private = _b64_add_padding(private_key)
        data = json.dumps(payload)
        claims = {'sub': email}
        sent = 0

        for sub in subs:
            subscription_info = {
                'endpoint': sub.endpoint,
                'keys': {
                    'p256dh': sub.p256dh,
                    'auth': sub.auth,
                },
            }
            try:
                webpush(
                    subscription_info=subscription_info,
                    data=data,
                    vapid_private_key=vapid_private,
                    vapid_claims=dict(claims),
                    ttl=60,
                )
                sub.write({
                    'last_notif_at': fields.Datetime.now(),
                    'fail_count': 0,
                })
                sent += 1
                _logger.info(
                    "kitchen_notify: push sent OK to %s (%s)",
                    sub.device_name or '?', sub.endpoint[:60],
                )
            except WebPushException as e:
                status = getattr(e.response, 'status_code', None) if e.response else None
                if status in (404, 410):
                    sub.write({'is_active': False})
                    _logger.info(
                        "kitchen_notify: deactivated dead subscription %s (HTTP %s)",
                        sub.endpoint[:60], status,
                    )
                else:
                    sub.fail_count += 1
                    _logger.warning(
                        "kitchen_notify: push failed for %s (HTTP %s): %s",
                        sub.endpoint[:60], status, e,
                    )
                    if sub.fail_count >= 5:
                        sub.is_active = False
            except Exception as e:
                _logger.exception("kitchen_notify: unexpected push error: %s", e)

        _logger.info("kitchen_notify: push delivery complete (%d/%d sent)", sent, len(subs))
        return sent


def _b64_add_padding(s):
    return s + '=' * (-len(s) % 4)
