# Admin 内容编辑与覆盖层

## 目标

管理员对题目、知识点、题目—知识点关联的修改，在产品语义上等同于直接修改当前已发布 Release：

- 学生端立即读取修改后的内容。
- 本地教材/试卷再次同步并生成新 Release 时，Admin 修改仍然优先。
- 不直接改写不可变 Release 文件；Admin 修改保存在应用数据库，读取时与 Release 合并。

## 数据结构

```text
admin_content_records
  subject_id, entity_type, entity_id, origin, data, base_release_id,
  created_by, created_at, updated_at
  UNIQUE(subject_id, entity_type, entity_id)

admin_content_revisions
  subject_id, revision, updated_at
```

`entity_type`：

- `paper`
- `question`
- `concept`
- `knowledge_point`
- `question_concept_link`
- `question_kp_link`

`origin`：

- `admin_created`
- `admin_edited`
- `admin_deleted`

`data` 保存完整快照。Admin 内容优先意味着：同一实体的本地新版本不会覆盖 Admin 快照；新增实体会继续保留。

## 有效内容目录

```text
data/app/effective/<subject>/<release_id>-r<revision>/
  exam.db
  knowledge.db
  release.json
  exclusions.json
  assets -> active Release assets
```

- `admin_content_revisions.revision` 变化后重新生成有效内容。
- 有效内容由 Active Release 复制后应用 Admin 覆盖记录生成。
- `current` 符号链接原子切换到最新版本。
- 学生端 `ContentStore`、Admin 内容页、assets 都读取有效内容目录。
- Release 文件本身保持只读；`data/app/effective/` 已被 gitignore。
- 设置 `EFFECTIVE_CONTENT_DIR` 可改变有效内容根目录。

## 标记字段

有效内容 DB 的相关表增加：

```text
admin_origin TEXT       -- admin_created / admin_edited / NULL
admin_updated_at TEXT   -- 最近一次 Admin 写入时间
```

覆盖的表：

- `papers`
- `questions`
- `options`
- `concept_clusters`
- `knowledge_points`
- `question_concept_links`
- `question_kp_links`

Admin API 在题目、知识点、试卷、关联记录中返回 `admin_origin` / `admin_updated_at`，后台显示「Admin 新建 / Admin 修改」标记。

## 题目星级

- 表：`question_stars(subject_id, question_id, stars, updated_by, created_at, updated_at)`，主键 `(subject_id, question_id)`。
- 取值 1–5；未评级不写记录。再次点击当前星级会清除评级。
- 星级保存在应用数据库，不进入 Admin 覆盖层：设置星级不会重建有效内容，也不会加 `admin_origin` 标记。
- 题目详情和试卷题目列表都返回 `stars`，未评级为 `null`。
- 写入要求 `super_admin` / `content_editor`，并记录 `content.question.stars.update` 审计日志。

## 题目总览

- 后台「题目」入口跨试卷列出当前科目的全部题目，并可直接在列表中修改星级。
- 筛选条件：
  - `source`：`all` / `unit`（单元练习）/ `real_exam`（真题）/ `mock_exam`（模拟题）/ `unit_practice`（章节练习）。
  - `unit`：1–5，仅在 `source=unit` 时生效；通过 `paper_question_map` + `practice_groups` 判断单元归属。
  - `section`：`MCQ` / `FRQ`。
  - `q`：按题干或题目 ID 模糊搜索。
- 列表返回试卷来源、年份、题型、选项数和 `stars`；`source=unit` 的题目额外返回 `unit_ids`。
- 使用 `limit + offset` 分页，默认 50 条，最大 200。

## 练习包 practice_bundle

`practice_bundle` 是 Unit 单元练习的**虚拟试卷**：

- `papers.question_count` 记录练习包题数，例如 Unit 1 为 345。
- 题目不在 `questions.paper_id = bundle_id` 下，而是通过 `paper_question_map` 指向源试卷题目。
- 学生端通过 `practice_groups` / `practice_topics` 使用这些题目，不作为整卷考试。
- Admin 试卷列表和详情现在会通过 `paper_question_map` 统计并列出题目（Unit 1 显示 345 道）。
- 练习包类型不可改为普通试卷；新建题目请到源试卷或练习 Topic 维护，不能在练习包上直接新建。
- 把 practice_bundle 移到「单元练习」筛选分类只影响展示类型，不会改变题目来源；Unit 1 当前仍正确显示 345 道。

## 科目分类

Admin 顶部有「内容科目」选择器，默认 `AP Psychology`，保存在当前浏览器：

- 试卷、原始知识点、概念、知识图谱都按所选科目筛选。
- 新建概念、补充知识点、新建题目都归属当前科目。
- 已启用科目可选择；未启用科目显示「未启用」并禁用。
- 当前只有 `psychology` 启用；`statistics` 在 `config/subjects/statistics.json` 中仍为 `enabled: false`。
- 内容 API 通过 `subject=<subject_id>` 传递分类；不传时默认 `psychology`。

## 概念（Concepts）与原始知识点（KPs）的区别

| | 概念 Concepts | 原始知识点 KPs |
|---|---|---|
| 数据表 | `concept_clusters` | `knowledge_points` |
| 来源 | 多个教材/KP 去重聚合 | 具体 book / section / subheading 的一条教材原文 |
| 学生端 | 知识图谱、题目关联、解析实际使用 | 不单独作为图谱节点；用于来源追溯和审校 |
| 关系 | 一个概念可有多个成员 KP | 通过 `concept_cluster_id` / `concept_members` 归属概念 |
| Admin 操作 | 可新建、编辑；Admin 新建 ID 为 `psy-admin-c-*` | 可编辑；暂不从零新建（必须有教材来源） |

