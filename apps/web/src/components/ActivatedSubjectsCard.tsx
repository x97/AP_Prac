"use client";

import { ArrowRight, CheckCircle2, KeyRound } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { SubjectEntitlement } from "@/lib/types";

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function ActivatedSubjectsCard() {
  const { t } = useLanguage();
  const [items, setItems] = useState<SubjectEntitlement[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    apiGet<{ entitlements: SubjectEntitlement[]; active_count?: number }>(
      "/me/entitlements",
    )
      .then((response) => {
        if (alive) setItems(response.entitlements);
      })
      .catch((error: Error) => {
        if (alive) setError(error.message);
      });
    return () => {
      alive = false;
    };
  }, []);

  const active = (items || []).filter((item) => item.active);

  return (
    <section className="card card-pad mt-4" aria-label={t("已激活科目")}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="eyebrow">Activated subjects</div>
          <h2 className="h2 mt-1">{t("已激活科目")}</h2>
          <p className="mt-1 text-[11.5px] muted">
            {t("当前账号已开通的科目和有效期；未开通科目仍可免费体验部分内容。")}
          </p>
        </div>
        <Link href="/me" className="btn btn-sm">
          <KeyRound size={13} /> {t("管理 / 激活")}
          <ArrowRight size={13} />
        </Link>
      </div>

      {error && <div className="mt-3 text-[11.5px] text-[var(--danger)]">{error}</div>}
      {!items && !error && <div className="mt-3 skeleton h-14 w-full" />}
      {items && active.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {active.map((item) => (
            <div
              key={item.subject_id}
              className="flex min-w-[210px] items-center gap-2 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2.5"
            >
              <CheckCircle2 size={16} className="shrink-0 text-[var(--success)]" />
              <div className="min-w-0">
                <div className="truncate text-[12.5px] font-medium">
                  {item.name || item.subject_id}
                </div>
                <div className="text-[10.5px] muted">
                  {t("有效期至 {date}", { date: formatDate(item.expires_at) })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {items && active.length === 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px] text-[var(--muted)]">
          {t("暂无已激活科目。")}
          <Link href="/me" className="text-[var(--primary)] hover:underline">
            {t("去输入激活码 →")}
          </Link>
        </div>
      )}
    </section>
  );
}
