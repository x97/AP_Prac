"use client";

import { MessageCircleQuestion } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

export function QaBell() {
  const { t } = useLanguage();
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const value = await apiGet<{ unread: number }>("/qa/unread-count");
        if (alive) setUnread(value.unread || 0);
      } catch {
        // Unauthenticated or transient failure: keep the last count.
      }
    }
    // No polling: refresh when a page is opened (route change/mount),
    // when the tab regains focus, or after a thread is read locally.
    load();
    function refresh() {
      load();
    }
    window.addEventListener("focus", refresh);
    window.addEventListener("ap:qa-read", refresh);
    return () => {
      alive = false;
      window.removeEventListener("focus", refresh);
      window.removeEventListener("ap:qa-read", refresh);
    };
  }, [pathname]);

  return (
    <Link
      href="/qa"
      className="qa-bell"
      aria-label={t("老师答疑")}
      title={unread > 0 ? t("有 {count} 条答疑回复", { count: unread }) : t("老师答疑")}
    >
      <MessageCircleQuestion size={17} strokeWidth={1.9} />
      {unread > 0 && (
        <span className="qa-bell-badge">{unread > 99 ? "99+" : unread}</span>
      )}
    </Link>
  );
}
