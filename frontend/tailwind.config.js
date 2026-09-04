/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
    "./hooks/**/*.{js,jsx,ts,tsx}",
    "./lib/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        brand: {
          yellow: "#FFCC00",
          yellowDark: "#E5B800",
          deepBlue: "#0B3D91",
          deepBlueDark: "#082E6E",
        },
        primary: {
          50: "#ECFEFF", 100: "#CFFAFE", 200: "#A5F3FC",
          300: "#67E8F9", 400: "#22D3EE", 500: "#06B6D4",
          600: "#0891B2", 700: "#0E7490", 800: "#155E75", 900: "#164E63",
        },
        secondary: {
          50: "#FFFBEB", 100: "#FEF3C7", 200: "#FDE68A",
          300: "#FCD34D", 400: "#FBBF24", 500: "#F59E0B",
          600: "#D97706", 700: "#B45309",
        },
        success: { 50: "#ECFDF5", 100: "#D1FAE5", 500: "#10B981", 700: "#047857" },
        warning: { 50: "#FFFBEB", 100: "#FEF3C7", 500: "#F59E0B", 700: "#B45309" },
        danger: { 50: "#FEF2F2", 100: "#FEE2E2", 500: "#EF4444", 700: "#B91C1C" },
        info: { 50: "#EFF6FF", 500: "#3B82F6", 700: "#1D4ED8" },
        neutral: {
          0: "#FFFFFF", 50: "#F8FAFC", 100: "#F1F5F9", 200: "#E2E8F0",
          300: "#CBD5E1", 400: "#94A3B8", 500: "#64748B", 600: "#475569",
          700: "#334155", 800: "#1E293B", 900: "#0F172A",
        },
      },
      spacing: {
        "space-1": 4, "space-2": 8, "space-3": 12,
        "space-4": 16, "space-6": 24, "space-8": 32,
        "space-12": 48, "space-16": 64,
      },
      borderRadius: {
        sm: 4, DEFAULT: 8, md: 12, lg: 16, full: 9999,
      },
    },
    fontSize: {
      xs: ["14", { lineHeight: "20" }],
      sm: ["16", { lineHeight: "22" }],
      base: ["18", { lineHeight: "26" }],
      lg: ["20", { lineHeight: "28" }],
      xl: ["22", { lineHeight: "30" }],
      "2xl": ["26", { lineHeight: "34" }],
      "3xl": ["32", { lineHeight: "40" }],
    },
  },
  plugins: [],
};
