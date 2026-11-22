"use client";

import { Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";

import { Modal } from "@/components/Modal";
import { apiPatch } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { GRADE_VALUES, gradeLabel } from "@/lib/profile";
import type { User } from "@/lib/types";

export function ProfileSetupModal({
  open,
  user,
  onClose,
  onSaved,
}: {
  open: boolean;
  user: User | null;
  onClose: () => void;
  onSaved: (user: User) => void;
}) {
  const { t } = useLanguage();
  const [nickname, setNickname] = useState("");
  const [grade, setGrade] = useState("");
  const [region, setRegion] = useState("");
  const [targetScore, setTargetScore] = useState("");
  const [studied, setStudied] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !user) return;
    setNickname(user.nickname || "");
    setGrade(user.grade || "");
    setRegion(user.region || "");
    setTargetScore(user.target_score ? String(user.target_score) : "");
    setStudied(
      user.studied_psychology === null || user.studied_psychology === undefined
        ? ""
        : user.studied_psychology
          ? "yes"
          : "no",
    );
    setError(null);
  }, [open, user]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        grade: grade || null,
        region: region.trim(),
        target_score: targetScore ? Number(targetScore) : null,
        studied_psychology: studied === "" ? null : studied === "yes",
        complete_profile: true,
      };
      // All fields are optional here. Only send a nickname when one was
      // entered, so a blank box does not overwrite an existing nickname.
      if (nickname.trim()) payload.nickname = nickname.trim();
      const response = await apiPatch<{ user: User }>("/me", payload);
      window.dispatchEvent(
        new CustomEvent("ap:user-updated", { detail: response.user }),
      );
      onSaved(response.user);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("保存失败，请重试"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t("完善个人信息")} narrow>
      <form className="space-y-3.5" onSubmit={submit}>
        <p className="text-[12px] leading-5 muted">
          {t("想填几项就填几项，保存后也可以在「我的」页面继续补充；填写的信息会同步给老师。")}
        </p>

        <label className="block">
          <span className="text-[12px] muted">{t("昵称")}</span>
          <input
            className="input mt-1.5"
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            maxLength={64}
            placeholder={t("设置昵称")}
            autoFocus
          />
        </label>

        <label className="block">
          <span className="text-[12px] muted">{t("年级")}</span>
          <select
            className="input mt-1.5"
            value={grade}
            onChange={(event) => setGrade(event.target.value)}
          >
            <option value="">{t("请选择年级")}</option>
            {GRADE_VALUES.map((value) => (
              <option key={value} value={value}>
                {gradeLabel(value, t)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[12px] muted">{t("地区")}</span>
          <input
            className="input mt-1.5"
            value={region}
            onChange={(event) => setRegion(event.target.value)}
            maxLength={64}
            placeholder={t("例如：上海 / 北京 / 美国")}
          />
        </label>

        <label className="block">
          <span className="text-[12px] muted">{t("目标分数")}</span>
          <select
            className="input mt-1.5"
            value={targetScore}
            onChange={(event) => setTargetScore(event.target.value)}
          >
            <option value="">{t("请选择目标分数")}</option>
            {[1, 2, 3, 4, 5].map((score) => (
              <option key={score} value={score}>
                {t("{score} 分", { score })}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[12px] muted">{t("是否学过心理课")}</span>
          <select
            className="input mt-1.5"
            value={studied}
            onChange={(event) => setStudied(event.target.value)}
          >
            <option value="">{t("请选择")}</option>
            <option value="yes">{t("学过")}</option>
            <option value="no">{t("没有学过")}</option>
          </select>
        </label>

        {error && <div className="text-[12px] text-[var(--danger)]">{error}</div>}

        <div className="flex items-center gap-2 pt-1">
          <button className="btn btn-primary flex-1" type="submit" disabled={saving}>
            {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
            {saving ? t("保存中…") : t("保存并继续")}
          </button>
          <button type="button" className="btn" onClick={onClose} disabled={saving}>
            {t("稍后填写")}
          </button>
        </div>
      </form>
    </Modal>
  );
}
