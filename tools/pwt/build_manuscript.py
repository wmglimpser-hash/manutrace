# -*- coding: utf-8 -*-
"""构建器：token 化源文件 → 编号化渲染 md（引用编号按首现派生 + 数字溯源求值）。

用法：$env:PYTHONUTF8="1"; python build_manuscript.py <src.md> --refs <references.json> \
        [--assets <assets.json>] --out <渲染.md>
退出码：0=成功，非 0=失败（硬性错误全部列完再退出；失败不写/删除输出文件）。

规格来源：paper-trace/docs/TASK_pwt1_citation_engine.md §5、TASK_pwt2_number_tracing.md §2。
渲染器只读 entry 的 rendered_text 与 status（局部解构），verification 物理上不可达。
数字 token：{{num:<alias>#<file>.<json.path>[|<fmt>]}}，取不到值/非数字/格式非法一律 FAIL。
引用池：pool=verified/provisional 可引用；pool=candidate 被 cite 直接 FAIL；
provisional 引用构建 WARN 并输出终核清单。
"""
import argparse
import json
import re
import sys
from pathlib import Path

REF_HEADING = "## 参考文献"
TOKEN_RE = re.compile(r"\{\{cite:([^}]*)\}\}")
NUM_TOKEN_RE = re.compile(r"\{\{num:([^}]*)\}\}")
# 连续段合并规则：run 长度 >=RANGE_MIN_RUN → 'a-b'，否则逐个列出
RANGE_MIN_RUN = 3
# 裸数字启发式（WARN 不阻断）：src 中非 token 的 >=2 位整数若与冻结统计值相等则告警
BARE_NUM_MIN_DIGITS = 2
BARE_NUM_YEAR_EXEMPT = (1900, 2099)          # 年份豁免区间
BARE_NUM_SOURCE_GLOB = "*stats*.json"        # 只拿聚合统计文件的值当比对基准（records 等原始文件噪声大）
BARE_NUM_RE = re.compile(r"(?<![\d.])\d{2,}(?![\d.])")
ALLOWED_REF_POOLS = {"verified", "provisional", "candidate"}

# ---- 以下正则与 expand() 抄自 check_manuscript.py（同一口径，禁止重新发明）----
CITE_GROUP_RE = re.compile(r"\[([0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*)\]")
NOTE_PAT = r"\[[^\[\]]*(?:待核|待补|待查|未核实)[^\[\]]*\]|⚠️|TODO"


def expand(token):
    """'3-5' -> [3,4,5]; '13' -> [13]"""
    if "-" in token:
        a, b = token.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(token)]


def merge_runs(nums):
    """[2,3,4,7] -> '2-4,7'；run 长度 <RANGE_MIN_RUN 逐个列出。输入需已升序去重。"""
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i + 1 >= RANGE_MIN_RUN:
            parts.append(f"{nums[i]}-{nums[j]}")
        else:
            parts.extend(str(n) for n in nums[i : j + 1])
        i = j + 1
    return ",".join(parts)


def load_assets(assets_path):
    """assets.json → {alias: 冻结目录绝对路径}；路径相对 assets.json 所在目录。"""
    with open(assets_path, encoding="utf-8") as f:
        data = json.load(f)
    base = Path(assets_path).parent
    return {alias: (base / spec["path"]).resolve() for alias, spec in data["assets"].items()}


def resolve_num_tokens(body, assets):
    """解析全部 {{num:...}}：返回 (替换后文本, 溯源表行, 错误列表)。

    payload 语法：<alias>#<file>.<json.path>[|<fmt>]，路径支持中文键与纯数字键。"""
    trace, errors, json_cache = [], [], {}

    def resolve(payload, token):
        if "#" not in payload:
            return None, f"num token 缺少 '#'：{token}"
        alias, _, rest = payload.partition("#")
        fmt = None
        if "|" in rest:
            rest, _, fmt = rest.rpartition("|")
        segs = rest.split(".")
        if len(segs) < 2:
            return None, f"num token 路径至少为 <file>.<key>：{token}"
        if alias not in assets:
            return None, f"alias 未注册于 assets.json：'{alias}'（token: {token}）"
        json_path = assets[alias] / (segs[0] + ".json")
        if json_path not in json_cache:
            if not json_path.is_file():
                return None, f"JSON 文件不存在：{json_path}（token: {token}）"
            with open(json_path, encoding="utf-8") as f:
                json_cache[json_path] = json.load(f)
        node = json_cache[json_path]
        for seg in segs[1:]:
            if not isinstance(node, dict) or seg not in node:
                return None, f"路径取不到值：'{rest}' 断在 '{seg}'（token: {token}）"
            node = node[seg]
        if isinstance(node, bool) or not isinstance(node, (int, float)):
            return None, f"取到的值不是数字（{type(node).__name__}）：{token}"
        try:
            literal = format(node, fmt) if fmt else str(node)
        except (ValueError, TypeError) as e:
            return None, f"格式化规则非法 '{fmt}'：{token}（{e}）"
        trace.append((token, str(json_path), node, literal))
        return literal, None

    def replace(m):
        literal, err = resolve(m.group(1), m.group(0))
        if err:
            errors.append(err)
            return m.group(0)
        return literal

    return NUM_TOKEN_RE.sub(replace, body), trace, errors


