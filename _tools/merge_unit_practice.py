#!/usr/bin/env python3
"""Group or bundle unit-practice papers without copying questions.

The canonical mode is config-driven:

  python3 _tools/merge_unit_practice.py \
    --config config/practice_groups/psychology.json \
    --dry-run

  python3 _tools/merge_unit_practice.py \
    --config config/practice_groups/psychology.json

Rules
-----
- Official question bank (CB) is always ``primary``.
- Textbook chapter practice is always ``supplement``.
- A group with no primary is marked ``needs_review``; supplements are not
  silently promoted.
- A virtual ``practice_bundle`` paper references original questions through
  ``paper_question_map``; questions/options are never copied.
- Duplicate questions are detected by ``question_fingerprint``; the first
  occurrence wins (primary block first).
- The optional concept-layer validation checks that a supplement's dominant
  ``concept_clusters.ap_unit`` matches the group's target unit.

Legacy single-group CLI is kept for compatibility, but new work should use a
config file under ``config/practice_groups/``.
"""
import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from subject_config import load_subject, source_paths

EXAM_DB = ROOT / "data" / "content" / "psychology" / "psychology_exam.db"
KNOWLEDGE_DB = ROOT / "data" / "content" / "psychology" / "psychology_knowledge.db"
REPORT_DIR = ROOT / "data" / "content" / "psychology" / "reports" / "knowledge"

ROLE_RANK = {"primary": 0, "supplement": 1, "old_edition": 2}
VALID_ROLES = set(ROLE_RANK)


class ConfigError(Exception):
    """Invalid config or input; print and stop before writing."""


def die(message):
    raise ConfigError(message)


def norm_text(value):
    value = (value or "").lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fingerprint(stem, options):
    parts = [norm_text(stem)]
    for opt in sorted(options, key=lambda x: x["label"]):
        parts.append(f"{opt['label']}:{norm_text(opt['content'])}")
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()


def normalize_unit_key(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"^unit[\s_-]*", "", text)
    return text


def resolve_path(value, default):
    if not value:
        return Path(default).resolve()
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def subject_defaults(subject_id):
    """Default source paths for a configured subject.

    Falls back to the legacy root paths only when the subject config is
    missing, so old ad-hoc runs still work.
    """
    try:
        return source_paths(load_subject(subject_id))
    except (FileNotFoundError, ValueError):
        return {"exam_db": EXAM_DB, "knowledge_db": KNOWLEDGE_DB}


def column_names(con, table):
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})")}


