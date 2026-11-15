import type { Metadata } from "next";
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  FileText,
  Layers,
  Network,
} from "lucide-react";
import Link from "next/link";

import { LandingCountdown } from "@/components/LandingCountdown";
import { brand } from "@/config/brand";
import { FlashcardStudy } from "@/components/FlashcardStudy";
import { LandingSampleQuestion } from "@/components/LandingSampleQuestion";

export const metadata: Metadata = {
  title: `${brand.name} · AP Psychology 2027`,
  description:
    `${brand.name}（${brand.domain}）AP Psychology 单元练习、真题、知识图谱、错题本和记忆卡片。先免费体验 Unit 1，按 CED 的 Unit/Topic 组织练习。`,
  openGraph: {
    title: `${brand.name} · AP Psychology 2027`,
    description:
      `${brand.name}（${brand.domain}）AP Psychology 单元练习、真题、知识图谱、错题本和记忆卡片。`,
    images: [
      {
        url: brand.logoFull,
        width: 512,
        height: 512,
        alt: brand.name,
      },
    ],
  },
};

const FEATURES = [
  {
    icon: BookOpen,
    title: "按 Unit 练习",
    description: "每个 Topic 即时判分，右侧同步显示本题概念和相关知识。",
  },
  {
    icon: FileText,
    title: "真题与模拟",
    description: "12 套真题与模拟，支持 MCQ、FRQ 和混合模式，考前练节奏。",
  },
  {
    icon: AlertCircle,
    title: "错题自动回炉",
    description: "答错自动进入错题本；连续答对两次才算真正掌握。",
  },
  {
    icon: Layers,
    title: "卡片反复记",
    description: "按概念权重出卡，Already Know / Review Later 控制下次出现时间。",
  },
];

const STEPS = [
  { number: "01", title: "选一个 Unit", description: "从 Unit 1 开始，也可以直接进某个 Topic。" },
  { number: "02", title: "做完看解析", description: "即时反馈、正确答案和本題概念一次看到。" },
  { number: "03", title: "错题 + 卡片回炉", description: "错题和到期的卡片会自动进入下一次复习。" },
];

const FAQ = [
  {
    question: "适合什么样的学生？",
    answer:
      "正在准备 AP Psychology、想按 CED 的 Unit/Topic 系统练习的人；也适合考试前冲刺、想快速提分，需要集中刷题和复盘错题的人。",
  },
  {
    question: "手机上能用吗？",
    answer:
      "可以。练习、真题、错题本和卡片都按手机屏幕适配，浏览器打开即可，不需要安装 App。",
  },
  {
    question: "FRQ 怎么练？",
    answer:
      "FRQ 交卷后按官方 rubric 逐项自评，显示评分标准和参考要点；适合在考前熟悉采分点。",
  },
  {
    question: "内容和考试大纲一致吗？",
    answer:
      "按最新 AP Psychology 考纲和 2027 教材整理，题目与解析覆盖最新 Unit/Topic 考点。",
  },
  {
    question: "知识图谱怎么用？",
    answer:
      "每张图先展示 Unit 结构，再进入章节思维导图。点概念可看定义、教材关系、真题易混和关联题目；图谱只展示账号已解锁的 Unit。",
  },
];

