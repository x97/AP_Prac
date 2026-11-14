#!/usr/bin/env python3
"""Final dedupe pass for the 102-section extraction.

1. Split the seven sentences that define a pair of concepts, so no two
   knowledge-point entries share an identical core definition.
2. Report cross-block same-name concepts; do not delete different senses
   or legitimate cross-chapter recaps.
3. Write a human-readable dedupe report and a CSV of repeated names.
"""
import csv
import json
import os
import re
import shutil
import unicodedata
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACT = os.path.join(ROOT, "data", "content", "psychology", "extraction")
SECTIONS = os.path.join(ROOT, "data", "content", "psychology", "extraction", "sections", "sections_text.json")
REPORT = os.path.join(ROOT, "data", "content", "psychology", "reports", "kp", "知识点去重报告.md")
REPEAT_CSV = os.path.join(ROOT, "data", "content", "psychology", "reports", "kp", "知识点同概念复现.csv")

# (chapter, section, concept name) -> concept-specific quote
SPLITS = {
    (7, "Principles of Visual Perception", "monocular depth cues"):
        "monocular depth cues (depth cues that do not depend on having two eyes)",
    (7, "Principles of Visual Perception", "binocular depth cues"):
        "binocular depth cues (cues that depend on having two eyes)",
    (9, "Sensory Memory", "iconic memory"):
        "less than a second for visual information (iconic memory)",
    (9, "Sensory Memory", "echoic memory"):
        "three to four seconds for auditory information (echoic memory)",
    (10, "Types of Tests", "aptitude tests"):
        "Aptitude tests measure ability or potential",
    (10, "Types of Tests", "achievement tests"):
        "achievement tests measure what one has learned or accomplished",
    (12, "Classical Conditioning", "Conditioned stimulus (CS)"):
        "the bell is no longer a neutral stimulus but, rather, a conditioned stimulus (CS)",
    (12, "Classical Conditioning", "Conditioned response (CR)"):
        "the bell elicits salivation, which is now a conditioned response (CR)",
    (12, "Operant Conditioning", "Positive punishment"):
        "positive punishment (usually referred to simply as punishment), which is the addition of something unpleasant",
    (12, "Operant Conditioning", "Omission training"):
        "omission training or negative punishment, which is the removal of something pleasant",
    (13, "The Psychology of Social Situations", "Upward social comparison"):
        "Upward social comparison is when we compare ourselves to people doing better than we are",
    (13, "The Psychology of Social Situations", "Downward social comparison"):
        "downward social comparison is when we compare ourselves to people doing worse than we are",
    (17, "Categories of Disorders", "positive symptoms"):
        "Positive symptoms refer to excesses in behavior, thought, or mood such as neologisms and hallucinations",
    (17, "Categories of Disorders", "negative symptoms"):
        "negative symptoms correspond to deficits such as flat affect or catatonic stupor",
}

