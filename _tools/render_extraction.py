#!/usr/bin/env python3
"""Render the validated 102-section extraction JSON files into Markdown."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTIONS = os.path.join(ROOT, "data", "content", "psychology", "extraction", "sections", "sections_text.json")
EXTRACT_DIR = os.path.join(ROOT, "data", "content", "psychology", "extraction")
OUT_MD = os.path.join(ROOT, "data", "content", "psychology", "reports", "kp", "知识点抽取_102节.md")
OUT_JSON = os.path.join(ROOT, "data", "content", "psychology", "reports", "kp", "知识点抽取_102节.json")

HAN = re.compile(r"[一-鿿]")
UNIT_NAMES = {
    0: "Science Practices",
    1: "Biological Bases of Behavior",
    2: "Cognition",
    3: "Development and Learning",
    4: "Social Psychology, Personality, Motivation, and Emotion",
    5: "Mental and Physical Health",
}
UNIT_PAGES = {0: 29, 1: 61, 2: 133, 3: 203, 4: 267, 5: 336}
CHAP_PAGES = {
    1: 30, 2: 35, 3: 49, 4: 62, 5: 96, 6: 114, 7: 134, 8: 152,
    9: 164, 10: 186, 11: 204, 12: 237, 13: 268, 14: 300, 15: 314,
    16: 337, 17: 350, 18: 377,
}


def load_extractions():
    data = {}
    for unit in range(6):
        path = os.path.join(EXTRACT_DIR, f"unit{unit}.json")
        if not os.path.exists(path):
            continue
        obj = json.load(open(path, encoding="utf-8"))
        for sec in obj.get("sections", []):
            data[(sec["chapter"], sec["section"])] = sec
    return data


def main():
    master = json.load(open(SECTIONS, encoding="utf-8"))
    extracted = load_extractions()
    merged = []
    lines = []
    lines.append("# AP Psychology Premium 2027 · 102 节知识点抽取")
    lines.append("")
    lines.append("> **来源**：`assets/psychology/books/AP Psychology Premium, 2027 - Allyson J. Weseley & Robert McEntarffer.pdf`")
    lines.append("> **粒度**：目录小节（Unit 0–5 / Chapter 1–18），共 102 个知识点块。")
    lines.append("> **页码**：PDF 文件页序，不是书内印刷页码。")
    lines.append("> **标题**：每个知识点块的标题逐字引用教材小节标题；概念名保留教材原文。")
    lines.append("> **字段**：原文定义（教材原句）、关键实验/研究者、≤20 字通俗解释。")
    lines.append("")
    lines.append("**阅读说明**")
    lines.append("")
    lines.append("- 每个 `####` 标题就是一个知识点块，标题逐字取自教材目录小节。")
    lines.append("- 块内加粗的概念名（如 `**Humanist Perspective**`）是该小节下的知识条目，不是独立块。")
    lines.append("- 原文定义使用教材本节原句；个别小节教材没有独立定义句，则取该节最接近定义的原文句子。")
    lines.append("- “关键实验/研究者”只填本节明确提到的人名或实验；没有则写“本节未提及”。")
    lines.append("- 已执行最终去重：拆分 7 组“一句定义两个概念”的共享定义；全库完全重复的核心定义 **0 组**。")
    lines.append("- 去重明细见 `data/content/psychology/reports/kp/知识点去重报告.md`。")
    lines.append("")
    lines.append("## 统计")
    lines.append("")
    lines.append("| 项目 | 数量 |")
    lines.append("|---|---:|")
    total_kps = 0
    for unit in range(6):
        secs = [s for s in master if s["unit"] == unit]
        kps = sum(len(extracted.get((s["chapter"], s["section"]), {}).get("knowledge_points", [])) for s in secs)
        total_kps += kps
        lines.append(f"| Unit {unit} | {len(secs)} 节 / {kps} 条 |")
    lines.append(f"| **合计** | **{len(master)} 节 / {total_kps} 条** |")
    lines.append("")
    lines.append("---")
    lines.append("")

    current_unit = None
    current_chapter = None
    block_no = 0
    for sec in master:
        unit = sec["unit"]
        chap = sec["chapter"]
        key = (chap, sec["section"])
        item = extracted.get(key)
        if unit != current_unit:
            current_unit = unit
            lines.append(f"## Unit {unit}: {UNIT_NAMES[unit]}")
            lines.append("")
            lines.append(f"`PDF p.{UNIT_PAGES[unit]}`")
            lines.append("")
            current_chapter = None
        if chap != current_chapter:
            current_chapter = chap
            lines.append(f"### Chapter {chap}: {sec['chapter_title']}")
            lines.append("")
            lines.append(f"`PDF p.{CHAP_PAGES[chap]}`")
            lines.append("")
        block_no += 1
        lines.append(f"#### {sec['section']}")
        lines.append("")
        meta = f"`PDF p.{sec['page']} · 块 {block_no}/102"
        if sec["subs"]:
            meta += f" · {len(sec['subs'])} 个正文子标题"
        meta += "`"
        lines.append(meta)
        lines.append("")
        if not item:
            lines.append("> ⚠️ 本节尚未抽取。")
            lines.append("")
            continue
        kps = item.get("knowledge_points") or []
        if not kps:
            lines.append("> ⚠️ 本节没有知识点条目。")
            lines.append("")
            continue
        for kp in kps:
            name = kp.get("name", "").strip()
            lines.append(f"**{name}**")
            lines.append("")
            lines.append(f"- **原文定义**：“{kp.get('definition_quote','').strip()}”")
            lines.append(f"- **关键实验/研究者**：{kp.get('researchers','').strip()}")
            plain = kp.get("plain", "").strip()
            han = len(HAN.findall(plain))
            lines.append(f"- **通俗解释**：{plain}（{han}字）")
            lines.append("")
        merged.append({
            "unit": unit,
            "chapter": chap,
            "chapter_title": sec["chapter_title"],
            "section": sec["section"],
            "page": sec["page"],
            "knowledge_points": kps,
        })
    lines.append("---")
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- 原文定义均为教材本节原句，未改写；引号内为逐字引用。")
    lines.append("- “关键实验/研究者”只填本节明确提到的人名或实验；没有则写“本节未提及”。")
    lines.append("- 通俗解释为中文自查用语，控制在 20 个汉字以内。")
    lines.append("- 题号/练习题/Key Terms/Learning Objectives/TIP/图表标题不作为知识点块。")
    lines.append("")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"sections": merged}, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {OUT_MD}: {len(merged)} sections, {total_kps} knowledge points")
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
