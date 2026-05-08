"use client";

import { motion } from "framer-motion";
import { Calendar, Clock, MapPin, ExternalLink } from "lucide-react";
import { weddingConfig } from "@/lib/wedding-config";
import { Section, SectionLabel, SectionTitle } from "@/components/ui/Section";
import { BotanicalDivider } from "@/components/ui/Ornaments";
import { formatDateIndo } from "@/lib/utils";

type EventCardProps = {
  label: string;
  date: string;
  time: string;
  venue: string;
  address: string;
  mapsUrl: string;
  index: number;
};

function EventCard({
  label,
  date,
  time,
  venue,
  address,
  mapsUrl,
  index,
}: EventCardProps) {
  return (
    <motion.div
      className="glass-panel relative overflow-hidden p-6 shadow-soft"
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay: index * 0.15 }}
    >
      {/* Decorative corner */}
      <div className="absolute -right-4 -top-4 h-16 w-16 rounded-full bg-sage-100 opacity-40" />
      <div className="absolute -left-2 -bottom-6 h-12 w-12 rounded-full bg-sand-100 opacity-50" />

      <div className="relative">
        {/* Label badge */}
        <div className="inline-flex items-center rounded-full bg-terracotta/10 px-3 py-1">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-terracotta">
            {label}
          </p>
        </div>

        {/* Date — large display */}
        <p className="mt-4 font-display text-3xl italic text-forest">
          {formatDateIndo(date)}
        </p>

        {/* Details */}
        <div className="mt-5 space-y-2.5">
          <div className="flex items-start gap-3 text-sm text-forest/80">
            <Clock className="mt-0.5 h-4 w-4 flex-shrink-0 text-sage-600" />
            <span>{time}</span>
          </div>
          <div className="flex items-start gap-3 text-sm text-forest/80">
            <MapPin className="mt-0.5 h-4 w-4 flex-shrink-0 text-sage-600" />
            <div>
              <p className="font-medium text-forest">{venue}</p>
              <p className="mt-0.5 text-xs text-forest/60">{address}</p>
            </div>
          </div>
        </div>

        {/* Maps button */}
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-5 inline-flex items-center gap-2 rounded-full bg-forest px-5 py-2 text-xs font-medium uppercase tracking-wider text-cream transition-all hover:bg-forest-700 active:scale-95"
        >
          <ExternalLink className="h-3 w-3" />
          Buka di Maps
        </a>
      </div>
    </motion.div>
  );
}

export function EventDetails() {
  return (
    <Section id="events">
      <SectionLabel>Save the Date</SectionLabel>
      <SectionTitle>Acara</SectionTitle>
      <BotanicalDivider className="mx-auto mt-4" />

      <p className="mx-auto mt-6 max-w-md text-center text-xs leading-relaxed text-forest/70">
        Merupakan suatu kebahagiaan bagi kami apabila Bapak/Ibu/Saudara/i berkenan hadir
      </p>

      <div className="mt-10 space-y-5">
        {weddingConfig.events.map((event, i) => (
          <EventCard
            key={event.id}
            label={event.label}
            date={event.date}
            time={event.time}
            venue={event.venue}
            address={event.address}
            mapsUrl={event.mapsUrl}
            index={i}
          />
        ))}
      </div>

      {/* Calendar add-to button */}
      <div className="mt-8 text-center">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-full border border-forest/20 bg-cream-light px-5 py-2 text-xs font-medium tracking-wider text-forest transition-all hover:border-forest/40 hover:bg-cream-light/70 active:scale-95"
          onClick={() => {
            // Generate Google Calendar link
            const start = "20260614T010000Z"; // 09:00 WITA = 01:00 UTC
            const end = "20260614T030000Z";
            const text = encodeURIComponent(
              `Pernikahan ${weddingConfig.groom.nickname} & ${weddingConfig.bride.nickname}`
            );
            const details = encodeURIComponent(weddingConfig.meta.description);
            const location = encodeURIComponent(weddingConfig.events[0].address);
            const url = `https://calendar.google.com/calendar/r/eventedit?text=${text}&dates=${start}/${end}&details=${details}&location=${location}`;
            window.open(url, "_blank");
          }}
        >
          <Calendar className="h-3.5 w-3.5" />
          Tambahkan ke Kalender
        </button>
      </div>
    </Section>
  );
}
