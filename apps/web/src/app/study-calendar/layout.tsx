import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "学习日历 · PsyPrac",
  description: "按老师安排的学习计划，查看每天要完成的题目和进度。",
  robots: { index: false, follow: false },
};

export default function StudyCalendarLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
