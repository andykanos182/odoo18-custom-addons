# 🎓 SKILL: DOKU Payment Gateway Development for Odoo 18

> **Module**: `andykanoz_doku_payment_geteway`
> **Companion to**: [`XENDIT_PAYMENT_PROVIDER_PATTERN.md`](./XENDIT_PAYMENT_PROVIDER_PATTERN.md) (read this FIRST for general payment provider patterns)
> **Status**: Phase 1 (Foundation) installed; Phase 2-5 in development
> **POS Integration**: ✅ Documented in companion skill [`DOKU_QRIS_POS_DYNAMIC_SKILL.md`](./DOKU_QRIS_POS_DYNAMIC_SKILL.md)
>
> **When to use**: Any time you build, fix, or extend the DOKU payment gateway integration. This skill captures DOKU-specific knowledge that complements the generic Xendit-based pattern.

---

## 📑 Contents

1. [DOKU API Reference](#-section-1-doku-api-reference)
2. [DOKU-Specific Payment Provider Patterns](#-section-2-doku-specific-payment-provider-patterns)
3. [POS Integration → see DOKU_QRIS_POS_DYNAMIC_SKILL.md](#-section-3-pos-integration)
4. [Workflow & Conventions](#%EF%B8%8F-section-4-workflow--conventions)
5. [Decision Trees](#-section-5-decision-trees)
6. [DOKU-Specific Gotchas](#-doku-specific-gotchas)
7. [Quick Checklist](#-quick-checklist)
8. [References](#-references)

---

## 🌐 Section 1: DOKU API Reference

### 1.1 Endpoints & URLs

| Environment | Base URL | When to use |
|-------------|----------|-------------|
| Sandbox | `https://api-sandbox.doku.com` | Development, testing, demo |
| Production | `https://api.doku.com` | Live transactions only |
| Webhook (Dev) | `https://nitro.gopokaja.com/payment/doku/webhook` | Cloudflare Tunnel → Docker |
| Webhook (Prod) | `https://www.gopokaja.com/payment/doku/webhook` | Production gopokaja domain |

**Routing rule**: `payment_provider.state` controls which URL to use.
- `state == 'test'` → sandbox
- `state == 'enabled'` → production
- `state == 'disabled'` → no API calls allowed

---

### 1.2 Official Documentation — ALWAYS FETCH FRESH

**🚨 STANDING RULE**: Before writing or modifying ANY DOKU API logic, fetch the latest official documentation from:

```
https://developers.doku.com/accept-payments/doku-checkout
```

**Why this is non-negotiable**:
- DOKU API specs change without notice
- AI training data (including mine) may be months out of date
- Header names, signature formats, and field schemas have all changed historically
- Only `developers.doku.com` is the source of truth

**How to fetch**: Use `web_fetch` tool with the relevant DOKU docs URL when starting a new API integration task.

---

### 1.3 HMAC-SHA256 Signature Generation

DOKU requires every API request to be signed with `HMAC-SHA256`. The canonical implementation lives in:

```
utils/signature.py
```

**General formula** (verify against official docs before coding):

```python
import hmac
import hashlib
import base64

def generate_signature(secret_key, client_id, request_id, request_timestamp, request_target, request_body):
    """
    DOKU signature = HMAC-SHA256(string_to_sign, secret_key) → Base64

    string_to_sign typically includes:
      - Client-Id
      - Request-Id
      - Request-Timestamp (ISO 8601 UTC, e.g. 2026-05-07T08:30:00Z)
      - Request-Target (e.g. /checkout/v1/payment)
      - Digest = Base64(SHA256(request_body))
    """
    digest = base64.b64encode(
        hashlib.sha256(request_body.encode('utf-8')).digest()
    ).decode('utf-8')

    string_to_sign = (
        f"Client-Id:{client_id}\n"
        f"Request-Id:{request_id}\n"
        f"Request-Timestamp:{request_timestamp}\n"
        f"Request-Target:{request_target}\n"
        f"Digest:{digest}"
    )

    raw_sig = hmac.new(
        secret_key.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).digest()

    return f"HMACSHA256={base64.b64encode(raw_sig).decode('utf-8')}"
```

**⚠️ Critical**: The exact format of `string_to_sign` (newlines, field order, casing) is dictated by DOKU. **Always re-verify against current official docs** — even if it worked yesterday, DOKU may have updated.

---

### 1.4 Required Request Headers

Every DOKU API request typically requires these headers (verify against current docs):

| Header | Purpose | Example |
|--------|---------|---------|
| `Client-Id` | Merchant identifier from DOKU dashboard | `BRN-XXXX-XXXX` |
| `Request-Id` | Unique UUID per request (idempotency key) | `uuid.uuid4()` |
| `Request-Timestamp` | ISO 8601 UTC | `2026-05-07T08:30:00Z` |
| `Signature` | Output of `generate_signature()` | `HMACSHA256=Abc123...` |
| `Content-Type` | Always `application/json` | `application/json` |

**Idempotency**: `Request-Id` must be unique per logical request. If you retry a failed request, **reuse the same Request-Id** — DOKU dedupes by this.

---

### 1.5 Payment Methods Supported

| Method | DOKU Code | Odoo `payment.method.code` | Flow |
|--------|-----------|---------------------------|------|
| QRIS | `QRIS` | `qris` | Hosted page → user scans QR → webhook |
| Virtual Account | `VIRTUAL_ACCOUNT_*` | `bank_bca`, `bank_mandiri`, etc. | VA number issued → user transfers → webhook |
| Credit Card | `CREDIT_CARD` | `card` | Hosted page → 3D Secure → webhook |
| E-wallet | `OVO`, `DANA`, `SHOPEEPAY` | `ovo`, `dana`, `shopeepay` | Deeplink/redirect → user authorizes → webhook |

**⚠️ Important**: Odoo's `payment.method.code` values use lowercase with `bank_` prefix for some banks (inconsistent). Always verify by querying actual records:

```python
env['payment.method'].search([('code', 'like', 'bank_%')]).mapped('code')
```

(See [`XENDIT_PAYMENT_PROVIDER_PATTERN.md` Pattern 3](./XENDIT_PAYMENT_PROVIDER_PATTERN.md) for full notes on Odoo's code naming inconsistency.)

---

### 1.6 Webhook Signature Verification

DOKU sends webhook notifications to your `_webhook_url`. **Always verify the incoming signature** before trusting the payload.

```python
from odoo.tools import consteq
from werkzeug.exceptions import Forbidden

def _verify_doku_webhook_signature(self, request):
    """Verify HMAC signature on incoming DOKU webhook."""
    received_sig = request.httprequest.headers.get('Signature')
    client_id = request.httprequest.headers.get('Client-Id')
    request_id = request.httprequest.headers.get('Request-Id')
    timestamp = request.httprequest.headers.get('Request-Timestamp')
    raw_body = request.httprequest.get_data(as_text=True)

    expected_sig = generate_signature(
        secret_key=self.doku_secret_key,
        client_id=client_id,
        request_id=request_id,
        request_timestamp=timestamp,
        request_target='/payment/doku/webhook',
        request_body=raw_body,
    )

    if not consteq(expected_sig, received_sig or ''):
        raise Forbidden("Invalid DOKU webhook signature")
```

**🔒 Critical**:
- Use `consteq` (constant-time), NOT `==` — prevents timing attacks
- Verify against the **raw body bytes**, not parsed JSON (re-serializing changes whitespace and breaks signature)
- Return HTTP 200 even if signature fails — log it, but don't trigger DOKU retry storms

(See [`XENDIT_PAYMENT_PROVIDER_PATTERN.md` Pattern 9-10](./XENDIT_PAYMENT_PROVIDER_PATTERN.md) for the parallel Xendit webhook pattern.)

---

### 1.7 Status & Error Code Mapping

DOKU returns transaction states that need to be mapped to Odoo's payment states. Define these in `const.py`:

```python
# const.py
PAYMENT_STATUS_MAPPING = {
    'draft':   (),
    'pending': ('PENDING', 'PROCESSING'),
    'done':    ('SUCCESS', 'SUCCESSFUL', 'PAID', 'COMPLETED'),
    'cancel':  ('CANCELLED', 'EXPIRED', 'VOIDED'),
    'error':   ('FAILED', 'REJECTED', 'DECLINED'),
}
```

**⚠️ Verify the actual status strings** DOKU sends in YOUR webhook payloads — copy them from real test transactions, not from docs (docs may differ from actual API output).

---

## 💳 Section 2: DOKU-Specific Payment Provider Patterns

> **READ FIRST**: [`XENDIT_PAYMENT_PROVIDER_PATTERN.md`](./XENDIT_PAYMENT_PROVIDER_PATTERN.md) — covers the 12 generic patterns (`setup_provider()`, `noupdate=1`, `consteq`, `_set_done()`, etc.). This section only covers DOKU-specific differences.

### 2.1 How DOKU Differs from Xendit

| Aspect | Xendit | DOKU |
|--------|--------|------|
| Auth | API key in Basic Auth | HMAC-SHA256 signature per request |
| Webhook auth | Static token (`x-callback-token`) | HMAC signature on each webhook |
| Request body | JSON | JSON, but signed via SHA256 digest |
| Idempotency | `idempotency-key` header | `Request-Id` header (UUID) |
| Endpoints | Single base, RESTful | Different endpoints per payment method family |

**Implication**: The DOKU module needs heavier `utils/` infrastructure than Xendit — specifically `signature.py` and `api_client.py` (already present in our module).

---

### 2.2 DOKU `const.py` Skeleton

```python
# const.py

# Endpoints
SANDBOX_URL = 'https://api-sandbox.doku.com'
PRODUCTION_URL = 'https://api.doku.com'

# Payment method codes (Odoo's, lowercase, set)
DEFAULT_PAYMENT_METHOD_CODES = {
    'qris', 'card',
    'bank_bca', 'bank_mandiri', 'bank_bni', 'bank_bri', 'bank_permata',
    'ovo', 'dana', 'shopeepay',
}

# Status mapping (verify against real DOKU webhook payloads)
PAYMENT_STATUS_MAPPING = {
    'pending': ('PENDING', 'PROCESSING'),
    'done':    ('SUCCESS', 'SUCCESSFUL', 'PAID'),
    'cancel':  ('CANCELLED', 'EXPIRED'),
    'error':   ('FAILED', 'REJECTED'),
}

# Webhook target paths (used in signature generation)
WEBHOOK_TARGET = '/payment/doku/webhook'
```

---

### 2.3 Provider Model Fields

In `models/payment_provider.py`, add DOKU-specific credential fields:

```python
class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('doku', "DOKU")],
        ondelete={'doku': 'set default'},
    )
    doku_client_id = fields.Char(
        string="Client ID",
        required_if_provider='doku',
        groups='base.group_system',
    )
    doku_secret_key = fields.Char(
        string="Secret Key",
        required_if_provider='doku',
        groups='base.group_system',
    )
    doku_webhook_secret = fields.Char(
        string="Webhook Secret",
        groups='base.group_system',
        help="Optional: separate secret if DOKU issues a different one for webhook verification",
    )
```

**🔒 Why `groups='base.group_system'`**: Restricts field visibility to system administrators only. Credentials should NEVER be visible to regular users.

---

### 2.4 utils/ Module Structure

The DOKU module uses a `utils/` subfolder for cross-cutting concerns:

```
utils/
├── __init__.py        # Imports both
├── signature.py       # HMAC-SHA256 generation + verification
└── api_client.py      # HTTP wrapper, handles signing + retries + logging
```

**Pattern for `api_client.py`**:
- One method per DOKU endpoint family (`create_qris_payment`, `create_va_payment`, etc.)
- All methods go through `_signed_request(method, path, body)` internally
- Logs request/response (with secrets redacted) to `_logger`
- Raises `ValidationError` on API errors so Odoo handles them gracefully

---

## 🔌 Section 3: POS Integration

> ✅ **POS pattern researched & documented** (2026-05-07).
>
> **Use case verified**: Dynamic QRIS via DOKU SNAP API + Odoo 18 POS, modeled after `pos_paytm` source code (canonical Odoo Enterprise pattern for dynamic-QR payments).
>
> **See dedicated skill**: [`DOKU_QRIS_POS_DYNAMIC_SKILL.md`](./DOKU_QRIS_POS_DYNAMIC_SKILL.md)
>
> That skill covers:
> - DOKU SNAP API specifics (HMAC-SHA512, NOT SHA256 — critical difference from web flow)
> - Odoo 18 POS payment architecture (`pos.payment.method`, `PaymentInterface`, `register_payment_method`)
> - Module file structure for adding POS to existing module
> - Backend & frontend code skeletons (verified from `pos_paytm`)
> - Polling + webhook reconciliation strategy
> - 8 critical gotchas
> - Phased implementation checklist
>
> **Other POS payment methods (VA, Card, E-wallet)** are NOT yet documented — they would each need separate skills if implemented for POS, since their flows differ from QRIS.

---

## ⚙️ Section 4: Workflow & Conventions

### 4.1 Filesystem-First Development

When developing on Andyka's Windows + Docker setup, **write files directly** to:

```
D:\MyServer\Odoo18\Addons\andykanoz_doku_payment_geteway\
```

**Rules**:
- Use `Desktop Commander:write_file` / `edit_block` for direct disk writes
- **Never** package as ZIP and ask user to extract — wastes time, breaks iterative flow
- **Never** copy-paste artifacts into chat for the user to manually save — same reason
- If access to the path is not yet granted, **stop and ask** for access before proceeding

---

### 4.2 Module Manifest Convention

**Always** in `__manifest__.py`:

```python
{
    'name': "DOKU Payment Gateway",
    'version': '18.0.1.X.Y',  # Bump on every meaningful change
    'category': 'MyCustom/Modules',  # ← STANDING RULE
    'depends': ['payment', 'account', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/payment_provider_data.xml',
        'data/ir_cron_data.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'views/payment_doku_templates.xml',
        'views/portal_templates.xml',
        'views/doku_menu_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
```

**Never** use `'category': 'Accounting'` or `'Hidden'` — Andyka's standing convention is `MyCustom/Modules`.

---

### 4.3 Docker Operations Matrix

| Change Type | Container Restart | Module Upgrade | Hard Refresh | Asset Recompile |
|-------------|-------------------|----------------|--------------|-----------------|
| Python code (`.py`) | ✅ Required | ✅ Required | ❌ | ❌ |
| XML data files | ✅ Required | ✅ Required | ❌ | ❌ |
| XML view templates (QWeb) | ❌ | ✅ Required | ✅ Required | Sometimes |
| JS / CSS / SCSS | ❌ | ✅ Required | ✅ Required | ✅ `?debug=assets` |
| `__manifest__.py` (depends) | ✅ Required | ✅ Required | ❌ | ❌ |
| `__manifest__.py` (data list only) | ❌ | ✅ Required | ❌ | ❌ |

**Quick commands**:
```bash
docker restart Odoo18
# Then in browser: Apps → Update Apps List → DOKU → Upgrade
# For asset issues: append ?debug=assets to URL
```

---

### 4.4 Pre-Code Communication Rule

**STANDING RULE**: Before modifying any code:

1. **Explain findings fully** — what's the issue, what's the root cause, what files are affected
2. **Wait for explicit confirmation** — phrases like "yes proceed", "lanjut", "ok kerjakan"
3. **Use surgical edits** — `edit_block` with exact `oldText`/`newText` matching, NOT full file rewrites
4. **One issue at a time** — don't bundle unrelated fixes

**Why**: Andyka prefers iterative validation; bundled changes are hard to review and debug if something breaks.

---

## 🧭 Section 5: Decision Trees

### 5.1 Container Restart vs. Module Upgrade Only?

```
Did I change any .py file?              ──── YES ──→ docker restart Odoo18 + Upgrade module
                                                       │
                                         ──── NO  ──→ ▼
Did I change any data XML (data/*.xml)? ──── YES ──→ docker restart Odoo18 + Upgrade module
                                                       │
                                         ──── NO  ──→ ▼
Did I change any view XML, JS, or CSS?  ──── YES ──→ Upgrade module + Hard refresh (Ctrl+Shift+R)
                                                       │
                                         ──── NO  ──→ ▼
Still broken?                          ──── YES ──→ Append ?debug=assets to URL → forces recompile
```

---

### 5.2 `noupdate="0"` vs. `noupdate="1"`?

```
Is the record an initial setup that user will customize?  ──── YES ──→ noupdate="1"
                                                                       (e.g., payment.provider record)
                                                            │
                                                  ──── NO  ──→ ▼
Do I need every install/upgrade to RESET it to my version? ── YES ──→ noupdate="0"
                                                                       (rare; e.g. fixing a typo in
                                                                        an ir.cron schedule across
                                                                        all customer installs)
                                                            │
                                                  ──── NO  ──→ ▼
                                                  Default: noupdate="1"
```

**Rule of thumb**: Use `noupdate="1"` for `payment.provider`, `payment.method`, `ir.cron`, and any record users are expected to configure. See [`XENDIT_PAYMENT_PROVIDER_PATTERN.md` Pattern 4 + Gotcha 1](./XENDIT_PAYMENT_PROVIDER_PATTERN.md).

---

### 5.3 Sandbox vs. Production?

```
provider.state == 'test'      ──→ Use api-sandbox.doku.com
provider.state == 'enabled'   ──→ Use api.doku.com
provider.state == 'disabled'  ──→ Don't make API calls; UI should hide DOKU option
```

**Implementation**: Add a computed property on the provider:

```python
@api.depends('state')
def _compute_doku_api_url(self):
    for rec in self:
        rec.doku_api_url = (
            'https://api-sandbox.doku.com' if rec.state == 'test'
            else 'https://api.doku.com'
        )
```

---

### 5.4 Async vs. Sync Payment Flow?

```
Method requires user interaction outside Odoo? (QR scan, OTP, redirect)  ── YES ──→ ASYNC
                                                                                    Use redirect_form
                                                                                    + webhook
                                                                          │
                                                                ──── NO  ──→ ▼
Direct charge with token (saved card, no 3DS)?                  ── YES ──→ SYNC
                                                                            Call _process_notification_data
                                                                            inline after API response
                                                                          │
                                                                ──── NO  ──→ ▼
                                                                Default: ASYNC
                                                                (safer; webhook is single source of truth)
```

**Why prefer async**: Webhooks are DOKU's authoritative event source. Even sync flows should re-confirm via webhook to avoid race conditions where the user closes their browser before the API response is processed.

---

### 5.5 Handling Webhook Signature Failures

```
Signature mismatch on incoming webhook?  ──→ Log full headers + body (with secrets redacted)
                                              │
                                              ▼
                                          Return HTTP 200 (NOT 403/401)
                                              │
                                              ▼
                                          Why? — DOKU will retry on non-2xx,
                                          flooding your logs. Returning 200
                                          drops the bad request silently.
                                              │
                                              ▼
                                          Manually inspect logs to detect
                                          attacks vs. config drift.
```

---

## 🚨 DOKU-Specific Gotchas

### Gotcha 1: Signature Fails Even Though Code "Looks Right"

**Symptom**: API returns `401 Invalid Signature`, but local signature looks correct.

**Most common causes**:
- `request_body` was re-serialized between signing and sending (whitespace/order changed)
- Timestamp is in local timezone, not UTC
- `Request-Target` includes query string (it shouldn't, usually)
- Secret key has trailing whitespace from copy-paste

**Debug**: Log the EXACT `string_to_sign` and the EXACT body bytes sent. Compare byte-for-byte against DOKU's signature playground if available.

---

### Gotcha 2: Webhook Never Arrives in Local Dev

**Symptom**: Test transaction succeeds in DOKU dashboard, but Odoo never updates.

**Most common causes**:
- DOKU webhook URL points to `localhost` (DOKU can't reach it)
- Cloudflare Tunnel (`nitro.gopokaja.com`) is down
- Tunnel domain not whitelisted in DOKU dashboard
- Odoo controller route has typo (`/payment/doku/webook` etc.)

**Debug**:
1. Check Cloudflare Tunnel status: `cloudflared tunnel list`
2. Test webhook manually: `curl -X POST https://nitro.gopokaja.com/payment/doku/webhook -d '{}'`
3. Check Odoo logs for ANY webhook hit (even rejected ones)
4. Verify DOKU dashboard webhook URL config

---

### Gotcha 3: Module State Resets on Upgrade

Same as `XENDIT_PAYMENT_PROVIDER_PATTERN.md` Gotcha 1 — solved by `noupdate="1"` on data XML.

---

### Gotcha 4: `post_init_hook` Doesn't Fire on Upgrade

Same as `XENDIT_PAYMENT_PROVIDER_PATTERN.md` Gotcha 4. Solution for DOKU:

```python
# migrations/18.0.1.0.X/post-migrate.py
from odoo.addons.payment import setup_provider

def migrate(cr, version):
    from odoo.api import Environment, SUPERUSER_ID
    env = Environment(cr, SUPERUSER_ID, {})
    setup_provider(env, 'doku')
```

---

### Gotcha 5: `payment_provider_FIXED.py` Detected in Module

**Symptom**: File `models/payment_provider_FIXED.py` exists alongside `payment_provider.py`.

**Cause**: Earlier debug iteration left a backup file.

**Fix**: This is technical debt — the `FIXED` file should be reviewed and either:
- (A) Merged into `payment_provider.py` if it has the working version, OR
- (B) Deleted if it's stale

**Action item**: Check this file's status and clean up before Phase 2 starts.

---

## 📋 Quick Checklist

Use this when starting any DOKU development task:

**Before writing API code**:
- [ ] Fetched current docs from `developers.doku.com/accept-payments/doku-checkout`
- [ ] Verified header names against current docs
- [ ] Verified signature format against current docs
- [ ] Verified status codes against current docs

**Before committing module changes**:
- [ ] Followed [`XENDIT_PAYMENT_PROVIDER_PATTERN.md`](./XENDIT_PAYMENT_PROVIDER_PATTERN.md) checklist
- [ ] `'category': 'MyCustom/Modules'` in `__manifest__.py`
- [ ] Used `Desktop Commander:write_file` / `edit_block` (filesystem-first)
- [ ] Bumped version in `__manifest__.py` if any logic changed
- [ ] Added migration script if changing `setup_provider()` behavior
- [ ] Logged but didn't expose secrets in any log statement
- [ ] Used `consteq` for any secret comparison
- [ ] Tested in sandbox before considering anything done

**Before asking user to test**:
- [ ] Restarted Docker if `.py` or data XML changed
- [ ] Upgraded module
- [ ] Suggested `?debug=assets` if JS/CSS changed
- [ ] Stated what user should look for (success criteria)

**Workflow hygiene**:
- [ ] Explained findings to Andyka BEFORE editing
- [ ] Got explicit confirmation BEFORE editing
- [ ] Made surgical edits (not full file rewrites)
- [ ] One issue per edit cycle

---

## 📚 References

### Internal (this module)

- **`utils/signature.py`** — canonical HMAC-SHA256 implementation for DOKU
- **`utils/api_client.py`** — HTTP wrapper with auto-signing
- **`models/payment_provider.py`** — provider model with DOKU credentials
- **`models/payment_transaction.py`** — transaction state handling
- **`controllers/main.py`** — webhook + return URL handlers
- **`HANDOFF/HANDOFF_TO_NEXT_AI.md`** — full project state for AI handoff
- **`HANDOFF/PENDING_PAYMENT_STRATEGIES.md`** — strategic decisions log
- **`HANDOFF/skills/XENDIT_PAYMENT_PROVIDER_PATTERN.md`** — generic Odoo 18 payment provider patterns

### External

- **DOKU Official Docs**: https://developers.doku.com/
- **DOKU Checkout Docs**: https://developers.doku.com/accept-payments/doku-checkout
- **DOKU Dashboard**: https://dashboard.doku.com/
- **Odoo 18 Payment Providers Docs**: https://www.odoo.com/documentation/18.0/applications/finance/payment_providers.html
- **Odoo Payment Module Source** (study reference): `D:\MyServer\Odoo18\Source Code Odoo18\payment_xendit\`

---

**Created**: 2026-05-07
**Created by**: Claude (per Andyka's request to consolidate DOKU dev knowledge)
**Status**: Section 3 (POS) deferred — update when verified pattern is established
**Companion file**: [`XENDIT_PAYMENT_PROVIDER_PATTERN.md`](./XENDIT_PAYMENT_PROVIDER_PATTERN.md)
