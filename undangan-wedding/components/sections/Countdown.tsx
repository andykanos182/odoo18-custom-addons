"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { weddingConfig } from "@/lib/wedding-config";
import { Section, SectionLabel, SectionTitle } from "@/components/ui/Section";
import { BotanicalDivider } from "@/components/ui/Ornaments";

type TimeLeft = {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
};

function calculateTimeLeft(target: Date): TimeLeft {
  const diff = target.getTime() - Date.now();
  if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0 };

  return {
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((diff / (1000 * 60)) % 60),
    seconds: Math.floor((diff / 1000) % 60),
  };
}

export function Countdown() {
  const [timeLeft, setTimeLeft] = useState<TimeLeft | null>(null);
  const target = new Date(weddingConfig.weddingDate);
  const isPast = target.getTime() <= Date.now();

  useEffect(() => {
    setTimeLeft(calculateTimeLeft(target));
    const id = setInterval(() => setTimeLeft(calculateTimeLeft(target)), 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const units = [
    { label: "Hari", value: timeLeft?.days ?? 0 },
    { label: "Jam", value: timeLeft?.hours ?? 0 },
    { label: "Menit", value: timeLeft?.minutes ?? 0 },
    { label: "Detik", value: timeLeft?.seconds ?? 0 },
  ];

  return (
    <Section id="countdown">
      <SectionLabel>Save the Date</SectionLabel>
      <SectionTitle>Counting Down</SectionTitle>

      <BotanicalDivider className="mx-auto mt-4" />

      {isPast ? (
        <p className="mt-12 text-center font-display text-2xl italic text-terracotta">
          Hari pernikahan kami telah tiba ✨
        </p>
      ) : (
        <div className="mt-12 grid grid-cols-4 gap-2">
          {units.map((unit, i) => (
            <motion.div
              key={unit.label}
              className="glass-panel flex flex-col items-center justify-center px-1 py-4 shadow-soft"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <p
                className="font-display text-3xl font-medium leading-none text-forest tabular-nums md:text-4xl"
                suppressHydrationWarning
              >
                {String(unit.value).padStart(2, "0")}
              </p>
              <p className="mt-2 text-[10px] uppercase tracking-widest text-forest/60">
                {unit.label}
              </p>
            </motion.div>
          ))}
        </div>
      )}

      <p className="mt-8 text-center text-xs text-forest/60">
        {new Intl.DateTimeFormat("id-ID", {
          weekday: "long",
          day: "numeric",
          month: "long",
          year: "numeric",
        }).format(target)}
      </p>
    </Section>
  );
}
