const messages: Record<string, string> = {
  // Navigation
  "页面导航": "Page navigation",
  "免费体验": "Free trial",
  "知识图谱": "Knowledge graph",
  "做一道样题": "Try a sample question",
  "怎么练": "How it works",
  "关于题库": "About the question bank",
  "登录": "Sign in",
  "注册": "Sign up",

  // Hero
  "把每个 Unit，": "Turn every Unit",
  "练成自己的得分点。": "into points on your score.",
  "道 MCQ / FRQ，": "MCQ / FRQ questions,",
  "个 CED Topic，": "CED Topics,",
  "套真题与模拟。": "practice exams and mocks.",
  "按 Unit 练习，错题自动回炉，考前只看自己真正薄弱的地方。":
    "Practice by Unit, with mistakes coming back automatically, so before the exam you focus only on what you're truly weak at.",
  "免费体验 Unit 1": "Try Unit 1 free",
  "先做一道样题": "Try a sample question first",
  "邮箱登录 · 进度自动保存 · 从 Unit 1 开始":
    "Email sign-in · Progress saved automatically · Start with Unit 1",
  "目前专注 AP Psychology，其他 AP 科目会在后续逐步加入。":
    "Currently focused on AP Psychology; other AP subjects will be added over time.",
  "距离考试": "Exam countdown",
  "今日：错题 5 道": "Today: 5 mistakes",
  "卡片：12 张到期": "Cards: 12 due",
  "下一套：2018 真题": "Next: 2018 exam",
  "坚持 42 天": "42-day streak",
  "已答 1,204 题": "1,204 questions answered",
  "内容规模": "Content overview",

  // Free Unit 1 section
  "先免费把 Unit 1 走一遍": "Walk through Unit 1 free",
  "不用先做决定。先用 Unit 1 体验完整的练习闭环：做题、即时解析、概念栏、错题记录。":
    "No need to decide yet. Use Unit 1 to experience the full practice loop: questions, instant explanations, the concept rail, and mistake tracking.",
  "按 Unit 练习": "Practice by Unit",
  "每个 Topic 即时判分，右侧同步显示本题概念和相关知识。":
    "Instant scoring for every Topic, with the question's concepts and related knowledge shown alongside.",
  "真题与模拟": "Past exams and mocks",
  "12 套真题与模拟，支持 MCQ、FRQ 和混合模式，考前练节奏。":
    "12 past exams and mocks with MCQ, FRQ, and mixed modes to practice exam pacing.",
  "错题自动回炉": "Mistakes come back automatically",
  "答错自动进入错题本；连续答对两次才算真正掌握。":
    "Wrong answers go straight into your mistake bank; two correct answers in a row count as mastered.",
  "卡片反复记": "Review with flashcards",
  "按概念权重出卡，Already Know / Review Later 控制下次出现时间。":
    "Cards are weighted by concept importance; Already Know / Review Later controls when each card returns.",
  "从 Unit 1 开始": "Start with Unit 1",
  "先体验，再决定要不要继续。": "Try it first, then decide whether to continue.",

  // Sample question section
  "先做一道，看看解析。": "Try one question and see the explanation.",
  "这是 Unit 1 的一道 MCQ。选完立即显示答案和解析，右侧同步看到本题相关知识点。":
    "This is an MCQ from Unit 1. Pick an answer to see the answer and explanation instantly, with related concepts shown on the right.",
  "即时解析": "Instant explanation",
  "正确": "Correct",
  "正确答案是 {label} · {concept}": "The correct answer is {label} · {concept}",
  "登录后继续做 Unit 1": "Sign in to continue Unit 1",
  "再试一次": "Try again",
  "概念分类": "Concept categories",
  "选完答案后，这里会显示本题的核心概念和易混概念。":
    "After you answer, this panel shows the core and confusable concepts from this question.",

  // Knowledge graph section
  "知识点不是散落的卡片，": "Knowledge isn't a pile of scattered cards,",
  "而是一张可以走进去的图。": "but a map you can step into.",
  "从 Unit 结构，到每个 Topic 的章节思维导图，再到单个概念的定义、教材关系和真题易混。":
    "From the Unit structure to each Topic's chapter mind map, down to a single concept's definition, textbook relationships, and exam confusions.",
  "先看全局，再点进细节；不把一百多个点一次塞给你。":
    "See the big picture first, then drill into details; we don't dump a hundred-plus nodes on you at once.",
  "Unit 结构": "Unit structure",
  "先看这个 Unit 由哪些 Topic 组成，每个 Topic 只露出 3 个核心概念。":
    "See which Topics make up the Unit, with only 3 core concepts shown per Topic.",
  "章节思维导图": "Chapter mind map",
  "XMind 风格，按教材章节展开；支持缩放、拖动和 Fit。":
    "XMind-style, organized by textbook chapter; supports zoom, drag, and Fit.",
  "知识点 + 题目": "Concepts + questions",
  "教材关系、真题易混和 Related Questions 都在右侧；题目可只读预览。":
    "Textbook relationships, exam confusions, and Related Questions sit on the right; questions can be previewed read-only.",
  "查看 Unit 1 图谱": "View the Unit 1 graph",
  "按已解锁 Unit 显示 · Unit 1 免费": "Shows unlocked Units only · Unit 1 is free",

  // Practice loop
  "练习 → 错题 → 卡片": "Practice → Mistakes → Cards",
  "每次练习都会留下下一步：错了什么、哪些概念还没稳、下一次该复习什么。":
    "Every practice session leaves you a next step: what you missed, which concepts are still shaky, and what to review next.",
  "选一个 Unit": "Pick a Unit",
  "从 Unit 1 开始，也可以直接进某个 Topic。":
    "Start with Unit 1, or jump straight into a Topic.",
  "做完看解析": "Review explanations after each set",
  "即时反馈、正确答案和本題概念一次看到。":
    "Instant feedback, the correct answer, and this question's concepts all in one place.",
  "错题 + 卡片回炉": "Mistakes + cards come back",
  "错题和到期的卡片会自动进入下一次复习。":
    "Mistakes and due cards automatically enter your next review.",

  // Teacher / about section
  "一个老师维护的练习室": "A practice room maintained by a teacher",
  "不是录播课，也不是把题目简单堆在一起。{name} 的题目、解析和练习顺序由一位 AP Psychology 老师持续维护：按 CED 的 Unit/Topic 拆开练，做完马上看解析，错题自动进入错题本。":
    "This isn't a recorded course, and it isn't a pile of questions. The questions, explanations, and practice order in {name} are maintained continuously by an AP Psychology teacher: practice split by CED Unit/Topic, see explanations right after each set, and mistakes go straight into your mistake bank.",
  "记忆卡片会按概念权重和复习间隔再次出现。练习路径已经排好：Unit → 错题 → 卡片，跟着走就行。":
    "Flashcards reappear based on concept weight and review intervals. The path is already laid out: Unit → Mistakes → Cards. Just follow it.",

  // FAQ
  "常见问题": "Frequently asked questions",
  "适合什么样的学生？": "Who is this for?",
  "正在准备 AP Psychology、想按 CED 的 Unit/Topic 系统练习的人；也适合考试前冲刺、想快速提分，需要集中刷题和复盘错题的人。":
    "Students preparing for AP Psychology who want systematic practice by CED Unit/Topic. It also suits last-minute exam prep when you need focused question drills and mistake review.",
  "手机上能用吗？": "Does it work on a phone?",
  "可以。练习、真题、错题本和卡片都按手机屏幕适配，浏览器打开即可，不需要安装 App。":
    "Yes. Practice, past exams, the mistake bank, and flashcards are all adapted for phone screens. Open it in your browser—no app install needed.",
  "FRQ 怎么练？": "How do I practice FRQs?",
  "FRQ 交卷后按官方 rubric 逐项自评，显示评分标准和参考要点；适合在考前熟悉采分点。":
    "After submitting an FRQ, self-assess item by item against the official rubric, with scoring criteria and key points displayed. It's a good way to learn where points come from before the exam.",
  "内容和考试大纲一致吗？": "Does the content match the exam outline?",
  "按最新 AP Psychology 考纲和 2027 教材整理，题目与解析覆盖最新 Unit/Topic 考点。":
    "It's organized around the latest AP Psychology course outline and 2027 materials, with questions and explanations covering the latest Unit/Topic content.",
  "知识图谱怎么用？": "How do I use the knowledge graph?",
  "每张图先展示 Unit 结构，再进入章节思维导图。点概念可看定义、教材关系、真题易混和关联题目；图谱只展示账号已解锁的 Unit。":
    "Each graph first shows the Unit structure, then opens into a chapter mind map. Click a concept to see its definition, textbook relationships, exam confusions, and related questions; the graph shows only the Units unlocked on your account.",

  // Footer
  "AP® 是 College Board 的注册商标；本站与 College Board 无隶属关系。":
    "AP® is a registered trademark of the College Board; this site is not affiliated with College Board.",

  // Countdown
  "距离 AP Psychology 考试": "AP Psychology exam countdown",
  "天": "days",

  // Teacher promo card
  "获取激活码": "Get an activation code",
  "需要老师帮你看一下？": "Want a teacher to take a look?",
  "20 分钟学习诊断：当前水平、薄弱 Unit、下一步练习计划。":
    "A 20-minute learning diagnostic: your current level, weak Units, and a next-step practice plan.",
  "预约诊断": "Book a diagnostic",
  "微信咨询/获取激活码": "WeChat consultation / activation code",
  "想让老师帮你看一下这份结果？":
    "Want a teacher to review these results with you?",
  "可以约一次 20 分钟诊断，一起看薄弱概念和下一步练习安排。":
    "Book a 20-minute diagnostic to review your weak concepts and next practice steps together.",
  "联系老师": "Contact the teacher",
  "{name} 微信二维码": "{name} WeChat QR code",
  "扫码添加微信": "Scan to add on WeChat",
  "微信二维码": "WeChat QR code",
  "在": "In",
  "配置二维码": "set the QR code",
  "已复制": "Copied",
  "复制": "Copy",
  "预约 20 分钟诊断": "Book a 20-minute diagnostic",
  "1v1 诊断 · FRQ 批改 · 学习规划":
    "1v1 diagnostic · FRQ feedback · study planning",
  "我是 Elfie，系统里的题目、解析和练习节奏由我维护。需要学习诊断、课程规划或获取激活码，可以直接加微信。":
    "I'm Elfie. I maintain the questions, explanations, and practice pace in this system. For a learning diagnostic, course planning, or an activation code, just add me on WeChat.",
  "加微信时备注「AP」": "Mention \"AP\" when adding me on WeChat.",
};

export default messages;
