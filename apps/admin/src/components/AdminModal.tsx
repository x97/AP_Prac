"use client";

import { X } from "lucide-react";
import { useEffect } from "react";

export function AdminModal({
  open,
  title,
  onClose,
  children,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/45 p-4 sm:p-8"
      onMouseDown={onClose}
      role="presentation"
    >
      <div
        className={`a-card my-auto w-full ${wide ? "max-w-4xl" : "max-w-xl"} p-5`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-[16px] font-semibold">{title}</h2>
          <button type="button" className="a-btn a-btn-sm" onClick={onClose} aria-label="关闭">
            <X size={15} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