def ensure_schema(con):
    if "question_fingerprint" not in column_names(con, "questions"):
        con.execute("ALTER TABLE questions ADD COLUMN question_fingerprint TEXT")
    if "bundle_paper_id" not in column_names(con, "practice_groups"):
        con.execute("ALTER TABLE practice_groups ADD COLUMN bundle_paper_id TEXT")
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_questions_fingerprint "
        "ON questions(question_fingerprint)"
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_groups (
            group_id   TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL REFERENCES subjects(subject_id),
            unit_id    TEXT,
            title      TEXT NOT NULL,
            edition    TEXT,
            status     TEXT NOT NULL DEFAULT 'active',
            note       TEXT,
            bundle_paper_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_group_papers (
            group_id   TEXT NOT NULL REFERENCES practice_groups(group_id) ON DELETE CASCADE,
            paper_id   TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            role       TEXT NOT NULL DEFAULT 'supplement',
            note       TEXT,
            PRIMARY KEY (group_id, paper_id)
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_question_map (
            paper_id        TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
            question_id     TEXT NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
            source_paper_id TEXT NOT NULL REFERENCES papers(paper_id),
            section         TEXT,
            number          INTEGER,
            sort_order      INTEGER,
            PRIMARY KEY (paper_id, question_id)
        )
        """
    )
    con.execute(
        "INSERT OR IGNORE INTO paper_types(type_code,name,name_zh) "
        "VALUES ('practice_bundle','Practice bundle','合并练习')"
    )


def load_config(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"config not found: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        die("config root must be an object")
    subject_id = str(data.get("subject_id") or "").strip()
    if not subject_id:
        die("config.subject_id is required")
    groups = data.get("groups")
    if not isinstance(groups, list) or not groups:
        die("config.groups must be a non-empty array")
    seen = set()
    for index, group in enumerate(groups, 1):
        if not isinstance(group, dict):
            die(f"config.groups[{index}] must be an object")
        group_id = str(group.get("group_id") or "").strip()
        if not group_id:
            die(f"config.groups[{index}].group_id is required")
        if group_id in seen:
            die(f"duplicate group_id in config: {group_id}")
        seen.add(group_id)
        for key in ("unit_id", "title", "members"):
            if group.get(key) is None or group.get(key) == "":
                die(f"{group_id}.{key} is required")
        if not isinstance(group["members"], list) or not group["members"]:
            die(f"{group_id}.members must be a non-empty array")
    validation = data.get("validation") or {}
    if not isinstance(validation, dict):
        die("config.validation must be an object")
    if validation.get("on_mismatch", "error") not in ("error", "warn"):
        die("config.validation.on_mismatch must be 'error' or 'warn'")
    return data


def parse_cli_members(values):
    members = []
    for index, raw in enumerate(values):
        raw = (raw or "").strip()
        if not raw:
            continue
        if "=" in raw:
            paper_id, role = raw.rsplit("=", 1)
        else:
            paper_id, role = raw, ("primary" if index == 0 else "supplement")
        members.append(
            {"paper_id": paper_id.strip(), "role": role.strip(), "_order": index}
        )
    if not members:
        die("at least one --member is required")
    return members


def normalize_members(raw_members, allow_multiple_primary=False):
    members = []
    seen_papers = set()
    for index, item in enumerate(raw_members):
        if isinstance(item, str):
            paper_id = item.strip()
            role = ""
        elif isinstance(item, dict):
            paper_id = str(item.get("paper_id") or "").strip()
            role = str(item.get("role") or "").strip()
        else:
            die(f"member #{index + 1} must be a string or object")
        if not paper_id:
            die(f"member #{index + 1} is missing paper_id")
        if paper_id in seen_papers:
            die(f"duplicate member paper_id: {paper_id}")
        seen_papers.add(paper_id)
        if not role:
            role = "primary" if index == 0 else "supplement"
        if role not in VALID_ROLES:
            die(f"bad member role for {paper_id}: {role!r}")
        members.append(
            {
                "paper_id": paper_id,
                "role": role,
                "_order": item.get("_order", index)
                if isinstance(item, dict) else index,
            }
        )
    if not members:
        die("a group must have at least one member")

    primary_count = sum(1 for member in members if member["role"] == "primary")
    if primary_count > 1 and not allow_multiple_primary:
        names = ", ".join(
            member["paper_id"] for member in members
            if member["role"] == "primary"
        )
        die(f"more than one primary member; use separate groups: {names}")

    members.sort(key=lambda member: (ROLE_RANK[member["role"]], member["_order"]))
    for index, member in enumerate(members):
        member["sort_order"] = index
        member.pop("_order", None)
    return members


def load_paper(con, paper_id):
    row = con.execute(
        "SELECT paper_id,paper_type,subject_id,year,title,chinese_title,question_count "
        "FROM papers WHERE paper_id=?",
        (paper_id,),
    ).fetchone()
    if not row:
        die(f"paper not found: {paper_id}")
    return dict(row)


def load_questions(con, paper_id):
    rows = [
        dict(row) for row in con.execute(
            "SELECT question_id,paper_id,section,number,stem,correct_answer "
            "FROM questions WHERE paper_id=? ORDER BY section DESC,number",
            (paper_id,),
        )
    ]
    options = defaultdict(list)
    if rows:
        qids = [row["question_id"] for row in rows]
        marks = ",".join("?" for _ in qids)
        for row in con.execute(
            f"SELECT question_id,label,content FROM options "
            f"WHERE question_id IN ({marks}) ORDER BY sort_order",
            qids,
        ):
            options[row["question_id"]].append(dict(row))
    for row in rows:
        row["options"] = options.get(row["question_id"], [])
        row["fingerprint"] = fingerprint(row["stem"], row["options"])
    return rows


def add_issue(plan, severity, message, paper_id=None):
    plan["issues"].append(
        {"severity": severity, "message": message, "paper_id": paper_id}
    )


def attach_knowledge(con, knowledge_db):
    path = Path(knowledge_db)
    if not path.exists():
        print(f"WARN: knowledge db not found, unit validation skipped: {path}")
        return False
    try:
        con.execute("ATTACH DATABASE ? AS knowledge", (str(path),))
        tables = {
            row[0] for row in con.execute(
                "SELECT name FROM knowledge.sqlite_master "
                "WHERE type='table' AND name IN "
                "('question_concept_links','concept_clusters')"
            )
        }
        if tables != {"question_concept_links", "concept_clusters"}:
            print(f"WARN: knowledge db missing concept tables, unit validation skipped: {path}")
            con.execute("DETACH DATABASE knowledge")
            return False
        return True
    except sqlite3.Error as exc:
        print(f"WARN: cannot attach knowledge db, unit validation skipped: {exc}")
        return False


def unit_signal(con, paper_id):
    rows = con.execute(
        """
        SELECT c.ap_unit AS unit, COUNT(*) AS n
        FROM knowledge.question_concept_links l
        JOIN knowledge.concept_clusters c ON c.cluster_id=l.concept_id
        JOIN questions q ON q.question_id=l.question_id
        WHERE q.paper_id=? AND l.relation_type='core'
        GROUP BY c.ap_unit
        """,
        (paper_id,),
    ).fetchall()
    signal = defaultdict(int)
    for row in rows:
        key = normalize_unit_key(row["unit"])
        if key and key not in {"0", "em"}:
            signal[key] += int(row["n"])
    return dict(signal)


def build_plan(con, group_cfg, subject_id, args,
               allow_multiple_primary=False):
    group_id = str(group_cfg["group_id"]).strip()
    unit_id = str(group_cfg.get("unit_id") or "").strip()
    title = str(group_cfg["title"]).strip()
    members = normalize_members(
        group_cfg["members"], allow_multiple_primary=allow_multiple_primary
    )

    papers = []
    for member in members:
        paper = load_paper(con, member["paper_id"])
        if paper["subject_id"] != subject_id:
            die(
                f"{paper['paper_id']} belongs to {paper['subject_id']}, "
                f"not {subject_id}"
            )
        if paper["paper_type"] != "unit_practice" and not args.allow_any_paper:
            die(
                f"{paper['paper_id']} is {paper['paper_type']}, not unit_practice; "
                "use --allow-any-paper to override"
            )
        papers.append((paper, member["role"], member["sort_order"]))

    bundle_id = str(group_cfg.get("bundle_paper_id") or "").strip() or None
    if bundle_id:
        row = con.execute(
            "SELECT paper_type FROM papers WHERE paper_id=?", (bundle_id,)
        ).fetchone()
        if row and row["paper_type"] != "practice_bundle":
            die(f"bundle paper id exists and is {row['paper_type']}: {bundle_id}")
        if bundle_id in {paper["paper_id"] for paper, _, _ in papers}:
            die(f"bundle paper id cannot also be a member paper: {bundle_id}")

    questions_by_paper = {}
    all_questions = []
    for paper, role, sort_order in papers:
        questions = load_questions(con, paper["paper_id"])
        questions_by_paper[paper["paper_id"]] = questions
        all_questions.extend(questions)

    by_fingerprint = defaultdict(list)
    for question in all_questions:
        by_fingerprint[question["fingerprint"]].append(question)
    duplicates = {
        fp: questions for fp, questions in by_fingerprint.items()
        if len(questions) > 1
    }
    unique_questions = [questions[0] for questions in by_fingerprint.values()]
    paper_order = {
        paper["paper_id"]: sort_order for paper, _role, sort_order in papers
    }
    unique_questions.sort(
        key=lambda question: (
            paper_order.get(question["paper_id"], 999),
            question["section"] or "",
            question["number"] or 0,
        )
    )
    unique_by_paper = Counter(
        question["paper_id"] for question in unique_questions
    )

    plan = {
        "group_id": group_id,
        "subject_id": subject_id,
        "unit_id": unit_id,
        "unit_key": normalize_unit_key(unit_id),
        "curriculum_topics": str(group_cfg.get("curriculum_topics") or "").strip(),
        "title": title,
        "edition": group_cfg.get("edition"),
        "note": group_cfg.get("note"),
        "bundle_paper_id": bundle_id,
        "bundle_title": str(
            group_cfg.get("bundle_title") or title
        ).strip(),
        "bundle_year": group_cfg.get("bundle_year"),
        "members": members,
        "papers": papers,
        "questions_by_paper": questions_by_paper,
        "all_questions": all_questions,
        "unique_questions": unique_questions,
        "unique_by_paper": unique_by_paper,
        "duplicates": duplicates,
        "issues": [],
        "unit_signals": [],
        "cross_group_duplicates": [],
        "status": "active" if any(
            member["role"] == "primary" for member in members
        ) else "needs_review",
    }
    if plan["status"] == "needs_review":
        add_issue(
            plan,
            "warning",
            "no primary paper; group status is needs_review; "
            "do not promote a supplement to primary",
        )
    return plan


def validate_cross_group(plans, allow_shared_members=False,
                         cross_group_policy="warn"):
    if cross_group_policy not in ("warn", "error", "ignore"):
        die("validation.on_cross_group_duplicate must be warn/error/ignore")
    group_ids = set()
    bundle_ids = set()
    paper_owner = {}
    for plan in plans:
        group_id = plan["group_id"]
        if group_id in group_ids:
            add_issue(plan, "error", f"duplicate group_id: {group_id}")
        group_ids.add(group_id)

        bundle_id = plan["bundle_paper_id"]
        if bundle_id:
            if bundle_id in bundle_ids:
                add_issue(plan, "error", f"duplicate bundle_paper_id: {bundle_id}")
            bundle_ids.add(bundle_id)

        for member in plan["members"]:
            paper_id = member["paper_id"]
            owner = paper_owner.get(paper_id)
            if owner and owner != group_id and not allow_shared_members:
                add_issue(
                    plan,
                    "error",
                    f"paper {paper_id} is also used by {owner}; "
                    "one practice paper should belong to one unit",
                    paper_id,
                )
            else:
                paper_owner.setdefault(paper_id, group_id)

    if cross_group_policy == "ignore":
        return
    fingerprint_groups = defaultdict(list)
    for plan in plans:
        for question in plan["unique_questions"]:
            fingerprint_groups[question["fingerprint"]].append((plan, question))
    for fingerprint, entries in fingerprint_groups.items():
        group_ids_for_fp = {plan["group_id"] for plan, _q in entries}
        if len(group_ids_for_fp) < 2:
            continue
        for plan in plans:
            own = [
                q for p, q in entries if p["group_id"] == plan["group_id"]
            ]
            if not own:
                continue
            others = [
                f"{p['group_id']}:{q['question_id']}"
                for p, q in entries if p["group_id"] != plan["group_id"]
            ]
            message = (
                f"cross-unit duplicate fingerprint {fingerprint[:12]}: "
                f"{', '.join(others)}"
            )
            severity = "error" if cross_group_policy == "error" else "warning"
            add_issue(plan, severity, message)
            plan["cross_group_duplicates"].append(
                {
                    "fingerprint": fingerprint,
                    "question_ids": [q["question_id"] for _p, q in entries],
                    "groups": sorted(group_ids_for_fp),
                }
            )


def validate_unit_map(con, plans, validation, knowledge_attached):
    if not knowledge_attached:
        return
    if not validation.get("enabled", True):
        return

    min_links = int(validation.get("min_core_links", 3))
    min_share = float(validation.get("min_dominant_share", 0.5))
    if min_links < 0:
        die("validation.min_core_links must be >= 0")
    if not 0 <= min_share <= 1:
        die("validation.min_dominant_share must be between 0 and 1")
    on_mismatch = validation.get("on_mismatch", "error")
    check_primary = bool(validation.get("check_primary", False))

    for plan in plans:
        target = plan["unit_key"]
        for member in plan["members"]:
            if member["role"] == "primary" and not check_primary:
                continue
            signal = unit_signal(con, member["paper_id"])
            total = sum(signal.values())
            record = {
                "paper_id": member["paper_id"],
                "role": member["role"],
                "target_unit": plan["unit_id"],
                "signal": signal,
                "total": total,
                "dominant_unit": None,
                "share": None,
                "checked": False,
            }
            if total < min_links:
                record["note"] = f"insufficient core links ({total} < {min_links}); skipped"
                plan["unit_signals"].append(record)
                continue
            dominant_unit, dominant_n = max(
                signal.items(), key=lambda item: item[1]
            )
            share = dominant_n / total
            record.update(
                {
                    "dominant_unit": dominant_unit,
                    "share": share,
                    "checked": True,
                }
            )
            plan["unit_signals"].append(record)
            if dominant_unit != target:
                message = (
                    f"{member['paper_id']} dominant concept unit is "
                    f"{dominant_unit} ({dominant_n}/{total}), "
                    f"but group target is {plan['unit_id']}"
                )
                severity = "error" if on_mismatch == "error" else "warning"
                add_issue(plan, severity, message, member["paper_id"])
            elif share < min_share:
                add_issue(
                    plan,
                    "warning",
                    f"{member['paper_id']} dominant unit matches, but only "
                    f"{dominant_n}/{total} ({share:.0%}) core links point to "
                    f"Unit {plan['unit_id']}; review the chapter mapping",
                    member["paper_id"],
                )


def write_plan(con, plan, now):
    con.execute(
        """
        INSERT INTO practice_groups
        (group_id,subject_id,unit_id,title,edition,status,note,bundle_paper_id,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(group_id) DO UPDATE SET
          subject_id=excluded.subject_id,
          unit_id=excluded.unit_id,
          title=excluded.title,
          edition=excluded.edition,
          status=excluded.status,
          note=excluded.note,
          bundle_paper_id=COALESCE(excluded.bundle_paper_id, practice_groups.bundle_paper_id)
        """,
        (
            plan["group_id"],
            plan["subject_id"],
            plan["unit_id"],
            plan["title"],
            plan["edition"],
            plan["status"],
            plan["note"],
            plan["bundle_paper_id"],
            now,
        ),
    )
    con.execute(
        "DELETE FROM practice_group_papers WHERE group_id=?",
        (plan["group_id"],),
    )
    for paper, role, sort_order in plan["papers"]:
        con.execute(
            "INSERT INTO practice_group_papers"
            "(group_id,paper_id,sort_order,role,note) VALUES (?,?,?,?,?)",
            (plan["group_id"], paper["paper_id"], sort_order, role, None),
        )
    for question in plan["all_questions"]:
        con.execute(
            "UPDATE questions SET question_fingerprint=? WHERE question_id=?",
            (question["fingerprint"], question["question_id"]),
        )

    bundle_count = 0
    bundle_id = plan["bundle_paper_id"]
    if bundle_id:
        years = [
            paper["year"] for paper, _role, _order in plan["papers"]
            if paper["year"] is not None
        ]
        year = plan["bundle_year"] or (max(years) if years else datetime.now().year)
        con.execute(
            """
            INSERT INTO papers
            (paper_id,year,title,chinese_title,subject_id,source_pdf,
             question_count,paper_type,source_id)
            VALUES (?,?,?,?,?,?,?,?,NULL)
            ON CONFLICT(paper_id) DO UPDATE SET
              year=excluded.year,
              title=excluded.title,
              chinese_title=excluded.chinese_title,
              subject_id=excluded.subject_id,
              question_count=excluded.question_count,
              paper_type='practice_bundle'
            """,
            (
                bundle_id,
                year,
                plan["bundle_title"],
                plan["bundle_title"],
                plan["subject_id"],
                None,
                len(plan["unique_questions"]),
                "practice_bundle",
            ),
        )
        con.execute(
            "DELETE FROM paper_question_map WHERE paper_id=?", (bundle_id,)
        )
        for index, question in enumerate(plan["unique_questions"], 1):
            con.execute(
                """
                INSERT INTO paper_question_map
                (paper_id,question_id,source_paper_id,section,number,sort_order)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    bundle_id,
                    question["question_id"],
                    question["paper_id"],
                    question["section"],
                    question["number"],
                    index,
                ),
            )
            bundle_count += 1
    plan["bundle_count"] = bundle_count
    return bundle_count


def issue_lines(plan):
    lines = []
    for issue in plan["issues"]:
        prefix = issue["severity"].upper()
        paper = f" `{issue['paper_id']}`" if issue["paper_id"] else ""
        lines.append(f"- **{prefix}**{paper}: {issue['message']}")
    return lines


def write_group_report(plan, path, config_path=None):
    lines = [
        "# 单元练习合并报告",
        "",
        f"- 生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- group_id：`{plan['group_id']}`",
        f"- 标题：{plan['title']}",
        f"- subject_id：`{plan['subject_id']}`",
        f"- unit_id：`{plan['unit_id']}`",
    ]
    if plan["curriculum_topics"]:
        lines.append(f"- 课程标准范围：`{plan['curriculum_topics']}`")
    if config_path:
        lines.append(f"- 配置文件：`{config_path}`")
    lines += [
        f"- 状态：`{plan['status']}`",
        f"- 成员试卷：{len(plan['members'])}",
        f"- 题目总数：{len(plan['all_questions'])}",
        f"- 唯一 fingerprint：{len(plan['unique_questions'])}",
        f"- 重复 fingerprint 组：{len(plan['duplicates'])}",
        f"- bundle：`{plan['bundle_paper_id'] or '—'}`",
        f"- bundle 题目映射：{plan.get('bundle_count', 0)}",
        "",
        "## 成员",
        "",
        "| 顺序 | paper_id | role | 题目数 | 进入 bundle 的唯一题 |",
        "|---:|---|---|---:|---:|",
    ]
    for paper, role, sort_order in plan["papers"]:
        lines.append(
            f"| {sort_order} | `{paper['paper_id']}` | {role} | "
            f"{len(plan['questions_by_paper'][paper['paper_id']])} | "
            f"{plan['unique_by_paper'].get(paper['paper_id'], 0)} |"
        )

    lines += ["", "## Unit 校验", ""]
    if not plan["unit_signals"]:
        lines.append("- 未启用或没有可校验的 supplement。")
    else:
        lines += [
            "| paper_id | 目标 Unit | 主导 Unit | 核心链接占比 | 结果 |",
            "|---|---:|---:|---:|---|",
        ]
        issue_by_paper = {
            issue["paper_id"]: issue["severity"]
            for issue in plan["issues"]
            if issue["paper_id"]
        }
        for record in plan["unit_signals"]:
            if not record["checked"]:
                result = record.get("note", "skipped")
            else:
                result = "OK"
                if issue_by_paper.get(record["paper_id"]) == "error":
                    result = "ERROR"
                elif issue_by_paper.get(record["paper_id"]) == "warning":
                    result = "WARN"
            share = (
                f"{record['share']:.0%}"
                if record["share"] is not None else "—"
            )
            lines.append(
                f"| `{record['paper_id']}` | {record['target_unit']} | "
                f"{record['dominant_unit'] or '—'} | {share} | {result} |"
            )

    lines += ["", "## 校验问题", ""]
    issues = issue_lines(plan)
    lines += issues if issues else ["- 无"]

    lines += ["", "## 重复题", ""]
    if plan["duplicates"]:
        for fp, questions in plan["duplicates"].items():
            names = "；".join(
                f"`{question['question_id']}`" for question in questions
            )
            lines.append(f"- `{fp[:12]}`：{names}")
    else:
        lines.append("- 无")

    lines += ["", "## 跨 Unit 重复题", ""]
    if plan["cross_group_duplicates"]:
        lines += [
            "| fingerprint | 涉及 group | question_id |",
            "|---|---|---|",
        ]
        for dup in plan["cross_group_duplicates"]:
            lines.append(
                f"| `{dup['fingerprint'][:12]}` | "
                f"{', '.join(f'`{g}`' for g in dup['groups'])} | "
                f"{', '.join(f'`{q}`' for q in dup['question_ids'])} |"
            )
    else:
        lines.append("- 无")

    lines += [
        "",
        "## 说明",
        "",
        "- group 模式只建组，不复制题目；原 paper / 题目 / 解析保持不动。",
        "- bundle 模式创建 `practice_bundle` 虚拟卷，`paper_question_map` 引用原题，不复制 `questions` / `options`。",
        "- 重复 fingerprint 只保留第一条进入 bundle；原题仍保留在各自 paper 中。",
        "- 跨 Unit 重复 fingerprint 只报告，不自动删除；归属需要人工确认。",
        "- 排序固定为 `primary → supplement → old_edition`；同一角色内按配置顺序。",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(plans, path, config_path, now):
    total_questions = sum(len(plan["all_questions"]) for plan in plans)
    total_unique = sum(len(plan["unique_questions"]) for plan in plans)
    total_duplicates = sum(len(plan["duplicates"]) for plan in plans)
    total_mapped = sum(plan.get("bundle_count", 0) for plan in plans)
    lines = [
        "# 单元练习合并摘要",
        "",
        f"> 日期：{now}",
        f"> 配置：`{config_path}`",
        "> 策略：官方题库 primary + 教材章节 supplement；虚拟 bundle；fingerprint 去重",
        "",
        "| Group | Unit | 标题 | 成员卷 | 题目数 | 唯一题 | 重复组 | 状态 |",
        "|---|---:|---|---:|---:|---:|---:|---|",
    ]
    for plan in plans:
        lines.append(
            f"| `{plan['group_id']}` | {plan['unit_id']} | {plan['title']} | "
            f"{len(plan['members'])} | {len(plan['all_questions'])} | "
            f"{len(plan['unique_questions'])} | {len(plan['duplicates'])} | "
            f"`{plan['status']}` |"
        )
    lines += [
        f"| **合计** | — | — | **{sum(len(p['members']) for p in plans)}** | "
        f"**{total_questions}** | **{total_unique}** | **{total_duplicates}** | — |",
        "",
        "> `重复组` 是 group 内重复；跨 Unit 重复见下方“跨 Unit 重复题”。",
        "",
        "## Bundle",
        "",
        "| Group | Bundle paper | 题目 |",
        "|---|---|---:|",
    ]
    for plan in plans:
        lines.append(
            f"| `{plan['group_id']}` | `{plan['bundle_paper_id'] or '—'}` | "
            f"{plan.get('bundle_count', 0)} |"
        )

    lines += ["", "## 成员结构", ""]
    for plan in plans:
        members = " → ".join(
            f"`{member['paper_id']}` ({member['role']})"
            for member in plan["members"]
        )
        lines.append(f"- Unit {plan['unit_id']}：{members}")

    lines += ["", "## 校验", ""]
    errors = [
        (plan, issue) for plan in plans for issue in plan["issues"]
        if issue["severity"] == "error"
    ]
    warnings = [
        (plan, issue) for plan in plans for issue in plan["issues"]
        if issue["severity"] == "warning"
    ]
    if not errors and not warnings:
        lines.append("- 全部通过。")
    for plan, issue in errors + warnings:
        paper = f" `{issue['paper_id']}`" if issue["paper_id"] else ""
        lines.append(
            f"- **{issue['severity'].upper()}** `{plan['group_id']}`{paper}: "
            f"{issue['message']}"
        )

    cross = {}
    for plan in plans:
        for dup in plan["cross_group_duplicates"]:
            cross.setdefault(dup["fingerprint"], dup)
    lines += ["", "## 跨 Unit 重复题", ""]
    if cross:
        lines += [
            "| fingerprint | 涉及 group | question_id |",
            "|---|---|---|",
        ]
        for fingerprint, dup in sorted(cross.items()):
            lines.append(
                f"| `{fingerprint[:12]}` | "
                f"{', '.join(f'`{g}`' for g in dup['groups'])} | "
                f"{', '.join(f'`{q}`' for q in dup['question_ids'])} |"
            )
    else:
        lines.append("- 无")

    lines += [
        "",
        "## 数据表",
        "",
        f"- `practice_groups`：{len(plans)} 条",
        f"- `practice_group_papers`：{sum(len(p['members']) for p in plans)} 条",
        f"- `paper_question_map`：{total_mapped} 条（{len(plans)} 个 bundle）",
        f"- `questions.question_fingerprint`：{total_questions} 条已填充",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_plan(plan):
    print(
        f"group={plan['group_id']} unit={plan['unit_id']} "
        f"status={plan['status']} members={len(plan['members'])} "
        f"questions={len(plan['all_questions'])} "
        f"unique={len(plan['unique_questions'])} "
        f"duplicate_groups={len(plan['duplicates'])}"
    )
    for member in plan["members"]:
        print(
            f"  {member['sort_order']}: {member['paper_id']} "
            f"role={member['role']} "
            f"questions={len(plan['questions_by_paper'][member['paper_id']])} "
            f"unique_in_bundle={plan['unique_by_paper'].get(member['paper_id'], 0)}"
        )
    for issue in plan["issues"]:
        paper = f" {issue['paper_id']}" if issue["paper_id"] else ""
        print(f"  {issue['severity'].upper()}{paper}: {issue['message']}")


def legacy_group(args):
    if not args.group_id:
        die("--group-id is required without --config")
    if not args.title:
        die("--title is required without --config")
    return {
        "group_id": args.group_id,
        "unit_id": args.unit_id,
        "title": args.title,
        "edition": args.edition,
        "note": args.note,
        "bundle_paper_id": args.bundle_paper_id,
        "bundle_title": args.bundle_title,
        "bundle_year": args.bundle_year,
        "members": parse_cli_members(args.member),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None,
                        help="JSON file under config/practice_groups/")
    parser.add_argument("--group-id", default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--subject-id", default=None)
    parser.add_argument("--unit-id", default=None)
    parser.add_argument("--edition", default=None)
    parser.add_argument("--note", default=None)
    parser.add_argument("--member", action="append", default=[],
                        help="legacy: paper_id[=primary|supplement|old_edition]")
    parser.add_argument("--bundle-paper-id", default=None)
    parser.add_argument("--bundle-title", default=None)
    parser.add_argument("--bundle-year", type=int, default=None)
    parser.add_argument("--allow-any-paper", action="store_true")
    parser.add_argument("--db", default=None)
    parser.add_argument("--knowledge-db", default=None)
    parser.add_argument("--report", default=None,
                        help="legacy single-group report path")
    parser.add_argument("--report-dir", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    config = None
    config_path = None
    if args.config:
        if args.member:
            die("--member cannot be combined with --config")
        if args.report:
            die("--report is only for legacy single-group mode; use --report-dir")
        config = load_config(args.config)
        config_path = args.config
        subject_id = str(config["subject_id"])
        db_path = resolve_path(
            args.db or config.get("exam_db"), EXAM_DB
        )
        knowledge_db = resolve_path(
            args.knowledge_db or config.get("knowledge_db"), KNOWLEDGE_DB
        )
        report_dir = resolve_path(
            args.report_dir or config.get("report_dir"), REPORT_DIR
        )
        groups = list(config["groups"])
        if args.group_id:
            groups = [
                group for group in groups
                if group["group_id"] == args.group_id
            ]
            if not groups:
                die(f"group_id not found in config: {args.group_id}")
        validation = config.get("validation") or {}
        allow_multiple_primary = bool(
            config.get("allow_multiple_primary", False)
        )
        allow_shared_members = bool(
            config.get("allow_shared_members", False)
        )
        cross_group_policy = validation.get(
            "on_cross_group_duplicate", "warn"
        )
    else:
        subject_id = args.subject_id or "psychology"
        defaults = subject_defaults(subject_id)
        db_path = resolve_path(args.db, defaults["exam_db"])
        knowledge_db = resolve_path(args.knowledge_db, defaults["knowledge_db"])
        report_dir = resolve_path(args.report_dir, REPORT_DIR)
        groups = [legacy_group(args)]
        validation = {"enabled": False}
        allow_multiple_primary = False
        allow_shared_members = False
        cross_group_policy = "ignore"

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    knowledge_attached = attach_knowledge(con, knowledge_db)

    plans = []
    try:
        for group_cfg in groups:
            plans.append(
                build_plan(
                    con, group_cfg, subject_id, args,
                    allow_multiple_primary=allow_multiple_primary,
                )
            )
        validate_cross_group(
            plans, allow_shared_members, cross_group_policy
        )
        validate_unit_map(con, plans, validation, knowledge_attached)
    except ConfigError as exc:
        print(f"ERROR: {exc}")
        con.close()
        return 2

    for plan in plans:
        print_plan(plan)

    errors = [
        (plan, issue) for plan in plans for issue in plan["issues"]
        if issue["severity"] == "error"
    ]
    if args.dry_run:
        print(
            f"dry-run: groups={len(plans)} "
            f"errors={len(errors)} "
            f"warnings={sum(1 for p in plans for i in p['issues'] if i['severity'] == 'warning')}"
        )
        con.close()
        return 1 if errors else 0
    if errors:
        print("VALIDATION FAILED: no database changes written")
        con.close()
        return 1

    if not args.no_backup:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = Path(db_path).with_name(
            Path(db_path).name + f".bak-{stamp}-before-practice-merge"
        )
        shutil.copy2(db_path, backup)
        print("backup:", backup)

    ensure_schema(con)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        with con:
            for plan in plans:
                write_plan(con, plan, now)
    except Exception:
        con.rollback()
        raise

    for plan in plans:
        if args.report:
            report_path = Path(args.report)
        else:
            report_path = report_dir / f"practice_merge_{plan['group_id']}.md"
        write_group_report(plan, report_path, config_path)

    if config and not args.group_id:
        write_summary(
            plans, report_dir / "practice_merge_summary.md",
            config_path, now,
        )

    print(
        f"written: groups={len(plans)} "
        f"members={sum(len(p['members']) for p in plans)} "
        f"bundle_questions={sum(p.get('bundle_count', 0) for p in plans)}"
    )
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = con.execute("PRAGMA foreign_key_check").fetchall()
    print(
        "integrity:", integrity,
        "foreign_key_check:", "OK" if not foreign_keys else foreign_keys[:3],
    )
    con.close()
    return 0 if integrity == "ok" and not foreign_keys else 1


if __name__ == "__main__":
    raise SystemExit(main())
