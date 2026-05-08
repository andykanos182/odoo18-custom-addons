# 🔧 Refactor Notes — Xendit Pattern Migration

**Date**: 2026-04-30
**Version**: 18.0.1.0.0 → 18.0.1.0.1
**Reason**: Payment methods kept disappearing after upgrade; ImportError on save

---

## 🎯 What Changed

This refactor migrates the DOKU module from a **fragile XML-based** approach
to the **official Odoo `setup_provider()` pattern**, as used by Odoo Enterprise's
own `payment_xendit` module.

### Files Modified

| File | Change |
|------|--------|
| `const.py` | ➕ Added `DEFAULT_PAYMENT_METHOD_CODES` (set of valid codes) |
| `hooks.py` | ✏️ Now uses `setup_provider`/`reset_payment_provider` helpers |
| `models/payment_provider.py` | ✏️ Added correct `_get_default_payment_method_codes()` override |
| `data/payment_provider_data.xml` | ✏️ Removed manual `payment_method_ids`, used `noupdate="1"` |
| `__manifest__.py` | 🔢 Version bump 1.0.0 → 1.0.1 |
| `migrations/18.0.1.0.1/post-migrate.py` | ➕ New migration script |

### Files Documented

| File | Purpose |
|------|---------|
| `HANDOFF/skills/XENDIT_PAYMENT_PROVIDER_PATTERN.md` | Full skill doc — Xendit patterns |
| `HANDOFF/REFACTOR_NOTES_XENDIT_PATTERN.md` | This file — what & why of this refactor |

---

## 🐛 Bugs Fixed

### Bug 1: Payment methods disappear after upgrade
**Root cause**: `data/payment_provider_data.xml` had `<data noupdate="0">`,
which RESETS the record on every upgrade — including `state="disabled"` and
the manually-linked `payment_method_ids`.

**Fix**: Changed to `<odoo noupdate="1">` (Xendit pattern). The record is only
created on first install, never overwritten. `payment_method_ids` is now
auto-managed by `setup_provider()`.

### Bug 2: `cannot import name 'DEFAULT_PAYMENT_METHOD_CODES'`
**Root cause**: Method `_get_default_payment_method_codes()` in `payment_provider.py`
imported a constant from `const.py` that was never defined.

**Fix**: Defined the constant in `const.py` AND simplified the import (now top-level
instead of inside the method).

### Bug 3: User customizations (state, credentials) reset on upgrade
**Root cause**: Same as Bug 1 (`noupdate="0"`).

**Fix**: Same as Bug 1 (`noupdate="1"` + minimal XML record).

---

## 🔄 Migration for Existing Users

For users (like Andyka) who already had the old version installed:

The migration script `migrations/18.0.1.0.1/post-migrate.py` will:
1. Run automatically when the module upgrades from any older version to 18.0.1.0.1+
2. Call `setup_provider(env, 'doku')` which re-links payment methods properly
3. Log success/failure to Odoo logs

After upgrade, user should:
1. Verify payment methods reappear in **Accounting → Configuration → Payment Providers → DOKU**
2. Set state to "Test Mode" (this should now PERSIST across future upgrades)
3. Re-enter credentials if they were lost (shouldn't happen with `noupdate="1"`)

---

## 🚧 Out of Scope (Preserved As-Is)

This refactor focused ONLY on payment method linking. The following were
NOT touched:

- ✅ Strategy 2 implementation (Tokopedia-style pending page)
- ✅ Custom controllers (`/payment/doku/pending/<id>`, `/cancel/<id>`)
- ✅ Portal banner ("Lanjutkan Pembayaran")
- ✅ Webhook signature verification (HMAC-SHA256)
- ✅ Cron jobs (auto-sync, auto-expire)
- ✅ Custom DOKU fields (Client ID, Secret Key, Merchant Code, Environment)
- ✅ Test Connection button logic
- ✅ Pop-up overlay vs full redirect (kept as full redirect per user choice)

Strategy 3 (DOKU Direct API + SNAP) explicitly NOT addressed per user request.

---

## 📚 References

- **Skill doc**: `HANDOFF/skills/XENDIT_PAYMENT_PROVIDER_PATTERN.md` (12 patterns explained)
- **Studied module**: `D:\MyServer\Odoo18\Source Code Odoo18\payment_xendit\`
- **Related issue**: User reported payment methods disappearing after upgrade
- **DOKU Strategy 2 docs**: `HANDOFF/HANDOFF_STRATEGY_2_SEMI_TOKOPEDIA.md` (Gemini)
