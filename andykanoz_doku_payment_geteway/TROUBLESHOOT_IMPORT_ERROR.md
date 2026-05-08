# 🐛 Troubleshoot: DEFAULT_PAYMENT_METHOD_CODES Import Error

## Error yang Muncul
```
cannot import name 'DEFAULT_PAYMENT_METHOD_CODES' from
'odoo.addons.andykanoz_doku_payment_geteway.const'
```

## Diagnosis

✅ **String `DEFAULT_PAYMENT_METHOD_CODES` TIDAK ADA dalam source code module**
(verified dengan content search di seluruh folder module)

⚠️ Ini berarti error berasal dari salah satu sumber berikut:

### Kemungkinan 1: Python Bytecode Cache (Paling Mungkin)
Python compile file `.py` → `.pyc` dan simpan di folder `__pycache__/`.
Ada kemungkinan file `.pyc` lama masih ter-load yang menunjuk ke konstanta lama.

### Kemungkinan 2: Odoo Registry Cache
Odoo punya in-memory registry yang cache class definitions.
Walau pakai `--dev=reload`, kadang import error tetap di-cache.

### Kemungkinan 3: Stuck Browser State
Tab Configuration mungkin masih simpan unsaved changes dari sebelumnya.

---

## 🔧 Solusi Step-by-Step

### Step 1: Discard Browser Changes
Klik tombol **"Discard changes"** di error popup.
Ini paling penting — jangan klik "Stay here" karena akan stuck.

### Step 2: Bersihkan Python Cache
Jalankan di terminal Anda:

```bash
# Hapus semua __pycache__ folder di module
docker exec Odoo18 find /mnt/extra-addons/andykanoz_doku_payment_geteway -type d -name __pycache__ -exec rm -rf {} +

# Atau dari Windows host (PowerShell):
cd D:\MyServer\Odoo18\Addons\andykanoz_doku_payment_geteway
Get-ChildItem -Recurse -Force -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

### Step 3: Restart Odoo Container (BUKAN Reload)
```bash
docker compose restart odoo18
```

⚠️ `--dev=reload` hanya reload Python source pada perubahan, TIDAK clear bytecode cache.
Restart container = full Python interpreter restart = clean import.

### Step 4: Reload Browser (Hard Refresh)
- **Windows**: `Ctrl + Shift + R` atau `Ctrl + F5`
- Ini clear browser cache untuk halaman tersebut

### Step 5: Coba Lagi Ubah State
1. Login ke Odoo
2. **Accounting → Configuration → Payment Providers → DOKU**
3. Ubah State ke "Test Mode"
4. Save

---

## 🆘 Jika Masih Error Setelah Step di Atas

Kalau masih muncul error yang sama, kemungkinan ada file external (di luar module folder) yang import dari const ini. Cek dengan:

```bash
docker exec Odoo18 grep -r "DEFAULT_PAYMENT_METHOD_CODES" /mnt/extra-addons/ 2>/dev/null
docker exec Odoo18 grep -r "DEFAULT_PAYMENT_METHOD_CODES" /var/lib/odoo/ 2>/dev/null
```

Kalau ada hasil — kasih tahu saya path file-nya.

---

## 🎯 Root Cause Analysis (Untuk Debugging)

Based on file listing earlier, ada folder-folder ini yang berisi `.pyc`:
- `controllers\__pycache__`
- `models\__pycache__`
- `utils\__pycache__`
- `__pycache__`

`.pyc` file di-generate setiap kali Python import sebuah `.py` file.
Kalau dulu ada konstanta `DEFAULT_PAYMENT_METHOD_CODES` di code (mungkin saat AI Gemini eksplorasi tapi lupa hapus atau saat awal Strategy 3 planning), maka `.pyc` lama akan tetap reference itu.

Solusi hapus semua `__pycache__` adalah cara standard untuk clean state.
