"use client";

import { motion } from "framer-motion";
import { weddingConfig } from "@/lib/wedding-config";
import { Section } from "@/components/ui/Section";
import { BotanicalDivider, Frangipani, PalmLeaf } from "@/components/ui/Ornaments";

export function Closing() {
  return (
    <Section id="closing" noReveal noPadding>
      <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden py-20 text-center">
        {/* Background ornaments */}
        <div className="pointer-events-none absolute -left-16 top-10 h-48 w-48 opacity-30">
          <PalmLeaf className="h-full w-full text-sage-400" />
        </div>
        <div
          className="pointer-events-none absolute -right-16 bottom-10 h-48 w-48 opacity-30"
          style={{ transform: "scaleX(-1) rotate(15deg)" }}
        >
          <PalmLeaf className="h-full w-full text-sage-400" />
        </div>
        <div className="pointer-events-none absolute right-12 top-32 h-10 w-10 opacity-60">
          <Frangipani />
        </div>
        <div className="pointer-events-none absolute left-12 bottom-32 h-12 w-12 opacity-60">
          <Frangipani />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <p className="font-script text-3xl text-terracotta">Terima kasih</p>
          <p className="mt-4 px-4 text-xs leading-relaxed text-forest/75">
            Atas kehadiran serta doa restu yang Bapak/Ibu/Saudara/i berikan,
            kami sekeluarga mengucapkan terima kasih.
          </p>
          <p className="mt-8 text-[11px] uppercase tracking-widest text-forest/60">
            Wassalamu&apos;alaikum Warahmatullahi Wabarakatuh
          </p>
        </motion.div>

        <BotanicalDivider className="mx-auto my-10" />

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1, delay: 0.3 }}
        >
          <p className="text-[11px] uppercase tracking-widest text-forest/60">
            Kami yang berbahagia
          </p>
          <h2 className="mt-6 font-display text-4xl italic leading-tight text-forest">
            {weddingConfig.groom.nickname}
          </h2>
          <p className="my-3 font-script text-3xl text-terracotta">&amp;</p>
          <h2 className="font-display text-4xl italic leading-tight text-forest">
            {weddingConfig.bride.nickname}
          </h2>
          <p className="mt-8 text-xs leading-relaxed text-forest/60">
            beserta keluarga
          </p>
        </motion.div>

        <motion.div
          className="mt-16"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1, delay: 0.6 }}
        >
          <p className="text-[10px] tracking-widest text-forest/40">
            Made with 💚 in Bali
          </p>
        </motion.div>
      </div>
    </Section>
  );
}
