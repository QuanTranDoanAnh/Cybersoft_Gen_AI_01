import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        muted: "#667085",
        line: "#d9e0e8",
        surface: "#ffffff",
        canvas: "#f5f7fa",
        teal: "#0f766e",
        coral: "#e75b47",
        amber: "#b7791f"
      },
      boxShadow: {
        panel: "0 12px 30px rgba(23, 32, 51, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
