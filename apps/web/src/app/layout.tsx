import type { Metadata } from "next";

import { AppShell } from "@/components/AppShell";
import { brand } from "@/config/brand";
import { LanguageProvider } from "@/lib/i18n";
import { THEME_STORED_IDS, THEME_STORAGE_KEY } from "@/lib/theme";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(brand.url),
  applicationName: brand.name,
  title: `${brand.name} · AP Psychology`,
  description:
    `${brand.name} (${brand.domain}) AP Psychology practice, past papers, mistake review, and flashcards.`,
  openGraph: {
    siteName: brand.name,
    title: `${brand.name} · AP Psychology`,
    description:
      `${brand.name} (${brand.domain}) AP Psychology practice, past papers, mistake review, and flashcards.`,
    url: brand.url,
    type: "website",
  },
};

const themeBootScript = `(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});var ok=${JSON.stringify(THEME_STORED_IDS)};if(ok.indexOf(t)>=0){document.documentElement.dataset.accent=t;}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
        <LanguageProvider>
          <AppShell>{children}</AppShell>
        </LanguageProvider>
      </body>
    </html>
  );
}