export default function LandingPage() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <div className="landing-nav-inner">
          <Link href="/" className="landing-brand">
            <img
              src={brand.logo}
              alt=""
              width={42}
              height={42}
              className="brand-logo landing-brand-logo"
            />
            <span>
              <span className="landing-brand-title">{brand.name}</span>
              <span className="landing-brand-sub">{brand.domain}</span>
            </span>
          </Link>

          <nav className="landing-links" aria-label="页面导航">
            <a href="#free">免费体验</a>
            <a href="#graph">知识图谱</a>
            <a href="#sample">做一道样题</a>
            <a href="#how">怎么练</a>
            <a href="#teacher">关于题库</a>
          </nav>

          <div className="landing-actions">
            <Link href="/login?next=/dashboard" className="btn btn-sm btn-ghost">
              登录
            </Link>
            <Link
              href="/login?mode=register&next=/dashboard"
              className="btn btn-sm btn-primary"
            >
              注册
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-hero-copy">
            <div className="eyebrow">{brand.name} · AP Psychology 2027</div>
            <h1 className="landing-title">
              把每个 Unit，
              <br />
              <span>练成自己的得分点。</span>
            </h1>
            <p className="landing-proof">
              <span>
                <strong>2,951</strong> 道 MCQ / FRQ，<strong>45</strong> 个 CED Topic，
                <strong>12</strong> 套真题与模拟。
              </span>
              <span>按 Unit 练习，错题自动回炉，考前只看自己真正薄弱的地方。</span>
            </p>

            <div className="landing-cta-row">
              <Link href="/dashboard" className="btn btn-primary">
                免费体验 Unit 1 <ArrowRight size={15} />
              </Link>
              <a href="#sample" className="btn">
                先做一道样题
              </a>
            </div>
            <p className="landing-note">邮箱登录 · 进度自动保存 · 从 Unit 1 开始</p>
            <p className="landing-focus-note">
              <span>Focus</span> 目前专注 AP Psychology，其他 AP 科目会在后续逐步加入。
            </p>
          </div>

          <div className="landing-preview">
            <div className="landing-preview-glow" aria-hidden="true" />
            <div className="landing-preview-card">
              <div className="flex items-center justify-between gap-3">
                <span className="eyebrow">Your practice room</span>
                <span className="pill pill-primary">2027</span>
              </div>

              <div className="landing-countdown">
                <span className="landing-countdown-label">距离考试</span>
                <LandingCountdown />
                <div className="landing-countdown-meta">
                  <span>2027.05.14</span>
                  <span>12:00 PM</span>
                  <span>AP Psychology</span>
                </div>
              </div>

              <div className="landing-preview-divider" />

              <div className="landing-preview-row">
                <span>Unit 1 · Biological Bases</span>
                <span className="font-mono text-[11px] text-[var(--primary)]">76%</span>
              </div>
              <div className="landing-bar">
                <span style={{ width: "76%" }} />
              </div>

              <div className="landing-preview-list">
                <div>
                  <CheckCircle2 size={15} className="text-[var(--primary)]" />
                  今日：错题 5 道
                </div>
                <div>
                  <Layers size={15} className="text-[var(--accent)]" />
                  卡片：12 张到期
                </div>
                <div>
                  <FileText size={15} className="text-[var(--muted)]" />
                  下一套：2018 真题
                </div>
              </div>

              <div className="landing-preview-foot">
                坚持 42 天 <span>·</span> 已答 1,204 题
              </div>
            </div>
          </div>
        </section>

        <section className="landing-stats" aria-label="内容规模">
          <div>
            <strong>5</strong>
            <span>Units</span>
          </div>
          <div>
            <strong>45</strong>
            <span>CED Topics</span>
          </div>
          <div>
            <strong>2,951</strong>
            <span>Questions</span>
          </div>
          <div>
            <strong>12</strong>
            <span>Exam papers</span>
          </div>
        </section>

        <section className="landing-section" id="free">
          <div className="landing-section-head">
            <div>
              <div className="eyebrow">Start here</div>
              <h2 className="landing-h2">先免费把 Unit 1 走一遍</h2>
            </div>
            <p>
              不用先做决定。先用 Unit 1 体验完整的练习闭环：做题、即时解析、概念栏、错题记录。
            </p>
          </div>

          <div className="landing-feature-grid">
            {FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <article key={feature.title} className="card card-pad landing-feature">
                  <span className="landing-feature-icon">
                    <Icon size={18} strokeWidth={1.8} />
                  </span>
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                </article>
              );
            })}
          </div>

          <div className="landing-inline-cta">
            <Link href="/dashboard" className="btn btn-primary btn-sm">
              从 Unit 1 开始 <ArrowRight size={14} />
            </Link>
            <span>先体验，再决定要不要继续。</span>
          </div>
        </section>

        <section className="landing-section" id="sample">
          <div className="landing-section-head">
            <div>
              <div className="eyebrow">Try one question</div>
              <h2 className="landing-h2">先做一道，看看解析。</h2>
            </div>
            <p>
              这是 Unit 1 的一道 MCQ。选完立即显示答案和解析，右侧同步看到本题相关知识点。
            </p>
          </div>
          <LandingSampleQuestion />
        </section>

        <section className="landing-section landing-graph-section" id="graph">
          <div className="landing-graph-grid">
            <div className="landing-graph-copy">
              <div className="eyebrow">Knowledge graph</div>
              <h2 className="landing-h2">知识点不是散落的卡片，<br />而是一张可以走进去的图。</h2>
              <p>
                从 Unit 结构，到每个 Topic 的章节思维导图，再到单个概念的定义、教材关系和真题易混。
                先看全局，再点进细节；不把一百多个点一次塞给你。
              </p>
              <ul className="landing-graph-points">
                <li>
                  <span>01</span>
                  <div><strong>Unit 结构</strong><small>先看这个 Unit 由哪些 Topic 组成，每个 Topic 只露出 3 个核心概念。</small></div>
                </li>
                <li>
                  <span>02</span>
                  <div><strong>章节思维导图</strong><small>XMind 风格，按教材章节展开；支持缩放、拖动和 Fit。</small></div>
                </li>
                <li>
                  <span>03</span>
                  <div><strong>知识点 + 题目</strong><small>教材关系、真题易混和 Related Questions 都在右侧；题目可只读预览。</small></div>
                </li>
              </ul>
              <div className="landing-cta-row">
                <Link href="/knowledge" className="btn btn-primary">
                  查看 Unit 1 图谱 <ArrowRight size={15} />
                </Link>
                <span className="landing-graph-note">按已解锁 Unit 显示 · Unit 1 免费</span>
              </div>
            </div>

            <div className="landing-graph-visual" aria-label="Knowledge graph preview">
              <div className="landing-graph-bar">
                <span><Network size={13} /> THE BRAIN · CHAPTER MAP</span>
                <span>XMind style</span>
              </div>
              <div className="landing-graph-canvas">
                <svg className="landing-graph-svg" viewBox="0 0 560 320" role="img" aria-label="Chapter mind map preview">
                  <path className="landing-kg-line left" d="M230 162 Q225 162 223 160" />
                  <path className="landing-kg-line right" d="M330 160 Q334 160 337 160" />
                  {[50, 90, 130, 170].map((y) => (
                    <path key={`l-${y}`} className="landing-kg-leaf-line left" d={`M143 160 C138 160 138 ${y} 136 ${y}`} />
                  ))}
                  {[50, 90, 130, 170].map((y) => (
                    <path key={`r-${y}`} className="landing-kg-leaf-line right" d={`M417 160 C422 160 422 ${y} 424 ${y}`} />
                  ))}

                  <rect x="230" y="136" width="100" height="48" rx="12" className="landing-kg-root" />
                  <text x="280" y="152" textAnchor="middle" className="landing-kg-code">1.4</text>
                  <text x="280" y="168" textAnchor="middle" className="landing-kg-root-title">The Brain</text>
                  <text x="280" y="178" textAnchor="middle" className="landing-kg-root-sub">20 concepts</text>

                  <rect x="143" y="145" width="80" height="30" rx="8" className="landing-kg-branch" />
                  <text x="183" y="157" textAnchor="middle" className="landing-kg-branch-title">Core content</text>
                  <text x="183" y="167" textAnchor="middle" className="landing-kg-branch-sub">16 concepts</text>

                  <rect x="337" y="145" width="80" height="30" rx="8" className="landing-kg-branch" />
                  <text x="377" y="157" textAnchor="middle" className="landing-kg-branch-title">Nervous system</text>
                  <text x="377" y="167" textAnchor="middle" className="landing-kg-branch-sub">2 concepts</text>

                  {[
                    ["Hypothalamus", 50, "Core content"],
                    ["Amygdala", 90, "Core content"],
                    ["Cerebellum", 130, "Core content"],
                    ["Limbic system", 170, "Core content"],
                  ].map(([label, y]) => (
                    <g key={label}>
                      <rect x="18" y={Number(y) - 11} width="118" height="22" rx="6" className="landing-kg-leaf" />
                      <rect x="19" y={Number(y) - 9} width="3" height="18" rx="1.5" className="landing-kg-leaf-accent" />
                      <text x="29" y={Number(y) + 3.5} className="landing-kg-leaf-title">{label}</text>
                    </g>
                  ))}
                  {[
                    ["Sympathetic NS", 50],
                    ["Parasympathetic", 90],
                    ["Neuroplasticity", 130],
                    ["Hippocampus", 170],
                  ].map(([label, y]) => (
                    <g key={label}>
                      <rect x="424" y={Number(y) - 11} width="118" height="22" rx="6" className="landing-kg-leaf" />
                      <rect x="425" y={Number(y) - 9} width="3" height="18" rx="1.5" className="landing-kg-leaf-accent" />
                      <text x="435" y={Number(y) + 3.5} className="landing-kg-leaf-title">{label}</text>
                    </g>
                  ))}
                </svg>
              </div>
              <div className="landing-graph-caption">
                <span>Unit 1 → 1.4 The Brain</span>
                <span>8 Topics · 197 concepts</span>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-section" id="how">
          <div className="landing-section-head">
            <div>
              <div className="eyebrow">The loop</div>
              <h2 className="landing-h2">练习 → 错题 → 卡片</h2>
            </div>
            <p>每次练习都会留下下一步：错了什么、哪些概念还没稳、下一次该复习什么。</p>
          </div>

          <div className="landing-steps">
            {STEPS.map((step) => (
              <div key={step.number} className="landing-step">
                <span className="landing-step-number">{step.number}</span>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="landing-section landing-teacher" id="teacher">
          <div className="landing-teacher-grid">
            <div className="landing-card-demo">
              <FlashcardStudy
                preview
                limit={20}
                compact
                showStats={false}
                showAllLink={false}
              />
            </div>

            <div className="card card-pad landing-teacher-card">
              <div>
                <div className="eyebrow">About this room</div>
                <h2 className="landing-h2">一个老师维护的练习室</h2>
                <p>
                  不是录播课，也不是把题目简单堆在一起。{brand.name} 的题目、解析和练习顺序
                  由一位 AP Psychology 老师持续维护：按 CED 的 Unit/Topic 拆开练，
                  做完马上看解析，错题自动进入错题本。
                </p>
                <p>
                  记忆卡片会按概念权重和复习间隔再次出现。练习路径已经排好：
                  Unit → 错题 → 卡片，跟着走就行。
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-section" id="faq">
          <div className="eyebrow">FAQ</div>
          <h2 className="landing-h2">常见问题</h2>
          <div className="landing-faq">
            {FAQ.map((item) => (
              <details key={item.question}>
                <summary>{item.question}</summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div>
          <strong>{brand.name}</strong> · {brand.domain}
        </div>
        <div>
          AP® 是 College Board 的注册商标；本站与 College Board 无隶属关系。
        </div>
        <div>
          <Link href="/login?next=/dashboard">登录</Link>
          <span className="mx-2">·</span>
          <Link href="/login?mode=register&next=/dashboard">注册</Link>
        </div>
      </footer>
    </div>
  );
}
