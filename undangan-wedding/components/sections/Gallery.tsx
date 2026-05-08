"use client";

import { useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import useEmblaCarousel from "embla-carousel-react";
import Autoplay from "embla-carousel-autoplay";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { weddingConfig } from "@/lib/wedding-config";
import { Section, SectionLabel, SectionTitle } from "@/components/ui/Section";
import { BotanicalDivider } from "@/components/ui/Ornaments";

/**
 * Gallery — prewedding photo carousel with click-to-zoom lightbox.
 */
export function Gallery() {
  const [emblaRef, emblaApi] = useEmblaCarousel(
    { loop: true, align: "center" },
    [Autoplay({ delay: 4500, stopOnInteraction: true })]
  );

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const onSelect = useCallback(() => {
    if (!emblaApi) return;
    setSelectedIndex(emblaApi.selectedScrollSnap());
  }, [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    onSelect();
    emblaApi.on("select", onSelect);
    return () => {
      emblaApi.off("select", onSelect);
    };
  }, [emblaApi, onSelect]);

  const scrollPrev = useCallback(() => emblaApi?.scrollPrev(), [emblaApi]);
  const scrollNext = useCallback(() => emblaApi?.scrollNext(), [emblaApi]);

  // Keyboard navigation in lightbox
  useEffect(() => {
    if (lightboxIndex === null) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightboxIndex(null);
      if (e.key === "ArrowLeft")
        setLightboxIndex((i) =>
          i === null
            ? null
            : (i - 1 + weddingConfig.gallery.length) % weddingConfig.gallery.length
        );
      if (e.key === "ArrowRight")
        setLightboxIndex((i) =>
          i === null ? null : (i + 1) % weddingConfig.gallery.length
        );
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [lightboxIndex]);

  return (
    <>
      <Section id="gallery">
        <SectionLabel>Memories</SectionLabel>
        <SectionTitle>Galeri</SectionTitle>
        <BotanicalDivider className="mx-auto mt-4" />

        <p className="mx-auto mt-6 max-w-md text-center text-xs leading-relaxed text-forest/70">
          Beberapa momen yang kami abadikan dalam perjalanan kami.
        </p>

        <motion.div
          className="mt-10"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          {/* Carousel */}
          <div className="overflow-hidden rounded-2xl shadow-soft" ref={emblaRef}>
            <div className="flex">
              {weddingConfig.gallery.map((src, i) => (
                <div key={i} className="relative min-w-0 flex-[0_0_100%]">
                  <button
                    type="button"
                    className="block aspect-[3/4] w-full overflow-hidden bg-gradient-to-br from-sage-200 via-sage-300 to-forest-400 transition-transform active:scale-95"
                    onClick={() => setLightboxIndex(i)}
                    aria-label={`Buka foto ${i + 1}`}
                  >
                    <div className="flex h-full w-full items-center justify-center">
                      <span className="font-display text-6xl italic text-cream-light/50">
                        {i + 1}
                      </span>
                    </div>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={src}
                      alt={`Galeri ${i + 1}`}
                      className="absolute inset-0 h-full w-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Navigation */}
          <div className="mt-4 flex items-center justify-between">
            <button
              type="button"
              onClick={scrollPrev}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-forest/20 bg-cream-light text-forest transition-all hover:border-forest/40 active:scale-95"
              aria-label="Foto sebelumnya"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            <div className="flex items-center gap-1.5">
              {weddingConfig.gallery.map((_, i) => (
                <button
                  type="button"
                  key={i}
                  onClick={() => emblaApi?.scrollTo(i)}
                  className={`h-1.5 rounded-full transition-all ${
                    i === selectedIndex
                      ? "w-6 bg-terracotta"
                      : "w-1.5 bg-forest/20 hover:bg-forest/40"
                  }`}
                  aria-label={`Ke foto ${i + 1}`}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={scrollNext}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-forest/20 bg-cream-light text-forest transition-all hover:border-forest/40 active:scale-95"
              aria-label="Foto selanjutnya"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </motion.div>
      </Section>

      {/* Lightbox */}
      {lightboxIndex !== null && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-forest-900/95 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => setLightboxIndex(null)}
        >
          <button
            type="button"
            className="absolute right-4 top-4 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-cream/10 text-cream backdrop-blur-sm transition-colors hover:bg-cream/20"
            onClick={(e) => {
              e.stopPropagation();
              setLightboxIndex(null);
            }}
            aria-label="Tutup"
          >
            <X className="h-5 w-5" />
          </button>

          <div
            className="relative max-h-[90vh] max-w-[90vw]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={weddingConfig.gallery[lightboxIndex]}
              alt={`Galeri ${lightboxIndex + 1}`}
              className="max-h-[90vh] max-w-[90vw] rounded-lg object-contain"
            />
          </div>
        </motion.div>
      )}
    </>
  );
}
