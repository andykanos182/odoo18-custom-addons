---
description: 'Detailed knowledge for andykanoz_purchase_mobile module — mobile-friendly Purchase with expiry tracking.'
applyTo: '**/andykanoz_purchase_mobile/**'
---

# Module: `andykanoz_purchase_mobile`

Mobile-friendly Purchase Order creation interface with expiry date capture at receipt time.

## Architecture Snapshot

```
andykanoz_purchase_mobile/
├── __manifest__.py
├── controllers/main.py          # JSON-RPC for mobile UI
├── models/
│   ├── purchase_order_line.py   # adds x_expected_expiry_date
│   ├── stock_move_line.py       # propagates expiry to stock.lot on _action_done
│   └── product_template.py      # may add x_requires_expiry fallback
├── security/
├── static/src/{js,xml,scss}/    # mobile UI
└── views/
```

## Manifest Dependencies

```python
'depends': ['base', 'purchase', 'stock', 'product']
# 'product_expiry' is OPTIONAL — graceful degradation
```

## Custom Fields

### `purchase.order.line.x_expected_expiry_date`

```python
x_expected_expiry_date = fields.Date(
    string='Expected Expiry Date',
    help='Optional expected expiration date for this line. Propagates to stock.lot at receipt.'
)
```

### `product.template.x_requires_expiry` (fallback)

If the bundled `product_expiry` module is NOT installed, this custom flag enables the expiry input UI:

```python
x_requires_expiry = fields.Boolean(
    string='Requires Expiry Tracking',
    help='Enable expiry date capture even without product_expiry module.'
)
```

The UI shows expiry input if EITHER `product.use_expiration_date` (from product_expiry) OR `x_requires_expiry` is True.

## Critical Method: Expiry Propagation

**File**: `models/stock_move_line.py`

```python
class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _action_done(self):
        # Capture mapping BEFORE super() because move lines may be merged/unlinked
        expiry_map = {}  # ml.id → expected_expiry_date
        for ml in self:
            po_line = ml.move_id.purchase_line_id
            if po_line and po_line.x_expected_expiry_date:
                expiry_map[ml.id] = po_line.x_expected_expiry_date

        res = super()._action_done()

        # After super, re-browse surviving move lines and propagate
        for ml_id, expiry in expiry_map.items():
            ml = self.browse(ml_id).exists()
            if not ml or not ml.lot_id:
                continue  # merged/deleted/no-lot → skip
            # Graceful: only write if field exists (product_expiry installed)
            if hasattr(ml.lot_id, 'expiration_date'):
                ml.lot_id.expiration_date = expiry

        return res
```

⚠️ **Capture BEFORE super()** — `_action_done` may merge or unlink move lines. Re-browse with `.exists()` after.

## UI Visual States (Expiry Badge)

In the mobile line card:
- **Gray badge "Tanpa expired"** — product not perishable / no expiry set
- **Amber badge "Exp: DD Mmm YYYY"** — expiry > threshold days from today
- **Red badge "Exp: DD Mmm YYYY · dekat" + ⚠** — expiry ≤ threshold days from today

Threshold configurable via `ir.config_parameter`:
- Key: `andykanoz_purchase_mobile.expiry_warning_days`
- Default: `60`

## Common Tasks

| Task | Where |
|---|---|
| Change expiry warning threshold | Set ir.config_parameter `andykanoz_purchase_mobile.expiry_warning_days` |
| Add new field on PO line | `purchase_order_line.py` (Python) + JS state + XML template |
| Change badge colors | SCSS file in `static/src/scss/` |
| Disable graceful fallback | Make `product_expiry` a hard dependency in manifest |

## Pitfalls

- ⚠️ **`_action_done` runs in batch contexts** — Odoo may call it on hundreds of lines at once. Don't put expensive operations inline.
- ⚠️ **Lot creation can be conditional** — products with `tracking='none'` don't create lots; expiry propagation silently no-ops.
- ⚠️ **Multi-receipt scenario**: One PO with partial receipts → multiple `stock.move.line` records share the same `purchase_line_id`. All get the same expiry. Usually fine but verify in your business case.
- ⚠️ **Editing expiry AFTER receipt**: Manual edit on `stock.lot.expiration_date` is the way; this module doesn't sync back.
- ⚠️ **Mobile UI breakpoints**: Test on actual device (Tab S8, phones). CSS may need `!important` for nested modals.

## Cross-Module: How Quick Purchase Differs

`andykanoz_quick_purchase` is a **separate module** for session-based PO drafting (different from `purchase_mobile`):

| | purchase_mobile | quick_purchase |
|---|---|---|
| Entry point | Mobile-optimized PO form | Session draft → convert to PO |
| Expiry | ✅ Yes | ❌ No |
| Camera scan | (verify) | ✅ Yes (with duplicate modal) |
| Persistence | DB (PO is real) | Server session |

Don't conflate them. They share `purchase` dependency but serve different workflows.

## Test Checklist

- [ ] Create PO via mobile UI → expiry input appears for perishable products
- [ ] Expiry input HIDDEN for non-perishable products
- [ ] Confirm PO → receipt created with expiry data preserved
- [ ] Validate receipt → `stock.lot.expiration_date` populated correctly
- [ ] Without `product_expiry` module → no error, UI works, propagation silently skips
- [ ] Badge colors render correctly on Tab S8 + phone
