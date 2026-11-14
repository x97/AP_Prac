# TODO / 未完成事项

> 更新时间：2026-10-30  
> 当前策略：Phase 1 —— 本地是权威内容源，服务器只消费 Release。  
> 原则：不要同时启用本地和服务器内容写入。

---

## 0. 当前基线

已完成：

- [x] 学生端登录、首页、单元练习、真题、FRQ 自评
- [x] 错题本、收藏、笔记、做题记录
- [x] 记忆卡片、自定义卡片
- [x] 学生昵称设置（可重复）
- [x] Unit 1 知识图谱：结构层、XMind 章节导图、概念详情
- [x] 解析 `心理学思维导图.pdf` 的章节层级；Unit 1 按教材/知识库整理
- [x] 导图知识点只显示英文；深层节点 `+N` 折叠
- [x] 知识图谱按已解锁 Unit 返回；未解锁 Unit 不返回概念数据
- [x] 知识图谱只读题目预览（不可作答）
- [x] Admin 知识图谱编辑：思维导图画布、创建/编辑/删除节点、本地搜索、补充知识点、草稿保存/恢复原图
- [x] Admin 内容覆盖层：题目/概念/KP/关联编辑与新建，Admin 标记，优先于本地同步
- [x] Admin 概念/KP 列表分页；名称模糊搜索
- [x] Admin 全局科目分类：试卷/知识点/知识图谱筛选与创建默认跟随当前科目
- [x] 学生首页/我的显示已激活科目、有效期和数量
- [x] Admin 思维导图画布拖拽、缩放、节点展开/收起
- [x] 删除/移除类操作统一确认
- [x] 知识图谱落地页宣传区 `/#graph`
- [x] 考试交卷后统一批改；作答时不写入错题本；交卷显示「正在批改中…」
- [x] 浏览器返回先显示「正在暂停考试…」至少 1.5 秒，暂停成功后返回上一页；失败留在考试页重试
- [x] Admin 独立登录、CLI 创建管理员
- [x] Admin 学生进度查看
- [x] Admin 试卷/题目/知识点只读浏览
- [x] Admin 内容写入默认关闭（Release 源库）；知识图谱草稿独立存应用库，按管理员角色开放
- [x] `content_releases` / `content_active_release`
- [x] 全局 `data/releases/active` 指针（合并 Release）
- [x] Release 本地构建/激活/归档/恢复
- [x] Release 热加载
- [x] 当前只保留一个可用 Release
- [x] 科目源库迁移：`data/content/<subject>/<subject>_exam.db` / `<subject>_knowledge.db`
- [x] psychology / statistics 源库物理拆分
- [x] 移除根目录兼容符号链接 `ap_exam.db` / `ap_knowledge.db`
- [x] `AP_exam/` 拆分到 `data/content/<subject>/{extraction,reports}` 与 `docs/content/`
- [x] 移除旧静态页 `pages/`、`index.html` 及 `build_quiz.py` / `build_unit_practice.py` / `build_knowledge_viewer.py`
- [x] 内容接口强制登录
- [x] 全局限流（单进程内存版）
- [x] API `Cache-Control: private, no-store`
- [x] 图片签名 URL（`/assets/{path}?exp&sig`）
- [x] 考试/练习/试卷 JSON 的 ECDH + AES-256-GCM payload 加密
- [x] 科目级课程权限与免费体验（Unit 1 + 1 真题 + 1 模拟）
- [x] Admin 批量生成/下载/作废激活码
- [x] 学生端激活码兑换、时长叠加、指定日期码
- [x] 锁定 Unit/真题卡片 + 使用激活码入口
- [x] 科目配置 `config/subjects/*.json`
- [x] statistics 三份内容配置占位（空、`enabled=false`）
- [x] `build_exam_configs.py` / `build_practice_topics.py` 支持 `--subject`
- [x] `build_merged_release.py` 合并发布脚本
- [x] `generate_ai_explanations.py --subject`
- [x] 当前 Release 改为合并包
- [x] Admin 激活合并 Release：写全局指针并按 `subjects` 更新 registry

