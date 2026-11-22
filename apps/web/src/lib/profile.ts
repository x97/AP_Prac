export const GRADE_VALUES = ["9", "10", "11", "12", "other"] as const;

export function gradeLabel(
  grade: string | null,
  t: (zh: string, vars?: Record<string, string | number>) => string,
) {
  if (!grade) return "—";
  if (grade === "other") return t("其他");
  return t("{grade} 年级", { grade });
}

export function studiedPsychologyLabel(
  value: boolean | null,
  t: (zh: string, vars?: Record<string, string | number>) => string,
) {
  if (value === null || value === undefined) return "—";
  return value ? t("学过") : t("没有学过");
}
