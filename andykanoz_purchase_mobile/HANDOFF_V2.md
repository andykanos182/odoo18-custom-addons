# HANDOFF V2 — andykanoz_purchase_mobile

**Status:** Phase 6 implementation complete, end-to-end functional (pending user verification)
**Created:** 22 April 2026
**Supersedes planning in:** `HANDOFF_V1.md` (still valid as reference for original scope & decisions)
**Target:** Odoo 18 Community
**Module Path:** `D:\MyServer\Odoo18\Addons\andykanoz_purchase_mobile`

---

## 0. How to Read This Document

V1 = original plan (scope, decisions, open questions, phase breakdown).
**V2 = what has actually been implemented, how, what broke along the way, and the landmines future AI sessions need to step around.**

If you are a fresh AI picking up this project, read V1 first for the "why", then V2 for the "how it actually turned out and what's still to do".

---

## 1. Phase Status Summary

| Phase | Scope | Status | Notes |
|---|---|---|---|
| 1 | Skeleton (module + menu + standalone page) | ✅ Done | Menu appears under Purchase root |
| 2 | Models + 4 JSON-RPC endpoints + config param | ✅ Done | Tested via Phase 2 endpoint tester UI |
| 3 | OWL bootstrap + POList + VendorPicker | ✅ Done | Required painful fixes — see §3 below |
| 4a | POEditor + ProductPicker + basic LineCard | ✅ Done | User-confirmed working |
| 4b | LineCard polish (QtyStepper, selects, inputs, expiry) | ✅ Done | User-confirmed working |
| 5 | Expiry propagation (PO line → stock.lot on receipt) | ✅ Done | Hybrid strategy per V1 §5. See §10 below. |
| 6 | Save / Confirm / Delete endpoints + UI | ✅ Done | User-confirmed working |
| 7 | PWA (manifest, service worker, install flow) | 🟡 In progress | controllers/pwa.py + template wiring done. Needs user upgrade + test on phone. See §12 below. |
| 8 | Barcode scanner (camera) | ✅ Done | BarcodeScanner component + ProductPicker integration. See §13. Needs phone-camera test. |
| 8b | Packaging-barcode auto-select | ✅ Done | Scan box barcode → line gets packaging pre-selected + qty = packaging.qty. See §14. |
| 8b+ | UoM dropdown fix | ✅ Done | Existing & new lines now show full UoM list filtered by category. See §15. |

---

## 2. Current File Structure (authoritative)

```
andykanoz_purchase_mobile/
├── __init__.py
├── __manifest__.py                        # name="AndykaNoz - Purchase Mobile", category="MyCustom/Modules"
├── HANDOFF_V1.md                          # original plan
├── HANDOFF_V2.md                          # THIS FILE — current state
│
├── controllers/
│   ├── __init__.py                        # from . import main, api, pwa
│   ├── main.py                            # /app route, renders QWeb app_shell
│   ├── api.py                             # 7 JSON-RPC endpoints
│   └── pwa.py                             # PWA: manifest.json, service-worker.js, icon.svg
│
├── models/
│   ├── __init__.py
│   ├── purchase_order.py                  # x_created_via_mobile (Boolean, indexed)
│   ├── purchase_order_line.py             # x_expected_expiry_date (Date)
│   └── product_template.py                # x_requires_expiry (Boolean, fallback flag)
│
├── data/
│   ├── ir_sequence.xml                    # sequence "MP00xxx"
│   └── ir_config_parameter.xml            # expiry_warning_days = 60
│
├── security/
│   └── ir.model.access.csv                # (placeholder — no custom models to gate yet)
│
├── views/
│   ├── purchase_mobile_action.xml         # ir.actions.act_url → /app
│   ├── purchase_mobile_menu.xml           # menuitem under purchase.menu_purchase_root
│   └── purchase_mobile_templates.xml      # QWeb app_shell (renders <div id="app">)
│
└── static/
    ├── pwa/                                # Currently empty — icons served dynamically
    │                                       # via /andykanoz_purchase_mobile/icon.svg
    └── src/
        ├── js/
        │   ├── _pre_load.js               # EMPTY STUB — DO NOT DELETE, not referenced in manifest
        │   ├── main.js                    # Bootstrap: registry patches + makeEnv + App.mount
        │   ├── purchase_mobile_app.js     # Root component (list ↔ editor router)
        │   ├── services/
        │   │   └── rpc_service.js         # fetch-based JSON-RPC wrapper
        │   └── components/
        │       ├── po_list.js             # Draft PO browser
        │       ├── po_editor.js           # Core editor (save/confirm/delete)
        │       ├── vendor_picker.js       # Custom autocomplete
        │       ├── product_picker.js      # Search modal
        │       ├── line_card.js           # Editable line card
        │       └── qty_stepper.js         # − N + control
        ├── xml/
        │   ├── purchase_mobile_app.xml    # Root template (view switching)
        │   └── components/
        │       ├── po_list.xml
        │       ├── po_editor.xml
        │       ├── vendor_picker.xml
        │       ├── product_picker.xml
        │       ├── line_card.xml
        │       └── qty_stepper.xml
        └── scss/
            ├── purchase_mobile.scss        # Phase 3 base styles
            ├── purchase_mobile_4b.scss     # Phase 4b additions
            └── purchase_mobile_6.scss      # Phase 6 additions
```

**Asset bundle section of `__manifest__.py`:**

