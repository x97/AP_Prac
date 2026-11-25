"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import componentMessages from "@/lib/i18n/messages/components";
import componentMessages2 from "@/lib/i18n/messages/components2";
import commonMessages from "@/lib/i18n/messages/common";
import landingMessages from "@/lib/i18n/messages/landing";
import studyCalendarMessages from "@/lib/i18n/messages/studyCalendar";
import studyMessages from "@/lib/i18n/messages/study";

export type Lang = "zh" | "en";
export type Vars = Record<string, string | number>;

const STORAGE_KEY = "ap_lang";

// Dictionary keys are the original Chinese UI strings. Content fetched from
// the API (questions, concepts, options) is never translated here.
const EN: Record<string, string> = {
  ...commonMessages,
  ...landingMessages,
  ...studyMessages,
  ...studyCalendarMessages,
  ...componentMessages,
  ...componentMessages2,
};

type LanguageContextValue = {
  lang: Lang;
  setLanguage: (lang: Lang) => void;
  t: (zh: string, vars?: Vars) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

function detectLanguage(): Lang {
  try {
    return navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en";
  } catch {
    return "en";
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");
  const [pickerOpen, setPickerOpen] = useState(false);

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      // Private mode / blocked storage.
    }
    if (stored === "zh" || stored === "en") {
      setLang(stored);
    } else {
      setLang(detectLanguage());
      setPickerOpen(true);
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  }, [lang]);

  const setLanguage = (next: Lang) => {
    setLang(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage can be unavailable; the in-memory choice still applies.
    }
    setPickerOpen(false);
  };

  const t = (zh: string, vars?: Vars) => {
    const template = lang === "zh" ? zh : (EN[zh] ?? zh);
    if (!vars) return template;
    return template.replace(/\{(\w+)\}/g, (_, key: string) =>
      String(vars[key] ?? `{${key}}`),
    );
  };

  const value = useMemo(() => ({ lang, setLanguage, t }), [lang]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
      {pickerOpen && <LanguagePicker lang={lang} onSelect={setLanguage} />}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const value = useContext(LanguageContext);
  if (!value) {
    throw new Error("useLanguage must be used inside LanguageProvider");
  }
  return value;
}

export function T({ children }: { children: string }) {
  const { t } = useLanguage();
  return <>{t(children)}</>;
}

export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const { lang, setLanguage } = useLanguage();
  return (
    <div
      className={`lang-switch ${className}`.trim()}
      role="group"
      aria-label="Language"
    >
      <button
        type="button"
        data-active={lang === "zh"}
        aria-pressed={lang === "zh"}
        onClick={() => setLanguage("zh")}
      >
        中文
      </button>
      <button
        type="button"
        data-active={lang === "en"}
        aria-pressed={lang === "en"}
        onClick={() => setLanguage("en")}
      >
        EN
      </button>
    </div>
  );
}

function LanguagePicker({
  lang,
  onSelect,
}: {
  lang: Lang;
  onSelect: (lang: Lang) => void;
}) {
  return (
    <div
      className="lang-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Choose your language"
    >
      <div className="lang-modal card card-pad">
        <div className="eyebrow">PsyPrac</div>
        <h2 className="h2 mt-2">Choose your language</h2>
        <p className="muted text-[13px] mt-2">
          选择你使用的语言，之后可以随时在页面右上角切换。
        </p>
        <div className="grid grid-cols-2 gap-2 mt-5">
          <button
            type="button"
            className={`btn ${lang === "zh" ? "btn-primary" : ""}`}
            onClick={() => onSelect("zh")}
          >
            中文
          </button>
          <button
            type="button"
            className={`btn ${lang === "en" ? "btn-primary" : ""}`}
            onClick={() => onSelect("en")}
          >
            English
          </button>
        </div>
      </div>
    </div>
  );
}
