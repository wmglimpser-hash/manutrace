# -*- coding: utf-8 -*-
"""受控 ref_key 改名：同步更新 references.json 与 .src.md cite token。"""
import argparse
import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

import build_manuscript


CITE_TOKEN_RE = re.compile(r"\{\{cite:([^}]*)\}\}")
NUM_TOKEN_RE = re.compile(r"\{\{num:[^}]*\}\}")
KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,63}$")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def cite_keys(text):
    keys = []
    for m in CITE_TOKEN_RE.finditer(text):
        keys.extend(k.strip() for k in m.group(1).split(",") if k.strip())
    return keys


def replace_cite_keys(text, mapping):
    def repl(m):
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        return "{{cite:" + ",".join(mapping.get(k, k) for k in keys) + "}}"

    return CITE_TOKEN_RE.sub(repl, text)


def run_build(src, refs, assets, out):
    argv = ["build_manuscript.py", str(src), "--refs", str(refs), "--out", str(out)]
    if assets:
        argv.extend(["--assets", str(assets)])
    old_argv = sys.argv[:]
    buf = io.StringIO()
    try:
        sys.argv = argv
        with contextlib.redirect_stdout(buf):
            code = build_manuscript.main()
    finally:
        sys.argv = old_argv
    return int(code or 0), buf.getvalue()


def validate(mapping, refs_data, src_text):
    errors = []
    ref_keys = [e["ref_key"] for e in refs_data["entries"]]
    ref_set = set(ref_keys)

    if len(ref_keys) != len(ref_set):
        errors.append("references.json 中存在重复 ref_key")

    target_seen = {}
    for old, new in mapping.items():
        if old not in ref_set:
            errors.append(f"mapping old key 不存在: {old}")
        if not KEY_RE.match(new):
            errors.append(f"new key 格式非法: {new}")
        if new in ref_set and new != old and new not in mapping:
            errors.append(f"new key 已被既有条目占用: {new}")
        if new in target_seen and target_seen[new] != old:
            errors.append(f"多个 old key 指向同一 new key: {target_seen[new]}, {old} -> {new}")
        target_seen[new] = old

    for key in cite_keys(src_text):
        if key not in ref_set:
            errors.append(f".src.md 中存在悬空 cite key: {key}")

    return errors


def main():
    ap = argparse.ArgumentParser(description="同步改名 .src.md 与 references.json 中的 ref_key")
    ap.add_argument("--src", required=True, type=Path, help="输入 .src.md")
    ap.add_argument("--refs", required=True, type=Path, help="输入 references.json")
    ap.add_argument("--mapping", required=True, type=Path, help="ref_key_renames.json")
    ap.add_argument("--out-src", type=Path, help="输出 .src.md")
    ap.add_argument("--out-refs", type=Path, help="输出 references.json")
    ap.add_argument("--assets", type=Path, help="assets.json；src 含 num token 时用于一致性构建")
    ap.add_argument("--in-place", action="store_true", help="原地覆盖输入文件（需用户明确授权）")
    args = ap.parse_args()

    src_text = args.src.read_text(encoding="utf-8")
    refs_data = load_json(args.refs)
    mapping_data = load_json(args.mapping)
    mapping = mapping_data.get("renames", {})

    if not mapping:
        print("FAIL: mapping 中没有 renames")
        return 1

    if NUM_TOKEN_RE.search(src_text) and not args.assets:
        print("FAIL: .src.md 含 num token；一致性构建必须提供 --assets")
        return 1

    errors = validate(mapping, refs_data, src_text)
    if errors:
        for err in errors:
            print("FAIL:", err)
        return 1

    renamed_refs = dict(refs_data)
    renamed_entries = []
    for entry in refs_data["entries"]:
        new_entry = dict(entry)
        new_entry["ref_key"] = mapping.get(entry["ref_key"], entry["ref_key"])
        renamed_entries.append(new_entry)
    renamed_refs["entries"] = renamed_entries
    renamed_src = replace_cite_keys(src_text, mapping)

    with tempfile.TemporaryDirectory(prefix="pwt4_rename_") as td:
        tmp = Path(td)
        before_out = tmp / "before.md"
        after_out = tmp / "after.md"
        after_src = tmp / "after.src.md"
        after_refs = tmp / "after.references.json"
        after_src.write_text(renamed_src, encoding="utf-8", newline="\n")
        write_json(after_refs, renamed_refs)

        code, out = run_build(args.src, args.refs, args.assets, before_out)
        if code != 0:
            print(out, end="")
            print("FAIL: 改名前基线构建失败")
            return 1
        code, out = run_build(after_src, after_refs, args.assets, after_out)
        if code != 0:
            print(out, end="")
            print("FAIL: 改名后构建失败")
            return 1
        if before_out.read_bytes() != after_out.read_bytes():
            print("FAIL: 改名后渲染产物与改名前不一致")
            return 1

    if args.in_place:
        out_src = args.src
        out_refs = args.refs
    else:
        if not args.out_src or not args.out_refs:
            print("FAIL: 非 --in-place 模式必须提供 --out-src 与 --out-refs")
            return 1
        out_src = args.out_src
        out_refs = args.out_refs

    out_src.parent.mkdir(parents=True, exist_ok=True)
    out_refs.parent.mkdir(parents=True, exist_ok=True)
    out_src.write_text(renamed_src, encoding="utf-8", newline="\n")
    write_json(out_refs, renamed_refs)

    print(f"改名条目: {len(mapping)}")
    for old, new in mapping.items():
        print(f"  {old} -> {new}")
    print(f"输出 src: {out_src}")
    print(f"输出 refs: {out_refs}")
    print("PASS: ref_key 改名后渲染产物与改名前逐字一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
