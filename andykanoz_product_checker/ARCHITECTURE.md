# Architecture Reference — `andykanoz_product_checker`

> **Purpose of this document:** A single reference that other Gopokaja
> modules (and future enhancements to this one) can rely on without
> re-reading the whole source. Every public model, RPC endpoint, client
> action, and integration seam is listed here with its exact signature.
>
> **Scope:** Odoo 18. Runs in Docker on Windows host. Accessible locally
> at `http://localhost:8018` and publicly via Cloudflare Tunnel at
> `www.gopokaja.com` / `nitro.gopokaja.com`.
>
> **Rule for changing this file:** When you add, rename, or remove a
> public RPC method / model field / state key / CSS class that another
> module relies on, update this document in the **same commit**. Treat
> everything under "PUBLIC API" as a stable contract.

---

## 1. Module overview

| Aspect | Value |
|---|---|
| Technical name | `andykanoz_product_checker` |
| Version | `18.0.1.0.0` |
| Category | `MyCustom/Modules` |
| Type | `application` (top-level menu) |
| Entry point | Client action `andykanoz_product_checker.ProductCheckerAction` |
| Route | `/odoo/action-<id>` → menu "Product Checker" |
| Primary model target | `product.template` (extended via `_inherit`) |
| Owned models | `product.checker.print.list`, `andykanoz_product_checker.saved_filter` |

### 1.1 Dependencies

```python
depends = [
    'base',
    'product',
    'stock',
    'website_sale',        # for is_published, public_categ_ids
    'point_of_sale',       # for available_in_pos
    'andykanoz_gemini_integration_auto_edit', # internal Gopokaja module
]
```

**If another module wants to reuse a feature here**, declare
`andykanoz_product_checker` in its own `depends` list.

### 1.2 File structure

```
andykanoz_product_checker/
├── __manifest__.py
├── README.md
├── ARCHITECTURE.md                 ← this file
├── controllers/
│   ├── __init__.py
│   └── main.py                     ← empty placeholder (all comms via ORM RPC)
├── models/
│   ├── __init__.py
│   ├── product_checker.py          ← extends product.template + print list model
│   ├── print_list.py               ← alternative print list model (legacy)
│   └── saved_filter.py             ← favorites (saved searches)
├── security/
│   └── ir.model.access.csv
├── static/
│   ├── description/icon.png
│   └── src/
│       ├── js/
│       │   ├── product_checker.js        ← main OWL component (~2300 lines)
│       │   ├── barcode_camera_widget.js  ← reusable field widget
│       │   └── zxing_barcode_polyfill.js ← BarcodeDetector polyfill for iOS
│       ├── scss/
│       │   └── product_checker.scss
│       └── xml/
│           ├── product_checker.xml
│           └── barcode_camera_widget.xml
└── views/
    ├── product_checker_menu.xml
    ├── product_checker_views.xml          ← client action record
    └── product_template_views.xml         ← injects barcode_camera widget on standard product form
```

---

## 2. PUBLIC API — Python (backend)

All methods below are `@api.model` unless noted. They are callable
from other modules via `self.env['model.name'].method_name(...)` and
from the frontend via ORM RPC (`this.orm.call(model, method, args)`).

### 2.1 Model: `product.template` (extended)

Extended in `models/product_checker.py` via `_inherit`.

#### Added fields read by this module (not newly created)
None — this module does NOT add new fields to `product.template`.
All toggles operate on existing standard/modular fields:
`sale_ok`, `purchase_ok`, `is_storable`, `is_published`, `available_in_pos`.

#### Public methods

##### `search_product_by_barcode(barcode, pricelist_id=None) → dict`
Main lookup used by the scanner input and history clicks.

**Search order:** exact barcode → exact default_code → variant barcode →
ilike name.

**Returns:**
```python
{'found': True, 'data': {...product info...}}
# or
{'found': False, 'searched': '<code>'}
```

##### `search_products_for_panel(query='', pricelist_id=None, offset=0, limit=50, filter_domain=None) → dict`
Paginated product list for the left-side drawer.

- `query` — free text matched ilike against `name`, `default_code`, `barcode`
- `pricelist_id` — optional; used to compute each product's `price`
- `offset`, `limit` — pagination (limit clamped 1–200, default 50)
- `filter_domain` — Python-literal domain string from `DomainSelectorDialog`
  (e.g. `"[('categ_id','in',[27])]"`). Combined with query using `AND`.

**Returns:**
```python
{
    'products': [ {id, name, default_code, barcode, image_url,
                   standard_price, price, qty_on_hand, uom_name,
                   currency_symbol, currency_position}, ... ],
    'total': int,
    'has_more': bool,
    'offset': int,
    'limit': int,
    'filter_count': int,  # leaf conditions in filter_domain, drives UI badge
}
```

##### `_get_checker_info(pricelist_id=None) → dict`
Private-by-convention (leading underscore) but used widely. Returns the
canonical serialisation of a `product.template` record for frontend
consumption. Safe to call from other modules.

