"use client";

import {
  Bookmark,
  GraduationCap,
  History,
  KeyRound,
  Layers,
  MapPin,
  MessageCircleQuestion,
  NotebookPen,
  Target,
  UserRound,
} from "lucide-react";
import { useEffect, useState } from "react";

import { CourseAccessCard } from "@/components/CourseAccessCard";
import { QuietLink } from "@/components/QuietLink";
import { ThemeColorPicker } from "@/components/ThemeColorPicker";
import { useMe } from "@/hooks/useMe";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import {
  EXAM_TIME_VALUES,
  GRADE_VALUES,
  STUDY_MODE_VALUES,
  examTimeLabel,
  gradeLabel,
  studyModeLabel,
} from "@/lib/profile";
import type { Dashboard, User } from "@/lib/types";

export default function MePage() {
  const { t } = useLanguage();
  const { user, error: meError } = useMe();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nickname, setNickname] = useState("");
  const [grade, setGrade] = useState("");
  const [region, setRegion] = useState("");
  const [targetScore, setTargetScore] = useState("");
  const [studyMode, setStudyMode] = useState("");
  const [examTime, setExamTime] = useState("2027");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSaved, setProfileSaved] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSaved, setPasswordSaved] = useState(false);

  useEffect(() => {
    if (!user) return;
    setNickname(user.nickname || "");
    setGrade(user.grade || "");
    setRegion(user.region || "");
    setTargetScore(user.target_score ? String(user.target_score) : "");
    setStudyMode(user.study_mode || "");
    setExamTime(user.exam_time || "2027");
  }, [user]);

  useEffect(() => {
    apiGet<Dashboard>("/me/dashboard")
      .then(setDashboard)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    const id = window.location.hash.replace(/^#/, "");
    if (!id) return;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ block: "start" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  async function saveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = nickname.trim();
    if (!value) {
      setProfileError(t("昵称不能为空"));
      return;
    }
    setSavingProfile(true);
    setProfileError(null);
    setProfileSaved(false);
    try {
      const response = await apiPatch<{ user: User }>("/me", {
        nickname: value,
        grade: grade || null,
        region: region.trim(),
        target_score: targetScore ? Number(targetScore) : null,
        study_mode: studyMode || null,
        exam_time: examTime || "2027",
      });
      window.dispatchEvent(
        new CustomEvent("ap:user-updated", { detail: response.user }),
      );
      setProfileSaved(true);
    } catch (e) {
      setProfileError(e instanceof Error ? e.message : t("昵称保存失败"));
    } finally {
      setSavingProfile(false);
    }
  }

  async function changePassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordSaved(false);
    if (newPassword.length < 8) {
      setPasswordError(t("新密码至少需要 8 位"));
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError(t("两次输入的新密码不一致"));
      return;
    }
    setSavingPassword(true);
    try {
      await apiPost("/me/password", {
        old_password: oldPassword,
        new_password: newPassword,
      });
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordSaved(true);
    } catch (error) {
      setPasswordError(
        error instanceof Error ? error.message : t("密码修改失败"),
      );
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">{t("个人中心")}</div>
          <h1 className="h1">{t("我的")}</h1>
        </div>
      </div>

      {(error || meError) && <div className="feedback feedback-bad">{error || meError}</div>}

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]">
        <div className="space-y-4">
          <section id="profile" className="card card-pad scroll-mt-24">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="grid h-14 w-14 place-items-center rounded-2xl bg-[var(--primary-soft)] text-xl font-bold text-[var(--primary)]">
                  {user?.nickname?.slice(0, 2).toUpperCase() || "AP"}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <UserRound size={16} className="text-[var(--primary)]" />
                    <h2 className="h2">{t("基本信息")}</h2>
                  </div>
                  <div className="mt-1 text-[12px] font-mono text-[var(--muted)]">
                    {user?.email_masked || user?.phone_masked || t("未绑定邮箱")}
                  </div>
                </div>
              </div>
              {profileSaved && (
                <span className="text-[11px] text-[var(--success)]">{t("已保存")}</span>
              )}
            </div>

            <form className="mt-5" onSubmit={saveProfile}>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
                    {t("昵称")}
                  </span>
                  <input
                    className="input mt-1.5"
                    value={nickname}
                    onChange={(event) => {
                      setNickname(event.target.value);
                      setProfileSaved(false);
                      setProfileError(null);
                    }}
                    maxLength={64}
                    placeholder={t("设置昵称")}
                  />
                </label>
                <label className="block">
                  <span className="flex items-center gap-1 text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
                    <GraduationCap size={12} /> {t("年级")}
                  </span>
                  <select
                    className="input mt-1.5"
                    value={grade}
                    onChange={(event) => {
                      setGrade(event.target.value);
                      setProfileSaved(false);
                    }}
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
                  <span className="flex items-center gap-1 text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
                    <MapPin size={12} /> {t("地区")}
                  </span>
                  <input
                    className="input mt-1.5"
                    value={region}
                    onChange={(event) => {
                      setRegion(event.target.value);
                      setProfileSaved(false);
                    }}
                    maxLength={64}
                    placeholder={t("例如：上海 / 北京 / 美国")}
                  />
                </label>
                <label className="block">
                  <span className="flex items-center gap-1 text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
                    <Target size={12} /> {t("目标分数")}
                  </span>
                  <select
                    className="input mt-1.5"
                    value={targetScore}
                    onChange={(event) => {
                      setTargetScore(event.target.value);
                      setProfileSaved(false);
                    }}
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
                  <span className="text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
                    {t("学习方式")}
                  </span>
                  <select
                    className="input mt-1.5"
                    value={studyMode}
                    onChange={(event) => {
                      setStudyMode(event.target.value);
                      setProfileSaved(false);
                    }}
                  >
                    <option value="">{t("请选择学习方式")}</option>
                    {STUDY_MODE_VALUES.map((value) => (
                      <option key={value} value={value}>
                        {studyModeLabel(value, t)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
                    {t("考试时间")}
                  </span>
                  <select
                    className="input mt-1.5"
                    value={examTime}
                    onChange={(event) => {
                      setExamTime(event.target.value);
                      setProfileSaved(false);
                    }}
                  >
                    {EXAM_TIME_VALUES.map((value) => (
                      <option key={value} value={value}>
                        {examTimeLabel(value, t)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={savingProfile || !nickname.trim()}
                >
                  {savingProfile ? t("保存中…") : t("保存")}
                </button>
                {profileError && (
                  <span className="text-[11px] text-[var(--danger)]">{profileError}</span>
                )}
              </div>
            </form>
          </section>

          <section id="access" className="card card-pad scroll-mt-24">
            <CourseAccessCard embedded />
          </section>

          <section id="security" className="card card-pad scroll-mt-24">
            <div className="flex items-center gap-2 text-[13px] font-semibold">
              <KeyRound size={15} className="text-[var(--primary)]" /> {t("账号安全")}
            </div>
            <div className="mt-1 text-[11.5px] faint">
              {t("登录邮箱：{email}", {
                email: user?.email_masked || t("未绑定"),
              })}
            </div>
            {user?.has_password ? (
              <form className="mt-3 space-y-2" onSubmit={changePassword}>
                <input
                  className="input"
                  type="password"
                  autoComplete="current-password"
                  placeholder={t("当前密码")}
                  aria-label={t("当前密码")}
                  value={oldPassword}
                  onChange={(event) => {
                    setOldPassword(event.target.value);
                    setPasswordSaved(false);
                  }}
                />
                <div className="grid gap-2 sm:grid-cols-2">
                  <input
                    className="input"
                    type="password"
                    autoComplete="new-password"
                    placeholder={t("新密码（至少 8 位）")}
                    aria-label={t("新密码")}
                    value={newPassword}
                    onChange={(event) => {
                      setNewPassword(event.target.value);
                      setPasswordSaved(false);
                    }}
                  />
                  <input
                    className="input"
                    type="password"
                    autoComplete="new-password"
                    placeholder={t("确认新密码")}
                    aria-label={t("确认新密码")}
                    value={confirmPassword}
                    onChange={(event) => {
                      setConfirmPassword(event.target.value);
                      setPasswordSaved(false);
                    }}
                  />
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <button
                    className="btn btn-sm btn-primary"
                    type="submit"
                    disabled={
                      savingPassword || !oldPassword || !newPassword || !confirmPassword
                    }
                  >
                    {savingPassword ? t("保存中…") : t("修改密码")}
                  </button>
                  {passwordSaved && (
                    <span className="text-[11px] text-[var(--success)]">
                      {t("密码已更新，其他设备已退出")}
                    </span>
                  )}
                </div>
                {passwordError && (
                  <div className="text-[11px] text-[var(--danger)]">{passwordError}</div>
                )}
              </form>
            ) : (
              <div className="mt-2 text-[11.5px] muted">
                {t("当前账号还没有密码。请在微信端绑定邮箱后设置密码。")}
              </div>
            )}
          </section>
        </div>

        <div className="space-y-4">
          <section id="records" className="card card-pad scroll-mt-24">
            <div className="flex items-center justify-between gap-3">
              <h2 className="h2">{t("学习记录")}</h2>
              <span className="text-[10px] uppercase tracking-[0.1em] text-[var(--faint)]">
                {t("历史与复习")}
              </span>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2">
              <div className="rounded-xl border border-[var(--line)] p-3">
                <div className="stat-value text-[22px]">{dashboard?.overview.answered ?? 0}</div>
                <div className="stat-label">{t("已答题目")}</div>
              </div>
              <div className="rounded-xl border border-[var(--line)] p-3">
                <div className="stat-value text-[22px]">
                  {dashboard?.overview.accuracy === null ||
                  dashboard?.overview.accuracy === undefined
                    ? "—"
                    : `${Math.round(dashboard.overview.accuracy * 100)}%`}
                </div>
                <div className="stat-label">{t("正确率")}</div>
              </div>
              <div className="rounded-xl border border-[var(--line)] p-3">
                <div className="stat-value text-[22px]">
                  {dashboard?.overview.streak_days ?? 0}
                </div>
                <div className="stat-label">{t("连续学习天数")}</div>
              </div>
            </div>

            <div className="mt-4 space-y-2">
              <QuietLink
                href="/qa"
                className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]"
              >
                <span className="flex items-center gap-2 text-[13.5px]">
                  <MessageCircleQuestion size={15} /> {t("老师答疑")}
                </span>
                <span className="text-[11px] faint">→</span>
              </QuietLink>
              <QuietLink
                href="/history"
                className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]"
              >
                <span className="flex items-center gap-2 text-[13.5px]">
                  <History size={15} /> {t("做题记录")}
                </span>
                <span className="text-[11px] faint">→</span>
              </QuietLink>
              <QuietLink
                href="/cards"
                className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]"
              >
                <span className="flex items-center gap-2 text-[13.5px]">
                  <Layers size={15} /> {t("记忆卡片")}
                </span>
                <span className="text-[11px] faint">→</span>
              </QuietLink>
              <QuietLink
                href="/bookmarks"
                className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]"
              >
                <span className="flex items-center gap-2 text-[13.5px]">
                  <Bookmark size={15} /> {t("收藏题目")}
                </span>
                <span className="text-[11px] faint">→</span>
              </QuietLink>
              <QuietLink
                href="/notes"
                className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]"
              >
                <span className="flex items-center gap-2 text-[13.5px]">
                  <NotebookPen size={15} /> {t("笔记本")}
                </span>
                <span className="text-[11px] faint">→</span>
              </QuietLink>
              <QuietLink
                href="/wrong"
                className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]"
              >
                <span className="flex items-center gap-2 text-[13.5px]">
                  <Target size={15} /> {t("错题本")}
                </span>
                <span className="text-[11px] faint">→</span>
              </QuietLink>
            </div>
          </section>

          <section id="theme" className="card card-pad scroll-mt-24">
            <ThemeColorPicker embedded />
          </section>

          <p className="max-w-[320px] text-[10.5px] leading-4 faint">
            {t("邮箱仅用于登录和账号找回。题目内容来自 CB 真题、Barron 和 Myers 教材，仅供个人学习。")}
          </p>
        </div>
      </div>
    </div>
  );
}
