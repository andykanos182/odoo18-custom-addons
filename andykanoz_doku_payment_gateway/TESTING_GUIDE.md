# 🧪 Testing Guide - DOKU Payment Gateway

Module sudah **100% selesai**! Sekarang saatnya testing end-to-end.

## 📋 Pre-Test Setup

### 1. Restart & Upgrade
```bash
# Di terminal Anda
cd D:\MyServer\Odoo18
docker compose restart odoo18
```

Lalu buka https://nitro.gopokaja.com:
- **Apps** → search "**DOKU**" → Click **Upgrade**

### 2. Verify `web.base.url`
1. Aktifkan **Developer Mode** (Settings → Developer Mode)
2. **Settings → Technical → System Parameters**
3. Cari `web.base.url` → Pastikan: `https://nitro.gopokaja.com`
4. Jika belum ada `web.base.url.freeze` → Buat baru: key=`web.base.url.freeze`, value=`True`

### 3. Configure DOKU Provider
1. **Accounting → Configuration → Payment Providers**
2. Klik **DOKU**
3. Tab **DOKU Configuration**:
   - **Environment**: `Sandbox`
   - **Merchant Code**: <paste sandbox merchant code>
   - **Client ID**: <paste sandbox client ID>
   - **Secret Key**: <paste sandbox secret key>
   - **Payment Expiry (Minutes)**: 60
   - ✅ Enable QRIS
   - ✅ Enable Virtual Account
   - ✅ Enable E-Wallet
4. **Save**
5. Header form: **State** → ubah ke **`Test Mode`**

### 4. Configure Webhook di DOKU Dashboard
1. Login: https://dashboard-sandbox.doku.com
2. **Settings → Webhook** (atau **Configuration → Notification URL** per channel)
3. Set **Notification URL**: `https://nitro.gopokaja.com/payment/doku/webhook`
4. Set **Return URL**: `https://nitro.gopokaja.com/payment/doku/return`
5. Save

---

## 🧪 Test Scenarios

### Test 1: QRIS Payment ✅

