# 知识图谱

## 1. 功能概览

知识图谱按 Unit 展示 AP Psychology 的概念结构，权限与 Unit 练习一致：

- 免费用户：只能查看 Unit 1 图谱
- 激活用户：显示全部已解锁 Unit
- 未解锁 Unit：只返回标题、Topic 数和题数，不返回概念、关系或题目

学生路径：

```text
Unit 结构
  ↓ 点击 Topic
章节思维导图（XMind 风格，英文知识点）
  ↓ 点击可解析的概念节点
概念详情（定义 / 教材关系 / 真题易混 / Related Questions）
  ↓ 点击易混或关联题
题目只读预览（不能作答、不记录成绩）
```

入口：`/knowledge`。侧边栏和移动端底部导航均有「知识图谱 / 图谱」入口。落地页 `/#graph` 有知识图谱宣传区和 CTA。

## 2. 页面展示

### 2.1 Unit 结构

- 展示该 Unit 的 CED Topic 节点。
- 每个 Topic 默认只露出 3 个核心概念。
- 节点之间显示跨 Topic 桥；桥来自教材关系、真题易混和同题共现。
- 点击 Topic 进入章节思维导图。

### 2.2 章节思维导图

- XMind Logic Chart / 横向知识树风格：Topic 标题卡在最左，一级章节使用分色圆角卡片向右展开，二级/三级知识点使用浅色卡片继续向右展开。
- 卡片高度按文字自动增加，长标签会换行；二级、三级卡片的文字不会被卡片裁掉。
- 一级到二级、二级到三级都从父节点右侧中心连出；多个子节点共用一个垂直分叉线，不再从父节点顶部连接。只有一个子节点时直接中心对中心连接。
- 树很高时图谱区域可上下滚动；滚轮滚动，`Ctrl / Cmd + 滚轮` 缩放，也可以拖动查看。
- 有子节点的卡片左侧有 `+ / −` 折叠按钮；点卡片仍然是查看概念释义，点 `+ / −` 才是展开/收起，两个动作分开。右上角还有全局 `Collapse / Expand`。
- **知识点标签只显示英文**：`The Brain`、`Nervous System`、`Action Potential`、`Structure of the Eye`。PDF 里的中文释义不进入导图。
- 导图层级来自 `心理学思维导图.pdf` 的章节思维导图，并用知识库概念名称做解析；Unit 1 额外做了教材/知识点整理，补齐 PDF 中省略的概念。
- 默认展开全部层级（当前数据最多 5 层：主分支 → 子分支 → 概念 → 子概念）；手动折叠后节点显示 `+N more`，点击该标记或左侧 `+` 按钮即可重新展开。
- 节点只有匹配到当前 Unit 的知识库概念时才可点击；纯结构标签或本 Unit 知识库没有的概念保留英文标签，但不可点击。
- 默认 100% 适配；支持 `− / 100% / + / Fit` 缩放，任何缩放级别都可以拖动；拖动不会误触节点。
- 左上角「返回结构图」回到 Unit 结构；缩放控件在右上角，与返回按钮同一水平线。
- 图谱工具栏有「全屏 / 退出全屏」按钮；全屏使用视口覆盖层，按 Esc 或按钮退出，详情弹窗仍可正常显示。
- 单元/章节标题在单元练习和知识图谱中只显示英文；中文只保留在内容数据里，不作为学生端标题。

### 2.3 节点类型与补充释义

学生端导图节点分三类：

- **结构分支 / branch**：如 `Theories`、`Obstacles`、`Structure of the Eye`。只负责分组，不可点击；分支至少需要一个子节点。
- **知识库概念 / concept**：来自 `concept_clusters`，可点击，显示定义、教材关系、易混题和 Related Questions。
- **补充知识点 / supplement**：知识库没有收录的课程术语，使用 `psy-supp-*`（AI/教材补充）或 `psy-custom-*`（后台人工补充）ID，同样可点击查看释义。

知识库内部还有 `core / supporting / confusable` 三类权重层级；它们是概念与题目的相关性层级，不是并列的节点类型。后台新建的补充知识点使用与 AI 补充相同的 supplement 机制，但来源标为 `admin`，审校状态为 `draft`。

补充释义规则：

