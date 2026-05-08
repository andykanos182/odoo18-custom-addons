{
    'name': 'Andykanoz Kitchen Notify (PWA + Push)',
    'version': '18.0.1.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Kitchen Display PWA with Web Push Notifications for POS orders',
    'description': """
Andykanoz Kitchen Notify
========================
Real-time kitchen display and push notifications for POS orders.

FEATURES
--------
* Standalone Kitchen Display page at /kitchen (mobile-first PWA)
* Web Push Notifications (W3C standard) — works even when app is closed
* Three-column Kanban: Menunggu / Sedang Dimasak / Selesai
* Linear flow: waiting -> [Mulai Masak] -> cooking -> [Selesai] -> done
  (no backward transitions, matching the MO lifecycle)
* Auto-refresh every 10 seconds via polling
* kitchen.order records linked to both pos.order and mrp.production
* Two-way sync: marking a kitchen.order done validates the linked MO
* VAPID keys auto-generated on install (single keypair, never rotated)
* Multi-device: several phones/tablets can subscribe at once
* Works 100% on Odoo Community — no Enterprise modules required

HOW TO USE — Initial setup
---------------------------
1. Install the module. VAPID keys are auto-generated and stored in
   ir.config_parameter (kitchen.vapid_public_key / kitchen.vapid_private_key).
2. Create a shared kitchen user, e.g. login=kitchen@gopokaja.com,
   with at least Internal User + Point of Sale / User access.
3. On every kitchen device (phone or tablet):
   a. Open https://YOUR-DOMAIN/kitchen in Chrome (Android) or Safari (iOS).
   b. Login as the kitchen user.
   c. Tap "Izinkan Notifikasi" -> grant the permission.
   d. Tap "Install App" (or "Add to Home Screen" via the browser menu)
      to install it as a PWA.
4. Done. Every paid POS order with at least one BoM-backed product will
   automatically:
     - create kitchen.order rows (one per BoM-backed POS line)
     - send a single push notification per POS order summarizing items
     - appear in the "Menunggu" column on every subscribed device

HOW TO USE — Daily kitchen flow
--------------------------------
1. Notification arrives on the kitchen phone -> staff taps it.
2. Kitchen Display opens, the new order is in "Menunggu".
3. Staff taps "▶ Mulai Masak" -> the card moves to "Sedang Dimasak".
4. When the dish is plated, staff taps "✓ Selesai" -> the card moves
   to "Selesai" (visible for 10 minutes) AND the linked Manufacturing
   Order is automatically validated (state -> done, components consumed).

DEBUG MODE
----------
Add ?debug=1 to the URL (e.g. /kitchen?debug=1) to reveal:
  * an on-page debug log panel showing every push / SW step
  * a red "Reset SW" button that unregisters all kitchen service workers
    and reloads the page
This is for troubleshooting only — staff should use the plain /kitchen URL.

ADMIN ENDPOINTS
---------------
* GET /kitchen/test-push    — sends a test push to all active subscriptions.
                              Requires base.group_system. Use this to verify
                              the push pipeline without creating a POS order.
* /kitchen/manifest.json    — PWA manifest
* /kitchen/sw.js            — service worker source
* /kitchen/orders           — JSON list of active orders (used by polling)

DEPENDENCIES
------------
Python:
  * pywebpush  (pip install pywebpush)
  * cryptography  (already shipped with Odoo)
Odoo:
  * point_of_sale, mrp, web, andykanoz_pos_auto_mo

If pywebpush is missing the module still installs — Kitchen Display works
via polling, but push notifications are silently disabled. The Odoo log
will warn at startup.

KNOWN GOTCHAS
-------------
* Push notifications require HTTPS. localhost works for development but
  any other host must be HTTPS (Cloudflare Tunnel, reverse proxy, etc.).
* Cloudflare aggressively caches /kitchen/sw.js. We mitigate this with a
  ?v=SW_VERSION query string and no-cache headers. If you change the SW
  source code, bump SW_VERSION in controllers/kitchen_controller.py so
  every browser refetches it.
* Marking a kitchen.order "done" calls button_mark_done() on the linked
  MO. If component stock is insufficient the MO validation will fail and
  be logged as a warning, but the kitchen.order will still be marked done
  so the kitchen UI is never blocked. Resolve such MOs manually in the
  Manufacturing app.
* iOS Safari only supports Web Push since iOS 16.4 and only when the PWA
  is installed to the home screen — not in a regular Safari tab.
    """,
    'author': 'Andyka',
    'depends': [
        'point_of_sale',
        'mrp',
        'web',
        'andykanoz_pos_auto_mo',
    ],
    'external_dependencies': {
        'python': ['pywebpush'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/kitchen_notify_data.xml',
        'views/kitchen_order_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