当前 Release：

```text
content-20261030-01
```

当前源库：

```text
data/content/psychology/psychology_exam.db
data/content/psychology/psychology_knowledge.db
data/content/statistics/statistics_exam.db
data/content/statistics/statistics_knowledge.db
```

---

## 1. P0：Phase 1 Release 发布链路

这是下一步最优先要做的事情。

### 1.1 Release 包与上传

- [ ] 增加本地 `publish_release.py`：构建 → 校验 → 打包 → checksum → 上传
- [ ] Release 包格式固定为 `tar.gz` 或 `zip`
- [ ] 生成/校验 `release.json`、`exam.db`、`knowledge.db`、`assets-manifest.json`
- [ ] 检查包内路径穿越、绝对路径、符号链接逃逸
- [ ] 检查文件大小、SQLite integrity、foreign key
- [ ] 检查 assets 是否存在且 checksum 一致
- [ ] 上传失败不影响当前 active Release

### 1.2 服务端导入 API

- [ ] `POST /api/v1/admin/releases/import`
- [ ] 导入到 staging
- [ ] 校验 subject_id、release_id、checksums、counts
- [ ] 校验通过后移动到正式 Release 目录
- [ ] 写入 `content_releases`，状态 `imported`
- [ ] 禁止覆盖已存在 Release ID
- [ ] 重复导入相同 checksum 时幂等处理
- [ ] 导入失败清理 staging
- [ ] 导入和激活严格分离

### 1.3 Admin 发布页面

- [ ] 上传 Release 包
- [ ] 显示导入进度/结果
- [ ] 显示 Release Diff 摘要
- [ ] 导入后显示“待激活”
- [ ] 只有 super_admin 可以激活
- [ ] 激活前二次确认
- [ ] 归档/恢复/回滚
- [ ] 显示当前 active Release

### 1.4 Admin 内容读取切换

Admin 内容读取已切到 active Release；写接口（默认关闭）仍写本地科目源库。Phase 1 生产环境还需：

- [x] 试卷列表从 active Release 读取
- [x] 题目详情从 active Release 读取
- [x] 知识点/概念从 active Release 读取
- [ ] Admin 内容页面显示当前 subject/release
- [ ] 生产环境隐藏本地构建入口
- [ ] 生产 Admin 内容只读
- [ ] 本地 Admin 编辑能力仅作为开发工具

### 1.5 部署脚本

- [ ] `deploy_release.sh` 改为上传到 staging
- [ ] 服务端 checksum 校验
- [ ] 原子移动/切换 active
- [ ] 不强制重启 API（使用热加载）
- [ ] 失败不切换 active
- [ ] 记录发布日志
- [ ] 保留上一版本用于回滚

### 1.6 多科目 Release

- [x] Release 包带 `subjects`
- [x] 科目源库目录化
- [x] 合并 Release 构建脚本
- [x] 全局 active Release 切换协议
- [x] `validate_content_release.py` 总 counts 改为按实际库计算
- [x] statistics 三份内容配置占位
- [ ] 多科目合并联调（statistics 暂未 enabled）
- [ ] Admin 页面增加 subject 选择器
- [ ] `/subjects` 返回真实 subjects
- [ ] `/assets/<subject>/...` 按 subject 提供资源
- [ ] `validate_content_release.py` 增加各科目内容不变量
- [ ] `ContentStore` 单元标题等按 subject 配置

### 1.7 历史版本与复盘

- [ ] 所有 attempt / practice session 写入并保留 `content_release_id`
- [ ] 查看旧 attempt 时按自己的 Release 读取
- [ ] 删除题目后旧 attempt 仍可复盘
- [ ] 当前 Release 找不到的题目显示“已从题库移除”
- [ ] 错题、收藏、笔记引用已删除题目时不删用户数据
- [ ] Release 归档/恢复后历史复盘仍可用

