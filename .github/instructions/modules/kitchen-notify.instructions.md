---
description: 'Detailed knowledge for andykanoz_kitchen_notify module — central to POS/Kitchen/Online integrations.'
applyTo: '**/andykanoz_kitchen_notify/**'
---

# Module: `andykanoz_kitchen_notify`

Web Push notifications and live kitchen display for incoming orders. Central to the POS / Online Order ecosystem.

## Architecture Snapshot

```
andykanoz_kitchen_notify/
├── __manifest__.py
├── controllers/
│   ├── main.py                  # /kitchen PWA endpoint, subscription endpoints
│   └── kitchen_html.py          # generates /kitchen HTML (PWA frontend)
├── models/
│   ├── kitchen_order.py         # the ticket/order model
│   ├── kitchen_vapid.py         # VAPID keys + push send + subscriptions
│   └── pos_order.py             # extends pos.order to fire push on payment
├── data/
│   └── ir_cron.xml              # auto-clear old served kitchen orders
├── security/ir.model.access.csv
├── static/                      # PWA service worker + manifest
└── views/
    └── kitchen_order_views.xml  # backend list/form/kanban
```

## Key Models

### `kitchen.order`

A single kitchen ticket. Created by:
- `pos.order.action_pos_order_paid()` → POS-originated
- `online.order.action_confirm()` → online-originated

**Critical fields**:
- `name` — auto-generated reference
- `pos_order_id` — Many2one('pos.order'), **was REQUIRED originally; ONLINE ORDER MAKES IT OPTIONAL** via inheritance
- `online_order_id` — Many2one('online.order'), added by `andykanoz_online_order`
- `state` — `'pending'`, `'preparing'`, `'ready'`, `'served'`, `'cancelled'`
- `line_ids` — one2many to `kitchen.order.line`

**Key methods**:
- `action_start_preparing()` — state → preparing
- `action_mark_ready()` — state → ready (triggers ready-push to cashier?)
- `action_mark_served()` — state → served (final state)
- `action_cancel()` — state → cancelled

### `kitchen.vapid`

Singleton-ish model holding VAPID keys for Web Push.

**Methods**:
- `get_or_generate_keys()` — returns dict with public/private VAPID keys; generates if not exists
- `send_push_to_all(title, body, data=None)` — iterates all active subscriptions, sends Web Push via `pywebpush` library

**Subscriptions** stored as `kitchen.vapid.subscription` (or similar) — populated when staff "subscribes" via /kitchen PWA.

## Critical Cross-Module Hook

```python
# Inside andykanoz_kitchen_notify/models/pos_order.py (probable structure)
class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        for order in self:
            # 🚨 CRITICAL: respect skip_kitchen_notify flag
            if order.skip_kitchen_notify:
                continue
            order._create_kitchen_order_and_push()
        return res
```

**The `skip_kitchen_notify` flag is OWNED by `andykanoz_online_order`** (it adds the field to `pos.order`). Kitchen notify must respect it to prevent duplicate kitchen tickets when an online order is later paid in POS.

## /kitchen PWA Endpoint

`/kitchen` is a public-ish HTML page rendered by `kitchen_html.py`. It's a Progressive Web App:
- Has a service worker that listens for push events
- Stores the user's subscription in localStorage
- Polls `/kitchen/orders` for pending tickets
- Click "Subscribe" → registers with `kitchen.vapid` model

**Rendered HTML is generated in Python** (not QWeb) — to extend the UI, edit `kitchen_html.py`. This is unusual for Odoo and worth flagging.

## Common Modifications

| Task | Where |
|---|---|
| Add field to kitchen ticket | `kitchen_order.py` + `kitchen_order_views.xml` |
| Change push notification text | search for `send_push_to_all(` calls — usually in `pos_order.py` and `online_order.py` |
| Add a new push trigger event | call `self.env['kitchen.vapid'].send_push_to_all(...)` from any model method |
| Filter which orders create tickets | edit `_create_kitchen_order_and_push` predicate in `pos_order.py` |
| Render new badge on /kitchen UI | edit `kitchen_html.py` (Python-generated HTML, not QWeb) |

## Pitfalls

- ⚠️ **VAPID keys are environment-specific**. Don't commit them. They're stored in DB via `kitchen.vapid` config.
- ⚠️ **Web Push requires HTTPS** in production. Localhost dev works without HTTPS for testing.
- ⚠️ **Service worker caching** — after JS changes, staff needs to "Update" the PWA or hard-refresh. Document this in handoff to staff.
- ⚠️ **`kitchen_order.pos_order_id` was REQUIRED originally** — the inheritance from online_order relaxes it. If you write a fresh override, double-check the constraint.
- ⚠️ **Don't move `_create_kitchen_order_and_push` logic out of `pos_order.py` override** — multiple modules hook into `action_pos_order_paid` and expect specific ordering.

## Test Checklist

Before considering kitchen notify changes "done":
- [ ] POS order paid → kitchen ticket appears + push received
- [ ] Online order confirmed → kitchen ticket appears + push received (different title)
- [ ] Online order converted to POS (with `skip_kitchen_notify=True`) → NO duplicate ticket, NO duplicate push
- [ ] Cancel kitchen order → state changes correctly
- [ ] /kitchen page reachable from external network (Cloudflare Tunnel)
