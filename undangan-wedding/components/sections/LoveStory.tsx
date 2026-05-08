"use client";

import { motion } from "framer-motion";
import { weddingConfig } from "@/lib/wedding-config";
import { Section, SectionLabel, SectionTitle } from "@/components/ui/Section";
import { BotanicalDivider, Frangipani } from "@/components/ui/Ornaments";

export function LoveStory() {
  return (
    <Section id="story">
      <SectionLabel>Our Journey</SectionLabel>
      <SectionTitle>Cerita Kami</SectionTitle>
      <BotanicalDivider className="mx-auto mt-4" />

      <p className="mx-auto mt-6 max-w-md text-center text-xs leading-relaxed text-forest/70">
        Setiap kisah memiliki awal — ini adalah awal cerita kami.
      </p>

      <div className="relative mt-12">
        {/* Vertical timeline line */}
        <div className="absolute left-[18px] top-2 bottom-2 w-px bg-gradient-to-b from-sage-300 via-sage-400 to-terracotta/50" />

        <div className="space-y-10">
          {weddingConfig.loveStory.map((item, i) => (
            <motion.div
              key={item.year}
              className="relative flex gap-5"
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.6, delay: i * 0.1 }}
            >
              {/* Timeline dot */}
              <div className="relative z-10 flex h-9 w-9 flex-shrink-0 items-center justify-center">
                <div className="absolute inset-0 rounded-full bg-cream-light" />
                <div className="absolute inset-1 rounded-full border-2 border-terracotta bg-cream" />
                <div className="relative h-1.5 w-1.5 rounded-full bg-terracotta" />
              </div>

              <div className="flex-1 pb-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-terracotta">
                  {item.year}
                </p>
                <h4 className="mt-1 font-display text-xl italic text-forest">
                  {item.title}
                </h4>
                <p className="mt-2 text-xs leading-relaxed text-forest/70">
                  {item.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="relative ml-1 mt-6 flex items-center gap-3">
          <div className="h-9 w-9 flex-shrink-0">
            <Frangipani />
          </div>
          <p className="font-script text-xl text-terracotta">
            ... &amp; the rest is forever
          </p>
        </div>
      </div>
    </Section>
  );
}