### 1.8 Release Diff

- [ ] 新增/删除/修改试卷
- [ ] 新增/删除/修改题目
- [ ] 选项/答案/解析变化
- [ ] FRQ rubric 变化
- [ ] 知识点/概念/关联变化
- [ ] practice topic / exam config 变化
- [ ] assets 变化
- [ ] 生成 `release-diff.json`
- [ ] Admin 激活前展示 Diff
- [ ] 有删除/答案变化/概念合并时要求 super_admin

---

## 2. P0：内容数据问题

- [ ] 2018 FRQ 2 评分标准只有 3/7，补齐缺失的 4 个 point
- [ ] `validate_content_release.py` 不能继续硬编码 2,876 题、1,105 概念等固定 counts
- [ ] 新增/删除题目后仍需能构建 Release
- [ ] 考试配置、practice topics、exclusions 的校验参数化
- [ ] 内容 Release 保留策略自动化（当前手工清理）
- [ ] 备份策略自动化（当前只保留一组手工备份）
- [ ] 明确 content source 备份频率和位置

---

## 2.1 P1：知识图谱后续

- [x] Unit 1–5 全部叶子节点补全释义（知识库概念或 AI/教材补充释义）
- [x] 导图节点折叠/展开（节点 +/− 与全局 Collapse/Expand）
- [x] Unit 结构图章节标题完整换行显示
- [ ] 审校 AI 补充释义（165 条 draft）及 Admin 新增补充知识点
- [ ] 继续用教材整理 Unit 2–5 的章节层级，减少未解析标签
- [x] 为导图 `+N` 节点增加展开/收起
- [ ] 评估把 `mindmap_concepts` 改为按需详情接口，降低首屏 payload
- [ ] 教材关系审校：前置依赖、同框架、跨单元因果候选边
- [ ] 按章节整理 10–20 条高价值知识关联路径
- [ ] 未映射到练习 Topic 的 Unit 概念设计「教材全量概念」补充层
- [ ] 关系变更的回归验证（避免孤立点、错误前置依赖）
- [x] Admin 知识图谱 Topic 树编辑 + 补充知识点（应用库草稿，不写 Release）
- [ ] Admin 编辑知识库概念之间的关系边（当前只编辑 Topic 树）

## 3. P1：内容安全加固

- [ ] 限流存储改为 Redis（多 worker / 多实例共享）
- [ ] WAF / IP 信誉 / 异常请求检测
- [ ] 设备指纹、同账号多地登录告警
- [ ] 题目图片用户水印
- [ ] OSS/COS 私有 bucket + CDN 签名
- [ ] 生产关闭 `/docs` / OpenAPI 或限制内网
- [ ] Admin 2FA + IP 白名单（见下一节）

---

## 4. P1：Admin 后台

- [ ] 题目报错列表页面（目前 Dashboard 只有计数）
- [ ] 报错处理状态：open / in_progress / resolved / ignored
- [ ] 管理员账号管理页面（当前只有 CLI）
- [ ] 角色权限细化到页面/按钮
- [ ] super_admin / content_editor / analyst / support 权限验证
- [ ] Admin 登录限流
- [ ] Admin 2FA
- [ ] Admin IP 白名单
- [ ] Admin CSRF 防护
- [ ] Admin 操作审计详情
- [ ] Admin 内容页面显示只读标识（已改为角色可编辑 + Admin 标记）
- [ ] Admin 新建 FRQ（含 rubric 编辑）
- [ ] Admin 新建题目关联到练习 Topic
- [ ] 生产环境隐藏/禁用本地构建按钮
- [ ] Admin 独立 Dockerfile
- [ ] Admin 接入 Docker Compose / Nginx

---

## 5. P1：内容生产线

