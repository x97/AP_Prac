#!/usr/bin/env python3
"""Shared Excel template and parser for self-authored MCQ questions.

The importer deliberately accepts a small, flat workbook:

    题干 | 选项A | 选项B | 选项C | 选项D | 选项E | 正确答案 | 解析 | 自研编号

Only 题干, 选项A, 选项B and 正确答案 are required. 解析 is optional but
recommended. 自研编号 is optional; when present it is used to recognise the
same question across repeated imports even if its stem is edited.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

SHEET_NAME = "题目"
EXAMPLE_SHEET = "示例"
HELP_SHEET = "填写说明"

HEADERS = [
    "题干",
    "选项A",
    "选项B",
    "选项C",
    "选项D",
    "选项E",
    "正确答案",
    "解析",
    "自研编号",
]

COLUMN_WIDTHS = {
    "题干": 70,
    "选项A": 40,
    "选项B": 40,
    "选项C": 40,
    "选项D": 40,
    "选项E": 40,
    "正确答案": 10,
    "解析": 70,
    "自研编号": 20,
}

HEADER_FILL = PatternFill("solid", fgColor="1F3A68")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=10)
BAND_FILL = PatternFill("solid", fgColor="F5F8FD")
THIN_LINE = Side(style="thin", color="D9DEE8")
BORDER = Border(left=THIN_LINE, right=THIN_LINE, top=THIN_LINE, bottom=THIN_LINE)

MAX_STEM_LENGTH = 20000
MAX_OPTION_LENGTH = 5000
MAX_EXPLANATION_LENGTH = 100000
OPTION_LABELS = ("A", "B", "C", "D", "E")

HEADER_ALIASES = {
    "题干": "stem",
    "题目": "stem",
    "题目内容": "stem",
    "问题": "stem",
    "选项A": "A",
    "选项B": "B",
    "选项C": "C",
    "选项D": "D",
    "选项E": "E",
    "正确答案": "answer",
    "答案": "answer",
    "正确选项": "answer",
    "解析": "explanation",
    "答案解析": "explanation",
    "题目解析": "explanation",
    "自研编号": "code",
    "题目编号": "code",
    "编号": "code",
    "题目ID": "code",
}

REQUIRED_HEADERS = ("stem", "A", "B", "answer")


@dataclass
class ParsedQuestion:
    row_number: int
    stem: str
    options: list[tuple[str, str]]
    answer: str
    explanation: str
    code: str


def normalize_stem(value: str) -> str:
    """Collapse whitespace so a copied stem still matches its previous import."""
    return " ".join(str(value or "").split())


def _header_key(value: Any) -> str:
    return "".join(str(value or "").split()).upper()


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = ILLEGAL_CHARACTERS_RE.sub("", text)
    return text.strip()


def _cell_at(values: list[Any], index: dict[str, int], key: str) -> str:
    position = index.get(key)
    if position is None or position >= len(values):
        return ""
    return _cell_text(values[position])


def _normalise_answer(raw: str, options: list[tuple[str, str]]) -> str | None:
    labels = [label for label, _ in options]
    upper = raw.upper()
    if upper in labels:
        return upper
    match = re.fullmatch(r"([A-E])\s*[.、,，。:：)）]?", upper)
    if match and match.group(1) in labels:
        return match.group(1)
    matches = [label for label, content in options if content == raw]
    if len(matches) == 1:
        return matches[0]
    return None


def read_questions(path: Path) -> tuple[list[ParsedQuestion], list[str], list[str]]:
    """Parse a workbook into question rows.

    Returns ``(questions, errors, warnings)``. Any error means the caller must
    not import the workbook; warnings are safe to ignore.
    """
    errors: list[str] = []
    warnings: list[str] = []
    questions: list[ParsedQuestion] = []

    try:
        workbook = load_workbook(path, data_only=True)
    except Exception as exc:  # noqa: BLE001 - surface any workbook error
        return [], [f"无法读取 Excel 文件：{exc}"], []

    try:
        if SHEET_NAME in workbook.sheetnames:
            sheet = workbook[SHEET_NAME]
        else:
            sheet = workbook.worksheets[0]
            warnings.append(
                f"未找到「{SHEET_NAME}」工作表，已读取第一个工作表「{sheet.title}」"
            )

        header_values = list(
            next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        )
        index: dict[str, int] = {}
        for position, value in enumerate(header_values):
            key = HEADER_ALIASES.get(_header_key(value))
            if not key:
                continue
            if key in index:
                errors.append(f"表头重复：{value}")
                continue
            index[key] = position

        missing = [
            label
            for label, key in zip(
                ("题干", "选项A", "选项B", "正确答案"), REQUIRED_HEADERS
            )
            if key not in index
        ]
        if missing:
            errors.append(f"缺少必填列：{', '.join(missing)}")
            return [], errors, warnings

        seen_codes: dict[str, int] = {}
        seen_stems: dict[str, int] = {}

        for row_number, row in enumerate(
            sheet.iter_rows(min_row=2, values_only=True), start=2
        ):
            values = list(row)
            if not any(_cell_text(value) for value in values):
                continue

            stem = _cell_at(values, index, "stem")
            if not stem:
                errors.append(f"第 {row_number} 行：题干为空")
                continue
            if len(stem) > MAX_STEM_LENGTH:
                errors.append(
                    f"第 {row_number} 行：题干超过 {MAX_STEM_LENGTH} 字"
                )
                continue

            raw_options: list[tuple[str, str]] = []
            last_filled = -1
            for position, label in enumerate(OPTION_LABELS):
                content = _cell_at(values, index, label)
                if content:
                    last_filled = position
                    if len(content) > MAX_OPTION_LENGTH:
                        errors.append(
                            f"第 {row_number} 行：选项{label}超过 "
                            f"{MAX_OPTION_LENGTH} 字"
                        )
                raw_options.append((label, content))

            if last_filled < 0:
                errors.append(f"第 {row_number} 行：没有填写选项")
                continue
            if last_filled < 1:
                errors.append(f"第 {row_number} 行：至少需要选项 A 和 B")
                continue
            gap = next(
                (
                    label
                    for label, content in raw_options[: last_filled + 1]
                    if not content
                ),
                None,
            )
            if gap:
                errors.append(
                    f"第 {row_number} 行：选项必须从 A 开始连续填写，"
                    f"选项{gap}为空"
                )
                continue
            options = raw_options[: last_filled + 1]

            answer_raw = _cell_at(values, index, "answer")
            if not answer_raw:
                errors.append(f"第 {row_number} 行：正确答案为空")
                continue
            answer = _normalise_answer(answer_raw, options)
            if not answer:
                errors.append(
                    f"第 {row_number} 行：正确答案「{answer_raw}」无法识别，"
                    "请填写 A–E 中的一个字母"
                )
                continue

            explanation = _cell_at(values, index, "explanation")
            if len(explanation) > MAX_EXPLANATION_LENGTH:
                errors.append(
                    f"第 {row_number} 行：解析超过 {MAX_EXPLANATION_LENGTH} 字"
                )
                continue
            if not explanation:
                warnings.append(f"第 {row_number} 行：解析为空")

            code = _cell_at(values, index, "code")
            if len(code) > 80:
                errors.append(f"第 {row_number} 行：自研编号超过 80 字")
                continue
            if code:
                if code in seen_codes:
                    errors.append(
                        f"第 {row_number} 行：自研编号「{code}」与第 "
                        f"{seen_codes[code]} 行重复"
                    )
                    continue
                seen_codes[code] = row_number

            stem_key = normalize_stem(stem)
            if stem_key in seen_stems:
                errors.append(
                    f"第 {row_number} 行：题干与第 {seen_stems[stem_key]} 行重复"
                )
                continue
            seen_stems[stem_key] = row_number

            questions.append(
                ParsedQuestion(
                    row_number=row_number,
                    stem=stem,
                    options=options,
                    answer=answer,
                    explanation=explanation,
                    code=code,
                )
            )
    finally:
        workbook.close()

    if not questions and not errors:
        errors.append("工作表里没有题目数据（从第 2 行开始填写）")
    return questions, errors, warnings


def write_template(path: Path) -> None:
    """Write the import template with an empty data sheet and examples."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = SHEET_NAME
    sheet.sheet_properties.tabColor = "2F5BE8"

    sheet.append(HEADERS)
    for index, label in enumerate(HEADERS, start=1):
        cell = sheet.cell(row=1, column=index)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
        sheet.column_dimensions[get_column_letter(index)].width = COLUMN_WIDTHS[label]
    sheet.row_dimensions[1].height = 28
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}51"

    # Light formatting for the first 50 data rows keeps the template usable
    # without turning the whole sheet into a styled block.
    for row_number in range(2, 52):
        sheet.row_dimensions[row_number].height = 48
        for column_number, label in enumerate(HEADERS, start=1):
            cell = sheet.cell(row=row_number, column=column_number)
            cell.border = BORDER
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=label not in ("正确答案", "自研编号"),
            )
            if row_number % 2 == 0:
                cell.fill = BAND_FILL

    answer_column = get_column_letter(HEADERS.index("正确答案") + 1)
    validation = DataValidation(
        type="list",
        formula1='"A,B,C,D,E"',
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="正确答案",
        error="请填写 A–E 中的一个字母",
    )
    sheet.add_data_validation(validation)
    validation.add(f"{answer_column}2:{answer_column}1000")

    example = workbook.create_sheet(EXAMPLE_SHEET)
    example.sheet_properties.tabColor = "B45309"
    example.append(HEADERS)
    for index, label in enumerate(HEADERS, start=1):
        cell = example.cell(row=1, column=index)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
        example.column_dimensions[get_column_letter(index)].width = COLUMN_WIDTHS[label]
    example.freeze_panes = "A2"

    examples = [
        [
            (
                "在经典条件反射中，原本中性的刺激经过与无条件刺激反复配对后，"
                "能够单独引发条件反应。这个原本中性的刺激被称为："
            ),
            "无条件刺激",
            "条件刺激",
            "强化物",
            "消退刺激",
            "",
            "B",
            (
                "中性刺激与无条件刺激反复配对后获得引发反应的能力，成为条件刺激。"
                "无条件刺激本身天然引发反应；强化物和消退属于操作性条件反射术语。"
            ),
            "SAMPLE-001",
        ],
        [
            "根据 Baddeley 的工作记忆模型，负责暂时保持和操作言语信息的成分是：",
            "中央执行系统",
            "语音环路",
            "视空间画板",
            "情景缓冲器",
            "",
            "B",
            (
                "语音环路负责言语和声音信息的短时保持；中央执行系统负责注意控制，"
                "视空间画板处理视觉空间信息，情景缓冲器整合多模态信息。"
            ),
            "SAMPLE-002",
        ],
    ]
    for row_number, values in enumerate(examples, start=2):
        example.append(values)
        for column_number in range(1, len(HEADERS) + 1):
            cell = example.cell(row=row_number, column=column_number)
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        example.row_dimensions[row_number].height = 72

    help_sheet = workbook.create_sheet(HELP_SHEET)
    help_sheet.sheet_properties.tabColor = "6B7280"
    help_sheet.column_dimensions["A"].width = 5
    help_sheet.column_dimensions["B"].width = 100
    help_sheet["B1"] = "自研选择题导入模板"
    help_sheet["B1"].font = Font(size=16, bold=True, color="1F3A68")
    help_sheet.merge_cells("B1:C1")

    instructions = [
        ("1", "只填写「题目」工作表，从第 2 行开始，一行一道题。"),
        ("2", "题干、选项 A、选项 B、正确答案为必填；选项最多到 E，且必须从 A 开始连续填写。"),
        ("3", "正确答案填写一个字母（A–E），必须对应已经填写的选项。"),
        ("4", "解析可留空，但建议填写；导入后会作为题目的答案解析。"),
        (
            "5",
            (
                "自研编号可选但建议填写。同一道题重复导入时请保持编号不变；"
                "修改题干后仍能识别为同一题。不填时按题干内容识别。"
            ),
        ),
        ("6", "不要合并单元格，不要在数据区使用公式。"),
        (
            "7",
            "重复导入会更新已有题目，不会重复创建；从 Excel 中删掉的题目不会自动删除。",
        ),
        (
            "8",
            (
                "导入后在后台「新建课堂作业」→「从题库选择题目」中，"
                "来源选「章节练习」或搜索 -self- 即可看到自研题。"
            ),
        ),
        ("9", "「示例」工作表只是填写示范，不会被导入。"),
    ]
    for row_number, (number, text) in enumerate(instructions, start=3):
        help_sheet.cell(row=row_number, column=1, value=number).font = Font(bold=True)
        cell = help_sheet.cell(row=row_number, column=2, value=text)
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        help_sheet.row_dimensions[row_number].height = 34
    help_sheet.freeze_panes = "A3"

    workbook.properties.title = "自研选择题导入模板"
    workbook.properties.creator = "PsyPrac"

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
