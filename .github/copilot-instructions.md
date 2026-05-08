# Project: Andyka Odoo 18 Custom Modules (Gopokaja)

This workspace is the **custom addons folder** of an Odoo 18 instance running in Docker on a Windows laptop. It powers **Gopokaja**, an F&B business in Denpasar, Bali. Staff use Samsung Tab S8 at cashier and kitchen stations.

## Filesystem

- Custom modules live in: `D:\MyServer\Odoo18\Addons\`
- Odoo core source (READ-ONLY reference): `D:\MyServer\Odoo18\Source Code Odoo18\addons\`
- Odoo runs in Docker; logs at `D:\MyServer\Odoo18\logs\odoo.log`
- Local URL: `http://localhost:8018` · Production: `https://nitro.gopokaja.com`

## Active Custom Modules

All custom modules are prefixed `andykanoz_`:

- `andykanoz_product_checker` — barcode scan, price/stock lookup, print list
- `andykanoz_product_kanban_desktop` — responsive kanban view for products
- `andykanoz_kitchen_notify` — Web Push to kitchen display (`kitchen.order`, `kitchen.vapid`)
- `andykanoz_pos_auto_mo` — auto-create MO from POS order on payment
- `andykanoz_online_order` — public ordering portal `/order-online`
- `andykanoz_purchase_mobile` — mobile-friendly PO with expiry tracking

## Critical Rules

1. **NEVER modify core Odoo files** in `Source Code Odoo18\` — read-only reference.
2. **Use `_inherit` to extend, `_name` only for genuinely new models.**
3. **Every new model REQUIRES `ir.model.access.csv`** — non-negotiable.
4. **Odoo 18 breaking changes — apply automatically:**
   - Storable products: `type='consu'` + `is_storable=True` (NOT `type='product'`)
   - View attributes: `attrs`/`states` removed → use Python expressions directly
   - List views: `<list>` (not `<tree>`)
   - OWL 2: pass ONLY props declared in component's `static props`
5. **Never fabricate Odoo APIs from memory** — verify in actual core source.

## Working Style

- Bahasa Indonesia campur Inggris untuk istilah teknis — ikuti gaya Andyka.
- **Explain BEFORE code.** Confirm understanding, then execute.
- One issue at a time. Don't fix unprompted bugs you happen to notice — mention them only.
- Surgical edits preferred (exact-match replacement) over full file rewrites.
- After every code change, state explicitly: **restart container? upgrade module? hard refresh browser?**

## Restart vs Upgrade Decision (during development)

During active development (mid-task, iterating), use granular rules to avoid wasting time on unnecessary restarts:

| Change | Action |
|---|---|
| `.py` files | Restart container + Upgrade module |
| New model / new field | Restart + Upgrade |
| `__manifest__.py` | Restart + Upgrade |
| View XML / data XML | Upgrade only (no restart) |
| Asset JS/XML/SCSS | Hard browser refresh (Ctrl+Shift+R) |
| `ir.model.access.csv` | Upgrade only |

## 🔁 Module Completion Protocol (MANDATORY)

**Whenever a module/feature/bugfix is COMPLETED** (not mid-iteration), the response MUST end with the full restart command — regardless of which files changed. Andyka's standing rule: every completed unit ships with a fresh container.

**Definition of "completed"**:
- Feature/module fully implemented and ready to test
- Bug fixed and verified-fixable
- Refactor/cleanup that's ready for review
- User says "selesai", "done", "sudah", or task hits its natural endpoint

**Mid-task work** (still iterating, debugging, exploring) → use granular table above.

**Required completion footer** — append at the END of completion responses:

```
---

## ✅ Module Completion — Restart Required

**Restart Docker container:**

    docker restart 9f007b47a78a

**Then upgrade the module:** Apps → search module → Upgrade

_Why: ensures fresh container state after module completion._
```

**Container ID note**: `9f007b47a78a` is Andyka's current container ID. If the command fails (container recreated), Andyka can find the new ID via `docker ps` and update this file. Do NOT silently substitute a guessed ID.

**During mid-task**, still use the lightweight format:
> ⚠️ **Jangan lupa restart Odoo + upgrade module** — alasan: \<one line\>

…OR for non-restart changes:
> 🔄 **Cukup upgrade module saja** (XML/data change)
> 🌐 **Hard refresh browser saja** (asset change)

## When Confused

If a request is ambiguous, ASK (max 3 focused questions). When in doubt about which module/file is involved, USE codebase search rather than guessing.

For deeper Odoo 18 patterns and full debug protocols, switch to the **Odoo 18 Expert** custom agent.
