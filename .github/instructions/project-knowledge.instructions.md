---
description: 'Project knowledge base — module map, dependency graph, cross-module integration patterns. Always loaded.'
applyTo: '**'
---

# Andyka / Gopokaja — Project Knowledge Base

This file is your map of the codebase. Reference it before answering questions about modules. For deep details about a specific module, see `instructions/modules/<module>.instructions.md` (auto-loaded when editing that module's files).

## 🗺️ Module Map

All modules are prefixed `andykanoz_` and live in `D:\MyServer\Odoo18\Addons\`.

| Module | Purpose | Key Models | Status |
|---|---|---|---|
| `andykanoz_product_checker` | Backend barcode scan + price/stock + print list | `product.template` (ext), `product.checker.print.list`, `product.checker.saved.filter` | ✅ Production |
| `andykanoz_product_kanban_desktop` | Responsive kanban view for products (3 breakpoints) | `product.template` (view only) | ✅ Production |
| `andykanoz_kitchen_notify` | Web Push to kitchen display | `kitchen.order`, `kitchen.vapid` | ✅ Production |
| `andykanoz_pos_auto_mo` | Auto-create MO from POS payment | `pos.order` (ext) | ✅ Production |
| `andykanoz_online_order` | Public ordering portal `/order-online` | `online.order`, `online.order.line`, `online.order.config` | ✅ Production |
| `andykanoz_purchase_mobile` | Mobile-friendly PO with expiry tracking | `purchase.order.line` (ext), `stock.move.line` (ext) | ✅ Production |
| `andykanoz_quick_purchase` | Session-based PO drafting interface | session storage on user | ✅ Production |
| `andykanoz_distance_shipping` | Distance-based shipping fee | (verify before answering) | ⚠️ Low-detail |
| `andykanoz_google_maps_peta` | Google Maps integration | (verify before answering) | ⚠️ Low-detail |
| `andykanoz_barcode_receiving` | Barcode receiving workflow | (verify before answering) | ⚠️ Low-detail |
| `andykanoz_auto_edit` | Auto-edit feature | (verify before answering) | ⚠️ Low-detail |

For modules marked ⚠️ "Low-detail": **read the actual files via `codebase`/`search` tools before claiming any specific behavior**. Do not fabricate field names or method signatures.

## 🔗 Dependency Graph

```
                           base
                            │
                ┌───────────┼───────────┬──────────┬─────────┐
                │           │           │          │         │
              product     stock      website     mrp      portal
                │           │      website_sale    │         │
                │           │           │          │         │
                │           ▼           ▼          ▼         │
                │     product_checker_                       │
                │   product_kanban_desktop                   │
                │                                            │
                ├──────► purchase ◄──── purchase_mobile      │
                │           │              │                 │
                │           ▼              ▼                 │
                │       quick_purchase   distance_shipping  │
                │                                            │
                └──────► point_of_sale                       │
                              │                              │
                              ▼                              │
                         pos_auto_mo ◄────┐                 │
                              │            │                 │
                              ▼            │                 │
                        kitchen_notify ────┤                 │
                              │            │                 │
                              ▼            ▼                 │
                              └────► online_order ◄──────────┘
                                          │
                                          ▼
                                   (uses google_maps_peta
                                    for delivery calc)
```

## 🌊 Critical Cross-Module Flows

### Flow 1: POS Order → Manufacturing + Kitchen Push

```
User taps "Payment" → "Validate" in POS
  └─→ pos.order.action_pos_order_paid()
        ├─→ andykanoz_pos_auto_mo override:
        │     • For each line where product has BoM:
        │       create mrp.production (state='confirmed')
        │     • Skip if no BoM
        │
        └─→ andykanoz_kitchen_notify override:
              • Create kitchen.order with pos_order_id
              • Iterate kitchen.vapid subscriptions
              • Send Web Push notification
              • UNLESS pos.order has skip_kitchen_notify=True
                (this flag is set by online_order to prevent dup push)
```

### Flow 2: Online Order → Kitchen Push (no POS yet)

```
Customer submits form at /order-online
  └─→ POST /api/online-order/create
        └─→ online.order.create()
              └─→ online.order.action_confirm()
                    └─→ Directly creates kitchen.order
                        with online_order_id (pos_order_id is null)
                    └─→ Calls kitchen.vapid.send_push_to_all()
                        with custom payload (title="Online Order!")

LATER, when customer pays at outlet:
  └─→ Staff converts online.order → pos.order
        └─→ pos.order is created with skip_kitchen_notify=True
            • prevents duplicate kitchen ticket
            • prevents duplicate push notification
            • but pos_auto_mo STILL fires (MO is needed for accounting)
```

### Flow 3: Purchase Receipt → Stock Lot Expiry

```
Buyer creates PO via Purchase Mobile
  └─→ purchase.order.line gets x_expected_expiry_date

Buyer confirms PO → state='purchase' → stock.picking (receipt) created

Receiver validates receipt
  └─→ stock.move.line._action_done() override (purchase_mobile):
        • For each move line with purchase_line_id:
          - Read x_expected_expiry_date from PO line
          - If product has tracking=lot/serial:
            * stock.lot is auto-created
            * Override expiration_date with PO line value
        • Graceful: skip if product_expiry module not installed
          (hasattr check on stock.lot.expiration_date)
```

## 🔐 Critical Patterns to Preserve

### Pattern 1: `skip_kitchen_notify` Flag

**Owner module**: `andykanoz_online_order` (extends `pos.order`)

**Field**: `pos.order.skip_kitchen_notify = fields.Boolean(default=False)`

**Set when**: online order is converted to POS order for accounting.

**Read by**: `andykanoz_kitchen_notify` in its `action_pos_order_paid` override — bails out if flag is True.

**Why it exists**: prevents duplicate kitchen ticket / duplicate push when order originates online.

**If you touch `pos.order` overrides, RESPECT this flag.** Do not strip or invert it.

### Pattern 2: `product.template` Single Source of Truth

`andykanoz_product_checker` and `andykanoz_product_kanban_desktop` both read product data. Neither **adds new fields** to `product.template`. They only read existing fields:
- `name`, `default_code`, `barcode`
- `list_price`, `standard_price`, `qty_available`
- `is_published`, `public_categ_ids` (from `website_sale`)
- `sale_ok`, `purchase_ok`, `is_storable`, `available_in_pos`

**If you need a new field on product**, add it in a logical owner module — most likely `product_checker` since it has the richest UI.

### Pattern 3: Graceful Optional Dependency

For features that depend on **modules that may not be installed** (e.g. `product_expiry` for expiration_date), use `hasattr` runtime checks rather than hard manifest dependency. This keeps modules installable in minimal environments.

```python
# Pattern: graceful degradation
StockLot = self.env['stock.lot']
if hasattr(StockLot, 'expiration_date'):
    lot.expiration_date = po_line.x_expected_expiry_date
# else: silently skip — feature unavailable but module still works
```

### Pattern 4: Cross-Module Hooks Use Inheritance

Every cross-module integration is via `_inherit` and `super()`, NEVER by editing another module's files. If you see code in module A that imports from module B's internals, that's a code smell — refactor to use proper Odoo extension points (model inheritance, event hooks, computed fields).

## ⚙️ Environment Constants

- **Container name**: confirm via `docker ps` (do not hardcode container ID — it changes on recreate)
- **Local dev URL**: `http://localhost:8018`
- **Production URL**: `https://nitro.gopokaja.com` (Cloudflare Tunnel)
- **Production target devices**: Samsung Tab S8 (kitchen + cashier)
- **Phone test target**: Xiaomi Note 10 Pro (mobile responsive)
- **Logs**: `D:\MyServer\Odoo18\logs\odoo.log`
- **Odoo core source (READ-ONLY)**: `D:\MyServer\Odoo18\Source Code Odoo18\addons\`

## 🚨 When in Doubt

- **Module behavior unclear?** → Use `codebase` search; read the actual `.py` file. Do NOT fabricate.
- **Field name uncertain?** → Search for `fields.<Type>(` in the relevant model file.
- **Cross-module conflict suspected?** → Trace the flow in this file's "Critical Cross-Module Flows" section first.
- **Question outside this map?** → Tell Andyka you don't have detail and offer to read files to find out.

## 📍 Where to Add New Knowledge

When a new pattern, gotcha, or integration is discovered, append a note to:
- `agents/odoo18-expert.agent.md` → `INTERNAL KNOWLEDGE BASE` section (case studies)
- This file → for cross-module flows or project-wide patterns

Andyka must append manually (these files are read-only at runtime). Output the diff/markdown block when "ingat ini" / "save ini" is said.
