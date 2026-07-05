# references.json 字段说明（PWT-1 / PWT-4）

## v1（当前构建器默认渲染格式）

```json
{
  "version": 1,
  "entries": [
    {
      "ref_key": "r03",
      "rendered_text": "徐弘民, 等. 基于……[J]. 南京中医药大学学报, 2024, 40(5): 1-9.",
      "status": "active",
      "pool": "verified",
      "verification": { "todos": [], "note": "" }
    }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `version` | 库格式版本，当前为 1 |
| `ref_key` | 稳定标识，迁移时按原编号生成 `r01`…`rNN`（零填充，宽度≥2）。key 无语义但全生命周期不变；改名走全库替换工具函数，不手工 sed |
| `rendered_text` | 条目原文 verbatim，**统一为去掉行首 `[n] ` 编号前缀后的整行**（全库统一口径）。编号前缀由 build 按首现顺序重写 |
| `status` | `active`（参与构建，若正文未引用则构建失败=孤立）\| `draft`（暂存：不参与构建、不算孤立、不出现在渲染产物） |
| `pool` | W1 新增，可选；缺省按 `verified` 兼容旧库。`verified` 可正常引用；`provisional` 可引用但构建 WARN 并输出终核清单；`candidate` 不得被 cite token 引用 |
| `verification` | **私有元数据**：核实待办与备注。build 通过局部解构只读取 `ref_key`/`rendered_text`/`status`，本字段物理上写不进渲染产物 |

关联规格：`docs/TASK_pwt1_citation_engine.md` §2；设计文档 `docs/paper_writing_tool_design.md` §5.1。

## v2（PWT-4 结构化扩展）

PWT-4 在 v1 字段外新增 `type` / `metadata` / `render_check`。迁移期必须保留
`rendered_text`，且 `build_manuscript.py` 默认仍只读 `ref_key` / `rendered_text` /
`status`。

```json
{
  "version": 2,
  "entries": [
    {
      "ref_key": "r03",
      "rendered_text": "徐弘民，等．题名[J]．刊名，2024，40（5）：1-9．",
      "status": "active",
      "pool": "verified",
      "type": "journal",
      "metadata": {
        "authors": ["徐弘民"],
        "author_et_al": true,
        "responsibility_suffixes": [],
        "title": "题名",
        "container": "刊名",
        "year": "2024",
        "volume": "40",
        "issue": "5",
        "pages": "1-9",
        "doi": null,
        "place": null,
        "publisher": null,
        "translators": [],
        "editors": []
      },
      "render_check": {
        "structured_text": "徐弘民，等．题名[J]．刊名，2024，40（5）：1-9．",
        "matches_rendered_text": true,
        "parse_warnings": []
      },
      "verification": { "todos": [], "note": "" }
    }
  ]
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `type` | `journal` / `book` / `thesis` / `proceedings` / `web` / `unknown` |
| `pool` | 引用池：`verified` / `provisional` / `candidate`；candidate 入库但不能被正文引用 |
| `metadata` | 从 `rendered_text` 保守解析出的结构化字段；缺失值写 `null` 或空数组，不得猜测 |
| `render_check.structured_text` | metadata 重渲染预览文本，只用于 audit |
| `render_check.matches_rendered_text` | `structured_text` 与 `rendered_text` 逐字一致才为 `true` |
| `render_check.parse_warnings` | 缺页码、缺卷号、责任者角色不确定、解析失败等 |

关联规格：`docs/TASK_pwt4_reference_metadata.md`。
