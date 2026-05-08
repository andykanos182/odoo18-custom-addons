---
description: 'Add a custom field to an existing Odoo 18 model — model, view, security, and migration steps.'
mode: 'agent'
---

# Add Field to Existing Model

Use this prompt when adding a custom field to an existing Odoo model (core or custom). Generates Python definition, view changes, security considerations, and migration notes.

## Step 1 — Gather Specs

Ask (if not specified):

1. **Target model** — e.g. `product.template`, `pos.order`, `purchase.order.line`
2. **Field name** — must be `x_<snake_case>` for fields on inherited models
3. **Field type** — Char / Text / Integer / Float / Boolean / Date / Datetime / Selection / Many2one / One2many / Many2many / Binary
4. **Owner module** — which `andykanoz_*` module should host this field?
   - Default: the module most logically related (e.g., a price field → product_checker)
5. **Required, default, computed?**
6. **Show in views?** — list, form, kanban, search filters?
7. **Searchable / indexable?** — `index=True` for Many2one filtered often

## Step 2 — Sanity Checks

Before generating, verify:

- ✅ Owner module already inherits this model? If yes, add to existing inherit class. If no, create new model file.
- ✅ Field name doesn't collide with existing field — search the model's `_inherit` chain.
- ✅ Field name follows convention — `x_` prefix on inherited models, snake_case, descriptive.
- ✅ For Many2one to a model from another module, that module is in `depends`.

If any check fails, FLAG before proceeding.

## Step 3 — Output the Plan

Show the user before writing:

```markdown
## Plan: Add `x_<field_name>` to `<model>`

**Owner module**: `andykanoz_<n>`
**Files to modify**:
1. `models/<model_filename>.py` — field definition
2. `views/<view_file>.xml` — show in form/list (if requested)
3. `security/ir.model.access.csv` — N/A (extending existing model, ACL inherits)

**Field definition**:
\`\`\`python
x_<name> = fields.<Type>(
    string='<User Label>',
    <other params>
)
\`\`\`

**Migration impact**:
- New column added to <table>
- Existing records: <default value or null>
- Backfill needed: yes/no

**Restart needed**: yes (Python change)
**Upgrade needed**: yes (new column creation)
```

Wait for user approval.

## Step 4 — Generate the Code

### Python (model file)

```python
# In models/<file>.py
class <Model>(models.Model):
    _inherit = '<model.name>'

    x_<field_name> = fields.<Type>(
        string='<User Label>',
        help='<Tooltip text>',
        # required=True,
        # default=...,
        # tracking=True,  # if mail.thread present
        # index=True,     # if Many2one filtered/searched often
    )
```

Add to `__init__.py` if it's a new file:
```python
from . import <model_filename>
```

### View XML (if user wants UI)

For form view:
```xml
<record id="<existing_view_id>_inherit" model="ir.ui.view">
    <field name="name"><existing.view.name>.inherit</field>
    <field name="model"><model.name></field>
    <field name="inherit_id" ref="<base_view_xml_id>"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='<reference_field>']" position="after">
            <field name="x_<field_name>"/>
        </xpath>
    </field>
</record>
```

For list view, similar pattern with `<field>` element targeted in xpath.

For search view (filter):
```xml
<xpath expr="//search" position="inside">
    <filter string="Has <Field>"
            name="filter_x_<field_name>"
            domain="[('x_<field_name>', '!=', False)]"/>
</xpath>
```

### Manifest update (if first file in module)

```python
'data': [
    'security/ir.model.access.csv',
    'views/<existing_view_file>.xml',  # add this if new
],
```

## Step 5 — Computed / Onchange (if applicable)

If user said the field is computed:

```python
x_<name> = fields.<Type>(compute='_compute_x_<name>', store=True)

@api.depends('<dependency1>', '<dependency2>')
def _compute_x_<name>(self):
    for rec in self:
        rec.x_<name> = <calculation>
```

Remind user:
- `store=True` → DB column written; needed for filtering/sorting
- `store=False` (default) → computed on read, not stored
- `@api.depends` MUST list every field accessed in compute body

If user said "should change when X changes":

```python
@api.onchange('<trigger_field>')
def _onchange_<trigger_field>(self):
    if self.<trigger_field>:
        self.x_<name> = <derived_value>
```

⚠️ Onchange is UX hint only. NEVER write to DB or send notifications from here.

## Step 6 — Final Output

After writing files:

```markdown
## ✅ Field Added

**Files modified**:
- `<file1>` — added field definition
- `<file2>` — view inheritance

**Next steps**:
1. ⚠️ Restart Odoo: `docker restart <container-name>`
2. 🔄 Upgrade module: Apps → search → Upgrade
3. Verify: <how to verify the field appears>

**Migration notes**:
- New records: default value applies
- Existing records: <how default applies / backfill needed?>
```

## Anti-Patterns

- ❌ Adding field directly to core Odoo file (`Source Code Odoo18\addons\`) — read-only
- ❌ No `x_` prefix on inherited models — breaks Odoo convention
- ❌ Required field without default on a model with existing records — breaks upgrade
- ❌ Adding to view without inheriting (replacing core view by ID) — breaks future Odoo updates
- ❌ Onchange that does business logic — moved to compute or action method
