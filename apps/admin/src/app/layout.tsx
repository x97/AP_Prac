import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "PsyPrac Admin",
  description: "PsyPrac content publishing and student analytics",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
