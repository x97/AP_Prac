"use client";

import { ChevronDown, ChevronRight, Minus, Plus } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import type { KnowledgeGraphEditorNode } from "@/lib/types";

type CanvasProps = {
  tree: KnowledgeGraphEditorNode;
  selectedId: string | null;
  expanded: Set<string>;
  canEdit: boolean;
  onSelect: (id: string) => void;
  onToggle: (id: string) => void;
  onAddChild: (id: string) => void;
};

type Measured = {
  node: KnowledgeGraphEditorNode;
  depth: number;
  lines: string[];
  cardHeight: number;
  height: number;
  children: Measured[];
};

type Card = {
  node: KnowledgeGraphEditorNode;
  id: string;
  depth: number;
  x: number;
  y: number;
  width: number;
  height: number;
  lines: string[];
};

const CARD_WIDTH = 224;
const ROOT_WIDTH = 250;
const X_START = 28;
const X_STEP = 282;
const Y_GAP = 16;
const PAD = 28;
const LINE_HEIGHT = 17;

function wrapLabel(value: string, limit: number, maxLines = 3): string[] {
  const words = String(value || "Untitled").split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length <= limit || !current) {
      current = next;
      continue;
    }
    lines.push(current);
    current = word;
    if (lines.length === maxLines - 1) break;
  }
  if (current && lines.length < maxLines) lines.push(current);
  const joined = lines.join(" ");
  if (joined.length < value.length && lines.length) {
    lines[lines.length - 1] = `${lines[lines.length - 1].replace(/…$/, "").slice(0, limit - 1)}…`;
  }
  return lines.length ? lines : ["Untitled"];
}

function cardHeight(lines: string[], root: boolean): number {
  return (root ? 50 : 44) + lines.length * LINE_HEIGHT;
}

function measure(
  node: KnowledgeGraphEditorNode,
  depth: number,
  expanded: Set<string>,
): Measured {
  const root = depth === 0;
  const width = root ? ROOT_WIDTH : CARD_WIDTH;
  const limit = root ? 24 : Math.max(18, Math.floor((width - 44) / 7));
  const lines = wrapLabel(node.label, limit, 3);
  const height = cardHeight(lines, root);
  const visible = expanded.has(node.id) ? node.children : [];
  const children = visible.map((child) => measure(child, depth + 1, expanded));
  const childrenHeight = children.reduce((sum, child) => sum + child.height, 0)
    + Math.max(0, children.length - 1) * Y_GAP;
  return {
    node,
    depth,
    lines,
    cardHeight: height,
    height: Math.max(height, childrenHeight),
    children,
  };
}

function place(
  measured: Measured,
  top: number,
  cards: Card[],
  links: Array<{ parentId: string; childId: string }>,
  parentId: string | null,
): Card {
  const root = measured.depth === 0;
  const width = root ? ROOT_WIDTH : CARD_WIDTH;
  const x = X_START + measured.depth * X_STEP;
  const y = top + (measured.height - measured.cardHeight) / 2;
  const card: Card = {
    node: measured.node,
    id: measured.node.id,
    depth: measured.depth,
    x,
    y,
    width,
    height: measured.cardHeight,
    lines: measured.lines,
  };
  cards.push(card);
  if (parentId) links.push({ parentId, childId: card.id });

  let childTop = top;
  for (const child of measured.children) {
    place(child, childTop, cards, links, card.id);
    childTop += child.height + Y_GAP;
  }
  return card;
}

function buildLayout(root: KnowledgeGraphEditorNode, expanded: Set<string>) {
  const measured = measure(root, 0, expanded);
  const cards: Card[] = [];
  const links: Array<{ parentId: string; childId: string }> = [];
  place(measured, PAD, cards, links, null);
  const maxX = Math.max(...cards.map((card) => card.x + card.width), 0);
  const maxY = Math.max(...cards.map((card) => card.y + card.height), 0);
  return {
    cards,
    links,
    width: maxX + PAD,
    height: maxY + PAD,
  };
}

function typeStyle(node: KnowledgeGraphEditorNode) {
  if (node.type === "concept") {
    return { label: "Concept", className: "a-badge a-badge-primary" };
  }
  if (node.type === "supplement") {
    return { label: "Supplement", className: "a-badge a-badge-warn" };
  }
  return { label: "Branch", className: "a-badge" };
}

