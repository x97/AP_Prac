import type { Metadata } from "next";

import { LandingPageContent } from "@/components/LandingPageContent";
import { brand } from "@/config/brand";

export const metadata: Metadata = {
  title: `${brand.name} · AP Psychology 2027`,
  description:
    `${brand.name} (${brand.domain}) AP Psychology unit practice, past exams, knowledge graph, mistake bank, and flashcards. Try Unit 1 free, with practice organized by CED Unit/Topic.`,
  openGraph: {
    title: `${brand.name} · AP Psychology 2027`,
    description:
      `${brand.name} (${brand.domain}) AP Psychology unit practice, past exams, knowledge graph, mistake bank, and flashcards.`,
    images: [
      {
        url: brand.logoFull,
        width: 512,
        height: 512,
        alt: brand.name,
      },
    ],
  },
};

export default function LandingPage() {
  return <LandingPageContent />;
}
