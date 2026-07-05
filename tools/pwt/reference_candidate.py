# -*- coding: utf-8 -*-
"""检索报告模板与候选文献转正（W2）。

用法：
  $env:PYTHONUTF8="1"; python tools/pwt/reference_candidate.py template --ref-key cand01 --out library/reports/cand01_search_report.md
  $env:PYTHONUTF8="1"; python tools/pwt/reference_candidate.py promote --refs library/references.json --candidate candidate.json --access-level A_fulltext --pool provisional --out library/references.next.json
"""
import argparse
import json
from datetime import date
from pathlib import Path


ACCESS_LEVELS = {"A_fulltext", "B_abstract", "C_unverified"}
ALLOWED_POOLS = {"verified", "provisional", "candidate"}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def cmd_template(args):
    ref_key = args.ref_key
    title = args.title or ""
    lines = [
        f"# 检索报告：{ref_key}",
        "",
        f"- date: {date.today().isoformat()}",
        f"- ref_key: `{ref_key}`",
        f"- title: {title}",
        "- access_level: A_fulltext | B_abstract | C_unverified",
        "- recommended_pool: provisional | candidate",
        "",
        "## 题录",
        "",
        "- rendered_text:",
        "- authors:",
        "- year:",
        "- source_url:",
        "- doi:",
        "",
        "## 检索过程",
        "",
        "| 渠道 | 检索式 | 结果 | 链接/备注 |",
        "|---|---|---|---|",
        "|  |  |  |  |",
        "",
        "## 可及性分级",
        "",
        "- A_fulltext：全文可读，可生成结构化摘要，转 provisional，交付进终核清单。",
        "- B_abstract：仅题录/摘要，不得引用，留 candidate，进待下载清单。",
        "- C_unverified：真实性未确认或来源存疑，不得引用，留 candidate 或拒绝入库。",
        "",
        "## 摘要锚点",
        "",
        "- p1: page= paragraph= note=",
        "",
        "## 转正建议",
        "",
        "- decision:",
        "- reason:",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"saved: {args.out}")
    print("PASS: 检索报告模板生成完成")
    return 0


def normalize_candidate(data, access_level, pool):
    required = ["ref_key", "rendered_text"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return None, [f"候选缺字段: {', '.join(missing)}"]
    if access_level not in ACCESS_LEVELS:
        return None, [f"access_level 非法: {access_level}"]
    if pool not in ALLOWED_POOLS:
        return None, [f"pool 非法: {pool}"]
    if access_level == "A_fulltext" and pool == "candidate":
        return None, ["A_fulltext 应转 provisional 或 verified；若暂不引用请保留在 candidates 文件夹"]
    if access_level in {"B_abstract", "C_unverified"} and pool in {"verified", "provisional"}:
        return None, [f"{access_level} 不得转入可引用池 {pool}"]

    entry = dict(data)
    entry["status"] = entry.get("status") or "active"
    entry["pool"] = pool
    verification = dict(entry.get("verification") or {})
    verification.setdefault("todos", [])
    verification["access_level"] = access_level
    verification.setdefault("note", "")
    if access_level == "A_fulltext" and pool == "provisional":
        todos = list(verification.get("todos") or [])
        marker = "作者终核全文锚点与题录后转 verified"
        if marker not in todos:
            todos.append(marker)
        verification["todos"] = todos
    if access_level in {"B_abstract", "C_unverified"}:
        entry["status"] = "draft"
    entry["verification"] = verification
    return entry, []


def cmd_promote(args):
    refs = load_json(args.refs)
    candidate = load_json(args.candidate)
    entry, errors = normalize_candidate(candidate, args.access_level, args.pool)
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1

    ref_key = entry["ref_key"]
    entries = refs.setdefault("entries", [])
    replaced = False
    for i, existing in enumerate(entries):
        if existing.get("ref_key") == ref_key:
            entries[i] = entry
            replaced = True
            break
    if not replaced:
        entries.append(entry)

    write_json(args.out, refs)
    print(f"ref_key: {ref_key}")
    print(f"pool: {entry['pool']}")
    print(f"status: {entry['status']}")
    print("action: replaced" if replaced else "action: appended")
    print(f"saved: {args.out}")
    print("PASS: 候选转正完成")
    return 0


def main():
    ap = argparse.ArgumentParser(description="检索报告模板与候选文献转正")
    sub = ap.add_subparsers(dest="cmd", required=True)

    tmpl = sub.add_parser("template", help="生成检索报告模板")
    tmpl.add_argument("--ref-key", required=True, help="候选 ref_key")
    tmpl.add_argument("--title", help="题名")
    tmpl.add_argument("--out", required=True, type=Path, help="输出 markdown")
    tmpl.set_defaults(func=cmd_template)

    promote = sub.add_parser("promote", help="将候选写入/更新 references.json")
    promote.add_argument("--refs", required=True, type=Path, help="references.json")
    promote.add_argument("--candidate", required=True, type=Path, help="候选 entry JSON")
    promote.add_argument("--access-level", required=True, choices=sorted(ACCESS_LEVELS), help="A/B/C 可及性")
    promote.add_argument("--pool", required=True, choices=sorted(ALLOWED_POOLS), help="目标 pool")
    promote.add_argument("--out", required=True, type=Path, help="输出 references.json")
    promote.set_defaults(func=cmd_promote)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
