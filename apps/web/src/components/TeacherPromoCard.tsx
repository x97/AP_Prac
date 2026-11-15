"use client";

import { ArrowRight, CalendarClock, Check, Copy, MessageCircle, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Modal } from "@/components/Modal";
import { teacherProfile } from "@/config/teacher";
import { useLanguage } from "@/lib/i18n";

type PromoVariant = "sidebar" | "home" | "result";

function initials(name: string) {
  return name.replace(/\s+/g, "").slice(0, 2) || "AP";
}

export function TeacherPromoCard({
  variant = "home",
  className = "",
}: {
  variant?: PromoVariant;
  className?: string;
}) {
  const { t } = useLanguage();
  const [hidden, setHidden] = useState(false);
  const [contactOpen, setContactOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const storageKey = "ap:teacher-promo-dismissed-on";

  useEffect(() => {
    if (!teacherProfile.enabled) return;
    try {
      const raw = window.localStorage.getItem(storageKey);
      const today = new Date();
      const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
      if (raw === todayKey) {
        setHidden(true);
      } else if (raw) {
        // Remove legacy timestamp values; only the current calendar day matters.
        window.localStorage.removeItem(storageKey);
      }
    } catch {
      // Storage can be unavailable in private mode.
    }
  }, [storageKey]);

  if (!teacherProfile.enabled || hidden) return null;

  function dismiss() {
    try {
      const today = new Date();
      const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
      window.localStorage.setItem(storageKey, todayKey);
    } catch {
      // Ignore storage failure; hide for this page view.
    }
    setHidden(true);
  }

  async function copyWechat() {
    if (!teacherProfile.wechatId) return;
    try {
      await navigator.clipboard.writeText(teacherProfile.wechatId);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  function openBooking() {
    if (teacherProfile.bookingUrl) {
      window.open(teacherProfile.bookingUrl, "_blank", "noopener,noreferrer");
      return;
    }
    setContactOpen(true);
  }

  return (
    <>
      {variant === "sidebar" && (
        <div className={`relative rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3 ${className}`}>
          <button
            type="button"
            onClick={dismiss}
            className="absolute right-1.5 top-1.5 rounded p-1 text-[var(--faint)] hover:bg-[var(--surface)]"
            aria-label="Dismiss teacher card"
          >
            <X size={12} />
          </button>
          <div className="flex items-center gap-2.5 pr-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[var(--ink)] text-[11px] font-semibold text-[var(--surface)]">
              {initials(teacherProfile.name)}
            </span>
            <div className="min-w-0">
              <div className="truncate text-[12px] font-semibold">{teacherProfile.name}</div>
              <div className="mt-0.5 truncate text-[10px] text-[var(--muted)]">
                {t(teacherProfile.tagline)}
              </div>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-primary btn-sm mt-3 w-full"
            onClick={() => setContactOpen(true)}
          >
            <MessageCircle size={13} /> {t("获取激活码")}
          </button>
        </div>
      )}

      {variant === "home" && (
        <div className={`card card-pad relative overflow-hidden ${className}`}>
          <div className="absolute -right-8 -top-10 h-28 w-28 rounded-full bg-[var(--accent-soft)]" />
          <div className="relative">
            <div className="eyebrow">1v1 Coaching</div>
            <h2 className="h2 mt-2">{t("需要老师帮你看一下？")}</h2>
            <p className="mt-2 text-[12.5px] leading-5 muted">
              {t("20 分钟学习诊断：当前水平、薄弱 Unit、下一步练习计划。")}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" className="btn btn-primary btn-sm" onClick={openBooking}>
                <CalendarClock size={14} /> {t("预约诊断")}
              </button>
              <button type="button" className="btn btn-sm" onClick={() => setContactOpen(true)}>
                <MessageCircle size={14} /> {t("微信咨询/获取激活码")}
              </button>
            </div>
          </div>
        </div>
      )}

      {variant === "result" && (
        <div className={`card card-pad mt-5 border-[color-mix(in_srgb,var(--primary)_24%,var(--line))] ${className}`}>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex min-w-0 items-start gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[var(--ink)] text-[12px] font-semibold text-[var(--surface)]">
                {initials(teacherProfile.name)}
              </span>
              <div className="min-w-0">
                <div className="eyebrow">Next step</div>
                <h2 className="h2 mt-1">{t("想让老师帮你看一下这份结果？")}</h2>
                <p className="mt-1.5 max-w-[560px] text-[12.5px] leading-5 muted">
                  {t("可以约一次 20 分钟诊断，一起看薄弱概念和下一步练习安排。")}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <button type="button" className="btn btn-primary btn-sm" onClick={openBooking}>
                <CalendarClock size={14} /> {t("预约诊断")}
                <ArrowRight size={13} />
              </button>
              <button type="button" className="btn btn-sm" onClick={() => setContactOpen(true)}>
                <MessageCircle size={14} /> {t("微信咨询/获取激活码")}
              </button>
            </div>
          </div>
        </div>
      )}

      <Modal open={contactOpen} onClose={() => setContactOpen(false)} title={t("联系老师")} narrow>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-full bg-[var(--ink)] text-[12px] font-semibold text-[var(--surface)]">
              {initials(teacherProfile.name)}
            </span>
            <div>
              <div className="text-[14px] font-semibold">{teacherProfile.name}</div>
              <div className="text-[11px] text-[var(--muted)]">{t(teacherProfile.tagline)}</div>
            </div>
          </div>

          <p className="text-[12.5px] leading-5 muted">{t(teacherProfile.intro)}</p>

          {teacherProfile.qrImage ? (
            <div className="text-center">
              <img
                src={teacherProfile.qrImage}
                alt={t("{name} 微信二维码", { name: teacherProfile.name })}
                className="mx-auto w-[240px] rounded-xl border border-[var(--line)] bg-white p-2"
              />
              <div className="mt-2 text-[11px] faint">{t("扫码添加微信")}</div>
            </div>
          ) : (
            <div className="grid min-h-[150px] place-items-center rounded-xl border border-dashed border-[var(--line)] bg-[var(--surface-2)] p-4 text-center">
              <div>
                <MessageCircle size={26} className="mx-auto text-[var(--faint)]" />
                <div className="mt-2 text-[12px] font-medium">{t("微信二维码")}</div>
                <div className="mt-1 text-[10.5px] faint">
                  {t("在")} <code>config/teacher.ts</code> {t("配置二维码")}
                </div>
              </div>
            </div>
          )}

          {teacherProfile.wechatId && (
            <button
              type="button"
              onClick={copyWechat}
              className="flex w-full items-center justify-between gap-3 rounded-xl border border-[var(--line)] px-3.5 py-3 text-left hover:bg-[var(--surface-2)]"
            >
              <span>
                <span className="block text-[10px] uppercase tracking-[0.1em] text-[var(--faint)]">
                  WeChat
                </span>
                <span className="mt-0.5 block font-mono text-[13px]">{teacherProfile.wechatId}</span>
              </span>
              <span className="flex items-center gap-1 text-[11px] text-[var(--primary)]">
                {copied ? <Check size={13} /> : <Copy size={13} />}
                {copied ? t("已复制") : t("复制")}
              </span>
            </button>
          )}

          {teacherProfile.bookingUrl && (
            <a
              href={teacherProfile.bookingUrl}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary w-full"
            >
              <CalendarClock size={15} /> {t("预约 20 分钟诊断")}
            </a>
          )}

          <p className="text-[11px] leading-5 faint">{t(teacherProfile.note)}</p>
        </div>
      </Modal>
    </>
  );
}
