export type ThemeAccentId =
  | "blue"
  | "ocean"
  | "teal"
  | "forest"
  | "mint"
  | "amber"
  | "sunset"
  | "crimson"
  | "sakura"
  | "violet"
  | "indigo"
  | "graphite";

export type ThemeAccent = {
  id: ThemeAccentId;
  label: string;
  tone: string;
  color: string;
  soft: string;
};

export const THEME_STORAGE_KEY = "ap-theme-accent";

export const THEME_ACCENTS: ThemeAccent[] = [
  { id: "blue", label: "经典蓝", tone: "Classic blue", color: "#2f5be8", soft: "#edf1ff" },
  { id: "ocean", label: "海盐蓝", tone: "Ocean blue", color: "#0369a1", soft: "#e8f5fd" },
  { id: "teal", label: "青碧", tone: "Teal", color: "#0f766e", soft: "#e6f7f4" },
  { id: "forest", label: "森林绿", tone: "Forest green", color: "#177245", soft: "#e8f5ee" },
  { id: "mint", label: "薄荷绿", tone: "Mint", color: "#0f8a5f", soft: "#e7f8f0" },
  { id: "amber", label: "琥珀金", tone: "Amber", color: "#a16207", soft: "#fff8e1" },
  { id: "sunset", label: "日落橙", tone: "Sunset orange", color: "#b45309", soft: "#fdf1e3" },
  { id: "crimson", label: "赤红", tone: "Crimson", color: "#b42318", soft: "#fdecec" },
  { id: "sakura", label: "樱花粉", tone: "Sakura pink", color: "#c2416b", soft: "#fdecf3" },
  { id: "violet", label: "紫罗兰", tone: "Violet", color: "#6d4aff", soft: "#f1edff" },
  { id: "indigo", label: "靛蓝", tone: "Indigo", color: "#4338ca", soft: "#ecebff" },
  { id: "graphite", label: "石墨灰", tone: "Graphite", color: "#475569", soft: "#eef2f6" },
];

// Old theme IDs are kept as aliases so an already-saved browser preference
// does not silently reset to blue after this palette was renamed.
const LEGACY_THEME_ALIASES: Record<string, ThemeAccentId> = {
  psychology: "violet",
  biology: "forest",
  chemistry: "sunset",
  physics: "teal",
  calculus: "crimson",
  statistics: "indigo",
};

export const THEME_IDS = THEME_ACCENTS.map((theme) => theme.id);
export const THEME_STORED_IDS = [...THEME_IDS, ...Object.keys(LEGACY_THEME_ALIASES)];

export function normalizeThemeAccent(value: string | null): ThemeAccentId | null {
  if (!value) return null;
  if (THEME_IDS.includes(value as ThemeAccentId)) return value as ThemeAccentId;
  return LEGACY_THEME_ALIASES[value] || null;
}

export function isThemeAccent(value: string | null): value is ThemeAccentId {
  return normalizeThemeAccent(value) !== null;
}

export function readStoredTheme(): ThemeAccentId {
  if (typeof window === "undefined") return "blue";
  try {
    const normalized = normalizeThemeAccent(window.localStorage.getItem(THEME_STORAGE_KEY));
    return normalized || "blue";
  } catch {
    return "blue";
  }
}

export function applyThemeAccent(id: ThemeAccentId) {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.accent = id;
}
