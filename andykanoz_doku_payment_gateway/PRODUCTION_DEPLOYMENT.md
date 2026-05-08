# 🚀 Production Deployment Guide - DOKU Payment Gateway

## ✅ Pre-Deployment Checklist

Before going live with DOKU production, ensure ALL of the following:

### 1. DOKU Account Setup
- [ ] DOKU production account verified by DOKU team
- [ ] Production credentials obtained:
  - [ ] Merchant Code (Mall ID)
  - [ ] Client ID (production)
  - [ ] Secret Key (production)
- [ ] Payment channels enabled in DOKU dashboard:
  - [ ] QRIS
  - [ ] Virtual Account (selected banks)
  - [ ] E-Wallet (OVO, DANA, ShopeePay, etc.)

### 2. Sandbox Testing Completed
- [ ] Successful QRIS payment test
- [ ] Successful Virtual Account payment test
- [ ] Successful E-Wallet payment test
- [ ] Webhook notifications received correctly
- [ ] Transaction state changes correctly (pending → done)
- [ ] Sale order auto-confirmed
- [ ] Invoice auto-validated
- [ ] Email notifications sent to customer
- [ ] Failed payment handling tested
- [ ] Expired payment handling tested
- [ ] Manual "Check Status" button tested

### 3. Server Requirements
- [ ] HTTPS/SSL certificate installed (REQUIRED)
- [ ] Public domain accessible from internet
- [ ] Cloudflare Tunnel or equivalent set up
- [ ] Firewall allows incoming POST to webhook URL
- [ ] Server time is accurate (NTP sync) - signature timestamp is critical
- [ ] Python `requests` library installed in Odoo container

### 4. Odoo Configuration
- [ ] `web.base.url` set to production URL (e.g., `https://www.gopokaja.com`)
- [ ] `web.base.url.freeze` set to `True` (prevent auto-overwrite)
- [ ] Backup database before deployment
- [ ] Cron jobs enabled and active

---

## 📋 Deployment Steps

### Step 1: Backup Current Production
```bash
# Backup database
docker exec Postgres17-Odoo18 pg_dump -U postgres <db_name> > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup addons folder
tar -czf addons_backup_$(date +%Y%m%d_%H%M%S).tar.gz D:\MyServer\Odoo18\Addons
```

### Step 2: Deploy Module to Production Server
```bash
# Copy module to production addons folder
# (adjust path according to your production setup)
```

### Step 3: Update Module
```bash
docker exec -it Odoo18 odoo \
  -c /etc/odoo/odoo.conf \
  -d <production_db_name> \
  -u andykanoz_doku_payment_geteway \
  --stop-after-init
```

### Step 4: Restart Odoo
```bash
docker compose restart odoo18
```

### Step 5: Configure Production Provider in Odoo
1. Login to production Odoo as Admin
2. **Accounting → Configuration → Payment Providers**
3. Click **DOKU**
4. Tab **DOKU Configuration**:
   - **Environment**: Change to **`Production`**
   - **Merchant Code**: Production merchant code
   - **Client ID**: Production client ID
   - **Secret Key**: Production secret key
5. **SAVE**
6. Change **State** from "Test Mode" to **"Enabled"**

### Step 6: Update Webhook URL in DOKU Production Dashboard
1. Login to https://dashboard.doku.com (PRODUCTION)
2. Navigate to **Settings → Webhook** (or per-channel)
3. Set **Notification URL**: `https://your-production-domain.com/payment/doku/webhook`
4. Set **Return URL**: `https://your-production-domain.com/payment/doku/return`
5. Save

### Step 7: Smoke Test
1. Make a small test payment (e.g., Rp 1,000) using a real card/account
2. Verify:
   - [ ] Pop-up loads correctly
   - [ ] Payment processes successfully
   - [ ] Webhook received in Odoo logs
   - [ ] Transaction state = "Done"
   - [ ] Sale order confirmed
   - [ ] Invoice validated
   - [ ] Customer receives email

### Step 8: Monitor for First 24 Hours
- Watch Odoo logs: `docker logs -f Odoo18`
- Monitor DOKU dashboard for transactions
- Check webhook delivery rate
- Ensure no signature verification failures

---

## 🔐 Security Best Practices

