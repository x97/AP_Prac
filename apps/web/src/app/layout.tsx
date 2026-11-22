import type { Metadata } from "next";

import { AppShell } from "@/components/AppShell";
import { brand } from "@/config/brand";
import { LanguageProvider } from "@/lib/i18n";
import { THEME_STORED_IDS, THEME_STORAGE_KEY } from "@/lib/theme";

import "./globals.css";

const siteTitle = `${brand.name} · AP Psychology 2027 备考练习与真题`;
const siteDescription =
  `${brand.name}（${brand.domain}）AP Psychology 2027 备考平台：按 CED Unit/Topic 练习、12 套真题与模拟、错题本、知识图谱和记忆卡片，Unit 1 免费体验。AP Psychology practice, past papers, and flashcards.`;

export const metadata: Metadata = {
  metadataBase: new URL(brand.url),
  applicationName: brand.name,
  title: {
    default: siteTitle,
    template: `%s · ${brand.name}`,
  },
  description: siteDescription,
  keywords: [
    "PsyPrac",
    "psyprac",
    "psyprac.com",
    "AP Psychology",
    "AP Psychology practice",
    "AP Psychology past papers",
    "AP Psychology flashcards",
    "AP 心理学",
    "AP 心理学练习",
    "AP Psychology 真题",
    "AP Psychology 备考",
    "CED Unit practice",
    "MCQ",
    "FRQ",
  ],
  authors: [{ name: brand.name, url: brand.url }],
  creator: brand.name,
  publisher: brand.name,
  category: "education",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  openGraph: {
    siteName: brand.name,
    title: siteTitle,
    description: siteDescription,
    url: brand.url,
    type: "website",
    locale: "zh_CN",
    alternateLocale: ["en_US"],
    images: [
      {
        url: brand.logoFull,
        width: 512,
        height: 512,
        alt: `${brand.name} · AP Psychology 2027`,
      },
    ],
  },
  twitter: {
    card: "summary",
    title: siteTitle,
    description: siteDescription,
    images: [brand.logoFull],
  },
};

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${brand.url}/#website`,
      url: `${brand.url}/`,
      name: brand.name,
      alternateName: ["psyprac", "PsyPrac AP Psychology"],
      description: siteDescription,
      inLanguage: ["zh-CN", "en"],
      publisher: { "@id": `${brand.url}/#organization` },
    },
    {
      "@type": "EducationalOrganization",
      "@id": `${brand.url}/#organization`,
      name: brand.name,
      alternateName: ["psyprac", "PsyPrac AP Psychology"],
      url: `${brand.url}/`,
      logo: `${brand.url}${brand.logoFull}`,
      description:
        "AP Psychology 2027 practice platform with CED Unit/Topic drills, past exams and mocks, knowledge graph, mistake bank, and flashcards.",
    },
  ],
};

const themeBootScript = `(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});var ok=${JSON.stringify(THEME_STORED_IDS)};if(ok.indexOf(t)>=0){document.documentElement.dataset.accent=t;}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
        <LanguageProvider>
          <AppShell>{children}</AppShell>
        </LanguageProvider>
      </body>
    </html>
  );
}
