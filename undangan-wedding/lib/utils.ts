import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Combine Tailwind class names safely, deduplicating conflicting classes.
 * Standard utility from shadcn/ui ecosystem.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Get the personalized guest name from URL query string `?to=...`
 * Returns "Tamu Undangan" as fallback.
 */
export function getGuestNameFromUrl(searchParams?: URLSearchParams): string {
  if (typeof window === "undefined" && !searchParams) return "Tamu Undangan";
  const params =
    searchParams ?? new URLSearchParams(window.location.search);
  const to = params.get("to") ?? params.get("kepada");
  if (!to) return "Tamu Undangan";
  // Replace + with space (URL encoding) and decode
  return decodeURIComponent(to.replace(/\+/g, " ")).trim();
}

/**
 * Format an ISO date string to Indonesian human-friendly format.
 * Example: "Senin, 14 Juni 2026"
 */
export function formatDateIndo(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat("id-ID", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

/**
 * Copy a string to clipboard. Returns true on success.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    // Fallback for older browsers
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}
