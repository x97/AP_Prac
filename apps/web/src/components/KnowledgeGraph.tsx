"use client";

import { ArrowLeft, Maximize2, Minimize2 } from "lucide-react";
import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";

import { Modal } from "@/components/Modal";
import { QuestionView } from "@/components/QuestionView";
import styles from "@/components/KnowledgeGraph.module.css";
import { apiGet } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type {
  KnowledgeGraphConcept,
  KnowledgeGraphMindNode,
  KnowledgeGraphRelation,
  KnowledgeGraphSample,
  KnowledgeGraphTopic,
  KnowledgeGraphUnit,
  Question,
} from "@/lib/types";

const W = 960;
const H = 720;
const CX = 480;
const CY = 360;
const RELATION_LABELS: Record<string, string> = {
  part_of: "组成",
  broader_narrower: "上下位",
  related_to: "相关",
  same_name_different_sense: "同名异义",
};
const ROLE_LABELS: Record<string, string> = {
  core: "核心题",
  supporting: "辅助题",
  confusable: "干扰项",
};

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function shortText(value: string, limit: number) {
  const base = value || "";
  return base.length > limit ? `${base.slice(0, limit - 1)}…` : base;
}

function conceptIndex(unit: KnowledgeGraphUnit) {
  const map = new Map<string, { topic: KnowledgeGraphTopic; concept: KnowledgeGraphConcept }>();
  for (const topic of unit.topics || []) {
    for (const concept of topic.concepts) {
      map.set(concept.concept_id, { topic, concept });
    }
  }
  for (const [id, concept] of Object.entries(unit.mindmap_concepts || {})) {
    if (map.has(id)) continue;
    const topic = unit.topics?.find((item) => item.code === concept.topic_code);
    if (topic) map.set(id, { topic, concept });
  }
  return map;
}

function structureCenters(topics: KnowledgeGraphTopic[]) {
  const centers = new Map<string, { x: number; y: number; ring: number }>();
  topics.forEach((topic, index) => {
    const angle = -Math.PI / 2 + (index / Math.max(1, topics.length)) * Math.PI * 2 + 0.12;
    const ring = clamp(32 + Math.sqrt(topic.concept_count) * 1.6, 35, 45);
    centers.set(topic.code, {
      x: CX + 245 * Math.cos(angle),
      y: CY + 245 * Math.sin(angle),
      ring,
    });
  });
  return centers;
}

const BRANCH_COLORS = ["var(--primary)", "var(--accent)", "var(--success)", "#7c5ce5", "#0e7490", "#be185d"];

type MindGroup = {
  label: string;
  concepts: KnowledgeGraphConcept[];
  color: string;
};

type MindLeaf = {
  concept: KnowledgeGraphConcept;
  cy: number;
};

type MindSideGroup = MindGroup & {
  branchY: number;
  leaves: MindLeaf[];
};

function branchLabel(chapter: string, topic: KnowledgeGraphTopic) {
  let label = (chapter || "Other concepts").trim();
  if (!label) label = "Other concepts";
  if (label.toLowerCase() === topic.title_en.toLowerCase()) return "Core content";
  const module = label.match(/^Module\s+([0-9.]+[a-z]?)\s+(.*)$/i);
  if (module) label = `${module[1]} ${module[2]}`;
  return shortText(label, 21);
}

function buildMindGroups(topic: KnowledgeGraphTopic): MindGroup[] {
  const map = new Map<string, KnowledgeGraphConcept[]>();
  for (const concept of topic.concepts) {
    const key = (concept.chapter || "Other concepts").trim() || "Other concepts";
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(concept);
  }
  let groups = [...map.entries()].map(([label, concepts]) => ({
    label: branchLabel(label, topic),
    concepts: concepts.slice().sort((a, b) => b.weight - a.weight),
    color: "var(--primary)",
  }));
  groups.sort((a, b) => b.concepts.length - a.concepts.length || a.label.localeCompare(b.label));
  // Tiny one-off book sections add noise to a chapter mind map. Fold them
  // into one Related concepts branch when there is enough structure.
  const singles = groups.filter((group) => group.concepts.length === 1);
  if (groups.length > 3 && singles.length > 0) {
    groups = groups.filter((group) => group.concepts.length > 1);
    groups.push({
      label: "Related concepts",
      concepts: singles.flatMap((group) => group.concepts),
      color: "var(--muted)",
    });
  }
  return groups.map((group, index) => ({
    ...group,
    color: group.label === "Related concepts" ? "var(--muted)" : BRANCH_COLORS[index % BRANCH_COLORS.length],
  }));
}

function layoutMindSide(groups: MindGroup[]): MindSideGroup[] {
  const total = groups.reduce((sum, group) => sum + group.concepts.length, 0);
  if (!total) return [];
  const top = 56;
  const bottom = H - 56;
  const available = bottom - top;
  const gap = Math.min(36, available / total);
  let y = top + (available - gap * total) / 2 + gap / 2;
  return groups.map((group) => {
    const start = y;
    const leaves: MindLeaf[] = group.concepts.map((concept) => {
      const cy = y;
      y += gap;
      return { concept, cy };
    });
    return {
      ...group,
      leaves,
      branchY: (start + y - gap) / 2,
    };
  });
}

function mindLeafWidth() {
  return 200;
}

function relationRows(concept: KnowledgeGraphConcept, lookup: Map<string, { topic: KnowledgeGraphTopic; concept: KnowledgeGraphConcept }>) {
  return concept.relations.map((relation: KnowledgeGraphRelation) => ({
    ...relation,
    exists: lookup.has(relation.id),
  }));
}

