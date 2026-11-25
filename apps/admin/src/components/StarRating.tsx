"use client";

import { Star } from "lucide-react";

type StarRatingProps = {
  value?: number | null;
  onChange?: (value: number | null) => void;
  disabled?: boolean;
  size?: number;
  label?: string;
};

export function StarRating({
  value,
  onChange,
  disabled = false,
  size = 15,
  label = "星级",
}: StarRatingProps) {
  const current = value ?? 0;
  const interactive = Boolean(onChange) && !disabled;
  return (
    <span
      className="inline-flex items-center gap-0.5"
      role="group"
      aria-label={label}
      title={interactive ? undefined : `${current} 星`}
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const active = star <= current;
        const icon = (
          <Star
            size={size}
            strokeWidth={1.8}
            className={active ? "fill-current" : undefined}
          />
        );
        const tone = active ? "text-[var(--accent)]" : "text-[var(--faint)]";
        if (!interactive) {
          return (
            <span key={star} className={`p-0.5 ${tone}`}>
              {icon}
            </span>
          );
        }
        return (
          <button
            key={star}
            type="button"
            className={`rounded p-0.5 transition hover:text-[var(--accent)] ${tone}`}
            aria-label={current === star ? `清除星级（当前 ${current} 星）` : `设为 ${star} 星`}
            aria-pressed={current === star}
            title={current === star ? "点击清除星级" : `设为 ${star} 星`}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onChange?.(current === star ? null : star);
            }}
          >
            {icon}
          </button>
        );
      })}
    </span>
  );
}
