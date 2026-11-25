"use client";

import {
  BadgeCheck,
  ChevronDown,
  History,
  KeyRound,
  Languages,
  Loader2,
  LogOut,
  MessageCircleQuestion,
  Palette,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { apiPost } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { User } from "@/lib/types";

const SECTIONS = [
  { id: "profile", label: "个人信息", icon: UserRound },
  { id: "records", label: "学习记录", icon: History },
  { id: "access", label: "激活科目", icon: BadgeCheck },
  { id: "security", label: "修改密码", icon: KeyRound },
  { id: "theme", label: "主题颜色", icon: Palette },
];

export function UserMenu({ user }: { user: User | null }) {
  const { t, lang, setLanguage } = useLanguage();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      setShowHint(!window.localStorage.getItem("ap:user-menu-seen"));
    } catch {
      // Storage unavailable: keep the hint hidden to avoid a permanent dot.
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  function toggleMenu() {
    setOpen((value) => !value);
    setShowHint(false);
    try {
      window.localStorage.setItem("ap:user-menu-seen", "1");
    } catch {
      // Storage unavailable; the dot still disappears for this view.
    }
  }

  function goToSection(id: string) {
    setOpen(false);
    if (pathname === "/me") {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
      window.history.replaceState(null, "", `/me#${id}`);
      return;
    }
    router.push(`/me#${id}`);
  }

  async function logout() {
    setLoggingOut(true);
    try {
      await apiPost("/auth/logout");
    } finally {
      window.location.replace("/");
    }
  }

  const initials = (user?.nickname || "").trim().slice(0, 2).toUpperCase();
  const displayName = user?.nickname || t("AP 学员");
  const account = user?.email_masked || user?.phone_masked || t("未绑定邮箱");

  return (
    <div className="user-menu-root" ref={rootRef}>
      <button
        type="button"
        className="user-avatar-btn"
        aria-label={t("账号菜单")}
        aria-haspopup="menu"
        aria-expanded={open}
        title={t("账号菜单")}
        onClick={toggleMenu}
      >
        <span className="user-avatar-circle">
          {initials || <UserRound size={17} strokeWidth={1.9} />}
          {showHint && <span className="user-avatar-hint" aria-hidden="true" />}
        </span>
        <span className="user-avatar-label">{t("我的")}</span>
        <ChevronDown size={14} strokeWidth={2.1} className="user-avatar-chevron" />
      </button>

      {open && (
        <div className="user-menu-panel" role="menu">
          <div className="user-menu-head">
            <span className="user-menu-avatar">
              {initials || <UserRound size={17} strokeWidth={1.9} />}
            </span>
            <div className="min-w-0">
              <div className="user-menu-name">{displayName}</div>
              <div className="user-menu-account">{account}</div>
            </div>
          </div>

          <div className="user-menu-list">
            <Link
              href="/qa"
              className="user-menu-item"
              role="menuitem"
              onClick={() => setOpen(false)}
            >
              <MessageCircleQuestion size={16} strokeWidth={1.8} />
              {t("老师答疑")}
            </Link>
            {SECTIONS.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  type="button"
                  role="menuitem"
                  className="user-menu-item"
                  onClick={() => goToSection(section.id)}
                >
                  <Icon size={16} strokeWidth={1.8} />
                  {t(section.label)}
                </button>
              );
            })}
          </div>

          <div className="user-menu-lang">
            <span className="user-menu-lang-label">
              <Languages size={14} strokeWidth={1.8} />
              {t("语言")}
            </span>
            <span className="user-menu-lang-switch">
              <button
                type="button"
                data-active={lang === "zh"}
                onClick={() => setLanguage("zh")}
              >
                中文
              </button>
              <button
                type="button"
                data-active={lang === "en"}
                onClick={() => setLanguage("en")}
              >
                EN
              </button>
            </span>
          </div>

          <div className="user-menu-sep" />

          <button
            type="button"
            role="menuitem"
            className="user-menu-item user-menu-logout"
            onClick={logout}
            disabled={loggingOut}
          >
            {loggingOut ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <LogOut size={16} strokeWidth={1.8} />
            )}
            {t("退出")}
          </button>
        </div>
      )}
    </div>
  );
}