**Returns keys:** `id, name, default_code, barcode, list_price,
standard_price, price, pricelist_name, qty_on_hand, uom_name, categ_id,
categ_name, image_url, is_published, sale_ok, purchase_ok, is_storable,
available_in_pos, public_categ_ids, currency_symbol, currency_position`.

##### `get_checker_config() → dict`
Returns bootstrap data needed when the client action mounts.

**Returns:**
```python
{
    'pricelists': [{id, name, currency_id}, ...],
    'default_pricelist_id': int | False,
    'categories': [{id, complete_name}, ...],   # product.category, limit 200
    'public_categories': [{id, name, display_name}, ...],
    'print_list': [...current user's print list items...],
}
```

##### `quick_create_from_checker(vals) → dict`
Create a product from the "not found → create" form.

**Input `vals`:** `{name, barcode, default_code, standard_price,
list_price, categ_id, is_published, public_categ_ids, pricelist_id,
pricelist_price}` — only `name` is required.

**Returns:** `{'success': bool, 'data': <_get_checker_info>, 'error': str}`.

##### `update_product_image(product_tmpl_id, image_base64) → dict`
Replaces `image_1920`. Returns cache-busted `image_url`.

##### `update_quantity_on_hand(product_tmpl_id, new_quantity) → dict`
Creates a `stock.quant` inventory adjustment in the company's main
warehouse, applies it, returns new `qty_available`.

##### `toggle_product_field(product_tmpl_id, field_name, value) → dict`
Whitelisted single-field setter for the inline toggles.

**Allowed fields:** `sale_ok`, `purchase_ok`, `available_in_pos`,
`is_storable`, `is_published`.

**Returns on failure for `is_storable=True`:**
```python
{'success': False, 'error': str, 'is_track_inventory': True}
```
The `is_track_inventory` flag is the signal for the frontend to open
the Duplicate & Archive recovery modal.

##### `duplicate_for_track_inventory(product_tmpl_id, pricelist_id=None) → dict`
Recovery flow when Track Inventory cannot be enabled on a product that
already has transactions.

**Behaviour (wrapped in `env.cr.savepoint()`):**
1. Clears `barcode` + `default_code` from the original
2. `copy()` the template with `is_storable=True`, transferring the
   identifiers and keeping the same name (no "(copy)" suffix)
3. Copies per-product pricelist items to the new record
4. Archives the original (`active=False`) — variants auto-archive

**Returns:** `{'success': bool, 'data': <_get_checker_info>, 'error': str}`.

##### `add_to_print_list(product_tmpl_id) → dict`
Idempotent. Returns `{success, already_exists, count, item}` where
`item` contains the fields needed to render a row.

##### `remove_from_print_list(product_tmpl_id) → dict`
Returns `{success, count}`.

##### `clear_print_list() → dict`
Returns `{success, count: 0}`.

##### `get_print_list_action() → dict`
Returns an Odoo action descriptor that opens the native
`product.label.layout` wizard pre-populated with the current user's list.

### 2.2 Model: `product.checker.print.list`

Per-user "to be printed" list. The canonical version of this model
lives in `models/product_checker.py`. A second file `models/print_list.py`
contains an alternative with slightly different method names — both
are loaded but the `product_checker.py` variant is the one driving
the UI today. Do not rely on `print_list.py` methods from other modules
until consolidated.

| Field | Type | Notes |
|---|---|---|
| `user_id` | m2o res.users | required, ondelete=cascade |
| `product_tmpl_id` | m2o product.template | required, ondelete=cascade |
| `company_id` | m2o res.company | only on `print_list.py` variant |

**SQL constraint:** `unique(user_id, product_tmpl_id)` — each user can
only have one row per product.

**Access (ir.model.access.csv):** group_user, full CRUD.

### 2.3 Model: `andykanoz_product_checker.saved_filter`

Per-user saved search definitions (Favorites).

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | Char | — | required |
| `user_id` | m2o res.users | current user | required, ondelete=cascade |
| `domain` | Text | `'[]'` | Python-literal domain string |
| `query` | Char | `''` | text typed in drawer search box when saved |
| `is_default` | Boolean | False | at most one per user (enforced by helper) |

**SQL constraint:** `unique(user_id, name)` — save-by-name is a proper
upsert; saving again with the same name overwrites.

**Order:** `is_default desc, name asc` — default always appears first.

#### Public methods

##### `get_saved_filters() → list[dict]`
Returns current user's filters as `[{id, name, domain, query, is_default}, ...]`.

##### `save_current_filter(name, domain, query='', is_default=False) → dict`
Upsert-by-name. If `is_default=True`, any other default for the user
is cleared first.

**Returns:** `{'success': bool, 'filter': {...}, 'error': str}`.

##### `delete_saved_filter(filter_id) → dict`
Silently ignores missing / foreign records. Returns `{'success': True}`.

##### `set_default_filter(filter_id) → dict`
Sets or clears the default flag. Pass `False`/`0` to clear.

