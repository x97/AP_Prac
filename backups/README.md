# 数据库备份

> 这里存放 `ap_exam.db` / `ap_knowledge.db` 的历史备份，命名格式：

```text
<db>.bak-<YYYYMMDD-HHMMSS>-<reason>
```

- 这些文件只用于回滚/审计，不被脚本读取。
- 当前使用的数据库仍在项目根目录：`ap_exam.db`、`ap_knowledge.db`。
- 恢复时先停掉写入，复制备份覆盖当前库，再跑 `PRAGMA integrity_check` / `foreign_key_check`。
