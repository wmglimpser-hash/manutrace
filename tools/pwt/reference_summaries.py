# -*- coding: utf-8 -*-
"""结构化文献摘要骨架生成与校验（W2）。

用法：
  $env:PYTHONUTF8="1"; python tools/pwt/reference_summaries.py init --refs library/references.json --out-dir library/summaries
  $env:PYTHONUTF8="1"; python tools/pwt/reference_summaries.py check --refs library/references.json --summaries library/summaries --strict
"""
import argparse
import json
from pathlib import Path


SUMMARY_FIELDS = ["research_question", "method", "data_scope", "findings", "limitations", "relevance"]
ACCESS_LEVELS = {"A_fulltext", "B_abstract", "C_unverified"}
USABLE_POOLS = {"verified", "provisional"}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def ref_title(entry):
    meta = entry.get("metadata") or {}
    if meta.get("title"):
        return meta["title"]
    rendered = entry.get("rendered_text", "")
    parts = rendered.split("．", 2)
    return parts[1] if len(parts) > 1 else ""


def summary_skeleton(entry):
    return {
        "version": 1,
        "ref_key": entry["ref_key"],
        "access_level": "A_fulltext" if entry.get("pool", "verified") in USABLE_POOLS else "B_abstract",
        "source_file": "",
        "source_url": "",
        "bibliographic_note": ref_title(entry),
        "anchors": [
            {
                "anchor_id": "p1",
                "page": "",
                "paragraph": "",
                "quote": "",
                "note": "",
            }
        ],
        "summary": {field: "" for field in SUMMARY_FIELDS},
        "claims_supported": [],
        "extraction_warnings": [],
    }


def cmd_init(args):
    refs = load_json(args.refs)
    out_dir = args.out_dir
    created = skipped = 0
    for entry in refs.get("entries", []):
        if entry.get("status") != "active":
            continue
        pool = entry.get("pool", "verified")
        if args.usable_only and pool not in USABLE_POOLS:
            continue
        out = out_dir / f"{entry['ref_key']}.json"
        if out.exists() and not args.force:
            skipped += 1
            continue
        write_json(out, summary_skeleton(entry))
        created += 1
    print(f"摘要骨架目录: {out_dir.resolve()}")
    print(f"created: {created}")
    print(f"skipped: {skipped}")
    print("PASS: 摘要骨架生成完成")
    return 0


def summary_files(path):
    if path.is_file():
        return [path]
    return sorted(path.glob("*.json"))


def cmd_check(args):
    refs = load_json(args.refs)
    entries = {e["ref_key"]: e for e in refs.get("entries", [])}
    errors, warns = [], []
    seen_files = 0

    for path in summary_files(args.summaries):
        seen_files += 1
        try:
            data = load_json(path)
        except json.JSONDecodeError as e:
            errors.append(f"{path}: JSON 解析失败: {e}")
            continue

        ref_key = data.get("ref_key")
        if not ref_key:
            errors.append(f"{path}: 缺 ref_key")
            continue
        if ref_key not in entries:
            errors.append(f"{path}: ref_key 不在 references.json: {ref_key}")
            continue

        access = data.get("access_level")
        if access not in ACCESS_LEVELS:
            errors.append(f"{path}: access_level 非法: {access}")

        entry = entries[ref_key]
        pool = entry.get("pool", "verified")
        if access in {"B_abstract", "C_unverified"} and pool in USABLE_POOLS:
            warns.append(f"{path}: {access} 摘要对应可引用池 {pool}，需确认是否应降为 candidate")

        anchors = data.get("anchors") or []
        if not anchors:
            errors.append(f"{path}: 缺 anchors")
            anchor_ids = set()
        else:
            anchor_ids = set()
            for anchor in anchors:
                aid = anchor.get("anchor_id")
                if not aid:
                    errors.append(f"{path}: anchor 缺 anchor_id")
                    continue
                if aid in anchor_ids:
                    errors.append(f"{path}: anchor_id 重复: {aid}")
                anchor_ids.add(aid)
                if args.strict and not (anchor.get("page") or anchor.get("paragraph") or anchor.get("source_url")):
                    errors.append(f"{path}: anchor {aid} 缺 page/paragraph/source_url")

        summary = data.get("summary") or {}
        for field in SUMMARY_FIELDS:
            if field not in summary:
                errors.append(f"{path}: summary 缺字段 {field}")
            elif args.strict and not str(summary.get(field) or "").strip():
                errors.append(f"{path}: summary.{field} 为空")

        for claim in data.get("claims_supported") or []:
            cid = claim.get("claim_id")
            if not cid:
                errors.append(f"{path}: claims_supported 缺 claim_id")
            if not str(claim.get("support") or "").strip() and args.strict:
                errors.append(f"{path}: claim {cid} 缺 support")
            for aid in claim.get("anchor_ids") or []:
                if aid not in anchor_ids:
                    errors.append(f"{path}: claim {cid} 引用不存在的 anchor_id: {aid}")

    if seen_files == 0:
        warns.append(f"未发现摘要文件: {args.summaries}")

    print(f"摘要文件: {seen_files}")
    for warn in warns:
        print(f"WARN: {warn}")
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1
    print("PASS: 摘要校验通过")
    return 0


def main():
    ap = argparse.ArgumentParser(description="结构化文献摘要骨架生成与校验")
    sub = ap.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="从 references.json 生成摘要骨架")
    init.add_argument("--refs", required=True, type=Path, help="references.json")
    init.add_argument("--out-dir", required=True, type=Path, help="摘要输出目录")
    init.add_argument("--usable-only", action="store_true", help="只为 verified/provisional 生成")
    init.add_argument("--force", action="store_true", help="覆盖已有摘要文件")
    init.set_defaults(func=cmd_init)

    check = sub.add_parser("check", help="校验摘要文件")
    check.add_argument("--refs", required=True, type=Path, help="references.json")
    check.add_argument("--summaries", required=True, type=Path, help="摘要目录或单个摘要 JSON")
    check.add_argument("--strict", action="store_true", help="空摘要字段/空锚点也视为 FAIL")
    check.set_defaults(func=cmd_check)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
