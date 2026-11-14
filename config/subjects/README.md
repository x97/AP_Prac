# Subject configuration

Every content subject has one directory under `data/content/<subject_id>/`:

```text
data/content/
  psychology/
    psychology_exam.db
    psychology_knowledge.db
    assets/
  statistics/
    statistics_exam.db
    statistics_knowledge.db
    assets/
```

Each `config/subjects/<subject_id>.json` declares:

| Field | Meaning |
|---|---|
| `subject_id` | Stable subject key |
| `enabled` | Include in the merged Release |
| `source_dir` | Subject source directory |
| `exam_db` | Subject question database |
| `knowledge_db` | Subject knowledge database |
| `asset_root` | Subject asset root |
| `exam_config` | Exam format config |
| `practice_topics` | Practice topic config |
| `exclusions` | Excluded question config |

Release building merges all `enabled` subjects into one `exam.db` and one `knowledge.db`.

Do not put multiple subjects' rows in the same subject source database. The subject source is the unit of content ownership.

`statistics` is currently `enabled: false`. Its three content configs exist as empty placeholders:

```text
config/exam_formats/statistics.json
config/practice_topics/statistics.json
config/content_exclusions/statistics.json
```

Fill them before enabling the subject; an empty topic config will not produce a usable practice release.

The merged Release is activated through one global pointer:

```text
data/releases/active -> content-YYYYMMDD-NNN
```

`release.json` lists enabled subjects in `subjects`; `data/releases/current` is kept as a compatibility alias.
