# -*- coding: utf-8 -*-
"""参考文献结构化解析：references.json v1/v2 -> 带 metadata 的 v2 JSON。

本脚本只做保守解析，不联网、不补猜字段；rendered_text 原样保留。
"""
import argparse
import json
import re
from pathlib import Path


TYPE_MARKERS = {
    "J": "journal",
    "M": "book",
    "D": "thesis",
    "C": "proceedings",
    "EB/OL": "web",
}


def split_people(text):
    parts = [p.strip() for p in text.split("，") if p.strip()]
    names, suffixes, et_al = [], [], False
    for part in parts:
        if part == "等":
            et_al = True
            continue
        if part in {"主编", "编", "译"}:
            suffixes.append(part)
            continue
        names.append(part)
    return names, suffixes, et_al


def empty_metadata():
    return {
        "authors": [],
        "author_et_al": False,
        "responsibility_suffixes": [],
        "title": None,
        "container": None,
        "year": None,
        "volume": None,
        "issue": None,
        "pages": None,
        "doi": None,
        "place": None,
        "publisher": None,
        "translators": [],
        "editors": [],
    }


def extract_doi(text):
    m = re.search(r"(?:．)?DOI[:：]\s*([^．]+)．?$", text)
    if not m:
        return text, None
    return text[: m.start()].rstrip("．"), m.group(1).strip()


def parse_reference(rendered_text):
    warnings = []
    meta = empty_metadata()
    text, doi = extract_doi(rendered_text.strip())
    meta["doi"] = doi

    marker_match = re.search(r"\[(J|M|D|C|EB/OL)\]", text)
    if not marker_match:
        warnings.append("未识别文献类型标识")
        return "unknown", meta, warnings

    marker = marker_match.group(1)
    ref_type = TYPE_MARKERS.get(marker, "unknown")
    before = text[: marker_match.start()]
    after = text[marker_match.end() :].lstrip("．").rstrip("．")

    if "．" not in before:
        warnings.append("责任者与题名切分失败")
        author_part, title = before, None
    else:
        author_part, title = before.split("．", 1)
    authors, suffixes, et_al = split_people(author_part)
    meta["authors"] = authors
    meta["author_et_al"] = et_al
    meta["responsibility_suffixes"] = suffixes
    if "主编" in suffixes or "编" in suffixes:
        meta["editors"] = authors[:]
    meta["title"] = title

    if ref_type == "journal":
        parse_journal(after, meta, warnings)
    elif ref_type == "book":
        parse_book(after, meta, warnings)
    elif ref_type == "thesis":
        parse_place_publisher_year(after, meta, warnings, publisher_label="授予单位")
    else:
        warnings.append(f"类型 {marker} 暂未实现专用解析")

    return ref_type, meta, warnings


def parse_journal(text, meta, warnings):
    m = re.match(
        r"^(?P<container>.+?)，(?P<year>\d{4})"
        r"(?:，(?P<volume>[^（）():：，]+))?"
        r"(?:[（(](?P<issue>[^）)]+)[）)])?"
        r"(?:[:：](?P<pages>.+))?$",
        text,
    )
    if not m:
        warnings.append("期刊条目刊名/年卷期页解析失败")
        meta["container"] = text or None
        return
    meta["container"] = m.group("container")
    meta["year"] = m.group("year")
    meta["volume"] = m.group("volume")
    meta["issue"] = m.group("issue")
    meta["pages"] = m.group("pages")
    if not meta["pages"]:
        warnings.append("期刊条目缺页码")
    if not meta["issue"]:
        warnings.append("期刊条目缺期号")


def parse_book(text, meta, warnings):
    m_trans = re.match(r"^(?P<translators>[^．]+)，译．(?P<rest>.+)$", text)
    if m_trans:
        translators, _, _ = split_people(m_trans.group("translators"))
        meta["translators"] = translators
        text = m_trans.group("rest")
    parse_place_publisher_year(text, meta, warnings, publisher_label="出版社")


def parse_place_publisher_year(text, meta, warnings, publisher_label):
    m = re.match(r"^(?P<place>[^：:]+)[:：](?P<publisher>.+)，(?P<year>\d{4})$", text)
    if not m:
        warnings.append(f"{publisher_label}/年份解析失败")
        return
    meta["place"] = m.group("place")
    meta["publisher"] = m.group("publisher")
    meta["year"] = m.group("year")


