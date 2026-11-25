import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "老师答疑 · PsyPrac",
  description: "查看你在学习日历作业中向老师提出的问题和老师回复。",
  robots: { index: false, follow: false },
};

export default function QaLayout({ children }: { children: React.ReactNode }) {
  return children;
}