Phase 1 不做服务器端 PDF 解析。以下先记录，不立即实施：

- [ ] 本地 PDF 解析 → staging 包
- [ ] 本地 AI explanation → staging
- [ ] 本地题目—概念关联 → staging
- [ ] staging 包上传服务器
- [ ] 服务器 staging 导入
- [ ] Admin 审核/合并
- [ ] 题目重复检测
- [ ] 题目映射报告
- [ ] 教材版本升级
- [ ] 概念合并/拆分审核
- [ ] 服务器内容工作区（Phase 2）

---

## 6. P1：学生端

- [ ] 多科目选择器/路由（当前只支持 psychology）
- [ ] 科目切换时加载对应 active Release
- [ ] 注册/登录隐私政策勾选
- [ ] 账号注销/数据删除
- [ ] 微信登录（后续）
- [ ] 小程序端（后续）
- [ ] PWA/离线（后续）
- [ ] 搜索（后续）
- [ ] 薄弱知识点组卷（后续）

---

## 7. P1：部署与运维

- [ ] 生产服务器采购/初始化
- [ ] 域名 + ICP 备案
- [ ] HTTPS
- [ ] Nginx 配置 Admin 子域名/路径
- [ ] Admin 只允许内网/VPN/IP 白名单
- [ ] 生产 `.env` 配置
- [ ] 生产邮箱发信服务（SMTP / SPF / DKIM）
- [ ] Postgres 每日备份
- [ ] Release 保留/归档策略
- [ ] `/healthz` / `/readyz` 监控
- [ ] 日志/错误监控
- [ ] 静态资源 OSS/COS/CDN
- [ ] 多科目 assets 路径
- [ ] Alembic 迁移（当前大量依赖 `create_all`）
- [ ] 生产 Release 导入服务
- [ ] 发布后 smoke test 自动化

---

## 8. P1：测试

- [ ] Release 导入/激活 E2E
- [ ] Release 回滚 E2E
- [ ] 多科目 active 切换 E2E
- [ ] 旧 attempt 按 content_release_id 复盘测试
- [ ] 删除题目后错题/笔记/收藏行为测试
- [ ] Admin 内容只读测试
- [ ] Admin 权限测试
- [ ] 学生端 Playwright E2E
- [ ] 移动端 390px E2E
- [ ] 断网/刷新/自动保存测试
- [ ] 生产 Release 包 checksum 测试

---

## 9. Phase 2（暂不开始）

只有确认需要在服务器端编辑/解析内容时再做：

- [ ] 服务器内容工作区（SQLite 单写者）
- [ ] 服务器构建 Release
- [ ] PDF 上传
- [ ] OCR/版面分析
- [ ] 试卷解析 worker
- [ ] 教材/KP worker
- [ ] AI explanation worker
- [ ] 题目—概念关联 worker
- [ ] 任务队列/重试/成本控制
- [ ] 人工审核 Diff
- [ ] Phase 1 → Phase 2 数据切迁

Phase 2 需要额外服务器资源，当前不启动。

---

## 10. 待决策

- [ ] 生产 assets 使用本地目录还是 OSS/CDN
- [ ] Release 保留数量：3 / 5 / 10 / 永久
- [ ] Admin 是否独立子域名
- [ ] 是否保留本地 Admin 编辑能力（仅开发环境）
- [ ] 内容库未来是否迁 PostgreSQL
- [ ] 是否开放微信登录/小程序

---

## 11. 下一步建议

按顺序：

```text
1. Release 包格式 + publish_release.py
2. 服务端 release import API
3. Admin Release 上传/导入/激活
4. [已完成] Admin 内容读取切换到 active Release
5. Release Diff
6. 历史 attempt 按 content_release_id 复盘
7. 多科目 assets/active 完整化
8. 自动化 Release 测试
9. Redis 限流 / WAF / 水印
```

在 1–3 完成前，不要开始服务器端 PDF/AI 解析。

