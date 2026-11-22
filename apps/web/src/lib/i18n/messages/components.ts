const messages: Record<string, string> = {
  // MyFlashcards
  "新卡": "New",
  "到期": "Due",
  "第 {box} 盒": "Box {box}",
  "加载卡片失败": "Failed to load cards",
  "术语和简短含义不能为空。": "Term and short meaning are required.",
  "保存卡片失败": "Failed to save card",
  "删除卡片失败": "Failed to delete card",
  "我的卡片": "My Cards",
  "个人卡组": "Personal deck",
  "{total} / {limit} 张。只有你自己能看到这些卡片。":
    "{total} / {limit} cards. Only you can see these cards.",
  "新建卡片": "New card",
  "开始学习": "Start studying",
  "已达到 {limit} 张上限。删除一张卡片后才能继续新建。":
    "You've reached the {limit}-card limit. Delete a card before creating a new one.",
  "还没有个人卡片": "No personal cards yet",
  "添加术语、简短含义，以及可选的详细解释。":
    "Add a term, a short meaning, and an optional detailed explanation.",
  "创建第一张卡片": "Create your first card",
  "认识 {known} 次 · 已复习 {seen} 次":
    "Known {known} times · Reviewed {seen} times",
  "尚未复习": "Not reviewed yet",
  "编辑": "Edit",
  "删除": "Delete",
  "编辑卡片": "Edit card",
  "术语 / 卡片名": "Term / Card name",
  "例如：Spacing effect": "e.g. Spacing effect",
  "简短含义": "Short meaning",
  "一句容易回忆的清晰解释。": "A clear explanation that's easy to recall.",
  "详细解释": "Detailed explanation",
  "可选：例子、语境或完整解释。":
    "Optional: an example, context, or full explanation.",
  "取消": "Cancel",
  "保存修改": "Save changes",
  "创建卡片": "Create card",
  "删除卡片？": "Delete card?",
  "确定删除": "Are you sure you want to delete",
  "？它的复习进度也会一起删除。":
    "? Its review progress will also be deleted.",
  "保留卡片": "Keep card",

  // FlashcardStudy
  "保存卡片进度失败": "Failed to save card progress",
  "今日学习完成": "Study complete for today",
  "今天到期的卡片已经复习完": "You've reviewed all cards due today",
  "今日已复习 {n} 张": "Reviewed {n} cards today",
  "今日新卡 {today} / {limit} · 今日已复习 {reviewed} 张":
    "New cards today {today} / {limit} · Reviewed today {reviewed} cards",
  "今日新卡上限已到。到期卡片仍会按时间自动出现。":
    "You've reached today's new-card limit. Due cards will still appear on schedule.",
  "后续到期卡片会在到时间后重新进入队列。":
    "Upcoming cards will return to the queue once they are due.",
  "重新检查": "Check again",
  "全部卡片": "All cards",
  "还没有创建任何卡片。": "You haven't created any cards yet.",
  "当前筛选范围没有卡片。": "No cards match the current filter.",
  "本组完成": "Set complete",
  "认识了 {known} 张 · 还不熟 {again} 张。没记住的卡片会更早再次出现。":
    "Known {known} · Still learning {again}. Cards you missed will appear again sooner.",
  "新一组": "New set",
  "待复习 {due} · 新卡 {new}": "Due {due} · New {new}",
  "待复习 {due} · 今日新卡 {today}/{limit}":
    "Due {due} · New today {today}/{limit}",
  "本组 {n} 张 · 共 {total} 张": "This set {n} cards · {total} total",
  "今日已复习 {reviewed} 张 · 本次 {session} 张":
    "Reviewed today {reviewed} cards · This session {session} cards",
  "待复习 {due} · 新卡 {new} · 已复习 {reviewed}":
    "Due {due} · New {new} · Reviewed {reviewed}",
  "认识了 {known} 张 · 还不熟 {again} 张":
    "Known {known} · Still learning {again}",
  "显示术语": "Show term",
  "显示释义": "Show definition",
  "音标 {ipa}": "IPA {ipa}",
  "IPA 音标": "IPA",
  "点击翻面": "Click to flip",
  "朗读术语": "Read term aloud",
  "朗读": "Read aloud",
  "点击卡片查看释义。可随时选择 Already Know 或 Review Later。":
    "Click the card to see the definition. Choose Already Know or Review Later at any time.",

  // KnowledgeGraph
  "组成": "Part of",
  "上下位": "Broader / narrower",
  "相关": "Related",
  "同名异义": "Same name, different meaning",
  "核心题": "Core question",
  "辅助题": "Supporting question",
  "干扰项": "Distractor",
  "教材 {semantic} · 易混 {contrast} · 同题 {co}":
    "Textbook {semantic} · Confusable {contrast} · Same question {co}",
  "返回结构图": "Back to structure",
  "先把结构看懂": "Understand the structure first",
  "这是按已解锁 Unit 生成的知识图谱。默认只展示 Topic 结构和每个 Topic 的 3 个核心概念；":
    "This knowledge graph is generated from unlocked Units. By default it shows the Topic structure and the 3 core concepts in each Topic;",
  "点击 Topic 节点查看内部概念图，再点概念查看定义、关系和关联题目。":
    "click a Topic node to open its internal concept map, then click a concept to see its definition, relations, and related questions.",
  "点击导图中的英文概念节点查看定义、关系和关联题目。返回结构图请用导图左上角按钮。":
    "Click an English concept node in the mind map to see its definition, relations, and related questions. Use the button at the top left of the mind map to return to the structure view.",
  "按权重排序": "Sorted by weight",
  "{n} 易混": "Confusable: {n}",
  "暂无定义。": "No definition yet.",
  "教材关系": "Textbook relations",
  "{n} 条": "{n} relations",
  "暂无教材显式关系。": "No explicit textbook relations yet.",
  "真题易混": "Exam confusables",
  "来自同题正确项 / 干扰项":
    "From correct options / distractors in the same question",
  "易混": "Confusable",
  "暂无真题层面的易混记录。": "No exam-level confusable records yet.",
  "按概念角色分组": "Grouped by concept role",
  "点击题号，只读查看题目":
    "Click a question number for a read-only preview",
  "暂无直接关联题目。": "No directly related questions yet.",
  "返回 Topic": "Back to Topic",
  "退出全屏": "Exit fullscreen",
  "全屏查看知识图谱": "View knowledge graph in fullscreen",
  "退出全屏（Esc）": "Exit fullscreen (Esc)",
  "全屏查看": "View fullscreen",
  "全屏": "Fullscreen",
  "左右滑动查看完整图": "Swipe left or right to see the full graph",
  "Unit 级先看结构，Topic 级进入思维导图":
    "Unit view shows structure; open a Topic for its mind map",
  "{n} 个节点": "{n} nodes",
  "只读预览 · 不记录作答 · 题目来自当前知识图谱关联":
    "Read-only preview · answers are not recorded · questions come from the current knowledge graph",

  // KnowledgeRail
  "近似匹配": "Approximate match",

  // Theme accents (labels stay Chinese in lib/theme.ts as source keys)
  "经典蓝": "Classic blue",
  "海盐蓝": "Ocean blue",
  "青碧": "Teal",
  "森林绿": "Forest green",
  "薄荷绿": "Mint",
  "琥珀金": "Amber",
  "日落橙": "Sunset orange",
  "赤红": "Crimson",
  "樱花粉": "Sakura pink",
  "紫罗兰": "Violet",
  "靛蓝": "Indigo",
  "石墨灰": "Graphite",
};

export default messages;
