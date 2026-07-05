# ManuTrace Workflow Reference

## Project Modes

Use the standard mode when the author provides project materials, frozen data, target journal requirements, and references.

Use cold-start mode when the author provides only a topic or title:

1. Confirm the research question, target journal, and article type.
2. Build the literature foundation first with A/B/C access grading.
3. Write result sections only after data freeze is available.
4. Use `[待实验数据]` placeholders for unavailable project results; strict coverage must fail until these are cleared.

## Directory Contract

`manutrace init` creates the manuscript project skeleton:

```text
input/                  read-only author materials
library/references.json reference registry with private verification metadata
library/summaries/      structured literature summaries
library/reports/        search reports and candidate audits
rules/journal.json      target journal rule package
evidence/claims.json    claim registry
evidence/evidence_map.md derived evidence map
src/                    tokenized manuscript source
builds/                 generated artifacts and logs
outline.md              author-approved writing outline
```

Do not overwrite files in `input/`. Do not overwrite a supplied manuscript docx used as a comparison baseline.

## Literature Access Grading

Use the reference pools consistently:

- `verified`: author- or source-verified; may be cited.
- `provisional`: full text was accessible to the agent and summarized with anchors; may be cited, but must appear in the final-review list.
- `candidate`: not citable.

Use access levels consistently:

- A/full text accessible: generate a structured summary with anchors; promote only to `provisional` unless the author has verified it.
- B/metadata or abstract only: keep in `candidate`; include in the download list.
- C/existence or authenticity uncertain: keep in `candidate` with a warning; never cite.

Never write claims from a title or abstract as if they came from full text.

## Evidence And Outline Gate

Every important factual claim in an outline must map to a `claim_id` in `evidence/claims.json`.

Use this outline shape:

```markdown
## 2.1 Section Title

- status: approved
- claim_id: claim_background_digitization
- evidence_refs: ref_a,ref_b
- evidence_nums: {{num:freeze#stats.total}}
- draft_note: writing intent
```

Run `manutrace outline check --require-approved` before drafting. If any required claim lacks literature evidence or data evidence, do not proceed to body drafting.

## Writing Gate

Write in `src/*.src.md` only.

Use:

- `{{cite:ref_key}}` for citations.
- `{{num:alias#file.path}}` for project statistics.
- `[作者确认: ...]` only for author-verifiable wording or missing administrative facts.
- `[待实验数据]` only for missing project results in cold-start or incomplete experimental work.

Do not include mechanism explanations, AI self-description, or validation narration in manuscript body text. Put them in delivery reports.

## Validation And Delivery

Run at least:

1. `manutrace outline check --require-approved`.
2. `manutrace coverage --strict`.
3. `manutrace pipeline` with new output paths and a change note.
4. Project-specific manuscript checks where available.

The delivery package must include:

- tokenized source,
- numbered markdown,
- docx,
- evidence map,
- coverage report,
- final-review list for `provisional` citations,
- download list for `candidate` or B-level references,
- raw command outputs,
- a change note explaining what changed and why.

Update the repository ledgers required by the project handoff protocol.
