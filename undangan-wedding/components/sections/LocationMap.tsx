"use client";

import { motion } from "framer-motion";
import { weddingConfig } from "@/lib/wedding-config";
import { Section, SectionLabel, SectionTitle } from "@/components/ui/Section";
import { BotanicalDivider } from "@/components/ui/Ornaments";

export function LocationMap() {
  // Show map of the resepsi (or first event if only one)
  const event =
    weddingConfig.events.find((e) => e.id === "resepsi") ?? weddingConfig.events[0];

  return (
    <Section id="location">
      <SectionLabel>Find Us</SectionLabel>
      <SectionTitle>Lokasi</SectionTitle>
      <BotanicalDivider className="mx-auto mt-4" />

      <motion.div
        className="mt-10 overflow-hidden rounded-2xl border border-forest/15 shadow-soft"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
      >
        <div className="aspect-square w-full bg-sage-100">
          <iframe
            src={event.mapsEmbedUrl}
            className="h-full w-full border-0"
            allowFullScreen
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            title={`Peta lokasi ${event.venue}`}
          />
        </div>

        <div className="bg-cream-light p-5">
          <p className="text-xs font-semibold uppercase tracking-widest text-terracotta">
            {event.label}
          </p>
          <p className="mt-2 font-display text-xl italic text-forest">{event.venue}</p>
          <p className="mt-1 text-xs leading-relaxed text-forest/70">{event.address}</p>

          <a
            href={event.mapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full bg-terracotta px-5 py-2.5 text-xs font-medium uppercase tracking-wider text-cream transition-all hover:bg-terracotta-500 active:scale-95"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 0 1 0-5 2.5 2.5 0 0 1 0 5z" />
            </svg>
            Petunjuk Arah
          </a>
        </div>
      </motion.div>
    </Section>
  );
}
