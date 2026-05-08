# Supabase Setup Guide

> Step-by-step untuk setup database backend untuk RSVP & ucapan tamu live.
> Estimasi: ~10 menit.

## Langkah 1 — Buat Akun & Project

1. Buka **https://supabase.com** → klik **Start your project**
2. Sign up dengan **GitHub** (paling cepat) atau email
3. Setelah masuk, klik **New Project**
4. Isi:
   - **Name**: `undangan-wedding`
   - **Database Password**: generate yang kuat — **SIMPAN BAIK-BAIK** (akan dipakai untuk akses DB langsung jika perlu)
   - **Region**: **Southeast Asia (Singapore)** — paling dekat dari Bali
   - **Pricing Plan**: **Free**
5. Klik **Create new project**, tunggu ~2 menit untuk provisioning

## Langkah 2 — Ambil Credentials

1. Setelah project ready, di sidebar klik **Project Settings** (icon gear di bawah)
2. Klik **API**
3. Copy 2 nilai berikut:
   - **Project URL** — `https://xxxxxxxx.supabase.co`
   - **Project API keys** → **anon / public** (yang format JWT, panjang)

⚠️ **JANGAN copy `service_role` key.** Itu private dan hanya untuk server.
   `anon` key aman untuk diekspos ke browser karena RLS policies kita yang akan jaga akses.

## Langkah 3 — Setup Environment Variables

Di folder project (`D:\MyServer\Odoo18\Addons\undangan-wedding\`):

1. Copy file `.env.local.example` menjadi `.env.local`
2. Isi dengan credentials dari Langkah 2:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxx.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
   ```

## Langkah 4 — Buat Database Schema

1. Di Supabase dashboard, klik **SQL Editor** (icon `</>` di sidebar)
2. Klik **New query**
3. Paste SQL berikut, lalu klik **Run** (atau Ctrl+Enter):

```sql
-- ──────────────────────────────────────────────────────────
-- WISHES (Ucapan & Doa Tamu) — public live wall
-- ──────────────────────────────────────────────────────────
create table if not exists public.wishes (
  id          bigserial primary key,
  guest_name  text not null check (char_length(guest_name) between 1 and 50),
  message     text not null check (char_length(message) between 1 and 500),
  attending   text check (attending in ('yes', 'no', 'maybe')),
  created_at  timestamptz not null default now()
);

-- index for fast "newest first" queries
create index if not exists wishes_created_at_idx
  on public.wishes (created_at desc);

-- ──────────────────────────────────────────────────────────
-- RSVPS (kehadiran tamu)
-- ──────────────────────────────────────────────────────────
create table if not exists public.rsvps (
  id            bigserial primary key,
  guest_name    text not null check (char_length(guest_name) between 1 and 50),
  attending     text not null check (attending in ('yes', 'no')),
  pax_count     integer not null default 1 check (pax_count between 1 and 10),
  message       text check (char_length(message) <= 500),
  submitted_at  timestamptz not null default now()
);

create index if not exists rsvps_submitted_at_idx
  on public.rsvps (submitted_at desc);

-- ──────────────────────────────────────────────────────────
-- ROW LEVEL SECURITY (RLS)
-- Public can INSERT (write ucapan/RSVP) and SELECT (read wishes wall)
-- But NOT update or delete — protects against trolling
-- ──────────────────────────────────────────────────────────
alter table public.wishes enable row level security;
alter table public.rsvps enable row level security;

-- WISHES: anyone can read & insert
drop policy if exists "wishes_select_public" on public.wishes;
create policy "wishes_select_public"
  on public.wishes for select
  using (true);

drop policy if exists "wishes_insert_public" on public.wishes;
create policy "wishes_insert_public"
  on public.wishes for insert
  with check (true);

-- RSVPS: anyone can insert (submit), but only authenticated users (= you, the admin)
-- can read the full list. Use service_role from your admin tool to view RSVPs.
drop policy if exists "rsvps_insert_public" on public.rsvps;
create policy "rsvps_insert_public"
  on public.rsvps for insert
  with check (true);

-- ──────────────────────────────────────────────────────────
-- REALTIME — broadcast new wishes to all connected clients
-- ──────────────────────────────────────────────────────────
alter publication supabase_realtime add table public.wishes;
```

4. Pastikan output: `Success. No rows returned.` (atau serupa)

## Langkah 5 — Verify Setup

1. Di sidebar, klik **Table Editor**
2. Anda akan lihat 2 tabel: `wishes` dan `rsvps`
3. Klik **wishes** → **Insert row** → isi `guest_name: "Test"`, `message: "Selamat ya!"` → **Save**
4. Refresh — row baru muncul. RLS sudah jalan.

## Langkah 6 — Lihat RSVP yang Masuk (Admin View)

Karena kita lock `SELECT` untuk RSVP, untuk lihat siapa saja yang RSVP:

1. **Cara mudah**: di Supabase dashboard → **Table Editor** → klik tabel `rsvps`. Anda otomatis pakai `service_role` di sini, jadi bisa lihat semua data.
2. **Cara lain**: di **SQL Editor**, jalankan:
   ```sql
   select guest_name, attending, pax_count, message, submitted_at
   from public.rsvps
   order by submitted_at desc;
   ```

Anda bisa juga export ke CSV dengan klik **Export** di Table Editor.

## Troubleshooting

**"row violates row-level security policy"**
- Belum jalankan SQL di Langkah 4. Re-run query lengkap.

**"failed to connect to server"**
- Cek `NEXT_PUBLIC_SUPABASE_URL` — harus pakai `https://` dan tanpa trailing slash.

**"Invalid API key"**
- Pastikan copy `anon` key, bukan `service_role`.
- Restart `npm run dev` setelah ubah `.env.local`.

**Realtime tidak jalan**
- Cek `alter publication supabase_realtime add table public.wishes;` jalan. Jika error "already exists", aman.

## Free Tier Limits (Untuk Wedding)

| Resource          | Limit Free Tier  | Untuk Wedding         |
|-------------------|------------------|------------------------|
| Database storage  | 500 MB           | <1 MB (cukup banget)   |
| Bandwidth         | 5 GB / bulan     | Cukup untuk 10K visit  |
| MAU (auth users)  | 50K              | Tidak pakai auth       |
| Realtime channels | 200 concurrent   | Cukup untuk live wall  |

Lebih dari cukup untuk wedding. 100% gratis.
