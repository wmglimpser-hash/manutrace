# -*- coding: utf-8 -*-
"""W3 大纲门禁：检查 outline.md 是否覆盖 claims.json 的证据需求。

用法：
  $env:PYTHONUTF8="1"; python tools/pwt/outline_gate.py check \
    --outline outline.md --claims evidence/claims.json --require-approved
"""
import argparse
import json
import re
from pathlib import Path


HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
FIELD_RE = re.compile(r"^-\s*([A-Za-z_]+)\s*:\s*(.*)$")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def split_list(value):
    return [item.strip() for item in re.split(r"[,，]", value or "") if item.strip()]


def parse_outline(path):
    sections = []
    current = None
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = HEADING_RE.match(raw)
        if m:
            current = {"heading": m.group(2), "line": line_no, "fields": {}}
            sections.append(current)
            continue
        if current is None:
            continue
        fm = FIELD_RE.match(raw.strip())
        if fm:
            key, value = fm.group(1), fm.group(2).strip()
            current["fields"].setdefault(key, []).append(value)
    return sections


def claim_specs(claims_data):
    return {claim.get("claim_id"): claim for claim in claims_data.get("claims", []) if claim.get("claim_id")}


def cmd_check(args):
    claims = claim_specs(load_json(args.claims))
    sections = parse_outline(args.outline)
    errors, warns = [], []
    seen_claims = set()

    for section in sections:
        fields = section["fields"]
        claim_ids = []
        for value in fields.get("claim_id", []):
            claim_ids.extend(split_list(value))

        if not claim_ids:
            warns.append(f"行{section['line']} {section['heading']}: 未声明 claim_id")
            continue

        status_values = [v.strip().lower() for v in fields.get("status", [])]
        if args.require_approved and "approved" not in status_values:
            errors.append(f"行{section['line']} {section['heading']}: 大纲未 approved")

        refs = []
        nums = []
        for value in fields.get("evidence_refs", []):
            refs.extend(split_list(value))
        for value in fields.get("evidence_nums", []):
            nums.extend(split_list(value))

        for cid in claim_ids:
            if cid not in claims:
                errors.append(f"行{section['line']} {section['heading']}: claim_id 不存在: {cid}")
                continue
            seen_claims.add(cid)
            claim = claims[cid]
            if claim.get("needs_literature", True) and not refs:
                errors.append(f"行{section['line']} {section['heading']}: {cid} 缺 evidence_refs")
            if claim.get("needs_data", False):
                if not nums:
                    errors.append(f"行{section['line']} {section['heading']}: {cid} 缺 evidence_nums")
                for token in nums:
                    if not token.startswith("{{num:"):
                        errors.append(f"行{section['line']} {section['heading']}: 非法 num token: {token}")

    required_claims = {cid for cid, claim in claims.items() if claim.get("required", False)}
    missing = sorted(required_claims - seen_claims)
    for cid in missing:
        errors.append(f"必需 claim 未进入大纲: {cid}")

    print(f"sections: {len(sections)}")
    print(f"claims_in_outline: {len(seen_claims)}")
    for warn in warns:
        print(f"WARN: {warn}")
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1
    print("PASS: 大纲门禁通过")
    return 0


def main():
    ap = argparse.ArgumentParser(description="检查 outline.md 是否覆盖 claims.json 的证据需求")
    sub = ap.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="检查大纲")
    check.add_argument("--outline", required=True, type=Path, help="outline.md")
    check.add_argument("--claims", required=True, type=Path, help="claims.json")
    check.add_argument("--require-approved", action="store_true", help="要求每个有 claim 的节 status=approved")
    check.set_defaults(func=cmd_check)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
