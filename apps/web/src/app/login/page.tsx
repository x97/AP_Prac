"use client";

import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  Lock,
  Mail,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { brand } from "@/config/brand";
import { apiPost } from "@/lib/api";
import { LanguageSwitcher, useLanguage } from "@/lib/i18n";

type Mode = "login" | "register" | "reset";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const COPY: Record<Mode, { eyebrow: string; title: string; submit: string }> = {
  login: { eyebrow: "欢迎回来", title: "登录 PsyPrac", submit: "登录" },
  register: { eyebrow: "创建账号", title: "创建新账户", submit: "注册并登录" },
  reset: { eyebrow: "找回密码", title: "修改密码", submit: "设置新密码" },
};

function updateModeInUrl(mode: Mode) {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  if (mode === "login") params.delete("mode");
  else params.set("mode", mode);
  const query = params.toString();
  window.history.replaceState(null, "", `/login${query ? `?${query}` : ""}`);
}

export default function LoginPage() {
  const { t } = useLanguage();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [countdown, setCountdown] = useState(0);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [next, setNext] = useState("/dashboard");
  const [devCode, setDevCode] = useState<string | null>(null);

  const emailValid = EMAIL_RE.test(email.trim());
  const needsCode = mode !== "login";
  const copy = COPY[mode];

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const target = params.get("next");
    if (target && target.startsWith("/") && !target.startsWith("//")) {
      setNext(target);
    }
    const initialMode = params.get("mode");
    if (initialMode === "register" || initialMode === "reset") {
      setMode(initialMode);
    }
  }, []);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setInterval(
      () => setCountdown((value) => Math.max(0, value - 1)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [countdown]);

  function switchMode(nextMode: Mode) {
    setMode(nextMode);
    setPassword("");
    setCode("");
    setDevCode(null);
    setError(null);
    setNotice(null);
    updateModeInUrl(nextMode);
  }

  async function sendCode() {
    if (!emailValid) {
      setError(t("请输入有效的邮箱地址"));
      return;
    }
    setSending(true);
    setError(null);
    setNotice(null);
    try {
      const res = await apiPost<{
        ok: boolean;
        expires_in: number;
        debug_code?: string;
      }>("/auth/email/code", {
        email: email.trim(),
        purpose: mode === "register" ? "register" : "reset",
      });
      setDevCode(res.debug_code || null);
      setCountdown(60);
      setNotice(t("验证码已发送，请查收邮箱"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("验证码发送失败"));
    } finally {
      setSending(false);
    }
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (!emailValid) {
      setError(t("请输入有效的邮箱地址"));
      return;
    }
    if (!password || (needsCode && code.length < 4)) {
      setError(
        needsCode
          ? t("请填写邮箱、验证码和密码")
          : t("请填写邮箱和密码"),
      );
      return;
    }
    setLoading(true);
    try {
      if (mode === "login") {
        await apiPost("/auth/email/login", {
          email: email.trim(),
          password,
        });
        window.location.replace(next);
        return;
      }
      if (mode === "register") {
        await apiPost("/auth/email/register", {
          email: email.trim(),
          code,
          password,
        });
        window.location.replace(next);
        return;
      }
      await apiPost("/auth/email/reset-password", {
        email: email.trim(),
        code,
        password,
      });
      switchMode("login");
      setNotice(t("密码已重置，请用新密码登录"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("操作失败，请重试"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen grid place-items-center px-4 py-10">
      <div className="w-full max-w-[420px]">
        <div className="mb-4 flex items-center justify-between gap-3">
          <Link href="/" className="btn btn-sm btn-ghost -ml-2">
            <ArrowLeft size={14} /> {t("返回首页")}
          </Link>
          <LanguageSwitcher />
        </div>
        <div className="flex items-center gap-3 mb-7 px-2">
          <img
            src={brand.logo}
            alt=""
            width={44}
            height={44}
            className="brand-logo login-brand-logo"
          />
          <div>
            <div className="font-semibold text-[15px]">{brand.name}</div>
            <div className="eyebrow">{brand.domain}</div>
          </div>
        </div>

        <div className="card card-pad">
          <div className="eyebrow">{t(copy.eyebrow)}</div>
          <h1 className="h1 mt-2 text-[28px]">{t(copy.title)}</h1>
          <p className="muted text-[13px] mt-2">
            {mode === "reset"
              ? t("输入注册邮箱，验证后设置新密码。")
              : mode === "register"
                ? t("用邮箱创建账号，验证码会发送到该邮箱。")
                : t("单元练习、整卷模考、错题和笔记都会保存到你的账号。")}
          </p>

          <form className="mt-5 space-y-4" onSubmit={submit}>
            <label className="block">
              <span className="text-[12px] muted">{t("邮箱")}</span>
              <div className="relative mt-1.5">
                <Mail
                  size={15}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
                />
                <input
                  className="input pl-9"
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
            </label>

            <label className="block">
              <span className="text-[12px] muted">
                {mode === "reset" ? t("新密码") : t("密码")}
              </span>
              <div className="relative mt-1.5">
                <Lock
                  size={15}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
                />
                <input
                  className="input pl-9"
                  type="password"
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                  placeholder={mode === "login" ? t("输入密码") : t("至少 8 位")}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>
            </label>

            {needsCode && (
              <label className="block">
                <span className="text-[12px] muted">{t("验证码")}</span>
                <div className="flex items-center gap-2 mt-1.5">
                  <input
                    className="input tracking-[0.35em] font-mono"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    placeholder={t("6 位验证码")}
                    value={code}
                    onChange={(event) =>
                      setCode(event.target.value.replace(/\D/g, ""))
                    }
                  />
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost shrink-0"
                    onClick={sendCode}
                    disabled={sending || countdown > 0 || !emailValid}
                  >
                    {sending ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <ShieldCheck size={14} />
                    )}
                    {countdown > 0 ? `${countdown}s` : t("发送验证码")}
                  </button>
                </div>
                {devCode && (
                  <span className="text-[11px] faint mt-1 block">
                    {t("测试验证码：")} {devCode}
                  </span>
                )}
              </label>
            )}

            {error && (
              <div className="feedback feedback-bad text-[13px] text-[var(--danger)]">
                {error}
              </div>
            )}
            {notice && (
              <div className="text-[12.5px] text-[var(--success)]">{notice}</div>
            )}

            <button
              className="btn btn-primary w-full"
              type="submit"
              disabled={loading || !emailValid || !password}
            >
              {loading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <ArrowRight size={16} />
              )}
              {t(copy.submit)}
            </button>

            {mode === "login" ? (
              <>
                <button
                  type="button"
                  className="btn w-full"
                  onClick={() => switchMode("register")}
                >
                  {t("创建新账户")}
                </button>
                <div className="flex items-center justify-between text-[12px]">
                  <button
                    type="button"
                    className="muted hover:text-[var(--text)]"
                    onClick={() => switchMode("reset")}
                  >
                    {t("修改密码")}
                  </button>
                  <span className="faint">{t("邮箱是账号的唯一凭证")}</span>
                </div>
              </>
            ) : (
              <button
                type="button"
                className="btn w-full"
                onClick={() => switchMode("login")}
              >
                {mode === "register" ? t("已有账号？登录") : t("返回登录")}
              </button>
            )}
          </form>
        </div>

        <p className="text-center text-[11px] faint mt-5 leading-5">
          {t("登录即表示你同意用户协议与隐私政策。邮箱仅用于登录和账号找回。")}
        </p>
      </div>
    </main>
  );
}
