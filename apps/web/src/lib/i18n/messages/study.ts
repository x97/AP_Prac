const messages: Record<string, string> = {
  // Dashboard
  "天": "days",
  "学习建议": "Study Tips",
  "先按单元练习": "Practice by unit first",
  "单元练习会即时给出解析和知识点；整套真题用来训练节奏和耐力。":
    "Unit practice gives instant explanations and concepts; full exams train pacing and stamina.",
  "连续答对两次才算掌握": "Two correct answers in a row count as mastered",
  "错题本会自动记录；连续答对后再标记为已掌握，仍可在「已掌握」中查看。":
    "The wrong book records automatically. After consecutive correct answers, mark the item as mastered; mastered items remain viewable under “Mastered”.",

  // Practice group
  "需要激活码，章节暂不可开始":
    "An activation code is required; chapters cannot be started yet.",
  "先选择 Unit，再选择章节。答题后即时判分，右侧同步显示相关概念。":
    "Choose a Unit, then a chapter. Answers are checked instantly with concepts on the right.",
  "{count} 个 Unit": "{count} Units",
  "独立的错题练习卷，包含未掌握和复习中的题目，并随错题本更新。":
    "A separate wrong-question paper. It includes unmastered and reviewing questions and updates with your wrong book.",
  "{topics} 个 Topic · {questions} 道练习题":
    "{topics} topics · {questions} practice questions",
  "已答 {answered}/{total}": "{answered}/{total} answered",
  "查看章节": "View chapters",
  "进入 Unit": "Enter Unit",
  "返回单元列表": "Back to Units",
  "继续": "Continue",
  "查看记录": "View Record",
  "开始新一组": "Start New Set",
  "{questions} 道练习题 · 已答 {answered} · 正确率 {accuracy}":
    "{questions} practice questions · {answered} answered · Accuracy {accuracy}",
  "章节": "Chapters",
  "点击章节继续上次进度。选择「重新练习」会从第 1 题开始新的记录。":
    "Click a chapter to resume. Choose “Practice Again” to start a new record from Question 1.",
  "{count} 个 Topic": "{count} topics",
  "已完成": "Completed",
  "进行中": "In Progress",
  "提前结束": "Ended Early",
  "已完成 {total}/{total} · 答对 {correct} 道":
    "Completed {total}/{total} · {correct} correct",
  "已完成 {answered}/{total} · 从第 {question} 题继续":
    "{answered}/{total} done · Continue at Question {question}",
  "提前结束 · 已答 {answered}/{total}":
    "Ended early · {answered}/{total} answered",
  "{count} 道题": "{count} questions",
  "累计 {answered}/{total} · {accuracy}":
    "Cumulative {answered}/{total} · {accuracy}",
  "未解锁": "Locked",
  "重新练习": "Practice Again",
  "这个 Unit 还没有练习题。": "This Unit has no practice questions yet.",

  // Practice session
  "移除这道题的收藏？": "Remove this question from your bookmarks?",
  "重新开始错题练习？当前答题记录会保留在「做题记录」，新练习会从第一题开始。":
    "Restart wrong practice? Your current answers stay in History, and the new practice starts from Question 1.",
  "重新开始本次练习？当前答题记录会保留在「做题记录」。":
    "Restart this practice? Your current answers stay in History.",
  "返回错题本": "Back to Wrong Book",
  "错题练习卷": "Wrong Practice Paper",
  "退出错题本": "Exit Wrong Book",
  "重新开始": "Restart",
  "错题练习完成": "Wrong Practice Complete",
  "错题练习已结束": "Wrong Practice Ended",

  // Exam paper
  "需要解锁": "Unlock Required",
  "这套试卷需要激活码。可在「我的 → 课程权限」中输入激活码后开始。":
    "This paper requires an activation code. Enter one under Me → Course Access to start.",

  // Exam attempt
  "暂停考试失败，请重试。": "Failed to pause the exam. Please try again.",
  "正在暂停考试…": "Pausing exam…",
  "正在保存考试状态并冻结计时，暂停成功后会返回上一页。":
    "Saving exam state and freezing the timer. You will return to the previous page once the pause succeeds.",
  "暂停失败": "Pause Failed",
  "暂停请求没有成功，考试仍在计时。请重试；只有暂停成功后才会返回上一页。":
    "The pause request did not succeed and the exam is still timed. Please try again; you will only return to the previous page after the pause succeeds.",
  "继续考试": "Continue Exam",
  "重试暂停": "Retry Pause",
  "正在交卷…": "Submitting…",
  "正在批改中…": "Grading…",
  "交卷后进入评分标准自评；错题会在整卷完成后统一记录。":
    "After submitting, you will self-grade against the rubric; wrong answers are recorded together once the full exam is complete.",
  "交卷后统一批改；错题会在批改完成后进入错题本。":
    "Answers are graded together after submission; wrong questions enter the wrong book when grading is complete.",

  // Flashcards
  "全部单元": "All Units",
  "研究方法": "Research Methods",
  "全部": "All",
  "首页": "Home",
  "做题记录": "Practice History",
  "记忆卡片": "Flashcards",
  "先看术语，翻面查看释义。按到期顺序连续出现，学完可以随时停下。":
    "See the term first, then flip to reveal the definition. Cards appear continuously in due order; stop whenever you like.",
  "自己创建卡片：术语、简短含义和详细解释。只有你自己能看到。":
    "Create your own cards: a term, a short meaning, and a detailed explanation. Only you can see them.",
  "按权重排序": "Sorted by weight",
  "卡片来源": "Card source",
  "官方卡片": "Official Cards",
  "我的卡片": "My Cards",
  "按单元筛选": "Filter by unit",
  "重要程度": "Importance",
  "按重要程度筛选": "Filter by importance",
  "星星表示概念权重：5★ 最重要。高权重卡片优先出现，也可以在上方筛选 4★+。卡片按到期顺序连续出现，不再按组抽取。每天最多引入 60 张新卡；新卡第一次选择「Already Know」后 30 分钟内会再次出现，第二次后进入 1 / 2 / 4 / 7 / 15 天间隔；「Review Later」10 分钟后再次出现。逾期卡片显示「逾期 N 天」，最长间隔为 15 天。":
    "Stars show concept weight: 5★ is the most important. Higher-weight cards appear first, and you can filter for 4★+ above. Cards appear continuously in due order instead of being drawn by group. At most 60 new cards are introduced per day; after you first choose “Already Know” on a new card, it reappears within 30 minutes, and after the second time it moves to a 1 / 2 / 4 / 7 / 15-day interval; “Review Later” makes it reappear after 10 minutes. Overdue cards show “Overdue N days”, and the maximum interval is 15 days.",

  // Wrong book
  "全部进行中": "All Active",
  "未掌握": "Unmastered",
  "复习中": "Reviewing",
  "已掌握": "Mastered",
  "错题练习启动失败": "Failed to start wrong practice",
  "操作失败": "Action failed",
  "题目加载失败": "Failed to load question",
  "错题本": "Wrong Book",
  "答错的题目会自动记录。点击卡片查看完整题目、正确答案和解析。":
    "Wrong answers are recorded automatically. Click a card to see the full question, correct answer, and explanation.",
  "独立于原单元的错题练习卷，包含未掌握和复习中的题目。":
    "A wrong-practice paper independent of the original Unit, containing unmastered and reviewing questions.",
  "{learning} 道未掌握 · {reviewing} 道复习中 · 已掌握题目不包含在内":
    "{learning} unmastered · {reviewing} reviewing · mastered questions are not included",
  "这份练习卷是动态的：新错题会自动加入，已掌握题目会移除，已作答进度会保留。":
    "This paper is dynamic: new wrong questions are added automatically, mastered questions are removed, and answered progress is kept.",
  "复习中 = 答错后已经答对一次；再连续答对一次即可标记为已掌握。":
    "Reviewing = answered correctly once after getting it wrong; one more correct answer in a row lets you mark it as mastered.",
  "开始练习": "Start Practice",
  "暂无可练习题目": "No Questions to Practice",
  "当前没有进行中的错题。已掌握的题目在「已掌握」标签中。":
    "There are no active wrong questions. Mastered questions are under the “Mastered” tab.",
  "「{tab}」中没有题目。": "No questions in “{tab}”.",
  "还没有错题。练习中答错的题目会自动出现在这里。":
    "No wrong questions yet. Questions you get wrong during practice appear here automatically.",
  "错 {count} 次": "Wrong {count} times",
  "再答对一次即掌握": "One more correct to master",
  "答对一次进入复习中": "One correct answer moves it to Reviewing",
  "标记为未掌握": "Mark as Unmastered",
  "标记为已掌握": "Mark as Mastered",
  "查看题目、答案与解析": "View Question, Answer & Explanation",
  "弹窗查看": "Open in dialog",
  "题目回顾 · Q{number}": "Question Review · Q{number}",
  "题目回顾": "Question Review",
  "相关概念（点击查看详情）": "Related Concepts (click for details)",
  "你当时答错了": "You answered incorrectly",
  "错 {count} 次 · 正确答案与解析仅供复习":
    "Wrong {count} times · Correct answer and explanation are for review only",

  // Bookmarks
  "长期收藏的题目，与考试中的「标记待复查」分开。":
    "Long-term saved questions, separate from Mark for Review inside an exam.",
  "练习收藏题目": "Practice Bookmarks",
  "收藏练习启动失败": "Failed to start bookmark practice",
  "移除收藏失败": "Failed to remove bookmark",
  "移除收藏": "Remove",
  "还没有收藏题目。练习时点题目右上角的「收藏」即可加入。":
    "No bookmarks yet. Tap “Bookmark” on a question during practice to add it here.",
  "收藏题目回顾": "Bookmarked question",

  // Notebook
  "删除这条笔记？删除后无法恢复。": "Delete this note? This cannot be undone.",

  // Knowledge graph
  "知识图谱": "Knowledge Graph",
  "按账号已解锁的 Unit 展示。先看 Unit 结构，再点 Topic 进入章节思维导图，最后点叶子概念查看详情。":
    "Shown for the Units your account has unlocked. Start with the Unit structure, click a Topic for the chapter mind map, then click a leaf concept for details.",
  "Unit {number} 尚未解锁": "Unit {number} is Locked",
  "知识图谱与 Unit 练习共用权限。当前账号只能查看已解锁 Unit 的图谱；激活后会自动显示其余 Unit 的结构和知识点关系。":
    "The knowledge graph shares access with Unit practice. This account can only view graphs for unlocked Units; after activation, the remaining Units' structure and concept relationships appear automatically.",
  "使用激活码": "Use Activation Code",
  "暂无可用知识图谱。": "No knowledge graph available yet.",
  "图谱为只读内容，跟随当前内容 Release 生成；未解锁 Unit 不返回概念和关系数据。":
    "The graph is read-only and generated from the current content release; locked Units return no concept or relationship data.",
  "正在生成知识图谱…": "Generating knowledge graph…",
};

export default messages;
