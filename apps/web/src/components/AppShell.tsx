"use client";

import {
  AlertCircle,
  BookOpen,
  FileText,
  History,
  Home,
  Layers,
  Network,
  NotebookPen,
  User as UserIcon,
} from "lucide-react";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { QuietLink } from "@/components/QuietLink";

import { brand } from "@/config/brand";
import { useMe } from "@/hooks/useMe";
import { TeacherPromoCard } from "@/components/TeacherPromoCard";

const NAV = [
  { href: "/dashboard", label: "首页", icon: Home },
  { href: "/practice", label: "单元练习", icon: BookOpen },
  { href: "/knowledge", label: "知识图谱", icon: Network },
  { href: "/exams", label: "真题", icon: FileText },
  { href: "/cards", label: "记忆卡片", icon: Layers },
  { href: "/wrong", label: "错题本", icon: AlertCircle },
  { href: "/notes", label: "笔记本", icon: NotebookPen },
  { href: "/history", label: "做题记录", icon: History },
  { href: "/me", label: "我的", icon: UserIcon },
];

const TABS = [
  { href: "/practice", label: "练习", icon: BookOpen },
  { href: "/knowledge", label: "图谱", icon: Network },
  { href: "/exams", label: "真题", icon: FileText },
  { href: "/wrong", label: "错题", icon: AlertCircle },
  { href: "/me", label: "我的", icon: UserIcon },
];

function isActive(pathname: string, href: string) {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(href + "/");
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  const isLanding = pathname === "/";
  const isReview = pathname.endsWith("/review");
  const isExam = pathname.includes("/attempt/") && !isReview;
  const showSidebarPromo =
    pathname !== "/dashboard" && !pathname.startsWith("/practice/session/");
  const { user, loading } = useMe(!isLogin && !isLanding);

  if (isLogin || isLanding) return <>{children}</>;

  if (isReview) {
    return (
      <main className="main">
        <div className="page">{children}</div>
      </main>
    );
  }

  if (isExam) {
    return <main className="exam-main">{children}</main>;
  }

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center p-6">
        <div className="card card-pad w-full max-w-sm">
          <div className="skeleton h-3 w-24 mb-3" />
          <div className="skeleton h-8 w-48 mb-2" />
          <div className="skeleton h-3 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <QuietLink href="/dashboard" className="brand">
          <img
            src={brand.logo}
            alt=""
            width={34}
            height={34}
            className="brand-logo"
          />
          <span>
            <span className="brand-title block">{brand.name}</span>
            <span className="brand-sub">{brand.domain}</span>
          </span>
        </QuietLink>
        <nav className="side-nav">
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <QuietLink
                key={item.href}
                href={item.href}
                prefetchOnHover
                className="side-link"
                data-active={isActive(pathname, item.href)}
              >
                <Icon size={16} strokeWidth={1.8} />
                {item.label}
              </QuietLink>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          {showSidebarPromo && <TeacherPromoCard variant="sidebar" className="mb-3" />}
          <div className="truncate">{user?.nickname || "AP 学员"}</div>
          <div className="font-mono text-[11px] mt-1 truncate">
            {user?.email_masked || user?.phone_masked}
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="page">{children}</div>
      </main>

      <nav className="tabbar">
        {TABS.map((item) => {
          const Icon = item.icon;
          return (
            <QuietLink
              key={item.href}
              href={item.href}
              prefetchOnHover
              className="tab-link"
              data-active={isActive(pathname, item.href)}
            >
              <Icon size={18} strokeWidth={1.8} />
              {item.label}
            </QuietLink>
          );
        })}
      </nav>
    </div>
  );
}