- 只对真实的课程术语补释义，不把 `Duration: 1 min`、`Remember things to be done` 这类说明句当知识点。
- 补充释义带 `supplement: true`、`review_status: draft` 和 `AI-assisted explanation · review against the 2027 textbook` 提示。
- 当前 Unit 1–5 的全部叶子节点都已可点击；补充释义统一标记为 draft，等待教材审校。

### 2.3.1 Admin 知识图谱编辑

Admin 新增 `/content/knowledge-graph`：

- 按 Unit / Topic 打开当前 Release 导图；以横向思维导图画布展示，卡片按文字换行、父子节点用总线/分支连接，支持缩放。
- 支持创建、编辑、删除、上移/下移节点；点击卡片在右侧 Inspector 编辑。
- 节点类型为「分支 / 知识库概念 / 补充知识点」；分支可新增，知识节点通过本地搜索选择。
- 搜索范围：当前 Unit 的 `concept_clusters`、已有 supplement、后台补充知识点。搜索不到时可创建补充知识点，填写英文名称和释义。
- 保存写入应用数据库 `knowledge_graph_topic_drafts`，不写 Release 内容库；同一 Topic 保存后学生端下一次请求立即生效。
- 自定义知识点写入 `knowledge_graph_custom_concepts`，可被同一 Unit 后续复用。
- 新表随 `AUTO_CREATE_TABLES=true` 创建；若生产关闭自动建表，需要先补迁移。
- 保存前校验：标签英文、叶子节点必须可点击、分支至少一个子节点、概念必须属于当前 Unit、节点数量/深度上限。
- 同一 Topic 重复知识点会提示但仍可保存，避免误判合法的跨分支复用；建议一个概念只保留一个入口。
- 可「恢复原图」删除该 Topic 草稿，回到 Release 导图。
- 45 个练习 Topic 中 35 个已有 Release 导图；`1.RM` / `1.OT` 等 10 个研究方法/综合 Topic 目前没有导图，可在 Admin 中从空白根节点开始创建。
- 当前不接运行时 LLM：后台创建补充知识点时由管理员填写英文释义，来源记为 `admin`，不会自动生成或伪装成教材原文。

Admin API：

```text
GET    /api/v1/admin/content/knowledge-graph/units
GET    /api/v1/admin/content/knowledge-graph/topic?unit_id=&topic_code=
GET    /api/v1/admin/content/knowledge-graph/search?unit_id=&q=
POST   /api/v1/admin/content/knowledge-graph/custom-concepts
PUT    /api/v1/admin/content/knowledge-graph/topic
DELETE /api/v1/admin/content/knowledge-graph/topic?unit_id=&topic_code=
```

### 2.4 概念详情

点击导图概念节点后，右侧 Inspector 显示：

- 英文定义与教材原文
- 教材关系及证据（`part_of` / `broader_narrower` / `related_to` 等）
- 真题易混概念及出现次数
- Related Questions：只显示 1 / 2 / 3 / 4 数字按钮，不展示题干；点击打开只读题目预览

### 2.5 题目只读预览

- 「真题易混」和「Related Questions」中的题目均可点击。
- 弹窗展示题干、context、图片和选项。
- 选项不可点击；不记录作答、不进入错题本或统计。
- 不返回 `is_correct`、解析或答案文本。
- 题目所属 Unit 或试卷未解锁时，接口返回 403，弹窗提示无权查看。

## 3. 数据流

```text
心理学思维导图.pdf
        ↓  _tools/build_mindmaps.py
apps/api/app/content/data/psychology-mindmaps.json   （英文层级，静态文件）
        ↓
Content Release（exam.db + knowledge.db）
        ↓  ContentStore.unit_mindmaps() 按当前 Release 解析 concept_id
ContentStore.unit_knowledge_graph(unit_id)
        ↓
GET /api/v1/knowledge-graph
GET /api/v1/knowledge-graph/questions/{question_id}
        ↓
/knowledge
```

导图数据不是独立内容库，也不写回 Release：

- `psychology-mindmaps.json` 随 API 代码发布，包含章节/分支/英文标签和可选 canonical concept name。
- API 启动/请求时按当前 Release 的 `concept_clusters` 解析名称；Release 切换后不需要重建层级文件。
- 静态文件不进入 `exam.db` / `knowledge.db`，构建脚本默认只读取 PDF 和只读知识库。
- 构建报告：`data/content/psychology/reports/mindmap_pdf_audit.md`。
- 没有 PDF 导图的 Topic（如研究方法/综合）由前端按 `concept.chapter` 生成同样的 XMind 树，不再退回旧的两栏列表。
- 图谱只返回题号/试卷/角色，不返回题干；题干由只读题目预览接口按需获取，减少首屏 payload。生产 Nginx 对 JSON 开启 gzip。

