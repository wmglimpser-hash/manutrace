# -*- coding: utf-8 -*-
"""由 claims.json 与结构化摘要生成证据地图（W2）。

用法：
  $env:PYTHONUTF8="1"; python tools/pwt/build_evidence_map.py \
    --refs library/references.json --claims evidence/claims.json \
    --summaries library/summaries --out evidence/evidence_map.md
"""
import argparse
import json
from pathlib import Path


USABLE_POOLS = {"verified", "provisional"}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_summaries(path):
    summaries = {}
    if path.is_file():
        files = [path]
    else:
        files = sorted(path.glob("*.json"))
    for file in files:
        data = load_json(file)
        ref_key = data.get("ref_key")
        if ref_key:
            summaries[ref_key] = data
    return summaries


def anchor_index(summary):
    return {a.get("anchor_id"): a for a in summary.get("anchors") or [] if a.get("anchor_id")}


def claim_summary_support(summaries):
    by_claim = {}
    for ref_key, summary in summaries.items():
        for claim in summary.get("claims_supported") or []:
            cid = claim.get("claim_id")
            if not cid:
                continue
            by_claim.setdefault(cid, []).append(
                {
                    "ref_key": ref_key,
                    "anchor_ids": claim.get("anchor_ids") or [],
                    "support": claim.get("support") or "",
                }
            )
    return by_claim


def validate_and_render(refs, claims, summaries):
    entries = {e["ref_key"]: e for e in refs.get("entries", [])}
    summary_claims = claim_summary_support(summaries)
    errors, warns, lines = [], [], ["# 证据地图", ""]
    counts = {"covered": 0, "gap": 0}

    for claim in claims.get("claims", []):
        cid = claim.get("claim_id")
        section = claim.get("section") or ""
        text = claim.get("claim") or ""
        required = bool(claim.get("required", False))
        needs_lit = bool(claim.get("needs_literature", True))
        needs_data = bool(claim.get("needs_data", False))
        literature = list(claim.get("literature") or [])
        data_evidence = list(claim.get("data") or [])

        for item in summary_claims.get(cid, []):
            literature.append(
                {
                    "ref_key": item["ref_key"],
                    "anchor_id": ",".join(item["anchor_ids"]),
                    "note": item["support"],
                    "_from_summary": True,
                }
            )

        lit_ok = not needs_lit or bool(literature)
        data_ok = not needs_data or bool(data_evidence)
        status = "covered" if lit_ok and data_ok else "gap"
        counts[status] += 1

        lines.append(f"## {cid} · {status}")
        if section:
            lines.append(f"- section: {section}")
        lines.append(f"- claim: {text}")
        lines.append(f"- required: {str(required).lower()}")

        if literature:
            lines.append("- literature:")
            for item in literature:
                ref_key = item.get("ref_key")
                anchor_id = item.get("anchor_id")
                note = item.get("note") or ""
                suffix = " (summary)" if item.get("_from_summary") else ""
                lines.append(f"  - `{ref_key}`{suffix} anchor=`{anchor_id or ''}` {note}".rstrip())
                if ref_key not in entries:
                    errors.append(f"{cid}: ref_key 不在 references.json: {ref_key}")
                    continue
                pool = entries[ref_key].get("pool", "verified")
                status_ref = entries[ref_key].get("status")
                if status_ref != "active":
                    errors.append(f"{cid}: ref_key 非 active: {ref_key}")
                if pool not in USABLE_POOLS:
                    errors.append(f"{cid}: ref_key 不在可引用池: {ref_key} pool={pool}")
                if anchor_id:
                    summary = summaries.get(ref_key)
                    if not summary:
                        errors.append(f"{cid}: 缺摘要文件，无法校验 anchor: {ref_key}")
                    else:
                        anchors = anchor_index(summary)
                        for aid in [p.strip() for p in str(anchor_id).split(",") if p.strip()]:
                            if aid not in anchors:
                                errors.append(f"{cid}: {ref_key} 缺 anchor_id: {aid}")
        else:
            lines.append("- literature: []")

        if data_evidence:
            lines.append("- data:")
            for item in data_evidence:
                token = item.get("num_token")
                note = item.get("note") or ""
                lines.append(f"  - `{token}` {note}".rstrip())
                if not token or not str(token).startswith("{{num:"):
                    errors.append(f"{cid}: data evidence 缺合法 num_token: {token}")
        else:
            lines.append("- data: []")

        if status == "gap":
            message = f"{cid}: 证据缺口"
            if needs_lit and not literature:
                message += "；缺文献"
            if needs_data and not data_evidence:
                message += "；缺数据"
            if required:
                errors.append(message)
            else:
                warns.append(message)
        lines.append("")

    lines.insert(2, f"- covered: {counts['covered']}")
    lines.insert(3, f"- gap: {counts['gap']}")
    lines.insert(4, "")
    return lines, warns, errors


def main():
    ap = argparse.ArgumentParser(description="生成证据地图")
    ap.add_argument("--refs", required=True, type=Path, help="references.json")
    ap.add_argument("--claims", required=True, type=Path, help="claims.json")
    ap.add_argument("--summaries", required=True, type=Path, help="摘要目录或单个摘要文件")
    ap.add_argument("--out", required=True, type=Path, help="输出 evidence map md")
    args = ap.parse_args()

    refs = load_json(args.refs)
    claims = load_json(args.claims)
    summaries = load_summaries(args.summaries)
    lines, warns, errors = validate_and_render(refs, claims, summaries)

    if errors:
        for warn in warns:
            print(f"WARN: {warn}")
        for err in errors:
            print(f"FAIL: {err}")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"claims: {len(claims.get('claims', []))}")
    print(f"summaries: {len(summaries)}")
    for warn in warns:
        print(f"WARN: {warn}")
    print(f"saved: {args.out}")
    print("PASS: 证据地图生成完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
