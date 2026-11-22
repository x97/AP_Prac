import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "登录 / 注册",
  description:
    "登录或注册 PsyPrac，继续 AP Psychology Unit 练习、真题、错题本、知识图谱与记忆卡片。",
  alternates: { canonical: "/login" },
  robots: {
    index: false,
    follow: true,
  },
};

export default function LoginLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