```python
'assets': {
    'web.assets_frontend': [
        'andykanoz_purchase_mobile/static/src/scss/**/*.scss',
        'andykanoz_purchase_mobile/static/src/js/services/**/*.js',
        'andykanoz_purchase_mobile/static/src/js/components/**/*.js',
        'andykanoz_purchase_mobile/static/src/js/purchase_mobile_app.js',
        'andykanoz_purchase_mobile/static/src/js/main.js',
        'andykanoz_purchase_mobile/static/src/xml/**/*.xml',
    ],
},
```

Do **NOT** use `('prepend', ...)` or `('include', 'web.assets_frontend')` — both broke mount in prior attempts. See §3.

---

## 3. Hard-Won Lessons (Phase 3 Debugging Saga)

Phase 3 took ~8 debug sessions to get right. These are the non-obvious landmines. Future AI sessions **must** not relearn these.

### 3.1 OWL mount pattern for Odoo 18 standalone frontend pages

Odoo 18 does **NOT** auto-wire the mount for custom standalone frontend pages. You must manually:

1. Build env with `makeEnv()` from `@web/env`
2. Run `await startServices(env)` from `@web/env`
3. Pass the env to `new App(Component, { env, getTemplate, translateFn, dev, props, ... })` from `@odoo/owl`
4. Call `await app.mount(rootEl)`

**Do NOT use:**
- `mount()` directly from `@odoo/owl` without env → hangs silently, no error, no resolution
- `templates` import from `@web/core/assets` → this does NOT exist in Odoo 18, use `getTemplate` from `@web/core/templates` instead
- `mountComponent()` from `@web/env` → helpful but collides with createPublicRoot's own startServices call (see §3.2)

### 3.2 The createPublicRoot DuplicatedKey race

On any frontend page with `@website` installed (which is what gets assets_frontend), `@website/js/content/website_root_instance` auto-runs `createPublicRoot()` during `whenReady`. That calls `startServices(env)` which registers components into `main_components` and `user_menuitems` registries. When our own mount also runs `startServices`, both calls race on `.add()` and throw `DuplicatedKeyError`.

**The fix (implemented in `main.js`):** Patch the `.add()` method of `main_components` and `user_menuitems` category instances (NOT `Registry.prototype` — patching the prototype breaks Odoo startup because some internal `.add()` calls legitimately rely on throwing). The patches swallow duplicate-key errors only; other errors still propagate. First registration wins.

```javascript
// From main.js — DO NOT DELETE OR INLINE INTO A SEPARATE FILE
function tolerantAddPatch(categoryKey) {
    const cat = registry.category(categoryKey);
    const originalAdd = cat.add.bind(cat);
    cat.add = function patchedAdd(key, value, options = {}) {
        try {
            return originalAdd(key, value, options);
        } catch (e) {
            if (/already exists|DuplicatedKey/i.test((e && e.message) || "")) {
                return cat;
            }
            throw e;
        }
    };
}
tolerantAddPatch("main_components");
tolerantAddPatch("user_menuitems");
```

If you ever see a `DuplicatedKeyError` from another category, just add it to the list.

### 3.3 The `_pre_load.js` ghost

There is an EMPTY file at `static/src/js/_pre_load.js`. It is **not** referenced in the manifest. **Do not delete it** — the file being present but unreferenced matches no glob, so it does nothing. But if some future `js/*.js` glob gets added, it might get picked up and cause havoc. Leave as empty stub until someone has time to safely remove.

**Why it exists:** Earlier attempts tried to use it as a pre-load shim. Adding it as the first asset caused it to end up at byte position 0 of the bundle, BEFORE Odoo's module loader infrastructure. Result: `odoo is not defined` crash and broken bundle. The patches are now inlined into `main.js` instead.

### 3.4 Template loading gotchas

- `<t t-call-assets="web.assets_frontend"/>` **once only** at end of `<body>`. Splitting into two calls (head for CSS, body for JS) caused the bundle to initialize twice per page.
- Custom bundles (`andykanoz_purchase_mobile.assets_app` with `('include', 'web.assets_frontend')`) do NOT auto-register XML templates into the global template registry. Must extend `web.assets_frontend` directly.
- XML prop callbacks to child components must use `.bind` suffix: `<VendorPicker onSelect.bind="onVendorSelected"/>`. Inline arrow (`onSelect="(v) => this.onVendorSelected(v)"`) works in some OWL 2 versions but not reliably; `.bind` is canonical.

### 3.5 Prop type validation accepts null

If a prop can be null (e.g. `partner` that's unset for new POs, `poId` that's null for new PO), declare as `[Type, { value: null }]`:

```javascript
static props = {
    poId: { type: [Number, { value: null }], optional: true },
    partner: { type: [Object, { value: null }], optional: true },
};
```

A plain `{ type: Object }` rejects null and OWL will destroy the entire component tree with a cryptic "Invalid props" error.

### 3.6 Testing after file changes

**Workflow that reliably picks up JS/CSS/XML changes:**

```javascript
// In browser devtools console on any Odoo page:
await fetch('/web/dataset/call_kw', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({jsonrpc:'2.0', method:'call', params:{
        model:'ir.attachment', method:'regenerate_assets_bundles',
        args:[], kwargs:{}
    }})
});
```

For data file changes (`*.xml` in `data/` or `views/`), an **module upgrade** is required — `button_immediate_upgrade` via RPC or via Apps UI. Asset regeneration alone won't pick up view XML changes.

