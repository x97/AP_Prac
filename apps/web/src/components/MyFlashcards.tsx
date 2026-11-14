"use client";

import {
  AlertTriangle,
  ArrowLeft,
  Loader2,
  Pencil,
  Play,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { FlashcardStudy } from "@/components/FlashcardStudy";
import { Modal } from "@/components/Modal";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { UserFlashcard, UserFlashcardList } from "@/lib/types";

type CardForm = {
  term: string;
  short_meaning: string;
  detail_meaning: string;
};

const EMPTY_FORM: CardForm = {
  term: "",
  short_meaning: "",
  detail_meaning: "",
};

function cardStatus(card: UserFlashcard) {
  if (card.seen_count === 0) return "新卡";
  if (card.next_due_at && new Date(card.next_due_at).getTime() <= Date.now()) {
    return "到期";
  }
  return `第 ${card.box} 盒`;
}

export function MyFlashcards() {
  const [data, setData] = useState<UserFlashcardList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [studying, setStudying] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<UserFlashcard | null>(null);
  const [form, setForm] = useState<CardForm>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<UserFlashcard | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await apiGet<UserFlashcardList>("/flashcards/custom"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载卡片失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openNew() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setFormOpen(true);
  }

  function openEdit(card: UserFlashcard) {
    setEditing(card);
    setForm({
      term: card.term,
      short_meaning: card.short_meaning,
      detail_meaning: card.detail_meaning,
    });
    setFormError(null);
    setFormOpen(true);
  }

  function closeForm() {
    if (saving) return;
    setFormOpen(false);
    setFormError(null);
  }

  async function saveCard(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const term = form.term.trim();
    const shortMeaning = form.short_meaning.trim();
    if (!term || !shortMeaning) {
      setFormError("术语和简短含义不能为空。");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const payload = {
        term,
        short_meaning: shortMeaning,
        detail_meaning: form.detail_meaning.trim(),
      };
      if (editing) {
        await apiPatch<UserFlashcard>(`/flashcards/custom/${editing.id}`, payload);
      } else {
        await apiPost<UserFlashcard>("/flashcards/custom", payload);
      }
      await load();
      setFormOpen(false);
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "保存卡片失败");
    } finally {
      setSaving(false);
    }
  }

  async function deleteCard() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await apiDelete(`/flashcards/custom/${deleteTarget.id}`);
      setData((prev) =>
        prev
          ? {
              ...prev,
              cards: prev.cards.filter((card) => card.id !== deleteTarget.id),
              total: Math.max(0, prev.total - 1),
            }
          : prev,
      );
      setDeleteTarget(null);
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : "删除卡片失败");
    } finally {
      setDeleting(false);
    }
  }

  if (studying) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between gap-2 mb-3">
          <button
            className="btn btn-sm btn-ghost -ml-2"
            onClick={() => {
              setStudying(false);
              void load();
            }}
          >
            <ArrowLeft size={14} /> 我的卡片
          </button>
          <span className="pill">个人卡组</span>
        </div>
        <FlashcardStudy custom continuous limit={20} showAllLink={false} />
      </div>
    );
  }

  const total = data?.total ?? 0;
  const limit = data?.limit ?? 200;
  const atLimit = total >= limit;

  return (
    <div className="max-w-5xl mx-auto">
      <div className="card card-pad">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="eyebrow">个人卡组</div>
            <h2 className="h2 mt-1">我的卡片</h2>
            <p className="text-[12px] muted mt-1">
              {total} / {limit} 张。只有你自己能看到这些卡片。
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="btn btn-sm btn-primary"
              onClick={openNew}
              disabled={atLimit || loading}
            >
              <Plus size={14} /> 新建卡片
            </button>
            <button
              className="btn btn-sm"
              onClick={() => setStudying(true)}
              disabled={total === 0 || loading}
            >
              <Play size={14} /> 开始学习
            </button>
          </div>
        </div>
        {atLimit && (
          <div className="feedback mt-3 text-[12px] leading-5">
            已达到 200 张上限。删除一张卡片后才能继续新建。
          </div>
        )}
      </div>

      {error && <div className="feedback feedback-bad mt-3">{error}</div>}

      {loading && !data ? (
        <div className="grid sm:grid-cols-2 gap-3 mt-4">
          <div className="skeleton h-40 w-full" />
          <div className="skeleton h-40 w-full" />
        </div>
      ) : total === 0 ? (
        <div className="card empty mt-4">
          <Sparkles size={26} className="mx-auto mb-2 text-[var(--faint)]" />
          <div className="font-medium">还没有个人卡片</div>
          <p className="text-[12px] muted mt-1">
            添加术语、简短含义，以及可选的详细解释。
          </p>
          <button className="btn btn-primary btn-sm mt-4" onClick={openNew}>
            <Plus size={14} /> 创建第一张卡片
          </button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3 mt-4">
          {data?.cards.map((card) => (
            <article key={card.id} className="card card-pad">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-[16px] font-semibold leading-6" lang="en">
                  {card.term}
                </h3>
                <span className="badge shrink-0">{cardStatus(card)}</span>
              </div>
              <p className="text-[13px] leading-6 mt-2 whitespace-pre-wrap" lang="en">
                {card.short_meaning}
              </p>
              {card.detail_meaning && (
                <p className="text-[12px] leading-5 muted mt-2 line-clamp-3 whitespace-pre-wrap" lang="en">
                  {card.detail_meaning}
                </p>
              )}
              <div className="flex items-center justify-between gap-2 mt-4 pt-3 border-t border-[var(--line)]">
                <span className="text-[10.5px] faint">
                  {card.seen_count > 0
                    ? `认识 ${card.known_count} 次 · 已复习 ${card.seen_count} 次`
                    : "尚未复习"}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => openEdit(card)}
                  >
                    <Pencil size={13} /> 编辑
                  </button>
                  <button
                    className="btn btn-ghost btn-sm text-[var(--danger)]"
                    onClick={() => {
                      setDeleteError(null);
                      setDeleteTarget(card);
                    }}
                  >
                    <Trash2 size={13} /> 删除
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      <Modal
        open={formOpen}
        onClose={closeForm}
        title={editing ? "编辑卡片" : "新建卡片"}
        dismissible={!saving}
      >
        <form onSubmit={saveCard}>
          <label className="block text-[12px] font-medium">
            术语 / 卡片名
            <input
              className="input mt-1.5"
              value={form.term}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, term: event.target.value }))
              }
              maxLength={200}
              placeholder="例如：Spacing effect"
              autoFocus
              required
              lang="en"
            />
          </label>
          <label className="block text-[12px] font-medium mt-3">
            简短含义
            <textarea
              className="input mt-1.5 min-h-[82px] resize-y leading-6"
              value={form.short_meaning}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, short_meaning: event.target.value }))
              }
              maxLength={500}
              placeholder="一句容易回忆的清晰解释。"
              required
              lang="en"
            />
          </label>
          <label className="block text-[12px] font-medium mt-3">
            详细解释
            <textarea
              className="input mt-1.5 min-h-[150px] resize-y leading-6"
              value={form.detail_meaning}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, detail_meaning: event.target.value }))
              }
              maxLength={5000}
              placeholder="可选：例子、语境或完整解释。"
              lang="en"
            />
          </label>
          {formError && <div className="feedback feedback-bad mt-3 text-[12px]">{formError}</div>}
          <div className="flex justify-end gap-2 mt-4">
            <button type="button" className="btn" onClick={closeForm} disabled={saving}>
              取消
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? <Loader2 size={15} className="animate-spin" /> : null}
              {editing ? "保存修改" : "创建卡片"}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => {
          if (!deleting) setDeleteTarget(null);
        }}
        title="删除卡片？"
        narrow
        dismissible={!deleting}
      >
        <div className="flex flex-col items-center text-center">
          <div className="grid h-12 w-12 place-items-center rounded-full bg-[var(--danger-soft)] text-[var(--danger)]">
            <AlertTriangle size={22} />
          </div>
          <p className="mt-3 text-[13px] muted leading-6">
            确定删除 <span className="font-semibold text-[var(--ink)]">{deleteTarget?.term}</span>？
            它的复习进度也会一起删除。
          </p>
        </div>
        {deleteError && <div className="feedback feedback-bad mt-3 text-[12px]">{deleteError}</div>}
        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            className="btn"
            onClick={() => setDeleteTarget(null)}
            disabled={deleting}
          >
            保留卡片
          </button>
          <button
            className="btn btn-danger"
            onClick={deleteCard}
            disabled={deleting}
          >
            {deleting ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
            删除
          </button>
        </div>
      </Modal>
    </div>
  );
}
