"use client";

import { Check, Palette } from "lucide-react";
import { useEffect, useState } from "react";

import {
  applyThemeAccent,
  readStoredTheme,
  THEME_ACCENTS,
  THEME_STORAGE_KEY,
  type ThemeAccentId,
} from "@/lib/theme";

export function ThemeColorPicker({ embedded = false }: { embedded?: boolean }) {
  const [active, setActive] = useState<ThemeAccentId>("blue");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setActive(readStoredTheme());
  }, []);

  function choose(id: ThemeAccentId) {
    setActive(id);
    applyThemeAccent(id);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, id);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 1600);
    } catch {
      // localStorage can be unavailable in private mode; the visual choice
      // still applies for the current page.
    }
  }

  return (
    <div className={embedded ? "" : "card card-pad max-w-xl mt-4"}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
            Appearance
          </div>
          <h2 className="h2 mt-1 flex items-center gap-2">
            <Palette size={18} className="text-[var(--primary)]" /> 主题颜色
          </h2>
        </div>
        {saved && <span className="text-[10.5px] text-[var(--success)]">已保存</span>}
      </div>
      <p className="mt-1 text-[11.5px] muted leading-5">
        选择一套强调色，应用到练习、考试、知识图谱和卡片。默认是经典蓝。
      </p>

      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {THEME_ACCENTS.map((theme) => {
          const selected = active === theme.id;
          return (
            <button
              key={theme.id}
              type="button"
              onClick={() => choose(theme.id)}
              aria-pressed={selected}
              className={[
                "flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-left transition",
                selected
                  ? "border-[var(--primary)] bg-[var(--primary-soft)]"
                  : "border-[var(--line)] bg-[var(--surface)] hover:border-[var(--line-strong)]",
              ].join(" ")}
            >
              <span
                className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-black/10 text-white shadow-sm"
                style={{ background: theme.color }}
              >
                {selected && <Check size={14} strokeWidth={2.6} />}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[12px] font-semibold">{theme.label}</span>
                <span className="mt-0.5 block truncate text-[9.5px] text-[var(--faint)]">
                  {theme.tone}
                </span>
              </span>
            </button>
          );
        })}
      </div>
      <p className="mt-3 text-[10px] leading-4 faint">
        主题保存在当前浏览器；换设备或清除浏览器数据后需要重新选择。
      </p>
    </div>
  );
}
