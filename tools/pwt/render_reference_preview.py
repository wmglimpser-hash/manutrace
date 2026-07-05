# -*- coding: utf-8 -*-
"""从 references v2 metadata 生成 GB/T 7714 预览文本并输出 audit。"""
import argparse
import json
from pathlib import Path

from parse_references import audit_markdown, render_reference


def main():
    ap = argparse.ArgumentParser(description="metadata -> structured reference preview")
    ap.add_argument("--refs", required=True, help="references v2 JSON")
    ap.add_argument("--audit-out", required=True, help="audit markdown 输出路径")
    args = ap.parse_args()

    with open(args.refs, encoding="utf-8") as f:
        data = json.load(f)

    for entry in data["entries"]:
        structured = render_reference(entry)
        warnings = list(entry.get("render_check", {}).get("parse_warnings") or [])
        if structured is None:
            warnings.append("结构化重渲染字段不足")
        entry["render_check"] = {
            "structured_text": structured,
            "matches_rendered_text": structured == entry["rendered_text"],
            "parse_warnings": warnings,
        }

    out = Path(args.audit_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(audit_markdown(data), encoding="utf-8", newline="\n")

    total = len(data["entries"])
    matched = sum(1 for e in data["entries"] if e["render_check"]["matches_rendered_text"])
    print(f"文献条目: {total} 条")
    print(f"结构化重渲染逐字一致: {matched}/{total}")
    print(f"audit: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
