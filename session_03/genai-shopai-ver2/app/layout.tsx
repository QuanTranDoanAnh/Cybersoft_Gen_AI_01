import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShopAI Assistant",
  description: "Shopee-like ecommerce demo with an AI customer support assistant"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}

