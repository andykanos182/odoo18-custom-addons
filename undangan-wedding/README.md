# Undangan Pernikahan — Andyka & Khusnul

> Wedding invitation website with Bali Tropical Elegance theme.
> Built with Next.js 15 + Supabase, hosted at https://undangan.gopokaja.com

## Quick Start

```powershell
# 1. Install dependencies (~2 min)
npm install

# 2. Configure environment (see docs/SUPABASE_SETUP.md)
copy .env.local.example .env.local
# Edit .env.local with Supabase credentials

# 3. Run dev server
npm run dev
# → http://localhost:3000

# 4. Build for production
npm run build
# → static files in ./out
```

## Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 — Foundation | ✅ Done | Project setup, design tokens, cover screen, hero section |
| 2 — Core Content | ⏳ Next | Countdown, couple, events, maps, gallery |
| 3 — Interactive | 🔜 Soon | RSVP, wishes wall, music, gift |
| 4 — Polish & Deploy | 🔜 Soon | Animations, SEO, deploy to production |

## Documentation

- [`MODULE_CONTEXT.md`](./MODULE_CONTEXT.md) — Architecture & decisions
- [`docs/SUPABASE_SETUP.md`](./docs/SUPABASE_SETUP.md) — Database setup
- [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) — How to deploy to home server

## Tech Stack

- **Framework**: Next.js 15 (App Router, static export)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v3
- **Animations**: Framer Motion
- **Backend**: Supabase (Postgres + Realtime)
- **Hosting**: Self-hosted via Cloudflare Tunnel + static file server

## Customization

All wedding-specific content lives in [`lib/wedding-config.ts`](./lib/wedding-config.ts).
Edit names, dates, venues, gift accounts, etc. there — components read from this single source.

## Personalized Links

Send tamu links with their name pre-filled:

```
https://undangan.gopokaja.com/?to=Bapak+Budi+Santoso
https://undangan.gopokaja.com/?to=Keluarga+Sutrisno
```

The cover screen will display their name automatically.

---

Made with 💚 in Bali
