import type { Metadata } from "next";

import { LandingPageContent } from "@/components/LandingPageContent";
import { brand } from "@/config/brand";

const title = `${brand.name} · AP Psychology 2027 备考练习与真题`;
const description =
  `${brand.name}（${brand.domain}）AP Psychology 2027 备考平台：按 CED Unit/Topic 练习、12 套真题与模拟、错题本、知识图谱和记忆卡片，Unit 1 免费体验。AP Psychology practice, past papers, and flashcards.`;

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: "/" },
  openGraph: {
    title,
    description,
    url: brand.url,
    type: "website",
    locale: "zh_CN",
    alternateLocale: ["en_US"],
    siteName: brand.name,
    images: [
      {
        url: brand.logoFull,
        width: 512,
        height: 512,
        alt: `${brand.name} · AP Psychology 2027`,
      },
    ],
  },
};

export default function LandingPage() {
  return <LandingPageContent />;
}
