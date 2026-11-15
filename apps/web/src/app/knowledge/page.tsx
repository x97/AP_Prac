"use client";

import { KeyRound, LockKeyhole, Network, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { RedeemCodeModal } from "@/components/RedeemCodeModal";
import { apiGet } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { KnowledgeGraphResponse } from "@/lib/types";

export default function KnowledgePage() {
  const { t } = useLanguage();
  const [data, setData] = useState<KnowledgeGraphResponse | null>(null);
  const [activeUnitId, setActiveUnitId] = useState<string | null>(null);
  const [unitResetToken, setUnitResetToken] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [redeemOpen, setRedeemOpen] = useState(false);

  const load = useCallback(() => {
    setError(null);
    apiGet<KnowledgeGraphResponse>("/knowledge-graph")
      .then((response) => {
        setData(response);
        setActiveUnitId((current) => {
          if (current && response.units.some((unit) => unit.unit_id === current)) return current;
          return response.units.find((unit) => !unit.locked)?.unit_id || response.units[0]?.unit_id || null;
        });
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const units = data?.units ?? [];
  const activeUnit = useMemo(
    () => units.find((unit) => unit.unit_id === activeUnitId) || null,
    [units, activeUnitId],
  );
  const accessibleCount = units.filter((unit) => !unit.locked).length;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">Knowledge graph</div>
          <h1 className="h1">{t("知识图谱")}</h1>
          <p className="muted text-[13px] mt-2">
            {t("按账号已解锁的 Unit 展示。先看 Unit 结构，再点 Topic 进入章节思维导图，最后点叶子概念查看详情。")}
          </p>
        </div>
        <span className="pill">
          <Network size={13} /> {accessibleCount} / {units.length || 5} Units
        </span>
      </div>

      {error && <div className="feedback feedback-bad mb-4">{error}</div>}
      {!data && !error && <div className="card card-pad h-52 skeleton" />}

      {data && (
        <>
          <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
            {units.map((unit) => {
              const selected = unit.unit_id === activeUnitId;
              return (
                <button
                  key={unit.unit_id}
                  type="button"
                  onClick={() => {
                    setActiveUnitId(unit.unit_id);
                    setUnitResetToken((value) => value + 1);
                  }}
                  className={[
                    "shrink-0 rounded-xl border px-3 py-2 text-left transition",
                    selected
                      ? "border-[var(--primary)] bg-[var(--primary-soft)]"
                      : "border-[var(--line)] bg-[var(--surface)] hover:border-[var(--line-strong)]",
                  ].join(" ")}
                >
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold">
                    {unit.locked ? <LockKeyhole size={12} className="text-[var(--danger)]" /> : null}
                    Unit {unit.unit_id}
                  </span>
                  <span className="mt-0.5 block max-w-[150px] truncate text-[10px] muted">
                    {unit.title_en || unit.title}
                  </span>
                </button>
              );
            })}
          </div>

          {activeUnit?.locked ? (
            <div className="card card-pad max-w-2xl">
              <div className="flex items-start gap-3">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[var(--danger-soft)] text-[var(--danger)]">
                  <LockKeyhole size={20} />
                </span>
                <div>
                  <h2 className="h2">{t("Unit {number} 尚未解锁", { number: activeUnit.unit_id })}</h2>
                  <p className="mt-1 text-[12px] leading-5 muted">
                    {t("知识图谱与 Unit 练习共用权限。当前账号只能查看已解锁 Unit 的图谱；激活后会自动显示其余 Unit 的结构和知识点关系。")}
                  </p>
                  <button type="button" className="btn btn-primary mt-4" onClick={() => setRedeemOpen(true)}>
                    <KeyRound size={14} /> {t("使用激活码")}
                  </button>
                </div>
              </div>
            </div>
          ) : activeUnit ? (
            <KnowledgeGraph key={`${activeUnit.unit_id}:${unitResetToken}`} unit={activeUnit} />
          ) : (
            <div className="empty">{t("暂无可用知识图谱。")}</div>
          )}

          <p className="mt-3 text-[10.5px] faint">
            {t("图谱为只读内容，跟随当前内容 Release 生成；未解锁 Unit 不返回概念和关系数据。")}
          </p>
        </>
      )}

      <RedeemCodeModal open={redeemOpen} onClose={() => setRedeemOpen(false)} onRedeemed={() => load()} />
      {!data && !error && (
        <div className="mt-3 flex items-center gap-2 text-[11px] muted">
          <RefreshCw size={12} className="animate-spin" /> {t("正在生成知识图谱…")}
        </div>
      )}
    </div>
  );
}
