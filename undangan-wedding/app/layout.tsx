import type { Metadata, Viewport } from "next";
import { Cormorant_Garamond, Plus_Jakarta_Sans, Great_Vibes } from "next/font/google";
import { Toaster } from "react-hot-toast";
import { weddingConfig } from "@/lib/wedding-config";
import "./globals.css";

// ── Fonts ─────────────────────────────────────────────────
// Display: elegant serif italic for couple names
const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-display",
  display: "swap",
});

// Body: clean sans-serif for readable Indonesian text
const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

// Script: handwritten accent for "couple invites you" type lines
const greatVibes = Great_Vibes({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-script",
  display: "swap",
});

// ── Metadata (SEO + WhatsApp share preview) ───────────────
export const metadata: Metadata = {
  title: weddingConfig.meta.title,
  description: weddingConfig.meta.description,
  metadataBase: new URL(weddingConfig.meta.siteUrl),
  openGraph: {
    title: weddingConfig.meta.title,
    description: weddingConfig.meta.description,
    url: weddingConfig.meta.siteUrl,
    siteName: weddingConfig.meta.title,
    images: [
      {
        url: weddingConfig.meta.ogImage,
        width: 1200,
        height: 630,
        alt: `Undangan Pernikahan ${weddingConfig.groom.nickname} & ${weddingConfig.bride.nickname}`,
      },
    ],
    locale: "id_ID",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: weddingConfig.meta.title,
    description: weddingConfig.meta.description,
    images: [weddingConfig.meta.ogImage],
  },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
  },
};

export const viewport: Viewport = {
  themeColor: "#2C3E2D",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="id"
      className={`${cormorant.variable} ${jakarta.variable} ${greatVibes.variable}`}
    >
      <body className="bg-paper">
        {children}
        <Toaster
          position="top-center"
          toastOptions={{
            duration: 3000,
            style: {
              background: "#2C3E2D",
              color: "#F5EFE3",
              fontSize: "14px",
              borderRadius: "999px",
              padding: "10px 18px",
            },
          }}
        />
      </body>
    </html>
  );
}
