import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "mercury-blue": "#5266eb",
        "ghost-blue": "#cdddff",
        "deep-space": "#171721",
        "midnight-slate": "#1e1e2a",
        graphite: "#272735",
        lead: "#70707d",
        starlight: "#ededf3",
        silver: "#c3c3cc",
        "pure-white": "#ffffff",
      },
      fontFamily: {
        display: ["Inter", "Manrope", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["Inter", "Manrope", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      fontSize: {
        caption: ["12px", { lineHeight: "1.5", letterSpacing: "0.24px" }],
        "body-sm": ["14px", { lineHeight: "1.5", letterSpacing: "0.28px" }],
        body: ["16px", { lineHeight: "1.5", letterSpacing: "0.16px" }],
        subheading: ["18px", { lineHeight: "1.4" }],
        "heading-sm": ["21px", { lineHeight: "1.35" }],
        heading: ["32px", { lineHeight: "1.2" }],
        "heading-lg": ["49px", { lineHeight: "1.15" }],
        display: ["65px", { lineHeight: "1.1", letterSpacing: "0.65px" }],
      },
      maxWidth: {
        page: "1200px",
      },
      spacing: {
        "80": "80px",
        "112": "112px",
        "128": "128px",
      },
    },
  },
  plugins: [],
};

export default config;
