const messages: Record<string, string> = {
  // CourseAccessCard
  "课程权限": "Course access",
  "已激活科目": "Activated subjects",
  "{count} 个": "{count} active",
  "这里列出你已激活的科目及有效期。即使尚未激活的科目，也有部分免费内容可以体验。":
    "These are the subjects you've activated, along with their access dates. Even subjects you haven't activated still include some free content for you to explore.",
  "你还没有已激活的科目。": "You don't have any activated subjects yet.",
  "输入激活码 →": "Enter an activation code →",
  "这里列出当前账号可用的科目和有效期；未激活科目可继续使用免费内容。":
    "Subjects available to this account and their access dates. Inactive subjects can still access free content.",
  "使用激活码": "Use Activation Code",
  "正在读取课程权限…": "Loading course access…",
  "内容暂未开放": "Content not yet available",
  "已激活 · 有效期至 {date}": "Active · Valid until {date}",
  "未激活 · 可免费体验部分内容": "Inactive · Some content available for free",
  "已激活": "Active",
  "未激活": "Inactive",

  // ActivatedSubjectsCard
  "当前账号已开通的科目和有效期；未开通科目仍可免费体验部分内容。":
    "Subjects enabled for this account and their access dates. Subjects that are not enabled can still access some free content.",
  "管理 / 激活": "Manage / Activate",
  "有效期至 {date}": "Valid until {date}",
  "暂无已激活科目。": "No activated subjects yet.",
  "去输入激活码 →": "Enter an activation code →",

  // RedeemCodeModal
  "激活失败，请检查激活码": "Activation failed. Please check the code.",
  "激活成功": "Activated",
  "确认激活": "Confirm activation",
  "课程已激活": "Course activated",
  "至 {date}": "Until {date}",
  "开始使用": "Get started",
  "确认使用这个激活码？": "Use this activation code?",
  "激活后会绑定当前账号，不能转给其他账号。确认后立即生效。":
    "The code will be bound to this account and cannot be transferred. It takes effect immediately after confirmation.",
  "返回修改": "Back",
  "激活中…": "Activating…",
  "激活码会绑定当前账号。新时长会叠加到已有有效期上；指定日期码会延长到该日期。":
    "The activation code will be bound to this account. New time is added to any existing access period; date-specific codes extend access to that date.",
  "取消": "Cancel",
  "下一步": "Next",

  // questionSource (translated where rendered by QuestionSourceLine)
  "真题 / 模拟": "Real exam / Mock exam",
};

export default messages;
