"use client";

import { Bookmark, BookmarkX, Play, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiDelete, apiGet, apiPost } from "@/lib/api";
import type { Bookmark as BookmarkType, SessionPayload } from "@/lib/types";

export default function BookmarksPage() {
  const router = useRouter();
  const [items, setItems] = useState<BookmarkType[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<BookmarkType[]>("/me/bookmarks?limit=200")
      .then(setItems)
      .catch((e: Error) => setError(e.message));
  }, []);

  async function practice() {
    setBusy(true);
    setError(null);
    try {
      const session = await apiPost<SessionPayload>("/practice-sessions", {
        source: "bookmark",
        count: 20,
      });
      router.push(`/practice/session/${session.session.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start bookmark practice");
      setBusy(false);
    }
  }

  async function remove(questionId: string) {
    if (!window.confirm("移除这道题的收藏？")) return;
    try {
      await apiDelete(`/me/bookmarks/${questionId}`);
      setItems((prev) => (prev ? prev.filter((x) => x.question_id !== questionId) : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove bookmark");
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">Bookmarks</div>
          <h1 className="h1">Bookmarks</h1>
          <p className="muted text-[13px] mt-2">Long-term saved questions. This is separate from Mark for Review inside an exam.</p>
        </div>
        <button className="btn btn-primary" onClick={practice} disabled={busy}>
          {busy ? <RefreshCw size={15} className="animate-spin" /> : <Play size={15} />}
          Practice Bookmarks
        </button>
      </div>

      {error && <div className="feedback feedback-bad mb-4">{error}</div>}
      {!items && <div className="skeleton h-56 w-full" />}
      {items && items.length === 0 && (
        <div className="card empty">
          <Bookmark size={26} className="mx-auto mb-2 text-[var(--faint)]" />
          No bookmarks yet. Tap “Bookmark” on a question during practice.
        </div>
      )}

      <div className="space-y-3">
        {items?.map((item) => (
          <div key={item.question_id} className="card card-pad flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="pill">
                  {item.section || "Question"} {item.display_number ? `Q${item.display_number}` : ""}
                </span>
                <span className="text-[10px] faint font-mono">{item.question_id}</span>
              </div>
              <div className="mt-2 text-[14px] leading-6 line-clamp-3" lang="en">
                {item.stem || item.question_id}
              </div>
            </div>
            <button className="btn btn-sm shrink-0" onClick={() => remove(item.question_id)}>
              <BookmarkX size={13} /> Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
