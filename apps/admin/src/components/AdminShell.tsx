"use client";

import {
  AlertTriangle,
  BookOpen,
  CalendarRange,
  ClipboardList,
  FileText,
  Network,
  KeyRound,
  LayoutDashboard,
  ListChecks,
  Loader2,
  LogOut,
  MessageCircleQuestion,
  ScrollText,
  Upload,
  Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";

import { apiGet, apiPost } from "@/lib/api";
import type { Admin, AdminSubject } from "@/lib/types";

import { AdminQaBell } from "./AdminQaBell";

const AdminContext = createContext<Admin | null>(null);

export function useAdmin() {
  return useContext(AdminContext);
}

type AdminSubjectContextValue = {
  subjects: AdminSubject[];
  subjectId: string;
  subject: AdminSubject | null;
  setSubjectId: (value: string) => void;
};

const AdminSubjectContext = createContext<AdminSubjectContextValue | null>(null);

export function useAdminSubject() {
  const value = useContext(AdminSubjectContext);
  if (!value) {
    throw new Error("useAdminSubject must be used inside AdminShell");
  }
  return value;
}

const NAV = [
  { href: "/dashboard", label: "仪表盘", icon: LayoutDashboard },
  { href: "/students", label: "学生", icon: Users },
  { href: "/study-plans", label: "学习计划", icon: CalendarRange },
  { href: "/homeworks", label: "课堂作业", icon: ClipboardList },
  { href: "/qa", label: "老师答疑", icon: MessageCircleQuestion },
  { href: "/reports", label: "题目报错", icon: AlertTriangle },
  { href: "/codes", label: "激活码", icon: KeyRound },
  { href: "/content/papers", label: "试卷", icon: FileText },
  { href: "/content/questions", label: "题目", icon: ListChecks },
  { href: "/content/import", label: "批量导入", icon: Upload },
  { href: "/content/knowledge", label: "知识点", icon: BookOpen },
  { href: "/content/knowledge-graph", label: "知识图谱", icon: Network },
  { href: "/audit", label: "审计日志", icon: ScrollText },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subjects, setSubjects] = useState<AdminSubject[]>([]);
  const [subjectId, setSubjectIdState] = useState("psychology");

  useEffect(() => {
    let alive = true;
    apiGet<{ admin: Admin }>("/auth/me")
      .then((response) => {
        if (alive) setAdmin(response.admin);
      })
      .catch((e: Error) => {
        if (alive) setError(e.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!admin) return;
    let alive = true;
    apiGet<{ subjects: AdminSubject[] }>("/subjects?include_disabled=true")
      .then((response) => {
        if (!alive) return;
        setSubjects(response.subjects);
        const enabled = response.subjects.filter((item) => item.enabled);
        let stored = "psychology";
        try {
          stored = localStorage.getItem("ap-admin-subject") || "psychology";
        } catch {
          // Ignore browser storage failures.
        }
        const next =
          enabled.find((item) => item.subject_id === stored)?.subject_id ||
          enabled[0]?.subject_id ||
          "psychology";
        setSubjectIdState(next);
      })
      .catch(() => {
        if (alive) setSubjects([]);
      });
    return () => {
      alive = false;
    };
  }, [admin]);

  function setSubjectId(value: string) {
    setSubjectIdState(value);
    try {
      localStorage.setItem("ap-admin-subject", value);
    } catch {
      // Ignore browser storage failures.
    }
  }

  async function logout() {
    try {
      await apiPost("/auth/logout");
    } finally {
      router.replace("/login");
    }
  }

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Loader2 size={26} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  if (!admin) {
    return (
      <div className="auth-page">
        <div className="a-card auth-card text-center">
          <div className="font-semibold">管理员登录已失效</div>
          <p className="mt-2 text-[13px] text-[var(--muted)]">{error || "请重新登录后台。"}</p>
          <Link href="/login" className="a-btn a-btn-primary mt-4">
            去登录
          </Link>
        </div>
      </div>
    );
  }

  const selectedSubject =
    subjects.find((item) => item.subject_id === subjectId) || null;

  return (
    <AdminContext.Provider value={admin}>
    <AdminSubjectContext.Provider
      value={{ subjects, subjectId, subject: selectedSubject, setSubjectId }}
    >
    <div>
      <aside className="sidebar">
        <div className="side-brand flex items-center gap-2.5 px-2">
          <img
            src="/brand/psyprac-logo-sm.png"
            alt=""
            width={32}
            height={32}
            className="h-8 w-8 rounded-lg object-cover"
          />
          <div>
            <div className="text-[15px] font-semibold text-white">PsyPrac</div>
            <div className="mt-1 text-[11px] text-[var(--sidebar-muted)]">内容管理后台</div>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {NAV.filter((item) => item.href !== "/codes" || admin.role === "super_admin").map((item) => {
            const active =
              item.href === "/dashboard"
                ? pathname === item.href
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="side-link"
                data-active={active}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="side-foot">
          <div className="truncate text-[12px] text-white">{admin.username}</div>
          <div className="mt-0.5 text-[10.5px] text-[var(--sidebar-muted)]">
            {admin.role}
          </div>
          <button
            type="button"
            className="mt-3 flex items-center gap-2 text-[11.5px] text-[var(--sidebar-muted)] hover:text-white"
            onClick={logout}
          >
            <LogOut size={13} /> 退出登录
          </button>
        </div>
      </aside>

      <main className="admin-main">
        <div className="admin-top">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-[12px] text-[var(--muted)]">
              内部管理后台 · 仅限授权管理员
            </div>
            <label className="flex shrink-0 items-center gap-1.5 whitespace-nowrap text-[11px] text-[var(--muted)]">
              内容科目
              <select
                className="a-input max-w-[240px] py-1.5 text-[12px]"
                value={subjectId}
                onChange={(event) => setSubjectId(event.target.value)}
              >
                {subjects.map((item) => (
                  <option
                    key={item.subject_id}
                    value={item.subject_id}
                    disabled={!item.enabled}
                  >
                    {item.name}
                    {item.enabled ? "" : "（未启用）"}
                  </option>
                ))}
                {subjects.length === 0 && <option value="psychology">AP Psychology</option>}
              </select>
            </label>
          </div>
          <div className="flex items-center gap-2">
            <AdminQaBell />
            <span className="a-badge a-badge-primary">{admin.role}</span>
            <span className="a-badge">{admin.email}</span>
          </div>
        </div>
        {children}
      </main>
    </div>
    </AdminSubjectContext.Provider>
    </AdminContext.Provider>
  );
}
