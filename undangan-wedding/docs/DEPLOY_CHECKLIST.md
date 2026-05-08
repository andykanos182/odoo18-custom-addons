# Deploy Checklist — Undangan Andyka & Khusnul

> Checklist final sebelum go-live di `https://undangan.gopokaja.com`
> Centang ✅ saat selesai. Refer ke `docs/DEPLOYMENT.md` untuk detail.

---

## Pre-Deploy (di Laptop Dev)

### Konten Final
- [ ] Edit `lib/wedding-config.ts`:
  - [ ] Nama orang tua kedua mempelai (replace `[Nama Ayah ...]`)
  - [ ] Tanggal & waktu real (kalau bukan 14 Juni 2026)
  - [ ] Venue Akad: nama tempat, alamat lengkap, link Google Maps
  - [ ] Venue Resepsi: nama tempat, alamat lengkap, link Google Maps
  - [ ] Update `mapsEmbedUrl` (dari Google Maps → Share → Embed → copy `src`)
  - [ ] Love story: ganti placeholder description
  - [ ] Bank accounts: ganti nomor rekening dummy dengan real
  - [ ] E-wallet number (jika dipakai)

### Asset Files
- [ ] Foto mempelai groom: `public/images/groom.jpg` (rasio 1:1, ~800x800px)
- [ ] Foto mempelai bride: `public/images/bride.jpg` (rasio 1:1, ~800x800px)
- [ ] Foto galeri prewedding: `public/images/gallery/01.jpg` s/d `06.jpg` (rasio 3:4, ~600x800px)
- [ ] Background music: `public/audio/bg-music.mp3` (instrumental, ~3-5 MB, royalty-free)
- [ ] Logo bank (opsional): `public/images/banks/bca.png`, `mandiri.png`, dll

### Social Share Preview (CRITICAL)
- [ ] Convert `public/images/og-image.svg` → PNG 1200x630
  - Cara cepat: buka SVG di browser → screenshot, atau pakai online converter (cloudconvert.com)
  - Simpan sebagai `public/images/og-image.png`
- [ ] Update `lib/wedding-config.ts` → ganti `ogImage: "/images/og-image.svg"` jadi `"/images/og-image.png"`

### Supabase
- [ ] Database schema sudah jalan (lihat `docs/SUPABASE_SETUP.md`)
- [ ] `.env.local` sudah berisi URL & anon key real
- [ ] Test di `localhost:3000` — RSVP form & wishes wall benar-benar masuk ke database
- [ ] Cek di Supabase dashboard → Table Editor → row test sudah masuk

---

## Build

- [ ] Double-click `build.bat`
- [ ] Tunggu sampai `=== Build complete ===`
- [ ] Cek folder `./out/` ada dan berisi:
  - [ ] `index.html`
  - [ ] `_next/static/` (folder JS, CSS, fonts)
  - [ ] `images/` (semua foto)
  - [ ] `audio/` (background music)
- [ ] Test preview lokal dari static build:
  ```powershell
  npx serve@latest out -p 8080
  ```
  Buka `http://localhost:8080` → harus identik dengan dev server

---

## Setup Server (192.168.1.47) — One-Time

### Caddy
- [ ] Download `caddy.exe` dari https://caddyserver.com/download
- [ ] Pindahkan ke `C:\Caddy\caddy.exe`
- [ ] Copy `docs/Caddyfile` dari project → `C:\Caddy\Caddyfile`
- [ ] Test manual run: `C:\Caddy\caddy.exe run`
- [ ] Buat folder `D:\MyServer\Undangan\out\` (akan diisi nanti dari laptop dev via robocopy)
- [ ] Install nssm: `winget install nssm`
- [ ] Run `docs/install-caddy-service.bat` as Administrator
- [ ] Verify: `sc query Caddy` → status RUNNING
- [ ] Test dari laptop dev: `http://192.168.1.47:8080` → muncul cover screen

### Cloudflare Tunnel
- [ ] Edit `~\.cloudflared\config.yml`, tambah ingress rule untuk `undangan.gopokaja.com` → `http://localhost:8080`
- [ ] Restart cloudflared: `Restart-Service cloudflared`
- [ ] Verify: dari Cloudflare Zero Trust dashboard → Tunnels → status "Healthy"

### DNS
- [ ] Cloudflare dashboard → `gopokaja.com` → DNS → Add CNAME
  - [ ] Name: `undangan`
  - [ ] Target: `<tunnel-id>.cfargotunnel.com`
  - [ ] Proxy: ON (orange cloud)
- [ ] Tunggu 1-2 menit DNS propagation

---

## Deploy (di Laptop Dev)

- [ ] Double-click `deploy.bat`
  - Otomatis build + robocopy ke network share
- [ ] Tunggu sampai `=== Deploy complete ===`

---

## Verifikasi Production

- [ ] Buka `https://undangan.gopokaja.com` dari **HP dengan data seluler** (BUKAN WiFi rumah, supaya benar-benar test via internet)
- [ ] Cover screen muncul, klik "Buka Undangan"
- [ ] Scroll mulus, semua section render
- [ ] Test personalized link: `https://undangan.gopokaja.com/?to=Bapak+Budi+Santoso`
- [ ] Submit RSVP → cek di Supabase dashboard, row baru muncul
- [ ] Submit ucapan di Wishes Wall → muncul live tanpa refresh
- [ ] Copy nomor rekening dari Amplop Digital → toast "Nomor disalin"
- [ ] Music player jalan (atau bisa di-toggle manual)

---

## Social Share Test

- [ ] Buka https://www.opengraph.xyz/
- [ ] Paste `https://undangan.gopokaja.com`
- [ ] Lihat preview — title, description, og-image harus muncul
- [ ] Test kirim link via WhatsApp ke diri sendiri:
  - [ ] Preview muncul (mungkin perlu wait 30 detik untuk WhatsApp fetch)
  - [ ] Title: "Andyka & Khusnul · 14 Juni 2026"
  - [ ] Image: og-image.png

---

## Performance Audit

- [ ] Run Lighthouse di Chrome DevTools (mode Mobile, Slow 4G)
- [ ] Target scores:
  - [ ] Performance: 90+
  - [ ] Accessibility: 95+
  - [ ] Best Practices: 95+
  - [ ] SEO: 95+
- [ ] First Contentful Paint < 2s
- [ ] Largest Contentful Paint < 3s
- [ ] Total page weight < 3 MB

Kalau ada yang fail, biasanya karena foto belum di-optimize. Pakai https://squoosh.app/ atau https://tinypng.com/ untuk compress.

---

## Distribusi ke Tamu

Format link untuk WhatsApp blast:

```
🌿 Undangan Pernikahan
Andyka Eka Putra & Khusnul Maulida
14 Juni 2026

Bapak/Ibu yang terhormat,
Berikut link undangan kami:
https://undangan.gopokaja.com/?to=Nama+Tamu

Mohon kehadiran & doa restunya. 🙏
```

**Tips**:
- Generate per-tamu URL via spreadsheet (Excel formula): `="https://undangan.gopokaja.com/?to=" & SUBSTITUTE(A2," ","+")`
- Mass send pakai WhatsApp Business API atau aplikasi seperti WaSender / Wablas
- Hindari karakter spesial di nama tamu (gunakan + untuk spasi, hindari simbol seperti & % # ?)

---

## Post-Wedding

- [ ] Backup data RSVP & Wishes dari Supabase (export CSV)
- [ ] Optional: take screenshot semua wishes untuk dijadikan kenang-kenangan
- [ ] Optional: keep website live forever atau take down (tinggal stop Caddy service)

Selamat menikah, Andyka & Khusnul! 💚