### Production Credentials
- ❌ NEVER commit credentials to git/version control
- ❌ NEVER share Secret Key via email/chat
- ✅ Store credentials in Odoo's encrypted fields (already done)
- ✅ Use different credentials for sandbox vs production
- ✅ Rotate Secret Key periodically (every 6-12 months)
- ✅ Limit access to provider config to admin users only

### Webhook Security
- ✅ HMAC-SHA256 signature verification implemented
- ✅ Amount validation against transaction amount
- ✅ Client-Id verification
- ✅ Constant-time signature comparison (anti timing attack)
- ✅ Idempotent processing (handles duplicate webhooks safely)

### Network Security
- ✅ HTTPS only for webhook URL
- ✅ Firewall rules to limit access
- ✅ Rate limiting on webhook endpoint (recommended via Cloudflare)
- ✅ Monitoring for failed signature attempts

---

## 📊 Monitoring & Maintenance

### Daily Tasks
- Check **DOKU Payment → Transactions** menu in Odoo
- Filter by **"No Webhook Received"** to find stuck transactions
- Click **"Check Status"** on any pending transactions

### Weekly Tasks
- Review error logs for patterns
- Check cron job execution history
- Reconcile DOKU dashboard vs Odoo transactions

### Monthly Tasks
- Audit transaction logs
- Review Secret Key rotation policy
- Update DOKU API libraries if released

### Emergency Contacts
- **DOKU Support**: support@doku.com
- **DOKU Documentation**: https://developers.doku.com
- **DOKU Dashboard**: https://dashboard.doku.com

---

## 🚨 Rollback Plan

If critical issues occur after deployment:

### Quick Disable (No Rollback Needed)
1. Login to Odoo as Admin
2. **Accounting → Configuration → Payment Providers → DOKU**
3. Change **State** to **"Disabled"**
4. Customers will see DOKU option grayed out

### Full Rollback
```bash
# 1. Disable provider in Odoo (above)

# 2. Restore database backup
docker exec -i Postgres17-Odoo18 psql -U postgres <db_name> < backup_YYYYMMDD_HHMMSS.sql

# 3. Restore addons folder
tar -xzf addons_backup_YYYYMMDD_HHMMSS.tar.gz -C /

# 4. Restart Odoo
docker compose restart odoo18
```

---

## 🐛 Common Issues & Solutions

### Issue: "Invalid signature" in webhook logs
**Cause**: Secret Key mismatch or component string format error
**Solution**:
1. Verify Secret Key in Odoo matches DOKU dashboard exactly (no extra spaces)
2. Verify webhook URL path is exactly `/payment/doku/webhook`
3. Check Odoo logs for component string used in signature calculation
4. Compare with DOKU's expected signature in their logs

### Issue: Transaction stays pending after payment
**Cause**: Webhook didn't reach Odoo
**Possible reasons**:
1. Cloudflare Tunnel not running
2. Webhook URL not set in DOKU dashboard
3. Firewall blocking incoming POST
4. SSL certificate issue

**Solution**:
1. Click **"Check Status"** button on transaction (manual sync)
2. Wait for cron job (every 15 min) to auto-sync
3. Verify webhook URL accessible: `curl -I https://yourdomain.com/payment/doku/webhook`

### Issue: "Amount mismatch" error
**Cause**: Notification amount doesn't match transaction amount
**Solution**: This is a security feature. Investigate:
1. Was order amount changed after payment initiated?
2. Currency conversion issue?
3. Possible tampering attempt - check logs

### Issue: Pop-up not appearing
**Cause**: DOKU JS library blocked or not loaded
**Solution**:
1. Check browser console for errors
2. Verify ad blocker not blocking jokul-checkout-1.0.0.js
3. Module has fallback to full redirect after 5 seconds

### Issue: Multiple webhooks for same transaction
**Cause**: Normal DOKU behavior (webhook retries)
**Solution**: Module is idempotent - safe to receive multiple webhooks. Check `doku_webhook_count` field for count.

---

## 📞 Support

For issues with this module:
1. Check Odoo logs: `docker logs Odoo18 | grep -i doku`
2. Check transaction details in **DOKU Payment → Transactions**
3. Review webhook payload in transaction's "Debug Information" section

For DOKU-specific issues:
- DOKU Sandbox Dashboard: https://dashboard-sandbox.doku.com
- DOKU Production Dashboard: https://dashboard.doku.com
- DOKU Developer Docs: https://developers.doku.com

---

**Last Updated**: April 30, 2026
**Module Version**: 18.0.1.0.0
**Status**: Production Ready ✅
