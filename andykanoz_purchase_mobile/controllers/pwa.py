# -*- coding: utf-8 -*-
"""Purchase Mobile — PWA endpoints.

Serves the Web App Manifest and Service Worker dynamically (instead of
static files) so we can:
  - Inject a SW_VERSION token to bust the Cloudflare Tunnel cache when
    we deploy a new version
  - Read PWA metadata from ir.config_parameter (e.g. company name) if
    we want to override defaults later
  - Avoid registering a static_file route for what's effectively config
"""

import json

from odoo import http
from odoo.http import request


# Bump this string whenever the service worker logic changes. The SW
# itself caches by SW_VERSION, so old caches are pruned on activation.
# Pattern matches `andykanoz_kitchen_notify`'s versioning approach.
SW_VERSION = "v1"

# Base URL prefix \u2014 everything PWA-related lives under our module path
# so the SW scope matches and the install banner triggers on the app
# page itself, not on unrelated frontend pages.
APP_PATH = "/andykanoz_purchase_mobile/app"
SCOPE = "/andykanoz_purchase_mobile/"


class PurchaseMobilePwa(http.Controller):
    """PWA manifest + service worker endpoints."""

    @http.route(
        '/andykanoz_purchase_mobile/icon.svg',
        type='http',
        auth='public',
        csrf=False,
    )
    def icon(self, size="192", **kwargs):
        """Generate a square SVG app icon.

        Chrome accepts SVG icons in PWA manifests (since Chrome 79+).
        Generating dynamically lets us avoid bundling binary PNGs in
        the addon and lets Andyka swap the design later by editing
        Python instead of running a PNG export pipeline.

        The mask-safe area is the inner ~80% of the canvas — we keep
        the "P" centered well inside that to survive iOS / Android
        circular masking.
        """
        try:
            s = max(48, min(1024, int(size)))
        except (TypeError, ValueError):
            s = 192
        # Font size at ~55% of the canvas so the glyph fits inside the
        # mask-safe inner circle that some launchers apply.
        font_px = int(s * 0.55)
        # Slight optical lift so the P sits centered visually.
        baseline_y = int(s * 0.7)
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 ' + str(s) + ' ' + str(s) + '" '
            'width="' + str(s) + '" height="' + str(s) + '">'
            '<rect width="' + str(s) + '" height="' + str(s) + '" fill="#1a2332"/>'
            '<text x="50%" y="' + str(baseline_y) + '" '
            'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" '
            'font-size="' + str(font_px) + '" '
            'font-weight="600" '
            'fill="#ffffff" '
            'text-anchor="middle">P</text>'
            '</svg>'
        )
        return request.make_response(
            svg,
            headers=[
                ('Content-Type', 'image/svg+xml'),
                ('Cache-Control', 'public, max-age=86400'),
            ],
        )

    @http.route(
        '/andykanoz_purchase_mobile/manifest.json',
        type='http',
        auth='public',
        csrf=False,
    )
    def manifest(self, **kwargs):
        """Web App Manifest.

        Public auth so the manifest is fetchable even before login \u2014
        the browser inspects it to decide whether to show the install
        prompt.
        """
        manifest_data = {
            "name": "Gopokaja Purchase Mobile",
            "short_name": "Purchase",
            "description": "Mobile-first purchase order entry for Gopokaja",
            "start_url": APP_PATH,
            "scope": SCOPE,
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#f5f5f7",
            "theme_color": "#1a2332",
            "lang": "id-ID",
            "icons": [
                {
                    "src": "/andykanoz_purchase_mobile/icon.svg?size=192",
                    "sizes": "192x192",
                    "type": "image/svg+xml",
                    "purpose": "any maskable"
                },
                {
                    "src": "/andykanoz_purchase_mobile/icon.svg?size=512",
                    "sizes": "512x512",
                    "type": "image/svg+xml",
                    "purpose": "any maskable"
                }
            ]
        }
        body = json.dumps(manifest_data)
        return request.make_response(
            body,
            headers=[
                ('Content-Type', 'application/manifest+json'),
                # Allow the browser to cache the manifest for an hour;
                # short enough that updates propagate quickly, long
                # enough that we don't hammer the server.
                ('Cache-Control', 'public, max-age=3600'),
            ],
        )

    @http.route(
        '/andykanoz_purchase_mobile/service-worker.js',
        type='http',
        auth='public',
        csrf=False,
    )
    def service_worker(self, **kwargs):
        """Service worker JS, served dynamically so we can inject SW_VERSION.

        The SW scope must be the directory containing the start_url so
        that navigation requests inside /andykanoz_purchase_mobile/ are
        intercepted. We set Service-Worker-Allowed header explicitly to
        reinforce the scope contract.

        Strategy:
          - App shell HTML / asset bundle JS+CSS / icons \u2192 cache-first,
            with network refresh in the background (stale-while-revalidate
            would be nicer but keeps things simple here).
          - JSON-RPC API calls (/api/*) \u2192 network-only. We do not have
            an offline plan for V1; if the network is down, the app
            shows fetch errors via the existing rpc_service error path.
          - Everything else \u2192 passthrough (no SW intervention).
        """
        # Note: the SW source is plain JS, not an OWL/Odoo module \u2014
        # service workers run in a separate worker context and have no
        # access to the page's odoo.loader.
        sw_source = (
            "// Purchase Mobile Service Worker\n"
            "// Generated dynamically by controllers/pwa.py \u2014 DO NOT EDIT\n"
            "// the response by hand; bump SW_VERSION in the controller.\n"
            "\n"
            "const SW_VERSION = '" + SW_VERSION + "';\n"
            "const CACHE_NAME = 'andykanoz_purchase_mobile-' + SW_VERSION;\n"
            "const APP_PATH = '" + APP_PATH + "';\n"
            "\n"
            "// Files we want available offline (the bare minimum to\n"
            "// boot the OWL app shell). The asset bundle URL is\n"
            "// hashed and changes on every regen; we don't precache\n"
            "// it \u2014 the install hook just primes the app shell HTML.\n"
            "const PRECACHE_URLS = [APP_PATH];\n"
            "\n"
            "self.addEventListener('install', (event) => {\n"
            "    event.waitUntil(\n"
            "        caches.open(CACHE_NAME).then((cache) =>\n"
            "            cache.addAll(PRECACHE_URLS).catch(() => {})\n"
            "        ).then(() => self.skipWaiting())\n"
            "    );\n"
            "});\n"
            "\n"
            "self.addEventListener('activate', (event) => {\n"
            "    // Claim clients immediately so the new SW controls\n"
            "    // open tabs without a reload, and prune old caches.\n"
            "    event.waitUntil(\n"
            "        caches.keys().then((keys) =>\n"
            "            Promise.all(\n"
            "                keys.filter((k) => k.startsWith('andykanoz_purchase_mobile-') && k !== CACHE_NAME)\n"
            "                    .map((k) => caches.delete(k))\n"
            "            )\n"
            "        ).then(() => self.clients.claim())\n"
            "    );\n"
            "});\n"
            "\n"
            "self.addEventListener('fetch', (event) => {\n"
            "    const req = event.request;\n"
            "    const url = new URL(req.url);\n"
            "\n"
            "    // Only handle GET; everything else (POST JSON-RPC,\n"
            "    // etc.) goes straight to network.\n"
            "    if (req.method !== 'GET') return;\n"
            "\n"
            "    // Network-only for /api/* calls \u2014 we don't have an\n"
            "    // offline strategy and stale data would be worse than\n"
            "    // a clean error.\n"
            "    if (url.pathname.includes('/andykanoz_purchase_mobile/api/')) {\n"
            "        return;\n"
            "    }\n"
            "\n"
            "    // For our app-shell URL, do network-first with cache\n"
            "    // fallback so users get fresh app shells when online\n"
            "    // but a usable shell when offline.\n"
            "    if (url.pathname === APP_PATH) {\n"
            "        event.respondWith(\n"
            "            fetch(req).then((res) => {\n"
            "                const copy = res.clone();\n"
            "                caches.open(CACHE_NAME).then((c) => c.put(req, copy)).catch(() => {});\n"
            "                return res;\n"
            "            }).catch(() => caches.match(req).then((m) => m || new Response('Offline', {status: 503})))\n"
            "        );\n"
            "        return;\n"
            "    }\n"
            "\n"
            "    // For other static assets within our scope, cache-first.\n"
            "    if (url.pathname.startsWith('/andykanoz_purchase_mobile/static/')) {\n"
            "        event.respondWith(\n"
            "            caches.match(req).then((cached) => cached || fetch(req).then((res) => {\n"
            "                const copy = res.clone();\n"
            "                caches.open(CACHE_NAME).then((c) => c.put(req, copy)).catch(() => {});\n"
            "                return res;\n"
            "            }))\n"
            "        );\n"
            "    }\n"
            "});\n"
        )
        return request.make_response(
            sw_source,
            headers=[
                ('Content-Type', 'application/javascript'),
                # Critical: tell the browser this SW can control the
                # entire module path, even though it's served from the
                # root. The Service-Worker-Allowed header relaxes the
                # default scope-equals-SW-path-directory rule.
                ('Service-Worker-Allowed', SCOPE),
                # Never cache the SW itself \u2014 it's the cache-busting
                # mechanism, so stale SWs would defeat the whole point.
                ('Cache-Control', 'no-cache, no-store, must-revalidate'),
            ],
        )
