---
description: 'Odoo 18 OWL 2 frontend conventions for JS components, XML templates, and SCSS.'
applyTo: '**/static/src/**'
---

# Odoo 18 OWL 2 Frontend Conventions

These rules apply automatically when editing files inside any module's `static/src/` folder.

## File Organization

```
static/src/
├── js/
│   ├── my_component.js       ← OWL component class
│   └── services/
│       └── my_service.js     ← reusable service
├── xml/
│   └── my_component.xml      ← OWL templates (t-name=)
└── scss/
    └── my_component.scss     ← styles, scoped via parent class
```

Register all three in `__manifest__.py`:

```python
'assets': {
    'web.assets_backend': [
        'andykanoz_<feature>/static/src/js/**/*.js',
        'andykanoz_<feature>/static/src/xml/**/*.xml',
        'andykanoz_<feature>/static/src/scss/**/*.scss',
    ],
},
```

## OWL 2 Component Skeleton

```javascript
/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MyComponent extends Component {
    static template = "andykanoz_module.MyComponentTemplate";
    static props = {
        // Declare ALL props the component accepts.
        // Anything not listed will throw OwlError.
        action: { type: Object, optional: true },
    };

    setup() {
        // Services
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        // State (reactive)
        this.state = useState({
            loading: false,
            data: [],
        });

        // Refs (DOM access)
        this.inputRef = useRef("input");

        // Lifecycle
        onWillStart(async () => {
            await this._loadInitialData();
        });

        onMounted(() => {
            this.inputRef.el?.focus();
        });
    }

    async _loadInitialData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.searchRead(
                "product.template",
                [["active", "=", true]],
                ["id", "name", "default_code"],
            );
        } finally {
            this.state.loading = false;
        }
    }

    async onClickButton() {
        await this.orm.call("product.template", "my_method", [[1, 2, 3]]);
        this.notification.add("Done!", { type: "success" });
    }
}

// For client actions (full-page custom views)
registry.category("actions").add("andykanoz_module.my_action", MyComponent);
```

## OWL Template (`xml/my_component.xml`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="andykanoz_module.MyComponentTemplate">
        <div class="o_my_component">
            <input
                t-ref="input"
                t-on-keydown="onKeydown"
                placeholder="Search..."
            />

            <div t-if="state.loading" class="o_loading">Loading...</div>

            <div t-else="" class="o_results">
                <t t-foreach="state.data" t-as="item" t-key="item.id">
                    <div class="o_item" t-on-click="() => this.selectItem(item)">
                        <t t-esc="item.name"/>
                    </div>
                </t>
            </div>

            <button class="btn btn-primary" t-on-click="onClickButton">
                Confirm
            </button>
        </div>
    </t>

</templates>
```

OWL directive cheat sheet:
- `t-name=` define template
- `t-esc=` escaped text output (default — safe)
- `t-out=` raw HTML output (only for trusted content)
- `t-if`/`t-elif`/`t-else=""` conditional render
- `t-foreach` + `t-as` + `t-key` (key REQUIRED for lists)
- `t-on-<event>` event binding (e.g. `t-on-click`)
- `t-ref` DOM ref handle
- `t-att-<attr>` dynamic attribute (e.g. `t-att-class`)
- `t-attf-<attr>` formatted attribute (e.g. `t-attf-style="color: {{color}}"`)

## CRITICAL: OWL 2 Strict Props Validation

OWL 2 throws `OwlError` for ANY undeclared prop passed to a component. Before passing props to a core dialog or component, **read its source** in `Source Code Odoo18\addons\web\static\src\...` to confirm the `static props` declaration.

```javascript
// ❌ Will crash with OwlError
this.dialog.add(DomainSelectorDialog, {
    resModel: "product.template",
    domain: "[]",
    onSelected: this.onSelected,    // not a valid prop
    onClose: this.onClose,          // not a valid prop
    defaultConnector: "&",          // not a valid prop
});

// ✅ Pass only declared props
this.dialog.add(DomainSelectorDialog, {
    resModel: "product.template",
    domain: "[]",
    isDebugMode: true,
    onConfirm: (newDomain) => this.applyDomain(newDomain),
});
```

This is a real bug we already hit on `andykanoz_product_checker`. See the agent file's INTERNAL KNOWLEDGE BASE.

## Services Cheat Sheet

```javascript
// In setup()
this.orm = useService("orm");                     // ORM calls
this.notification = useService("notification");   // toast notifications
this.dialog = useService("dialog");               // dialogs
this.action = useService("action");               // dispatch actions
this.user = useService("user");                   // current user info
this.rpc = useService("rpc");                     // raw RPC (rare; prefer orm)
```

ORM service methods:
```javascript
await this.orm.searchRead(model, domain, fields, options);
await this.orm.read(model, ids, fields);
await this.orm.search(model, domain);
await this.orm.searchCount(model, domain);
await this.orm.create(model, vals_list);
await this.orm.write(model, ids, vals);
await this.orm.unlink(model, ids);
await this.orm.call(model, method, args, kwargs);  // call any model method
```

## Actions

Open another view from JS:

```javascript
// Open a form view
this.action.doAction({
    type: "ir.actions.act_window",
    res_model: "product.template",
    res_id: productId,
    views: [[false, "form"]],
    target: "current",
});

// Open by XML ID
this.action.doAction("andykanoz_module.action_my_window");

// Open URL
this.action.doAction({
    type: "ir.actions.act_url",
    url: "/web/binary/download?id=...",
    target: "new",
});
```

## SCSS Conventions

Always scope styles under a parent class to avoid global pollution:

```scss
// ❌ Global pollution
.btn-primary { background: red; }

// ✅ Scoped
.o_my_component {
    .btn-primary { background: red; }
}
```

For Odoo 18 responsive (we use Tab S8 in production), use mobile-first breakpoints aligned with Bootstrap 5:

```scss
.o_my_component {
    // mobile-first base
    padding: 0.5rem;

    @media (min-width: 576px)  { padding: 0.75rem; }   // sm
    @media (min-width: 768px)  { padding: 1rem;    }   // md (Tab S8 portrait)
    @media (min-width: 992px)  { padding: 1.25rem; }   // lg (Tab S8 landscape)
    @media (min-width: 1200px) { padding: 1.5rem;  }   // xl (desktop)
}
```

In nested modal/dialog contexts, `!important` is sometimes required to override Odoo's modal CSS. Use sparingly and document why.

## Patching Existing Components

To extend a core OWL component without re-implementing it:

```javascript
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        // your additions
    },
    async myCustomMethod() {
        // entirely new method
    },
});
```

`patch()` modifies the prototype in place — every instance afterwards gets your changes.

## Asset Loading Reminder

After ANY change to JS/XML/SCSS:
- **No restart needed.** No upgrade needed.
- Just **hard refresh browser** (Ctrl+Shift+R).
- If asset bundle didn't rebuild, delete `~/.local/share/Odoo/sessions/` (Linux) or restart container as last resort.

## Common Pitfalls

- **Forgetting `t-key` in `t-foreach`** — OWL warns and may render incorrectly.
- **Mutating `state` from outside setup synchronously in onWillStart** — initialize via assignment, not push.
- **Calling `orm.call` with wrong arg shape** — args is array of positional, kwargs is dict. Recordset methods receive `[ids, ...other_args]`.
- **Importing from wrong path** — use `@odoo/owl`, `@web/core/...`, `@web/views/...`. Never deep-import from a third-party module's internals.
- **Service used before `setup()`** — `useService` must be called inside `setup`, not in handlers or async methods.
