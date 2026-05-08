---
description: 'Odoo 18 Python conventions, ORM patterns, and security rules.'
applyTo: '**/*.py'
---

# Odoo 18 Python Conventions

These rules apply automatically whenever you edit a Python file in this workspace.

## File Header

Every Python file starts with:

```python
# -*- coding: utf-8 -*-
```

## Manifest (`__manifest__.py`)

Use this skeleton — version always starts with `18.0.`:

```python
# -*- coding: utf-8 -*-
{
    'name': 'Andykanoz <Feature>',
    'version': '18.0.1.0.0',
    'category': '<Inventory|Sales|Manufacturing|Point of Sale|Website>',
    'summary': 'One-line summary',
    'author': 'Andyka',
    'license': 'LGPL-3',
    'depends': ['base'],   # always declare ALL deps explicitly
    'data': [
        'security/ir.model.access.csv',
        'views/<model>_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'andykanoz_<feature>/static/src/js/*.js',
        ],
    },
    'installable': True,
    'application': False,
}
```

## Models

### Inheriting (most common)

```python
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_my_field = fields.Char(string='My Field')
```

### New model

```python
class MyModel(models.Model):
    _name = 'my.model'
    _description = 'My Model'   # REQUIRED — Odoo will warn without it
    _order = 'create_date desc'
    _check_company_auto = True   # if multi-company aware

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )
```

**If you create a new model with `_name`, you MUST also add an entry to `security/ir.model.access.csv`. No exceptions.**

## Field Conventions

- Custom fields on inherited models prefixed `x_` (Odoo convention for non-core fields).
- Always provide `string=` for user-visible labels — translatable.
- For Many2one to `res.users` or `res.partner`, consider `index=True` if filtered/searched often.
- Selection fields: define choices as module-level constant or use `selection=lambda` if dynamic.

## Compute Fields

```python
total = fields.Float(compute='_compute_total', store=True)

@api.depends('line_ids.price', 'line_ids.quantity')
def _compute_total(self):
    for rec in self:
        rec.total = sum(l.price * l.quantity for l in rec.line_ids)
```

Rules:
- `@api.depends` must list EVERY field read inside the compute (including dotted paths).
- Always loop `for rec in self` — never assume single record unless `self.ensure_one()`.
- `store=True` only when filtering/sorting on this field; otherwise leave unstored.
- Never write to other models from a compute. Use `create()`/`write()` overrides instead.

## Onchange

```python
@api.onchange('partner_id')
def _onchange_partner_id(self):
    if self.partner_id:
        self.payment_term_id = self.partner_id.property_payment_term_id
```

Rules:
- Onchange is for UX hints ONLY — runs in browser before save.
- NEVER do business logic, write to DB, or send notifications here.
- Use `_compute_*` if value should always be derived; use `default_get` for new-record defaults.

## Create / Write Overrides

```python
@api.model_create_multi
def create(self, vals_list):
    records = super().create(vals_list)
    for rec in records:
        rec._post_create_hook()
    return records

def write(self, vals):
    res = super().write(vals)
    if 'state' in vals and vals['state'] == 'done':
        self._on_done()
    return res
```

- Always use `@api.model_create_multi` (not `@api.model`) for `create()` in v18.
- Call `super()` first unless you have a strong reason; then add side-effects.

## Action Methods

```python
def action_confirm(self):
    self.ensure_one()
    if self.state != 'draft':
        raise UserError(_("Only draft records can be confirmed."))
    self.write({'state': 'confirmed'})
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': _('Success'),
            'message': _('Record confirmed.'),
            'type': 'success',
        },
    }
```

- Method name starts with `action_` for buttons.
- Always use `_()` for translatable strings in user messages.
- Raise `UserError` (user fault) or `ValidationError` (data integrity), never raw `Exception`.

## ORM Best Practices

✅ DO:
```python
# Batch read with mapped()
total = sum(self.line_ids.mapped('price'))

# Single search outside loop
products = self.env['product.template'].search([('active', '=', True)])
for product in products:
    ...

# Use search_count when you only need the count
if self.env['sale.order'].search_count([('partner_id', '=', partner.id)]):
    ...

# read_group for aggregation
data = self.env['stock.move'].read_group(
    domain=[('state', '=', 'done')],
    fields=['product_id', 'qty_done:sum'],
    groupby=['product_id'],
)
```

❌ DON'T:
```python
# N+1: search inside loop
for line in self.line_ids:
    products = self.env['product.template'].search([('id', '=', line.product_id.id)])  # NO!

# Reading entire recordset just to count
count = len(self.env['sale.order'].search([...]))  # use search_count instead

# Raw SQL when ORM works
self.env.cr.execute("SELECT * FROM product_template")  # only with strong justification
```

## Storable Products (Odoo 18 specific)

```python
# ❌ Old (pre-v18) — will raise ValueError
self.env['product.template'].create({'type': 'product'})

# ✅ Odoo 18
self.env['product.template'].create({
    'type': 'consu',
    'is_storable': True,
})
```

## Security

When you call `.sudo()`, leave a comment explaining why bypass is intentional:

```python
# sudo: portal user needs to read internal pricelist for display
price = self.pricelist_id.sudo()._get_product_price(product, qty=1)
```

For multi-company-aware models:

```python
class MyModel(models.Model):
    _name = 'my.model'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', check_company=True)
```

## Logging

```python
import logging
_logger = logging.getLogger(__name__)

_logger.info("Processed %d records for partner %s", len(records), partner.name)
_logger.warning("Skipping record %s: missing pricelist", rec.id)
_logger.exception("Unhandled error in _process_batch")  # logs traceback
```

Never use `print()` in production code.

## Common Pitfalls

- **`self.env.user` vs `self.env.uid`** — `user` is a record, `uid` is an int. Use `user` for `.has_group()` checks, `uid` for raw comparisons.
- **`@api.constrains` runs on create AND write** — make sure logic handles both.
- **`fields.Many2one(..., ondelete='cascade')`** — be deliberate; cascade can wipe data unexpectedly.
- **Don't trust `self` is a single record** — use `self.ensure_one()` if you need it.
- **`unlink()` triggers ORM hooks**; for bulk deletes consider implications.
