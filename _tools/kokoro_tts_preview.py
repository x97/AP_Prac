#!/usr/bin/env python3
"""Generate a small Kokoro TTS preview deck for flashcard terms.

This is a local audition tool, not the production audio pipeline. It writes
WAV files plus an HTML page with one audio player per term.

Usage:
    python3 _tools/kokoro_tts_preview.py \
      --model /tmp/kokoro_models/kokoro-v1.0.onnx \
      --voices /tmp/kokoro_models/voices-v1.0.bin

The input JSON is data/content/psychology/reports/tts_preview/terms.json.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TERMS = ROOT / "data/content/psychology/reports/tts_preview/terms.json"
DEFAULT_OUT = ROOT / "data/content/psychology/reports/tts_preview"
VOICE_COMPARISON = ["af_heart", "af_bella", "am_michael", "bf_emma"]


def slug(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "term"


def write_wav(path: Path, samples: np.ndarray, sample_rate: int) -> float:
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak > 0:
        samples = samples / peak * 0.9
    sf.write(path, samples, sample_rate, subtype="PCM_16")
    return len(samples) / sample_rate


def render(kokoro: Kokoro, text: str, voice: str, speed: float) -> tuple[np.ndarray, int]:
    samples, sample_rate = kokoro.create(
        text,
        voice=voice,
        speed=speed,
        lang="en-us",
    )
    return np.asarray(samples), int(sample_rate)


def build_html(out_dir: Path, items: list[dict[str, Any]], voices: list[dict[str, Any]]) -> None:
    cards = "\n".join(
        f'''
        <article class="card">
          <div class="num">{index:02d}</div>
          <div class="body">
            <div class="term" lang="en">{html.escape(item["term"])}</div>
            <div class="meta">概念权重 {item["weight"]:.2f} · {item["duration"]:.2f} 秒 · {item["size_kb"]} KB</div>
            <audio controls preload="metadata" src="{html.escape(item["file"])}"></audio>
          </div>
        </article>'''
        for index, item in enumerate(items, start=1)
    )
    voice_cards = "\n".join(
        f'''
        <article class="card voice-card">
          <div class="body">
            <div class="term" lang="en">{html.escape(item["term"])}</div>
            <div class="meta">voice: {html.escape(item["voice"])} · {item["duration"]:.2f} 秒 · {item["size_kb"]} KB</div>
            <audio controls preload="metadata" src="{html.escape(item["file"])}"></audio>
          </div>
        </article>'''
        for item in voices
    )
    page = f'''<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kokoro 发音试听</title>
  <style>
    :root {{
      --bg: #f6f4ef;
      --surface: #ffffff;
      --ink: #1c1f24;
      --muted: #6b7280;
      --line: #e5e1d8;
      --primary: #2f5be8;
      --primary-soft: #edf1ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px 18px 56px;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.5 ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 980px; margin: 0 auto; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; letter-spacing: -0.02em; }}
    .sub {{ margin: 0 0 22px; color: var(--muted); }}
    .note {{
      margin: 0 0 22px; padding: 12px 14px; border: 1px solid var(--line);
      background: var(--surface); border-radius: 12px; color: var(--muted);
    }}
    h2 {{ margin: 30px 0 10px; font-size: 14px; text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }}
    .card {{
      display: flex; gap: 10px; padding: 12px; background: var(--surface);
      border: 1px solid var(--line); border-radius: 14px;
    }}
    .num {{
      display: grid; place-items: center; width: 28px; height: 28px; flex: 0 0 auto;
      border-radius: 8px; background: var(--primary-soft); color: var(--primary);
      font: 700 11px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
    }}
    .body {{ min-width: 0; flex: 1; }}
    .term {{ font-weight: 650; overflow-wrap: anywhere; }}
    .meta {{ margin-top: 2px; color: var(--muted); font-size: 11.5px; }}
    audio {{ width: 100%; height: 34px; margin-top: 8px; }}
    .voice-card {{ border-color: color-mix(in srgb, var(--primary) 35%, var(--line)); }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #101216; --surface: #171a1f; --ink: #e9e7e1; --muted: #9aa1ac;
        --line: #2a2e36; --primary: #7c9bff; --primary-soft: #1b2544;
      }}
    }}
  </style>
</head>
<body>
<main>
  <h1>Kokoro 发音试听</h1>
  <p class="sub">30 个高频 AP Psychology 术语 · voice <code>af_heart</code> · speed 0.9</p>
  <p class="note">这些是本地 Kokoro-82M 生成的 WAV 试听文件。页面里还有一个 4 音色对比区，用来确认是否换音色。</p>
  <div class="grid">{cards}</div>
  <h2>音色对比 · Operant conditioning</h2>
  <div class="grid">{voice_cards}</div>
</main>
</body>
</html>
'''
    (out_dir / "index.html").write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--voices", required=True, type=Path)
    parser.add_argument("--terms", type=Path, default=DEFAULT_TERMS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--speed", type=float, default=0.9)
    args = parser.parse_args()

    terms = json.loads(args.terms.read_text(encoding="utf-8"))
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro(str(args.model), str(args.voices))

    items: list[dict[str, Any]] = []
    for index, item in enumerate(terms, start=1):
        term = str(item["term"])
        filename = f"{index:02d}-{slug(term)}.wav"
        samples, sample_rate = render(kokoro, term, args.voice, args.speed)
        duration = write_wav(out_dir / filename, samples, sample_rate)
        size_kb = max(1, round((out_dir / filename).stat().st_size / 1024))
        items.append(
            {
                "term": term,
                "weight": float(item.get("weight") or 0),
                "file": filename,
                "voice": args.voice,
                "duration": duration,
                "size_kb": size_kb,
                "sample_rate": sample_rate,
            }
        )
        print(f"{index:02d}/{len(terms)} {term} -> {filename} ({duration:.2f}s)")

    voice_items: list[dict[str, Any]] = []
    for voice in VOICE_COMPARISON:
        filename = f"voice-{voice}-operant-conditioning.wav"
        samples, sample_rate = render(kokoro, "Operant conditioning", voice, args.speed)
        duration = write_wav(out_dir / filename, samples, sample_rate)
        size_kb = max(1, round((out_dir / filename).stat().st_size / 1024))
        voice_items.append(
            {
                "term": "Operant conditioning",
                "file": filename,
                "voice": voice,
                "duration": duration,
                "size_kb": size_kb,
                "sample_rate": sample_rate,
            }
        )
        print(f"voice {voice} -> {filename} ({duration:.2f}s)")

    manifest = {
        "engine": "kokoro-onnx",
        "model": args.model.name,
        "voice": args.voice,
        "speed": args.speed,
        "terms": items,
        "voice_comparison": voice_items,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    build_html(out_dir, items, voice_items)
    print(f"preview: {out_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
