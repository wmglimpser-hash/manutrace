# -*- coding: utf-8 -*-
"""初始化 paper-trace 初稿项目目录。

用法：$env:PYTHONUTF8="1"; python tools/pwt/pwt_init.py <project_dir> \
        --journal-id journal-demo --journal-name 示例期刊
"""
import argparse
import json
from datetime import datetime
from pathlib import Path


DIRS = [
    "input/project",
    "input/refs",
    "library/verified",
    "library/provisional",
    "library/candidates",
    "library/summaries",
    "library/reports",
    "evidence",
    "rules",
    "src",
    "builds",
]


def write_if_missing(path, text, force=False):
    if path.exists() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return "created" if not path.exists() else "written"


def main():
    ap = argparse.ArgumentParser(description="初始化 paper-trace 初稿项目目录")
    ap.add_argument("project_dir", type=Path, help="稿件项目目录")
    ap.add_argument("--journal-id", default="unknown", help="期刊规则包 id")
    ap.add_argument("--journal-name", default="待定期刊", help="期刊名称")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的种子文件")
    args = ap.parse_args()

    root = args.project_dir.resolve()
    created_dirs = []
    for rel in DIRS:
        path = root / rel
        path.mkdir(parents=True, exist_ok=True)
        keep = path / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8", newline="\n")
        created_dirs.append(rel)

    refs = {
        "version": 2,
        "entries": [],
        "notes": "pool=verified/provisional/candidate；candidate 不得被 cite token 引用。",
    }
    journal = {
        "version": 1,
        "journal_id": args.journal_id,
        "name": args.journal_name,
        "source_files": [],
        "body_min_cjk": None,
        "body_max_cjk": None,
        "abstract_max_cjk": None,
        "citation_style": None,
        "reference_min": None,
        "reference_recommended": None,
        "section_hint": [],
        "figure_rules": [],
        "tone_notes": "",
        "rules": [],
    }
    manifest = {
        "version": 1,
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "layout": "draft_writing_workflow_design.md v0.2 + W2 evidence workflow",
        "protected_inputs": ["input/"],
        "notes": "input/ 全区只读；构建产物写入 builds/；不要覆盖作者原始文件。",
    }
    claims = {
        "version": 1,
        "claims": [
            {
                "claim_id": "c_example_001",
                "section": "",
                "claim": "",
                "required": True,
                "needs_literature": True,
                "needs_data": False,
                "literature": [],
                "data": [],
            }
        ],
    }

    seed_files = {
        "library/references.json": json.dumps(refs, ensure_ascii=False, indent=2) + "\n",
        "evidence/claims.json": json.dumps(claims, ensure_ascii=False, indent=2) + "\n",
        "rules/journal.json": json.dumps(journal, ensure_ascii=False, indent=2) + "\n",
        "outline.md": "# 论文大纲\n\n> 大纲是 A 类决策；作者确认后再进入全稿撰写。\n",
        "README.md": (
            "# paper-trace 稿件项目\n\n"
            "- `input/`：作者供给区，只读。\n"
            "- `library/verified/`：已核实文献，可引用。\n"
            "- `library/provisional/`：全文可读但待作者终核文献，可暂准引用。\n"
            "- `library/candidates/`：候选/待下载/存疑文献，不得直接引用。\n"
            "- `library/summaries/`：结构化文献摘要与锚点。\n"
            "- `library/reports/`：检索报告与候选转正依据。\n"
            "- `evidence/claims.json`：论点清单与证据需求。\n"
            "- `rules/journal.json`：期刊规则包。\n"
            "- `src/`：token 化初稿源文件，唯一编辑对象。\n"
            "- `builds/`：构建产物和日志，不手改。\n"
        ),
        "pwt_project.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    }

    file_results = []
    for rel, text in seed_files.items():
        path = root / rel
        existed = path.exists()
        if existed and not args.force:
            file_results.append((rel, "skipped"))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        file_results.append((rel, "overwritten" if existed else "created"))

    print(f"项目目录: {root}")
    print("目录:")
    for rel in created_dirs:
        print(f"  {rel}")
    print("种子文件:")
    for rel, status in file_results:
        print(f"  {status}: {rel}")
    print("PASS: pwt init 完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
