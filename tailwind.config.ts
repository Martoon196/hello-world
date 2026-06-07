import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // ProperInvest brand palette
        brand: {
          50: "#eef5ff",
          100: "#d9e8ff",
          200: "#bcd6ff",
          300: "#8ebbff",
          400: "#5994ff",
          500: "#326dff",
          600: "#1a4ff5",
          700: "#143ce1",
          800: "#1733b6",
          900: "#19318f",
        },
        ink: {
          900: "#0b1020",
          800: "#141a2e",
          700: "#1d2540",
          600: "#2a3354",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Helvetica", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
