"use client";

import { motion } from "framer-motion";
import { weddingConfig } from "@/lib/wedding-config";
import { BotanicalDivider, Frangipani, PalmLeaf } from "@/components/ui/Ornaments";
import { Section, SectionLabel } from "@/components/ui/Section";

export function HeroNames() {
  return (
    <Section id="hero" noReveal noPadding>
      <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden py-20">
        {/* Decorative palm leaves */}
        <div className="pointer-events-none absolute -left-16 top-10 h-48 w-48 opacity-40">
          <PalmLeaf className="h-full w-full text-sage-400" />
        </div>
        <div
          className="pointer-events-none absolute -right-16 bottom-20 h-48 w-48 opacity-40"
          style={{ transform: "scaleX(-1) rotate(15deg)" }}
        >
          <PalmLeaf className="h-full w-full text-sage-400" />
        </div>
        <div className="pointer-events-none absolute right-8 top-32 h-12 w-12 opacity-70">
          <Frangipani />
        </div>
        <div className="pointer-events-none absolute left-12 bottom-32 h-10 w-10 opacity-60">
          <Frangipani />
        </div>

        {/* Quote */}
        <motion.div
          className="relative mx-auto max-w-md text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.3 }}
        >
          <p className="text-[13px] leading-relaxed text-forest/80">
            {weddingConfig.openingQuote.text}
          </p>
          <p className="mt-3 text-xs font-medium tracking-wider text-terracotta">
            ({weddingConfig.openingQuote.source})
          </p>
        </motion.div>

        <BotanicalDivider className="mx-auto mt-12" />

        {/* Section label */}
        <motion.div
          className="mt-12"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.6 }}
        >
          <SectionLabel>Assalamu&apos;alaikum Wr. Wb.</SectionLabel>
          <p className="mt-6 px-4 text-center text-sm leading-relaxed text-forest/80">
            Dengan memohon rahmat dan ridho Allah SWT,
            <br />
            kami bermaksud menyelenggarakan pernikahan putra-putri kami:
          </p>
        </motion.div>

        {/* Couple names — large display */}
        <motion.div
          className="mt-12 text-center"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.2, delay: 0.8 }}
        >
          <h1 className="font-display text-5xl italic leading-tight text-forest md:text-6xl">
            {weddingConfig.groom.nickname}
          </h1>
          <p className="my-4 font-script text-4xl text-terracotta">&amp;</p>
          <h1 className="font-display text-5xl italic leading-tight text-forest md:text-6xl">
            {weddingConfig.bride.nickname}
          </h1>
        </motion.div>

        {/* Date */}
        <motion.div
          className="mt-12 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.1 }}
        >
          <BotanicalDivider className="mx-auto" />
          <div className="mt-4 flex items-center justify-center gap-6">
            <div className="text-center">
              <p className="text-xs uppercase tracking-widest text-forest/60">Hari</p>
              <p className="mt-1 font-display text-xl italic text-forest">Minggu</p>
            </div>
            <div className="h-12 w-px bg-forest/20" />
            <div className="text-center">
              <p className="font-display text-5xl italic leading-none text-terracotta">
                14
              </p>
              <p className="mt-1 text-xs uppercase tracking-widest text-forest/60">
                Juni 2026
              </p>
            </div>
            <div className="h-12 w-px bg-forest/20" />
            <div className="text-center">
              <p className="text-xs uppercase tracking-widest text-forest/60">Pukul</p>
              <p className="mt-1 font-display text-xl italic text-forest">08.00</p>
            </div>
          </div>
        </motion.div>

        {/* Scroll hint */}
        <motion.div
          className="mt-16 flex flex-col items-center gap-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.5 }}
        >
          <p className="text-[10px] uppercase tracking-widest text-forest/50">
            Scroll ke bawah
          </p>
          <motion.svg
            className="h-5 w-5 text-forest/60"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            animate={{ y: [0, 6, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          >
            <path d="M12 5v14M5 12l7 7 7-7" />
          </motion.svg>
        </motion.div>
      </div>
    </Section>
  );
}
