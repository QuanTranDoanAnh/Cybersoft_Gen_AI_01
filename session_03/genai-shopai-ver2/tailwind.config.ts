import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          orange: "#ee4d2d",
          teal: "#0f766e",
          ink: "#182230",
          soft: "#f6f7fb"
        }
      },
      boxShadow: {
        panel: "0 18px 50px rgba(15, 23, 42, 0.14)"
      }
    }
  },
  plugins: []
};

export default config;