#### Steps:
1. **Sales → Orders → Create**
2. Pilih customer (e.g., "YourBrand")
3. Tambah product → Confirm
4. Klik **Send by Email** → kirim portal access ke customer
5. Atau: **Action → Preview Order** → bayar sebagai customer
6. Klik **Pay** → Pilih **DOKU**
7. **Pop-up DOKU muncul** ✨
8. Pilih **QRIS**
9. Buka [DOKU Simulator](https://sandbox.doku.com/integration/simulator/)
10. Input invoice number yang muncul → klik **Simulate Success**

#### Expected Result:
- ✅ Pop-up DOKU loads
- ✅ QR code terdisplay
- ✅ Webhook diterima (cek logs)
- ✅ Transaction state = **Done**
- ✅ Sale Order **confirmed**
- ✅ Invoice **validated**
- ✅ Email confirmation terkirim

#### Verify di Odoo:
1. **DOKU Payment → Transactions** (menu baru!)
2. Klik transaction yang baru
3. Tab **DOKU Details**:
   - `doku_webhook_count` = 1 (atau lebih)
   - `doku_last_webhook_status` = `SUCCESS`
   - `doku_paid_at` terisi
   - `doku_payment_method` = `qris`
   - `doku_payment_channel` = `QRIS`

---

### Test 2: Virtual Account Payment ✅

#### Steps:
1. Buat Sale Order baru
2. Pay → Pilih DOKU
3. Pop-up muncul → Pilih **Virtual Account → BCA** (atau bank lain)
4. DOKU akan tampilkan VA number
5. Buka DOKU Simulator → Input invoice → Simulate Success

#### Verify:
- ✅ `doku_payment_method` = `virtual_account`
- ✅ `doku_va_number` terisi
- ✅ `doku_acquirer` = `BCA` (atau bank yang dipilih)
- ✅ `doku_payment_channel` = `VIRTUAL_ACCOUNT_BCA`

---

### Test 3: E-Wallet Payment ✅

#### Steps:
1. Buat Sale Order baru
2. Pay → DOKU
3. Pilih **E-Wallet → OVO** (atau DANA/ShopeePay)
4. Simulate di DOKU Simulator

#### Verify:
- ✅ `doku_payment_method` = `ewallet`
- ✅ `doku_acquirer` = `OVO` / `DANA` / `SHOPEEPAY`
- ✅ Transaction success flow normal

---

### Test 4: Manual Status Check 🔄

#### Steps:
1. Buat transaksi pending (jangan simulate dulu)
2. Buka transaksi di Odoo
3. Tab **DOKU Details**
4. Klik tombol **Check Status**

#### Expected:
- ✅ Notification muncul: "Status check complete"
- ✅ State updated jika sudah dibayar (atau tetap pending)
- ✅ `doku_last_status_check_at` terisi

---

### Test 5: Auto-Cron Status Sync 🤖

#### Steps:
1. Buat 1-2 transaksi pending
2. Activate Developer Mode
3. **Settings → Technical → Scheduled Actions**
4. Cari **"DOKU: Check Pending Transactions"**
5. Klik **Run Manually**

#### Expected (di logs):
```
DOKU Cron: Checking status of X pending transactions
```

---

### Test 6: Failed Payment 💥

#### Steps:
1. Buat transaksi
2. Di DOKU Simulator → Pilih **Simulate Failed**

#### Expected (per DOKU best practice):
- ✅ Webhook diterima dengan status FAILED
- ✅ Transaction **TIDAK** berubah ke error (sengaja, customer bisa retry)
- ✅ `doku_last_webhook_status` = `FAILED`
- ✅ Log: "FAILED notification - IGNORED (customer may retry)"

Customer bisa retry dengan method lain.

---

### Test 7: Expired Transaction ⏰

#### Steps:
1. Buat transaksi
2. Tunggu sampai `doku_expired_at` terlewati (atau ubah manual untuk testing)
3. Activate Developer Mode
4. **Settings → Technical → Scheduled Actions**
5. Run **"DOKU: Expire Old Pending Transactions"**

#### Expected:
- ✅ Transaction state berubah ke **Cancelled**
- ✅ Log: "Expired transaction X marked as cancelled"

---

## 🐛 Troubleshooting

### Pop-up tidak muncul
1. Buka **Browser Console** (F12)
2. Cari error tentang `jokul-checkout`
3. Pastikan tidak ada ad blocker
4. Coba browser lain

### Webhook tidak diterima
1. Cek **Cloudflare Tunnel** masih running:
   ```bash
   docker ps | findstr cloudflared
   ```
2. Test webhook URL accessible:
   ```bash
   curl -X POST https://nitro.gopokaja.com/payment/doku/webhook -d "{}"
   ```
   Should return JSON error (bukan 404)
3. Cek webhook URL di DOKU Dashboard sudah benar

### "Invalid signature" error
1. Pastikan Secret Key di Odoo **EXACT** sama dengan DOKU Dashboard
2. Tidak ada extra space di awal/akhir
3. Cek logs:
   ```bash
   docker logs Odoo18 | grep -i "DOKU webhook"
   ```

### Transaction stuck pending
1. Klik tombol **Check Status** di transaction
2. Atau tunggu cron 15 menit
3. Atau run manual cron di Settings → Scheduled Actions

---

## ✅ Final Verification Checklist

Setelah semua test pass:

- [ ] QRIS payment works end-to-end
- [ ] Virtual Account payment works end-to-end
- [ ] E-Wallet payment works end-to-end
- [ ] Webhook signature verification working
- [ ] Auto-invoice validation working
- [ ] Sale order auto-confirmation working
- [ ] Customer email notifications working
- [ ] Manual "Check Status" button working
- [ ] Cron jobs running correctly
- [ ] Failed payment properly ignored (per DOKU spec)
- [ ] Expired payments auto-cancelled
- [ ] DOKU Transactions menu showing data
- [ ] Filters & grouping working in transactions list

---

## 🚀 After All Tests Pass

Module is **PRODUCTION READY**!

Selanjutnya:
1. Baca **PRODUCTION_DEPLOYMENT.md** untuk deploy ke production
2. Get DOKU production credentials
3. Update production webhook URL
4. Switch environment to "Production"
5. Change state ke "Enabled"
6. Test small amount real payment
7. Monitor 24 hours

🎉 **Selamat! Module DOKU Payment Gateway untuk Odoo 18 selesai!**

---

**Last Updated**: April 30, 2026
