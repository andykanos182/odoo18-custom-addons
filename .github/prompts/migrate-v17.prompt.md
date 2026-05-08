---
description: 'Migrate legacy Odoo v16/v17 code to v18 — handles attrs, states, type=product, OWL 2, and other breaking changes.'
mode: 'agent'
---

# Migrate Code to Odoo 18

Use this prompt when porting code from older Odoo versions (or fixing legacy patterns that crept in). Handles all known v17→v18 breaking changes.

## Step 1 — Identify Scope

Ask:
1. **What's being migrated?** Single file? Whole module? Specific feature?
2. **Source version** — v16, v17, or unknown?
3. **Has it ever worked on v18?** — affects whether to expect new bugs or just compatibility issues.

If user pasted code directly, scope is that snippet.

## Step 2 — Scan for Breaking Changes

Read the target file(s). Check each pattern below. Output a checklist of what was found:

### Pattern 1: `attrs` and `states` removed in v18

**Search for**: `attrs="`, `states="`

❌ v17 and earlier:
```xml
<field name="x" attrs="{'invisible': [('state','=','draft')]}"/>
<field name="y" states="done,cancel"/>
```

✅ v18:
```xml
<field name="x" invisible="state == 'draft'"/>
<field name="y" invisible="state not in ('done', 'cancel')"/>
```

Supported attrs replacements: `invisible`, `readonly`, `required`, `column_invisible` (list views).

### Pattern 2: `type='product'` for storable goods

**Search for**: `'type': 'product'`, `type="product"`

❌ Pre-v18:
```python
self.env['product.template'].create({'type': 'product'})
```

✅ v18:
```python
self.env['product.template'].create({
    'type': 'consu',
    'is_storable': True,
})
```

### Pattern 3: `<tree>` view tag

**Search for**: `<tree`, `</tree>`

❌ Pre-v17.3:
```xml
<tree string="Products">
    <field name="name"/>
</tree>
```

✅ v18:
```xml
<list string="Products">
    <field name="name"/>
</list>
```

### Pattern 4: OWL 1 patterns

**Search for**: `static template = xml`, `Component.env`, `useState({...}, this)`, no `static props`

❌ OWL 1:
```javascript
class MyComponent extends Component {
    static template = xml`<div t-esc="state.value"/>`;
    setup() {
        this.state = useState({...}, this);
    }
}
```

✅ OWL 2 (v18):
```javascript
import { Component, useState } from "@odoo/owl";

class MyComponent extends Component {
    static template = "module.MyComponentTemplate";  // template name, not inline XML
    static props = {};                                // REQUIRED — declare all props
    setup() {
        this.state = useState({...});                 // no second arg
    }
}
```

### Pattern 5: Service injection

**Search for**: `Component.env.services`, deprecated service paths

❌ Old pattern:
```javascript
const orm = Component.env.services.orm;
```

✅ v18:
```javascript
import { useService } from "@web/core/utils/hooks";

setup() {
    this.orm = useService("orm");
}
```

### Pattern 6: `@api.model` on `create()`

**Search for**: `@api.model\n    def create(self, vals):`

❌ Old:
```python
@api.model
def create(self, vals):
    return super().create(vals)
```

✅ v18 (preferred):
```python
@api.model_create_multi
def create(self, vals_list):
    return super().create(vals_list)
```

### Pattern 7: Search method signatures

**Search for**: `_name_search`, `_search` overrides

In v18, `_name_search` and `_search` signatures changed. Check parameters:

❌ Old:
```python
def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
```

✅ v18:
```python
def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
```

### Pattern 8: Asset import paths

**Search for**: deep imports from `@web/legacy/...`, `web.foo`, `'web.AbstractAction'`

Many legacy paths are gone. Common replacements:

| v17 import | v18 equivalent |
|---|---|
| `@web/legacy/js/core/component_extension` | use OWL 2 directly |
| `'web.Widget'` | OWL Component |
| `web.AbstractAction` | client action via registry |
| `mail.Activity` | activity mixin via inherit |

### Pattern 9: `ir.config_parameter` API

**Search for**: `get_param`, `set_param` calls

API stable but `sudo()` requirements changed:

✅ v18 best practice:
```python
value = self.env['ir.config_parameter'].sudo().get_param('my.key', default='100')
```

### Pattern 10: List view `<button>` placement

**Search for**: `<button>` inside `<tree>`/`<list>`

In v18 list views, button placement is more strict. Check tested structure:

```xml
<list>
    <field name="name"/>
    <field name="state"/>
    <button name="action_x" type="object" string="Do It"
            invisible="state == 'done'"/>  <!-- not attrs anymore -->
</list>
```

## Step 3 — Output Migration Report

Format:

```markdown
## 📋 Migration Report

**Scope**: <files or feature>
**Source version**: v<n>
**Target**: v18

### Breaking Changes Found

| # | Pattern | Count | Severity |
|---|---|---|---|
| 1 | attrs/states | <n> | 🔴 Blocker |
| 2 | type='product' | <n> | 🔴 Blocker |
| 3 | <tree> | <n> | 🟡 Warning (still works in v18 with deprecation) |
| ... |  |  |  |

### Other Issues Spotted (not v18-specific but worth fixing)

- ...

### Estimated effort

- Mechanical changes: <n> files, ~<n> minutes
- Logic review needed: <list>
```

## Step 4 — Confirm Before Migrating

Show the user:

> "Found <n> breaking changes. Mau saya apply migration sekaligus, atau review per pattern dulu?"

Wait for explicit "lanjut" / approval.

## Step 5 — Apply Migrations

For each pattern found, use surgical `edit` operations. After all changes:

```markdown
## ✅ Migration Complete

**Files modified**: <list>

**Manual review still needed**:
- <items that auto-migration couldn't handle confidently>

**To verify**:
1. ⚠️ Restart Odoo
2. 🔄 Upgrade module
3. Test: <specific scenarios>
```

## Tone

- **Explicit about what changed and why** — Andyka should learn the v18 patterns, not just see them applied
- **Conservative on logic-heavy migrations** — when unsure, flag for manual review rather than guess
- **Cite the v18 docs/source** when explaining a change
