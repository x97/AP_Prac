import type { QuestionSourceInfo } from "@/lib/types";

const SECTION_LABEL: Record<string, string> = {
  MCQ: "Section I · MCQ",
  FRQ: "Section II · FRQ",
};

export function questionSourceParts(
  question?: QuestionSourceInfo | null,
): { primary: string; secondary: string } {
  if (!question) return { primary: "", secondary: "" };
  const isExam =
    question.paper_type === "real_exam" || question.paper_type === "mock_exam";
  const paper = question.paper_title || question.paper_title_en || "";
  const section = question.section
    ? SECTION_LABEL[question.section] || question.section
    : "";

  if (isExam) {
    return {
      primary: paper || "真题 / 模拟",
      secondary: section,
    };
  }

  const unitChapter = [
    question.unit_id ? `Unit ${question.unit_id}` : "",
    [question.topic_code, question.topic_title_en].filter(Boolean).join(" "),
  ]
    .filter(Boolean)
    .join(" · ");

  if (unitChapter) {
    return { primary: unitChapter, secondary: paper };
  }
  return { primary: paper, secondary: section };
}

export function questionSourceLabel(
  question?: QuestionSourceInfo | null,
): string {
  const parts = questionSourceParts(question);
  return [parts.primary, parts.secondary].filter(Boolean).join(" · ");
}
