"use client";

import { CalendarClock, CheckCircle2, Lock, Play } from "lucide-react";
import Link from "next/link";

import { useLanguage } from "@/lib/i18n";
import type { StudyDayTask } from "@/lib/types";

export function StudyTaskCard({
  task,
  starting,
  planColor,
  onStart,
}: {
  task: StudyDayTask;
  starting: boolean;
  planColor?: string;
  onStart: (task: StudyDayTask) => void;
}) {
  const { t } = useLanguage();
  const completed = task.status === "completed";
  const locked = task.status === "locked";
  return (
    <div
      className={`study-task-card ${planColor ? `plan-tint color-${planColor}` : ""} ${
        completed ? "is-completed" : ""
      } ${task.status === "overdue" ? "is-overdue" : ""} ${
        locked ? "is-locked" : ""
      }`}
    >
      <div className="study-task-main">
        <div className="study-task-title">
          <span className="text-[13.5px]">{task.title}</span>
          {task.early && <span className="pill pill-primary">{t("提前")}</span>}
          {task.status === "overdue" && (
            <span className="pill pill-warn">{t("待补做")}</span>
          )}
          {task.overdue && task.status === "locked" && (
            <span className="pill pill-warn">{t("逾期")}</span>
          )}
          {task.completed_late && <span className="pill">{t("迟完成")}</span>}
        </div>
        <div className="study-task-meta">
          <span>{task.homework_title}</span>
          {task.unit_title && <span>Unit {task.unit_id} · {task.unit_title}</span>}
          {task.topic_title && <span>{task.topic_title}</span>}
          <span>
            {task.answered_question_count}/{task.question_count} {t("题")}
          </span>
          {task.unavailable_question_count > 0 && (
            <span className="text-[var(--danger)]">
              {t("{count} 题已移除", { count: task.unavailable_question_count })}
            </span>
          )}
        </div>
        {task.note && <p className="study-task-note">{task.note}</p>}
        {locked && (
          <div className="study-task-lock">
            <Lock size={13} /> {task.locked_reason || t("完成前一项后解锁")}
          </div>
        )}
      </div>
      <div className="study-task-action">
        {completed ? (
          task.session_id ? (
            <Link
              href={`/practice/session/${task.session_id}?from=calendar&task=${task.task_id}`}
              className="btn btn-sm"
            >
              <CheckCircle2 size={14} /> {t("查看回顾")}
            </Link>
          ) : (
            <span className="pill pill-success">{t("已完成")}</span>
          )
        ) : locked ? (
          <span className="pill pill-locked">
            <Lock size={12} /> {t("已锁定")}
          </span>
        ) : (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => onStart(task)}
            disabled={starting}
          >
            {starting ? (
              <CalendarClock size={14} className="animate-pulse" />
            ) : (
              <Play size={14} />
            )}
            {task.session_status === "in_progress"
              ? t("继续作业")
              : task.status === "overdue"
                ? t("补做作业")
                : t("开始作业")}
          </button>
        )}
      </div>
    </div>
  );
}
