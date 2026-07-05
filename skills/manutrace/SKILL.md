---
name: manutrace
description: 稿迹 ManuTrace：中文期刊论文写作与投稿构建工作流。用于从主题、项目材料、冻结数据、参考文献生成或审查可追溯稿件，执行 cite/num token、文献 A/B/C 分级、证据地图、大纲门禁、覆盖率报告、md/docx 构建日志，防止孤立引用、乱序编号、无源数字和覆盖原稿。
---

# 稿迹 ManuTrace

Use this skill for Chinese journal manuscript work where citations, numbers, evidence, and build outputs must be traceable.

Before running a full manuscript workflow, cold-start drafting, reference promotion, outline approval, coverage reporting, or delivery packaging, read [references/workflow.md](references/workflow.md).

## Core Rules

1. Treat tokenized markdown in `src/` as the only editable manuscript source.
2. Treat numbered markdown and docx as build artifacts; never hand-edit them.
3. Cite only with `{{cite:ref_key}}`; `ref_key` must be in the `verified` or `provisional` pool.
4. Write project statistics only with `{{num:alias#file.path}}` pointing to frozen data.
5. Keep `verification` private; rendered output may read only `rendered_text`, `status`, and `pool`.
6. Keep `input/` and user-supplied original docx files read-only.
7. Stop for A-class decisions: semantic manuscript changes, adding/removing references, external submission, and outline approval.
8. Produce new files plus a change note for every manuscript/docx change.

## Standard Command Chain

Install ManuTrace before running the command chain. Use the wheel attached to the release, or install
from a local clone of the ManuTrace repository:

```powershell
$env:PYTHONUTF8="1"
python -m pip install manutrace-0.1.0a1-py3-none-any.whl
manutrace --help
```

```powershell
$env:PYTHONUTF8="1"
manutrace init <project_dir> --journal-id <id> --journal-name <name>
manutrace extract-rules <submission_guide.txt> --out <project_dir>/rules/journal.json --audit <project_dir>/rules/journal_audit.md
manutrace summaries init --refs <project_dir>/library/references.json --out-dir <project_dir>/library/summaries --usable-only
manutrace summaries check --refs <project_dir>/library/references.json --summaries <project_dir>/library/summaries --strict
manutrace evidence-map --refs <project_dir>/library/references.json --claims <project_dir>/evidence/claims.json --summaries <project_dir>/library/summaries --out <project_dir>/evidence/evidence_map.md
manutrace outline check --outline <project_dir>/outline.md --claims <project_dir>/evidence/claims.json --require-approved
manutrace coverage --src <project_dir>/src/draft.src.md --refs <project_dir>/library/references.json --out <project_dir>/builds/coverage.md --strict
manutrace pipeline --src <project_dir>/src/draft.src.md --refs <project_dir>/library/references.json --assets <project_dir>/src/assets.json --manuscript-out <project_dir>/builds/draft.md --docx-out <project_dir>/builds/draft.docx --docx-builder <builder.py> --change-note "manuscript build"
```

## Delivery Package

Return the tokenized source, numbered markdown, docx, evidence map, coverage report, final-review list for provisional citations, download list for candidate/B-level literature, and raw validation output. Record validation conclusions in the project ledgers required by the repository.
