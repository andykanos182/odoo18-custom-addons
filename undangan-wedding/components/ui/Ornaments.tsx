/**
 * Botanical SVG ornaments — Bali Tropical
 * ─────────────────────────────────────────
 * Reusable decorative elements drawn inline as SVG so they:
 *  - scale crisply on retina displays
 *  - inherit color via currentColor / props
 *  - have zero network requests
 *
 * Usage: <FrangipaniCorner className="absolute top-0 left-0 w-32 text-sage-300" />
 */

import { cn } from "@/lib/utils";

type OrnamentProps = {
  className?: string;
  "aria-hidden"?: boolean;
};

/* ── Frangipani / Plumeria flower (Bali signature) ─────── */
export function Frangipani({ className }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={cn("text-sand-200", className)}
      aria-hidden="true"
    >
      <g fill="currentColor">
        {/* 5 overlapping petals around center */}
        {[0, 72, 144, 216, 288].map((angle) => (
          <ellipse
            key={angle}
            cx="50"
            cy="32"
            rx="14"
            ry="22"
            transform={`rotate(${angle} 50 50)`}
            opacity="0.85"
          />
        ))}
      </g>
      {/* yellow center */}
      <circle cx="50" cy="50" r="6" fill="#F2D5A5" opacity="0.9" />
      <circle cx="50" cy="50" r="3" fill="#C97B5B" opacity="0.7" />
    </svg>
  );
}

/* ── Palm leaf ─────────────────────────────────────────── */
export function PalmLeaf({ className }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 200 200"
      className={cn("text-sage-400", className)}
      aria-hidden="true"
    >
      <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        {/* central stem */}
        <path d="M 100 180 Q 100 100 100 20" strokeWidth="2.5" />
        {/* leaflets, mirrored on both sides */}
        {Array.from({ length: 12 }).map((_, i) => {
          const y = 30 + i * 12;
          const len = 45 - Math.abs(i - 5) * 2.5;
          return (
            <g key={i}>
              <path
                d={`M 100 ${y} Q ${100 - len * 0.6} ${y - 4} ${100 - len} ${y - 8}`}
              />
              <path
                d={`M 100 ${y} Q ${100 + len * 0.6} ${y - 4} ${100 + len} ${y - 8}`}
              />
            </g>
          );
        })}
      </g>
    </svg>
  );
}

/* ── Monstera leaf (lush, holes, signature tropical) ───── */
export function MonsteraLeaf({ className }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 200 200"
      className={cn("text-sage-500", className)}
      aria-hidden="true"
    >
      <path
        fill="currentColor"
        opacity="0.85"
        d="M 100 190 C 100 190 30 170 30 110 C 30 60 60 25 100 15 C 140 25 170 60 170 110 C 170 170 100 190 100 190 Z"
      />
      {/* Characteristic Monstera holes & cuts */}
      <g fill="#F5EFE3">
        <ellipse cx="70" cy="80" rx="10" ry="6" transform="rotate(-30 70 80)" />
        <ellipse cx="130" cy="80" rx="10" ry="6" transform="rotate(30 130 80)" />
        <ellipse cx="60" cy="120" rx="8" ry="5" transform="rotate(-40 60 120)" />
        <ellipse cx="140" cy="120" rx="8" ry="5" transform="rotate(40 140 120)" />
        <path d="M 95 50 L 105 50 L 100 30 Z" />
        <path d="M 25 110 L 50 105 L 50 115 Z" />
        <path d="M 175 110 L 150 105 L 150 115 Z" />
      </g>
    </svg>
  );
}

/* ── Decorative divider (botanical line) ───────────────── */
export function BotanicalDivider({ className }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 200 24"
      className={cn("h-6 text-forest/40", className)}
      aria-hidden="true"
    >
      <g fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round">
        <line x1="10" y1="12" x2="80" y2="12" />
        <line x1="120" y1="12" x2="190" y2="12" />
        {/* center motif: small leaf */}
        <path
          d="M 95 12 Q 100 4 100 12 Q 100 20 105 12"
          fill="currentColor"
          opacity="0.6"
        />
        <circle cx="100" cy="12" r="1.5" fill="currentColor" />
      </g>
    </svg>
  );
}

/* ── Corner spray (group of leaves & flower) ───────────── */
export function CornerSpray({
  className,
  flip = false,
}: OrnamentProps & { flip?: boolean }) {
  return (
    <svg
      viewBox="0 0 200 200"
      className={cn(className)}
      style={flip ? { transform: "scaleX(-1)" } : undefined}
      aria-hidden="true"
    >
      {/* sage palm fronds */}
      <g fill="none" stroke="#A8B89C" strokeWidth="1.4" strokeLinecap="round" opacity="0.8">
        <path d="M 0 0 Q 60 30 110 80" strokeWidth="2" />
        {Array.from({ length: 8 }).map((_, i) => {
          const t = (i + 1) / 9;
          const px = t * 110;
          const py = t * 80;
          return (
            <g key={i}>
              <path d={`M ${px} ${py} Q ${px + 5} ${py - 18} ${px - 5} ${py - 28}`} />
              <path d={`M ${px} ${py} Q ${px + 18} ${py + 5} ${px + 28} ${py - 5}`} />
            </g>
          );
        })}
      </g>
      {/* terracotta accent flower */}
      <g transform="translate(70 50) scale(0.5)">
        <Frangipani />
      </g>
    </svg>
  );
}