function StructureGraph({
  unit,
  onOpenTopic,
}: {
  unit: KnowledgeGraphUnit;
  onOpenTopic: (topic: KnowledgeGraphTopic, conceptId?: string) => void;
}) {
  const { t } = useLanguage();
  const topics = unit.topics || [];
  const centers = useMemo(() => structureCenters(topics), [topics]);
  const bridges = useMemo(() => {
    return (unit.bridges || [])
      .filter((bridge) => bridge.semantic > 0 || bridge.contrast >= 8 || bridge.co >= 4)
      .sort((a, b) => b.semantic + b.contrast + b.co - (a.semantic + a.contrast + a.co))
      .slice(0, 12)
      .map((bridge) => ({
        ...bridge,
        a: centers.get(bridge.source),
        b: centers.get(bridge.target),
      }))
      .filter((bridge) => bridge.a && bridge.b);
  }, [unit.bridges, centers]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${unit.title_en} knowledge graph structure`}>
      <defs>
        <marker id="kg-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" className={styles.arrow} />
        </marker>
      </defs>

      {bridges.map((bridge) => {
        const a = bridge.a!;
        const b = bridge.b!;
        const mx = (a.x + b.x) / 2;
        const my = (a.y + b.y) / 2;
        const dx = mx - CX;
        const dy = my - CY;
        const len = Math.max(1, Math.hypot(dx, dy));
        const qx = mx + (dx / len) * 32;
        const qy = my + (dy / len) * 32;
        const kind = bridge.contrast >= 8 ? "contrast" : bridge.semantic ? "semantic" : "co";
        const weight = bridge.semantic + bridge.contrast + bridge.co;
        return (
          <path
            key={`${bridge.source}-${bridge.target}`}
            d={`M ${a.x.toFixed(1)} ${a.y.toFixed(1)} Q ${qx.toFixed(1)} ${qy.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`}
            className={cx(styles.bridge, kind === "contrast" ? styles.contrast : kind === "semantic" ? styles.semantic : styles.co)}
            style={{ opacity: 0.2 + Math.min(0.42, Math.log2(1 + weight) * 0.06) }}
          >
            <title>{`${bridge.source} ↔ ${bridge.target} · ${t("教材 {semantic} · 易混 {contrast} · 同题 {co}", {
              semantic: bridge.semantic,
              contrast: bridge.contrast,
              co: bridge.co,
            })}`}</title>
          </path>
        );
      })}

      {topics.map((topic) => {
        const center = centers.get(topic.code);
        if (!center) return null;
        const dx = center.x - CX;
        const dy = center.y - CY;
        const len = Math.max(1, Math.hypot(dx, dy));
        return (
          <line
            key={`spoke-${topic.code}`}
            x1={CX + (dx / len) * 45}
            y1={CY + (dy / len) * 45}
            x2={CX + (dx / len) * (len - center.ring - 3)}
            y2={CY + (dy / len) * (len - center.ring - 3)}
            className={styles.spoke}
          />
        );
      })}

      <g>
        <circle cx={CX} cy={CY} r={48} className={styles.hub} />
        <text x={CX} y={CY - 8} textAnchor="middle" className={styles.hubTitle}>Unit {unit.unit_id}</text>
        <text x={CX} y={CY + 9} textAnchor="middle" className={styles.hubSub}>{shortText(unit.title_en, 24)}</text>
        <text x={CX} y={CY + 23} textAnchor="middle" className={styles.hubSub}>{unit.concept_count ?? 0} concepts</text>
      </g>

      {topics.map((topic) => {
        const center = centers.get(topic.code);
        if (!center) return null;
        const top = topic.concepts.slice(0, 3);
        return (
          <g
            key={topic.topic_id}
            className={styles.topic}
            role="button"
            tabIndex={0}
            aria-label={`${topic.code} ${topic.title_en}, ${topic.concept_count} concepts`}
            onClick={() => onOpenTopic(topic)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onOpenTopic(topic);
              }
            }}
          >
            <title>{`${topic.code} ${topic.title_en} · ${topic.concept_count} concepts · ${topic.question_count} questions`}</title>
            <circle cx={center.x} cy={center.y} r={center.ring} className={styles.topicCircle} />
            {top.map((concept, index) => {
              const angle = -Math.PI / 2 + 0.31 + (index / Math.max(1, top.length)) * Math.PI * 2;
              const rr = center.ring - 8;
              const x = center.x + rr * Math.cos(angle);
              const y = center.y + rr * Math.sin(angle);
              return (
                <g key={concept.concept_id}>
                  <circle
                    cx={x}
                    cy={y}
                    r={4.2}
                    className={cx(styles.topicDot, concept.tier === "core" ? styles.core : styles.supporting)}
                    onClick={(event) => {
                      event.stopPropagation();
                      onOpenTopic(topic, concept.concept_id);
                    }}
                  >
                    <title>{`${concept.name} · ${concept.questions.total} questions`}</title>
                  </circle>
                  <text
                    x={center.x + (center.ring + 9) * Math.cos(angle)}
                    y={center.y + (center.ring + 9) * Math.sin(angle) + 3}
                    textAnchor={Math.cos(angle) > 0.25 ? "start" : Math.cos(angle) < -0.25 ? "end" : "middle"}
                    className={styles.keyLabel}
                  >
                    {shortText(concept.name, 14)}
                  </text>
                </g>
              );
            })}
            {(() => {
              const dx = center.x - CX;
              const dy = center.y - CY;
              const len = Math.max(1, Math.hypot(dx, dy));
              const cos = dx / len;
              const sin = dy / len;
              const lines = wrapOutlineLabel(topic.title_en, 18, 4);
              const side = Math.abs(cos) > 0.34;
              const anchor = side ? (cos > 0 ? "start" : "end") : "middle";
              const lineHeight = 17;
              const x = side
                ? center.x + (cos > 0 ? 1 : -1) * (center.ring + 12)
                : center.x;
              const y = side
                ? center.y - ((lines.length - 1) * lineHeight) / 2
                : center.y + (sin > 0 ? 1 : -1) * (center.ring + 18) + (sin < 0 ? -(lines.length - 1) * lineHeight : 0);
              return (
                <>
                  <text x={center.x} y={center.y + 3} textAnchor="middle" className={styles.structureCode}>
                    {topic.code}
                  </text>
                  {lines.map((line, index) => (
                    <text
                      key={`${line}-${index}`}
                      x={x}
                      y={y + index * lineHeight}
                      textAnchor={anchor}
                      className={styles.structureTitle}
                    >
                      {line}
                    </text>
                  ))}
                </>
              );
            })()}
          </g>
        );
      })}
    </svg>
  );
}

const OUTLINE_W = 1000;
const OUTLINE_X = [24, 280, 540, 800, 1020, 1240];
const OUTLINE_WIDTHS = [200, 230, 230, 190, 190, 170];
const OUTLINE_LIMITS = [18, 23, 23, 20, 20, 18];
const OUTLINE_LINE_HEIGHT = [22, 18, 17, 16, 16, 15];
const OUTLINE_MAX_DEPTH = 5;
const OUTLINE_MARGIN = 36;
const OUTLINE_V_GAP = 14;
const OUTLINE_BRANCH_GAP = 20;
const OUTLINE_TRUNK_GAP = 20;
const MIND_COLORS = [
  "var(--primary)",
  "var(--accent)",
  "var(--success)",
  "#7c5ce5",
  "#0e7490",
  "#be185d",
];

type OutlineCard = {
  node: KnowledgeGraphMindNode;
  id: string;
  collapsed: boolean;
  depth: number;
  color: string;
  index: number;
  parent: OutlineCard | null;
  lines: string[];
  width: number;
  height: number;
  x: number;
  y: number;
  subtree: number;
  hidden: number;
  children: OutlineCard[];
};

function descendantCount(node: KnowledgeGraphMindNode): number {
  return (node.children || []).reduce((sum, child) => sum + 1 + descendantCount(child), 0);
}

function wrapOutlineLabel(text: string, limit: number, maxLines = 3): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const raw of words) {
    let word = raw;
    if (word.length > limit) {
      if (current) {
        lines.push(current);
        current = "";
      }
      lines.push(`${word.slice(0, limit - 1)}…`);
      word = word.slice(limit - 1);
      if (!word) continue;
    }
    const next = current ? `${current} ${word}` : word;
    if (next.length > limit && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) lines.push(current);
  if (lines.length > maxLines) {
    const kept = lines.slice(0, maxLines);
    const last = kept[maxLines - 1];
    kept[maxLines - 1] = `${last.slice(0, Math.max(1, limit - 1))}…`;
    return kept;
  }
  return lines.length ? lines : [text];
}

function outlineKey(parentId: string, label: string, index: number): string {
  const slug = label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `${parentId}/${slug || "node"}-${index}`;
}

function collectParentKeys(
  nodes: KnowledgeGraphMindNode[],
  parentId: string,
  depth = 1,
  out: string[] = [],
): string[] {
  nodes.forEach((node, index) => {
    const id = outlineKey(parentId, node.label, index);
    if (depth < OUTLINE_MAX_DEPTH && node.children?.length) {
      out.push(id);
      collectParentKeys(node.children, id, depth + 1, out);
    }
  });
  return out;
}

function buildOutlineCard(
  node: KnowledgeGraphMindNode,
  depth: number,
  color: string,
  index: number,
  parent: OutlineCard | null,
  id: string,
  collapsed: Set<string>,
): OutlineCard {
  const lines = wrapOutlineLabel(node.label, OUTLINE_LIMITS[depth] || 20);
  const isCollapsed = collapsed.has(id);
  const hidden = depth >= OUTLINE_MAX_DEPTH || isCollapsed ? descendantCount(node) : 0;
  const height = lines.length * (OUTLINE_LINE_HEIGHT[depth] || 16) + 14 + (hidden ? 12 : 0);
  const card: OutlineCard = {
    node,
    id,
    collapsed: isCollapsed,
    depth,
    color,
    index,
    parent,
    lines,
    width: OUTLINE_WIDTHS[depth] || 180,
    height,
    x: OUTLINE_X[depth] || 800,
    y: 0,
    subtree: height,
    hidden,
    children: [],
  };
  if (depth < OUTLINE_MAX_DEPTH && !isCollapsed && node.children?.length) {
    card.children = node.children.map((child, childIndex) =>
      buildOutlineCard(
        child,
        depth + 1,
        color,
        childIndex,
        card,
        outlineKey(id, child.label, childIndex),
        collapsed,
      ),
    );
  }
  return card;
}

function measureOutline(card: OutlineCard): number {
  if (!card.children.length) {
    card.subtree = card.height;
    return card.subtree;
  }
  card.children.forEach(measureOutline);
  const childrenHeight =
    card.children.reduce((sum, child) => sum + child.subtree, 0) +
    OUTLINE_V_GAP * Math.max(0, card.children.length - 1);
  card.subtree = Math.max(card.height, childrenHeight);
  return card.subtree;
}

function placeOutline(card: OutlineCard, top: number): void {
  if (card.children.length) {
    const childrenHeight =
      card.children.reduce((sum, child) => sum + child.subtree, 0) +
      OUTLINE_V_GAP * Math.max(0, card.children.length - 1);
    let cursor = top + (card.subtree - childrenHeight) / 2;
    card.children.forEach((child) => {
      placeOutline(child, cursor);
      cursor += child.subtree + OUTLINE_V_GAP;
    });
    card.y = (card.children[0].y + card.children[card.children.length - 1].y) / 2;
  } else {
    card.y = top + card.height / 2;
  }
}

function layoutOutline(
  branches: KnowledgeGraphMindNode[],
  title: string,
  rootPrefix: string,
  collapsed: Set<string>,
) {
  const cards = branches.map((node, index) =>
    buildOutlineCard(
      node,
      1,
      MIND_COLORS[index % MIND_COLORS.length],
      index,
      null,
      outlineKey(rootPrefix, node.label, index),
      collapsed,
    ),
  );
  cards.forEach(measureOutline);
  const branchesHeight = cards.length
    ? cards.reduce((sum, card) => sum + card.subtree, 0) +
      OUTLINE_BRANCH_GAP * Math.max(0, cards.length - 1)
    : 0;
  const rootLines = wrapOutlineLabel(title, OUTLINE_LIMITS[0], 4);
  const rootHeight = 20 + rootLines.length * OUTLINE_LINE_HEIGHT[0] + 18 + 14;
  const canvasHeight = Math.max(520, branchesHeight + OUTLINE_MARGIN * 2, rootHeight + OUTLINE_MARGIN * 2);
  let cursor = (canvasHeight - branchesHeight) / 2;
  cards.forEach((card) => {
    placeOutline(card, cursor);
    cursor += card.subtree + OUTLINE_BRANCH_GAP;
  });
  const rootY = cards.length
    ? (cards[0].y + cards[cards.length - 1].y) / 2
    : canvasHeight / 2;
  let rightEdge = OUTLINE_X[0] + OUTLINE_WIDTHS[0];
  const walkRight = (item: OutlineCard) => {
    rightEdge = Math.max(rightEdge, item.x + item.width);
    item.children.forEach(walkRight);
  };
  cards.forEach(walkRight);
  return {
    cards,
    rootLines,
    rootHeight,
    rootY,
    canvasHeight,
    canvasWidth: Math.max(OUTLINE_W, rightEdge + 10),
    rootX: OUTLINE_X[0],
    rootWidth: OUTLINE_WIDTHS[0],
  };
}

function fallbackMindBranches(topic: KnowledgeGraphTopic): KnowledgeGraphMindNode[] {
  return buildMindGroups(topic).map((group) => ({
    label: group.label,
    children: group.concepts.map((concept) => ({
      label: concept.name,
      concept_id: concept.concept_id,
      concept_name: concept.name,
    })),
  }));
}

function countTreeNodes(nodes: KnowledgeGraphMindNode[]): number {
  return nodes.reduce((sum, node) => sum + 1 + countTreeNodes(node.children || []), 0);
}

const TOPIC_ZOOM = 1;

function centeredView(width: number, height: number, scale = TOPIC_ZOOM) {
  return {
    scale,
    tx: (width - width * scale) / 2,
    ty: (height - height * scale) / 2,
  };
}

function TopicMindMap({
  topic,
  selectedConceptId,
  onSelectConcept,
  onBack,
}: {
  topic: KnowledgeGraphTopic;
  selectedConceptId: string | null;
  onSelectConcept: (id: string) => void;
  onBack: () => void;
}) {
  const { t } = useLanguage();
  const fallbackBranches = useMemo(
    () => (topic.mindmap?.children?.length ? [] : fallbackMindBranches(topic)),
    [topic],
  );
  const treeBranches = topic.mindmap?.children?.length
    ? topic.mindmap.children
    : fallbackBranches;
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const parentKeys = useMemo(
    () => collectParentKeys(treeBranches, topic.code),
    [treeBranches, topic.code],
  );
  const allCollapsed = parentKeys.length > 0 && parentKeys.every((key) => collapsed.has(key));
  const outline = useMemo(
    () => layoutOutline(treeBranches, topic.title_en, topic.code, collapsed),
    [treeBranches, topic.title_en, topic.code, collapsed],
  );
  useEffect(() => {
    setCollapsed(new Set());
  }, [topic.code]);
  const toggleCollapsed = (id: string) => {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const toggleAll = () => {
    setCollapsed(allCollapsed ? new Set() : new Set(parentKeys));
  };
  const outlineCards = useMemo(() => {
    const flat: OutlineCard[] = [];
    const walk = (card: OutlineCard) => {
      flat.push(card);
      card.children.forEach(walk);
    };
    outline.cards.forEach(walk);
    return flat;
  }, [outline]);
  const treeNodeCount = topic.mindmap?.node_count ?? countTreeNodes(treeBranches);
  const treeMatchedCount = topic.mindmap?.matched_count ?? topic.concepts.length;
  const canvas = { w: outline.canvasWidth, h: outline.canvasHeight, cx: outline.canvasWidth / 2, cy: outline.canvasHeight / 2 };
  const [view, setView] = useState(() => centeredView(canvas.w, canvas.h));
  const [dragging, setDragging] = useState(false);
  const viewRef = useRef(view);
  const dragRef = useRef<{
    startX: number;
    startY: number;
    tx: number;
    ty: number;
    moved: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    viewRef.current = view;
  }, [view]);

  useEffect(() => {
    setView(centeredView(canvas.w, canvas.h));
  }, [topic.code, canvas.w, canvas.h]);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const scroller = svg.closest("[data-graph-scroll]") as HTMLElement | null;
    if (!scroller) return;
    const frame = window.requestAnimationFrame(() => {
      const scale = svg.clientHeight / Math.max(1, canvas.h);
      const topCard = Math.min(
        ...outline.cards.map((card) => card.y - card.height / 2),
        outline.rootY - outline.rootHeight / 2,
      );
      scroller.scrollTop = Math.max(0, topCard * scale - 18);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [topic.code, outline.rootY, canvas.h]);

  const clampView = (next: { scale: number; tx: number; ty: number }) => {
    const scale = clamp(next.scale, 1, 3.2);
    if (scale <= 1.001) {
      return {
        scale: 1,
        tx: clamp(next.tx, -canvas.w * 0.2, canvas.w * 0.2),
        ty: clamp(next.ty, -canvas.h * 0.2, canvas.h * 0.2),
      };
    }
    return {
      scale,
      tx: clamp(next.tx, canvas.w - canvas.w * scale - 18, 18),
      ty: clamp(next.ty, canvas.h - canvas.h * scale - 18, 18),
    };
  };

  const zoom = (factor: number) => {
    setView((current) => {
      const nextScale = clamp(current.scale * factor, 1, 3.2);
      const ratio = nextScale / current.scale;
      return clampView({
        scale: nextScale,
        tx: canvas.w / 2 - (canvas.w / 2 - current.tx) * ratio,
        ty: canvas.h / 2 - (canvas.h / 2 - current.ty) * ratio,
      });
    });
  };

  const fit = () => setView(centeredView(canvas.w, canvas.h));

  useEffect(() => {
    const move = (event: PointerEvent) => {
      const drag = dragRef.current;
      const svg = svgRef.current;
      if (!drag || !svg) return;
      const matrix = svg.getScreenCTM();
      if (!matrix) return;
      const dx = (event.clientX - drag.startX) / matrix.a;
      const dy = (event.clientY - drag.startY) / matrix.d;
      if (Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) > 3) {
        drag.moved = true;
      }
      if (drag.moved) {
        setView((current) => clampView({ scale: current.scale, tx: drag.tx + dx, ty: drag.ty + dy }));
      }
    };
    const end = () => {
      if (!dragRef.current) return;
      if (dragRef.current.moved) {
        suppressClickRef.current = true;
        setTimeout(() => { suppressClickRef.current = false; }, 240);
      }
      dragRef.current = null;
      setDragging(false);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
    };
  }, []);

  const renderLinks = (parent: OutlineCard | null, children: OutlineCard[]) => {
    if (!children.length) return null;
    const parentRight = parent ? parent.x + parent.width : outline.rootX + outline.rootWidth;
    const parentY = parent ? parent.y : outline.rootY;
    const color = children[0]?.color || "var(--line-strong)";
    if (children.length === 1) {
      const child = children[0];
      const mid = (parentRight + child.x) / 2;
      return (
        <path
          key={`link-single-${parent?.node.label || "root"}`}
          d={`M ${parentRight} ${parentY} C ${mid} ${parentY} ${mid} ${child.y} ${child.x} ${child.y}`}
          className={styles.outlineConnector}
          style={{ stroke: color }}
        />
      );
    }
    const firstY = Math.min(...children.map((child) => child.y));
    const lastY = Math.max(...children.map((child) => child.y));
    const busX = Math.min(parentRight + OUTLINE_TRUNK_GAP, children[0].x - 8);
    return (
      <g key={`links-${parent?.node.label || "root"}`}>
        <path
          d={`M ${parentRight} ${parentY} H ${busX}`}
          className={styles.outlineConnector}
          style={{ stroke: color }}
        />
        <path
          d={`M ${busX} ${firstY} V ${lastY}`}
          className={styles.outlineConnector}
          style={{ stroke: color }}
        />
        {children.map((child) => (
          <path
            key={`stub-${child.depth}-${child.y}-${child.node.label}`}
            d={`M ${busX} ${child.y} H ${child.x}`}
            className={styles.outlineConnector}
            style={{ stroke: color }}
          />
        ))}
      </g>
    );
  };

  const renderCard = (card: OutlineCard) => {
    const selected = Boolean(card.node.concept_id && card.node.concept_id === selectedConceptId);
    const clickable = Boolean(card.node.concept_id);
    const lineHeight = OUTLINE_LINE_HEIGHT[card.depth] || 16;
    const top = card.y - card.height / 2;
    const firstBaseline = top + 7 + lineHeight * 0.72;
    const textX = card.x + 10;
    const labelClass =
      card.depth === 1
        ? styles.outlineL1Label
        : card.depth === 2
          ? styles.outlineL2Label
          : styles.outlineL3Label;
    const handleClick = () => {
      if (suppressClickRef.current || !card.node.concept_id) return;
      onSelectConcept(card.node.concept_id);
    };
    return (
      <g
        key={`card-${card.depth}-${card.x}-${card.y}-${card.node.label}`}
        style={{ "--branch": card.color } as CSSProperties}
        className={cx(
          styles.outlineCardGroup,
          clickable && styles.outlineClickable,
          selected && styles.outlineSelected,
        )}
        role={clickable ? "button" : undefined}
        tabIndex={clickable ? 0 : undefined}
        aria-label={clickable ? `${card.node.label}${card.node.concept_name ? `, ${card.node.concept_name}` : ""}` : undefined}
        onClick={clickable ? handleClick : undefined}
        onKeyDown={
          clickable
            ? (event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  handleClick();
                }
              }
            : undefined
        }
      >
        <title>{card.node.label}{card.node.concept_name ? ` · ${card.node.concept_name}` : ""}</title>
        <rect
          x={card.x}
          y={top}
          width={card.width}
          height={card.height}
          rx={9}
          className={cx(
            styles.outlineCard,
            card.depth === 1 && styles.outlineBranchCard,
            card.depth === 2 && styles.outlineSubCard,
            selected && styles.outlineCardSelected,
          )}
        />
        {card.depth > 1 && (
          <rect
            x={card.x + 1}
            y={top + 5}
            width={3}
            height={Math.max(8, card.height - 10)}
            rx={1.5}
            className={styles.outlineAccentBar}
          />
        )}
        <text
          x={textX}
          className={cx(styles.outlineLabel, labelClass)}
        >
          {card.lines.map((line, index) => (
            <tspan key={`${line}-${index}`} x={textX} y={firstBaseline + index * lineHeight}>
              {line}
            </tspan>
          ))}
        </text>
        {card.hidden > 0 && (
          <g
            className={styles.outlineMoreGroup}
            role="button"
            tabIndex={0}
            aria-label={`Expand ${card.hidden} hidden nodes under ${card.node.label}`}
            onClick={(event) => {
              event.stopPropagation();
              toggleCollapsed(card.id);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                event.stopPropagation();
                toggleCollapsed(card.id);
              }
            }}
          >
            <text
              x={card.x + card.width - 8}
              y={top + card.height - 6}
              textAnchor="end"
              className={styles.outlineMore}
            >
              +{card.hidden} more
            </text>
          </g>
        )}
        {card.depth < OUTLINE_MAX_DEPTH && Boolean(card.node.children?.length) && (
          <g
            className={styles.outlineToggle}
            role="button"
            tabIndex={0}
            aria-expanded={!card.collapsed}
            aria-label={`${card.collapsed ? "Expand" : "Collapse"} ${card.node.label}`}
            onPointerDown={(event) => event.stopPropagation()}
            onClick={(event) => {
              event.stopPropagation();
              toggleCollapsed(card.id);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                event.stopPropagation();
                toggleCollapsed(card.id);
              }
            }}
          >
            <circle cx={card.x - 10} cy={card.y} r={8} />
            <text x={card.x - 10} y={card.y + 3.5} textAnchor="middle">
              {card.collapsed ? "+" : "−"}
            </text>
          </g>
        )}
      </g>
    );
  };

  const rootTop = outline.rootY - outline.rootHeight / 2;
  const rootCenterX = outline.rootX + outline.rootWidth / 2;

  return (
    <>
      <div className={styles.mindTop}>
        <button type="button" className={styles.stageBack} onClick={onBack} aria-label="Back to Unit structure">
          <ArrowLeft size={13} /> {t("返回结构图")}
        </button>
        <div className={styles.mindTools} role="group" aria-label="Mind map zoom controls">
          <button type="button" className={styles.mindTool} onClick={() => zoom(0.8)} aria-label="Zoom out">−</button>
          <span className={styles.mindZoom}>{Math.round(view.scale * 100)}%</span>
          <button type="button" className={styles.mindTool} onClick={() => zoom(1.25)} aria-label="Zoom in">+</button>
          <button type="button" className={cx(styles.mindTool, styles.mindFit)} onClick={toggleAll}>
            {allCollapsed ? "Expand" : "Collapse"}
          </button>
          <button type="button" className={cx(styles.mindTool, styles.mindFit)} onClick={fit}>Fit</button>
        </div>
      </div>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${canvas.w} ${canvas.h}`}
        role="img"
        aria-label={`${topic.code} ${topic.title_en} mind map`}
        className={cx(styles.mindSvg, dragging && styles.mindDragging)}
        onPointerDown={(event) => {
          if (event.button !== 0) return;
          const current = viewRef.current;
          dragRef.current = { startX: event.clientX, startY: event.clientY, tx: current.tx, ty: current.ty, moved: false };
          setDragging(true);
        }}
        onWheel={(event) => {
          if (!event.ctrlKey && !event.metaKey) return;
          event.preventDefault();
          zoom(event.deltaY < 0 ? 1.12 : 1 / 1.12);
        }}
      >
        <g transform={`translate(${view.tx.toFixed(2)} ${view.ty.toFixed(2)}) scale(${view.scale.toFixed(3)})`}>
          <rect
            x={outline.rootX}
            y={rootTop}
            width={outline.rootWidth}
            height={outline.rootHeight}
            rx={16}
            className={styles.outlineRootCard}
          />
          <text x={rootCenterX} y={rootTop + 18} textAnchor="middle" className={styles.outlineRootCode}>
            {topic.code}
          </text>
          {outline.rootLines.map((line, index) => (
            <text
              key={`${line}-${index}`}
              x={rootCenterX}
              y={rootTop + 40 + index * OUTLINE_LINE_HEIGHT[0]}
              textAnchor="middle"
              className={styles.outlineRootTitle}
            >
              {line}
            </text>
          ))}
          <text
            x={rootCenterX}
            y={rootTop + outline.rootHeight - 10}
            textAnchor="middle"
            className={styles.outlineRootCount}
          >
            {treeNodeCount} nodes · {treeMatchedCount} concepts
          </text>
          {renderLinks(null, outline.cards)}
          {outlineCards.filter((card) => card.children.length).map((card) => renderLinks(card, card.children))}
          {outlineCards.map(renderCard)}
        </g>
      </svg>
    </>
  );
}

