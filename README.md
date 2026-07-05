# ManuTrace

ManuTrace is a traceable manuscript writing and submission build toolkit for Chinese journal papers.

It keeps citations, statistical numbers, evidence claims, and generated manuscript artifacts auditable by using structured markdown tokens and strict build-time checks.

## What It Does

- Renders citation tokens such as `{{cite:ref_key}}` into ordered numeric citations.
- Renders number tokens such as `{{num:freeze#stats.total}}` from frozen data files.
- Fails on dangling citations, orphan references, candidate-only references, and missing data paths.
- Builds evidence maps from structured literature summaries and claim registries.
- Checks author-approved outlines before drafting.
- Generates section-level citation/number coverage reports.
- Builds numbered markdown and docx artifacts while keeping source markdown as the editable truth.

## Install From Source

```powershell
$env:PYTHONUTF8="1"
python -m pip install .
manutrace --help
```

## Basic Workflow

```powershell
manutrace init <project_dir> --journal-id <id> --journal-name <name>
manutrace extract-rules <submission_guide.txt> --out <project_dir>/rules/journal.json --audit <project_dir>/rules/journal_audit.md
manutrace summaries check --refs <project_dir>/library/references.json --summaries <project_dir>/library/summaries --strict
manutrace evidence-map --refs <project_dir>/library/references.json --claims <project_dir>/evidence/claims.json --summaries <project_dir>/library/summaries --out <project_dir>/evidence/evidence_map.md
manutrace outline check --outline <project_dir>/outline.md --claims <project_dir>/evidence/claims.json --require-approved
manutrace coverage --src <project_dir>/src/draft.src.md --refs <project_dir>/library/references.json --out <project_dir>/builds/coverage.md --strict
manutrace pipeline --src <project_dir>/src/draft.src.md --refs <project_dir>/library/references.json --assets <project_dir>/src/assets.json --manuscript-out <project_dir>/builds/draft.md --docx-out <project_dir>/builds/draft.docx --docx-builder <builder.py> --change-note "manuscript build"
```

## Codex Skill

The Codex skill is included at:

```text
skills/manutrace/
```

Use `$manutrace` for traceable Chinese journal manuscript drafting, review, evidence mapping, and build workflows.

## Status

This is an alpha release. The CLI is useful for controlled manuscript projects, but APIs and file schemas may still change before `0.1.0`.

## License

MIT
