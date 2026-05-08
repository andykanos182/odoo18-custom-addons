# -*- coding: utf-8 -*-
"""
Migration script to version 18.0.1.0.1.

Triggered automatically when the module is upgraded from any older version.
This script re-runs setup_provider() for the DOKU provider to:

1. Auto-link payment methods based on _get_default_payment_method_codes()
   (Previously, methods were linked manually via XML which got reset on
   every upgrade due to noupdate="0".)

2. Recover from the state where user upgraded but payment methods disappeared.

Reference: Pattern from payment_xendit official module.
"""
import logging

from odoo.addons.payment import setup_provider

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Re-run setup_provider for DOKU on upgrade.

    :param cr: Database cursor
    :param version: Previous version of the module (string or False)
    """
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info(
        "DOKU Migration to 18.0.1.0.1: Running setup_provider to "
        "re-link payment methods and reset provider config..."
    )

    try:
        setup_provider(env, 'doku')
        _logger.info(
            "DOKU Migration to 18.0.1.0.1: setup_provider completed successfully. "
            "Payment methods should now be properly linked."
        )
    except Exception as e:
        _logger.exception(
            "DOKU Migration to 18.0.1.0.1: setup_provider failed: %s. "
            "You may need to manually re-link payment methods in the UI.",
            str(e)
        )
        # Don't re-raise — migration should not block upgrade
