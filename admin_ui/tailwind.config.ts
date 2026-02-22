import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        slate: "#e5e7eb",
        ocean: "#0f766e",
        ember: "#b45309",
      },
      fontFamily: {
        sans: ["\"Public Sans\"", "\"Segoe UI\"", "sans-serif"],
        display: ["\"Sora\"", "\"Segoe UI\"", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
