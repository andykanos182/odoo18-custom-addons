# 🎓 SKILL: Odoo 18 Payment Provider Pattern — Lessons from Xendit Module

> **Source studied**: `D:\MyServer\Odoo18\Source Code Odoo18\payment_xendit\` (Odoo Enterprise, official module)
>
> **Context**: This module is the canonical reference for building custom payment providers in Odoo 18. Studying it revealed several critical patterns we were doing wrong in our DOKU module.
>
> **When to use this skill**: Any time you build or fix a custom payment provider for Odoo 17/18.

---

## 🎯 The 12 Patterns

### 1. Use `setup_provider()` Helper, NOT Manual Linking

**❌ WRONG** (what AI Gemini did in DOKU):
```xml
<record id="payment_provider_doku" model="payment.provider">
    <field name="payment_method_ids" eval="[(6, 0, [
        ref('payment.payment_method_qris'),
        ref('payment.payment_method_bank_bca'),
        ...
    ])]"/>
</record>
```

**✅ RIGHT** (Xendit pattern):
```python
# __init__.py
from odoo.addons.payment import setup_provider, reset_payment_provider

def post_init_hook(env):
    setup_provider(env, 'xendit')

def uninstall_hook(env):
    reset_payment_provider(env, 'xendit')
```

**Why**: `setup_provider()` reads `_get_default_payment_method_codes()` from your provider model and links matching `payment.method` records automatically. It's the official Odoo pattern, handles edge cases, and survives upgrades.

---

### 2. Override `_get_default_payment_method_codes()` Correctly

```python
# models/payment_provider.py
def _get_default_payment_method_codes(self):
    """ Override of `payment` to return the default payment method codes. """
    default_codes = super()._get_default_payment_method_codes()
    if self.code != 'xendit':
        return default_codes
    return const.DEFAULT_PAYMENT_METHOD_CODES  # Returns a SET of strings
```

**Critical**:
- Must call `super()` first (chain compatibility)
- Must check `self.code` (only apply for your provider)
- Must return a **set/frozenset/list of strings** matching existing `payment.method.code` values
- Codes must be **lowercase** and match Odoo's payment.method records

---

### 3. `DEFAULT_PAYMENT_METHOD_CODES` is a SET of Lowercase Strings

```python
# const.py
DEFAULT_PAYMENT_METHOD_CODES = {
    'card', 'qris', 'ovo', 'dana', 'shopeepay',
    'bank_bca', 'bank_permata',  # Some banks use 'bank_' prefix
    'mandiri', 'bni', 'bri',     # Others don't (Odoo inconsistency)
    'kredivo', 'akulaku',
}
```

**Notice**: Code naming is **inconsistent in Odoo core** — some banks have `bank_` prefix, some don't. Always verify by looking at actual `payment.method` records:
```python
env['payment.method'].search([('code', 'like', 'bank_%')]).mapped('code')
```

---

### 4. Use `noupdate="1"` to Prevent Upgrade Resets

**❌ WRONG** (what was happening in DOKU):
```xml
<odoo>
    <data noupdate="0">  <!-- Will RESET on every upgrade! -->
        <record id="payment_provider_doku" model="payment.provider">
            <field name="state">disabled</field>  <!-- Resets user's "Test Mode" choice -->
        </record>
    </data>
</odoo>
```

**✅ RIGHT** (Xendit pattern):
```xml
<odoo noupdate="1">  <!-- Prevents reset on upgrade -->
    <record id="payment_provider_xendit" model="payment.provider">
        <field name="code">xendit</field>
        <field name="redirect_form_view_id" ref="redirect_form"/>
    </record>
</odoo>
```

**Why**:
- `noupdate="1"` = record only created on FIRST install, never updated by upgrades
- User customizations (like state="test", credentials) PERSIST across upgrades
- Use `noupdate="0"` only if you intentionally want to push updates to all installations

**Special case**: Xendit puts `noupdate="1"` directly on the `<odoo>` tag (not on `<data>`). Both work, but the `<odoo noupdate="1">` form is more idiomatic in Odoo 18.

---

### 5. Provider Data XML — Keep It MINIMAL

Xendit's full data XML is just 6 lines:
```xml
<odoo noupdate="1">
    <record id="payment.payment_provider_xendit" model="payment.provider">
        <field name="code">xendit</field>
        <field name="redirect_form_view_id" ref="redirect_form"/>
        <field name="inline_form_view_id" ref="inline_form"/>
    </record>
