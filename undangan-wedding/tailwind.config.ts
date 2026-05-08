import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Bali Tropical Elegance palette
        forest: {
          DEFAULT: "#2C3E2D",
          50: "#EDF1ED",
          100: "#D6DFD6",
          200: "#AEC0AE",
          300: "#86A086",
          400: "#5E815E",
          500: "#3F5C40",
          600: "#2C3E2D", // base
          700: "#243325",
          800: "#1B271C",
          900: "#121A13",
        },
        sage: {
          DEFAULT: "#A8B89C",
          50: "#F1F4EE",
          100: "#E0E7DA",
          200: "#C7D3BD",
          300: "#A8B89C",
          400: "#8B9F7E",
          500: "#708463",
          600: "#576949",
          700: "#3F4D34",
        },
        terracotta: {
          DEFAULT: "#C97B5B",
          50: "#FAEFE9",
          100: "#F2D6C8",
          200: "#E5B197",
          300: "#D89472",
          400: "#C97B5B",
          500: "#B26143",
          600: "#8E4D34",
          700: "#6A3826",
        },
        sand: {
          DEFAULT: "#F2D5A5",
          50: "#FDF7EC",
          100: "#FAEBD0",
          200: "#F2D5A5",
          300: "#E9BD7B",
          400: "#D9A057",
        },
        cream: {
          DEFAULT: "#F5EFE3",
          light: "#FAF6EE",
          dark: "#E8DEC9",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
        script: ["var(--font-script)", "cursive"],
      },
      letterSpacing: {
        wider: "0.1em",
        widest: "0.2em",
        ultra: "0.3em",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "leaf-sway": {
          "0%, 100%": { transform: "rotate(-3deg)" },
          "50%": { transform: "rotate(3deg)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.8s ease-out forwards",
        "fade-in": "fade-in 1.2s ease-out forwards",
        "leaf-sway": "leaf-sway 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
