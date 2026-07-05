# -*- coding: utf-8 -*-
"""一次性迁移器：把编号化 manuscript md 反向转换为 token 化源文件 + 文献库 JSON。

用法：$env:PYTHONUTF8="1"; python migrate_manuscript.py <编号化.md> --outdir <dir>
输出：<dir>/<原名>.src.md + <dir>/references.json
退出码：0=成功，非 0=失败。

规格来源：paper-trace/docs/TASK_pwt1_citation_engine.md §4。
悬空/孤立在迁移期只 WARN 不阻断（迁移的职责是忠实转换现状，修复靠 build）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

REF_HEADING = "## 参考文献"
# 与 check_manuscript.py 第 37 行同一正则（同一口径，禁止重新发明）
CITE_GROUP_RE = re.compile(r"\[([0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*)\]")
REF_LINE_RE = re.compile(r"^\[(\d+)\] (.*)$", re.M)


def expand(token):
    """'3-5' -> [3,4,5]; '13' -> [13]（抄自 check_manuscript.py）"""
    if "-" in token:
        a, b = token.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(token)]


def main():
    ap = argparse.ArgumentParser(description="编号化 md → token 化 src.md + references.json")
    ap.add_argument("manuscript", help="编号化 manuscript md 路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    args = ap.parse_args()

    src_path = Path(args.manuscript)
    with open(src_path, encoding="utf-8", newline="") as f:
        text = f.read()

    body, _, refsec = text.partition(REF_HEADING)
    if not refsec:
        print(f"FAIL: 找不到 '{REF_HEADING}' 节")
        return 1

    # ---- 文献节 → entries（rendered_text 为去掉 '[n] ' 前缀后的整行 verbatim）----
    entries_by_num = {}
    for m in REF_LINE_RE.finditer(refsec):
        n = int(m.group(1))
        if n in entries_by_num:
            print(f"FAIL: 文献节编号 [{n}] 重复出现")
            return 1
        entries_by_num[n] = m.group(2)
    if not entries_by_num:
        print("FAIL: 文献节未解析到任何 '[n] ' 条目")
        return 1

    width = max(2, len(str(max(entries_by_num))))
    key_of = {n: f"r{n:0{width}d}" for n in entries_by_num}

    # ---- 正文引用组 → cite token（一个方括号组 = 一个 token）----
    report = []          # (行号, 原字面, 新token)
    cited_nums = set()
    dangling_literals = []

    def replace(m):
        literal = m.group(0)
        nums = []
        for part in m.group(1).split(","):
            nums.extend(expand(part))
        cited_nums.update(nums)
        missing = [n for n in nums if n not in key_of]
        if missing:
            dangling_literals.append((literal, missing))
        # 悬空编号也生成占位 key（保持忠实转换），build 期会拦截
        keys = [key_of.get(n, f"r{n:0{width}d}") for n in nums]
        token = "{{cite:" + ",".join(keys) + "}}"
        line_no = body[: m.start()].count("\n") + 1
        report.append((line_no, literal, token))
        return token

    tokenized_body = CITE_GROUP_RE.sub(replace, body)

    # ---- WARN（不阻断）----
    orphan = sorted(set(entries_by_num) - cited_nums)
    if orphan:
        print(f"WARN: 孤立参考文献（声明未被引用）: {orphan}")
    if dangling_literals:
        for literal, missing in dangling_literals:
            print(f"WARN: 正文引用无对应条目: {literal} 缺 {missing}")

    # ---- 写出 ----
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    src_out = outdir / (src_path.stem + ".src.md")
    refs_out = outdir / "references.json"

    with open(src_out, "w", encoding="utf-8", newline="") as f:
        f.write(tokenized_body)

    refs_data = {
        "version": 1,
        "entries": [
            {
                "ref_key": key_of[n],
                "rendered_text": entries_by_num[n],
                "status": "active",
                "verification": {"todos": [], "note": ""},
            }
            for n in sorted(entries_by_num)
        ],
    }
    with open(refs_out, "w", encoding="utf-8", newline="") as f:
        json.dump(refs_data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # ---- 迁移报告 ----
    print(f"文献条目: {len(entries_by_num)} 条 → {refs_out}")
    print(f"引用 token: {len(report)} 处 → {src_out}")
    for line_no, literal, token in report:
        print(f"  行{line_no}: {literal} → {token}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
