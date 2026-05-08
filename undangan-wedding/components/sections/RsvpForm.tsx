"use client";

import { useState, useEffect, type FormEvent } from "react";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import { Check, Send } from "lucide-react";
import { Section, SectionLabel, SectionTitle } from "@/components/ui/Section";
import { BotanicalDivider } from "@/components/ui/Ornaments";
import { getSupabase } from "@/lib/supabase/client";
import { getGuestNameFromUrl } from "@/lib/utils";

type Attending = "yes" | "no";

export function RsvpForm() {
  const [name, setName] = useState("");
  const [attending, setAttending] = useState<Attending | null>(null);
  const [paxCount, setPaxCount] = useState(1);
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const guestName = getGuestNameFromUrl();
    if (guestName !== "Tamu Undangan") setName(guestName);
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !attending) {
      toast.error("Mohon lengkapi nama dan kehadiran");
      return;
    }

    setSubmitting(true);
    const supabase = getSupabase();

    const { error } = await supabase.from("rsvps").insert({
      guest_name: name.trim().slice(0, 50),
      attending,
      pax_count: attending === "yes" ? paxCount : 0,
      message: message.trim().slice(0, 500) || null,
    });

    setSubmitting(false);

    if (error) {
      console.error("[rsvp]", error);
      toast.error("Gagal mengirim. Coba lagi nanti.");
      return;
    }

    toast.success("Terima kasih atas konfirmasinya!");
    setSubmitted(true);
  };

  return (
    <Section id="rsvp">
      <SectionLabel>Konfirmasi Kehadiran</SectionLabel>
      <SectionTitle>RSVP</SectionTitle>
      <BotanicalDivider className="mx-auto mt-4" />

      <p className="mx-auto mt-6 max-w-md text-center text-xs leading-relaxed text-forest/70">
        Mohon konfirmasi kehadiran Anda agar kami dapat mempersiapkan acara dengan
        lebih baik.
      </p>

      <motion.div
        className="glass-panel mt-10 p-6 shadow-soft"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
      >
        {submitted ? (
          <div className="flex flex-col items-center py-6 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-sage-200">
              <Check className="h-7 w-7 text-forest" />
            </div>
            <h3 className="mt-4 font-display text-2xl italic text-forest">
              Terima Kasih!
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-forest/70">
              Konfirmasi Anda telah kami terima. Sampai jumpa di hari bahagia kami.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="rsvp-name"
                className="block text-[11px] font-semibold uppercase tracking-widest text-forest/70"
              >
                Nama
              </label>
              <input
                id="rsvp-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={50}
                placeholder="Nama lengkap Anda"
                required
                className="mt-2 w-full rounded-xl border border-forest/15 bg-cream-light/50 px-4 py-3 text-sm text-forest placeholder:text-forest/30 focus:border-terracotta focus:outline-none focus:ring-1 focus:ring-terracotta"
              />
            </div>

            <div>
              <p className="block text-[11px] font-semibold uppercase tracking-widest text-forest/70">
                Kehadiran
              </p>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setAttending("yes")}
                  className={`rounded-xl border px-4 py-3 text-sm font-medium transition-all active:scale-95 ${
                    attending === "yes"
                      ? "border-forest bg-forest text-cream"
                      : "border-forest/15 bg-cream-light/50 text-forest/80 hover:border-forest/30"
                  }`}
                >
                  ✓ Hadir
                </button>
                <button
                  type="button"
                  onClick={() => setAttending("no")}
                  className={`rounded-xl border px-4 py-3 text-sm font-medium transition-all active:scale-95 ${
                    attending === "no"
                      ? "border-terracotta bg-terracotta text-cream"
                      : "border-forest/15 bg-cream-light/50 text-forest/80 hover:border-forest/30"
                  }`}
                >
                  Tidak Hadir
                </button>
              </div>
            </div>

            {attending === "yes" && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                transition={{ duration: 0.3 }}
              >
                <label
                  htmlFor="rsvp-pax"
                  className="block text-[11px] font-semibold uppercase tracking-widest text-forest/70"
                >
                  Jumlah Tamu
                </label>
                <div className="mt-2 flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setPaxCount(Math.max(1, paxCount - 1))}
                    className="flex h-10 w-10 items-center justify-center rounded-full border border-forest/20 bg-cream-light text-forest transition-all hover:border-forest/40 active:scale-95"
                  >
                    −
                  </button>
                  <input
                    id="rsvp-pax"
                    type="number"
                    min={1}
                    max={10}
                    value={paxCount}
                    onChange={(e) => {
                      const v = parseInt(e.target.value, 10);
                      setPaxCount(Number.isNaN(v) ? 1 : Math.max(1, Math.min(10, v)));
                    }}
                    className="w-16 rounded-xl border border-forest/15 bg-cream-light/50 py-2 text-center font-display text-xl text-forest focus:border-terracotta focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setPaxCount(Math.min(10, paxCount + 1))}
                    className="flex h-10 w-10 items-center justify-center rounded-full border border-forest/20 bg-cream-light text-forest transition-all hover:border-forest/40 active:scale-95"
                  >
                    +
                  </button>
                  <span className="ml-1 text-xs text-forest/60">orang</span>
                </div>
              </motion.div>
            )}

            <div>
              <label
                htmlFor="rsvp-message"
                className="block text-[11px] font-semibold uppercase tracking-widest text-forest/70"
              >
                Pesan / Doa
                <span className="ml-1 font-normal normal-case tracking-normal text-forest/40">
                  (opsional)
                </span>
              </label>
              <textarea
                id="rsvp-message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                maxLength={500}
                rows={3}
                placeholder="Sampaikan pesan & doa Anda..."
                className="mt-2 w-full resize-none rounded-xl border border-forest/15 bg-cream-light/50 px-4 py-3 text-sm text-forest placeholder:text-forest/30 focus:border-terracotta focus:outline-none focus:ring-1 focus:ring-terracotta"
              />
              <p className="mt-1 text-right text-[10px] text-forest/40">
                {message.length} / 500
              </p>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-forest px-6 py-3.5 text-xs font-semibold uppercase tracking-widest text-cream shadow-soft transition-all hover:bg-forest-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-cream/30 border-t-cream" />
                  Mengirim...
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  Kirim Konfirmasi
                </>
              )}
            </button>
          </form>
        )}
      </motion.div>
    </Section>
  );
}