##### `_ensure_single_default(user_id, keep_id=None)` (private)
Enforces at-most-one default per user. Called by the upsert and setter
methods.

---

## 3. Security (ACLs)

All models are accessible to `base.group_user` (all internal users) with
full CRUD. Users cannot see or modify other users' rows because every
method filters by `self.env.user.id` at the domain level — **never**
skip this filter when extending.

```
access_product_checker_print_list_user   → model_product_checker_print_list
access_product_checker_saved_filter_user → model_andykanoz_product_checker_saved_filter
```

---

## 4. Client action & menu

### 4.1 Client action
- **XML ID:** `andykanoz_product_checker.action_product_checker`
- **Tag:** `andykanoz_product_checker.ProductCheckerAction`
- **Target:** `current` (replaces main content area, not a dialog)
- **Registration:** `registry.category("actions").add(tag, Component)` in
  `product_checker.js`

### 4.2 Menu
- **XML ID:** `andykanoz_product_checker.menu_product_checker_root`
- Top-level menu named "Product Checker" with custom icon at
  `sequence=20`. Launches the client action.

### 4.3 Standard product form extension
`views/product_template_views.xml` injects `widget="barcode_camera"` on
the standard `product.template.form` `barcode` field. This makes the
camera-scanner widget available anywhere Odoo shows a product barcode.

---

## 5. Frontend — main OWL component

**Class:** `ProductCheckerAction` in
`static/src/js/product_checker.js` (~2300 lines).

**Template:** `andykanoz_product_checker.ProductCheckerPage` in
`static/src/xml/product_checker.xml`.

**Service dependencies injected via `useService`:** `orm`, `notification`,
`action`, `dialog`.

**Sub-components:** `SelectMenu` (inline autocomplete),
`DomainSelectorDialog` (custom filter modal).

### 5.1 Reactive state keys (public contract for extensions)

Grouped by concern. All live on `this.state = useState({...})`.

#### Search & current product
- `barcode` — text currently in search input
- `loading` — global loading flag (also reused by modals)
- `product` — object from `_get_checker_info`, or `null`
- `notFound` — boolean, true when last search had no match
- `searchedCode` — the code that was searched (shown on "not found")

#### Pricelist
- `pricelists` — array from `get_checker_config`
- `selectedPricelistId` — active pricelist id (null = default list price)

#### History sidebar (right)
- `history` — last 20 items (in-memory only, not persisted)
- `sidebarOpen` — mobile drawer state

#### Print list
- `printList` — array of `{id, name, default_code, barcode, image_url}`
- `autoAddToPrintList` — bool; if true, every successful search auto-adds
- `printListPanelOpen` — modal state

#### Camera scanner
- `showCameraModal`, `cameraMode` (`"once"` | `"continuous"`),
  `cameraFacing` (`"environment"` | `"user"`), `cameraError`,
  `lastDetected`, `torchSupported`, `torchOn`, `scannedCount`,
  `lastScanStatus` (`"success"` | `"duplicate"` | `"notfound"` | `null`),
  `lastScanMessage`

#### Quick-create form
- `showCreateForm`, `createForm: {name, barcode, default_code,
  standard_price, list_price, categ_id, is_published, public_categ_ids,
  pricelist_id, pricelist_price}`

#### Inline edit modals
- `showImageUpdateModal`
- `showCostUpdateModal` + `editCostValue`
- `showStockUpdateModal` + `editStockValue`
- `showTrackInventoryErrorModal` + `trackInventoryErrorMessage`

#### Meta-area autocompletes
- `metaCategQuery`, `metaCategSuggestions`, `metaCategActiveSuggestion`,
  `showMetaCategDropdown`, `metaCategShowQuickCreate`
- `pubCategQuery`, `pubCategSuggestions`, `pubCategActiveSuggestion`,
  `showPubCategDropdown`

#### Product List drawer (left)
- `productListOpen` — drawer visibility
- `productListQuery` — text filter (preserved across close/open)
- `productListItems` — loaded rows
- `productListTotal` — total count matching current filter
- `productListOffset` — next-page cursor
- `productListLoading`
- `productListInitialized` — true after first successful load

#### Custom Filter (Domain Selector)
- `productListDomain` — Python-literal domain string (default `"[]"`)
- `productListFilterCount` — leaf count, drives the badge

#### Saved favorites
- `savedFilters` — array of `{id, name, domain, query, is_default}`
- `activeSavedFilterId` — id of the currently applied favorite (`null`
  = none)
- `favoritesDropdownOpen`
- `saveFilterFormOpen`
- `saveFilterName`, `saveFilterIsDefault`
- `savedFiltersLoaded` — true after first fetch; default auto-applies
  only once per session

#### Inline option toggles
- `savingOptionField` — field name currently being saved (disables its
  switch)

### 5.2 Public methods on `ProductCheckerAction`

The following methods are stable entry points — extensions can patch or
call them via `patch(ProductCheckerAction.prototype, ...)`. Names are
grouped by feature area.