### 概念在系统中的作用

- **标准知识点身份**：把多本教材的重复条目去重聚合，学生端只看到一个标准术语。
- **知识图谱节点**：Unit 结构、Topic 思维导图、概念详情，以及关系/易混/相关题目都以概念为节点。
- **题目关联桥梁**：`question_concept_links` 连接题目与概念；core / supporting / confusable 驱动题目解析、知识栏和相关题目。
- **记忆卡片**：卡片池按概念权重和星级出卡，复习进度以概念为单位。
- **教材证据聚合**：一个概念聚合多个原始 KP；KP 保留教材原文/页码/来源，概念负责学生端统一呈现。
- **Admin 内容优先**：Admin 新建/修改概念进入有效内容层，学生端立即生效，并优先于本地同步内容。

> 题目关联的是概念，不是原始 KP。知识图谱编辑器中的「补充知识点」只用于图谱补缺，不进入题目关联。

**选择建议：**

- 新增术语、修改学生端名称/释义、给题目关联知识点 → 使用 **Concepts**。
- 修正教材原文、引文、页码、来源 → 编辑 **KPs**。
- Admin 在知识图谱/题目里看到的「知识点」都是概念层。

## 支持的 Admin 操作

### 题目

- 编辑已有题目：题干、材料、选项、正确答案、解析、答案来源/置信度。
- 设置题目星级：1–5 星，可在试卷题目列表或题目详情直接点选，再次点击同一星清除。
- 新建 MCQ：题干、材料、2–5 个选项、一个正确项。
- 新建题目默认追加到当前试卷；试卷 `question_count` 和 MCQ 配置数量会同步调整。
- 新建题目会出现在试卷题目列表和新的整卷 attempt 中。
- 暂不支持新建 FRQ 评分标准。

### 知识点（概念层）

- 编辑已有概念：名称、描述/释义、Unit、Topic、状态、权重。
- 新建概念：名称、英文释义、Unit、Topic，ID 为 `psy-admin-c-*`，`weight_tier=admin`。
- 新建概念会进入学生端知识库/图谱概念池，可由知识图谱编辑器加入 Topic 导图。

### 知识点（原始 KP 层）

- 编辑已有 KP：名称、plain English、原文 definition、subheading、status、weight。
- 原始 KP 仍保留教材来源和 book/section 关系。
- 暂不从零新建原始 KP；学生端图谱与题目关联使用概念层。

### 题目—知识点关联

- 新增 core / supporting / confusable 关联。
- confusable 关联必须指定干扰项 label。
- 可移除已有或 Admin 新增的关联。
- 关联记录返回 Admin 标记。

### 试卷

- 编辑标题、中文标题、年份、类型；通过覆盖层生效。

## API

```text
GET    /api/v1/admin/content/papers
GET    /api/v1/admin/content/papers/{paper_id}
GET    /api/v1/admin/content/questions?source=&unit=&section=&q=&limit=&offset=
GET    /api/v1/admin/content/questions/{question_id}
POST   /api/v1/admin/content/questions
PATCH  /api/v1/admin/content/questions/{question_id}
PATCH  /api/v1/admin/content/questions/{question_id}/stars
POST   /api/v1/admin/content/questions/{question_id}/concepts
DELETE /api/v1/admin/content/questions/{question_id}/concepts/{link_id}

GET    /api/v1/admin/content/knowledge/concepts?limit=&offset=&q=
GET    /api/v1/admin/content/knowledge/concepts/{cluster_id}
POST   /api/v1/admin/content/knowledge/concepts
PATCH  /api/v1/admin/content/knowledge/concepts/{cluster_id}

GET    /api/v1/admin/content/knowledge/kps?limit=&offset=&q=
GET    /api/v1/admin/content/knowledge/kps/{kp_id}
PATCH  /api/v1/admin/content/knowledge/kps/{kp_id}
```

写接口要求 `super_admin` / `content_editor`，并写入审计日志。

概念/KP 列表使用 `limit + offset` 分页，返回 `total`；`q` 只对名称做模糊搜索，不再搜索释义/主题/来源。

## 冲突规则

1. 同一实体 ID：Admin 覆盖记录优先；新的本地 Release 不会覆盖 Admin 版本。
2. Admin 新建实体：覆盖记录中没有对应 Release 实体时直接插入有效内容。
3. Admin 删除关联：`admin_deleted` 记录在有效内容重建时删除对应关联。
4. 唯一键冲突（例如未来 Release 新增了与 Admin 新建题目相同的试卷题号）目前不自动重排；发布后需要人工检查。

## 知识图谱编辑器

`/content/knowledge-graph` 使用横向思维导图画布：

- 左侧父节点，右侧子节点；曲线/总线连接。
- 卡片按文字换行和动态高度绘制。
- 点击卡片选中，右侧 Inspector 编辑。
- 支持节点展开/收起、缩放、添加子节点、添加分支、更换知识点、上下移动、删除。
- 保存仍写入 `knowledge_graph_topic_drafts`，学生端下一次请求立即生效。

## 验证

- 37 个 API 测试通过，覆盖 Admin 覆盖层、题目/概念/关联创建、Admin 标记、学生端读取和清理。
- Admin `typecheck` / `next build` 通过。
