# -*- coding: utf-8 -*-
"""
DOKU API Client

Wrapper for DOKU Checkout API requests.

Reference:
- https://developers.doku.com/accept-payments/doku-checkout/integration-guide/backend-integration
- https://developers.doku.com/get-started-with-doku-api/signature-component/non-snap

Usage:
    client = DokuClient(
        client_id='MCH-0001-1234567890',
        secret_key='your-secret-key',
        environment='sandbox',  # or 'production'
    )

    # Create payment
    response = client.create_payment(
        invoice_number='INV-2026-0001',
        amount=20000,
        payment_due_date=60,
    )
    payment_url = response['response']['payment']['url']
"""
import json
import logging

import requests

from ..const import (
    API_TIMEOUT,
    DOKU_API_URLS,
    DOKU_ENDPOINTS,
)
from .signature import DokuSignature

_logger = logging.getLogger(__name__)


class DokuAPIError(Exception):
    """Base exception for DOKU API errors."""

    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class DokuAuthenticationError(DokuAPIError):
    """Raised when authentication/signature fails."""
    pass


class DokuValidationError(DokuAPIError):
    """Raised when request payload is invalid."""
    pass


class DokuTimeoutError(DokuAPIError):
    """Raised when API request times out."""
    pass


class DokuClient:
    """
    Client for DOKU Checkout API.

    Handles authentication, signature generation, request/response
    processing, and error handling for all DOKU API calls.
    """

    def __init__(self, client_id, secret_key, merchant_code=None,
                 environment='sandbox', timeout=API_TIMEOUT):
        """
        Initialize DOKU API client.

        :param str client_id: DOKU Client ID
        :param str secret_key: DOKU Secret Key (kept secret!)
        :param str merchant_code: DOKU Merchant Code / Mall ID (optional, for reference)
        :param str environment: 'sandbox' or 'production'
        :param int timeout: Request timeout in seconds
        """
        if environment not in DOKU_API_URLS:
            raise ValueError(
                f"Invalid environment '{environment}'. "
                f"Must be one of: {list(DOKU_API_URLS.keys())}"
            )

        self.client_id = client_id
        self.secret_key = secret_key
        self.merchant_code = merchant_code
        self.environment = environment
        self.timeout = timeout

        self.base_url = DOKU_API_URLS[environment]
        self.signer = DokuSignature(client_id, secret_key)

    # ==========================================
    # PUBLIC API METHODS
    # ==========================================
    def create_payment(self, invoice_number, amount, payment_due_date=60,
                       customer=None, line_items=None, payment_method_types=None,
                       callback_url=None, callback_url_cancel=None,
                       callback_url_result=None, auto_redirect=False,
                       additional_info=None, **kwargs):
        """
        Create a payment session and obtain payment.url for DOKU Checkout.

        :param str invoice_number: Unique merchant invoice number (max 64 chars,
                                    or 30 if Credit Card enabled)
        :param int amount: Amount in IDR without decimal (max 12 digits)
        :param int payment_due_date: Expiry in minutes (default 60)
        :param dict|None customer: Customer info (id, name, email, phone, etc.)
        :param list|None line_items: List of order items
        :param list|None payment_method_types: Specific payment methods to show.
                                                If None, all methods are shown.
        :param str|None callback_url: URL for "Back to Merchant" button
        :param str|None callback_url_cancel: URL for cancellation redirect
        :param str|None callback_url_result: URL for result page button
        :param bool auto_redirect: Auto-redirect after payment
        :param dict|None additional_info: Additional config (allow_tenor, etc.)
        :param dict kwargs: Additional order parameters
        :return: dict - DOKU API response with payment.url
        :raises DokuAPIError: If API request fails
        """
        # Build request body per DOKU specification
        order = {
            'amount': int(amount),
            'invoice_number': invoice_number,
        }

        if callback_url:
            order['callback_url'] = callback_url
        if callback_url_cancel:
            order['callback_url_cancel'] = callback_url_cancel
        if callback_url_result:
            order['callback_url_result'] = callback_url_result
        if auto_redirect is not None:
            order['auto_redirect'] = bool(auto_redirect)
        if line_items:
            order['line_items'] = line_items

        # Apply any additional order kwargs
        for key, value in kwargs.items():
            if value is not None:
                order[key] = value

        payment = {
            'payment_due_date': int(payment_due_date),
        }
        if payment_method_types:
            payment['payment_method_types'] = payment_method_types

        body = {
            'order': order,
            'payment': payment,
        }

        if customer:
            body['customer'] = customer
        if additional_info:
            body['additional_info'] = additional_info

        # Send request
        return self._post(
            endpoint=DOKU_ENDPOINTS['create_payment'],
            body=body,
        )

    def check_payment_status(self, invoice_number):
        """
        Check the status of a payment by invoice number.

        :param str invoice_number: The merchant invoice number to check
        :return: dict - DOKU API response with payment status
        :raises DokuAPIError: If API request fails
        """
        endpoint = DOKU_ENDPOINTS['check_status'].format(
            invoice_number=invoice_number
        )
        return self._get(endpoint=endpoint)

    # ==========================================
    # INTERNAL HTTP METHODS
    # ==========================================
    def _post(self, endpoint, body):
        """
        Perform a signed POST request to DOKU API.

        :param str endpoint: API endpoint path (e.g., '/checkout/v1/payment')
        :param dict body: Request body
        :return: dict - Parsed JSON response
        :raises DokuAPIError: If request fails or response is invalid
        """
        return self._request('POST', endpoint, body=body)

    def _get(self, endpoint):
        """
        Perform a signed GET request to DOKU API.

        :param str endpoint: API endpoint path
        :return: dict - Parsed JSON response
        :raises DokuAPIError: If request fails or response is invalid
        """
        return self._request('GET', endpoint, body=None)

    def _request(self, method, endpoint, body=None):
        """
        Perform a signed HTTP request to DOKU API with full error handling.

        :param str method: HTTP method ('GET' or 'POST')
        :param str endpoint: API endpoint path
        :param dict|None body: Request body (for POST)
        :return: dict - Parsed JSON response
        :raises DokuAPIError: On any failure
        """
        url = f"{self.base_url}{endpoint}"

        # Generate signed headers
        headers = self.signer.generate_headers(
            method=method,
            target_path=endpoint,
            body=body,
        )

        # Use minified JSON for body to match the digest calculation
        body_data = None
        if body is not None:
            body_data = json.dumps(body, separators=(',', ':'))

        # Log request (mask sensitive data)
        self._log_request(method, url, headers, body)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=body_data,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as e:
            _logger.error("DOKU API timeout: %s", str(e))
            raise DokuTimeoutError(
                f"DOKU API request timed out after {self.timeout}s",
            ) from e
        except requests.exceptions.ConnectionError as e:
            _logger.error("DOKU API connection error: %s", str(e))
            raise DokuAPIError(
                f"Failed to connect to DOKU API: {str(e)}",
            ) from e
        except requests.exceptions.RequestException as e:
            _logger.error("DOKU API request error: %s", str(e))
            raise DokuAPIError(
                f"DOKU API request failed: {str(e)}",
            ) from e

        # Log response
        self._log_response(response)

        # Parse and validate response
        return self._handle_response(response)

    def _handle_response(self, response):
        """
        Handle and validate DOKU API response.

        :param requests.Response response: HTTP response object
        :return: dict - Parsed JSON response body
        :raises DokuAPIError: On HTTP error or invalid response
        """
        # Try to parse JSON response
        try:
            response_data = response.json()
        except ValueError:
            response_data = {'raw': response.text}

        # Handle HTTP errors
        if response.status_code == 200:
            return response_data

        # Build a comprehensive error message that surfaces ALL info DOKU returned.
        # DOKU error responses can use multiple structures:
        #   {"error_messages": ["..."]}
        #   {"message": "..."}
        #   {"response": {"status": "...", "message": "..."}}
        #   {"errors": [{"code": "...", "description": "..."}]}
        error_detail = self._extract_error_detail(response_data)

        # Always log the FULL response body when we hit an error so we can debug.
        _logger.error(
            "DOKU API error response (status %s):\nFULL BODY: %s",
            response.status_code,
            json.dumps(response_data, indent=2) if isinstance(response_data, dict) else str(response_data),
        )

        if response.status_code == 400:
            raise DokuValidationError(
                f"DOKU API validation error (400): {error_detail}",
                status_code=response.status_code,
                response_body=response_data,
            )

        if response.status_code in (401, 403):
            raise DokuAuthenticationError(
                f"DOKU API authentication failed (status {response.status_code}). "
                f"Verify Client-Id, Secret Key, and signature. Detail: {error_detail}",
                status_code=response.status_code,
                response_body=response_data,
            )

        if response.status_code == 404:
            raise DokuAPIError(
                f"DOKU API endpoint not found: {response.url}. Detail: {error_detail}",
                status_code=response.status_code,
                response_body=response_data,
            )

        if 500 <= response.status_code < 600:
            raise DokuAPIError(
                f"DOKU API server error (status {response.status_code}). "
                f"Please try again later. Detail: {error_detail}",
                status_code=response.status_code,
                response_body=response_data,
            )

        # Other errors
        raise DokuAPIError(
            f"DOKU API request failed (status {response.status_code}): {error_detail}",
            status_code=response.status_code,
            response_body=response_data,
        )

    @staticmethod
    def _extract_error_detail(response_data):
        """
        Extract a human-readable error message from various DOKU response shapes.

        DOKU error response structures vary by endpoint and error type.
        This tries every known shape and falls back to the raw body.
        """
        if not isinstance(response_data, dict):
            return str(response_data)[:500]

        parts = []

        # Pattern 1: {"error_messages": ["msg1", "msg2"]}
        error_messages = response_data.get('error_messages')
        if error_messages:
            if isinstance(error_messages, list):
                parts.extend(str(m) for m in error_messages)
            else:
                parts.append(str(error_messages))

        # Pattern 2: {"message": "..."}
        message = response_data.get('message')
        if message:
            parts.append(str(message))

        # Pattern 3: {"response": {"status": "...", "message": "..."}}
        nested_response = response_data.get('response')
        if isinstance(nested_response, dict):
            nested_message = nested_response.get('message')
            nested_status = nested_response.get('status')
            if nested_message:
                parts.append(f"[{nested_status}] {nested_message}" if nested_status else nested_message)

        # Pattern 4: {"errors": [{"code": "...", "description": "..."}]}
        errors = response_data.get('errors')
        if isinstance(errors, list):
            for err in errors:
                if isinstance(err, dict):
                    code = err.get('code', '')
                    desc = err.get('description') or err.get('message') or str(err)
                    parts.append(f"[{code}] {desc}" if code else desc)
                else:
                    parts.append(str(err))

        # Pattern 5: {"error": "..."} (single error string)
        single_error = response_data.get('error')
        if single_error and not parts:
            if isinstance(single_error, dict):
                parts.append(str(single_error.get('message', single_error)))
            else:
                parts.append(str(single_error))

        # Fallback: return the entire body (truncated) so user sees something useful
        if not parts:
            return f"(no recognized error field) Raw response: {json.dumps(response_data)[:500]}"

        return " | ".join(parts)

    # ==========================================
    # LOGGING
    # ==========================================
    def _log_request(self, method, url, headers, body):
        """Log API request, masking sensitive headers."""
        masked_headers = self._mask_sensitive_headers(headers)
        _logger.info(
            "DOKU API Request: %s %s\nHeaders: %s\nBody: %s",
            method, url,
            json.dumps(masked_headers, indent=2),
            json.dumps(body, indent=2) if body else 'None',
        )

    def _log_response(self, response):
        """Log API response, including FULL body for debugging."""
        # Use INFO for success (200), ERROR for failures so they're easier to spot in logs
        log_method = _logger.info if response.status_code == 200 else _logger.error
        log_method(
            "DOKU API Response: status=%d\nFULL BODY:\n%s",
            response.status_code,
            response.text,  # No truncation — DOKU responses are not huge
        )

    @staticmethod
    def _mask_sensitive_headers(headers):
        """Mask sensitive header values for logging."""
        masked = dict(headers)
        if 'Signature' in masked:
            sig = masked['Signature']
            masked['Signature'] = sig[:20] + '...' + sig[-8:] if len(sig) > 30 else '***'
        return masked
