Module: andykanoz_product_kanban_desktop
Purpose: Enhanced desktop-style Kanban for products (pricelist selector, inline toggles, category edits).

Overview:
- Frontend assets (JS/CSS/XML) implement a custom Kanban controller and a ControlPanel patch to add a "Desktop Kanban" switcher button.
- Backend model extension computes dynamic pricelist price and profit and exposes related template fields for variant compatibility.

Key files:
- models/product_template.py
  - Extends `product.template` with `dynamic_pricelist_price` and `dynamic_profit`.
  - Extends `product.product` (variant) with its own `_compute_dynamic_price`. (Note: We rely on standard Odoo `_inherits` so `product.product` automatically has `categ_id`, `sale_ok`, etc. We do NOT redefine them).

- views/product_kanban_views.xml
  - Defines `product.template` desktop kanban view: `product_template_kanban_view_desktop`.
  - Added `product.product` desktop kanban view: `product_product_kanban_view_desktop` (mirrors template card layout, but uses `lst_price` for fallback variant pricing).

- views/kanban_desktop_action.xml
  - Action `action_product_desktop_kanban` (product.template) — existing.
  - Added `action_product_product_desktop_kanban` for `product.product` (variant) view.

- static/src/js/product_kanban_controller.js
  - Controller that fetches pricelists and updates search context (works for both models).

- static/src/js/product_kanban_view.js
  - Registers `product_kanban_desktop` view type and sets `buttonTemplate`.

- static/src/js/view_switcher_patch.js
  - Patched to show the Desktop Kanban switcher on both `product.template` and `product.product`.
  - Navigates to the matching action depending on current model.

- static/src/xml/product_kanban_buttons.xml
  - Button template with the pricelist dropdown.

What I changed (summary):
- Added `ProductProduct` `_inherit` in `models/product_template.py` for variant-level price computation (`_compute_dynamic_price`).
- Added `product.product` kanban view to `views/product_kanban_views.xml`.
- Added action for `product.product` in `views/kanban_desktop_action.xml`.
- Updated `view_switcher_patch.js` so the control-panel button appears for variants and opens the correct action.
- Created this `MODULE_CONTEXT.md` to document structure and changes for easier future development.

Testing & debugging notes:
1. Restart Odoo after this change (Python code modified):

   ⚠️ Jangan lupa restart Odoo:
   docker restart 9f007b47a78a

2. After restart, update module (Apps → Update Apps List if needed) and upgrade `andykanoz_product_kanban_desktop`.
3. Browse to Inventory → Products (Templates) and Inventory → Products (Variants) and ensure the Desktop Kanban button appears in the view switcher.
4. Open Desktop Kanban from either Products (Templates) or Products (Variants); the cards should show pricelist dropdown and inline toggles.
5. If things don't appear: check browser console for JS errors and Odoo server logs for Python tracebacks.

Quick debug steps:
- Browser console: look for errors from `andykanoz_product_kanban_desktop` assets.
- Server logs: tail Odoo log while reproducing the issue.
- If changes to XML views don't reflect, clear browser cache / hard reload, and run `?debug=assets` to bypass assets caching.

Notes & caveats:
- The variant pricing compute attempts variant-level pricelist lookup first, then falls back to template-level if necessary.
- Because `product.product` inherits `product.template` via `_inherits`, fields like `categ_id` or `sale_ok` are automatically accessible. Overriding them via `related` was a bug and has been removed to avoid breaking native Odoo behavior.

If you want, I can now restart Odoo and run a quick smoke-check, then fix any errors found.