function UnitInspector({
  unit,
  onOpenTopic,
}: {
  unit: KnowledgeGraphUnit;
  onOpenTopic: (topic: KnowledgeGraphTopic) => void;
}) {
  const { t } = useLanguage();
  return (
    <>
      <div className={styles.inspectorHead}>
        <div className={styles.eyebrow}>Unit {unit.unit_id} · Structure</div>
        <h2 className={styles.inspectorTitle}>{unit.title_en}</h2>
        <div className={styles.chips}>
          <span className={cx(styles.chip, styles.core)}>{unit.topic_count} topics</span>
          <span className={styles.chip}>{unit.concept_count} concepts</span>
          <span className={styles.chip}>{unit.question_count} practice Qs</span>
        </div>
      </div>
      <section className={styles.section}>
        <div className={styles.sectionLabel}>How to use <span>{t("先把结构看懂")}</span></div>
        <p className={styles.definition}>
          {t("这是按已解锁 Unit 生成的知识图谱。默认只展示 Topic 结构和每个 Topic 的 3 个核心概念；")}{" "}
          {t("点击 Topic 节点查看内部概念图，再点概念查看定义、关系和关联题目。")}
        </p>
      </section>
      <section className={styles.section}>
        <div className={styles.sectionLabel}>Topics <span>{unit.topics?.length || 0}</span></div>
        <div className={styles.topicList}>
          {(unit.topics || []).map((topic) => (
            <button key={topic.topic_id} type="button" className={styles.topicRow} onClick={() => onOpenTopic(topic)}>
              <span className={styles.code}>{topic.code}</span>
              <span className={styles.name}>{topic.title_en}</span>
              <span className={styles.count}>{topic.concept_count}</span>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

function TopicInspector({
  unit,
  topic,
  onOpenConcept,
}: {
  unit: KnowledgeGraphUnit;
  topic: KnowledgeGraphTopic;
  onOpenConcept: (conceptId: string) => void;
}) {
  const { t } = useLanguage();
  return (
    <>
      <div className={styles.inspectorHead}>
        <div className={styles.eyebrow}>Unit {unit.unit_id} · Topic {topic.code}</div>
        <h2 className={styles.inspectorTitle}>{topic.title_en}</h2>
        <div className={styles.chips}>
          <span className={cx(styles.chip, styles.core)}>{topic.concept_count} concepts</span>
          <span className={styles.chip}>{topic.question_count} questions</span>
        </div>
      </div>
      <section className={styles.section}>
        <div className={styles.topicCard}>
          <div className={styles.eyebrow}>{topic.code} · Topic</div>
          <h3>{topic.title_en}</h3>
          <p>{t("点击导图中的英文概念节点查看定义、关系和关联题目。返回结构图请用导图左上角按钮。")}</p>
        </div>
      </section>
      <section className={styles.section}>
        <div className={styles.sectionLabel}>Concepts <span>{t("按权重排序")}</span></div>
        <div className={styles.conceptList}>
          {topic.concepts.map((concept) => (
            <button key={concept.concept_id} type="button" className={styles.conceptRow} onClick={() => onOpenConcept(concept.concept_id)}>
              <span className={styles.tier}>{concept.tier === "core" ? "C" : "S"}</span>
              <span className={styles.name}>{concept.name}</span>
              <span className={styles.count}>{concept.questions.total}</span>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

function ConceptInspector({
  unit,
  topic,
  concept,
  onOpenConcept,
  onBackTopic,
  onPreviewQuestion,
}: {
  unit: KnowledgeGraphUnit;
  topic: KnowledgeGraphTopic;
  concept: KnowledgeGraphConcept;
  onOpenConcept: (topicCode: string, conceptId: string) => void;
  onBackTopic: () => void;
  onPreviewQuestion: (questionId: string, sample?: KnowledgeGraphSample) => void;
}) {
  const { t } = useLanguage();
  const lookup = useMemo(() => conceptIndex(unit), [unit]);
  const rows = relationRows(concept, lookup);
  return (
    <>
      <div className={styles.inspectorHead}>
        <div className={styles.eyebrow}>Unit {unit.unit_id} · {topic.code}</div>
        <h2 className={styles.inspectorTitle}>{concept.name}</h2>
        <div className={styles.chips}>
          <span className={cx(styles.chip, concept.tier === "core" ? styles.core : styles.accent)}>{concept.tier}</span>
          <span className={styles.chip}>{concept.questions.total} questions</span>
          <span className={styles.chip}>{t("{n} 易混", { n: concept.contrast.length })}</span>
          {concept.supplement && (
            <span className={styles.chip}>
              {concept.supplement_source === "admin" ? "Admin supplement" : "AI supplement"}
            </span>
          )}
        </div>
      </div>

      <section className={styles.section}>
        <div className={styles.sectionLabel}>Definition <span>{concept.book}</span></div>
        <p className={styles.definition}>{concept.definition || t("暂无定义。")}</p>
        {concept.quote && concept.quote !== concept.definition && (
          <blockquote className={styles.quote}>“{concept.quote}”</blockquote>
        )}
        <div className={styles.source}>
          {concept.section}{concept.section && concept.book ? " · " : ""}{concept.book}
        </div>
        {concept.supplement && (
          <div className={styles.supplementNote}>
            {concept.supplement_source === "admin"
              ? "Editor-written explanation · review against the 2027 textbook"
              : "AI-assisted explanation · review against the 2027 textbook"}
          </div>
        )}
      </section>

      <section className={styles.section}>
        <div className={styles.sectionLabel}>{t("教材关系")} <span>{t("{n} 条", { n: rows.length })}</span></div>
        {rows.length ? (
          <div className={styles.relationList}>
            {rows.map((relation) => (
              <button
                key={`${relation.id}-${relation.type}-${relation.direction}`}
                type="button"
                className={styles.relationRow}
                disabled={!relation.exists}
                onClick={() => {
                  if (relation.exists) onOpenConcept(lookup.get(relation.id)!.topic.code, relation.id);
                }}
              >
                <span className={styles.relLabel}>{relation.label || t(RELATION_LABELS[relation.type] || "相关")}</span>
                <span className={styles.relName}>{relation.name}</span>
                <span className={styles.relMeta}>{relation.confidence ? `${Math.round(relation.confidence * 100)}%` : ""}</span>
                {relation.evidence && <span className={styles.relEvidence}>{relation.evidence}</span>}
              </button>
            ))}
          </div>
        ) : (
          <div className={styles.empty}>{t("暂无教材显式关系。")}</div>
        )}
      </section>

      <section className={styles.section}>
        <div className={styles.sectionLabel}>{t("真题易混")} <span>{t("来自同题正确项 / 干扰项")}</span></div>
        {concept.contrast.length ? (
          <div className={styles.relationList}>
            {concept.contrast.map((relation) => {
              return (
                <button
                  key={relation.id}
                  type="button"
                  className={styles.relationRow}
                  disabled={!relation.questions[0]}
                  onClick={() => {
                    const sample = relation.questions[0];
                    if (sample) onPreviewQuestion(sample.question_id, sample);
                  }}
                >
                  <span className={styles.relLabel}>{t("易混")}</span>
                  <span className={styles.relName}>{relation.name}</span>
                  <span className={styles.relMeta}>×{relation.weight}</span>
                  {relation.questions[0] && (
                    <span className={styles.relEvidence}>
                      {relation.questions[0].paper} · Q{relation.questions[0].number}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ) : (
          <div className={styles.empty}>{t("暂无真题层面的易混记录。")}</div>
        )}
      </section>

      <section className={styles.section}>
        <div className={styles.sectionLabel}>Related Questions <span>{t("按概念角色分组")}</span></div>
        <div className={styles.chips} style={{ marginBottom: 8 }}>
          <span className={styles.chip}><b>{concept.questions.core}</b> core</span>
          <span className={styles.chip}><b>{concept.questions.supporting}</b> supporting</span>
          <span className={styles.chip}><b>{concept.questions.confusable}</b> confusable</span>
        </div>
        {concept.samples.length ? (
          <>
            <div className={styles.questionPicker} role="group" aria-label="Related question previews">
              {concept.samples.map((sample, index) => (
                <button
                  key={`${sample.question_id}-${sample.role}`}
                  type="button"
                  className={styles.questionNumber}
                  title={`${sample.paper} · Q${sample.number}${sample.role ? ` · ${t(ROLE_LABELS[sample.role] || sample.role)}` : ""}`}
                  aria-label={`Question ${index + 1}: ${sample.paper} Q${sample.number}`}
                  onClick={() => onPreviewQuestion(sample.question_id, sample)}
                >
                  {index + 1}
                </button>
              ))}
            </div>
            <p className={styles.questionHint}>{t("点击题号，只读查看题目")}</p>
          </>
        ) : (
          <div className={styles.empty}>{t("暂无直接关联题目。")}</div>
        )}
        <div className={styles.actions}>
          <button type="button" className={styles.ghostAction} onClick={onBackTopic}>
            <ArrowLeft size={13} /> {t("返回 Topic")}
          </button>
        </div>
      </section>
    </>
  );
}

export function KnowledgeGraph({ unit }: { unit: KnowledgeGraphUnit }) {
  const { t } = useLanguage();
  const [topicCode, setTopicCode] = useState<string | null>(null);
  const [conceptId, setConceptId] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewQuestion, setPreviewQuestion] = useState<Question | null>(null);
  const [previewMeta, setPreviewMeta] = useState<KnowledgeGraphSample | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const graphScrollRef = useRef<HTMLDivElement | null>(null);

  const topic = topicCode ? unit.topics?.find((item) => item.code === topicCode) || null : null;
  const lookup = useMemo(() => conceptIndex(unit), [unit]);
  const selected = useMemo(() => {
    if (!conceptId) return null;
    const currentConcept = topic?.concepts.find((concept) => concept.concept_id === conceptId);
    if (topic && currentConcept) return { topic, concept: currentConcept };
    const extra = unit.mindmap_concepts?.[conceptId];
    if (topic && extra) return { topic, concept: extra };
    return lookup.get(conceptId) || null;
  }, [conceptId, topic, lookup, unit.mindmap_concepts]);

  useEffect(() => {
    const element = graphScrollRef.current;
    if (!element) return;
    const frame = window.requestAnimationFrame(() => {
      element.scrollLeft = Math.max(0, (element.scrollWidth - element.clientWidth) / 2);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [topicCode, unit.unit_id, fullscreen]);

  useEffect(() => {
    if (!fullscreen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !previewOpen) setFullscreen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [fullscreen, previewOpen]);

  function openTopic(nextTopic: KnowledgeGraphTopic, nextConceptId?: string) {
    setTopicCode(nextTopic.code);
    setConceptId(nextConceptId || null);
  }

  function openConcept(nextTopicCode: string, nextConceptId: string) {
    setTopicCode(nextTopicCode);
    setConceptId(nextConceptId);
  }

  function selectConcept(nextConceptId: string) {
    setConceptId((current) => (current === nextConceptId ? null : nextConceptId));
  }

  function openQuestionPreview(questionId: string, sample?: KnowledgeGraphSample) {
    setPreviewOpen(true);
    setPreviewMeta(sample || null);
    setPreviewQuestion(null);
    setPreviewError(null);
    setPreviewLoading(true);
    apiGet<Question>(`/knowledge-graph/questions/${encodeURIComponent(questionId)}`)
      .then((question) => setPreviewQuestion(question))
      .catch((error: Error) => setPreviewError(error.message))
      .finally(() => setPreviewLoading(false));
  }

  function closePreview() {
    setPreviewOpen(false);
    setPreviewQuestion(null);
    setPreviewError(null);
    setPreviewMeta(null);
  }

  return (
    <div className={styles.layout}>
      <div className={cx(styles.graphCard, fullscreen && styles.fullscreenGraph)}>
        <div className={styles.graphBar}>
          <div className={styles.graphMeta}>
            <strong>{topic ? `${topic.code} · ${topic.title_en}` : `Unit ${unit.unit_id} · Structure`}</strong>
            <span>
              {topic
                ? `${topic.mindmap?.node_count ?? topic.concept_count} nodes · ${topic.mindmap?.matched_count ?? topic.concept_count} concepts · XMind`
                : `${unit.topic_count} topics · ${unit.concept_count} concepts · ${unit.bridges?.length || 0} bridges`}
            </span>
          </div>
          <div className={styles.barActions}>
            <button
              type="button"
              className={styles.fullscreenBtn}
              onClick={() => setFullscreen((current) => !current)}
              aria-label={fullscreen ? t("退出全屏") : t("全屏查看知识图谱")}
              title={fullscreen ? t("退出全屏（Esc）") : t("全屏查看")}
            >
              {fullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
              <span>{fullscreen ? t("退出全屏") : t("全屏")}</span>
            </button>
            <span className={styles.mobileHint}>{t("左右滑动查看完整图")}</span>
            <span className={styles.hint}>{topic ? "Drag to pan · Ctrl + wheel to zoom · click a concept" : "Click a Topic to open its mind map"}</span>
          </div>
        </div>
        <div className={cx(styles.graphScroll, topic && styles.graphScrollTree)} ref={graphScrollRef} data-graph-scroll>
          <div className={cx(styles.stage, topic && styles.stageMind, !topic && styles.stageStructure)}>
            {topic ? (
              <TopicMindMap
                topic={topic}
                selectedConceptId={conceptId}
                onSelectConcept={selectConcept}
                onBack={() => { setTopicCode(null); setConceptId(null); }}
              />
            ) : (
              <StructureGraph unit={unit} onOpenTopic={openTopic} />
            )}
          </div>
        </div>
        <div className={styles.graphFoot}>
          <div className={styles.keys}>
            <span className={styles.key}><span className={styles.keyDot} /> core</span>
            <span className={styles.key}><span className={cx(styles.keyDot, styles.supporting)} /> supporting</span>
            {topic ? (
              <span className={styles.key}>concept = click to inspect</span>
            ) : (
              <>
                <span className={styles.key}><span className={styles.keyLine} /> {t("教材关系")}</span>
                <span className={styles.key}><span className={cx(styles.keyLine, styles.contrast)} /> {t("真题易混")}</span>
              </>
            )}
          </div>
          <span>{topic ? `${topic.mindmap?.node_count ?? topic.concept_count} nodes · XMind mind map` : t("Unit 级先看结构，Topic 级进入思维导图")}</span>
        </div>
      </div>

      <aside className={styles.inspector} aria-live="polite">
        {selected ? (
          <ConceptInspector
            unit={unit}
            topic={selected.topic}
            concept={selected.concept}
            onOpenConcept={openConcept}
            onBackTopic={() => { setConceptId(null); }}
            onPreviewQuestion={openQuestionPreview}
          />
        ) : topic ? (
          <TopicInspector
            unit={unit}
            topic={topic}
            onOpenConcept={(id) => setConceptId(id)}
          />
        ) : (
          <UnitInspector unit={unit} onOpenTopic={openTopic} />
        )}
      </aside>

      <Modal
        open={previewOpen}
        onClose={closePreview}
        title={previewMeta ? `${previewMeta.paper} · Q${previewMeta.number}` : "Question preview"}
        wide
      >
        <div className="mb-3 rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-[11px] muted">
          {t("只读预览 · 不记录作答 · 题目来自当前知识图谱关联")}
        </div>
        {previewLoading && <div className="skeleton h-40 w-full" />}
        {previewError && <div className="feedback feedback-bad">{previewError}</div>}
        {previewQuestion && (
          <QuestionView
            question={previewQuestion}
            onSelect={() => undefined}
            disabled
            readOnly
          />
        )}
      </Modal>
    </div>
  );
}
