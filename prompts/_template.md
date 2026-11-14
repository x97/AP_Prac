---
id: <stable-prompt-id>
title: <中文标题>
version: <prompt-family>-v1
status: draft
kind: extraction | integration | linking | ingestion | generation | orchestration
updated: YYYY-MM-DD
inputs: [<input1>, <input2>]
outputs: [<table_or_file>]
depends_on: []
used_by: []
superseded_by: null
---

# <中文标题>

> 版本：`<prompt-family>-v1`  
> 用途：  
> 适用：  
> 核心约束：

---

## 一、任务参数

```text
【任务参数】
- 学科 subject_id：
- 数据库路径：
- 范围：
- 模式：盘点 / dry-run / apply
- 是否重建页面：
- 其他要求：
```

---

## 二、提示词正文

```text
# ROLE

# INPUTS

# NON-NEGOTIABLE RULES

# PIPELINE — 按顺序执行，每步有 GATE

## Stage 0 — 盘点
GATE G0：

## Stage 1 — 计划/diff
GATE G1：

## Stage 2 — staging
GATE G2：

## Stage 3 — QA
GATE G3：

## Stage 4 — 写库
GATE G4：

## Stage 5 — 验证与报告
GATE G5：

# OUTPUT CONTRACT

# STOP CONDITIONS

# FINAL CHECKLIST
[ ]
```

---

## 三、本项目实现映射

- 相关脚本：
- 相关表：
- 相关报告：

---

## 四、最短使用方式

```text
请按 <文件名> 执行。
范围：...
模式：先盘点 + dry-run
```