后端缓存：

- `ContentStore.unit_knowledge_graph()` 使用进程内 LRU 缓存，按 Unit 缓存。
- API 启动时会在 lifespan 中预热所有 Unit 图谱；第一个用户请求不再承担 SQLite 扫描/组装成本。
- 缓存键属于当前 Store/Release；Release 变化会创建新的 Store，旧缓存不会跨 Release 混用。
- 图谱本身与用户无关；接口仍按用户权限过滤 Unit，因此不把带权限的完整响应做公共缓存。
- 关系/概念数据只读，不做数据库写入。

缓存边界：

- 不做浏览器端 `Cache-Control` 公共缓存，避免切换账号/激活状态后看到旧图谱。
- 不缓存带签名 URL 的题目详情（签名会过期）；图谱只缓存概念、关系和题号/试卷/角色元数据。
- 如果未来改为 Redis/多 worker，可把 `unit_knowledge_graph` 的结果按 `release_id + unit_id` 外置；当前单进程 LRU 足够。

## 4. V1 关系模型

首版只使用可解释、可回查的关系，不生成“AI 自由发挥”的边。

| 层 | 来源 | 方向 | 用途 |
|---|---|---|---|
| 章节层级 | `心理学思维导图.pdf` 的矢量连线 + 知识库概念解析 | 树形 | 导图展示：章节 → 分支 → 概念 |
| 教材关系 | `concept_relations`：`part_of` / `broader_narrower` / `related_to` / `same_name_different_sense` | 有向 | 定义、组成、上下位 |
| 真题易混 | 同一道 MCQ 中的 `core` 概念与 `confusable` 选项概念 | 对称 | 易混辨析、题目关联 |
| 同题共现 | 同一道 MCQ 中的 `core` 与 `supporting` 概念 | 对称 | 考试关联、Topic 桥 |

约束：

- 关系边带 `source_type`、`weight`、`evidence`。
- Topic 导图本身只展示概念层级；教材关系和易混关系在 Inspector 中展示。
- API 仍保留 Topic 内的关系边供结构桥和后续视图使用；当前导图不直接绘制这些边。
- Topic 边最多保留较强的易混边和同题边：contrast `weight >= 3`，共现 `weight >= 2`，并分别限制数量。
- 当前不生成前置依赖、同框架边、跨单元因果。
- 前置依赖不能从 `part_of` 自动推断成“先学 A 再学 B”。
- PDF 章节层级只用于“怎么摆导图”，不表示正式的前置依赖；两者不要混用。
- Unit 1 的层级经过人工整理，补入 PDF 未列出的教材概念；Unit 2–5 以 PDF 解析结果为主并做描述句清理。
- 导图节点只匹配**当前 Unit** 的知识库概念；例如 Unit 1 的 Hippocampus 仍显示英文标签，但不会越权打开 Unit 2 的概念数据。

### Unit 1 关系审计

当前 Unit 1 的显式关系规模：

| 层 | 数量 |
|---|---:|
| 教材显式关系 | 35（26 条 part_of、8 条 broader_narrower、1 条 related_to） |
| 真题易混（weight >= 2） | 82 |
| 同题共现 | 154 |
| 跨章节教材关系 | 5 |
| 跨章节真题易混 | 7 |
| 跨章节同题共现 | 18 |

完整审计记录：`data/content/psychology/reports/unit1_relation_audit.md`

后续如果要增加教材前置关系，应先形成候选边并保留教材原文证据，不直接让模型写正式图。

## 5. 权限规则

与 `config/entitlements/psychology.json` 和 `UserEntitlement` 共用：

- `free_unit_ids`: 当前为 `["1"]`
- 激活状态：subject-level entitlement
- Unit 练习题：按所属 Unit 权限
- 真题：按试卷权限（`free_paper_ids` 或激活）

接口：

