# -*- coding: utf-8 -*-
"""
DOKU Signature Generator (Non-SNAP)

Implements HMAC-SHA256 signature generation and verification for DOKU API
according to official DOKU documentation.

Reference:
- https://developers.doku.com/get-started-with-doku-api/signature-component/non-snap/signature-component-from-request-header
- https://jokul.doku.com/docs/docs/http-notification/http-notification-best-practice/
- https://dashboard.doku.com/docs/docs/technical-references/generate-signature/

Algorithm:
1. Generate Digest (POST only): base64(sha256(request_body))
2. Build component string with newline separators
3. Calculate HMAC-SHA256 base64 using secret key
4. Prepend "HMACSHA256=" to the signature
"""
import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)


class DokuSignature:
    """
    DOKU API Signature Generator and Validator.

    Usage:
        signer = DokuSignature(client_id, secret_key)

        # For outgoing POST request
        headers = signer.generate_headers(
            method='POST',
            target_path='/checkout/v1/payment',
            body={'order': {'amount': 20000, 'invoice_number': 'INV-001'}}
        )

        # For incoming webhook verification
        is_valid = signer.verify_webhook_signature(
            received_signature='HMACSHA256=...',
            target_path='/payment/doku/webhook',
            raw_body=request_body_string,
            request_id='...',
            timestamp='2021-01-27T03:24:23Z'
        )
    """

    SIGNATURE_PREFIX = 'HMACSHA256='

    def __init__(self, client_id, secret_key):
        """
        Initialize the signature generator.

        :param str client_id: DOKU Client ID (e.g., MCH-0001-1234567890)
        :param str secret_key: DOKU Secret Key (kept secret!)
        """
        if not client_id:
            raise ValueError("DokuSignature requires client_id")
        if not secret_key:
            raise ValueError("DokuSignature requires secret_key")

        self.client_id = client_id
        self.secret_key = secret_key

    # ==========================================
    # PUBLIC METHODS - OUTGOING REQUESTS
    # ==========================================
    def generate_headers(self, method, target_path, body=None, request_id=None,
                         timestamp=None):
        """
        Generate complete DOKU request headers including signature.

        :param str method: HTTP method ('GET', 'POST', etc.)
        :param str target_path: Endpoint path (e.g., '/checkout/v1/payment')
        :param dict|None body: Request body (for POST). None for GET.
        :param str|None request_id: Optional UUID. Auto-generated if not provided.
        :param str|None timestamp: Optional ISO8601 timestamp. Auto-generated if not provided.
        :return: dict - Complete headers dict ready to use in requests
        """
        request_id = request_id or self.generate_request_id()
        timestamp = timestamp or self.generate_timestamp()

        signature = self.generate_signature(
            method=method,
            target_path=target_path,
            body=body,
            request_id=request_id,
            timestamp=timestamp,
        )

        headers = {
            'Client-Id': self.client_id,
            'Request-Id': request_id,
            'Request-Timestamp': timestamp,
            'Signature': signature,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        return headers

    def generate_signature(self, method, target_path, body=None,
                           request_id=None, timestamp=None):
        """
        Generate signature for DOKU API request.

        :param str method: HTTP method
        :param str target_path: Endpoint path
        :param dict|None body: Request body for POST
        :param str request_id: Request ID (UUID)
        :param str timestamp: ISO8601 timestamp
        :return: str - Signature with prefix (e.g., 'HMACSHA256=...')
        """
        component = self._build_component_string(
            method=method,
            target_path=target_path,
            body=body,
            request_id=request_id,
            timestamp=timestamp,
        )

        signature_b64 = self._hmac_sha256_base64(component)
        return f"{self.SIGNATURE_PREFIX}{signature_b64}"

    # ==========================================
    # PUBLIC METHODS - INCOMING WEBHOOK VERIFICATION
    # ==========================================
    def verify_webhook_signature(self, received_signature, target_path, raw_body,
                                  request_id, timestamp):
        """
        Verify the signature of an incoming webhook from DOKU.

        IMPORTANT: This uses the RAW body string (not parsed dict) because
        DOKU calculates digest from the exact bytes they sent. Re-serializing
        a parsed dict may produce different bytes.

        :param str received_signature: Signature header from DOKU (e.g., 'HMACSHA256=...')
        :param str target_path: Path of OUR notification URL (e.g., '/payment/doku/webhook')
        :param str raw_body: Raw request body string (as received)
        :param str request_id: Request-Id header value from DOKU
        :param str timestamp: Request-Timestamp header value from DOKU
        :return: bool - True if signature is valid
        """
        if not received_signature:
            _logger.warning("DOKU webhook: empty signature received")
            return False

        if not request_id or not timestamp:
            _logger.warning(
                "DOKU webhook: missing required headers "
                "(request_id=%s, timestamp=%s)",
                bool(request_id), bool(timestamp)
            )
            return False

        # Calculate expected signature using RAW body
        digest = self.generate_digest_from_raw(raw_body)

        components = [
            f"Client-Id:{self.client_id}",
            f"Request-Id:{request_id}",
            f"Request-Timestamp:{timestamp}",
            f"Request-Target:{target_path}",
            f"Digest:{digest}",
        ]
        component_string = '\n'.join(components)

        expected_signature_b64 = self._hmac_sha256_base64(component_string)
        expected_full = f"{self.SIGNATURE_PREFIX}{expected_signature_b64}"

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_full, received_signature)

        if not is_valid:
            _logger.warning(
                "DOKU webhook signature mismatch.\n"
                "Expected: %s\n"
                "Received: %s\n"
                "Component string used:\n%s",
                expected_full,
                received_signature,
                component_string,
            )

        return is_valid

    def verify_signature(self, signature, method, target_path, body=None,
                         request_id=None, timestamp=None):
        """
        Verify a signature for non-webhook contexts (e.g., API responses).

        For webhook verification, prefer verify_webhook_signature() which
        uses raw body bytes.

        :param str signature: Received signature (with or without prefix)
        :return: bool - True if signature is valid
        """
        if not signature:
            return False

        expected = self.generate_signature(
            method=method,
            target_path=target_path,
            body=body,
            request_id=request_id,
            timestamp=timestamp,
        )

        return hmac.compare_digest(expected, signature)

    # ==========================================
    # HELPER METHODS
    # ==========================================
    @staticmethod
    def generate_request_id():
        """
        Generate a unique request ID (UUID4 format).
        Max 128 characters per DOKU spec.

        :return: str - UUID string
        """
        return str(uuid.uuid4())

    @staticmethod
    def generate_timestamp():
        """
        Generate current timestamp in ISO8601 UTC+0 format required by DOKU.

        Format: yyyy-MM-ddTHH:mm:ssZ
        Example: 2020-08-11T08:45:42Z

        :return: str - ISO8601 timestamp
        """
        now = datetime.now(timezone.utc)
        return now.strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def generate_digest(body):
        """
        Generate Digest from request body (dict or string).
        Digest = base64(sha256(json_minified_body))

        :param dict|str body: Request body
        :return: str - Base64 encoded SHA256 digest
        """
        if body is None:
            return ''

        if isinstance(body, dict):
            # Use minified JSON (no extra spaces) - critical for signature match
            body_str = json.dumps(body, separators=(',', ':'))
        elif isinstance(body, str):
            body_str = body
        else:
            raise TypeError(f"Body must be dict or str, got {type(body).__name__}")

        return DokuSignature.generate_digest_from_raw(body_str)

    @staticmethod
    def generate_digest_from_raw(raw_body_str):
        """
        Generate Digest from raw request body string.
        Use this for webhook verification where we have raw bytes.

        :param str raw_body_str: Raw request body as string
        :return: str - Base64 encoded SHA256 digest
        """
        if raw_body_str is None:
            raw_body_str = ''

        digest_bytes = hashlib.sha256(raw_body_str.encode('utf-8')).digest()
        return base64.b64encode(digest_bytes).decode('utf-8')

    # ==========================================
    # INTERNAL METHODS
    # ==========================================
    def _hmac_sha256_base64(self, message):
        """
        Calculate HMAC-SHA256 of message and return base64-encoded result.

        :param str message: Message to sign
        :return: str - Base64 encoded HMAC-SHA256 signature
        """
        signature_bytes = hmac.new(
            key=self.secret_key.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(signature_bytes).decode('utf-8')

    def _build_component_string(self, method, target_path, body, request_id, timestamp):
        """
        Build the signature component string per DOKU specification.

        For POST/PUT/PATCH: includes Digest
        For GET/DELETE: no Digest

        Format (POST):
            Client-Id:value\n
            Request-Id:value\n
            Request-Timestamp:value\n
            Request-Target:value\n
            Digest:value

        Format (GET):
            Client-Id:value\n
            Request-Id:value\n
            Request-Timestamp:value\n
            Request-Target:value

        IMPORTANT: No trailing \n at the end!

        :return: str - Component string ready for signing
        """
        method_upper = method.upper()
        components = [
            f"Client-Id:{self.client_id}",
            f"Request-Id:{request_id}",
            f"Request-Timestamp:{timestamp}",
            f"Request-Target:{target_path}",
        ]

        # Add Digest only for methods with body
        if method_upper in ('POST', 'PUT', 'PATCH') and body is not None:
            digest = self.generate_digest(body)
            components.append(f"Digest:{digest}")

        return '\n'.join(components)
