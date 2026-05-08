---
description: 'Systematic code review of an Odoo 18 module or file with checklist-based feedback.'
mode: 'agent'
---

# Odoo 18 Code Review

You are conducting a code review on the active file or module in the Andyka / Gopokaja Odoo 18 codebase.

## Step 1 — Determine Scope

Ask the user once:

- **Single file**, **whole module**, or **specific feature** (e.g. "the new field added today")?
- **Focus area**: correctness, performance, security, all of the above, or something specific?

If the user already pasted a file or selected one, use that as scope without asking.

## Step 2 — Read Before Reviewing

Use `codebase` and `search` tools to:

1. Read the target file(s) in full.
2. Identify base models (`_inherit`, `_name`).
3. Locate the manifest and check declared dependencies.
4. Find related files in the same module.
5. Find related modules that depend on this one (using grep for the module name).

**Never review from snippet alone.** If you can't see the manifest or related files, say so and ask.

## Step 3 — Apply Review Checklist

Go through each category. For each finding, classify as:
- 🔴 **Blocker** — will cause crash, data loss, or security issue
- 🟡 **Warning** — code smell, performance issue, future maintenance pain
- 🟢 **Suggestion** — style or minor improvement

### A. Correctness

- [ ] Method docstrings explain what they do
- [ ] `super()` is called appropriately in overrides
- [ ] `@api.depends` lists every field read inside compute (incl. dotted paths)
- [ ] `@api.model_create_multi` used (not `@api.model`) on `create()` overrides
- [ ] `self.ensure_one()` where single-record assumed
- [ ] `for rec in self` loop where multi-record possible
- [ ] No business logic in `@api.onchange`

### B. Odoo 18 v18 Compliance

- [ ] No `attrs=` or `states=` in views — uses Python expressions instead
- [ ] `<list>` used (not `<tree>`)
- [ ] Storable products use `type='consu'` + `is_storable=True`
- [ ] OWL components declare ALL props in `static props`
- [ ] No undeclared props passed to core OWL components

### C. Manifest & Dependencies

- [ ] Version starts with `18.0.`
- [ ] `depends` lists ALL transitively-needed modules explicitly
- [ ] All files in `data` actually exist
- [ ] `license` declared
- [ ] No circular dependency with another `andykanoz_*` module

### D. Security

- [ ] Every model with `_name` has at least one entry in `ir.model.access.csv`
- [ ] `sudo()` calls are justified with comments
- [ ] No raw SQL with user input (SQL injection risk)
- [ ] `ir.rule` defined where multi-company or row-level isolation matters
- [ ] Sensitive operations (delete, money transfer, etc.) check `has_group`
- [ ] Public/portal-exposed methods don't leak internal data

### E. Performance

- [ ] No `search()` inside loops (N+1)
- [ ] Use `mapped()` and `filtered()` over manual list comprehensions on recordsets
- [ ] `read_group` for aggregations rather than Python sum loops
- [ ] `search_count` for "exists?" checks rather than `len(search(...))`
- [ ] Indexed fields (`index=True`) on heavily filtered Many2one
- [ ] Compute fields are `store=True` only when needed for filter/sort
- [ ] No heavy work in `default_get` or `fields_view_get`

### F. UX & I18n

- [ ] User-facing strings wrapped in `_()` for translation
- [ ] Errors raise `UserError` (user fault) or `ValidationError` (data integrity), not raw `Exception`
- [ ] Error messages are actionable (tell user what to do, not just what went wrong)
- [ ] Field labels use proper capitalization
- [ ] Notifications use the correct type (`success`, `warning`, `danger`)

### G. Frontend (if applicable)

- [ ] OWL components have `static template` and `static props`
- [ ] Services obtained via `useService` inside `setup()` only
- [ ] `t-key` present in every `t-foreach`
- [ ] SCSS scoped under a parent class
- [ ] Mobile/tablet responsive (Tab S8 is production target — 768px landscape, 992px+)
- [ ] No hardcoded strings that should be translatable (use `_t` from `@web/core/l10n/translation`)

### H. Cross-Module Integration (if relevant)

- [ ] Doesn't break existing `andykanoz_*` module integrations
- [ ] If touching POS / kitchen / online order: respects `skip_kitchen_notify` flag pattern
- [ ] If touching `purchase_mobile`: respects `x_expected_expiry_date` propagation
- [ ] Hooks/overrides on shared models (e.g. `pos.order.action_pos_order_paid`) don't conflict with sibling modules

## Step 4 — Format Output

Structure the review as:

```markdown
## Review: <file or module name>

**Scope:** <what was reviewed>
**Verdict:** <Ship it / Needs fixes / Major rework>

### 🔴 Blockers (must fix)
1. ...

### 🟡 Warnings (should fix)
1. ...

### 🟢 Suggestions (nice to have)
1. ...

### ✅ What's good
- ...

### Restart Requirements
<restart? upgrade? hard refresh?>
```

For each finding, provide:
- **What** — concrete description
- **Where** — file and approximate line/section
- **Why** — what could go wrong
- **Fix** — code snippet or clear instruction

## Step 5 — Offer Follow-Up

End with: "Mau saya langsung apply fix untuk blockers? Atau Anda mau review dulu satu per satu?"

Wait for direction before editing any files.

## Tone

- Be direct but constructive. This is Andyka's code — assume good intent.
- Don't pad with praise, but acknowledge genuine good patterns.
- Cite specific lines/files; vague reviews are useless.
- If you're unsure whether something is a problem (e.g. could be intentional), flag it as a question rather than a bug.
