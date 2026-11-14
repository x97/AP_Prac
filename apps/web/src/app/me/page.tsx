"use client";

import {
  Bookmark,
  History,
  KeyRound,
  Layers,
  LogOut,
  NotebookPen,
  Target,
} from "lucide-react";
import { useEffect, useState } from "react";

import { CourseAccessCard } from "@/components/CourseAccessCard";
import { ThemeColorPicker } from "@/components/ThemeColorPicker";
import { useMe } from "@/hooks/useMe";
import { QuietLink } from "@/components/QuietLink";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Dashboard, User } from "@/lib/types";

export default function MePage() {
  const { user, error: meError } = useMe();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nickname, setNickname] = useState("");
  const [savingNickname, setSavingNickname] = useState(false);
  const [nicknameError, setNicknameError] = useState<string | null>(null);
  const [nicknameSaved, setNicknameSaved] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSaved, setPasswordSaved] = useState(false);

  useEffect(() => {
    if (!user) return;
    setNickname(user.nickname || "");
  }, [user]);

  useEffect(() => {
    apiGet<Dashboard>("/me/dashboard")
      .then(setDashboard)
      .catch((e: Error) => setError(e.message));
  }, []);

  async function saveNickname(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = nickname.trim();
    if (!value) {
      setNicknameError("昵称不能为空");
      return;
    }
    setSavingNickname(true);
    setNicknameError(null);
    setNicknameSaved(false);
    try {
      const response = await apiPatch<{ user: User }>("/me", { nickname: value });
      setNickname(response.user.nickname || "");
      setNicknameSaved(true);
      window.dispatchEvent(
        new CustomEvent("ap:user-updated", { detail: response.user }),
      );
    } catch (e) {
      setNicknameError(e instanceof Error ? e.message : "昵称保存失败");
    } finally {
      setSavingNickname(false);
    }
  }

  async function changePassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordSaved(false);
    if (newPassword.length < 8) {
      setPasswordError("新密码至少需要 8 位");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("两次输入的新密码不一致");
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
        error instanceof Error ? error.message : "密码修改失败",
      );
    } finally {
      setSavingPassword(false);
    }
  }

  async function logout() {
    try {
      await apiPost("/auth/logout");
    } finally {
      window.location.replace("/");
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">Profile</div>
          <h1 className="h1">Profile</h1>
        </div>
      </div>

      {(error || meError) && <div className="feedback feedback-bad">{error || meError}</div>}

      <div className="card card-pad max-w-xl">
        <div className="flex items-center gap-4">
          <div className="h-14 w-14 rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)] grid place-items-center text-xl font-bold">
            AP
          </div>
          <div>
            <div className="font-semibold text-[16px]">{user?.nickname || "AP Student"}</div>
            <div className="text-[12px] muted font-mono mt-0.5">
              {user?.email_masked || user?.phone_masked || "未绑定邮箱"}
            </div>
          </div>
        </div>

        <form className="mt-5" onSubmit={saveNickname}>
          <label className="block text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
            Nickname
          </label>
          <div className="flex items-center gap-2 mt-1.5">
            <input
              className="input"
              value={nickname}
              onChange={(event) => {
                setNickname(event.target.value);
                setNicknameSaved(false);
                setNicknameError(null);
              }}
              maxLength={64}
              placeholder="Set a nickname"
              aria-label="Nickname"
            />
            <button
              type="submit"
              className="btn btn-sm btn-primary shrink-0"
              disabled={savingNickname || !nickname.trim()}
            >
              {savingNickname ? "Saving…" : "Save"}
            </button>
          </div>
          <div className="flex items-center justify-between gap-2 mt-1.5">
            <span className="text-[10.5px] faint">
              Nicknames can be duplicated across students.
            </span>
            {nicknameSaved && (
              <span className="text-[10.5px] text-[var(--success)]">Saved</span>
            )}
          </div>
          {nicknameError && (
            <div className="text-[11px] text-[var(--danger)] mt-1">{nicknameError}</div>
          )}
        </form>

        <div className="mt-6 border-t border-[var(--line)] pt-5">
          <CourseAccessCard embedded />
        </div>

        <div className="grid grid-cols-3 gap-3 mt-6">
          <div className="rounded-xl border border-[var(--line)] p-3">
            <div className="stat-value text-[22px]">{dashboard?.overview.answered ?? 0}</div>
            <div className="stat-label">Questions Answered</div>
          </div>
          <div className="rounded-xl border border-[var(--line)] p-3">
            <div className="stat-value text-[22px]">
              {dashboard?.overview.accuracy === null || dashboard?.overview.accuracy === undefined
                ? "—"
                : `${Math.round(dashboard.overview.accuracy * 100)}%`}
            </div>
            <div className="stat-label">Accuracy</div>
          </div>
          <div className="rounded-xl border border-[var(--line)] p-3">
            <div className="stat-value text-[22px]">{dashboard?.overview.streak_days ?? 0}</div>
            <div className="stat-label">Day Streak</div>
          </div>
        </div>

        <div className="mt-6 border-t border-[var(--line)] pt-5">
          <div className="flex items-center gap-2 text-[13px] font-semibold">
            <KeyRound size={15} /> 账号安全
          </div>
          <div className="text-[11.5px] faint mt-1">
            登录邮箱：{user?.email_masked || "未绑定"}
          </div>
          {user?.has_password ? (
            <form className="mt-3 space-y-2" onSubmit={changePassword}>
              <input
                className="input"
                type="password"
                autoComplete="current-password"
                placeholder="当前密码"
                aria-label="当前密码"
                value={oldPassword}
                onChange={(event) => {
                  setOldPassword(event.target.value);
                  setPasswordSaved(false);
                }}
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  className="input"
                  type="password"
                  autoComplete="new-password"
                  placeholder="新密码（至少 8 位）"
                  aria-label="新密码"
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
                  placeholder="确认新密码"
                  aria-label="确认新密码"
                  value={confirmPassword}
                  onChange={(event) => {
                    setConfirmPassword(event.target.value);
                    setPasswordSaved(false);
                  }}
                />
              </div>
              <div className="flex items-center justify-between gap-2">
                <button
                  className="btn btn-sm btn-primary"
                  type="submit"
                  disabled={
                    savingPassword || !oldPassword || !newPassword || !confirmPassword
                  }
                >
                  {savingPassword ? "保存中…" : "修改密码"}
                </button>
                {passwordSaved && (
                  <span className="text-[11px] text-[var(--success)]">
                    密码已更新，其他设备已退出
                  </span>
                )}
              </div>
              {passwordError && (
                <div className="text-[11px] text-[var(--danger)]">{passwordError}</div>
              )}
            </form>
          ) : (
            <div className="text-[11.5px] muted mt-2">
              当前账号还没有密码。请在微信端绑定邮箱后设置密码。
            </div>
          )}
        </div>

        <div className="mt-6 space-y-2">
          <QuietLink href="/history" className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]">
            <span className="flex items-center gap-2 text-[13.5px]">
              <History size={15} /> History
            </span>
            <span className="text-[11px] faint">→</span>
          </QuietLink>
          <QuietLink href="/cards" className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]">
            <span className="flex items-center gap-2 text-[13.5px]">
              <Layers size={15} /> Flashcards
            </span>
            <span className="text-[11px] faint">→</span>
          </QuietLink>
          <QuietLink href="/bookmarks" className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]">
            <span className="flex items-center gap-2 text-[13.5px]">
              <Bookmark size={15} /> Bookmarks
            </span>
            <span className="text-[11px] faint">→</span>
          </QuietLink>
          <QuietLink href="/notes" className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]">
            <span className="flex items-center gap-2 text-[13.5px]">
              <NotebookPen size={15} /> Notebook
            </span>
            <span className="text-[11px] faint">→</span>
          </QuietLink>
          <QuietLink href="/wrong" className="flex items-center justify-between rounded-xl border border-[var(--line)] px-4 py-3 hover:bg-[var(--surface-2)]">
            <span className="flex items-center gap-2 text-[13.5px]">
              <Target size={15} /> Wrong Book
            </span>
            <span className="text-[11px] faint">→</span>
          </QuietLink>
        </div>

        <button className="btn btn-ghost mt-6 text-[var(--danger)]" onClick={logout}>
          <LogOut size={15} /> Log Out
        </button>
      </div>

      <ThemeColorPicker />

      <p className="text-[11px] faint mt-4 max-w-xl leading-5">
        Your email is used only for login and account recovery. Question content comes from CB exams, Barron, and Myers materials for personal study.
      </p>
    </div>
  );
}