</odoo>
```

**Don't define in XML**:
- `state` — let user control via UI
- `payment_method_ids` — let `setup_provider()` handle
- Default flag values like `allow_tokenization`, `capture_manually` — defaults from Python field definition are sufficient
- `module_id` — auto-set by Odoo

**DO define in XML**:
- `code` (required for selection field)
- `redirect_form_view_id` (reference to your QWeb template)
- `inline_form_view_id` (if using inline form, e.g. for credit card)
- `name` (display name — but only if different from auto-generated)

---

### 6. View Inheritance Pattern — Use Named Group, Not XPath

**❌ WRONG** (what we did in DOKU before):
```xml
<xpath expr="//page[@name='credentials']" position="inside">
    <group invisible="code != 'doku'">
        <field name="doku_client_id"/>
    </group>
</xpath>
```

**✅ RIGHT** (Xendit pattern):
```xml
<group name="provider_credentials" position="inside">
    <group invisible="code != 'xendit'">
        <field name="xendit_public_key"
               required="code == 'xendit' and state != 'disabled'"
               password="True"/>
    </group>
</group>
```

**Why**:
- `group name="provider_credentials"` is the official extension point
- More resilient to Odoo internal restructuring
- Cleaner — no XPath maintenance
- Standard pattern across all official payment provider modules

---

### 7. Required-If-Provider-Active Pattern

```xml
<field name="xendit_public_key"
       required="code == 'xendit' and state != 'disabled'"/>
```

**Why**: Only require credential when:
- Provider is your specific code (`code == 'xendit'`)
- AND not disabled (`state != 'disabled'`)

This lets users save the provider as disabled while still missing credentials, which is needed during initial setup.

---

### 8. Status Mapping — Tuple-Based Buckets

```python
# const.py
PAYMENT_STATUS_MAPPING = {
    'draft': (),
    'pending': ('PENDING',),  # Note: trailing comma for tuple!
    'done': ('SUCCEEDED', 'PAID', 'CAPTURED'),
    'cancel': ('CANCELLED', 'EXPIRED'),
    'error': ('FAILED',),
}
```

**Usage in payment_transaction.py**:
```python
if payment_status in const.PAYMENT_STATUS_MAPPING['done']:
    self._set_done()
elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
    self._set_canceled()
```

**Why**: Cleaner than nested if/elif on individual statuses; also supports providers that have multiple "done" statuses (like Xendit's SUCCEEDED/PAID/CAPTURED).

---

### 9. Webhook Token Verification with `consteq`

```python
from odoo.tools import consteq
from werkzeug.exceptions import Forbidden

def _verify_notification_token(self, received_token, tx_sudo):
    if not received_token:
        raise Forbidden()  # Missing token
    if not consteq(tx_sudo.provider_id.xendit_webhook_token, received_token):
        raise Forbidden()  # Token mismatch
```

**Why `consteq` not `==`**:
- Constant-time comparison
- Resistant to timing attacks
- Required by Odoo security guidelines for any secret comparison

---

### 10. Standard Webhook Controller Pattern

```python
class XenditController(http.Controller):
    _webhook_url = '/payment/xendit/webhook'
    _return_url = '/payment/xendit/return'

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def xendit_webhook(self):
        data = request.get_json_data()
        try:
            received_token = request.httprequest.headers.get('x-callback-token')
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'xendit', data
            )
            self._verify_notification_token(received_token, tx_sudo)
            tx_sudo._handle_notification_data('xendit', data)
        except ValidationError:
            _logger.exception("Unable to handle notification data; skipping to acknowledge.")
        return request.make_json_response(['accepted'], status=200)
```

**Key takeaways**:
- Always `auth='public'` (webhook from external service, no Odoo session)
- Always `csrf=False` (external service can't include CSRF token)
- Always wrap in try/except — return 200 even on error to prevent retry storms
- Use `_get_tx_from_notification_data()` then `_handle_notification_data()` chain
- Don't manually update tx state — let `_process_notification_data()` do it

---

### 11. Override `_process_notification_data()` for State Updates

```python
def _process_notification_data(self, notification_data):
    super()._process_notification_data(notification_data)
    if self.provider_code != 'xendit':
        return

    self.provider_reference = notification_data.get('id')

    payment_status = notification_data.get('status')
    if payment_status in const.PAYMENT_STATUS_MAPPING['done']:
        self._set_done()  # Auto-handles invoice, sale order, email
    elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
        self._set_canceled()
    elif payment_status in const.PAYMENT_STATUS_MAPPING['error']:
        self._set_error(_("..."))
```

**Why this matters**: `_set_done()`, `_set_canceled()`, etc. are NOT just status setters. They trigger:
- Invoice reconciliation
- Sale order confirmation
- Email notifications
- State machine transitions
- Tokenization (if `tokenize=True`)

Don't manually do `self.state = 'done'` — always use `_set_done()` etc.

---

### 12. Redirect Form — Super Simple Template

```xml
<template id="redirect_form">
    <form t-att-action="api_url" method="get"/>
