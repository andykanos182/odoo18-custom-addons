# Deployment Guide — undangan.gopokaja.com

> Step-by-step deploy ke `192.168.1.47` dengan Caddy + cloudflared.
> Estimasi total: ~30 menit (sekali setup, lalu tinggal `deploy.bat` untuk update).

## Arsitektur

```
Internet User
   ↓ HTTPS (undangan.gopokaja.com)
Cloudflare Edge
   ↓ Cloudflare Tunnel
cloudflared di 192.168.1.47
   ↓ http://localhost:8080
Caddy (file server)
   ↓ baca dari folder
D:\MyServer\Undangan\out\
```

---

## Langkah 1 — Build Production Bundle (di Laptop Dev)

Di folder project (`D:\MyServer\Odoo18\Addons\undangan-wedding\`):

1. Pastikan `.env.local` sudah ada dengan kredensial Supabase
2. Double-click `build.bat`
3. Tunggu sampai output `=== Build complete ===`
4. Folder `./out` akan terbentuk berisi semua file static

**Verifikasi**: lihat isi `./out/`. Harus ada minimal:
- `index.html`
- `_next/static/...` (folder dengan JS, CSS, fonts)
- `images/`, `audio/`, dll dari `/public`

---

## Langkah 2 — Copy Files ke Network Share

**Opsi A — Pakai script otomatis (recommended)**:

Double-click `deploy.bat` di folder project. Script ini:
1. Build production
2. Mirror `./out` → `\\192.168.1.47\GeForce D\MyServer\Undangan\out\` pakai robocopy

**Opsi B — Manual**:

```powershell
robocopy ".\out" "\\192.168.1.47\GeForce D\MyServer\Undangan\out" /MIR /NFL /NDL /NJH /NJS
```

Atau drag-drop folder `./out` ke network share via File Explorer.

---

## Langkah 3 — Setup Caddy di 192.168.1.47

Caddy adalah single-file web server yang akan serve file static.

### 3.1. Download Caddy

Di mesin **192.168.1.47**:

1. Buka https://caddyserver.com/download
2. Pilih:
   - **Platform**: Windows
   - **Architecture**: amd64 (kemungkinan besar)
3. Klik **Download** → dapatkan `caddy_windows_amd64.exe`
4. Rename jadi `caddy.exe`
5. Pindahkan ke folder permanen, contoh: `C:\Caddy\caddy.exe`

### 3.2. Buat Caddyfile

Buat file `C:\Caddy\Caddyfile` (TANPA ekstensi) dengan isi:

```caddyfile
# undangan.gopokaja.com - static file server
# Listening di port 8080, akan di-fronted oleh cloudflared

:8080 {
    root * "D:\MyServer\Undangan\out"
    file_server
    try_files {path} {path}/ {path}.html /index.html
    
    # Caching untuk static assets
    @static {
        path *.js *.css *.woff2 *.woff *.png *.jpg *.jpeg *.webp *.svg *.ico *.mp3
    }
    header @static Cache-Control "public, max-age=31536000, immutable"
    
    # No cache untuk HTML (supaya update langsung kelihatan)
    @html {
        path *.html /
    }
    header @html Cache-Control "no-cache, must-revalidate"
    
    # Compression
    encode gzip zstd
    
    # Security headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        Referrer-Policy "strict-origin-when-cross-origin"
        # Remove server header
        -Server
    }
}
```

**Penjelasan**:
- `:8080` — listen di port 8080 di semua interface
- `root *` — folder yang berisi file static
- `try_files` — handle trailing slashes (penting untuk Next.js export)
- Caching long-term untuk assets, no-cache untuk HTML

### 3.3. Test Caddy

Buka PowerShell sebagai Administrator di `C:\Caddy\`:

```powershell
.\caddy.exe run
```

Kalau berhasil, Anda akan lihat output seperti:
```
{"level":"info","msg":"serving initial configuration"}
```

Test di browser: `http://localhost:8080` atau `http://192.168.1.47:8080` dari laptop dev.

Harus muncul cover screen undangan. Kalau ya — Caddy sukses. Stop dulu dengan Ctrl+C, lanjut ke step berikutnya.

### 3.4. Install Caddy sebagai Windows Service (auto-start)

Supaya Caddy jalan otomatis saat 192.168.1.47 booting:

```powershell
# Download nssm.exe dari https://nssm.cc/download
# Atau pakai winget:
winget install nssm

# Install service
nssm install Caddy "C:\Caddy\caddy.exe" "run --config C:\Caddy\Caddyfile"
nssm set Caddy AppDirectory "C:\Caddy"
nssm set Caddy DisplayName "Caddy Web Server"
nssm set Caddy Description "Static file server untuk undangan.gopokaja.com"
nssm set Caddy Start SERVICE_AUTO_START

# Start service
nssm start Caddy

# Verify
sc query Caddy
```

Atau pakai Task Scheduler kalau tidak mau install nssm — lihat lampiran di bawah.

