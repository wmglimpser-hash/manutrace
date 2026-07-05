# -*- coding: utf-8 -*-
"""W3 证据覆盖率报告：统计 token 化初稿的 cite/num 密度与终核清单。

用法：
  $env:PYTHONUTF8="1"; python tools/pwt/coverage_report.py \
    --src src/draft.src.md --refs library/references.json --out reports/coverage.md --strict
"""
import argparse
import json
import re
from pathlib import Path


CITE_RE = re.compile(r"\{\{cite:([^}]*)\}\}")
NUM_RE = re.compile(r"\{\{num:([^}]*)\}\}")
HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.M)
AUTHOR_CONFIRM_RE = re.compile(r"\[作者确认[:：][^\]]+\]")
PENDING_DATA_RE = re.compile(r"\[待实验数据[^\]]*\]")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def split_refs(payload):
    return [item.strip() for item in payload.split(",") if item.strip()]


def section_spans(text):
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [{"heading": "(全文)", "level": 0, "text": text, "start_line": 1}]
    spans = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        start_line = text[: match.start()].count("\n") + 1
        spans.append(
            {
                "heading": match.group(2),
                "level": len(match.group(1)),
                "text": text[start:end],
                "start_line": start_line,
            }
        )
    return spans


def line_hits(pattern, text):
    hits = []
    for match in pattern.finditer(text):
        line = text[: match.start()].count("\n") + 1
        hits.append((line, match.group(0)))
    return hits


def cited_ref_keys(text):
    keys = []
    for match in CITE_RE.finditer(text):
        keys.extend(split_refs(match.group(1)))
    return keys


def refs_index(refs_data):
    return {entry["ref_key"]: entry for entry in refs_data.get("entries", [])}


def provisional_refs(cited, entries):
    seen = []
    for key in cited:
        entry = entries.get(key)
        if entry and entry.get("pool", "verified") == "provisional" and key not in seen:
            seen.append(key)
    return seen


def candidate_entries(entries):
    out = []
    for key, entry in sorted(entries.items()):
        if entry.get("pool") == "candidate":
            out.append((key, entry))
    return out


def render_report(src_path, refs_path, text, refs_data, strict):
    entries = refs_index(refs_data)
    cited = cited_ref_keys(text)
    cite_count = len(CITE_RE.findall(text))
    num_count = len(NUM_RE.findall(text))
    author_confirms = line_hits(AUTHOR_CONFIRM_RE, text)
    pending_data = line_hits(PENDING_DATA_RE, text)
    sections = section_spans(text)

    lines = [
        "# 证据覆盖率报告",
        "",
        f"- src: `{src_path}`",
        f"- refs: `{refs_path}`",
        f"- cite_tokens: {cite_count}",
        f"- num_tokens: {num_count}",
        f"- cited_ref_keys_unique: {len(set(cited))}",
        f"- author_confirm_placeholders: {len(author_confirms)}",
        f"- pending_data_placeholders: {len(pending_data)}",
        "",
        "## 分节统计",
        "",
        "| section | line | cite tokens | num tokens | author confirm | pending data |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for section in sections:
        body = section["text"]
        lines.append(
            "| {heading} | {line} | {cite} | {num} | {confirm} | {pending} |".format(
                heading=section["heading"].replace("|", "\\|"),
                line=section["start_line"],
                cite=len(CITE_RE.findall(body)),
                num=len(NUM_RE.findall(body)),
                confirm=len(AUTHOR_CONFIRM_RE.findall(body)),
                pending=len(PENDING_DATA_RE.findall(body)),
            )
        )

    lines.extend(["", "## 作者确认占位", ""])
    if author_confirms:
        for line, value in author_confirms:
            lines.append(f"- line {line}: `{value}`")
    else:
        lines.append("- none")

    lines.extend(["", "## 待实验数据占位", ""])
    if pending_data:
        for line, value in pending_data:
            lines.append(f"- line {line}: `{value}`")
    else:
        lines.append("- none")

    lines.extend(["", "## 终核清单（provisional 引用）", ""])
    provisional = provisional_refs(cited, entries)
    if provisional:
        for key in provisional:
            entry = entries[key]
            title = (entry.get("metadata") or {}).get("title") or entry.get("rendered_text", "")
            todos = "；".join((entry.get("verification") or {}).get("todos") or [])
            lines.append(f"- `{key}`: {title}" + (f"；{todos}" if todos else ""))
    else:
        lines.append("- none")

    lines.extend(["", "## 待下载清单（candidate）", ""])
    candidates = candidate_entries(entries)
    if candidates:
        for key, entry in candidates:
            title = (entry.get("metadata") or {}).get("title") or entry.get("rendered_text", "")
            access = (entry.get("verification") or {}).get("access_level", "")
            lines.append(f"- `{key}`: {title}" + (f"；access_level={access}" if access else ""))
    else:
        lines.append("- none")

    errors, warns = [], []
    if author_confirms:
        warns.append(f"作者确认占位 {len(author_confirms)} 处")
    if pending_data:
        message = f"待实验数据占位 {len(pending_data)} 处"
        if strict:
            errors.append(message)
        else:
            warns.append(message)

    lines.extend(["", "## 检查结论", ""])
    for warn in warns:
        lines.append(f"- WARN: {warn}")
    for err in errors:
        lines.append(f"- FAIL: {err}")
    if not errors:
        lines.append("- PASS: 覆盖率报告生成完成")

    return lines, warns, errors


def main():
    ap = argparse.ArgumentParser(description="生成证据覆盖率报告")
    ap.add_argument("--src", required=True, type=Path, help="token 化 src.md")
    ap.add_argument("--refs", required=True, type=Path, help="references.json")
    ap.add_argument("--out", required=True, type=Path, help="输出报告 md")
    ap.add_argument("--strict", action="store_true", help="[待实验数据] 视为 FAIL")
    args = ap.parse_args()

    text = args.src.read_text(encoding="utf-8")
    refs_data = load_json(args.refs)
    lines, warns, errors = render_report(args.src, args.refs, text, refs_data, args.strict)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"sections: {len(section_spans(text))}")
    print(f"cite_tokens: {len(CITE_RE.findall(text))}")
    print(f"num_tokens: {len(NUM_RE.findall(text))}")
    for warn in warns:
        print(f"WARN: {warn}")
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1
    print(f"saved: {args.out}")
    print("PASS: 证据覆盖率报告生成完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
