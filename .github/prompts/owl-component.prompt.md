---
description: 'Scaffold a complete Odoo 18 OWL 2 component — JS class, XML template, SCSS, and registration.'
mode: 'agent'
---

# Scaffold OWL 2 Component

Use this prompt to create a complete OWL 2 component for Odoo 18 — JS class + XML template + SCSS + registration.

## Step 1 — Gather Specs

Ask:

1. **Component name** — PascalCase (e.g. `BarcodeScanner`, `OrderDashboard`)
2. **Owner module** — which `andykanoz_*` module hosts it?
3. **Component type**:
   - **Client action** — full-page custom view (e.g. product checker, online order admin)
   - **Field widget** — custom form field (e.g. barcode scanner widget)
   - **Patched component** — extends an existing Odoo component (e.g. POS screen extension)
   - **Standalone widget** — embedded in another component
4. **Services needed** — `orm`, `notification`, `dialog`, `action`, `user`, `rpc`?
5. **Initial state** — what data does it manage? (rough list of state keys)
6. **Initial data fetch needed** — does it need to load data from server on mount?
7. **Mobile/tablet responsive?** — defaults to YES (Tab S8 production)

## Step 2 — Output the Plan

```markdown
## Plan: `<ComponentName>` Component

**Type**: Client action / Field widget / Patched / Standalone
**Owner module**: `andykanoz_<n>`

**Files to create**:
1. `static/src/js/<n>.js` — component class
2. `static/src/xml/<n>.xml` — template
3. `static/src/scss/<n>.scss` — styles

**Files to modify**:
1. `__manifest__.py` — register assets
2. `views/<view_file>.xml` — register client action / menu (if applicable)

**Component signature**:
\`\`\`
class <ComponentName> {
  state: { <key>: <type>, ... }
  services: <list>
  template: andykanoz_<module>.<ComponentName>Template
}
\`\`\`

**No restart needed** (asset-only change). Just hard refresh browser after install.
```

Wait for user approval.

## Step 3 — Generate JavaScript (`static/src/js/<n>.js`)

```javascript
/** @odoo-module **/

import { Component, useState, useRef, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class <ComponentName> extends Component {
    static template = "andykanoz_<module>.<ComponentName>Template";
    static props = {
        // Declare ALL props the component accepts.
        // Anything not listed will throw OwlError in OWL 2.
        action: { type: Object, optional: true },  // for client actions
    };

    setup() {
        // Services
        this.orm = useService("orm");
        this.notification = useService("notification");
        // Add others as needed

        // Refs
        this.<refName> = useRef("<refName>");

        // State (reactive — DOM auto-updates on change)
        this.state = useState({
            loading: false,
            // ...other state keys
        });

        // Lifecycle
        onWillStart(async () => {
            await this._loadInitialData();
        });

        onMounted(() => {
            // Focus, attach listeners, etc.
        });
    }

    async _loadInitialData() {
        this.state.loading = true;
        try {
            // const data = await this.orm.searchRead(...);
            // this.state.data = data;
        } catch (error) {
            this.notification.add(_t("Failed to load: ") + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    // Event handlers
    async onClickAction() {
        // ...
    }
}

// === Registration ===
// For CLIENT ACTION:
registry.category("actions").add(
    "andykanoz_<module>.<ComponentName>Action",
    <ComponentName>
);

// For FIELD WIDGET:
// import { standardFieldProps } from "@web/views/fields/standard_field_props";
// <ComponentName>.props = { ...standardFieldProps, /* extra */ };
// registry.category("fields").add("<widget_name>", { component: <ComponentName> });

// For PATCH:
// import { patch } from "@web/core/utils/patch";
// import { ExistingComponent } from "<existing path>";
// patch(ExistingComponent.prototype, { /* additions */ });
```

## Step 4 — Generate XML Template (`static/src/xml/<n>.xml`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="andykanoz_<module>.<ComponentName>Template">
        <div class="o_<module>_<component_snake>">

            <!-- Loading state -->
            <div t-if="state.loading" class="o_loading">
                <i class="fa fa-spinner fa-spin"/> Loading...
            </div>

            <!-- Main content -->
            <div t-else="" class="o_content">
                <!-- Build your UI here using:
                     t-esc=  for text (escaped, safe)
                     t-out=  for raw HTML (only trusted content)
                     t-if/t-elif/t-else=""  for conditionals
                     t-foreach + t-as + t-key  for loops
                     t-on-click  for events
                     t-att-class  for dynamic class
                -->
            </div>

        </div>
    </t>

</templates>
```

## Step 5 — Generate SCSS (`static/src/scss/<n>.scss`)

```scss
.o_<module>_<component_snake> {
    // Mobile-first base
    padding: 0.5rem;

    .o_loading {
        text-align: center;
        padding: 2rem;
        color: var(--text-muted);
    }

    .o_content {
        // ...
    }

    // Tablet (Tab S8 portrait)
    @media (min-width: 768px) {
        padding: 1rem;
    }

    // Tablet landscape (Tab S8 landscape)
    @media (min-width: 992px) {
        padding: 1.25rem;
    }

    // Desktop
    @media (min-width: 1200px) {
        padding: 1.5rem;
    }
}
```

## Step 6 — Register in `__manifest__.py`

Add to the `assets` block:

```python
'assets': {
    'web.assets_backend': [
        'andykanoz_<module>/static/src/js/<n>.js',
        'andykanoz_<module>/static/src/xml/<n>.xml',
        'andykanoz_<module>/static/src/scss/<n>.scss',
    ],
},
```

(Use `web.assets_frontend` instead if it's a portal/website component.)

## Step 7 — Register Action / Menu (for client actions)

Create or edit `views/<view_file>.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_<component_snake>" model="ir.actions.client">
        <field name="name"><Component Display Name></field>
        <field name="tag">andykanoz_<module>.<ComponentName>Action</field>
        <field name="target">current</field>
    </record>

    <menuitem
        id="menu_<component_snake>"
        name="<Menu Label>"
        action="action_<component_snake>"
        sequence="20"
        web_icon="andykanoz_<module>,static/description/icon.png"/>
</odoo>
```

## Step 8 — Final Output

```markdown
## ✅ Component Scaffolded

**Files created**:
- `static/src/js/<n>.js`
- `static/src/xml/<n>.xml`
- `static/src/scss/<n>.scss`

**Files modified**:
- `__manifest__.py`
- `views/<view_file>.xml` (if client action)

**To activate**:
1. ⚠️ Restart Odoo: `docker restart <container>` (manifest changed)
2. 🔄 Upgrade module: Apps → Upgrade
3. 🌐 Hard refresh browser: Ctrl+Shift+R

**Where to find it**:
<menu path or how to access>

**Next steps suggested**:
- Wire up <feature 1>
- Add <feature 2>
- Test on Tab S8 + phone
```

## Anti-Patterns

- ❌ Forgetting `static template` on the component class — OWL won't know what to render
- ❌ Forgetting `static props` — OWL 2 throws OwlError for any prop not declared (use `static props = ["*"]` only as escape hatch, prefer explicit list)
- ❌ Calling `useService` outside `setup()` — it must be inside the lifecycle
- ❌ Mutating state synchronously in template — use `state.foo = bar` in handlers
- ❌ Forgetting `t-key` in `t-foreach` — OWL warns and may render incorrectly
- ❌ Unscoped SCSS — bleeds into other components, hard to debug
- ❌ Hardcoded colors instead of CSS variables — breaks dark mode and theming