Cache behavior:
- Odoo deduplicates bundle content — if your change only affects an SCSS file and no JS factory changed, the bundle hash **may not change** even after regen. Force-delete the attachment if you suspect staleness:
  ```javascript
  // deletes all cached frontend bundle attachments
  await fetch('/web/dataset/call_kw', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({jsonrpc:'2.0', method:'call', params:{
          model:'ir.attachment', method:'search_unlink_bundle',
          args:[[['name','like','web.assets_frontend']]], kwargs:{}
      }})
  });
  ```
- Cloudflare Tunnel (`nitro.gopokaja.com`) caches aggressively. When testing, use a fresh incognito tab — the previous tab may hold OWL state from prior failed mounts that taints future tests.

---

## 4. Backend Reference

### 4.1 Models (Phase 2)

All three extend existing Odoo models, no new tables created.

```python
# models/purchase_order.py
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    x_created_via_mobile = fields.Boolean(default=False, copy=False, index=True)

# models/purchase_order_line.py
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    x_expected_expiry_date = fields.Date()

# models/product_template.py
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    x_requires_expiry = fields.Boolean(default=False)
```

### 4.2 Sequence

```xml
<!-- data/ir_sequence.xml -->
<record id="seq_andykanoz_purchase_mobile" model="ir.sequence">
    <field name="code">andykanoz.purchase.mobile</field>
    <field name="prefix">MP</field>
    <field name="padding">5</field>
</record>
```

Called in `api.py → po_save`:

```python
name = request.env['ir.sequence'].next_by_code('andykanoz.purchase.mobile')
```

### 4.3 JSON-RPC endpoints (7 total)

All at `/andykanoz_purchase_mobile/api/*`, `type='json'`, `auth='user'`.

| Endpoint | Purpose | Params |
|---|---|---|
| `vendors` | Search suppliers (name_search with `res_partner_search_mode='supplier'` context) | `query`, `limit` |
| `products/search` | Search by barcode/SKU/name + 3-tier price fallback if vendor_id given | `query`, `limit`, `vendor_id` |
| `pos/list` | List PO filtered by state | `state`, `mobile_only`, `limit` |
| `po/get` | Single PO full detail | `po_id` |
| `po/save` | Create new (MP00001 seq + x_created_via_mobile=True) OR update draft | `po_id` nullable, `vendor_id`, `lines` |
| `po/confirm` | Call `po.button_confirm()` | `po_id` |
| `po/delete` | Unlink draft PO | `po_id` |

All mutating endpoints guard `state != 'draft'` → return `{error: 'not_draft'}`.

### 4.4 Price three-tier fallback

In `api.py → _get_unit_price()`:
1. Most recent `purchase.order.line` for this product + vendor (state in purchase/done), ordered by create_date desc
2. `product.supplierinfo` (`seller_ids`) entry for this vendor
3. `product.standard_price`

Pattern inherited from `andykanoz_quick_purchase`.

### 4.5 `_has_product_expiry()` detection

```python
def _has_product_expiry(self):
    return 'use_expiration_date' in request.env['product.template']._fields
```

Used so the module degrades gracefully when `product_expiry` isn't installed. The `x_requires_expiry` custom flag on `product.template` is the fallback.

---

## 5. Frontend Architecture

### 5.1 Component tree

```
PurchaseMobileApp (root — list ↔ editor router)
├── [view=='list']
│   ├── "+ New Purchase Order" button
│   └── POList (draft PO browser)
│       └── (tap) → onPickOrder → openExistingEditor(order.id)
│
└── [view=='editor']
    └── POEditor (props: poId, onBack)
        ├── Header: back, ref, state+dirty-dot, delete, save
        ├── Error banner (on saveError)
        ├── VendorPicker (locked chip when vendorLocked)
        ├── LineCard[] (editable)
        │   ├── QtyStepper
        │   └── native <select>/<input type=date>
        ├── ProductPicker (modal, on showProductPicker)
        └── Footer: untaxed, total, Confirm button (if canConfirm)
```

### 5.2 Client-side state shape (POEditor)

```javascript
state = {
    loading: boolean,
    error: string | null,
    order: {
        id, name, state, stateLabel, partner, currency,
        createdViaMobile
    },
    lines: [{
        clientId,        // "cli-xxx" or "srv-<id>"
        serverId,        // purchase.order.line ID or null
        product, productQty, productUom, productPackaging,
        productPackagingQty, priceUnit, priceSubtotal,
        expectedExpiryDate, requiresExpiry,
        _packagings,     // Product's packaging options (for <select>)
        _uoms,           // Product's UoM options (for <select>)
    }],
    showProductPicker: boolean,
    saving, confirming, deleting: boolean,
    saveError: string | null,
    dirty: boolean,  // flipped by every mutation, cleared after save
}
```

`_packagings` and `_uoms` are populated at add-line time from the product/search response. When loading an existing PO, these are empty (only the already-selected uom is in `_uoms`), which means users can't swap UoM/packaging without first re-picking the product. This is a known limitation — a `products/detail` endpoint could be added to fetch these on demand.

### 5.3 Save flow (Phase 6)

1. User edits → every mutation sets `state.dirty = true`
2. User taps Save → `onSave()` calls `/api/po/save` with:
   - `po_id` (null for new PO)
   - `vendor_id`
   - `lines[]` — each line has `id` (null for new) plus all fields
3. Backend create-path: new `purchase.order` with MP00001 sequence, `x_created_via_mobile=True`, lines as `[(0, 0, vals)]` commands
4. Backend update-path: diff incoming line IDs vs existing, unlink removed, write updated, create new
5. Response is the same shape as `po/get` so client can replace local state via `_applyServerOrder()`
6. `dirty` cleared on success