HOMONYMS = {
    "accommodation": "视觉调节（晶状体变焦） vs 皮亚杰认知顺应",
    "autonomy": "埃里克森自主 vs 自我决定理论的自主",
    "discrimination": "经典条件作用的辨别 vs 社会偏见中的歧视行为",
    "opponent-process theory": "颜色视觉对立过程理论 vs 动机对立过程理论",
    "proximity": "格式塔邻近原则 vs 人际吸引的接近性",
    "resistance": "压力反应的抵抗阶段 vs 心理治疗中的阻抗",
    "similarity": "格式塔相似原则 vs 人际吸引的相似性",
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = text.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", text).strip()


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def load_units():
    units = {}
    for unit in range(6):
        path = os.path.join(EXTRACT, f"unit{unit}.json")
        units[unit] = json.load(open(path, encoding="utf-8"))
    return units


def main():
    sections = {(s["chapter"], s["section"]): s for s in json.load(open(SECTIONS, encoding="utf-8"))}
    raw_dir = os.path.join(EXTRACT, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    for unit in range(6):
        src = os.path.join(EXTRACT, f"unit{unit}.json")
        dst = os.path.join(raw_dir, f"unit{unit}.json")
        if not os.path.exists(dst):
            shutil.copy2(src, dst)

    units = load_units()
    applied = []
    failures = []
    for unit, data in units.items():
        for sec in data["sections"]:
            key = (sec["chapter"], sec["section"])
            src_text = sections[key]["text"]
            for kp in sec["knowledge_points"]:
                split_key = (sec["chapter"], sec["section"], kp["name"])
                if split_key in SPLITS:
                    new_quote = SPLITS[split_key]
                    if squash(new_quote) not in squash(src_text):
                        failures.append((split_key, new_quote))
                    else:
                        kp["definition_quote"] = new_quote
                        applied.append(split_key)

    if failures:
        print("FAILED splits (not applied):")
        for f in failures:
            print(" ", f)
        return 1

    for unit, data in units.items():
        json.dump(data, open(os.path.join(EXTRACT, f"unit{unit}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    # Flatten
    items = []
    for unit in range(6):
        data = units[unit]
        for sec in data["sections"]:
            for i, kp in enumerate(sec["knowledge_points"], 1):
                items.append({
                    "unit": unit,
                    "chapter": sec["chapter"],
                    "section": sec["section"],
                    "page": sec["page"],
                    "kp_index": i,
                    "name": kp["name"],
                    "nname": norm(kp["name"]),
                    "quote": kp["definition_quote"],
                    "nquote": norm(kp["definition_quote"]),
                    "plain": kp["plain"],
                })

    by_quote = defaultdict(list)
    for item in items:
        by_quote[item["nquote"]].append(item)
    exact_groups = [(q, g) for q, g in by_quote.items() if len(g) > 1]

    by_name = defaultdict(list)
    for item in items:
        by_name[item["nname"]].append(item)
    repeat_groups = []
    for name, group in sorted(by_name.items()):
        if len({(x["chapter"], x["section"]) for x in group}) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                import difflib
                ratio = difflib.SequenceMatcher(None, a["nquote"], b["nquote"]).ratio()
                if a["nquote"] == b["nquote"]:
                    kind = "exact_duplicate"
                elif ratio >= 0.85:
                    kind = "near_duplicate"
                elif name in HOMONYMS:
                    kind = "homonym"
                else:
                    kind = "same_name_different_definition"
                repeat_groups.append({
                    "concept": a["name"],
                    "a_block": f"Ch{a['chapter']} / {a['section']}",
                    "a_quote": a["quote"],
                    "b_block": f"Ch{b['chapter']} / {b['section']}",
                    "b_quote": b["quote"],
                    "similarity": round(ratio, 3),
                    "classification": kind,
                    "note": HOMONYMS.get(name, ""),
                })

    lines = []
    lines.append("# 知识点去重报告")
    lines.append("")
    lines.append("## 去重规则")
    lines.append("")
    lines.append("1. **完全重复的核心定义**：同一句原文同时定义两个概念时，拆成各自的概念定义，避免两条记录共用同一句定义。")
    lines.append("2. **同名但不同义**：如同一个词在不同章节表示不同概念（如 `accommodation` 视觉调节 vs 皮亚杰顺应），保留两条。")
    lines.append("3. **同名同概念、跨章复现**：教材在不同章节重复出现时，保留两条；它们通常承担不同语境或复习功能，不按名称删除。")
    lines.append("4. **近似但不同的定义**：只有定义文字高度接近（相似度 ≥ 0.85）时标记为 `near_duplicate`，供人工复核。")
    lines.append("")
    lines.append("## 本次处理")
    lines.append("")
    lines.append(f"- 拆分共享定义：**{len(applied)} 条**（7 组 × 2 个概念）。")
    lines.append("- 拆分后全库完全重复的定义组：**%d 组**。" % len(exact_groups))
    lines.append(f"- 跨块同名概念对（含同章复现）：**{len(repeat_groups)} 组**；其中 `near_duplicate` **{sum(1 for x in repeat_groups if x['classification']=='near_duplicate')} 组**，`exact_duplicate` **{sum(1 for x in repeat_groups if x['classification']=='exact_duplicate')} 组**。")
    lines.append("")
    lines.append("### 已拆分的 7 组共享定义")
    lines.append("")
    lines.append("| Chapter / Section | 概念 A | 概念 B |")
    lines.append("|---|---|---|")
    split_groups = [
        (7, "Principles of Visual Perception", "monocular depth cues", "binocular depth cues"),
        (9, "Sensory Memory", "iconic memory", "echoic memory"),
        (10, "Types of Tests", "aptitude tests", "achievement tests"),
        (12, "Classical Conditioning", "Conditioned stimulus (CS)", "Conditioned response (CR)"),
        (12, "Operant Conditioning", "Positive punishment", "Omission training"),
        (13, "The Psychology of Social Situations", "Upward social comparison", "Downward social comparison"),
        (17, "Categories of Disorders", "positive symptoms", "negative symptoms"),
    ]
    for ch, sec, a, b in split_groups:
        lines.append(f"| Ch{ch} / {sec} | {a} | {b} |")
    lines.append("")
    lines.append("### 跨块同名概念（含同章复现；保留，不按名称删除）")
    lines.append("")
    lines.append("| 概念 | 位置 A | 位置 B | 相似度 | 类型 |")
    lines.append("|---|---|---|---:|---|")
    for row in repeat_groups:
        lines.append(f"| {row['concept']} | {row['a_block']} | {row['b_block']} | {row['similarity']} | `{row['classification']}` |")
    lines.append("")
    lines.append("> 说明：`same_name_different_definition` 和 `homonym` 不是重复知识点，不应删除；`near_duplicate` 是文字高度接近的跨章复现，建议人工确认是否保留。")
    lines.append("")
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))

    with open(REPEAT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["concept", "a_block", "a_quote", "b_block", "b_quote", "similarity", "classification", "note"])
        w.writeheader()
        w.writerows(repeat_groups)

    print(f"applied splits: {len(applied)}")
    print(f"exact duplicate groups after split: {len(exact_groups)}")
    print(f"repeat pairs: {len(repeat_groups)}")
    print(f"wrote {REPORT}")
    print(f"wrote {REPEAT_CSV}")
    return 0 if not exact_groups else 1


if __name__ == "__main__":
    raise SystemExit(main())
