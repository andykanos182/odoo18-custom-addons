import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Supabase browser client (singleton)
 * ─────────────────────────────────────
 * Uses the public anon key, which is safe to expose to the browser.
 * Row Level Security (RLS) policies in Supabase enforce who can
 * read/write — see docs/SUPABASE_SETUP.md for the schema & policies.
 */

let cachedClient: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (cachedClient) return cachedClient;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    // Don't crash during build if env not set yet — return a dummy
    // so static export still works. RSVP/Wishes will just no-op.
    if (typeof window !== "undefined") {
      console.warn(
        "[supabase] Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY"
      );
    }
    cachedClient = createClient(
      "https://placeholder.supabase.co",
      "placeholder-key",
      { auth: { persistSession: false } }
    );
    return cachedClient;
  }

  cachedClient = createClient(url, anonKey, {
    auth: { persistSession: false },
    realtime: { params: { eventsPerSecond: 5 } },
  });

  return cachedClient;
}

// ── Database row types (mirror SUPABASE_SETUP.md schema) ────────
export type WishRow = {
  id: number;
  guest_name: string;
  message: string;
  attending: "yes" | "no" | "maybe" | null;
  created_at: string;
};

export type RsvpRow = {
  id: number;
  guest_name: string;
  attending: "yes" | "no";
  pax_count: number;
  message: string | null;
  submitted_at: string;
};
