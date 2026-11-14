"use client";

import { AlertCircle, ArrowRight, BookOpen, Layers, LockKeyhole } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { PracticeGroup } from "@/lib/types";

export default function PracticePage() {
  const [groups, setGroups] = useState<PracticeGroup[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadGroups = useCallback(() => {
    apiGet<PracticeGroup[]>("/practice-groups")
      .then(setGroups)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">Unit practice</div>
          <h1 className="h1">Practice by Unit</h1>
          <p className="muted text-[13px] mt-2">
            Choose a Unit, then a chapter. Answers are checked instantly with concepts on the right.
          </p>
        </div>
        <span className="pill">
          <Layers size={13} /> 5 Units
        </span>
      </div>

      <Link
        href="/wrong"
        className="card card-pad mb-4 flex items-center justify-between gap-4"
      >
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-[var(--danger-soft)] text-[var(--danger)]">
            <AlertCircle size={18} />
          </span>
          <div>
            <div className="font-semibold text-[14px]">Wrong Practice Paper</div>
            <div className="text-[12px] muted mt-0.5">
              A separate wrong-question paper. It includes unmastered and reviewing questions and updates with your wrong book.
            </div>
          </div>
        </div>
        <ArrowRight size={16} className="text-[var(--danger)] shrink-0" />
      </Link>

      {error && <div className="feedback feedback-bad">{error}</div>}
      {!groups && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="card card-pad h-44 skeleton" />
          ))}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {groups?.map((g) => {
          const progress = g.total ? Math.round((g.answered / g.total) * 100) : 0;
          const inner = (
            <>
              <div className="flex items-center justify-between gap-3">
                <span className={g.locked ? "pill pill-locked" : "pill pill-primary"}>
                  {g.locked && <LockKeyhole size={11} />} Unit {g.unit_id}
                </span>
                {g.locked ? (
                  <LockKeyhole size={18} className="text-[var(--danger)]" strokeWidth={2.2} />
                ) : (
                  <BookOpen size={16} className="text-[var(--muted)]" />
                )}
              </div>
              <h2 className="h2 mt-4" lang="en">
                {g.title_en || g.title}
              </h2>
              <div className="mt-1 text-[12px] muted">
                {g.topic_count} topics · {g.question_count} practice questions
              </div>
              <div className="mt-5 flex items-center justify-between text-[12px] muted">
                <span>
                  {g.answered}/{g.total} answered
                </span>
                <span>{g.accuracy === null ? "—" : `${Math.round(g.accuracy * 100)}%`}</span>
              </div>
              <div className="progress mt-2">
                <i style={{ width: `${progress}%` }} />
              </div>
              <div className="mt-4 flex items-center justify-between">
                <span className={g.locked ? "text-[12px] text-[var(--muted)]" : "text-[12px] text-[var(--primary)] font-medium"}>
                  {g.locked ? "View chapters" : "Enter Unit"}
                </span>
                {g.locked ? (
                  <LockKeyhole size={15} className="text-[var(--danger)]" />
                ) : (
                  <ArrowRight size={15} className="text-[var(--primary)]" />
                )}
              </div>
            </>
          );
          return (
            <Link key={g.group_id} href={`/practice/${g.group_id}`} className="card unit-card">
              {inner}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
