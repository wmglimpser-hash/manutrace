# evidence / summaries schema（W2）

## `library/summaries/<ref_key>.json`

```json
{
  "version": 1,
  "ref_key": "r01",
  "access_level": "A_fulltext",
  "source_file": "input/refs/example.pdf",
  "source_url": null,
  "bibliographic_note": "",
  "anchors": [
    {
      "anchor_id": "p1",
      "page": "1",
      "paragraph": "2",
      "quote": "",
      "note": ""
    }
  ],
  "summary": {
    "research_question": "",
    "method": "",
    "data_scope": "",
    "findings": "",
    "limitations": "",
    "relevance": ""
  },
  "claims_supported": [
    {
      "claim_id": "c_background_001",
      "support": "",
      "anchor_ids": ["p1"]
    }
  ],
  "extraction_warnings": []
}
```

规则：

- `access_level` 取值：
  - `A_fulltext`：全文可读，可转 `provisional`，交付时进终核清单。
  - `B_abstract`：仅题录/摘要，不得引用，进待下载清单。
  - `C_unverified`：真实性存疑，不得引用。
- `anchors[].anchor_id` 在单文件内唯一。
- `claims_supported[].anchor_ids` 必须指向本文件已有 anchor。
- `summary` 六字段可以先为空；`check --strict` 时为空会 FAIL。

## `evidence/claims.json`

```json
{
  "version": 1,
  "claims": [
    {
      "claim_id": "c_background_001",
      "section": "2.1",
      "claim": "古籍数字化推动资源从影像保存转向结构化利用。",
      "required": true,
      "needs_literature": true,
      "needs_data": false,
      "literature": [
        {
          "ref_key": "r13",
          "anchor_id": "p1",
          "note": "支持古籍整理应用路径"
        }
      ],
      "data": [
        {
          "num_token": "{{num:freeze0630#stats.total}}",
          "note": "样本规模"
        }
      ]
    }
  ]
}
```

规则：

- `required=true` 且缺必需证据时，`build_evidence_map.py` exit 1。
- `needs_literature=true` 时至少需要 1 条文献证据。
- `needs_data=true` 时至少需要 1 条数据证据。
- 文献证据的 `ref_key` 必须存在于 `references.json`，且不能是 `pool=candidate`。
- 若写 `anchor_id`，必须能在对应摘要文件中找到。
