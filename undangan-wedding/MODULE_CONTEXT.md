# Undangan Wedding — Module Context

> Cross-session development memory for Andyka & Khusnul wedding invitation site.
> Hosted at: **https://undangan.gopokaja.com**

## Project Overview

A custom-built wedding invitation website with:
- **Frontend**: Next.js 15 + React 19 + TypeScript + Tailwind CSS v3
- **Backend**: Supabase (Postgres + Realtime) — RSVP, ucapan tamu live
- **Animations**: Framer Motion
- **Output**: Static export (`output: 'export'`) → served via cloudflared
- **Deploy target**: `\\192.168.1.47\GeForce D\MyServer\Undangan\` (network share on home server)

## Build Status

| Phase | Status | Sections / Features |
|-------|--------|---------------------|
| 1 — Foundation | ✅ Done | Project setup, design tokens, ornaments, CoverScreen, HeroNames |
| 2 — Core Content | ✅ Done | Countdown, CoupleInfo, EventDetails, LocationMap, LoveStory, Gallery |
| 3 — Interactive | ✅ Done | RsvpForm, WishesWall (live), MusicPlayer, DigitalGift, Closing |
| 4 — Polish & Deploy | ⏳ In Progress | OG image, performance, deploy to production |

## Section Files

```
components/sections/
├── CoverScreen.tsx     Cover layar pembuka dengan tombol "Buka Undangan"
├── HeroNames.tsx       Quote QS Ar-Rum:21 + nama mempelai besar + tanggal
├── Countdown.tsx       4-unit countdown (hari/jam/menit/detik), live update
├── CoupleInfo.tsx      Foto + nama lengkap + nama orang tua kedua mempelai
├── EventDetails.tsx    Card Akad + Resepsi, tombol Maps, add to calendar
├── LocationMap.tsx     Iframe Google Maps + petunjuk arah
├── LoveStory.tsx       Timeline cerita pacaran (sage→terracotta gradient)
├── Gallery.tsx         Embla carousel + lightbox keyboard-nav
├── RsvpForm.tsx        Form RSVP → insert ke Supabase rsvps table
├── WishesWall.tsx      Live wishes wall via Supabase realtime channel
├── DigitalGift.tsx     Amplop digital, copy-to-clipboard nomor rekening
├── Closing.tsx         Penutup: terima kasih + nama mempelai
└── MusicPlayer.tsx     Floating button bottom-right, autoplay attempt
```

## Key Design Decisions

### Why static export?
- Server `192.168.1.47` doesn't run Node.js
- `cloudflared` can serve static files directly via Caddy/serve
- Faster TTFB — no SSR overhead
- All "dynamic" features (RSVP write, wishes wall) work via Supabase JS SDK from the browser

### Why Supabase over Google Sheets?
- Realtime subscription out of the box (ucapan baru muncul live tanpa refresh)
- Proper Postgres types & queries
- Free tier easily covers a wedding (~50K MAU, 500MB DB)
- Row Level Security keeps `INSERT` open without auth but locks down `UPDATE/DELETE`

### Why `@/` path alias?
- Cleaner imports: `@/components/...` instead of `../../components/...`
- Configured in `tsconfig.json` paths and Next.js handles it natively
- Works in both dev and static export builds

### Why custom palette tokens (forest, sage, terracotta)?
- More semantic than hex codes scattered everywhere
- Lets us swap palette globally if needed
- Tailwind extends, not replaces — all default Tailwind utilities still work

### Personalized links
- Pattern: `https://undangan.gopokaja.com/?to=Bapak+Budi+Santoso`
- Read in `CoverScreen` and `RsvpForm` via `URLSearchParams`
- No need for per-guest pages — keeps static export simple
- `+` is decoded to space, URL encoding handled

## Folder Structure