function cardTone(node: KnowledgeGraphEditorNode, depth: number) {
  if (depth === 0) return "bg-[var(--primary)] text-white border-[var(--primary)]";
  if (node.type === "supplement") {
    return "bg-[var(--accent-soft)] border-[#f4dfc4] text-[var(--ink)]";
  }
  if (node.type === "concept") {
    return "bg-white border-[var(--line)] text-[var(--ink)]";
  }
  return "bg-[var(--surface-2)] border-[var(--line)] text-[var(--ink)]";
}

export function KnowledgeGraphCanvas({
  tree,
  selectedId,
  expanded,
  canEdit,
  onSelect,
  onToggle,
  onAddChild,
}: CanvasProps) {
  const [zoom, setZoom] = useState(1);
  const [dragging, setDragging] = useState(false);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{
    pointerId: number;
    x: number;
    y: number;
    scrollLeft: number;
    scrollTop: number;
  } | null>(null);
  const layout = useMemo(() => buildLayout(tree, expanded), [tree, expanded]);
  const cardById = useMemo(
    () => new Map(layout.cards.map((card) => [card.id, card])),
    [layout.cards],
  );

  useEffect(() => {
    // Center the root when a Topic first opens. Expanding/collapsing and
    // selecting cards must not yank the user's scroll position.
    const scroller = scrollerRef.current;
    const root = layout.cards.find((card) => card.depth === 0);
    if (!scroller || !root) return;
    scroller.scrollLeft = 0;
    scroller.scrollTop = Math.max(0, (root.y - 80) * zoom);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tree.id]);

  function startDrag(event: React.PointerEvent<HTMLDivElement>) {
    if (event.pointerType !== "mouse" || event.button !== 0) return;
    const target = event.target as HTMLElement;
    if (target.closest("[data-graph-card]") || target.closest("button")) return;
    const scroller = scrollerRef.current;
    if (!scroller) return;
    dragRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      scrollLeft: scroller.scrollLeft,
      scrollTop: scroller.scrollTop,
    };
    setDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function moveDrag(event: React.PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    const scroller = scrollerRef.current;
    if (!drag || !scroller || drag.pointerId !== event.pointerId) return;
    scroller.scrollLeft = drag.scrollLeft - (event.clientX - drag.x);
    scroller.scrollTop = drag.scrollTop - (event.clientY - drag.y);
  }

  function endDrag(event: React.PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function setZoomSafe(next: number) {
    setZoom(Math.max(0.7, Math.min(1.6, Math.round(next * 10) / 10)));
  }

  return (
    <div className="relative">
      <div className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-md border border-[var(--line)] bg-white/90 px-2 py-1 text-[9.5px] text-[var(--faint)] shadow-sm">
        拖拽空白处上下左右移动 · 滚轮滚动
      </div>
      <div className="pointer-events-none absolute right-3 top-3 z-10 flex gap-1">
        <div className="pointer-events-auto flex items-center gap-1 rounded-lg border border-[var(--line)] bg-white/95 p-1 shadow-sm">
          <button
            type="button"
            className="grid h-6 w-6 place-items-center rounded text-[var(--muted)] hover:bg-[var(--surface-2)]"
            onClick={() => setZoomSafe(zoom - 0.1)}
            aria-label="缩小"
          >
            <Minus size={13} />
          </button>
          <span className="min-w-[38px] text-center font-mono text-[10px] text-[var(--muted)]">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            className="grid h-6 w-6 place-items-center rounded text-[var(--muted)] hover:bg-[var(--surface-2)]"
            onClick={() => setZoomSafe(zoom + 0.1)}
            aria-label="放大"
          >
            <Plus size={13} />
          </button>
        </div>
      </div>

      <div
        ref={scrollerRef}
        data-graph-scroller="true"
        className={[
          "overflow-auto rounded-xl border border-[var(--line)] bg-[var(--surface)]",
          dragging ? "cursor-grabbing select-none" : "cursor-grab",
        ].join(" ")}
        onPointerDown={startDrag}
        onPointerMove={moveDrag}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={endDrag}
        style={{
          maxHeight: "calc(100vh - 360px)",
          minHeight: 420,
          backgroundImage:
            "radial-gradient(circle, color-mix(in srgb, var(--line) 70%, transparent) 1px, transparent 1px)",
          backgroundSize: "18px 18px",
        }}
      >
        <div
          style={{
            width: layout.width * zoom,
            height: layout.height * zoom,
          }}
        >
          <div
            className="relative"
            style={{
              width: layout.width,
              height: layout.height,
              transform: `scale(${zoom})`,
              transformOrigin: "top left",
            }}
          >
            <svg
              className="pointer-events-none absolute inset-0"
              width={layout.width}
              height={layout.height}
              aria-hidden="true"
            >
              {layout.cards.map((parent) => {
                const children = layout.links
                  .filter((link) => link.parentId === parent.id)
                  .map((link) => cardById.get(link.childId))
                  .filter((card): card is Card => Boolean(card));
                if (!children.length) return null;
                const sx = parent.x + parent.width;
                const sy = parent.y + parent.height / 2;
                const busX = children[0].x - 22;
                const firstY = children[0].y + children[0].height / 2;
                const lastY = children[children.length - 1].y + children[children.length - 1].height / 2;
                return (
                  <g key={parent.id}>
                    <path
                      d={`M ${sx} ${sy} L ${busX} ${sy}`}
                      fill="none"
                      stroke="color-mix(in srgb, var(--primary) 45%, var(--line))"
                      strokeWidth={1.4}
                    />
                    {children.length > 1 && (
                      <path
                        d={`M ${busX} ${firstY} L ${busX} ${lastY}`}
                        fill="none"
                        stroke="color-mix(in srgb, var(--primary) 45%, var(--line))"
                        strokeWidth={1.4}
                      />
                    )}
                    {children.map((child) => (
                      <path
                        key={child.id}
                        d={`M ${busX} ${child.y + child.height / 2} L ${child.x} ${child.y + child.height / 2}`}
                        fill="none"
                        stroke="color-mix(in srgb, var(--primary) 45%, var(--line))"
                        strokeWidth={1.4}
                      />
                    ))}
                  </g>
                );
              })}
            </svg>

            {layout.cards.map((card) => {
              const root = card.depth === 0;
              const type = typeStyle(card.node);
              const selected = selectedId === card.id;
              const hasChildren = card.node.children.length > 0;
              const open = expanded.has(card.id);
              return (
                <div
                  key={card.id}
                  data-graph-card="true"
                  role="button"
                  tabIndex={0}
                  className={[
                    "group absolute cursor-pointer rounded-xl border px-3 py-2 shadow-sm transition",
                    cardTone(card.node, card.depth),
                    selected ? "ring-2 ring-[var(--primary)] ring-offset-2" : "hover:shadow-md",
                    card.depth > 0 && card.node.type === "concept" ? "border-l-4 border-l-[var(--primary)]" : "",
                    card.depth > 0 && card.node.type === "supplement" ? "border-l-4 border-l-[var(--accent)]" : "",
                  ].join(" ")}
                  style={{
                    left: card.x,
                    top: card.y,
                    width: card.width,
                    minHeight: card.height,
                  }}
                  onClick={() => onSelect(card.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect(card.id);
                    }
                  }}
                  title={card.node.label}
                >
                  {hasChildren && (
                    <button
                      type="button"
                      className={[
                        "absolute -left-2.5 top-1/2 z-10 grid h-5 w-5 -translate-y-1/2 place-items-center rounded-full border shadow-sm",
                        root
                          ? "border-white/50 bg-white text-[var(--primary)]"
                          : "border-[var(--line)] bg-white text-[var(--muted)] hover:text-[var(--ink)]",
                      ].join(" ")}
                      onClick={(event) => {
                        event.stopPropagation();
                        onToggle(card.id);
                      }}
                      aria-label={open ? "收起子节点" : "展开子节点"}
                    >
                      {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </button>
                  )}
                  <div className="min-w-0">
                    {card.lines.map((line, index) => (
                      <div
                        key={`${card.id}-${index}`}
                        className={[
                          "leading-[17px]",
                          root ? "text-[12.5px] font-semibold" : "text-[12px] font-medium",
                        ].join(" ")}
                      >
                        {line}
                      </div>
                    ))}
                    <div className="mt-1 flex items-center gap-1.5">
                      <span className={root ? "a-badge border-white/30 bg-white/15 text-white" : type.className}>
                        {type.label}
                      </span>
                      {!open && hasChildren && (
                        <span className={root ? "text-[9px] text-white/75" : "text-[9px] text-[var(--faint)]"}>
                          +{card.node.children.length}
                        </span>
                      )}
                      {canEdit && (
                        <button
                          type="button"
                          className={[
                            "ml-auto grid h-5 w-5 place-items-center rounded opacity-0 transition group-hover:opacity-100",
                            root
                              ? "bg-white/20 text-white hover:bg-white/30"
                              : "bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--primary)]",
                          ].join(" ")}
                          onClick={(event) => {
                            event.stopPropagation();
                            onAddChild(card.id);
                          }}
                          aria-label="添加子节点"
                        >
                          <Plus size={12} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
