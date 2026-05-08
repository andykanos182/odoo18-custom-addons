"use client";

import { motion } from "framer-motion";
import { weddingConfig } from "@/lib/wedding-config";
import { Section, SectionLabel, SectionTitle } from "@/components/ui/Section";
import { BotanicalDivider, Frangipani } from "@/components/ui/Ornaments";

type Person = {
  fullName: string;
  nickname: string;
  fatherName: string;
  motherName: string;
  childOrder: string;
  instagram?: string;
  photo?: string;
};

function PersonCard({ person, accent }: { person: Person; accent: "left" | "right" }) {
  return (
    <motion.div
      className="relative flex flex-col items-center text-center"
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8 }}
    >
      {/* Photo frame with botanical accent */}
      <div className="relative">
        <div
          className={`absolute -z-10 h-12 w-12 ${
            accent === "left" ? "-left-3 -top-3" : "-right-3 -top-3"
          }`}
        >
          <Frangipani />
        </div>

        <div className="relative h-44 w-44 overflow-hidden rounded-full border-4 border-cream-light shadow-soft">
          {/* Placeholder gradient if no photo yet */}
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-sage-200 via-sage-300 to-forest-400">
            <span className="font-display text-5xl italic text-cream-light">
              {person.nickname.charAt(0)}
            </span>
          </div>
          {/* Real img will replace placeholder when photo exists */}
          {person.photo && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={person.photo}
              alt={person.fullName}
              className="absolute inset-0 h-full w-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          )}
        </div>
      </div>

      {/* Names */}
      <h3 className="mt-6 font-display text-3xl italic text-forest">
        {person.fullName}
      </h3>

      {person.instagram && (
        <a
          href={`https://instagram.com/${person.instagram}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-flex items-center gap-1.5 text-xs text-terracotta transition-colors hover:text-terracotta-600"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2.16c3.2 0 3.58.01 4.85.07 1.17.05 1.81.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.25 1.81-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-1.17-.05-1.81-.25-2.23-.41-.56-.22-.96-.48-1.38-.9-.42-.42-.68-.82-.9-1.38-.16-.42-.36-1.06-.41-2.23C2.17 15.58 2.16 15.2 2.16 12s.01-3.58.07-4.85c.05-1.17.25-1.81.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.42 2.17 8.8 2.16 12 2.16zM12 0C8.74 0 8.33.01 7.05.07 5.78.13 4.9.33 4.14.63c-.79.31-1.46.72-2.13 1.39C1.34 2.69.93 3.36.63 4.14.33 4.9.13 5.78.07 7.05.01 8.33 0 8.74 0 12s.01 3.67.07 4.95c.06 1.27.26 2.15.56 2.91.31.79.72 1.46 1.39 2.13.67.67 1.34 1.08 2.13 1.39.76.3 1.64.5 2.91.56C8.33 23.99 8.74 24 12 24s3.67-.01 4.95-.07c1.27-.06 2.15-.26 2.91-.56.79-.31 1.46-.72 2.13-1.39.67-.67 1.08-1.34 1.39-2.13.3-.76.5-1.64.56-2.91.06-1.28.07-1.69.07-4.95s-.01-3.67-.07-4.95c-.06-1.27-.26-2.15-.56-2.91a5.89 5.89 0 0 0-1.39-2.13A5.89 5.89 0 0 0 19.86.63c-.76-.3-1.64-.5-2.91-.56C15.67.01 15.26 0 12 0zm0 5.84a6.16 6.16 0 1 0 0 12.32 6.16 6.16 0 0 0 0-12.32zm0 10.16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.4-11.85a1.44 1.44 0 1 0 0 2.88 1.44 1.44 0 0 0 0-2.88z" />
          </svg>
          @{person.instagram}
        </a>
      )}

      {/* Parents */}
      <div className="mt-5 space-y-1 text-xs text-forest/75">
        <p>{person.childOrder}</p>
        <p className="font-medium">{person.fatherName}</p>
        <p className="text-forest/50">&amp;</p>
        <p className="font-medium">{person.motherName}</p>
      </div>
    </motion.div>
  );
}

export function CoupleInfo() {
  return (
    <Section id="couple">
      <SectionLabel>The Bride &amp; Groom</SectionLabel>
      <SectionTitle>Mempelai</SectionTitle>
      <BotanicalDivider className="mx-auto mt-4" />

      <p className="mx-auto mt-6 max-w-md text-center text-xs leading-relaxed text-forest/70">
        Dengan rahmat Allah SWT, kami akan menyelenggarakan pernikahan putra-putri kami
      </p>

      <div className="mt-12 space-y-16">
        <PersonCard person={weddingConfig.groom} accent="left" />

        {/* Ampersand divider */}
        <div className="flex items-center justify-center gap-4">
          <div className="h-px w-20 bg-forest/20" />
          <p className="font-script text-5xl text-terracotta">&amp;</p>
          <div className="h-px w-20 bg-forest/20" />
        </div>

        <PersonCard person={weddingConfig.bride} accent="right" />
      </div>
    </Section>
  );
}
