"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { weddingConfig } from "@/lib/wedding-config";
import { getGuestNameFromUrl } from "@/lib/utils";
import { Frangipani, PalmLeaf, BotanicalDivider } from "@/components/ui/Ornaments";

type CoverScreenProps = {
  onOpen: () => void;
};

export function CoverScreen({ onOpen }: CoverScreenProps) {
  const [guestName, setGuestName] = useState("Tamu Undangan");
  const [isOpening, setIsOpening] = useState(false);

  useEffect(() => {
    setGuestName(getGuestNameFromUrl());
  }, []);

  const handleOpen = () => {
    setIsOpening(true);
    // delay slightly so animation can play before unmount
    setTimeout(() => onOpen(), 900);
  };

  return (
    <AnimatePresence>
      {!isOpening && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden bg-cream"
          initial={{ opacity: 1 }}
          exit={{
            opacity: 0,
            scale: 1.1,
            transition: { duration: 0.8, ease: "easeInOut" },
          }}
        >
          {/* ── Background ornaments ───────────────────── */}
          <div className="absolute inset-0 bg-paper">
            {/* Top left palm */}
            <motion.div
              className="absolute -left-12 -top-16 h-56 w-56 opacity-50"
              initial={{ rotate: -20, opacity: 0 }}
              animate={{ rotate: -10, opacity: 0.5 }}
              transition={{ duration: 1.4, delay: 0.2 }}
            >
              <PalmLeaf className="h-full w-full text-sage-400 animate-leaf-sway" />
            </motion.div>

            {/* Top right palm */}
            <motion.div
              className="absolute -right-12 -top-16 h-56 w-56 opacity-50"
              initial={{ rotate: 20, opacity: 0 }}
              animate={{ rotate: 10, opacity: 0.5 }}
              transition={{ duration: 1.4, delay: 0.3 }}
              style={{ transform: "scaleX(-1)" }}
            >
              <PalmLeaf className="h-full w-full text-sage-400" />
            </motion.div>

            {/* Bottom decorations */}
            <motion.div
              className="absolute -bottom-10 -left-10 h-44 w-44"
              initial={{ rotate: 200, opacity: 0 }}
              animate={{ rotate: 210, opacity: 0.4 }}
              transition={{ duration: 1.4, delay: 0.5 }}
            >
              <PalmLeaf className="h-full w-full text-sage-300" />
            </motion.div>

            {/* Floating frangipanis */}
            {[
              { top: "15%", left: "12%", size: 8, delay: 0.6 },
              { top: "70%", right: "10%", size: 10, delay: 0.8 },
              { top: "30%", right: "8%", size: 6, delay: 1.0 },
            ].map((f, i) => (
              <motion.div
                key={i}
                className="absolute"
                style={{
                  top: f.top,
                  left: f.left,
                  right: f.right,
                  width: `${f.size * 4}px`,
                  height: `${f.size * 4}px`,
                }}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 0.7, scale: 1 }}
                transition={{ duration: 0.8, delay: f.delay }}
              >
                <Frangipani />
              </motion.div>
            ))}
          </div>

          {/* ── Foreground content ─────────────────────── */}
          <div className="container-invitation relative z-10 text-center">
            <motion.p
              className="font-script text-3xl text-terracotta"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
            >
              The Wedding of
            </motion.p>

            <motion.h1
              className="mt-4 font-display text-5xl italic leading-none text-forest md:text-6xl"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, delay: 0.6 }}
            >
              {weddingConfig.groom.nickname}
              <span className="mx-3 font-script text-3xl text-terracotta md:text-4xl">
                &amp;
              </span>
              {weddingConfig.bride.nickname}
            </motion.h1>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1, delay: 1 }}
            >
              <BotanicalDivider className="mx-auto mt-8" />
            </motion.div>

            <motion.p
              className="mt-2 font-display text-base tracking-widest text-forest/70"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1, delay: 1.1 }}
            >
              14 · 06 · 2026
            </motion.p>

            {/* Personalized greeting */}
            <motion.div
              className="mt-16"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 1.4 }}
            >
              <p className="text-xs uppercase tracking-widest text-forest/60">
                Kepada Yth. Bapak/Ibu/Saudara/i
              </p>
              <p className="mt-3 font-display text-2xl italic text-forest">
                {guestName}
              </p>
              <p className="mt-1 text-xs text-forest/50">
                di tempat
              </p>
            </motion.div>

            {/* Open button */}
            <motion.button
              onClick={handleOpen}
              className="mt-12 inline-flex items-center gap-2 rounded-full bg-forest px-8 py-3 text-xs font-medium uppercase tracking-widest text-cream shadow-soft transition-all hover:bg-forest-700 hover:shadow-lg active:scale-95"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 1.7 }}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              <svg
                className="h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 8v13H3V8" />
                <path d="M1 3h22v5H1z" />
                <path d="M10 12h4" />
              </svg>
              Buka Undangan
            </motion.button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
