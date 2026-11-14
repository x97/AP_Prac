"use client";

import {
  BookOpen,
  Loader2,
  NotebookPen,
  Save,
  Search,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ConceptTags } from "@/components/ConceptTags";
import { Modal } from "@/components/Modal";
import { QuestionSourceLine } from "@/components/QuestionSourceLine";
import { QuestionView } from "@/components/QuestionView";
import { apiDelete, apiGet, apiPatch } from "@/lib/api";
import type { Feedback, Note } from "@/lib/types";

export default function NotesPage() {
  const [items, setItems] = useState<Note[] | null>(null);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [openNote, setOpenNote] = useState<Note | null>(null);
  const [detail, setDetail] = useState<Feedback | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [noteDraft, setNoteDraft] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [noteSaved, setNoteSaved] = useState(false);
  const [noteError, setNoteError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Note[]>("/me/notes?limit=200")
      .then(setItems)
      .catch((e: Error) => setError(e.message));
  }, []);

  const filtered = useMemo(() => {
    if (!items) return null;
    const term = q.trim().toLowerCase();
    if (!term) return items;
    return items.filter(
      (n) =>
        n.content.toLowerCase().includes(term) ||
        (n.question?.stem || "").toLowerCase().includes(term),
    );
  }, [items, q]);

  async function remove(id: string) {
    if (!window.confirm("删除这条笔记？删除后无法恢复。")) return;
    try {
      await apiDelete(`/me/notes/${id}`);
      setItems((prev) => (prev ? prev.filter((n) => n.id !== id) : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete note");
    }
  }

  async function openQuestion(note: Note) {
    if (!note.question) return;
    setOpenNote(note);
    setNoteDraft(note.content);
    setNoteSaved(false);
    setNoteError(null);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const data = await apiGet<Feedback>(
        `/me/questions/${note.question.question_id}`,
      );
      setDetail(data);
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : "Failed to load question");
    } finally {
      setDetailLoading(false);
    }
  }

  function closeQuestion() {
    setOpenNote(null);
    setDetail(null);
    setDetailError(null);
    setNoteSaved(false);
    setNoteError(null);
  }

  async function saveOpenNote() {
    if (!openNote || savingNote) return;
    setSavingNote(true);
    setNoteError(null);
    try {
      const updated = await apiPatch<{
        id: string;
        content: string;
        updated_at: string;
      }>(`/me/notes/${openNote.id}`, { content: noteDraft });
      setItems((prev) =>
        prev
          ? prev.map((item) =>
              item.id === openNote.id
                ? {
                    ...item,
                    content: updated.content,
                    updated_at: updated.updated_at,
                  }
                : item,
            )
          : prev,
      );
      setOpenNote((prev) =>
        prev
          ? {
              ...prev,
              content: updated.content,
              updated_at: updated.updated_at,
            }
          : prev,
      );
      setNoteSaved(true);
    } catch (e) {
      setNoteError(e instanceof Error ? e.message : "Failed to save note");
    } finally {
      setSavingNote(false);
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">Notebook</div>
          <h1 className="h1">Notebook</h1>
          <p className="muted text-[13px] mt-2">
            View all question notes here, and open the original question and explanation directly.
          </p>
        </div>
      </div>

      <div className="relative mb-4 max-w-md">
        <Search
          size={15}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
        />
        <input
          className="input pl-9"
          placeholder="Search notes or question text…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {error && <div className="feedback feedback-bad mb-4">{error}</div>}
      {!filtered && <div className="skeleton h-56 w-full" />}
      {filtered && filtered.length === 0 && (
        <div className="card empty">
          <NotebookPen size={26} className="mx-auto mb-2 text-[var(--faint)]" />
          No notes yet. Write one under a question in practice and it will appear here.
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {filtered?.map((note) => (
          <div key={note.id} className="card card-pad flex flex-col">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="badge">
                  {note.question ? `Q${note.question.display_number}` : note.target_type}
                </span>
                <div className="text-[11px] faint mt-1">
                  {new Date(note.updated_at).toLocaleString("zh-CN")}
                </div>
                <QuestionSourceLine
                  question={note.question}
                  className="text-[11px] muted mt-1.5 max-w-[300px] leading-4"
                />
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => remove(note.id)}
                title="Delete note"
              >
                <Trash2 size={14} />
              </button>
            </div>
            {note.question?.stem && (
              <div className="mt-2 text-[12px] muted line-clamp-2" lang="en">
                {note.question.stem}
              </div>
            )}
            <div className="mt-3 text-[14px] whitespace-pre-wrap leading-6">
              {note.content}
            </div>
            {note.question && (
              <div className="mt-auto pt-3 flex justify-end">
                <button
                  className="btn btn-sm btn-ghost"
                  onClick={() => openQuestion(note)}
                >
                  <BookOpen size={13} /> View Question, Answer & Explanation
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <Modal
        open={Boolean(openNote)}
        onClose={closeQuestion}
        title={
          openNote?.question
            ? `Question Review · Q${openNote.question.display_number}`
            : "Question Review"
        }
        wide
      >
        {detailLoading && (
          <div className="skeleton h-64 w-full" />
        )}
        {detailError && (
          <div className="feedback feedback-bad text-[13px]">{detailError}</div>
        )}
        {detail && (
          <>
            <QuestionSourceLine
              question={openNote?.question}
              className="text-[11.5px] muted mb-2 leading-4"
            />
            {detail.concepts && detail.concepts.length > 0 && (
              <div className="card card-pad mb-3">
                <div className="text-[11px] faint mb-2">
                  Related Concepts (click for details)
                </div>
                <ConceptTags concepts={detail.concepts} limit={12} />
              </div>
            )}
            <QuestionView
              question={{
                ...detail,
                answered_at: new Date().toISOString(),
                selected_label: null,
                is_correct: false,
                feedback: detail,
              }}
              onSelect={() => undefined}
              disabled
              resultLabel="Question Review"
              resultTone="neutral"
            />
          </>
        )}
        {!detailLoading && !detail && !detailError && (
          <div className="empty py-6 text-[12px]">
            <Loader2 size={16} className="animate-spin mx-auto" />
          </div>
        )}
        {openNote && (
          <div className="card card-pad mt-3">
            <div className="flex items-center justify-between gap-2">
              <div className="text-[11px] faint">My Notes (editable)</div>
              {noteSaved && (
                <span className="text-[11px] text-[var(--success)]">Saved</span>
              )}
            </div>
            <textarea
              className="input mt-2 min-h-[140px] resize-y leading-6"
              value={noteDraft}
              onChange={(event) => {
                setNoteDraft(event.target.value);
                setNoteSaved(false);
              }}
              maxLength={20000}
              placeholder="Note the tricky part, key terms, or your own understanding…"
            />
            {noteError && (
              <div className="feedback feedback-bad mt-2 text-[12px]">
                {noteError}
              </div>
            )}
            <div className="mt-2 flex items-center justify-between gap-2">
              <span className="text-[10.5px] faint">
                {noteDraft.length} / 20000
              </span>
              <button
                className="btn btn-primary btn-sm"
                onClick={saveOpenNote}
                disabled={
                  savingNote ||
                  !openNote ||
                  noteDraft === openNote.content
                }
              >
                {savingNote ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Save size={13} />
                )}
                Save Note
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
