---
description: 'Scaffold a new Odoo 18 module with proper structure, manifest, security, and views.'
mode: 'agent'
---

# Scaffold New Odoo 18 Module

You are scaffolding a new custom module for the Andyka / Gopokaja Odoo 18 codebase.

## Step 1 — Gather Requirements

Ask the user (max 5 focused questions):

1. **Module name** — must follow `andykanoz_<feature>` convention (snake_case).
2. **Category** — Inventory / Sales / Manufacturing / Point of Sale / Website / Purchase / etc.
3. **Purpose** — one sentence.
4. **Base model(s)** — does it extend an existing model (e.g. `product.template`, `sale.order`), define a new model, or both?
5. **Dependencies** — beyond `base`, which Odoo modules does it depend on? Does it need any of the existing `andykanoz_*` modules?

Stop and confirm understanding before generating any file.

## Step 2 — Confirm Plan

Before scaffolding, present the user with:

- Final module name
- Folder structure to be created
- Files to be generated (with one-line description each)
- Dependency list
- Whether new model(s) will be created (and the implication: `ir.model.access.csv` entries needed)
- Restart/upgrade requirement after install

Wait for explicit "ya" / "lanjutkan" / "ok" before writing files.

## Step 3 — Scaffold

Create files in `D:\MyServer\Odoo18\Addons\andykanoz_<feature>\` with this structure:

```
andykanoz_<feature>/
├── __init__.py                    # from . import models, controllers (only if needed)
├── __manifest__.py
├── README.md                      # brief description + install steps
├── models/
│   ├── __init__.py
│   └── <main_model>.py
├── views/
│   ├── <main_model>_views.xml
│   └── <main_model>_menu.xml      # only if new top-level menu
├── security/
│   └── ir.model.access.csv        # MANDATORY for any new model
└── static/
    └── description/
        └── icon.png               # placeholder; user replaces later
```

Add these only if needed:

- `controllers/` — only if HTTP routes (`@http.route`) are required
- `data/` — for `ir.sequence`, `ir.cron`, default records
- `wizard/` — for transient models
- `report/` — for QWeb reports
- `static/src/{js,xml,scss}/` — for OWL frontend

## Step 4 — Manifest Template

```python
# -*- coding: utf-8 -*-
{
    'name': 'Andykanoz <Feature Title>',
    'version': '18.0.1.0.0',
    'category': '<Category>',
    'summary': '<one line>',
    'description': """
<Feature Title>
===============
<2-3 line description>
    """,
    'author': 'Andyka',
    'license': 'LGPL-3',
    'depends': [
        'base',
        # other deps
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/<main_model>_views.xml',
        'views/<main_model>_menu.xml',
    ],
    'installable': True,
    'application': <True|False>,    # True only if it has a top-level menu
}
```

## Step 5 — Security CSV (if new model)

Always generate at minimum:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_<model>_user,<model>.user,model_<model_underscores>,base.group_user,1,1,1,0
access_<model>_manager,<model>.manager,model_<model_underscores>,base.group_system,1,1,1,1
```

If multi-company, add `ir.rule` for company isolation.

## Step 6 — Verify Odoo 18 Compliance

Before declaring scaffold complete, scan generated files for these v18 compliance issues:

- ❌ `attrs=`, `states=` in any view → use Python expressions
- ❌ `<tree>` → use `<list>`
- ❌ `type='product'` for storable → use `type='consu'` + `is_storable=True`
- ❌ Undeclared OWL props
- ❌ Missing `_description` on new models
- ❌ Missing `@api.model_create_multi` on `create()` overrides

## Step 7 — Final Output

After scaffolding, tell the user:

1. List of files created (with paths).
2. Next steps:
   ```
   1. Restart container: docker restart <container-name>
   2. Activate Developer Mode in Odoo
   3. Apps → Update Apps List
   4. Search "Andykanoz <Feature>" → Install
   ```
3. Suggested follow-up tasks (e.g., "add demo data", "wire frontend", "write first test").
4. Reminder that this is v18.0.1.0.0 — bump version on subsequent feature additions.

## Anti-Patterns to Avoid

- Don't generate empty placeholder files just for structure — only create what's actually needed.
- Don't generate controllers if there are no HTTP routes.
- Don't add `application: True` unless there's a top-level menu.
- Don't fabricate field names from imagination — verify against actual Odoo models in `Source Code Odoo18\addons\` if uncertain.
