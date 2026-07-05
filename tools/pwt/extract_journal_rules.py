# -*- coding: utf-8 -*-
"""从投稿说明原文中提炼 journal.json 规则包初稿与对照 audit。

本脚本只做确定性提取；未识别的规则保留到 audit，需作者/执行 agent 复核。
"""
import argparse
import json
import re
from pathlib import Path


def first_int(patterns, text):
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return int(m.group(1)), m.group(0)
    return None, None


def find_evidence(pattern, text):
    m = re.search(pattern, text)
    return m.group(0) if m else None


def extract_rules(text, source, journal_id, journal_name):
    body_min, body_min_ev = first_int(
        [r"(?:全文|正文)[^\n。；;]{0,20}(?:不少于|≥|不低于)\s*(\d{4,5})\s*字"],
        text,
    )
    body_max, body_max_ev = first_int(
        [r"(?:全文|正文)[^\n。；;]{0,20}(?:不超过|≤|以内)\s*(\d{4,5})\s*字"],
        text,
    )
    abstract_max, abstract_ev = first_int(
        [r"摘要[^\n。；;]{0,30}(?:不超过|≤|以内)\s*(\d{2,4})\s*字"],
        text,
    )
    reference_min, reference_ev = first_int(
        [r"参考文献[^\n。；;]{0,30}(?:不少于|≥|不低于)\s*(\d{1,3})\s*条"],
        text,
    )
    reference_recommended, reference_rec_ev = first_int(
        [r"参考文献[^\n。；;]{0,30}(?:超过|>|多于)\s*(\d{1,3})\s*条"],
        text,
    )

    citation_style_ev = find_evidence(r"GB/T\s*7714[—\-–]?\d{0,4}|顺序编码制", text)
    abstract_struct_ev = find_evidence(r"结构式摘要|目的[、/／]方法[、/／]结果[、/／]结论", text)
    figure_ev = find_evidence(r"三线表|图题|表题|分辨率|矢量", text)

    rules = []
    for key, value, evidence in [
        ("body_min_cjk", body_min, body_min_ev),
        ("body_max_cjk", body_max, body_max_ev),
        ("abstract_max_cjk", abstract_max, abstract_ev),
        ("reference_min", reference_min, reference_ev),
        ("reference_recommended", reference_recommended, reference_rec_ev),
        ("citation_style", citation_style_ev, citation_style_ev),
        ("abstract_structure", abstract_struct_ev, abstract_struct_ev),
        ("figure_rules", figure_ev, figure_ev),
    ]:
        if value is not None:
            rules.append({"field": key, "value": value, "evidence": evidence})

    return {
        "version": 1,
        "journal_id": journal_id,
        "name": journal_name,
        "source_files": [str(source)],
        "body_min_cjk": body_min,
        "body_max_cjk": body_max,
        "abstract_max_cjk": abstract_max,
        "citation_style": citation_style_ev,
        "reference_min": reference_min,
        "reference_recommended": reference_recommended,
        "section_hint": ["引言", "资料与方法", "结果", "讨论"],
        "figure_rules": [figure_ev] if figure_ev else [],
        "tone_notes": "",
        "rules": rules,
    }


def audit_markdown(rules):
    lines = [
        "# journal rules audit",
        "",
        "本文件由 extract_journal_rules.py 生成；每条规则需对照投稿说明原文复核。",
        "",
        f"- journal_id: {rules['journal_id']}",
        f"- name: {rules['name']}",
        "",
        "## 提取结果",
        "",
    ]
    if not rules["rules"]:
        lines.append("WARN: 未提取到结构化规则，请人工补录。")
    for item in rules["rules"]:
        lines.append(f"- `{item['field']}` = `{item['value']}`")
        lines.append(f"  - evidence: {item['evidence']}")
    lines.append("")
    lines.append("## 未覆盖提醒")
    lines.append("")
    lines.append("- 未识别到的投稿要求必须人工补入 `rules/journal.json`。")
    lines.append("- 规则包错误会导致后续写作门禁错误；作者过目后再进入撰写。")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="投稿说明原文 -> journal.json + audit")
    ap.add_argument("source", type=Path, help="投稿说明原文 txt/md")
    ap.add_argument("--out", required=True, type=Path, help="journal.json 输出路径")
    ap.add_argument("--audit-out", required=True, type=Path, help="audit markdown 输出路径")
    ap.add_argument("--journal-id", default="unknown")
    ap.add_argument("--journal-name", default="待定期刊")
    args = ap.parse_args()

    text = args.source.read_text(encoding="utf-8")
    rules = extract_rules(text, args.source, args.journal_id, args.journal_name)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
        f.write("\n")
    args.audit_out.write_text(audit_markdown(rules), encoding="utf-8", newline="\n")

    print(f"规则条目: {len(rules['rules'])}")
    print(f"journal.json: {args.out}")
    print(f"audit: {args.audit_out}")
    if not rules["rules"]:
        print("WARN: 未提取到结构化规则")
    print("PASS: 规则包提炼完成（需作者过目）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
