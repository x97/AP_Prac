"use client";

import { Clock3, FileText, FlaskConical, LockKeyhole } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { Paper } from "@/lib/types";

function formatLabel(p: Paper) {
  if (p.format_code === "legacy_100") return "Legacy 100 Q";
  if (p.format_code === "2025_75") return "New 75 Q";
  return "Full Exam";
}

function PaperCard({ paper, showFree = false }: { paper: Paper; showFree?: boolean }) {
  const inner = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="eyebrow">
            {paper.paper_type === "real_exam" ? "Real Exam" : "Mock Exam"} · {paper.year}
          </div>
          <h2 className="font-semibold mt-1.5 leading-6">
            {paper.title || paper.paper_id}
          </h2>
        </div>
        {paper.locked ? (
          <span className="pill pill-locked">
            <LockKeyhole size={12} /> Locked
          </span>
        ) : (
          <span className="pill pill-primary">{formatLabel(paper)}</span>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-[12px] muted">
        <span className="flex items-center gap-1.5">
          <FileText size={13} /> {paper.mcq_count ?? 0} MCQ
        </span>
        <span className="flex items-center gap-1.5">
          <Clock3 size={13} /> {paper.mcq_minutes ?? 0} min
        </span>
        <span className="flex items-center gap-1.5">
          <FlaskConical size={13} /> {paper.frq_count ?? 0} FRQ
        </span>
        <span className="flex items-center gap-1.5">
          <Clock3 size={13} /> {paper.frq_minutes ?? 0} min
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {showFree && !paper.locked && <span className="badge badge-core">Free</span>}
        {paper.frq_forms.length > 0 && (
          <span className="badge">FRQ {paper.frq_forms.join(" / ")}</span>
        )}
        {paper.modes.includes("full") && <span className="badge">Mixed</span>}
        {paper.frq_warning && <span className="badge badge-confusable">{paper.frq_warning}</span>}
      </div>
    </>
  );
  return (
    <Link href={`/exams/${paper.paper_id}`} className="card unit-card">
      {inner}
    </Link>
  );
}

export default function ExamsPage() {
  const [papers, setPapers] = useState<Paper[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPapers = useCallback(() => {
    apiGet<Paper[]>("/papers")
      .then(setPapers)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    loadPapers();
  }, [loadPapers]);

  const hasLocked = Boolean(papers?.some((p) => p.locked));
  const free = hasLocked ? papers?.filter((p) => !p.locked) || [] : [];
  const real =
    papers?.filter(
      (p) => p.paper_type === "real_exam" && (!hasLocked || p.locked),
    ) || [];
  const mock =
    papers?.filter(
      (p) => p.paper_type === "mock_exam" && (!hasLocked || p.locked),
    ) || [];

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">Exams</div>
          <h1 className="h1">Exams</h1>
          <p className="muted text-[13px] mt-2">
            Timed like the real AP exam. Review after submission; FRQ uses rubric self-grading.
          </p>
        </div>
      </div>

      {error && <div className="feedback feedback-bad">{error}</div>}
      {!papers && (
        <div className="grid gap-3 md:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card card-pad h-48 skeleton" />
          ))}
        </div>
      )}

      {free.length > 0 && (
        <>
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="h2">Free Access</h2>
              <p className="mt-1 text-[12px] muted">
                Open without an activation code. Start here to try the full exam flow.
              </p>
            </div>
            <span className="pill pill-warn">No code needed</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {free.map((p) => (
              <PaperCard key={p.paper_id} paper={p} showFree />
            ))}
          </div>
        </>
      )}

      {real.length > 0 && (
        <>
          <h2 className={`h2 mb-3 ${free.length > 0 ? "mt-8" : ""}`}>Past Papers</h2>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {real.map((p) => (
              <PaperCard key={p.paper_id} paper={p} />
            ))}
          </div>
        </>
      )}

      {mock.length > 0 && (
        <>
          <h2 className="h2 mt-8 mb-3">Mock Exams</h2>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {mock.map((p) => (
              <PaperCard key={p.paper_id} paper={p} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
