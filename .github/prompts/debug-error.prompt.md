---
description: 'Analyze an Odoo 18 error and provide root cause + fix in structured format.'
mode: 'agent'
---

# Debug Odoo 18 Error

## Step 1 — Collect Inputs

Ask the user to provide (if not already given):

1. **Full error / traceback** — last 20 lines minimum
2. **What they were doing** — exact steps to reproduce
3. **What changed recently** — new install, upgrade, code edit
4. **Browser console** (if frontend issue)
5. **odoo.log tail** (if backend issue, path: `D:\MyServer\Odoo18\logs\odoo.log`)

If user already pasted full info, skip this step.

## Step 2 — Classify the Layer

Identify which layer:

- 🐍 **Python backend** — traceback, UserError, 500
- 🦉 **OWL frontend** — OwlError, blank page, console error
- 📄 **View XML** — ParseError on install/upgrade
- 🗄️ **Database** — IntegrityError, constraint violation
- 📦 **Asset / Cache** — old behavior persists after change

State your classification.

## Step 3 — Locate the Origin

Read traceback bottom-up. The first frame OUTSIDE `/usr/lib/python` and `/odoo/addons/<core>` is usually the culprit. In this codebase, it's typically an `andykanoz_*` module.

Use `codebase`/`search` tools to read the suspected file. Cite the specific lines.

## Step 4 — Pattern Match

Compare against known error patterns:

| Error pattern | Common root cause |
|---|---|
| `OwlError: Invalid props` | OWL 2 strict props validation; component received undeclared prop |
| `Wrong value for product.template.type: 'product'` | Pre-v18 type usage; should be `consu` + `is_storable` |
| `ParseError ... attrs` | Legacy `attrs=` in v18; use Python expression directly |
| `View ... has no field "..."` | Field added but module not upgraded |
| `psycopg2.errors.UniqueViolation` | DB unique constraint hit |
| `MissingError` | Stale recordset; needs `.exists()` |
| `Access denied` | Missing ACL or record rule blocks |
| Blank page on action | Duplicate `@http.route`, JS exception, or asset cache |

If pattern matches a known case from `agents/odoo18-expert.agent.md` INTERNAL KNOWLEDGE BASE, cite it.

## Step 5 — Output Structured Diagnosis

Use this format:

```markdown
## 🐛 Root Cause

**Layer**: <Python/OWL/XML/DB/Asset>
**Module**: `andykanoz_<n>`
**File**: `<path>:<line>`
**Pattern**: <one-line classification>

**What's happening**:
<2-3 sentences>

**Why it's happening**:
<2-3 sentences>

## 🔧 Fix

<minimal code change — surgical, not full rewrite>

## ✅ Verify

1. <reproduction step>
2. <expected behavior after fix>

⚠️/🔄/🌐 <restart? upgrade? hard refresh?>

## 📌 Related

<Other issues spotted but not fixed unless asked>
```

## Step 6 — Offer Follow-Up

End with:

> "Mau saya langsung apply fix-nya, atau Anda mau pelajari dulu?"

Do NOT edit files until user explicitly approves.

## Tone

- **Direct.** No "might be" or "perhaps" — commit to a diagnosis.
- **Cite evidence.** Every claim references a specific file/line.
- **Brief diagnosis, clear fix.** User wants the bug gone.
- **One bug at a time.** Mention related issues but focus on the requested one.
