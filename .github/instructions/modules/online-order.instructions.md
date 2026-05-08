---
description: 'Detailed knowledge for andykanoz_online_order module — public ordering portal at /order-online.'
applyTo: '**/andykanoz_online_order/**'
---

# Module: `andykanoz_online_order`

Public ordering portal at `/order-online` for Gopokaja customers. Creates draft orders that flow into kitchen + accounting.

## Architecture Snapshot

```
andykanoz_online_order/
├── __manifest__.py
├── controllers/
│   ├── api_controller.py        # JSON-RPC: menu, create order, check availability, delivery fee
│   └── portal_controller.py     # /order-online, /my/online-orders
├── models/
│   ├── online_order.py          # main order model
│   ├── online_order_line.py     # order line
│   ├── online_order_config.py   # singleton settings (opening hours, fees, etc.)
│   ├── kitchen_order_inherit.py # adds online_order_id, relaxes pos_order_id required
│   └── pos_order_inherit.py     # adds skip_kitchen_notify field
├── data/
│   ├── online_order_sequence.xml      # ORD/YYYY/##### naming
│   ├── online_order_config_data.xml   # default singleton record
│   └── ir_cron.xml                    # auto-cancel stale drafts
├── security/ir.model.access.csv
├── static/src/{css,js}/         # portal frontend
├── templates/                   # portal QWeb templates
└── views/                       # backend admin views
```

## Manifest Dependencies

```python
'depends': [
    'base', 'website', 'portal', 'point_of_sale', 'mrp',
    'andykanoz_pos_auto_mo',
    'andykanoz_kitchen_notify',
]
```

This module **REQUIRES** kitchen_notify and pos_auto_mo. It's the most coupled module in the project.

## Key Models

### `online.order`

The main order entity.

**Critical fields**:
- `name` — auto from sequence `ORD/YYYY/#####`
- `customer_name`, `customer_phone`, `customer_email`
- `fulfillment_type` — `'pickup'` or `'delivery'`
- `scheduled_time` — when customer wants to pickup/receive
- `delivery_kecamatan`, `delivery_address` (if delivery)
- `state` — `'draft'`, `'confirmed'`, `'preparing'`, `'ready'`, `'completed'`, `'cancelled'`
- `total_amount` — computed from lines + delivery fee
- `pos_order_id` — Many2one filled when converted for accounting (post-fulfillment)
- `kitchen_order_id` — Many2one to kitchen ticket created on confirm
- `line_ids` — one2many to `online.order.line`

**Key action methods**:
- `action_confirm()` — draft → confirmed; creates kitchen.order + sends push
- `action_mark_ready()` — preparing → ready; optionally pushes to customer
- `action_complete()` — ready → completed; converts to pos.order with `skip_kitchen_notify=True`
- `action_cancel()` — any state → cancelled

### `online.order.config`

Singleton (one record only) holding business rules:
- `store_name`, `store_phone`, `store_address`
- `opening_time`, `closing_time` (float hours, e.g. 10.0 = 10:00)
- `enable_pickup`, `enable_delivery`
- `pickup_lead_time`, `delivery_lead_time` (minutes)
- `delivery_fee` (flat MVP), `min_delivery_amount`
- `advance_order_days` (how far in future can be booked)

Use `self.env['online.order.config'].sudo().get_config()` to retrieve.

### `online.order.line`

One product per line. Snapshot of `product_id`, `product_name`, `quantity`, `unit_price`, `subtotal`, `notes`.

## Public API Endpoints

All under `/api/online-order/*`, `type='json'`, `auth='public'`, `csrf=False`:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/online-order/menu` | POST | Returns menu (products marked as `online_order_available`) |
| `/api/online-order/availability` | POST | Returns current opening status + lead times |
| `/api/online-order/delivery-fee` | POST | Returns delivery fee for a kecamatan (MVP: flat) |
| `/api/online-order/create` | POST | Creates draft order from form data |

Portal pages under `/order-online/*`:

| URL | Purpose |
|---|---|
| `/order-online` | Public ordering form |
| `/order-online/thanks/<order_id>` | Confirmation + tracking link |
| `/my/online-orders` | Customer's order history (portal-authenticated) |

## Critical Patterns This Module Owns

### Pattern: `pos.order.skip_kitchen_notify`

This module ADDS the field `skip_kitchen_notify = fields.Boolean(default=False)` to `pos.order`.

When `online.order.action_complete()` creates a `pos.order` for accounting, it sets this flag to True. This prevents `andykanoz_kitchen_notify` from creating a duplicate kitchen ticket.

⚠️ **NEVER remove this field. Kitchen notify reads it.** ⚠️

### Pattern: `kitchen.order.online_order_id`

This module ADDS `online_order_id = fields.Many2one('online.order')` to `kitchen.order`, and **relaxes `pos_order_id` from required to optional** via attribute inheritance:

```python
class KitchenOrder(models.Model):
    _inherit = 'kitchen.order'

    online_order_id = fields.Many2one('online.order', ...)
    pos_order_id = fields.Many2one('pos.order', required=False)  # was required=True

    @api.constrains('pos_order_id', 'online_order_id')
    def _check_source(self):
        for rec in self:
            if not rec.pos_order_id and not rec.online_order_id:
                raise ValidationError("Kitchen order needs a source.")
```

## Frontend (Portal)

The order form is a **single-page JS app** in `static/src/js/portal_order.js`. Not OWL — vanilla JS with fetch() to the JSON-RPC endpoints. Reasons:
- Public route (no Odoo authentication)
- Simpler bundle for mobile customers

## Pitfalls & Known Limitations

- ⚠️ `/kitchen` PWA HTML does NOT yet show "ONLINE" badge visually. Backend list does. Edit `kitchen_html.py` (in kitchen_notify) to extend.
- ⚠️ WhatsApp confirmation is currently a manual link. Auto-send needs paid API (Fonnte / Wablas / Meta).
- ⚠️ Payment is COD / pay-on-pickup ONLY. No online payment integration yet.
- ⚠️ Delivery fee is flat. For distance-based, integrate `andykanoz_distance_shipping` (deferred).
- ⚠️ The `online_order_available` flag on products is what filters menu — make sure new products have it set if they should be orderable online.
- ⚠️ Sequence runs yearly (`ORD/2026/#####`), resets January 1 — coordinate with accounting if year-end happens during active orders.

## Test Checklist

- [ ] Submit order at `/order-online` → kitchen receives push
- [ ] /kitchen shows the ticket with online indicator (or backend list at minimum)
- [ ] Action "Mark Ready" works
- [ ] Action "Complete" creates pos.order with `skip_kitchen_notify=True`
- [ ] No duplicate kitchen ticket appears when completing
- [ ] Auto-cancel cron removes stale drafts after configured timeout
- [ ] Outside opening hours → form shows "closed" message
- [ ] Pickup-only mode → delivery section hidden in form
