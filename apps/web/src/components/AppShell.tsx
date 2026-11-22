"use client";

import {
  AlertCircle,
  Bookmark,
  BookOpen,
  FileText,
  History,
  Home,
  Layers,
  Network,
  NotebookPen,
} from "lucide-react";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { QuietLink } from "@/components/QuietLink";

import { brand } from "@/config/brand";
import { useMe } from "@/hooks/useMe";
import { LanguageSwitcher, useLanguage } from "@/lib/i18n";
import { ProfileSetupModal } from "@/components/ProfileSetupModal";
import { TeacherPromoCard } from "@/components/TeacherPromoCard";
import { UserMenu } from "@/components/UserMenu";

const NAV = [
  { href: "/dashboard", label: "首页", icon: Home },
  { href: "/practice", label: "单元练习", icon: BookOpen },
  { href: "/knowledge", label: "知识图谱", icon: Network },
  { href: "/exams", label: "真题", icon: FileText },
  { href: "/cards", label: "记忆卡片", icon: Layers },
  { href: "/wrong", label: "错题本", icon: AlertCircle },
  { href: "/bookmarks", label: "收藏题目", icon: Bookmark },
  { href: "/notes", label: "笔记本", icon: NotebookPen },
  { href: "/history", label: "做题记录", icon: History },
];

const TABS = [
  { href: "/practice", label: "练习", icon: BookOpen },
  { href: "/knowledge", label: "图谱", icon: Network },
  { href: "/exams", label: "真题", icon: FileText },
  { href: "/wrong", label: "错题", icon: AlertCircle },
];

function isActive(pathname: string, href: string) {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(href + "/");
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { t } = useLanguage();
  const isLogin = pathname === "/login";
  const isLanding = pathname === "/";
  const isReview = pathname.endsWith("/review");
  const isExam = pathname.includes("/attempt/") && !isReview;
  const showSidebarPromo =
    pathname !== "/dashboard" && !pathname.startsWith("/practice/session/");
  const { user, loading } = useMe(!isLogin && !isLanding);
  const [setupOpen, setSetupOpen] = useState(false);

  useEffect(() => {
    if (!user || user.profile_completed) {
      setSetupOpen(false);
      return;
    }
    try {
      // Dismissal lasts for this sign-in session; the prompt returns on the
      // next fresh session until the profile is completed.
      if (window.sessionStorage.getItem(`ap:profile-setup-dismissed:${user.id}`)) {
        return;
      }
    } catch {
      // Browser storage can be unavailable; show the prompt.
    }
    setSetupOpen(true);
  }, [user]);

  function closeSetup() {
    setSetupOpen(false);
    if (!user) return;
    try {
      window.sessionStorage.setItem(`ap:profile-setup-dismissed:${user.id}`, "1");
    } catch {
      // Ignore storage failure; dismissal still applies to this page view.
    }
  }

  if (isLogin || isLanding) return <>{children}</>;

  if (isReview) {
    return (
      <main className="main">
        <div className="user-corner">
          <UserMenu user={user} />
        </div>
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
                {t(item.label)}
              </QuietLink>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          <div className="mb-3">
            <LanguageSwitcher />
          </div>
          {showSidebarPromo && <TeacherPromoCard variant="sidebar" className="mb-3" />}
          <div className="truncate">{user?.nickname || t("AP 学员")}</div>
          <div className="font-mono text-[11px] mt-1 truncate">
            {user?.email_masked || user?.phone_masked}
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="page">{children}</div>
      </main>

      <div className="user-corner">
        <UserMenu user={user} />
      </div>

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
              {t(item.label)}
            </QuietLink>
          );
        })}
      </nav>

      <ProfileSetupModal
        open={setupOpen}
        user={user}
        onClose={closeSetup}
        onSaved={() => setSetupOpen(false)}
      />
    </div>
  );
}