def bare_number_warnings(body, assets):
    """启发式：src 中非 token 的 >=2 位整数，与冻结聚合统计值相等 → WARN 行列表。"""
    frozen = set()

    def collect(node):
        if isinstance(node, dict):
            for v in node.values():
                collect(v)
        elif isinstance(node, list):
            for v in node:
                collect(v)
        elif not isinstance(node, bool) and isinstance(node, (int, float)):
            frozen.add(node)

    for adir in assets.values():
        for jf in sorted(adir.glob(BARE_NUM_SOURCE_GLOB)):
            with open(jf, encoding="utf-8") as f:
                collect(json.load(f))

    masked = NUM_TOKEN_RE.sub(lambda m: " " * len(m.group(0)), body)
    masked = TOKEN_RE.sub(lambda m: " " * len(m.group(0)), masked)
    warns = []
    for m in BARE_NUM_RE.finditer(masked):
        n = int(m.group(0))
        if BARE_NUM_YEAR_EXEMPT[0] <= n <= BARE_NUM_YEAR_EXEMPT[1]:
            continue
        if n in frozen:
            line_no = masked[: m.start()].count("\n") + 1
            warns.append(f"WARN: 疑似裸数字 {m.group(0)}（行{line_no}，与冻结统计值相等且未走 num token）")
    return warns


def check_rendered(text):
    """二道校验：check_manuscript.py 四项逻辑原样搬运，作用于渲染产物文本。

    返回 (exit_code, 输出行列表)。"""
    out = []
    body, _, refsec = text.partition(REF_HEADING)
    if not refsec:
        return 1, [f"FAIL: 找不到 '{REF_HEADING}' 节"]

    declared = [int(m) for m in re.findall(r"^\[(\d+)\]", refsec, re.M)]
    cited_seq = []
    for m in CITE_GROUP_RE.finditer(body):
        for part in m.group(1).split(","):
            cited_seq.extend(expand(part))

    errors, warns = [], []

    orphan = sorted(set(declared) - set(cited_seq))
    dangling = sorted(set(cited_seq) - set(declared))
    if orphan:
        errors.append(f"孤立参考文献（声明未被引用）: {orphan}")
    if dangling:
        errors.append(f"正文引用无对应条目: {dangling}")
    if sorted(declared) != list(range(1, len(declared) + 1)):
        errors.append(f"文末编号非连续 1..{len(declared)}: {declared}")

    first_order, seen = [], set()
    for n in cited_seq:
        if n not in seen:
            seen.add(n)
            first_order.append(n)
    if first_order != sorted(first_order):
        errors.append(f"顺序编码乱序，首现顺序为: {first_order}")

    bad_ref = re.findall(NOTE_PAT, refsec)
    if bad_ref:
        errors.append(f"参考文献区残留编辑批注 {len(bad_ref)} 处: {bad_ref}")
    bad_body = re.findall(NOTE_PAT, body)
    if bad_body:
        errors.append(f"正文残留编辑批注 {len(bad_body)} 处: {bad_body}")
    fill_body = len(re.findall(r"待填", body))
    if fill_body:
        warns.append(f"正文含 [待填] 占位 {fill_body} 处（作者信息类，投稿前由作者填写）")

    cjk = len(re.findall(r"[一-鿿]", text))
    out.append(f"参考文献: {len(declared)} 条；正文引用编号去重: {len(seen)} 个")
    out.append(f"CJK 字数: {cjk}" + ("（<6000，不达标）" if cjk < 6000 else ""))
    if cjk < 6000:
        errors.append(f"CJK 字数 {cjk} < 6000")

    out.extend("WARN: " + w for w in warns)
    if errors:
        out.extend("FAIL: " + e for e in errors)
        return 1, out
    out.append("PASS: 引用闭环 / 顺序编码 / 无警告残留 / 字数 全部通过")
    return 0, out


