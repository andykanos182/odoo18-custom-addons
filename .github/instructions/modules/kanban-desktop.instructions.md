---
description: 'Detailed knowledge for andykanoz_product_kanban_desktop module — responsive product kanban view.'
applyTo: '**/andykanoz_product_kanban_desktop/**'
---

# Module: `andykanoz_product_kanban_desktop`

Custom kanban view for product master with full responsive support (desktop / tablet / phone).

## Architecture Snapshot

```
andykanoz_product_kanban_desktop/
├── __manifest__.py
├── static/src/
│   ├── css/kanban_desktop.css           # 3-breakpoint responsive
│   ├── js/view_switcher_patch.js        # patches ViewSwitcher to add this kanban
│   └── xml/view_switcher_patch.xml
├── views/
│   └── product_kanban_views.xml         # the kanban view definition
└── (no models — view-only module)
```

## Manifest Dependencies

```python
'depends': ['base', 'product']
```

This is a **view-only** module — no Python models, no fields, no business logic. Pure frontend.

## Responsive Breakpoints

Three states based on viewport width:

| Breakpoint | Trigger | Layout |
|---|---|---|
| **Desktop** | `≥ 1200px` | 4-5 cards per row, full info |
| **Tablet** | `768px - 1199px` | 2-3 cards per row, condensed (Tab S8 target) |
| **Phone** | `< 768px` | 1 card per row, minimal |

CSS is in `static/src/css/kanban_desktop.css`. All rules scoped under a parent class to avoid global pollution.

## View Switcher Patch

`view_switcher_patch.js` extends Odoo's view switcher to inject the custom kanban as an option for `product.template`:

```javascript
import { patch } from "@web/core/utils/patch";
import { ViewSwitcher } from "@web/views/view_switcher";

patch(ViewSwitcher.prototype, {
    setup() {
        super.setup();
        // Add custom kanban option for product.template
    },
});
```

⚠️ **Don't break this patch when upgrading Odoo** — `ViewSwitcher` API may change between minor versions.

## Common Tasks

| Task | Where |
|---|---|
| Change cards per row | `kanban_desktop.css` — `.o_kanban_record { width: ...% }` per breakpoint |
| Show/hide field on card | `product_kanban_views.xml` — add/remove `<field name="..."/>` |
| Change breakpoint thresholds | `kanban_desktop.css` — `@media (min-width: ...)` |
| Add quick-action button | `product_kanban_views.xml` — `<button name="..." type="object" .../>` |

## Pitfalls

- ⚠️ **No models means no upgrade impact for fields** — but view changes still need module upgrade in Apps.
- ⚠️ **CSS scoping**: ALL custom CSS must be under a unique parent class (e.g. `.o_andykanoz_kanban_desktop`) to avoid breaking other kanbans.
- ⚠️ **Tab S8 portrait vs landscape**: 768px is the threshold; landscape Tab S8 is ~1024px (tablet view), portrait is ~768px (also tablet view). Test both.
- ⚠️ **View switcher patch is order-sensitive**: if other modules also patch ViewSwitcher, the order in `assets` matters.

## Test Checklist

- [ ] Desktop: 4-5 product cards per row
- [ ] Tablet (Tab S8 portrait): 2-3 cards per row, tap-friendly
- [ ] Phone: 1 card per row, all info readable
- [ ] View switcher shows the custom kanban as an option
- [ ] Cards link to product form on click
- [ ] No CSS bleed into other kanbans (sale order, purchase, etc.)