#### Search
- `searchProduct(overrideBarcode=null)` — main lookup
- `resetSearch()`, `newScan()` — input management
- `addToHistory(productData)` — history management
- `onBarcodeInput`, `onBarcodeKeydown`, `onPricelistChange`

#### History sidebar
- `toggleSidebar`, `closeSidebar`, `clearHistory`, `onHistoryClick`

#### Print list
- `addToPrintList(silent=false)`, `removeFromPrintList(productId)`,
  `clearPrintList`, `printLabels`
- `togglePrintListPanel`, `closePrintListPanel`, `isInPrintList(id)`
- `onAutoAddToggle`

#### Camera scanner
- `openCameraOnce`, `openCameraContinuous`, `closeCameraScanner`
- `toggleTorch`, `switchCamera`
- Internal: `_startCamera`, `stopCamera`, `_scanFrame`,
  `_onBarcodeDetected`, `_scanAndAddToPrintList`,
  `_detectTorchCapability`, `_playScanSound`

#### Image update
- `openImageUpdateDialog`, `closeImageUpdateModal`
- `chooseFromGallery`, `takePhoto`
- `onImageFileSelected`, `autoWhiteBackground`
- Internal: `_processImageFile`

#### Cost / Stock inline edit
- `onKpiAction(actionType)` — dispatcher for `'price' | 'cost' | 'stock'`
- `closeCostUpdateModal`, `saveCostUpdate`
- `closeStockUpdateModal`, `saveStockUpdate`

#### Quick-create form
- `openCreateForm`, `cancelCreateForm`, `submitCreateForm`
- Input handlers: `onNameInput`, `onBarcodeFormInput`,
  `onDefaultCodeInput`, `onStandardPriceInput`, `onListPriceInput`,
  `onPricelistPriceInput`, `onIsPublishedToggle`
- `onCategorySelect`, `onCreateFormPricelistSelect`,
  `onPublicCategoriesSelect`

#### Meta-area autocompletes
- Category: `onMetaCategoryInput`, `onMetaCategoryFocus`,
  `onMetaCategoryBlur`, `onMetaCategoryKeydown`, `selectMetaCateg`,
  `toggleMetaCategoryDropdown`, `onMetaCategorySelect`,
  `quickCreateCategory`, `openCreateCategory`
- Public (ecommerce) category: `onPubCategContainerClick`,
  `onPubCategInput`, `onPubCategFocus`, `onPubCategBlur`,
  `onPubCategKeydown`, `selectPubCateg`, `removePubCateg`,
  `quickCreatePubCateg`, `togglePubCategDropdown`

#### Product List drawer
- `toggleProductList` (async — also bootstraps favorites)
- `closeProductList`
- `onProductListQueryInput` (debounced 300ms)
- `loadProductList(reset=false)`
- `loadMoreProducts`
- `onProductListItemClick(item)`

#### Custom Filter
- `openFilterDialog` — opens `DomainSelectorDialog`
- `_applyFilterDomain(newDomain)` — normalises the various return
  formats (string / array / object) into a Python-literal string
- `clearFilterDomain`
- `clearAllFiltersAndQuery` — clears filter + text query + active favorite

#### Inline product toggles
- `onProductFieldToggle(fieldName, ev)` — optimistic UI, auto-revert on
  failure, opens TI modal on `is_storable=true` error
- `closeTrackInventoryErrorModal`, `duplicateAndArchive`

#### Saved favorites
- `loadSavedFilters({applyDefault=false})`
- `toggleFavoritesDropdown`, `toggleSaveFilterForm`
- `onSaveFilterNameKeydown`, `saveCurrentFilter`
- `applySavedFilter(filter)`, `deleteSavedFilter(filter)`

#### Utilities
- `formatPrice(price, product)` — respects `currency_symbol` /
  `currency_position`
- `openProductForm()` — jumps to standard product form
- `openCategoryForm()` — opens category in modal form

### 5.3 Lifecycle hooks
- `onMounted` → `loadConfig()`, `focusInput()`, registers a
  `document` click listener for favorites click-outside
- `onWillUnmount` → `stopCamera()`, removes the click listener

### 5.4 Instance variables (non-reactive)
Stored directly on `this` — not in `state` because they hold DOM objects
or timers that shouldn't trigger re-renders.

- `_audioCtx` — Web Audio context for scan sounds
- `_cameraStream`, `_cameraTrack`, `_barcodeDetector`
- `_scanLoopHandle` — `setInterval` handle
- `_lastScannedCode`, `_lastScannedAt` — anti-duplicate guard
- `_debounceTimer`, `_metaCategDebounce`, `_pubCategDebounce`,
  `_productListDebounceTimer`
- `_onDocumentClick` — registered document listener

---

## 6. Reusable frontend components

### 6.1 `BarcodeCameraField` widget
**File:** `static/src/js/barcode_camera_widget.js`
**Registration:** field registry, name `barcode_camera`
**Usage:** set `widget="barcode_camera"` on any `Char` field.

Already applied by this module to the standard `product.template.barcode`
field (see `views/product_template_views.xml`). Other modules can reuse
it on any text field that stores a barcode.