</template>
```

**Just a form with `t-att-action`**. Odoo's payment.js auto-submits it. Don't add JavaScript, don't add buttons, don't add styling. The user shouldn't even see this template — it's a vehicle for redirect.

**Pass `api_url`** (or your provider's equivalent like `payment_url`) from `_get_specific_rendering_values()`:
```python
def _get_specific_rendering_values(self, processing_values):
    res = super()._get_specific_rendering_values(processing_values)
    if self.provider_code != 'xendit':
        return res
    # ... call provider API to get URL ...
    return {'api_url': payment_url}
```

---

## 🚨 Key "Gotchas" That Bit Us in DOKU

### Gotcha 1: `noupdate="0"` Resets User Preferences on Upgrade

**Symptom**: User sets state to "Test Mode", upgrades module, state goes back to "Disabled".
**Cause**: `noupdate="0"` makes Odoo re-write the record on every upgrade.
**Fix**: Use `noupdate="1"`.

### Gotcha 2: Manual `payment_method_ids` Linking Fights with `setup_provider()`

**Symptom**: Payment methods show in form, then disappear after upgrade.
**Cause**: Manual linking in XML clashes with Odoo's lifecycle expectation.
**Fix**: Use `_get_default_payment_method_codes()` + `setup_provider()` pattern.

### Gotcha 3: Importing Undefined Constants Crashes Form Load

**Symptom**: `cannot import name 'DEFAULT_PAYMENT_METHOD_CODES' from const`.
**Cause**: Method imports a constant that doesn't exist in `const.py`.
**Lesson**: Always verify constants exist BEFORE writing import statements.

### Gotcha 4: `post_init_hook` Doesn't Run on Upgrade

**Symptom**: After refactoring to use `setup_provider()`, payment methods still don't appear.
**Cause**: `post_init_hook` only runs on FIRST install, not on upgrade.
**Fix**: Either:
- (A) Bump module version + add `migrations/X.X.X.X/post-migrate.py` that calls `setup_provider()`, OR
- (B) Have user uninstall + reinstall (loses configuration), OR
- (C) Add an admin action button "Re-setup Payment Methods" that calls `setup_provider()` manually

---

## 📋 Quick Checklist When Building a New Payment Provider

- [ ] Used `setup_provider()`/`reset_payment_provider()` in hooks
- [ ] Defined `DEFAULT_PAYMENT_METHOD_CODES` in `const.py` as a set of valid codes
- [ ] Override `_get_default_payment_method_codes()` returning that set
- [ ] Data XML uses `noupdate="1"`
- [ ] Data XML is minimal (only `code`, `redirect_form_view_id`, etc.)
- [ ] No manual `payment_method_ids` linking in XML
- [ ] View extension uses `<group name="provider_credentials" position="inside">`
- [ ] Required fields use `required="code == 'X' and state != 'disabled'"`
- [ ] Webhook controller uses `consteq` for token verification
- [ ] `_process_notification_data()` calls `_set_done()`/`_set_canceled()`/etc., NOT direct state assignment
- [ ] `redirect_form` template is just `<form t-att-action="api_url" method="get"/>`
- [ ] Webhook returns 200 even on error (to prevent retry storms)
- [ ] Migration script for users upgrading from older versions

---

## 📚 References

- **Source studied**: `payment_xendit` module (Odoo Enterprise 18)
- **Key files**:
  - `__init__.py` — hooks pattern
  - `const.py` — `DEFAULT_PAYMENT_METHOD_CODES` set
  - `models/payment_provider.py` — `_get_default_payment_method_codes` override
  - `models/payment_transaction.py` — `_process_notification_data` override
  - `controllers/main.py` — webhook with `consteq`
  - `data/payment_provider_data.xml` — minimal record with `noupdate="1"`
  - `views/payment_provider_views.xml` — `group name="provider_credentials"` extension
  - `views/payment_xendit_templates.xml` — minimal redirect form

- **Other official providers to study** (in `D:\MyServer\Odoo18\Source Code Odoo18\` if available):
  - `payment_stripe` — most complex, supports tokenization, 3DS, SCA
  - `payment_paypal` — simpler, hosted checkout pattern
  - `payment_adyen` — direct API pattern
  - `payment_razorpay` — Indian gateway, similar to Xendit

---

**Created**: 2026-04-30
**Created by**: Claude (after studying Xendit module per Andyka's request)
**For**: Anyone (human or AI) building/fixing Odoo 18 payment providers