```
undangan-wedding/
├── app/
│   ├── globals.css         Tailwind base + custom utilities (.bg-paper, .glass-panel)
│   ├── layout.tsx          Fonts, metadata, OG tags, Toaster
│   └── page.tsx            Main entry: cover + sections
├── components/
│   ├── sections/           One file per scroll section (13 files)
│   └── ui/
│       ├── Section.tsx     Wrapper with consistent spacing + scroll reveal
│       └── Ornaments.tsx   SVG components: Frangipani, PalmLeaf, Monstera, Divider
├── lib/
│   ├── supabase/client.ts  Singleton Supabase client (anon key, browser-safe)
│   ├── utils.ts            cn(), getGuestNameFromUrl(), copyToClipboard(), formatDateIndo()
│   └── wedding-config.ts   ALL wedding data (names, dates, gifts, gallery paths)
├── docs/
│   ├── SUPABASE_SETUP.md   Step-by-step DB setup
│   └── DEPLOYMENT.md       cloudflared + serve setup
├── public/
│   ├── audio/              bg-music.mp3 (TBD)
│   ├── images/gallery/     prewedding photos (placeholder)
│   ├── images/banks/       BCA, Mandiri logos (placeholder)
│   └── ornaments/          (reserved for raster ornaments if needed)
├── .env.local              Supabase URL + anon key (gitignored)
├── dev.bat / build.bat     Helpers because npm not in PowerShell PATH
├── next.config.ts          Static export config
├── tailwind.config.ts      Color palette + fonts + animations
└── tsconfig.json           Path aliases
```

## Color Palette (Bali Tropical Elegance)

| Token       | Hex       | Use                              |
|-------------|-----------|----------------------------------|
| Forest      | `#2C3E2D` | Primary text, dark backgrounds   |
| Sage        | `#A8B89C` | Leaves, muted accents            |
| Terracotta  | `#C97B5B` | Accents, ampersand, highlights   |
| Sand        | `#F2D5A5` | Frangipani, warm highlights      |
| Cream       | `#F5EFE3` | Page background                  |
| Cream Light | `#FAF6EE` | Card backgrounds                 |

## Typography

- **Display** (couple names, titles): Cormorant Garamond — italic, serif
- **Body** (paragraphs, info): Plus Jakarta Sans
- **Script** (accents like "&"): Great Vibes — handwritten

All loaded via `next/font/google` with `display: swap` for FOUT-free first paint.

## Environment Variables

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...               # public anon key (safe in client)
NEXT_PUBLIC_WEDDING_DATE=2026-06-14T08:00:00+08:00
NEXT_PUBLIC_SITE_URL=https://undangan.gopokaja.com
```

Copy `.env.local.example` → `.env.local`, fill in values.

## Build & Deploy Commands

### Windows-specific helpers (because npm not in PowerShell PATH):

```powershell
# Dev server
.\dev.bat
# → http://localhost:3000

# Production build → static files in ./out
.\build.bat
```

### Standard npm commands (if PATH is fixed):

```powershell
npm install
npm run dev
npm run build
npm run preview
```

## Common Gotchas

- **Static export limits**: No `getServerSideProps`, no API routes — all dynamic data must come from client-side calls (Supabase). This is intentional.
- **Image optimization disabled**: `next/image` with `unoptimized: true` because the image optimizer needs a Node server. Use `<img>` or pre-optimized images.
- **`use client` everywhere**: All section components are `"use client"` because they use hooks (useState, useEffect) and Framer Motion. Layout.tsx remains a server component for SEO/OG.
- **Hot reload**: `wedding-config.ts` is a module — saving it triggers fast refresh, no restart needed.
- **Mobile-first**: Container max width is 480px on purpose (invitations are read on phones). Don't try to use the full viewport width.
- **Body scroll lock**: While CoverScreen is shown, body has `.no-scroll` class. Cleared in cleanup effect.
- **Music autoplay**: Browsers block autoplay without user gesture. The "Buka Undangan" click is the gesture — we attempt play() in MusicPlayer's effect. If still blocked (some iOS), user can tap manually.
- **Supabase missing creds**: Client gracefully falls back to a placeholder URL so static export build doesn't fail. Real values picked up at runtime from `.env.local`.
- **npm config omit=dev**: Andyka's machine has this. Use `npm install --include=dev` to override.
- **Network drives in cmd.exe**: Direct cd to UNC paths fails — use PowerShell or pushd. See `docs/DEPLOYMENT.md` for robocopy script.

## Todo for Phase 4 (Polish & Deploy)

- [ ] Generate proper OG image (1200x630) with couple names + date
- [ ] Add real prewedding photos (replace `/images/gallery/01-06.jpg` placeholders)
- [ ] Add real bg-music.mp3 (royalty-free instrumental, ~3-5 MB)
- [ ] Test on real Galaxy Tab S8 + iPhone
- [ ] Lighthouse audit (target: 90+ all categories)
- [ ] Deploy to `\\192.168.1.47\GeForce D\MyServer\Undangan\out\`
- [ ] Setup cloudflared tunnel + Caddy/serve
- [ ] DNS CNAME `undangan.gopokaja.com`
- [ ] Final QC with personalized link via WhatsApp