---

## Langkah 4 — Setup Cloudflare Tunnel

Anda sudah punya cloudflared running untuk Odoo (`nitro.gopokaja.com`). Tinggal tambah ingress rule.

### 4.1. Edit `config.yml`

Cari file config tunnel Anda, biasanya di:
- `C:\Users\<username>\.cloudflared\config.yml`, atau
- `C:\ProgramData\.cloudflared\config.yml`

Tambah rule untuk undangan **SEBELUM** rule fallback `http_status:404`:

```yaml
tunnel: <tunnel-id-anda>
credentials-file: C:\Users\<username>\.cloudflared\<tunnel-id>.json

ingress:
  # ✅ TAMBAHAN BARU — wedding invitation
  - hostname: undangan.gopokaja.com
    service: http://localhost:8080
  
  # Existing rule untuk Odoo
  - hostname: nitro.gopokaja.com
    service: http://localhost:8018
  
  # Existing rule untuk www (production)
  - hostname: www.gopokaja.com
    service: http://localhost:XXXX
  
  # Wajib jadi rule TERAKHIR
  - service: http_status:404
```

### 4.2. Restart cloudflared service

```powershell
# Kalau sudah jadi service
Restart-Service cloudflared

# Atau kalau jalan manual, kill & restart
Stop-Process -Name cloudflared -Force
cloudflared tunnel run <tunnel-name>
```

### 4.3. Verifikasi tunnel routing

```powershell
cloudflared tunnel route ip show
```

---

## Langkah 5 — DNS Record di Cloudflare Dashboard

1. Login ke https://dash.cloudflare.com
2. Pilih domain `gopokaja.com`
3. Klik **DNS** → **Records**
4. Klik **Add record**:
   - **Type**: `CNAME`
   - **Name**: `undangan`
   - **Target**: `<tunnel-id>.cfargotunnel.com` (sama dengan target untuk `nitro`)
   - **Proxy status**: 🟠 Proxied (HARUS orange cloud — kalau abu-abu, tunnel tidak jalan)
   - **TTL**: Auto
5. **Save**

Tunggu ~1-2 menit DNS propagation.

---

## Langkah 6 — Test Production

1. Buka `https://undangan.gopokaja.com` dari HP / browser di luar network rumah (test pakai data seluler!)
2. Test personalized link: `https://undangan.gopokaja.com/?to=Bapak+Budi+Santoso`
3. Test RSVP form (akan submit ke Supabase)
4. Test wishes wall (kirim ucapan, lihat live update)

---

## Workflow Update (Setelah Initial Setup)

Setelah deploy pertama selesai, untuk setiap perubahan:

```
Di laptop dev:
1. Edit code / config
2. Test di localhost:3000 (npm run dev)
3. Sudah mantap? → double-click deploy.bat
4. Tunggu robocopy selesai
5. Refresh browser → perubahan langsung kelihatan
```

Tidak perlu restart Caddy atau cloudflared — file static langsung di-serve fresh.

---

## Troubleshooting

### "ERR_CONNECTION_REFUSED" dari undangan.gopokaja.com
- Cek Caddy running: `sc query Caddy` atau buka `http://localhost:8080` dari mesin server
- Cek cloudflared running: `sc query cloudflared` atau di Cloudflare dashboard → Zero Trust → Tunnels

### "404 Not Found" 
- Cek folder `D:\MyServer\Undangan\out\index.html` benar-benar ada
- Cek path di Caddyfile pakai backslash `\` ATAU forward slash `/` (keduanya valid di Windows)

### Foto/audio 404 setelah deploy
- Pastikan folder `public/` ter-copy ke `./out/`. Next.js otomatis copy ini saat build, tapi cek manual: `out/images/` dan `out/audio/` harus ada

### Update tidak muncul setelah deploy
- Hard refresh browser: `Ctrl+Shift+R`
- Atau buka di Incognito untuk bypass cache

### Slow first load
- Cloudflare proxy butuh ~30 detik untuk cold start setelah deploy. Subsequent loads instant.

---

## Lampiran: Auto-start tanpa nssm (Task Scheduler)

Kalau tidak mau install nssm, pakai Task Scheduler:

1. Buka **Task Scheduler** → **Create Task**
2. **General** tab:
   - Name: `Caddy Web Server`
   - Run whether user is logged on or not
   - Run with highest privileges
3. **Triggers** tab → New:
   - Begin: At startup
4. **Actions** tab → New:
   - Program: `C:\Caddy\caddy.exe`
   - Arguments: `run --config C:\Caddy\Caddyfile`
   - Start in: `C:\Caddy`
5. **Conditions** tab:
   - Uncheck "Start the task only if the computer is on AC power"
6. **OK** → masukkan password Anda untuk run-as-user

Test reboot: setelah restart 192.168.1.47, akses `http://192.168.1.47:8080` dari laptop dev. Kalau muncul cover screen, auto-start sukses.