### 6.2 `BarcodeDetector` polyfill
**File:** `static/src/js/zxing_barcode_polyfill.js`
**Export:** `ensureBarcodeDetector()` — returns `Promise<boolean>`, loads
the ZXing polyfill on demand for browsers that lack native support
(Safari pre-17, older iOS).

---

## 7. CSS / SCSS classes (public selectors)

Every selector below is scoped under `.o_product_checker_page` so
styles from other modules won't leak in. Listed here so other modules
can (a) style overrides or (b) copy the pattern.

### 7.1 Layout
- `.o_product_checker_page` — root
- `.o_pc_topbar` — top bar containing search, pricelist, buttons
- `.o_pc_body` — main content row (drawer + main + sidebar)
- `.o_pc_main` — main product display area

### 7.2 Search & buttons
- `.o_pc_search_box`
- `.o_pc_barcode_input`
- `.o_pc_search_btn`, `.o_pc_newscan_btn`, `.o_pc_camera_once_btn`,
  `.o_pc_camera_continuous_btn`, `.o_pc_reset_btn`
- `.o_pc_pricelist_selector`
- `.o_pc_auto_add` — auto-add-to-print switch
- `.o_pc_history_toggle`, `.o_pc_history_badge`

### 7.3 Product card
- `.o_pc_product_card`, `.o_pc_product_image`, `.o_pc_product_info`,
  `.o_pc_product_name`, `.o_pc_product_meta`, `.o_pc_meta_item`,
  `.o_pc_label`, `.o_pc_value`
- `.o_pc_price_stock_grid`, `.o_pc_kpi`, `.o_pc_kpi_price`,
  `.o_pc_kpi_cost`, `.o_pc_kpi_stock`, `.o_pc_kpi_label`,
  `.o_pc_kpi_value`, `.o_pc_kpi_action_btn`, `.o_pc_out_of_stock`
- `.o_pc_image_actions`, `.o_pc_update_image_btn`, `.o_pc_auto_bg_btn`
- `.o_pc_actions`

### 7.4 Inline product option toggles
- `.o_pc_options_row`, `.o_pc_options_label`, `.o_pc_options_grid`,
  `.o_pc_option_item`

### 7.5 Meta autocompletes
- `.o_pc_meta_autocomplete`, `.o_pc_meta_ac_input`,
  `.o_pc_meta_ac_dropdown`, `.o_pc_meta_ac_item`
- `.o_pc_m2m_tags`, `.o_pc_m2m_container`, `.o_pc_m2m_tag`,
  `.o_pc_m2m_tag_label`, `.o_pc_m2m_tag_delete`, `.o_pc_m2m_input`,
  `.o_pc_m2m_arrow`, `.o_pc_m2m_dropdown`, `.o_pc_m2m_dropdown_item`

### 7.6 History sidebar (right, mobile drawer)
- `.o_pc_sidebar`, `.o_pc_sidebar_open`, `.o_pc_sidebar_header`,
  `.o_pc_sidebar_close`, `.o_pc_sidebar_backdrop`,
  `.o_pc_backdrop_visible`
- `.o_pc_history_list`, `.o_pc_history_empty`, `.o_pc_history_item`,
  `.o_pc_history_image`, `.o_pc_history_info`, `.o_pc_history_name`,
  `.o_pc_history_code`, `.o_pc_history_meta`, `.o_pc_history_price`,
  `.o_pc_history_stock`, `.o_pc_history_time`

### 7.7 Product List drawer (left, desktop-only)
- `.o_pc_productlist_toggle`
- `.o_pc_product_list_sidebar`, `.o_pc_product_list_open`,
  `.o_pc_product_list_header`, `.o_pc_product_list_close`,
  `.o_pc_product_list_search`, `.o_pc_product_list_body`,
  `.o_pc_product_list_empty`, `.o_pc_product_list_loading`,
  `.o_pc_product_list_item`, `.o_pc_product_list_image`,
  `.o_pc_product_list_info`, `.o_pc_product_list_name`,
  `.o_pc_product_list_code`, `.o_pc_product_list_meta`,
  `.o_pc_product_list_price`, `.o_pc_product_list_cost`,
  `.o_pc_product_list_stock`, `.o_pc_product_list_loadmore`,
  `.o_pc_product_list_footer_info`

### 7.8 Custom Filter (Domain Selector)
- `.o_pc_productlist_filter_btn`, `.o_pc_has_filters`,
  `.o_pc_productlist_filter_badge`
- `.o_pc_productlist_chip_summary`, `.o_pc_chip_clear`

### 7.9 Favorites dropdown
- `.o_pc_favorites_wrap`, `.o_pc_productlist_favorites_btn`,
  `.o_pc_fav_active`, `.o_pc_favorites_dropdown`,
  `.o_pc_fav_header`, `.o_pc_fav_empty`,
  `.o_pc_fav_item`, `.o_pc_fav_selected`, `.o_pc_fav_check`,
  `.o_pc_fav_name`, `.o_pc_fav_default_badge`, `.o_pc_fav_delete`,
  `.o_pc_fav_divider`, `.o_pc_fav_save_toggle`, `.o_pc_fav_save_form`,
  `.o_pc_fav_save_title`

