# -*- coding: utf-8 -*-
"""
Post-init and uninstall hooks for DOKU Payment Gateway module.

Uses Odoo's official `setup_provider` and `reset_payment_provider` helpers
from the `payment` module. This is the standard pattern (verified against
Odoo Enterprise's `payment_xendit` module).

`setup_provider(env, 'doku')` will automatically:
- Read `_get_default_payment_method_codes()` from the DOKU provider model
- Find matching `payment.method` records by code
- Link them to the DOKU provider via `payment_method_ids`
- Set the provider's initial state appropriately
"""
import logging

from odoo.addons.payment import setup_provider, reset_payment_provider

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Hook executed after module installation.

    Calls Odoo's setup_provider() helper which auto-links payment methods
    based on _get_default_payment_method_codes() in the provider model.
    """
    _logger.info("DOKU Payment Gateway: Running post_init_hook (setup_provider)...")
    setup_provider(env, 'doku')
    _logger.info(
        "DOKU Payment Gateway: Module installed and provider set up. "
        "Configure credentials at Accounting > Configuration > Payment Providers."
    )


def uninstall_hook(env):
    """
    Hook executed when module is uninstalled.

    Calls Odoo's reset_payment_provider() helper which:
    - Resets the provider state to 'disabled'
    - Removes payment method links
    - Cleans up provider-specific configuration
    """
    _logger.info("DOKU Payment Gateway: Running uninstall_hook (reset_payment_provider)...")
    reset_payment_provider(env, 'doku')
    _logger.info("DOKU Payment Gateway: Provider reset and module uninstalled.")
