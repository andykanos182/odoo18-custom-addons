"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Music, Pause } from "lucide-react";
import { weddingConfig } from "@/lib/wedding-config";

type MusicPlayerProps = {
  /** Auto-play attempt fires when this becomes true. Browsers may still block. */
  shouldPlay: boolean;
};

/**
 * MusicPlayer
 * ─────────────────────────────────────
 * Floating circular button bottom-right that plays/pauses
 * background music. Visible only after the cover is opened.
 *
 * Browser autoplay policy: only user gestures can start audio.
 * The "Buka Undangan" button click counts as a gesture, so we
 * try to play() right after the cover unmounts. If blocked,
 * the user can still toggle manually.
 */
export function MusicPlayer({ shouldPlay }: MusicPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);

  useEffect(() => {
    if (!shouldPlay || !weddingConfig.music.enabled) return;
    const audio = audioRef.current;
    if (!audio) return;

    audio.volume = 0.5;
    const tryPlay = async () => {
      try {
        await audio.play();
        setIsPlaying(true);
      } catch {
        // Autoplay blocked — user must tap manually
        setIsPlaying(false);
      }
    };
    tryPlay();
  }, [shouldPlay]);

  const togglePlay = async () => {
    setHasInteracted(true);
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      try {
        await audio.play();
        setIsPlaying(true);
      } catch (err) {
        console.warn("Audio play failed:", err);
      }
    }
  };

  if (!weddingConfig.music.enabled) return null;

  return (
    <>
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <audio ref={audioRef} src={weddingConfig.music.src} loop preload="auto" />

      <AnimatePresence>
        {shouldPlay && (
          <motion.button
            type="button"
            onClick={togglePlay}
            className="fixed bottom-5 right-5 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-forest text-cream shadow-soft transition-all hover:bg-forest-700 active:scale-95"
            initial={{ opacity: 0, scale: 0, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0 }}
            transition={{ duration: 0.4, delay: 0.5 }}
            aria-label={isPlaying ? "Pause musik" : "Putar musik"}
          >
            {isPlaying ? (
              <>
                <Pause className="h-4 w-4" />
                <span className="absolute inset-0 -z-10 animate-ping rounded-full bg-forest opacity-30" />
              </>
            ) : (
              <>
                <Music className="h-4 w-4" />
                {!hasInteracted && (
                  <span className="absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full bg-terracotta" />
                )}
              </>
            )}
          </motion.button>
        )}
      </AnimatePresence>
    </>
  );
}
