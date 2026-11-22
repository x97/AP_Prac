export const GRADE_VALUES = ["9", "10", "11", "12", "other"] as const;

export const STUDY_MODE_VALUES = ["school", "tutoring", "self", "not_yet"] as const;

export const EXAM_TIME_VALUES = ["2027", "2028", "undecided"] as const;

const STUDY_MODE_LABELS: Record<string, string> = {
  school: "学校教授",
  tutoring: "机构辅导",
  self: "自学",
  not_yet: "还未学习",
};

export function gradeLabel(
  grade: string | null,
  t: (zh: string, vars?: Record<string, string | number>) => string,
) {
  if (!grade) return "—";
  if (grade === "other") return t("其他");
  return t("{grade} 年级", { grade });
}

export function studyModeLabel(
  value: string | null,
  t: (zh: string, vars?: Record<string, string | number>) => string,
) {
  if (!value) return "—";
  return STUDY_MODE_LABELS[value] ? t(STUDY_MODE_LABELS[value]) : value;
}

export function examTimeLabel(
  value: string | null,
  t: (zh: string, vars?: Record<string, string | number>) => string,
) {
  if (!value) return "—";
  if (value === "undecided") return t("观望中");
  return value;
}

export function studiedPsychologyLabel(
  value: boolean | null,
  t: (zh: string, vars?: Record<string, string | number>) => string,
) {
  if (value === null || value === undefined) return "—";
  return value ? t("学过") : t("没有学过");
}