### 7.10 Print list modal
- `.o_pc_printlist_toggle`, `.o_pc_printlist_badge`,
  `.o_pc_printlist_backdrop`, `.o_pc_printlist_modal`,
  `.o_pc_printlist_header`, `.o_pc_printlist_close`,
  `.o_pc_printlist_body`, `.o_pc_printlist_empty`,
  `.o_pc_printlist_item`, `.o_pc_printlist_image`,
  `.o_pc_printlist_info`, `.o_pc_printlist_name`,
  `.o_pc_printlist_code`, `.o_pc_printlist_footer`

### 7.11 Camera & update modals
- `.o_pc_camera_backdrop`, `.o_pc_camera_modal`, `.o_pc_camera_header`,
  `.o_pc_camera_close`, `.o_pc_camera_video_wrap`,
  `.o_pc_camera_overlay`, `.o_pc_camera_target`,
  `.o_pc_camera_flash`, `.o_pc_camera_toast`, `.o_pc_camera_status`,
  `.o_pc_camera_controls`, `.o_pc_camera_switch_btn`
- `.o_pc_imgupdate_backdrop`, `.o_pc_imgupdate_modal`,
  `.o_pc_imgupdate_options`, `.o_pc_imgupdate_option`
- `.o_pc_track_inventory_modal`, `.o_pc_ti_error_message`,
  `.o_pc_ti_explainer`, `.o_pc_ti_steps`

### 7.12 Barcode camera field widget
- `.o_field_barcode_camera`, `.o_barcode_camera_btn`

---

## 8. Feature map

A concise "what's here, where it lives" index for feature spelunking.

| Feature | Backend | Frontend methods | State keys | Styling |
|---|---|---|---|---|
| Scan / search product | `search_product_by_barcode` | `searchProduct`, `onBarcodeInput`, `onBarcodeKeydown` | `barcode`, `product`, `notFound`, `searchedCode` | `.o_pc_search_box`, `.o_pc_product_card` |
| Pricelist switch | — (read-only) | `onPricelistChange` | `pricelists`, `selectedPricelistId` | `.o_pc_pricelist_selector` |
| Scan history | — (in-memory) | `addToHistory`, `onHistoryClick`, `clearHistory` | `history`, `sidebarOpen` | `.o_pc_sidebar`, `.o_pc_history_*` |
| Quick-create product | `quick_create_from_checker` | `openCreateForm`, `submitCreateForm`, form input handlers | `showCreateForm`, `createForm` | `.o_pc_create_form` |
| Update image | `update_product_image` | `openImageUpdateDialog`, `onImageFileSelected` | `showImageUpdateModal` | `.o_pc_imgupdate_*` |
| Update cost / stock | `update_quantity_on_hand`, `product.template.write` | `onKpiAction`, `saveCostUpdate`, `saveStockUpdate` | `showCostUpdateModal`, `showStockUpdateModal` | `.o_pc_kpi_*` |
| Inline field toggles | `toggle_product_field` | `onProductFieldToggle` | `savingOptionField` | `.o_pc_options_row`, `.o_pc_option_item` |
| Track Inventory recovery | `duplicate_for_track_inventory` | `duplicateAndArchive`, `closeTrackInventoryErrorModal` | `showTrackInventoryErrorModal`, `trackInventoryErrorMessage` | `.o_pc_track_inventory_modal` |
| Print list | `add_to_print_list`, `remove_from_print_list`, `clear_print_list`, `get_print_list_action` | `addToPrintList`, `removeFromPrintList`, `clearPrintList`, `printLabels`, `togglePrintListPanel` | `printList`, `printListPanelOpen`, `autoAddToPrintList` | `.o_pc_printlist_*` |
| Camera scanner (once / continuous) | — (reuses `search_product_by_barcode`) | `openCameraOnce`, `openCameraContinuous`, `_scanFrame`, `toggleTorch`, `switchCamera` | `showCameraModal`, `cameraMode`, `cameraFacing`, `torchSupported`, `torchOn`, `scannedCount` | `.o_pc_camera_*` |
| Meta-area category autocomplete | `product.category.create`, `product.template.write` | `onMetaCategory*`, `selectMetaCateg`, `quickCreateCategory` | `metaCateg*` | `.o_pc_meta_autocomplete`, `.o_pc_meta_ac_*` |
| Ecommerce category multi-tag | `product.public.category.create`, `product.template.write` | `onPubCateg*`, `selectPubCateg`, `removePubCateg`, `quickCreatePubCateg` | `pubCateg*` | `.o_pc_m2m_*` |
| Product List drawer | `search_products_for_panel` | `toggleProductList`, `loadProductList`, `loadMoreProducts`, `onProductListItemClick`, `onProductListQueryInput` | `productList*` | `.o_pc_product_list_sidebar`, `.o_pc_productlist_toggle` |
| Custom Filter (Domain Selector) | `search_products_for_panel` (via `filter_domain` kwarg) | `openFilterDialog`, `_applyFilterDomain`, `clearFilterDomain`, `clearAllFiltersAndQuery` | `productListDomain`, `productListFilterCount` | `.o_pc_productlist_filter_btn`, `.o_pc_productlist_chip_summary` |
| Saved favorites | `andykanoz_product_checker.saved_filter.*` methods | `loadSavedFilters`, `toggleFavoritesDropdown`, `toggleSaveFilterForm`, `saveCurrentFilter`, `applySavedFilter`, `deleteSavedFilter` | `savedFilters`, `activeSavedFilterId`, `favoritesDropdownOpen`, `saveFilterFormOpen`, `saveFilterName`, `saveFilterIsDefault`, `savedFiltersLoaded` | `.o_pc_favorites_*`, `.o_pc_productlist_favorites_btn`, `.o_pc_fav_*` |

