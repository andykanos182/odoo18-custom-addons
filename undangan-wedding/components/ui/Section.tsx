"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Section — wrapper that handles consistent spacing,
 * scroll-reveal animation, and the mobile-first reading column.
 */

type SectionProps = {
  id?: string;
  children: ReactNode;
  className?: string;
  /** Override default padding */
  noPadding?: boolean;
  /** Disable scroll-reveal animation */
  noReveal?: boolean;
};

export function Section({
  id,
  children,
  className = "",
  noPadding = false,
  noReveal = false,
}: SectionProps) {
  const content = (
    <div
      className={`container-invitation ${
        noPadding ? "" : "py-20"
      } ${className}`}
    >
      {children}
    </div>
  );

  if (noReveal) {
    return (
      <section id={id} className="relative">
        {content}
      </section>
    );
  }

  return (
    <motion.section
      id={id}
      className="relative"
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
    >
      {content}
    </motion.section>
  );
}

/**
 * SectionLabel — small uppercase text that sits above section titles.
 * E.g. "The Wedding of", "Save the Date".
 */
export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-center text-[11px] font-medium uppercase tracking-ultra text-terracotta">
      {children}
    </p>
  );
}

/**
 * SectionTitle — main display title in italic serif.
 */
export function SectionTitle({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <h2
      className={`mt-3 text-center font-display text-4xl italic text-forest md:text-5xl ${className}`}
    >
      {children}
    </h2>
  );
}