| 接口 | 行为 |
|---|---|
| `GET /api/v1/knowledge-graph` | 返回所有 Unit 元数据；只对已解锁 Unit 返回 `topics` / `mindmap` / `mindmap_concepts` / `bridges` |
| `GET /api/v1/knowledge-graph/questions/{question_id}` | 只读题目预览；检查 Unit / 试卷权限；不含答案 |

两个接口都需要登录。`/api/v1/knowledge-graph` 已加入内容加密前缀。未解锁 Unit 不返回任何 `mindmap`、`mindmap_concepts` 或概念数据。

## 6. API 响应概要

`GET /api/v1/knowledge-graph`：

```json
{
  "release_id": "content-...",
  "subject_id": "psychology",
  "units": [
    {
      "unit_id": "1",
      "title": "心理学 Unit 1 单元练习",
      "title_en": "Biological Bases of Behavior",
      "topic_count": 8,
      "question_count": 342,
      "locked": false,
      "concept_count": 197,
      "topics": [
        {
          "code": "1.4",
          "title_en": "The Brain",
          "concepts": [
            {
              "concept_id": "psy-...",
              "name": "Hypothalamus",
              "tier": "core",
              "chapter": "The Brain",
              "definition": "...",
              "relations": [],
              "contrast": [],
              "samples": []
            }
          ],
          "edges": []
        }
      ],
      "bridges": []
    }
  ]
}
```

`edges` 只返回当前 Topic 内可展示的教材 / 易混 / 同题边。`samples` 和 `contrast[].questions` 只返回题号、试卷和角色，不返回题干；题干由只读预览接口按需获取。

Topic 还带 `mindmap`：

```json
{
  "label": "Interaction of Heredity and Environment",
  "node_count": 25,
  "matched_count": 21,
  "children": [
    {
      "label": "Behavioral Genetics",
      "children": [
        {"label": "Genes", "concept_id": "psy-...", "concept_name": "Genes"}
      ]
    }
  ]
}
```

- `label` 只含英文；结构节点没有 `concept_id`。
- `node_count` 统计除根节点外的导图节点；`matched_count` 统计能解析到概念的节点。
- 深层节点在 JSON 中保留；前端默认展开全部层级，可用节点 `+ / −`、`+N more` 标记或全局 Collapse / Expand 展开收起。

Unit 级 `mindmap_concepts` 是“导图出现的、但没有进入任何练习 Topic 的概念”详情，前端用它与 Topic 概念一起构成概念索引：

```json
{
  "mindmap_concepts": {
    "psy-...": {
      "concept_id": "psy-...",
      "name": "Genes",
      "definition": "...",
      "topic_code": "1.1",
      "supplement": false
    }
  }
}
```

## 7. 当前覆盖范围

| Unit | 图谱概念数 | Topic 数 | PDF/教材导图 |
|---|---:|---:|---|
| Unit 1 | 197 | 8 | 6 个章节导图 + 研究方法/综合 fallback |
| Unit 2 | 148 | 10 | 4 个章节导图 |
| Unit 3 | 170 | 11 | 2 个章节导图，拆分 9 个 Topic |
| Unit 4 | 153 | 9 | 6 个章节导图 |
| Unit 5 | 132 | 7 | 3 个章节导图 |

Unit 1 的 197 个概念 = 练习 Topic 已映射的 127 个 + 导图引用、通过 `mindmap_concepts` 补充的 70 个。Unit 1 的用户可见导图节点数：

| Topic | 节点数 | 可点击概念 |
|---|---:|---:|
| 1.1 Heredity & Environment | 25 | 21 |
| 1.2 Nervous System & Endocrine | 25 | 24 |
| 1.3 Neuron & Neural Firing | 31 | 27 |
| 1.4 The Brain | 44 | 40 |
| 1.5 Sleep | 24 | 21 |
| 1.6 Sensation | 56 | 45 |

Unit 2–5 没有进入练习 Topic 的概念，同样只作为可点击的 `mindmap_concepts` 补充，不会生成孤立的结构图节点。

当前可点击性：

- Unit 1–5：全部叶子节点可点击（知识库概念或补充释义）。
- 补充释义数量：Unit 1 / 2 / 3 / 4 / 5 = 30 / 33 / 35 / 41 / 26。
- Unit 2.2 已去除重复的 `Framing` / `Mental Set`，并重新整理为 Theories / Problem Solving / Obstacles / Decision Making / Creativity。
- 补充释义均为 `review_status: draft`，仍需对照 2027 教材审校。

