# -*- coding: utf-8 -*-
"""
Post-init and uninstall hooks for DOKU Payment Gateway module.
"""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Hook executed after module installation.
    
    Tasks:
    - Log successful installation
    - Optionally setup default configuration
    """
    _logger.info("DOKU Payment Gateway: Module installed successfully.")
    _logger.info("DOKU Payment Gateway: Configure provider at "
                 "Accounting > Configuration > Payment Providers")


def uninstall_hook(env):
    """
    Hook executed when module is uninstalled.
    
    Tasks:
    - Disable DOKU payment provider (don't delete to preserve transaction history)
    - Log uninstallation
    """
    providers = env['payment.provider'].search([('code', '=', 'doku')])
    if providers:
        providers.write({'state': 'disabled'})
        _logger.info(
            "DOKU Payment Gateway: Disabled %d provider(s) on uninstall.",
            len(providers)
        )
    _logger.info("DOKU Payment Gateway: Module uninstalled.")
