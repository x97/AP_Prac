#!/usr/bin/env python3
"""Generate 1–10 word English study glosses for Myers glossary KPs."""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import link_question_kps as linker  # noqa: E402

DEFAULT_JSON = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_glossary.json")
DEFAULT_CSV = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_glossary.csv")


def word_count(text):
    return len(re.findall(r"[A-Za-z0-9']+", text or ""))


def parse_array(text):
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < start:
        raise ValueError("no JSON array in response")
    payload = raw[start:end + 1]
    payload = re.sub(r",\s*([}\]])", r"\1", payload)
    return json.loads(payload, strict=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=DEFAULT_JSON)
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--model", default="deepseek-flash[1m]")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    with open(args.json, encoding="utf-8") as handle:
        entries = json.load(handle)
    todo = [entry for entry in entries if not entry.get("plain_en")]
    if args.limit:
        todo = todo[:args.limit]
    print(f"entries={len(entries)} missing_plain={len(todo)}")
    if not todo:
        return 0

    system = (
        "You write concise AP Psychology study glosses. For each term, "
        "write a plain-English explanation of 1 to 10 words. Do not copy "
        "the definition verbatim, do not add facts, and do not use Chinese. "
        "Return only a JSON array."
    )
    failures = []
    for start in range(0, len(todo), args.batch_size):
        batch = todo[start:start + args.batch_size]
        lines = []
        for index, entry in enumerate(batch, 1):
            sense = f" [{entry['sense']}]" if entry.get("sense") else ""
            lines.append(
                f"{index}. {entry['term']}{sense}: {entry['definition'][:320]}"
            )
        prompt = (
            "Write one gloss per item. Return exactly:\n"
            '[{"i":1,"plain":"..."}]\n\n' + "\n".join(lines)
        )
        print(f"batch {start // args.batch_size + 1}: {len(batch)} terms", flush=True)
        try:
            text, usage = linker.call_api(
                system, prompt, args.model, 4000, args.timeout, 2
            )
            data = parse_array(text)
        except Exception as error:
            print("  ERROR", error, flush=True)
            failures.extend(entry["term"] for entry in batch)
            continue
        by_index = {}
        for row in data:
            try:
                by_index[int(row.get("i"))] = str(row.get("plain") or "").strip()
            except (TypeError, ValueError):
                continue
        for index, entry in enumerate(batch, 1):
            plain = by_index.get(index, "")
            if not plain or word_count(plain) < 1 or word_count(plain) > 10:
                failures.append(entry["term"])
                continue
            entry["plain_en"] = plain
            entry["plain_word_count"] = word_count(plain)
            entry["status"] = "approved"
        # Keep the JSON durable after each batch.
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(entries, handle, ensure_ascii=False, indent=2)
        print(f"  saved; failures so far={len(failures)}", flush=True)
        time.sleep(0.3)

    with open(args.json, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, ensure_ascii=False, indent=2)
    with open(args.csv, "w", encoding="utf-8-sig", newline="") as handle:
        import csv
        writer = csv.DictWriter(handle, fieldnames=[
            "term", "sense", "definition", "units", "unit", "module_code",
            "module_title", "section_id", "mapping_method",
            "mapping_confidence", "source_page", "body_page", "plain_en",
        ])
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "term": entry["term"],
                "sense": entry.get("sense") or "",
                "definition": entry["definition"],
                "units": ",".join(entry.get("units") or []),
                "unit": entry.get("unit") or "",
                "module_code": entry.get("module_code") or "",
                "module_title": entry.get("module_title") or "",
                "section_id": entry.get("section_id") or "",
                "mapping_method": entry.get("mapping_method") or "",
                "mapping_confidence": entry.get("mapping_confidence") or "",
                "source_page": entry.get("source_page") or "",
                "body_page": entry.get("body_page") or "",
                "plain_en": entry.get("plain_en") or "",
            })
    print("failures:", len(failures), failures[:20])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
