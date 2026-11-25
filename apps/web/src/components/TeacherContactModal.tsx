"use client";

import { Check, Copy, Mail, MessageCircle } from "lucide-react";
import { useState } from "react";

import { Modal } from "@/components/Modal";
import { teacherProfile } from "@/config/teacher";
import { useLanguage } from "@/lib/i18n";

function initials(name: string) {
  return name.replace(/\s+/g, "").slice(0, 2) || "AP";
}

export function TeacherContactModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useLanguage();
  const [copied, setCopied] = useState(false);
  const [emailCopied, setEmailCopied] = useState(false);

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

  async function copyEmail() {
    if (!teacherProfile.email) return;
    try {
      await navigator.clipboard.writeText(teacherProfile.email);
      setEmailCopied(true);
      window.setTimeout(() => setEmailCopied(false), 1600);
    } catch {
      setEmailCopied(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t("联系老师")} narrow>
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-full bg-[var(--ink)] text-[12px] font-semibold text-[var(--surface)]">
            {initials(teacherProfile.name)}
          </span>
          <div>
            <div className="text-[14px] font-semibold">{teacherProfile.name}</div>
            <div className="text-[11px] text-[var(--muted)]">
              {t(teacherProfile.tagline)}
            </div>
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
            </div>
          </div>
        )}

        {teacherProfile.email && (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-[var(--line)] px-3.5 py-3">
            <a
              href={`mailto:${teacherProfile.email}`}
              className="flex min-w-0 items-center gap-2.5"
            >
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[var(--primary-soft)] text-[var(--primary)]">
                <Mail size={15} />
              </span>
              <span className="min-w-0">
                <span className="block text-[10px] uppercase tracking-[0.1em] text-[var(--faint)]">
                  {t("邮箱")}
                </span>
                <span className="mt-0.5 block truncate font-mono text-[13px]">
                  {teacherProfile.email}
                </span>
              </span>
            </a>
            <button
              type="button"
              onClick={copyEmail}
              className="flex shrink-0 items-center gap-1 text-[11px] text-[var(--primary)]"
            >
              {emailCopied ? <Check size={13} /> : <Copy size={13} />}
              {emailCopied ? t("已复制") : t("复制")}
            </button>
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
              <span className="mt-0.5 block font-mono text-[13px]">
                {teacherProfile.wechatId}
              </span>
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
            {t("预约 20 分钟诊断")}
          </a>
        )}

        <p className="text-[11px] leading-5 faint">{t(teacherProfile.note)}</p>
      </div>
    </Modal>
  );
}
