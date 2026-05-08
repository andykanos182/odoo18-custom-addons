---
description: 'Detailed knowledge for andykanoz_quick_purchase module — session-based PO drafting with camera scan.'
applyTo: '**/andykanoz_quick_purchase/**'
---

# Module: `andykanoz_quick_purchase`

Session-based product drafting interface that converts to Purchase Orders (RFQ). Distinct from `andykanoz_purchase_mobile`.

## Architecture Snapshot

```
andykanoz_quick_purchase/
├── __manifest__.py
├── controllers/
│   └── main.py                  # JSON-RPC: save/load/clear session, create_purchase_order
├── models/
│   └── res_users.py             # may store session data per user (verify)
├── security/ir.model.access.csv
├── static/src/
│   ├── js/quick_purchase.js     # main OWL component (~1600+ lines)
│   ├── xml/quick_purchase.xml
│   └── scss/quick_purchase.scss
└── views/
    ├── menu.xml
    └── client_action.xml
```

## Key Behaviors

- **Session-based drafting**: User adds products to a draft "session" (server-side store) before committing.
- **Camera scan**: Two modes — "Once" (popup confirms) and "Continuous" (auto-add).
- **Duplicate handling**: In "Once" mode, scanning an existing product shows a confirmation modal with `[input][-][+]` qty stepper.
- **Convert to PO**: One-click conversion of session to RFQ (purchase.order in 'draft' state).

## Routes (Controller)

```
POST /quick_purchase/save_session
POST /quick_purchase/load_session
POST /quick_purchase/clear_session
POST /quick_purchase/create_purchase_order
```

Routes use JSON type, csrf=False.

## Critical: `clear_session` Bug Pattern

A historical bug had **duplicate `clear_session` definitions** in `controllers/main.py` — the second (legacy "Section 9") overrode the first (correct "Section 8"). Result: blank page when clicking "Create Purchase Order".

**Lesson**: When reading this file, search for duplicate route definitions with the same path. Python's last-definition-wins silently breaks routing.

## Critical: SCSS `!important` Override

The duplicate-product modal uses a `[input][-][+]` qty stepper that breaks under existing rule:

```scss
// Rule that causes wrap (existing in module)
.o_qp_modal .o_qp_form_row input { width: 100%; }
```

Override needs `!important` because the duplicate modal is nested inside the same `.o_qp_modal` selector:

```scss
.o_qp_duplicate_modal .o_qp_qty_stepper input {
    width: auto !important;  // override needed
    flex: 0 0 60px;
}
```

## Common Modifications

| Task | Where |
|---|---|
| Add field to session product | `quick_purchase.js` (state.lines schema) + xml + scss |
| Change camera scan threshold | `_onBarcodeDetected` in JS |
| Customize generated PO | `create_purchase_order` in controllers/main.py |
| Add button to mobile card | `quick_purchase.xml` + corresponding handler in JS |

## Known Pre-Existing Issues (Deferred)

- Undefined methods called from template: `toggleSortOrder`, `switchCamera`, scan popup handlers
- These don't crash but are dead-button pitfalls. User chose to defer.

## Pitfalls

- ⚠️ **Two camera modes** ("Once" and "Continuous") have very different UX. Andyka explicitly does NOT want Continuous mode touched. Always confirm before changing camera logic.
- ⚠️ **`stepQty(productId, delta)` was missing** — added later for mobile +/- buttons. Min qty clamped to 1.
- ⚠️ **`.venv/`, `current_js.txt`, `temp_replacement*.txt`** — these are legacy scratch files. Do NOT include in scaffolds; they were cleaned up.
- ⚠️ **`onWillUnmount` had bug** — called non-existent `_saveSession()`; correct method is `_saveCurrentSession()` then `_saveSessionToServer()`. Don't reintroduce that mistake.

## Test Checklist

- [ ] Add product → appears in session
- [ ] Refresh page → session persists (server-side)
- [ ] Camera scan in "Once" mode → adds product OR shows duplicate modal
- [ ] Camera scan in "Continuous" mode → auto-adds (don't break this)
- [ ] Mobile +/- buttons work (`stepQty` not undefined)
- [ ] "Create Purchase Order" button → goes to RFQ form (no blank page)
- [ ] Clear session removes all lines
