"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiPost } from "@/lib/api";
import type { Admin } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [next, setNext] = useState("/dashboard");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get("next");
    if (value && value.startsWith("/")) setNext(value);
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiPost<{ admin: Admin }>("/auth/login", { identifier, password });
      router.replace(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "登录失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="a-card auth-card">
        <img
          src="/brand/psyprac-logo-sm.png"
          alt=""
          width={48}
          height={48}
          className="h-12 w-12 rounded-xl object-cover"
        />
        <div className="mt-4 text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
          PsyPrac
        </div>
        <h1 className="mt-1 text-[26px] font-semibold tracking-[-0.03em]">
          管理后台
        </h1>
        <p className="mt-2 text-[12.5px] leading-5 text-[var(--muted)]">
          使用管理员账号、邮箱和密码登录。学生账号无法进入后台。
        </p>

        <form className="mt-6 space-y-3" onSubmit={submit}>
          <label className="block text-[12px] font-medium">
            账号或邮箱
            <input
              className="a-input mt-1.5"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              autoComplete="username"
              placeholder="admin 或 admin@example.com"
              required
            />
          </label>
          <label className="block text-[12px] font-medium">
            密码
            <input
              className="a-input mt-1.5"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
              {error}
            </div>
          )}
          <button className="a-btn a-btn-primary w-full" type="submit" disabled={busy}>
            {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
            登录后台
          </button>
        </form>

        <p className="mt-5 text-[10.5px] leading-5 text-[var(--faint)]">
          管理员账号由命令行创建：<code>python -m app.cli create-admin</code>
        </p>
      </div>
    </div>
  );
}
