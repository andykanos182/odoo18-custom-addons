import json
import logging

from odoo import fields, http
from odoo.http import request, Response

from .kitchen_html import KITCHEN_DISPLAY_HTML

_logger = logging.getLogger(__name__)

# Bump this whenever you change _SERVICE_WORKER_JS or kitchen_html.py so the
# browser refetches the SW + HTML shell instead of using a cached version.
# Cloudflare will also cache-bust on this via the ?v=SW_VERSION query string.
SW_VERSION = '4'


class KitchenController(http.Controller):

    # ==================================================================
    # 1. Main Kitchen Display page (HTML shell, served directly)
    #    Accepts BOTH /kitchen and /kitchen/ to avoid SW scope mismatch.
    #    Append ?debug=1 to the URL to reveal the troubleshooting panel.
    # ==================================================================
    @http.route(
        ['/kitchen', '/kitchen/'],
        type='http', auth='user', website=False, csrf=False,
    )
    def kitchen_page(self, **kwargs):
        """Render the Kitchen Display PWA shell."""
        public_key = request.env['kitchen.vapid'].sudo().get_public_key() or ''
        user_name = request.env.user.name or ''
        html = KITCHEN_DISPLAY_HTML.format(
            vapid_public_key=public_key,
            user_name=_escape_html(user_name),
            sw_version=SW_VERSION,
        )
        headers = [
            ('Content-Type', 'text/html; charset=utf-8'),
            # Do NOT let Cloudflare cache the HTML shell, otherwise a fresh
            # SW_VERSION in the Python code won't reach the browser.
            ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'),
        ]
        return Response(html, headers=headers)

    # ==================================================================
    # 2. Service worker
    #
    # Two critical things here:
    #   (a) Service-Worker-Allowed: /kitchen  lets a SW served from
    #       /kitchen/sw.js control the broader scope /kitchen (without
    #       trailing slash), which is the URL users actually open.
    #   (b) Cache-Control must try to prevent Cloudflare from caching
    #       the SW script. Cloudflare may still cache by default, so
    #       we also append ?v=SW_VERSION to cache-bust from the client.
    # ==================================================================
    @http.route('/kitchen/sw.js', type='http', auth='public', csrf=False)
    def kitchen_service_worker(self, **kwargs):
        headers = [
            ('Content-Type', 'application/javascript; charset=utf-8'),
            ('Service-Worker-Allowed', '/kitchen'),
            ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'),
            ('Pragma', 'no-cache'),
            ('Expires', '0'),
        ]
        sw_source = '// SW_VERSION=' + SW_VERSION + '\n' + _SERVICE_WORKER_JS
        return Response(sw_source, headers=headers)

    # ==================================================================
    # 3. PWA manifest
    # ==================================================================
    @http.route('/kitchen/manifest.json', type='http', auth='public', csrf=False)
    def kitchen_manifest(self, **kwargs):
        manifest = {
            "name": "Gopokaja Kitchen",
            "short_name": "Kitchen",
            "description": "Kitchen Display for Gopokaja POS orders",
            "start_url": "/kitchen",
            "scope": "/kitchen",
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#0f172a",
            "theme_color": "#0f172a",
            "icons": [
                {
                    "src": "/andykanoz_kitchen_notify/static/description/icon.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any"
                },
                {
                    "src": "/andykanoz_kitchen_notify/static/description/icon.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "maskable"
                },
                {
                    "src": "/andykanoz_kitchen_notify/static/description/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any"
                },
                {
                    "src": "/andykanoz_kitchen_notify/static/description/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable"
                }
            ]
        }
        return Response(
            json.dumps(manifest),
            headers=[
                ('Content-Type', 'application/manifest+json'),
                ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'),
            ],
        )

    # ==================================================================
    # 4. Expose VAPID public key
    # ==================================================================
    @http.route('/kitchen/vapid-public-key', type='http', auth='user', csrf=False)
    def vapid_public_key(self, **kwargs):
        key = request.env['kitchen.vapid'].sudo().get_public_key() or ''
        return Response(
            json.dumps({'publicKey': key}),
            headers=[('Content-Type', 'application/json')],
        )

    # ==================================================================
    # 5. Save a push subscription from the browser
    # ==================================================================
    @http.route('/kitchen/subscribe', type='json', auth='user', csrf=False, methods=['POST'])
    def kitchen_subscribe(self, **kwargs):
        endpoint = kwargs.get('endpoint')
        keys = kwargs.get('keys') or {}
        device_name = kwargs.get('deviceName') or 'Kitchen Device'

        p256dh = keys.get('p256dh') if isinstance(keys, dict) else None
        auth_secret = keys.get('auth') if isinstance(keys, dict) else None

        _logger.info(
            "kitchen_notify: subscribe called by user=%s device=%r endpoint_present=%s keys_present=%s",
            request.env.user.login, device_name, bool(endpoint),
            bool(p256dh and auth_secret),
        )

        if not (endpoint and p256dh and auth_secret):
            return {'success': False, 'error': 'Missing subscription fields'}

        Sub = request.env['kitchen.push.subscription'].sudo()
        existing = Sub.search([('endpoint', '=', endpoint)], limit=1)
        if existing:
            existing.write({
                'p256dh': p256dh,
                'auth': auth_secret,
                'is_active': True,
                'fail_count': 0,
                'user_id': request.env.user.id,
                'device_name': device_name,
            })
            sub_id = existing.id
            _logger.info("kitchen_notify: updated existing subscription id=%s", sub_id)
        else:
            sub = Sub.create({
                'endpoint': endpoint,
                'p256dh': p256dh,
                'auth': auth_secret,
                'device_name': device_name,
                'user_id': request.env.user.id,
            })
            sub_id = sub.id
            _logger.info("kitchen_notify: created new subscription id=%s", sub_id)

        return {'success': True, 'id': sub_id}

    # ==================================================================
    # 6. Fetch active orders (polling endpoint)
    # ==================================================================
    @http.route('/kitchen/orders', type='http', auth='user', csrf=False)
    def kitchen_orders(self, **kwargs):
        """Return active orders (waiting + cooking) + recently done (10 min)."""
        KitchenOrder = request.env['kitchen.order'].sudo()
        waiting = KitchenOrder.search([('status', '=', 'waiting')])
        cooking = KitchenOrder.search([('status', '=', 'cooking')])
        done = KitchenOrder.search([
            ('status', '=', 'done'),
            ('done_time', '>=', fields.Datetime.subtract(fields.Datetime.now(), minutes=10)),
        ])

        result = {
            'waiting': [k._to_kitchen_json() for k in waiting],
            'cooking': [k._to_kitchen_json() for k in cooking],
            'done': [k._to_kitchen_json() for k in done],
            'server_time': fields.Datetime.to_string(fields.Datetime.now()),
        }
        return Response(
            json.dumps(result),
            headers=[
                ('Content-Type', 'application/json'),
                ('Cache-Control', 'no-store'),
            ],
        )

    # ==================================================================
    # 7. Update order status — LINEAR FLOW ONLY
    # Allowed transitions:
    #   waiting -> cooking
    #   cooking -> done
    # ==================================================================
    @http.route('/kitchen/update-status', type='json', auth='user', csrf=False, methods=['POST'])
    def kitchen_update_status(self, **kwargs):
        order_id = kwargs.get('id')
        new_status = kwargs.get('status')

        if not order_id or new_status not in ('cooking', 'done'):
            return {'success': False, 'error': 'Invalid status (only cooking/done allowed)'}

        ko = request.env['kitchen.order'].sudo().browse(int(order_id))
        if not ko.exists():
            return {'success': False, 'error': 'Kitchen order not found'}

        valid_transitions = {
            ('waiting', 'cooking'): 'action_start_cooking',
            ('cooking', 'done'): 'action_mark_done',
        }
        action = valid_transitions.get((ko.status, new_status))
        if not action:
            return {
                'success': False,
                'error': 'Transition %s -> %s not allowed' % (ko.status, new_status),
            }

        try:
            getattr(ko, action)()
            return {'success': True, 'id': ko.id, 'status': ko.status}
        except Exception as e:
            _logger.exception("kitchen_notify: status update failed: %s", e)
            return {'success': False, 'error': str(e)}

    # ==================================================================
    # 8. Admin helper: send a test push to all active subscriptions.
    # Open this URL in a browser while logged in as admin to trigger
    # a test notification without having to create a POS order.
    # ==================================================================
    @http.route('/kitchen/test-push', type='http', auth='user', csrf=False)
    def kitchen_test_push(self, **kwargs):
        if not request.env.user.has_group('base.group_system'):
            return Response('Forbidden', status=403)
        payload = {
            'title': '🧪 Test Notification',
            'body': 'Kalau Anda lihat ini, push notification bekerja!',
            'url': '/kitchen',
            'pos_order_id': 0,
        }
        sent = request.env['kitchen.vapid'].sudo().send_push_to_all(payload)
        return Response(
            json.dumps({'sent': sent}),
            headers=[('Content-Type', 'application/json')],
        )


def _escape_html(s):
    return (
        str(s or '')
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )


# ======================================================================
# Service Worker JavaScript
# ======================================================================
_SERVICE_WORKER_JS = r"""
// Andykanoz Kitchen Notify Service Worker
self.addEventListener('install', (event) => {
  console.log('[kitchen-sw] install');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[kitchen-sw] activate');
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  console.log('[kitchen-sw] push event received');
  let data = {
    title: 'Order baru',
    body: 'Ada order dapur masuk',
    url: '/kitchen',
  };
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }
  const options = {
    body: data.body || '',
    icon: '/andykanoz_kitchen_notify/static/description/icon.png',
    badge: '/andykanoz_kitchen_notify/static/description/icon.png',
    vibrate: [200, 100, 200, 100, 200],
    tag: 'kitchen-order-' + (data.pos_order_id || Date.now()),
    renotify: true,
    requireInteraction: true,
    data: {
      url: data.url || '/kitchen',
      pos_order_id: data.pos_order_id,
    },
  };
  event.waitUntil(
    self.registration.showNotification(data.title || 'Order baru', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || '/kitchen';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes('/kitchen') && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
"""