---

## 9. Extension recipes

How other modules should extend this one. Always declare
`andykanoz_product_checker` in the dependent module's `depends`.

### 9.1 Add a field to the returned product info
Override `_get_checker_info`:

```python
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_checker_info(self, pricelist_id=None):
        info = super()._get_checker_info(pricelist_id=pricelist_id)
        info['my_custom_field'] = self.my_custom_field
        return info
```

Then read `state.product.my_custom_field` in your OWL patch.

### 9.2 Add a new RPC method
Inherit the model and add `@api.model` methods. They become callable
from `this.orm.call('product.template', 'my_method', args)` in any
frontend code.

### 9.3 Patch the frontend component
```javascript
import { patch } from "@web/core/utils/patch";
import { ProductCheckerAction } from "@andykanoz_product_checker/product_checker";

patch(ProductCheckerAction.prototype, {
    async searchProduct(overrideBarcode = null) {
        await super.searchProduct(overrideBarcode);
        // your extra logic
    },
});
```

### 9.4 Add a new toggle to the inline options row
1. Add the field name to `_CHECKER_TOGGLE_ALLOWED_FIELDS` in
   `product_checker.py` (requires a Python override).
2. Add the field to the `_get_checker_info` return dict.
3. Patch the XML template (inherit `ProductCheckerPage` via OWL).
4. No new JS method needed — `onProductFieldToggle` already handles
   any whitelisted field name.

### 9.5 Add a new filter preset
Favorites are stored per-user by design, so a "preset" ships as a
record of `andykanoz_product_checker.saved_filter` created in a
`data/` XML file (with `noupdate="1"`). The user can then delete /
override it.

---

## 10. Conventions & invariants

Things that MUST stay true when extending. Breaking these will
silently break behaviour users rely on.

1. **`_CHECKER_TOGGLE_ALLOWED_FIELDS` is a whitelist.** Every inline
   toggle field must be listed here. Unlisted field names are rejected
   by `toggle_product_field` with `"Field not allowed"`.
2. **`is_storable=True` errors open the TI modal.** The
   `is_track_inventory: True` flag in the error response is the
   one-way signal. Don't set it for any other failure mode.
3. **Domain strings, not lists.** `productListDomain` is always stored
   as a **Python-literal string** (e.g. `"[('sale_ok','=',True)]"`).
   This makes it trivial to persist / JSON-serialise. `_applyFilterDomain`
   handles the conversion from whatever `DomainSelectorDialog` returns.
4. **`safe_eval` has no `datetime` module.** Odoo 18 hardened
   `safe_eval` to reject raw module injection. If you need date
   expressions, use `odoo.tools.safe_eval.datetime` (a pre-wrapped
   module) — not `import datetime`.
5. **Every user-scoped model query MUST filter by `self.env.user.id`.**
   Don't trust the ACL alone — a bug in ACL or group membership could
   leak cross-user data.
6. **Instance variables for DOM / timers, state for reactive data.**
   Camera streams, `setInterval` handles, and debounce timers go on
   `this._x`. Anything the template reads goes in `this.state`.
7. **Drawer preserves query & filter on close.** `closeProductList`
   must NOT reset `productListQuery`, `productListDomain`, or
   `productListItems`. This is an intentional UX promise.
8. **Favorites default auto-applies once per session.** The guard is
   `savedFiltersLoaded`. Don't re-trigger default application when the
   drawer is re-opened — the user may have cleared the filter on
   purpose.
9. **Anti-duplicate scan guard: 2 seconds per code.** Continuous camera
   mode ignores the same barcode within 2000ms of the previous
   detection. Adjust only in `_scanFrame`; other timings should not
   diverge.
10. **Camera widget XML ID is part of the public contract.**
    `andykanoz_product_checker.BarcodeCameraField` template name — do
    not rename without updating consumers.

---

## 11. Known gotchas

Things that already bit us (or almost did) during development. Read
this before trying to reproduce similar patterns.

