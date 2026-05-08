# -*- coding: utf-8 -*-
"""Purchase Mobile — HTTP controllers.

Phase 1: minimal controller that renders the app shell for authenticated
users. Later phases will add JSON-RPC endpoints under
`/andykanoz_purchase_mobile/api/*` for vendor/product/PO operations,
plus PWA manifest and service worker routes.
"""

from odoo import http
from odoo.http import request


class PurchaseMobileController(http.Controller):
    """Standalone page controller for the Purchase Mobile PWA."""

    @http.route(
        '/andykanoz_purchase_mobile/app',
        type='http',
        auth='user',
        csrf=False,
    )
    def app_shell(self, **kwargs):
        """Render the app shell HTML.

        Auth is enforced by `auth='user'` — unauthenticated visitors get
        redirected to /web/login and back. Phase 1 just confirms the route
        is reachable and the template renders with current user context.
        """
        user = request.env.user
        values = {
            'user_name': user.name,
            'user_login': user.login,
            'module_version': '18.0.1.0.0',
            'phase': 'Phase 8b+ — UoM Dropdown Fix',
        }
        return request.render('andykanoz_purchase_mobile.app_shell', values)
