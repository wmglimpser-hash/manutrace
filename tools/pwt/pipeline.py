# -*- coding: utf-8 -*-
"""单命令构建管道：src.md -> 编号化 md -> docx -> 构建日志。

用法：$env:PYTHONUTF8="1"; python tools/pwt/pipeline.py \
        --src <src.md> --refs <references.json> --assets <assets.json> \
        --manuscript-out <编号化.md> --docx-out <.docx>

退出码：0=全链成功；非 0=任一环节失败。
"""
import argparse
import contextlib
import hashlib
import io
import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import build_manuscript


LOG_NAME = "builds.log.md"
LOG_HEADER = "# 构建日志\n\n本文件由 pipeline.py 自动追加，禁止手改。\n"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_docx_document_xml(path):
    with zipfile.ZipFile(path) as zf:
        return hashlib.sha256(zf.read("word/document.xml")).hexdigest()


def run_build_manuscript(src, refs, assets, out):
    argv = [
        "build_manuscript.py",
        str(src),
        "--refs",
        str(refs),
        "--out",
        str(out),
    ]
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


def run_docx_builder(src, out):
    return 1, "", "FAIL: 请通过 --docx-builder 显式指定 docx 构建脚本"


def run_docx_builder_with(src, out, builder):
    if not builder.is_file():
        return 1, "", f"FAIL: 找不到 docx 构建脚本：{builder}"
    cmd = [
        sys.executable,
        str(builder),
        "--in",
        str(src),
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8")
    return proc.returncode, proc.stdout, proc.stderr


def append_log(src, manuscript_out, docx_out, build_output, log_out=None):
    log_path = Path(log_out).resolve() if log_out else src.parent / LOG_NAME
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(LOG_HEADER + "\n", encoding="utf-8", newline="\n")

    timestamp = datetime.now().strftime("%Y-%m-%dT %H:%M:%S")
    entry = (
        f"## {timestamp}\n"
        f"- src: {src.name} ({sha256_file(src)[:12]})\n"
        f"- md:  {manuscript_out.name} ({sha256_file(manuscript_out)[:12]})\n"
        f"- docx: {docx_out.name} "
        f"({sha256_docx_document_xml(docx_out)[:12]})\n"
        "- 校验输出：\n"
        "  ```\n"
        + "".join(f"  {line}\n" for line in build_output.splitlines())
        + "  ```\n\n"
    )
    with open(log_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(entry)
    return log_path, entry


def write_change_note(src, manuscript_out, docx_out, note, note_out=None):
    if not note:
        return None
    path = Path(note_out) if note_out else docx_out.with_suffix(docx_out.suffix + ".changes.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# 修改说明\n\n"
        f"- src: {src}\n"
        f"- md: {manuscript_out}\n"
        f"- docx: {docx_out}\n"
        f"- 说明: {note}\n"
    )
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def main():
    ap = argparse.ArgumentParser(description="src.md -> 编号化 md -> docx -> 构建日志")
    ap.add_argument("--src", required=True, type=Path, help="token 化源文件路径")
    ap.add_argument("--refs", required=True, type=Path, help="references.json 路径")
    ap.add_argument("--assets", type=Path, help="assets.json 路径")
    ap.add_argument("--manuscript-out", required=True, type=Path, help="编号化 md 输出路径")
    ap.add_argument("--docx-out", required=True, type=Path, help=".docx 输出路径")
    ap.add_argument("--change-note", help="docx 输出对应的修改说明")
    ap.add_argument("--change-note-out", type=Path, help="修改说明输出路径；默认 <docx>.changes.md")
    ap.add_argument("--log-out", type=Path, help="构建日志输出路径；默认写入 src/builds.log.md")
    ap.add_argument("--docx-builder", required=True, type=Path, help="docx 构建脚本路径")
    ap.add_argument("--protected-docx", type=Path, help="禁止覆盖的原始 docx 路径")
    args = ap.parse_args()

    src = args.src.resolve()
    refs = args.refs.resolve()
    assets = args.assets.resolve() if args.assets else None
    manuscript_out = args.manuscript_out.resolve()
    docx_out = args.docx_out.resolve()
    docx_builder = args.docx_builder.resolve()
    protected_docx = args.protected_docx.resolve() if args.protected_docx else None
    tmp_out = manuscript_out.with_name(manuscript_out.name + ".tmp")

    if protected_docx and docx_out == protected_docx:
        print(f"FAIL: 受保护 docx 禁止覆盖：{docx_out}")
        print("FAIL: 请输出到新文件名（如 原名_修改说明_日期.docx）或 builds/，并提供 --change-note。")
        return 1

    tmp_out.unlink(missing_ok=True)
    code, build_output = run_build_manuscript(src, refs, assets, tmp_out)
    print(build_output, end="")
    if code != 0:
        tmp_out.unlink(missing_ok=True)
        print("FAIL: build_manuscript 未通过，已保留现有编号化 md 与 docx")
        return 1

    manuscript_out.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp_out, manuscript_out)

    code, stdout, stderr = run_docx_builder_with(manuscript_out, docx_out, docx_builder)
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)
    if code != 0:
        print(
            "FAIL: md 已更新，但 docx 构建失败，编号化 md 与 docx 已漂移；"
            f"请修复 docx 构建后重跑 pipeline。docx: {docx_out}"
        )
        return 1

    note_path = write_change_note(src, manuscript_out, docx_out, args.change_note, args.change_note_out)
    log_path, entry = append_log(src, manuscript_out, docx_out, build_output, args.log_out)
    if note_path:
        print(f"修改说明已写入: {note_path}")
    print(entry, end="")
    print(f"构建日志已追加: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