### 11.1 `safe_eval` in Odoo 18 rejects raw Python modules
Passing `{'datetime': datetime, 'relativedelta': relativedelta}` to
`safe_eval(...)` throws `"Module X can not be used in evaluation
contexts"`. Fix: use `odoo.tools.safe_eval.datetime` (pre-wrapped) or
just don't inject those modules if the callers never produce date
expressions. Currently `search_products_for_panel` passes only
`{True, False, None}` which is enough for `DomainSelectorDialog`
output.

### 11.2 `DomainSelectorDialog` callback names vary by Odoo minor version
Some minor versions use `onConfirm`, others `onSelected`, others
`onClose`. `openFilterDialog` registers all of them + an `applied`
guard so exactly one fires. If the dialog stops applying filters after
an Odoo update, check which callback name is current.

### 11.3 `onConfirm` may pass string OR array OR object
`_applyFilterDomain` normalises all three shapes into a Python-literal
string. Don't assume a fixed shape.

### 11.4 OWL `t-on-change` with inline arrow handlers is buggy
Applies specifically to `<select>` elements with inline arrows —
compiler fails silently. Always use a named method: `t-on-change="onMyChange"`.

### 11.5 Service Worker scope needs trailing slash
Not a problem in this module (no SW here) but common across Gopokaja
modules — scope mismatch silently breaks caching.

### 11.6 `standard_price` is JSONB in Odoo 18
On `product_product`. `product.template.standard_price` is the
aggregated view. Always write to the template field, not the variant.

### 11.7 Cloudflare Tunnel aggressive JS caching
Use `?v=<VERSION>` on asset URLs to bust cache when deploying via
`nitro.gopokaja.com`. The backend is already served with
`?unique=<timestamp>` by Odoo itself, but custom assets loaded via
`<script src>` need manual busting.

### 11.8 Variants auto-archive with template
When `active=False` on a `product.template`, its variants
(`product.product`) are auto-archived. Don't iterate and archive
manually — it's redundant and slower.

### 11.9 `image_1920` vs `image_1024` vs `image_128`
Write to `image_1920` (the source). Read from `image_1024` for the
card display, `image_128` for the list / sidebar. URLs include a
`?t=<timestamp>` suffix after updates to bust browser cache.

### 11.10 `point_of_sale` dependency is stricter than it looks
Adding `point_of_sale` to `depends` means the module can't install on
an Odoo instance without POS. If you need to deploy somewhere without
POS, make `available_in_pos` opt-in via `_fields` guard (already done
in `_get_checker_info` and `toggle_product_field`).

### 11.11 Filter input inside `input-group` needs explicit flex rules
Bootstrap's `.input-group` doesn't stretch nested custom wrappers by
default. See section 7 — the favorites wrap needs
`display: flex; align-items: stretch` plus `flex-wrap: nowrap` on the
group itself.

---

## 12. Roadmap / known TODOs

Track future enhancements here so other modules know what's planned
and can coordinate.

- [ ] **Unify print list models.** `models/product_checker.py` and
  `models/print_list.py` both define `product.checker.print.list`.
  The canonical one is in `product_checker.py`; delete or merge
  `print_list.py` once consumers are confirmed to all use the
  canonical methods.
- [ ] **Bulk inline edit for cost** from the drawer list. Hover-to-edit
  small input per row. Requires a new RPC
  `bulk_update_cost(product_tmpl_ids, new_cost)`.
- [ ] **Delete confirmation** for saved filters. Current behaviour
  deletes instantly on trash icon click — add a quick undo toast
  (5s) like Gmail.
- [ ] **Shared saved filters** (team-wide). Requires a second model
  `saved_filter_share` or an `is_shared` field with visibility logic.
  Currently scoped per-user only.
- [ ] **Date-based domain support.** If any future filter needs
  `create_date > context_today() - relativedelta(days=7)`, re-enable
  `safe_eval` module context using `odoo.tools.safe_eval.datetime` +
  `odoo.tools.safe_eval.relativedelta`.
- [ ] **Remove debug log lines.** `product_checker.py` still has INFO
  logs in `search_products_for_panel` that were added during filter
  debugging. Remove once production stable.
- [ ] **Remove frontend `console.log`.** `_applyFilterDomain` has
  debug traces that should be stripped for production.

---

## 13. Change log

| Date | Change | Author |
|---|---|---|
| 2026-04 | Initial architecture document | Andyka + Claude |
| 2026-04 | Added Product List drawer, Custom Filter, inline toggles, Track Inventory recovery, Favorites | Andyka + Claude |

---

## 14. How to update this document

1. When adding a public RPC → add its signature in section 2.
2. When adding state keys → add them in section 5.1.
3. When adding a CSS class that's meant to be styled externally → add
   it in section 7.
4. When discovering a gotcha that another developer would hit → add it
   in section 11.
5. When breaking an invariant in section 10 intentionally → update the
   invariant AND write a migration note in section 13.
6. Run `grep -r "<symbol>" andykanoz_product_checker/` to confirm
   nothing else inside the module references a removed symbol.
