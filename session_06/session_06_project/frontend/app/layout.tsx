import type { Metadata } from "next";
import "./globals.css";


export const metadata: Metadata = {
  title: "InsightFlow — AI Business Intelligence",
  description: "Ask questions, explore data and build dashboards with AI.",
};


export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