def render_reference(entry):
    meta = entry["metadata"]
    marker = {
        "journal": "J",
        "book": "M",
        "thesis": "D",
        "proceedings": "C",
        "web": "EB/OL",
    }.get(entry.get("type"), None)
    if not marker or not meta.get("authors") or not meta.get("title"):
        return None

    authors = "，".join(meta["authors"])
    if meta.get("author_et_al"):
        authors += "，等"
    suffixes = meta.get("responsibility_suffixes") or []
    if suffixes:
        authors += "，" + "，".join(suffixes)

    head = f"{authors}．{meta['title']}[{marker}]．"
    if entry.get("type") == "journal":
        if not meta.get("container") or not meta.get("year"):
            return None
        tail = f"{meta['container']}，{meta['year']}"
        if meta.get("volume"):
            tail += f"，{meta['volume']}"
        if meta.get("issue"):
            tail += f"（{meta['issue']}）"
        if meta.get("pages"):
            tail += f"：{meta['pages']}"
        tail += "．"
    elif entry.get("type") == "book":
        if not meta.get("place") or not meta.get("publisher") or not meta.get("year"):
            return None
        mid = ""
        if meta.get("translators"):
            mid = "，".join(meta["translators"]) + "，译．"
        tail = f"{mid}{meta['place']}：{meta['publisher']}，{meta['year']}．"
    elif entry.get("type") == "thesis":
        if not meta.get("place") or not meta.get("publisher") or not meta.get("year"):
            return None
        tail = f"{meta['place']}：{meta['publisher']}，{meta['year']}．"
    else:
        return None

    doi = meta.get("doi")
    if doi:
        tail += f"DOI：{doi}．"
    return head + tail


def convert(data):
    out = {
        "version": 2,
        "entries": [],
    }
    for entry in data["entries"]:
        new_entry = dict(entry)
        ref_type, metadata, warnings = parse_reference(entry["rendered_text"])
        new_entry["type"] = ref_type
        new_entry["metadata"] = metadata
        preview_entry = {"type": ref_type, "metadata": metadata}
        structured = render_reference(preview_entry)
        if structured is None:
            warnings.append("结构化重渲染字段不足")
        new_entry["render_check"] = {
            "structured_text": structured,
            "matches_rendered_text": structured == entry["rendered_text"],
            "parse_warnings": warnings,
        }
        out["entries"].append(new_entry)
    return out


def audit_markdown(data):
    lines = [
        "# reference metadata audit",
        "",
        "本文件由 PWT-4 解析工具生成；用于人工审查，不参与投稿渲染。",
        "",
    ]
    for entry in data["entries"]:
        rc = entry["render_check"]
        lines.append(f"## {entry['ref_key']} ({entry.get('type', 'unknown')})")
        lines.append(f"- matches_rendered_text: {str(rc['matches_rendered_text']).lower()}")
        warnings = rc.get("parse_warnings") or []
        lines.append("- warnings: " + ("; ".join(warnings) if warnings else "无"))
        if not rc["matches_rendered_text"]:
            lines.append("- rendered_text:")
            lines.append("  ```")
            lines.append(f"  {entry['rendered_text']}")
            lines.append("  ```")
            lines.append("- structured_text:")
            lines.append("  ```")
            lines.append(f"  {rc.get('structured_text')}")
            lines.append("  ```")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="references.json v1/v2 -> v2 metadata JSON")
    ap.add_argument("refs", help="输入 references.json")
    ap.add_argument("--out", required=True, help="输出 v2 references.json")
    ap.add_argument("--audit-out", help="输出 markdown audit")
    args = ap.parse_args()

    with open(args.refs, encoding="utf-8") as f:
        data = json.load(f)
    converted = convert(data)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if args.audit_out:
        audit_path = Path(args.audit_out)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(audit_markdown(converted), encoding="utf-8", newline="\n")

    total = len(converted["entries"])
    matched = sum(1 for e in converted["entries"] if e["render_check"]["matches_rendered_text"])
    warn_count = sum(len(e["render_check"]["parse_warnings"]) for e in converted["entries"])
    print(f"文献条目: {total} 条")
    print(f"结构化重渲染逐字一致: {matched}/{total}")
    print(f"WARN: 解析警告 {warn_count} 条")
    print(f"输出: {out_path}")
    if args.audit_out:
        print(f"audit: {args.audit_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
