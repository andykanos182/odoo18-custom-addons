"use client";

import { useState, useEffect, useRef, type FormEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";
import { Heart, Send, MessageCircle } from "lucide-react";
import { Section, SectionLabel, SectionTitle } from "@/components/ui/Section";
import { BotanicalDivider } from "@/components/ui/Ornaments";
import { getSupabase, type WishRow } from "@/lib/supabase/client";
import { getGuestNameFromUrl } from "@/lib/utils";

const PAGE_SIZE = 8;

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "baru saja";
  if (m < 60) return `${m} menit lalu`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} jam lalu`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} hari lalu`;
  return new Date(iso).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
  });
}

export function WishesWall() {
  const [wishes, setWishes] = useState<WishRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [attending, setAttending] = useState<"yes" | "no" | "maybe">("yes");
  const [submitting, setSubmitting] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const channelRef = useRef<ReturnType<
    ReturnType<typeof getSupabase>["channel"]
  > | null>(null);

  useEffect(() => {
    const supabase = getSupabase();

    const fetchWishes = async () => {
      const { data, error } = await supabase
        .from("wishes")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(50);

      if (error) {
        console.warn("[wishes] fetch error", error.message);
      } else if (data) {
        setWishes(data as WishRow[]);
      }
      setLoading(false);
    };

    fetchWishes();

    const guestName = getGuestNameFromUrl();
    if (guestName !== "Tamu Undangan") setName(guestName);

    const channel = supabase
      .channel("wishes-changes")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "wishes" },
        (payload) => {
          setWishes((prev) => [payload.new as WishRow, ...prev]);
        }
      )
      .subscribe();
    channelRef.current = channel;

    return () => {
      if (channelRef.current) supabase.removeChannel(channelRef.current);
    };
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !message.trim()) {
      toast.error("Nama dan ucapan tidak boleh kosong");
      return;
    }

    setSubmitting(true);
    const supabase = getSupabase();

    const { error } = await supabase.from("wishes").insert({
      guest_name: name.trim().slice(0, 50),
      message: message.trim().slice(0, 500),
      attending,
    });

    setSubmitting(false);

    if (error) {
      console.error("[wishes]", error);
      toast.error("Gagal mengirim. Coba lagi nanti.");
      return;
    }

    toast.success("Terima kasih atas ucapannya! 💚");
    setMessage("");
  };

  const visible = wishes.slice(0, visibleCount);

  const attendingBadge = (a: WishRow["attending"]) => {
    if (a === "yes")
      return { label: "✓ Hadir", color: "bg-sage-200 text-forest" };
    if (a === "no")
      return { label: "Tidak Hadir", color: "bg-terracotta/15 text-terracotta-600" };
    if (a === "maybe")
      return { label: "Mungkin", color: "bg-sand-100 text-forest/70" };
    return null;
  };

  return (
    <Section id="wishes">
      <SectionLabel>Doa &amp; Ucapan</SectionLabel>
      <SectionTitle>Wishes Wall</SectionTitle>
      <BotanicalDivider className="mx-auto mt-4" />

      <p className="mx-auto mt-6 max-w-md text-center text-xs leading-relaxed text-forest/70">
        Sampaikan doa &amp; ucapan terbaik Anda untuk kami. Akan ditampilkan secara live di sini.
      </p>

      <motion.form
        onSubmit={handleSubmit}
        className="glass-panel mt-10 space-y-4 p-5 shadow-soft"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
      >
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={50}
          placeholder="Nama Anda"
          required
          className="w-full rounded-xl border border-forest/15 bg-cream-light/50 px-4 py-2.5 text-sm text-forest placeholder:text-forest/30 focus:border-terracotta focus:outline-none focus:ring-1 focus:ring-terracotta"
        />

        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          maxLength={500}
          rows={3}
          placeholder="Tuliskan ucapan & doa Anda..."
          required
          className="w-full resize-none rounded-xl border border-forest/15 bg-cream-light/50 px-4 py-3 text-sm text-forest placeholder:text-forest/30 focus:border-terracotta focus:outline-none focus:ring-1 focus:ring-terracotta"
        />

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-forest/70">
            Kehadiran:
          </span>
          {(["yes", "maybe", "no"] as const).map((opt) => (
            <button
              type="button"
              key={opt}
              onClick={() => setAttending(opt)}
              className={`rounded-full px-3 py-1 text-[11px] font-medium transition-all active:scale-95 ${
                attending === opt
                  ? "bg-forest text-cream"
                  : "bg-cream-light text-forest/60 hover:bg-cream"
              }`}
            >
              {opt === "yes" ? "Hadir" : opt === "maybe" ? "Mungkin" : "Tidak Hadir"}
            </button>
          ))}
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-terracotta px-5 py-2.5 text-xs font-semibold uppercase tracking-widest text-cream transition-all hover:bg-terracotta-500 active:scale-95 disabled:opacity-50"
        >
          {submitting ? (
            <>
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-cream/30 border-t-cream" />
              Mengirim...
            </>
          ) : (
            <>
              <Send className="h-3.5 w-3.5" />
              Kirim Ucapan
            </>
          )}
        </button>
      </motion.form>

      <div className="mt-8">
        <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-forest/60">
          <MessageCircle className="h-3.5 w-3.5" />
          {wishes.length} ucapan
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="glass-panel h-20 animate-pulse opacity-50" />
            ))}
          </div>
        ) : wishes.length === 0 ? (
          <div className="glass-panel p-8 text-center">
            <Heart className="mx-auto h-6 w-6 text-terracotta/40" />
            <p className="mt-3 text-xs text-forest/60">
              Belum ada ucapan. Jadilah yang pertama mengirimkan doa!
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence initial={false}>
              {visible.map((wish) => {
                const badge = attendingBadge(wish.attending);
                return (
                  <motion.div
                    key={wish.id}
                    layout
                    initial={{ opacity: 0, y: -10, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    transition={{ duration: 0.4 }}
                    className="glass-panel p-4 shadow-soft"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-sage-300 to-forest-400 font-display text-base italic text-cream">
                        {wish.guest_name.charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="truncate text-sm font-semibold text-forest">
                            {wish.guest_name}
                          </p>
                          {badge && (
                            <span
                              className={`rounded-full px-2 py-0.5 text-[9px] font-medium ${badge.color}`}
                            >
                              {badge.label}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-[11px] text-forest/50">
                          {timeAgo(wish.created_at)}
                        </p>
                        <p className="mt-2 break-words text-sm leading-relaxed text-forest/85">
                          {wish.message}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>

            {visibleCount < wishes.length && (
              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
                  className="rounded-full border border-forest/20 bg-cream-light px-5 py-2 text-xs font-medium tracking-wider text-forest transition-all hover:border-forest/40 active:scale-95"
                >
                  Lihat lebih banyak ({wishes.length - visibleCount} lagi)
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </Section>
  );
}