def main():
    ap = argparse.ArgumentParser(description="token 化 src.md → 编号化渲染 md")
    ap.add_argument("src", help="token 化源文件路径")
    ap.add_argument("--refs", required=True, help="references.json 路径")
    ap.add_argument("--assets", help="assets.json 路径（正文含 num token 时必填）")
    ap.add_argument("--out", required=True, help="渲染输出 md 路径")
    args = ap.parse_args()

    with open(args.src, encoding="utf-8", newline="") as f:
        body = f.read()
    with open(args.refs, encoding="utf-8") as f:
        refs_data = json.load(f)

    # ---- 数字溯源：num token 求值（任何失败都不写输出）----
    num_trace, num_errors, bare_warns = [], [], []
    if NUM_TOKEN_RE.search(body):
        if not args.assets:
            print("FAIL: 正文含 {{num:...}} token 但未提供 --assets")
            return 1
        assets = load_assets(args.assets)
        bare_warns = bare_number_warnings(body, assets)
        body, num_trace, num_errors = resolve_num_tokens(body, assets)
    elif args.assets:
        assets = load_assets(args.assets)
        bare_warns = bare_number_warnings(body, assets)

    # 渲染器只允许访问 rendered_text 与 status —— 局部解构，verification 不进入后续流程
    rendered_text_of, status_of, pool_of = {}, {}, {}
    for entry in refs_data["entries"]:
        ref_key = entry["ref_key"]
        rendered_text = entry["rendered_text"]
        status = entry["status"]
        pool = entry.get("pool", "verified")
        if ref_key in rendered_text_of:
            print(f"FAIL: references.json 中 ref_key 重复: {ref_key}")
            return 1
        if pool not in ALLOWED_REF_POOLS:
            print(f"FAIL: references.json 中 ref_key={ref_key} 的 pool 非法: {pool}")
            return 1
        rendered_text_of[ref_key] = rendered_text
        status_of[ref_key] = status
        pool_of[ref_key] = pool
    del refs_data, entry

    # ---- 第一遍扫描：收集首现序列 + 硬性错误（全部列完再退出）----
    errors = []
    num_of, first_seq = {}, []
    for m in TOKEN_RE.finditer(body):
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        seen_in_token = set()
        for k in keys:
            if k in seen_in_token:
                errors.append(f"同一 token 内重复 key: {k}（token: {m.group(0)}）")
            seen_in_token.add(k)
            if k not in rendered_text_of:
                errors.append(f"悬空引用：token 引用不存在的 ref_key: {k}")
                continue
            if pool_of[k] == "candidate":
                errors.append(f"候选池文献不得引用：ref_key={k} pool=candidate")
                continue
            if k not in num_of:
                num_of[k] = len(num_of) + 1
                first_seq.append(k)

    orphan_keys = [
        k for k in rendered_text_of
        if status_of[k] == "active" and pool_of[k] in {"verified", "provisional"} and k not in num_of
    ]
    for k in orphan_keys:
        errors.append(f"孤立文献：status=active 的条目未被任何 token 引用: {k}")

    if num_errors or errors:
        for e in num_errors + errors:
            print("FAIL:", e)
        return 1

    # ---- token 替换 ----
    def replace(m):
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        nums = sorted(num_of[k] for k in keys)
        return f"[{merge_runs(nums)}]"

    rendered_body = TOKEN_RE.sub(replace, body)

    # ---- 文献节整体重生成（按首现编号顺序）----
    ref_lines = [f"[{num_of[k]}] {rendered_text_of[k]}" for k in first_seq]
    rendered = rendered_body + REF_HEADING + "\n\n" + "\n\n".join(ref_lines) + "\n"

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(rendered)

    # ---- stdout：编号映射表 + 数字溯源表 ----
    print(f"文献条目: {len(first_seq)} 条（active 且被引用）")
    print("编号映射表:")
    for k in first_seq:
        print(f"  {k} → [{num_of[k]}]")
    if num_trace:
        print(f"数字溯源表: {len(num_trace)} 个 num token")
        for token, path, value, literal in num_trace:
            print(f"  {token} → {path} → {value} → 渲染为 '{literal}'")
    for w in bare_warns:
        print(w)
    provisional_keys = [k for k in first_seq if pool_of[k] == "provisional"]
    if provisional_keys:
        print(f"WARN: provisional 引用需作者终核 {len(provisional_keys)} 条")
        print("终核清单:")
        for k in provisional_keys:
            print(f"  {k}: {rendered_text_of[k]}")

    # ---- 二道校验（FAIL → 删除输出，不留半成品）----
    print("--- 二道校验（check_manuscript.py 逻辑） ---")
    code, lines = check_rendered(rendered)
    for line in lines:
        print(line)
    if code != 0:
        out_path.unlink(missing_ok=True)
        print(f"FAIL: 二道校验未通过，已删除输出文件 {out_path}")
        return 1
    print(f"构建成功: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
