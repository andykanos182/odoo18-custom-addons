---
description: 'Trace how data flows across multiple modules — from trigger to final state, identifying all hooks and side effects.'
mode: 'agent'
---

# Cross-Module Trace

Use this prompt when you need to understand or document how data flows across multiple Odoo modules — especially useful for debugging unexpected behavior or onboarding to a complex feature.

## Step 1 — Define the Trace

Ask the user:

1. **Starting point** — what's the trigger? (e.g. "user pays POS order", "user submits online order form", "validate purchase receipt")
2. **End point** — what's the final outcome? Or "trace until I say stop"?
3. **Specific concern** — are they debugging something, or just understanding?

## Step 2 — Identify the Entry Method

Translate the trigger into the actual code entry point:

| Trigger description | Likely entry method |
|---|---|
| "User pays POS order" | `pos.order.action_pos_order_paid()` |
| "User submits online order" | `online.order.create()` via `/api/online-order/create` |
| "User confirms purchase order" | `purchase.order.button_confirm()` |
| "User validates receipt" | `stock.picking.button_validate()` → `stock.move.line._action_done()` |
| "Customer subscribes to /kitchen" | `kitchen.vapid.subscribe()` (or controller endpoint) |
| "User adds product to print list" | `product.checker.print.list.create()` |

## Step 3 — Trace Forward

Use `codebase`/`search`/`usages` tools to follow the call chain:

1. Read the entry method.
2. Identify every `super()` call, every method call, every event/notification/cron triggered.
3. For each, recursively trace into modules that override or hook those.
4. Stop when you reach: a return value, a UI update, an external system call, or user-defined endpoint.

For each hop, capture:
- **Module** owning the method
- **File:line** of the implementation
- **What it does** (one sentence)
- **Side effects** (DB writes, push notifications, MO creation, etc.)

## Step 4 — Visualize the Flow

Use ASCII arrows + indentation:

```
User pays POS order
  └─→ pos.order.action_pos_order_paid()
        ├── [point_of_sale] super(): mark order as paid, generate invoice
        │
        ├── [andykanoz_pos_auto_mo] override:
        │     For each line with BoM:
        │       └─→ mrp.production.create() → action_confirm()
        │             └─→ stock.move reservations triggered
        │
        ├── [andykanoz_kitchen_notify] override:
        │     If NOT skip_kitchen_notify:
        │       ├─→ kitchen.order.create()
        │       │     - Sets pos_order_id
        │       │     - State: pending
        │       └─→ kitchen.vapid.send_push_to_all(
        │             title="🍽️ Order baru!",
        │             body=...)
        │             └─→ pywebpush.webpush() per subscription
        │
        └── [andykanoz_online_order] override (extends pos.order):
              No additional behavior on this path; only adds skip_kitchen_notify field

← Returns to caller
```

## Step 5 — Highlight Risks & Variations

After the main trace, list:

### Branching points

Where does the flow change based on data?

```
* If pos.order.skip_kitchen_notify == True:
  → kitchen_notify hook becomes no-op
  → no kitchen ticket, no push (intentional, set by online_order conversion)

* If line.product_id has no BoM:
  → pos_auto_mo silently skips that line
  → no MO created
```

### Failure modes

What can go wrong at each hop?

```
* mrp.production.create() can fail if:
  - BoM has invalid components (deleted products)
  - User lacks mrp.group_user permission
  → would raise UserError; payment still succeeds, MO is missing

* webpush() can fail if:
  - VAPID key invalid
  - Subscription expired (browser unregistered)
  → silently logged, kitchen ticket still exists in DB
```

### Race conditions

```
* If user double-clicks "Validate" rapidly:
  - Two threads enter action_pos_order_paid simultaneously
  - Could create duplicate MOs / duplicate kitchen tickets
  - Mitigation: state check at top of override?
```

### Performance hotspots

```
* For a POS order with 50+ lines, all with BoM:
  - 50 mrp.production.create() calls
  - 50 action_confirm() → 50 stock.move reservations
  - Could slow payment finalization
  - Mitigation: defer to cron if >10 lines?
```

## Step 6 — Output Format

```markdown
# Trace: <trigger> → <endpoint>

## Visual Flow
<ASCII diagram>

## Module Touchpoints
| Order | Module | File:line | Method | Side Effect |
|---|---|---|---|---|
| 1 | point_of_sale | <path> | <method> | <effect> |
| 2 | andykanoz_pos_auto_mo | <path> | <method> | <effect> |
| ... |

## Branching Points
- ...

## Failure Modes
- ...

## Performance Notes
- ...

## Recommendations (if any)
- ...
```

## Step 7 — Offer Follow-Ups

End with options:

> "Mau saya:
> (1) Drill down ke salah satu hop untuk explain detail?
> (2) Trace flow yang lain?
> (3) Generate dokumentasi markdown dari trace ini untuk Anda simpan?"

## Tone

- **Concrete and evidence-based.** Every claim cites file:line.
- **Acknowledge what you don't know.** "I haven't read kitchen_html.py yet — let me check before continuing."
- **Highlight surprises.** If the actual code differs from documented architecture, FLAG it.
- **No fabrication.** If a method doesn't exist or wasn't called, don't invent it.
