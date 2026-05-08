---
description: 'Detailed knowledge for andykanoz_pos_auto_mo module — auto-creates Manufacturing Orders from POS payments.'
applyTo: '**/andykanoz_pos_auto_mo/**'
---

# Module: `andykanoz_pos_auto_mo`

When a POS order is paid, automatically create a Manufacturing Order (MO) for each line whose product has a Bill of Materials.

## Architecture Snapshot

```
andykanoz_pos_auto_mo/
├── __manifest__.py
├── models/
│   └── pos_order.py     # extends pos.order.action_pos_order_paid
├── security/ir.model.access.csv  # may be empty if no new model
└── views/               # may be empty
```

## Manifest Dependencies

```python
'depends': ['base', 'point_of_sale', 'mrp']
```

## How It Works

```python
# Probable structure of pos_order.py
class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        for order in self:
            order._auto_create_manufacturing_orders()
        return res

    def _auto_create_manufacturing_orders(self):
        """For each order line where product has a BoM, create a confirmed MO."""
        Mo = self.env['mrp.production']
        for line in self.lines:
            bom = self.env['mrp.bom']._bom_find(
                products=line.product_id, company_id=self.company_id.id,
            ).get(line.product_id)
            if not bom:
                continue
            mo = Mo.create({
                'product_id': line.product_id.id,
                'product_qty': line.qty,
                'product_uom_id': line.product_id.uom_id.id,
                'bom_id': bom.id,
                'origin': self.name,
            })
            mo.action_confirm()
```

⚠️ **The above is the LIKELY structure — read actual file before editing.** Field names and method signatures may differ slightly.

## Key Behaviors

- Fires on `action_pos_order_paid` — once per order, after super().
- Skips lines without a BoM (regular goods, not made-to-order).
- Creates MO in confirmed state (not draft) — assumes BoM is correct and ready to manufacture.
- Sets `origin` = POS order reference for traceability.

## Interaction with Online Order

When `online.order.action_complete()` creates a `pos.order` with `skip_kitchen_notify=True`:
- ✅ pos_auto_mo **STILL FIRES** — MO is needed for accounting/inventory regardless
- ❌ kitchen_notify does NOT fire — kitchen already got the ticket from online_order

This is intentional: the `skip_kitchen_notify` flag only controls kitchen notification, not MO creation.

## Common Modifications

| Task | Where |
|---|---|
| Skip MO creation for certain products | Add filter in `_auto_create_manufacturing_orders` (e.g. by category, by `service_tracking`) |
| Create MO in draft instead of confirmed | Remove the `action_confirm()` call |
| Different MO routing/source location | Pass `location_src_id`/`location_dest_id` in create vals |
| Track which orders auto-created MO | Add `auto_created_from_pos = fields.Boolean()` on mrp.production |

## Pitfalls

- ⚠️ **Multi-level BoM**: `_bom_find` returns the top-level BoM. Sub-MOs are created automatically by Odoo's manufacturing engine.
- ⚠️ **Negative stock**: If components don't have stock, MO confirmation may still succeed but reservation will be partial. Verify stock setup.
- ⚠️ **Performance with many lines**: Bulk POS orders (rare in F&B but possible) may slow payment. Consider deferring to cron if it becomes an issue.
- ⚠️ **Refund flow**: When a POS order is refunded, MO is NOT auto-cancelled. Manual cleanup needed.
- ⚠️ **Already paid + reopened**: If a paid order is somehow reopened and re-paid, this could create duplicate MOs. Verify idempotency if encountered.

## Test Checklist

- [ ] POS order with product (has BoM) paid → MO created, confirmed
- [ ] POS order with product (no BoM) paid → no MO, no error
- [ ] POS order with mixed products → MO only for BoM products
- [ ] Online order completed (creates pos.order) → MO fires correctly
- [ ] MO origin field shows POS order reference
