---
description: 'Detailed knowledge for andykanoz_product_checker module.'
applyTo: '**/andykanoz_product_checker/**'
---

# Module: `andykanoz_product_checker`

Backend barcode scanner for product lookup, price/stock check, quick-create, and persistent print list.

## Architecture Snapshot

```
andykanoz_product_checker/
├── __manifest__.py
├── controllers/main.py              # placeholder (all comms via ORM RPC)
├── models/
│   ├── product_checker.py           # extends product.template + print list model (~main file, ~big)
│   ├── print_list.py                # alternative print list model (legacy — verify which is active)
│   └── saved_filter.py              # favorites / saved searches
├── security/ir.model.access.csv
├── static/src/
│   ├── js/
│   │   ├── product_checker.js              # main OWL component (~2300 lines)
│   │   ├── barcode_camera_widget.js        # reusable camera-scan field widget
│   │   └── zxing_barcode_polyfill.js       # BarcodeDetector polyfill for iOS Safari
│   ├── scss/product_checker.scss
│   └── xml/
│       ├── product_checker.xml
│       └── barcode_camera_widget.xml
└── views/
    ├── product_checker_menu.xml
    ├── product_checker_views.xml            # client action record
    └── product_template_views.xml           # injects barcode_camera widget on standard product form
```

## Manifest Dependencies

```python
'depends': ['base', 'product', 'stock', 'website_sale']
```

`website_sale` is REQUIRED because `is_published` and `public_categ_ids` come from it.

## Key Methods on `product.template`

These are public RPC entry points — callable via `this.orm.call('product.template', '<method>', args)`:

### `search_product_by_barcode(barcode, pricelist_id=None) → dict`
Main lookup for scanner input and history clicks.

**Search order** (fallback chain):
1. exact `barcode` match on template
2. exact `default_code` (internal reference)
3. exact `barcode` on variant (`product.product`)
4. ilike on `name`

Returns `{'found': True, 'data': {...}}` or `{'found': False, 'searched': '<code>'}`.

### `search_products_for_panel(query='', pricelist_id=None, offset=0, limit=50, filter_domain=None) → dict`
Paginated product list for left-side drawer.

`filter_domain` is a Python-literal domain string from `DomainSelectorDialog` (e.g. `"[('categ_id','in',[27])]"`). Combined with query using AND.

### `quick_create_from_checker(vals) → dict`
Creates new product from quick form. Validates duplicate barcode before create. Sets `type='consu' + is_storable=True` for storable items.

## Print List Feature

**Model**: `product.checker.print.list`
- One record per (user, product) pair
- `product_tmpl_id` Many2one to product
- `quantity` Integer (label count)
- `user_id` Many2one to res.users (`default=lambda self: self.env.user`)

**Workflow**:
1. User clicks "Add to Print List" on a scanned product (or auto-add via checkbox)
2. Print List drawer slides in from right side
3. User adjusts quantities, then clicks "Print Labels"
4. Opens Odoo's native `product.label.layout` wizard with collected products

**Critical**: do NOT replicate label printing logic. The `product.label.layout` wizard is the integration point — pass it `product_ids` and let Odoo handle PDF generation.

## Saved Filters Feature

**Model**: `product.checker.saved.filter`
- Stores user's favorite domain searches
- Used with Odoo's `DomainSelectorDialog` for visual filter building

⚠️ **Known issue solved**: see Internal Knowledge Base case `DomainSelectorDialog OwlError` — strict props validation in OWL 2 means only `resModel`, `domain`, `isDebugMode`, `onConfirm` are accepted props.

## Responsive Breakpoints

This module is mobile-first. Breakpoints at:
- `1200px` — sidebar shrinks
- `992px` — tablet landscape
- `768px` — tablet portrait / large phone
- `480px` — small phone (icon-only buttons, slide-in drawer)

## Common Tasks Reference

| Task | Where |
|---|---|
| Change debounce delay | `product_checker.js` — search for `setTimeout(..., 500)` |
| Change history limit | `product_checker.js` — `if (this.state.history.length > 20)` |
| Change main image size | `product_checker.scss` — `.o_pc_product_image { flex: 0 0 400px; }` |
| Add field to quick-create | `product_checker.xml` (form) + `product_checker.js` (state) + `product_checker.py` (`quick_create_from_checker`) |

## Pitfalls

- ⚠️ Two print list model files exist (`print_list.py` and inside `product_checker.py`) — verify which is active in `__init__.py` before editing.
- ⚠️ `_get_product_price()` signature varies between Odoo 18 minor versions — fallback to `list_price` is implemented with try/except.
- ⚠️ Camera scan on iOS Safari requires the `zxing_barcode_polyfill.js` (BarcodeDetector API not native).
- ⚠️ DOM `BarcodeDetector` is gated behind HTTPS in browsers — local dev needs `http://localhost` (works) or self-signed cert.