### 5.4 Confirm flow

Only visible when `state.order.id && state.order.state === 'draft' && lines.length > 0 && !dirty`. Calls `po.button_confirm()` which runs standard Odoo validation (supplier info, uom, etc). On success, pops back to list (user shouldn't stay on a non-draft editor).

---

## 6. Open Issues / Known Limitations

| # | Issue | Severity | Notes |
|---|---|---|---|
| 1 | `_packagings` / `_uoms` empty on existing-PO load | Medium | Users can't change UoM/packaging without re-adding product. Needs `products/detail` endpoint. |
| 2 | No optimistic UI on save — full re-render after server response | Low | Fine for current use case (small teams). |
| 3 | Vendor change on existing PO discards all lines silently | Low | UI locks vendor after first line anyway. |
| 4 | No confirmation dialog before product-picker closes modal | Low | User can just tap outside to dismiss. |
| 5 | Phase 5 (expiry → stock.lot propagation) IMPLEMENTED but untested at receipt validation | Medium | See §10 — user should validate one receipt to confirm `stock.lot.expiration_date` actually gets set. |
| 6 | No PWA yet (Phase 7) | Low | controllers/pwa.py written. Pending user verification on actual phone install flow. |
| 7 | No barcode scanner yet (Phase 8) | Low | BarcodeScanner component done. Pending phone-camera verification. |

---

## 7. Next Phase Priority

Recommended sequence:

1. **User acceptance test of Phase 5** — create new PO via mobile with a perishable product (one with `use_expiration_date=True` or `x_requires_expiry=True`), set expiry date in LineCard, save, confirm, validate receipt in desktop Odoo, verify the resulting `stock.lot` has `expiration_date` matching what was entered.
2. **User acceptance test of Phase 7** — see §12 testing checklist below.
3. **User acceptance test of Phase 8** — see §13 testing checklist below. Requires Chrome Android — Safari iOS will hide the scan button.
4. **Polish backlog** (when bandwidth available):
   - Add `products/detail` endpoint so existing-PO edits can swap UoM/packaging (issue §6 #1)
   - Add settings page for `expiry_warning_days` (currently only via Settings → Technical → System Parameters)
   - Replace dynamic SVG icon with proper PNG raster icons if Andyka has a logo (PWA still works with SVG, but Android Adaptive Icon support is better with PNG)
   - Add `quagga2` or `zxing-js` fallback for browsers without native BarcodeDetector (currently Safari iOS has no scan button at all)

---

## 8. Phase 5 Implementation Notes (Expiry Propagation)

### What was added

**`models/stock_move_line.py`** — overrides `_action_done()` on `stock.move.line` to copy `purchase_line_id.x_expected_expiry_date` into the newly-created `stock.lot.expiration_date` when a receipt (or any move from a PO) is validated.

### Why `_action_done()` is the right hook

Odoo's flow when a receipt is validated:
1. User clicks Validate on `stock.picking`
2. Picking calls `_action_done()` on each `stock.move`
3. Move's `_action_done()` calls `_action_done()` on each `stock.move.line`
4. **Inside that call, lots get auto-created if tracking by lot/serial and no lot was provided**
5. After `_action_done()` returns, `move_line.lot_id` is populated

So the override:
- Captures `(move_line.id → expected_date)` BEFORE calling `super()` (because move lines can be merged/unlinked during `_action_done`)
- Calls `super()._action_done()` so Odoo creates the lot normally
- Re-browses the surviving move lines, walks `lot_id`, writes `expiration_date`

### Compatibility

- **`product_expiry` module installed**: `stock.lot.expiration_date` field exists. Our value overrides any compute that might have run (per-batch wins over product-default). Tested in code; user verification pending.
- **`product_expiry` NOT installed**: Field doesn't exist. The override detects this via `'expiration_date' not in stock.lot._fields` and silently skips propagation. The PO line's `x_expected_expiry_date` is still persisted (for reporting), just no downstream effect.

### Configurable warning threshold

The "near expiry" red badge threshold (default 60 days) is now read from `ir.config_parameter` key `andykanoz_purchase_mobile.expiry_warning_days`. Backend exposes it via `_get_expiry_warning_days()` helper, frontend captures it from response payloads on `po/get` and `products/search` (piggyback pattern — no dedicated config endpoint needed).

**To change the threshold**: Settings → Technical → System Parameters → search `andykanoz_purchase_mobile.expiry_warning_days` → edit value. Takes effect on next API response (no module upgrade needed).

### Edge cases handled in `_action_done` override

| Case | Behavior |
|---|---|
| Move line has no `purchase_line_id` (manual move, return, etc.) | Skipped — our mapping is empty for it |
| PO line has no `x_expected_expiry_date` | Skipped — nothing to copy |
| Move line has no `lot_id` after `super()` (tracking='none') | Skipped — nowhere to write |
| Move line gets merged/unlinked during `super()._action_done()` | `.exists()` check filters out dead records before write |
| `product_expiry` not installed | `'expiration_date' not in Lot._fields` check returns early |
| Lot already has correct `expiration_date` | Compared before write — no-op if same |

### Testing

```
1. Create a perishable product (set use_expiration_date=True, tracking=lot)
2. Open Purchase Mobile, create new PO, pick that product
3. In LineCard, see the date picker (because requiresExpiry=true)
4. Enter a date 30 days from today (should show red badge "· dekat"
   if expiry_warning_days >= 30)
5. Save → PO created with MP00xxx ref
6. Confirm → receipt auto-created
7. Open receipt in desktop Odoo → Validate
8. Open the resulting stock.lot → expiration_date should match
   what was entered in the mobile app's LineCard
```

---

## 9. Frontend Changes Made During Phase 5

These are minor UI/data-flow additions to support the configurable threshold:

- `po_editor.js`: added `state.expiryWarningDays` (default 60), populated by `loadExisting`, `_applyServerOrder`, and via `onConfigUpdate` callback from ProductPicker.
- `product_picker.js`: added `onConfigUpdate` prop. After every search response, calls `onConfigUpdate({expiryWarningDays})`. Bubble-up pattern — no dedicated config endpoint.
- `line_card.js`: added `expiryWarningDays` prop (default 60). Replaced hardcoded `60` in expiry badge classification with `this.props.expiryWarningDays`.
- `po_editor.xml`: passes `expiryWarningDays="state.expiryWarningDays"` to LineCard, `onConfigUpdate.bind="onConfigUpdate"` to ProductPicker.

---

## 10. Instructions for the Next AI Session

### If the user reports "something broke":

1. **Check bundle hash** in script tag: `document.querySelector('script[src*="assets_frontend"]').src`. If same as before your last change, regenerate assets bundle (see §3.6).
2. **Check for DuplicatedKeyError** in console. If a NEW category name shows up (not `main_components` or `user_menuitems`), add it to `tolerantAddPatch()` list in `main.js`.
3. **Check bundle first 80 chars** — should NOT start with `_pre_load.js` content. If it does, manifest regressed; ensure `_pre_load.js` is not listed and no `prepend` op is used.
4. **Test in fresh incognito tab**, not the same tab that had the error. OWL holds state across failed mounts.

### When adding a new component:

1. Follow the existing pattern: `components/foo.js` + `xml/components/foo.xml` (glob auto-picks them up).
2. Always declare props with explicit null tolerance if null is possible: `[Type, { value: null }]`.
3. Use `.bind` suffix for function props: `<Foo onBar.bind="onBar"/>`.
4. Flip `state.dirty = true` in any mutation handler so save/confirm guards work correctly.

### When adding a new endpoint:

1. Add to `controllers/api.py` inside the `PurchaseMobileApi` class.
2. Use `@http.route('/andykanoz_purchase_mobile/api/...', type='json', auth='user')`.
3. Guard state on mutating endpoints (`if po.state != 'draft': return {'error': 'not_draft'}`).
4. Return same shape as `po_get` for mutating endpoints so client can reuse `_applyServerOrder()`.
5. Log INFO line with `_logger.info("[purchase_mobile] ...")` for audit trail.

### When user says "lanjut" / "continue" and you're not sure what:

Ask. Don't guess. Previous sessions burned hours chasing the wrong fix by assuming intent.

---

## 12. Phase 7 Implementation Notes (PWA)

### What was added

- **`controllers/pwa.py`** — three HTTP endpoints:
  - `/andykanoz_purchase_mobile/manifest.json` — Web App Manifest, public auth, references the icon endpoint at 192px and 512px with `purpose: "any maskable"`
  - `/andykanoz_purchase_mobile/service-worker.js` — service worker source generated dynamically. SW caches the app shell HTML (network-first) and static assets (cache-first), passes through API calls (network-only).
  - `/andykanoz_purchase_mobile/icon.svg` — dynamic square SVG with dark-navy background and centered “P” glyph. Generated via Python string concat — no PIL/Cairo dependency.
- **`controllers/__init__.py`** — added `from . import pwa`.
- **`views/purchase_mobile_templates.xml`** — added to `<head>`:
  - `<link rel="manifest">` pointing to `/andykanoz_purchase_mobile/manifest.json`
  - iOS meta tags (`apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, `apple-mobile-web-app-title`, `apple-touch-icon`)
  - SW registration `<script>` at end of `<body>` using `window.addEventListener('load', ...)` with explicit scope.

### Why dynamic SVG icon (no PNG bundle)

Filesystem write tools available to the AI session can only emit text files; binary PNG generation would have required a build step or a checked-in PNG. Dynamic SVG keeps everything in Python, lets us tweak the design without rebuilding, and is supported by Chrome 79+ for PWA install. Tradeoff: Android Adaptive Icon support is slightly worse with SVG — if Andyka wants a polished icon later, replace `controllers/pwa.py:icon()` with a static-file route serving real PNG raster icons in `static/pwa/`.

### Cache-busting strategy

- `SW_VERSION = "v1"` constant at top of `controllers/pwa.py` controls the cache name (`andykanoz_purchase_mobile-v1`). Bump this string whenever the SW logic itself changes; the activate hook deletes any cache whose name doesn't match.
- The SW response itself uses `Cache-Control: no-cache, no-store, must-revalidate` so the browser always fetches a fresh SW source. Without this, a stale SW could persist indefinitely and defeat the cache-busting mechanism.
- Manifest uses `Cache-Control: public, max-age=3600` — 1 hour is a reasonable balance between change propagation and server load.
- Cloudflare Tunnel adds another layer of caching that can defeat all of the above. If a user reports stale SW after deploy, they may need to bust the Cloudflare cache (purge URL on dashboard) or wait for natural expiry.

### Scope contract

- SW path: `/andykanoz_purchase_mobile/service-worker.js` (served from app's URL prefix)
- Declared scope (in registration script + manifest): `/andykanoz_purchase_mobile/`
- The `Service-Worker-Allowed: /andykanoz_purchase_mobile/` response header is required because the SW is technically being asked to control a directory level above its own location — without this header, the browser would reject the registration with a scope error.

### Testing checklist (user verification needed)

```
1. Module upgrade (data file change in templates.xml requires upgrade,
   not just regen).
2. Regenerate assets bundles.
3. On Chrome Android, hard-reload nitro.gopokaja.com/andykanoz_purchase_mobile/app
   in fresh incognito (or clear site data first).
4. Open DevTools (chrome://inspect from desktop Chrome paired with phone
   via USB, or use the standalone Chrome remote debugging if available).
   Console should show: "[purchase_mobile] SW registered: /andykanoz_purchase_mobile/"
5. Tap the menu (⋮) → "Add to Home screen" should show. If it doesn't,
   open chrome://flags and check "Bypass user engagement checks" —
   normally Chrome requires the user to spend ~30s on the page before
   the install banner appears.
6. Tap install. App should now have a launcher icon labeled "Purchase".
7. Tap launcher icon. App should open in standalone mode (no address bar,
   no Chrome chrome). Status bar should be theme-color #1a2332.
8. Toggle airplane mode after first load. Reload the app — the SW should
   serve the cached app shell, then JSON-RPC calls fail gracefully
   (existing rpc_service error path).
```

### Edge cases handled

- **`navigator.serviceWorker` not supported** (very old browsers): the registration block is gated by `if ('serviceWorker' in navigator)`, so the page works fine without PWA features.
- **SW registration failure**: caught and logged as warning; the app still loads normally over the network.
- **Manifest fetch blocked by auth**: manifest endpoint uses `auth='public'` so even logged-out browsers can read it (required for the install prompt to appear).
- **iOS Safari**: doesn't read manifest.json the same way Chrome does, so we have iOS-specific meta tags. iOS PWA support is more limited (no install banner; user must use Share → Add to Home Screen), but the meta tags ensure the resulting standalone app behaves correctly.

---

## 13. Phase 8 Implementation Notes (Barcode Scanner)

### What was added

- **`static/src/js/components/barcode_scanner.js`** — new component. Full-screen camera overlay that detects barcodes via the native `BarcodeDetector` API and emits decoded values to its parent.
- **`static/src/xml/components/barcode_scanner.xml`** — template with topbar (close + torch toggle), video element, corner reticle, hint text, error fallback.
- **`static/src/scss/purchase_mobile_8.scss`** — styles for scanner overlay and the new scan button inside ProductPicker's search bar.
- **`product_picker.js`** — imports BarcodeScanner, adds `state.showScanner`, getter `scannerSupported`, methods `openScanner`, `closeScanner`, `onBarcodeDetected`, `_searchAndMaybeAutoPick`.
- **`product_picker.xml`** — wraps search input + new 📷 button in `.pm-modal-search-with-scan`. Renders `<BarcodeScanner>` overlay when `state.showScanner` is true.

### Why native `BarcodeDetector` (not zxing-js or quagga)

Chrome Android (which is what Andyka and team will use) has had `window.BarcodeDetector` natively since Chrome 83 (2020). It uses on-device hardware acceleration where available, runs at full frame rate, and has zero bundle size cost. The tradeoff is that Safari iOS doesn't expose any equivalent API (the OS has Vision framework but it's not bridged to web). For the Gopokaja team this is acceptable — they're on Android. If iOS support becomes important later, a JS-only library like `zxing-js/library` could be added as a fallback inside the `isSupported` check.

### Lifecycle and resource management

The scanner is mounted/unmounted on every open/close cycle, not kept alive in the background. This matters because:

- `getUserMedia` shows a camera-active indicator on Android. Leaving it open after the user has selected a product would be creepy.
- Active video tracks consume battery aggressively.
- The animation-frame polling loop runs continuously; pausing it via state isn't enough — the track itself must be stopped.

The `onWillUnmount` hook calls `_stop()` which cancels the requestAnimationFrame and stops every track on the MediaStream. Verified to release the camera (no Android indicator after close).

### Auto-pick behavior

When the scanner detects a barcode, the parent ProductPicker:

1. Stuffs the decoded text into the search input
2. Closes the scanner overlay
3. Triggers a search
4. **If exactly one result returns, auto-picks it and closes the modal**
5. Otherwise leaves the user on the results list

The one-result-auto-pick is the common case (a unique EAN-13 or SKU). Multiple results means an ambiguous/partial match — user disambiguates manually.

### Edge cases handled

| Case | Behavior |
|---|---|
| `BarcodeDetector` not available (iOS, Firefox) | Scan button is hidden via `t-if="scannerSupported"`. The text input still works as a manual barcode-entry fallback. |
| Camera permission denied | Error message shown in the viewport: "Tidak bisa akses kamera. Cek izin di browser." |
| Front camera returned instead of back (some devices ignore facingMode) | Accepted silently — better than failing outright. |
| Same barcode detected on consecutive frames | Suppressed via `_lastEmitted` cache; only fires `onDetect` once per unique value. |
| Detector throws transiently (frame not ready) | Caught and skipped — next animation frame retries. |
| Torch toggle fails (some devices report supported but reject constraint) | `torchAvailable` flipped to `false` so the button hides on persistent failure. |
| User taps scan, then closes app, then reopens via SW cache | onWillUnmount stops the stream cleanly; nothing leaks. |

### Format support

Detector requests these formats explicitly:

- **EAN-13 / EAN-8**: standard retail barcodes (most common in Indonesia)
- **UPC-A / UPC-E**: US retail (some imported products)
- **CODE-128**: warehouse / shipping labels
- **CODE-39**: legacy SKUs
- **QR**: modern internal codes

If the device's BarcodeDetector doesn't support all of these (Android's implementation varies), the constructor falls back to its native default set.

### Testing checklist (user verification needed)

```
1. Module upgrade (no data file changes this phase, but doesn't hurt)
2. Regenerate assets bundles
3. Hard reload on Chrome Android
4. Tap + New PO → pick vendor → + Tambah Produk
5. Look for 📷 camera button next to search input — should appear on
   Chrome Android, NOT on Safari iOS
6. Tap 📷 — browser asks for camera permission, grant it
7. Should see live camera viewfinder with corner reticle and "Arahkan
   kamera ke barcode produk" hint
8. If device has flashlight, 🔦 button should appear top-right
9. Aim at any retail product barcode (EAN-13)
10. Within ~1 second, scanner closes, search input fills with the
    decoded number, and search runs
11. If exactly one product matches, line is added immediately;
    otherwise user disambiguates from the list
12. Tap × to close scanner without scanning — camera light should
    turn off (verify on Android status bar / device indicator)
```

---

## 14. Phase 8b Implementation Notes (Packaging Barcode Auto-Select)

### Why this exists

Gopokaja's warehouse receives goods in mixed units — sometimes individual cans, sometimes whole boxes. A box label has its own barcode (e.g. "BOX-COKE-24" or a separate EAN) that maps to a `product.packaging` row in Odoo. Without this feature, scanning a box barcode would either fail (no `product.barcode` match) or pick the product but require manual entry of qty=24 and packaging select. Phase 8b makes "scan the box, get the box configuration" automatic.

### What was added

- **`controllers/api.py → products_search()`**:
  - Probes `product.packaging` for an exact `barcode` match in addition to the existing `product.product` search.
  - When matched, prepends the packaging's product to the result list (deduped) so it's first.
  - Adds `matched_packaging_id` field to each result — set to the packaging row id only on the matched product, `null` otherwise.
- **`static/src/js/components/po_editor.js → onProductPicked()`**:
  - When `product.matched_packaging_id` is set, finds the matching packaging in the product's `packagings` list and pre-selects it on the new line.
  - Sets `productPackagingQty = 1` (= 1 box scanned).
  - Sets `productQty = packaging.qty * 1` (= unit equivalent, e.g. 24 cans).
  - Without a match, behavior is unchanged from prior: pre-select first packaging if any, qty=1 unit.

### Pricing semantic (per V1 confirmation)

Uses Odoo's default packaging math: price stays per `product_uom` base unit. Subtotal = `priceUnit × productQty` = `priceUnit × (packaging.qty × packagingQty)`. So scanning a box of 24 with unit price Rp 5,000 gives subtotal Rp 120,000, which matches what the desktop Odoo PO form would compute. If a supplier ever quotes per-box pricing instead, that's a future special case (would need a `product.supplierinfo.price_box` field or similar).

### Edge cases handled

| Case | Behavior |
|---|---|
| Query exact-matches a packaging barcode but that product is unpurchasable (`purchase_ok=False`) | Skipped — product not added to results. The user sees an empty result and knows to investigate. |
| Query matches both a product barcode AND a packaging barcode (rare collision) | Both result rows still show; the packaging match takes priority position. The product is deduped via the `pkg_product \| (products - pkg_product)` set operation. |
| Multiple packagings have the same barcode (data error) | `search(..., limit=1)` picks one. The user can manually fix the data via desktop Odoo. |
| Packaging has barcode but `qty=0` (data error) | `(chosenPackaging.qty \|\| 1) * packagingQty` falls back to qty=1 instead of multiplying by zero. Frontend defensive default. |
| Existing PO line being edited — user changes packaging via select dropdown | Not affected by this phase. The select still works as before; this phase only changes the *initial* packaging set when adding a NEW line via scan. |
| `product.packaging` model not present (e.g. stock module variant) | Module won't load — `purchase` depends on `stock` which provides this model on Community 18. Not a real concern. |

### Auto-pick interaction with Phase 8 scanner

ProductPicker's `_searchAndMaybeAutoPick()` (Phase 8) closes the modal & adds line when search returns exactly one result. Combined with this phase:

- Scan box barcode → search returns 1 product (the one matched via packaging) → auto-pick fires → line added with packaging pre-selected and qty = packaging.qty. **Single tap, fully configured line.**
- Scan unit barcode → search returns 1 product → auto-pick fires → line added with default packaging (= first or none) and qty=1. Same as before.
- Scan ambiguous code that matches multiple products → user picks from list → same logic applies on tap.

### Testing checklist

```
Prep:
  1. In desktop Odoo, pick a product (e.g. Coca-Cola can) with use_packaging.
  2. Add a packaging row: name="Box 24", qty=24, barcode="BOX-COKE-24"
     (or any code your test scanner can read).
  3. Save the product.

Mobile test:
  4. Module upgrade + regen assets.
  5. Open Purchase Mobile → New PO → pick vendor.
  6. Tap + Tambah Produk → 📷 scan button.
  7. Scan the BOX barcode (BOX-COKE-24).
  8. Within ~1 sec: scanner closes, search auto-fills with the code,
     ONE result returns (the can product). Auto-pick fires.
  9. Verify the new line in editor:
     - Packaging dropdown should show "Box 24" SELECTED (not blank or first).
     - Qty should show 24.00 (not 1.00).
     - Subtotal should be priceUnit × 24.
  10. Save → confirm in desktop → verify the PO line in desktop has
      product_packaging_id set to the Box 24 packaging.

Regression test:
  11. Repeat steps 6-9 but scan the unit barcode instead.
  12. Should add the SAME product but with qty=1.00 and packaging blank
      (or first packaging selected, depending on the product).
```

---

## 15. Phase 8b+ Implementation Notes (UoM Dropdown Fix)

### Bug reported

User reported that the UoM dropdown on a line card "didn't work" when creating a new RFQ. After investigation, three related defects were found.

### Root causes

1. **`_uoms` array was too small.** The frontend was building it client-side as `[product.uom_id, product.uom_po_id].filter(Boolean)`. For most products `uom_id == uom_po_id`, so after dedupe the dropdown had exactly one option — nothing to choose between. The product's full UoM category was never queried.

2. **`po/get` shipped only the saved UoM.** When loading an existing draft PO, each line's `_uoms` was built as `[line.product_uom]`. So even after the user opened a draft, they couldn't switch UoM — dropdown was locked to the one already saved. Same issue applied to `_packagings` (was hardcoded `[]`).

3. **Template used `t-att-value` on `<select>`.** This sometimes worked, sometimes didn't, depending on whether the OWL diff applied the value before or after option DOM nodes were materialized. Combined with bug #1, the select looked frozen.

### Fixes applied

**Backend (`controllers/api.py`):**
- New helper `_serialize_uom_options(product)` returns all active UoMs sharing the product's UoM category. Falls back to `[uom_id, uom_po_id]` if category lookup is empty (defensive).
- `products_search` now includes `uom_options` per product.
- `po/get`'s line serializer now includes `uom_options` AND `packagings` (full list, not just the line's selected packaging) so dropdowns work on edit.

**Frontend (`po_editor.js`):**
- `onProductPicked()`: prefer `product.uom_options` from server, fall back to old client-side compute for safety.
- `_applyServerOrder()`: prefer `line.uom_options` and `line.packagings` from server over old empty/single-element arrays.

**Template (`line_card.xml`):**
- Removed `t-att-value` from `<select>` elements (UoM and Packaging selects).
- Changed `t-att-selected="uom.id === currentUomId"` to `t-att-selected="uom.id === currentUomId ? 'selected' : null"`. The boolean form sometimes rendered as `selected="false"` which browsers treat as truthy. The explicit `null` makes OWL omit the attribute entirely when not selected, which is the correct HTML behavior.

### How to verify the fix

```
1. Module upgrade + regen assets (backend changes require upgrade,
   not just regen).
2. Open mobile app → New PO → pick vendor → + Tambah Produk → search
   any product that has multiple UoMs in its category (e.g. anything
   in the "Unit" category will have at least Units, Dozens, Hundreds).
3. Tap the UoM dropdown — should now show ALL UoMs from that category,
   not just one. Tap a different one — it should change and persist
   when you tap Save.
4. Re-open the saved PO — dropdown should still offer all UoMs from
   the category, with the saved value pre-selected.
5. For Packaging dropdown: same flow, products with packagings should
   show all of them ("— tidak ada —" + each packaging row), and
   selection should persist through save / reload.
```

### Lesson learned (added to §3 hard-won lessons)

**OWL select binding gotcha.** Always use `t-att-selected="... ? 'selected' : null"` on `<option>` elements; never set `t-att-value` on the parent `<select>`. The boolean form `t-att-selected="someExpr"` can render as `selected="false"` which all browsers interpret as `selected=""` (truthy), causing the wrong option to appear pre-selected. The ternary with explicit `null` sidesteps this entirely.

---

## 11. Gopokaja Context (for reference)

- Small F&B business in Denpasar, Bali
- Products: Rice Bowl and similar F&B items sold via POS
- Andyka is owner + sole technical developer; team is very small
- Odoo 18 Community runs in Docker on Windows, publicly exposed via Cloudflare Tunnel (`nitro.gopokaja.com`)
- Addons folder: `D:\MyServer\Odoo18\Addons\`
- Odoo instance URL: `http://localhost:8018`
- Communication: Bahasa Indonesia primarily, technical terms in English

### Related modules Andyka has built (code reuse patterns)

- `andykanoz_quick_purchase` — custom OWL client action, barcode scanner (BarcodeDetector + torch), vendor autocomplete (mousedown pattern, `res_partner_search_mode='supplier'` context), price 3-tier fallback. **This module reuses several patterns from it.**
- `andykanoz_kitchen_notify` — PWA pattern (manifest, service worker, Cloudflare cache-bust via `?v=SW_VERSION`). Reference for Phase 7.
- `andykanoz_product_checker` — product scan + pricelist display, slide-in panel for mobile. Reference for any product-detail view if needed.
- `andykanoz_purchase_qty_fix` — lightweight JS-only focusin event delegation to auto-select numeric input contents.
- `andykanoz_pos_auto_mo` — auto-create Manufacturing Orders on POS payment.
- `andykanoz_profit_report` — custom report.

### User workflow preferences (learned across modules)

- Prefers full problem explanation BEFORE any code is written
- Prefers versioned handoff documents (`HANDOFF_V1.md`, `HANDOFF_V2.md`) — don't edit a V1, write a V2
- Uses explicit step-scoped confirmations when switching AI assistants
- Comfortable with technical detail; respond in Bahasa Indonesia with English technical terms

---

*End of HANDOFF V2*
