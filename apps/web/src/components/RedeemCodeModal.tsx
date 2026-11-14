"use client";

import { CheckCircle2, KeyRound, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Modal } from "@/components/Modal";
import { apiPost } from "@/lib/api";
import type { SubjectEntitlement } from "@/lib/types";

type RedeemResult = {
  ok: boolean;
  subjects: Array<{
    subject_id: string;
    expires_at: string;
    previous_expires_at: string | null;
  }>;
  entitlements: SubjectEntitlement[];
};

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function RedeemCodeModal({
  open,
  onClose,
  onRedeemed,
}: {
  open: boolean;
  onClose: () => void;
  onRedeemed?: (result: RedeemResult) => void;
}) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RedeemResult | null>(null);

  useEffect(() => {
    if (!open) return;
    setCode("");
    setBusy(false);
    setConfirming(false);
    setError(null);
    setResult(null);
  }, [open]);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!code.trim() || busy) return;
    setConfirming(true);
  }

  async function redeem() {
    if (!code.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await apiPost<RedeemResult>("/me/activation-codes/redeem", {
        code: code.trim(),
      });
      setResult(response);
      setConfirming(false);
      onRedeemed?.(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "激活失败，请检查激活码");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={busy ? () => undefined : onClose}
      title={result ? "激活成功" : confirming ? "确认激活" : "使用激活码"}
      narrow
      dismissible={!busy}
    >
      {result ? (
        <div className="py-4 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-[var(--success-soft)] text-[var(--success)]">
            <CheckCircle2 size={28} />
          </div>
          <h3 className="mt-4 text-[17px] font-semibold">课程已激活</h3>
          <div className="mx-auto mt-4 max-w-[320px] space-y-2">
            {result.subjects.map((item) => (
              <div
                key={item.subject_id}
                className="flex items-center justify-between gap-3 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3.5 py-2.5 text-left text-[12px]"
              >
                <span className="font-medium">{item.subject_id}</span>
                <span className="text-[var(--muted)]">至 {formatDate(item.expires_at)}</span>
              </div>
            ))}
          </div>
          <button type="button" className="btn btn-primary mt-5" onClick={onClose}>
            开始使用
          </button>
        </div>
      ) : confirming ? (
        <div className="py-2 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
            <KeyRound size={27} />
          </div>
          <h3 className="mt-4 text-[17px] font-semibold">确认使用这个激活码？</h3>
          <p className="mx-auto mt-2 max-w-[280px] text-[12px] leading-5 muted">
            激活后会绑定当前账号，不能转给其他账号。确认后立即生效。
          </p>
          <div className="mx-auto mt-4 max-w-[280px] rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-4 py-3 font-mono text-[14px] tracking-[0.08em]">
            {code}
          </div>
          <div className="mt-5 flex justify-center gap-2">
            <button
              type="button"
              className="btn"
              onClick={() => setConfirming(false)}
              disabled={busy}
            >
              返回修改
            </button>
            <button
              type="button"
              className="btn btn-primary min-w-[112px]"
              onClick={() => void redeem()}
              disabled={busy}
            >
              {busy ? <Loader2 size={15} className="animate-spin" /> : <KeyRound size={15} />}
              {busy ? "激活中…" : "确认激活"}
            </button>
          </div>
          {error && (
            <div className="mx-auto mt-4 max-w-[300px] rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2.5 text-[12px] text-[var(--danger)]">
              {error}
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div className="flex items-start gap-3 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3.5">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[var(--primary-soft)] text-[var(--primary)]">
              <KeyRound size={17} />
            </div>
            <p className="text-[12px] leading-5 muted">
              激活码会绑定当前账号。新时长会叠加到已有有效期上；指定日期码会延长到该日期。
            </p>
          </div>

          <label className="block">
            <span className="text-[11px] font-medium uppercase tracking-[0.1em] text-[var(--faint)]">
              Activation code
            </span>
            <input
              className="input mt-1.5 font-mono text-[14px] tracking-[0.08em]"
              value={code}
              onChange={(event) => setCode(event.target.value.toUpperCase())}
              placeholder="AP-XXXX-XXXX-XXXX"
              autoComplete="off"
              spellCheck={false}
              disabled={busy}
              autoFocus
            />
          </label>

          {error && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2.5 text-[12px] text-[var(--danger)]">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 border-t border-[var(--line)] pt-4">
            <button type="button" className="btn" onClick={onClose} disabled={busy}>
              取消
            </button>
            <button
              type="submit"
              className="btn btn-primary min-w-[110px]"
              disabled={busy || code.trim().length < 6}
            >
              {busy ? <Loader2 size={15} className="animate-spin" /> : <KeyRound size={15} />}
              下一步
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
