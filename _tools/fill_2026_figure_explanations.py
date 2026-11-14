#!/usr/bin/env python3
"""Fill AI explanations for the 2026 figure/table MCQs.

The bulk generator intentionally skipped question-level figures because the
chart data are not in the text context. These 12 explanations were written
against the cropped figures and their printed descriptions, then checked for
the verified answer. Only options.ai_explanation is written.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/content/psychology/psychology_exam.db"
PAPER_ID = "psychology-ap-2026"
EXPORT = ROOT / "data/content/psychology/extraction/ai_explanations_psychology-ap-2026.json"
REPORT = ROOT / "data/content/psychology/reports/ai_explanation_2026_figures.md"

EXPLANATIONS = {
    9: (
        "Regression toward the mean occurs when extreme scores on an initial measurement tend to move closer to the average on a retest, partly because of random variation. Figure 2 shows the retest distribution shifted toward the middle of the score range rather than preserving Figure 1's extreme pattern. Mental set, bimodal distribution, and self-fulfilling prophecy do not describe this shift toward the mean."
    ),
    18: (
        "Dr. Salvatore's hypothesis was that working on a superordinate goal would improve attitudes toward the rival group. The AHS students' mean attitude rose from 2.3 before the mural to 8.5 afterward, supporting the hypothesis; the BHS students' mean stayed essentially unchanged, from 3.1 to 3.0, so their data do not. Therefore only the AHS data support the prediction."
    ),
    31: (
        "The scatterplot shows that patients who attended longer hypnosis sessions generally reported lower anxiety ratings afterward. As session length increases from left to right, the data points trend downward, which is a negative correlation. The pattern does not indicate no relationship or a positive relationship, and the graph alone does not establish statistical significance or causation."
    ),
    46: (
        "Growth mindset scores were positively associated with academic behaviors: students with higher mindset scores tended to have higher grades, more study time, and more feedback-seeking. Graph D shows a scatterplot with 15 points rising from left to right, which matches that positive relationship. Graph C shows no clear pattern, while A and B are bar graphs that do not depict a correlation between two continuous variables."
    ),
    53: (
        "Random assignment took place, but the groups differed substantially in age: Group 1's mean age was 32 and Group 2's was 55. Age could affect how quickly participants learn to use a new technology, so it provides an alternative explanation for the group difference in completion time. Gender percentages were similar, time of day was held constant, and reading ability was not measured as a group difference."
    ),
    60: (
        "An operational definition specifies how a variable is measured in the study. Here, the effect of opioid addiction was measured as participants' ratings of withdrawal-symptom severity on a 0-to-10 scale at 24, 48, and 96 hours after stopping opioids. That rating is the concrete, quantifiable measure used in the study, whereas time, years addicted, and quantity consumed are not the outcome actually measured."
    ),
    61: (
        "Range is the difference between the highest and lowest observed values. In the table, the withdrawal-symptom ratings range from 0 to 8 across the three rating periods, so the range is 8. The scale's maximum of 10 and the 96-hour time period are not the observed range."
    ),
    62: (
        "A Likert scale asks respondents to rate a statement or experience along an ordered scale. Participants rated withdrawal-symptom severity from 0 to 10, which is a Likert-type rating scale. A structured interview is a data-collection procedure, while a correlation coefficient and an effect size are statistics, not measurement tools."
    ),
    66: (
        "Positive psychology focuses on factors that improve well-being, not merely on treating disorder. The dashed curve is shifted to the right, with its peak in the Moderate Mental Health range, indicating that the intervention population has more people in higher well-being categories. That supports the interpretation that the interventions are associated with improved well-being; the graph alone does not establish causation or a specific effect size."
    ),
    72: (
        "Researchers randomly assigned participants to one of two conditions and manipulated whether other recipients' email addresses were visible. They then measured how many participants offered to help. Random assignment plus manipulation of an independent variable and measurement of a dependent variable define an experiment. Case studies, naturalistic observation, and meta-analysis do not involve this controlled manipulation."
    ),
    73: (
        "The dependent variable is the outcome the researchers measured: whether participants offered help, recorded as the number of participants who offered to help. The visibility of email addresses was the independent variable manipulated across the two conditions. Whether someone replied to the recruitment email describes eligibility, and the classmate is part of the scenario rather than the measured outcome."
    ),
    74: (
        "Diffusion of responsibility occurs when the presence of other people reduces each person's sense of responsibility to help. When the email showed 20 other recipients, only 12 participants offered help; when no other addresses were visible, 18 offered help. That difference fits diffusion of responsibility, whereas memory cues, framing, and the just-world phenomenon do not explain the effect of perceived others."
    ),
}


def backup() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = DB.with_name(f"{DB.name}.bak-{stamp}-ai-figures-2026")
    shutil.copy2(DB, target)
    return target


def main() -> int:
    backup_path = backup()
    print(f"backup: {backup_path}")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        for number, explanation in EXPLANATIONS.items():
            qid = f"psychology-2026-mcq-{number:03d}"
            row = conn.execute(
                "SELECT correct_answer FROM questions WHERE question_id=? AND paper_id=?",
                (qid, PAPER_ID),
            ).fetchone()
            if not row or not row["correct_answer"]:
                raise ValueError(f"missing question/answer: {qid}")
            cur = conn.execute(
                "UPDATE options SET ai_explanation=? WHERE question_id=? AND label=?",
                (explanation, qid, row["correct_answer"]),
            )
            if cur.rowcount != 1:
                raise ValueError(f"expected one correct option for {qid}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Rebuild the export with all 75 explanations, including the 12 manual ones.
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT q.number, q.question_id, q.correct_answer, o.content, o.ai_explanation
        FROM questions q
        JOIN options o ON o.question_id=q.question_id AND o.label=q.correct_answer
        WHERE q.paper_id=? AND q.section='MCQ'
        ORDER BY q.number
        """,
        (PAPER_ID,),
    ).fetchall()
    wrong = conn.execute(
        """
        SELECT COUNT(*) FROM options o JOIN questions q ON q.question_id=o.question_id
        WHERE q.paper_id=? AND o.is_correct=0
          AND o.ai_explanation IS NOT NULL AND trim(o.ai_explanation)<>''
        """,
        (PAPER_ID,),
    ).fetchone()[0]
    missing = [r["number"] for r in rows if not (r["ai_explanation"] or "").strip()]
    if missing:
        raise ValueError(f"missing AI explanations: {missing}")
    if wrong:
        raise ValueError(f"AI explanations on {wrong} wrong options")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("foreign_key_check failed")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("integrity_check failed")

    items = []
    for row in rows:
        items.append(
            {
                "question_id": row["question_id"],
                "paper_id": PAPER_ID,
                "number": row["number"],
                "answer_label": row["correct_answer"],
                "answer_content": row["content"],
                "explanation": row["ai_explanation"],
                "has_figure": row["number"] in EXPLANATIONS,
                "source": "manual_figure_review" if row["number"] in EXPLANATIONS else "ai_batch",
            }
        )
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": "deepseek-flash[1m] + manual figure review",
        "language": "en",
        "papers": [PAPER_ID],
        "count": len(items),
        "items": items,
    }
    EXPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "\n".join(
            [
                "# 2026 MCQ AI 解析补全记录",
                "",
                f"- 范围：`{PAPER_ID}`",
                f"- 总覆盖：{len(items)}/75",
                "- 批量生成：63 道非图题（deepseek-flash[1m]）",
                "- 读图补写：12 道（Q9、Q18、Q31、Q46、Q53、Q60、Q61、Q62、Q66、Q72、Q73、Q74）",
                "- 只写入正确选项的 `options.ai_explanation`；`options.explanation` 未改动。",
                "- 备份：" + f"`{backup_path.relative_to(ROOT)}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    conn.close()
    print(f"wrote {EXPORT}")
    print(f"wrote {REPORT}")
    print(f"coverage: {len(items)}/75; wrong-option AI: {wrong}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
