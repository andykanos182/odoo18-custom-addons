# DOKU Payment Gateway - Phase 3 Testing Checklist

## ✅ What's Been Implemented

### Phase 1 (Completed) ✅
- Module structure
- Configuration UI (Provider tab)
- Payment provider/transaction models with DOKU fields

### Phase 3 (Current) ✅
- ✅ DOKU API Client (`utils/api_client.py`)
- ✅ HMAC-SHA256 Signature Generator (`utils/signature.py`)
- ✅ Real `_get_specific_rendering_values()` calling DOKU API
- ✅ Pop-up overlay frontend (DOKU JS library)
- ✅ Webhook controller with basic processing
- ✅ Return URL handler

## 🧪 Testing Steps

### Pre-test Checklist
1. ✅ Module installed in Odoo 18
2. ⚠️ **Restart Odoo server** (required - new files added)
3. ⚠️ **Upgrade module** (Apps → DOKU Payment Gateway → Upgrade)
4. ⚠️ Configure DOKU credentials:
   - Go to: Accounting → Configuration → Payment Providers
   - Click "DOKU"
   - Tab "DOKU Configuration":
     - Environment: Sandbox
     - Merchant Code: <your sandbox merchant code>
     - Client ID: <your sandbox client ID>
     - Secret Key: <your sandbox secret key>
   - Save
   - Change State to "Test Mode" (top of provider form)

### Test 1: Create Test Transaction (via Sale Order)
1. Create a Sales Order with a customer
2. Send the order to customer (or use your own portal access)
3. As customer, click "Pay Now"
4. Select "DOKU" payment method
5. Click "Pay"

**Expected Result:**
- DOKU popup should appear over the page
- Customer can select QRIS / VA / E-Wallet
- After payment simulation in sandbox, customer returns to /payment/status

### Test 2: Webhook Reception
- Use ngrok or public URL for local testing:
  ```
  ngrok http 8018
  ```
- Configure webhook URL in DOKU Dashboard:
  - Settings → Notification URL → https://your-ngrok-url.ngrok.io/payment/doku/webhook
- Make a sandbox payment
- Check Odoo logs for "DOKU Webhook received"

### Test 3: Manual Status Check
1. Open any DOKU transaction in Odoo
2. Click "Check Status" button on transaction form
3. Should show DOKU API response

## 🐛 Common Issues & Solutions

### Issue: "DokuAuthenticationError"
- Cause: Invalid Client ID / Secret Key
- Solution: Re-verify credentials in DOKU dashboard

### Issue: "Module not loading after restart"
- Cause: Python files cached
- Solution: Restart Odoo with `--update=andykanoz_doku_payment_geteway`

### Issue: Popup doesn't appear
- Cause: DOKU JS library blocked or not loaded
- Solution: Check browser console for errors
- Fallback: Module auto-redirects after 5 seconds

### Issue: Webhook not received
- Cause: URL not accessible from internet (localhost)
- Solution: Use ngrok or deploy to staging server

## 📊 Files Modified in Phase 3

```
andykanoz_doku_payment_geteway/
├── const.py                          [UPDATED - real DOKU codes]
├── models/
│   └── payment_transaction.py        [UPDATED - real API integration]
├── controllers/
│   └── main.py                       [UPDATED - webhook processing]
├── views/
│   └── payment_doku_templates.xml    [UPDATED - popup overlay]
└── utils/                            [NEW DIRECTORY]
    ├── __init__.py                   [NEW]
    ├── signature.py                  [NEW - HMAC-SHA256 signing]
    └── api_client.py                 [NEW - DOKU API wrapper]
```

## 🚧 Phase 4 (Next - Webhook Signature Verification)

Will implement:
- HMAC-SHA256 signature verification on incoming webhooks
- Auto-invoice validation on payment success
- Payment journal entry creation
- Email notifications

## 📚 Official DOKU References

- Backend Integration: https://developers.doku.com/accept-payments/doku-checkout/integration-guide/backend-integration
- Frontend Integration: https://developers.doku.com/accept-payments/doku-checkout/integration-guide/frontend-integration
- Signature Generation: https://developers.doku.com/get-started-with-doku-api/signature-component/non-snap/signature-component-from-request-header
- Simulate Payment: https://developers.doku.com/accept-payments/doku-checkout/integration-guide/simulate-payment-and-notification
- Sandbox Demo: https://sandbox.doku.com/demo/checkout-api