## 8. 代码位置

| 层 | 文件 |
|---|---|
| PDF 导图解析/整理 | `_tools/build_mindmaps.py` |
| 静态导图层级 | `apps/api/app/content/data/psychology-mindmaps.json` |
| 导图审计报告 | `data/content/psychology/reports/mindmap_pdf_audit.md` |
| 图谱生成 | `apps/api/app/content/store.py` → `unit_knowledge_graph()` + `unit_mindmaps()` |
| 图谱 / 题目 API | `apps/api/app/api/v1/content.py` |
| Admin 图谱 API | `apps/api/app/api/v1/admin_graph.py` |
| Admin 草稿/搜索/校验 | `apps/api/app/services/knowledge_graph.py` |
| 草稿与补充知识点表 | `apps/api/app/users/models.py` → `knowledge_graph_topic_drafts` / `knowledge_graph_custom_concepts` |
| 权限 | `apps/api/app/services/entitlements.py` |
| API 测试 | `apps/api/tests/test_smoke.py` |
| 前端页面 | `apps/web/src/app/knowledge/page.tsx` |
| 图谱组件 | `apps/web/src/components/KnowledgeGraph.tsx` |
| 图谱样式 | `apps/web/src/components/KnowledgeGraph.module.css` |
| 只读题目组件 | `apps/web/src/components/QuestionView.tsx`（`readOnly`） |
| 前端类型 | `apps/web/src/lib/types.ts` |
| Admin 图谱页面 | `apps/admin/src/app/(admin)/content/knowledge-graph/page.tsx` |
| Admin 类型 | `apps/admin/src/lib/types.ts` |
| 落地页宣传 | `apps/web/src/app/page.tsx` → `#graph` |
| 加密前缀 | `apps/api/app/core/config.py`、`apps/web/src/lib/api.ts` |

Admin 内容覆盖层说明见 `docs/admin-content.md`。

## 9. 验证

已覆盖：

- 免费用户只返回 Unit 1 图谱；其余 Unit 只返回 locked 元数据，不返回 `mindmap` / `mindmap_concepts`
- 激活用户返回全部 Unit 图谱
- 导图节点标签英文；测试会拒绝 CJK 字符
- 导图节点 `concept_id` 必须能在 Topic 概念或 `mindmap_concepts` 中找到
- Admin 保存 Topic 草稿后学生端立即读到新树；删除草稿后恢复 Release 原图
- 35 个 Release 导图全部通过 Admin 保存校验（含弯引号/破折号归一化为 ASCII）
- Admin 创建补充知识点后可搜索到，并在学生端以 `review_status=draft` 展示
- 图谱 payload 不含题目答案
- 题目预览对 Unit 练习题按 Unit 权限校验，对真题按试卷权限校验
- 只读预览选项不可点击，不记录作答
- 前端 `typecheck`、`next build` 通过
- 移动端和暗色模式无页面级横向溢出（图谱内部允许横向查看）
- Playwright 验证结构图、导图、缩放、拖动、返回结构图、Unit 标签复位、导图概念点击和题目弹窗

后端测试：`cd apps/api && PYTHONPATH=. .venv/bin/pytest -q`

## 10. 暂不做

- Admin 编辑知识库概念之间的关系边（当前只编辑 Topic 树和补充知识点）
- 运行时 LLM 自动生成关系或释义（Admin 人工填写补充释义）
- 跨单元知识路径
- Neo4j / 图数据库
- 全量 225 个教材概念视图

下一步：

1. 审校 165 条补充释义（30 + 33 + 35 + 41 + 26），把 `review_status: draft` 逐条改为 `reviewed`。
2. 全量关系审计：同一 Topic 下不允许重复 normalized 标签；`Framing` / `Mental Set` 这类重复已在 Unit 2.2 修正；其他 Topic 继续人工复核。
3. 用 Admin 图谱编辑器清理剩余重复项（当前 Unit 4.1 的 `Self-fulfilling prophecy`、Unit 5.4 的 `Etiology` / `Neurochemical Factors` 等会显示重复提示）。
4. 评估把 `mindmap_concepts` 改成按需详情接口，降低首屏 payload。
5. 教材关系审校后，再做按章节的高价值知识关联路径。
