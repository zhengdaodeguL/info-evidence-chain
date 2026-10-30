# 证据台账 schema

下面的字段用于 CSV、XLSX、JSON 或数据库。允许增加项目字段，但不要删除审计字段。

## claim（主张）

| 字段 | 必填 | 说明 |
|---|---:|---|
| `claim_id` | 是 | 稳定 ID，例如 `C-001` |
| `claim_text` | 是 | 可被证伪的一句话，不写成口号 |
| `scope` | 是 | 地区、时间、对象和适用条件 |
| `claim_type` | 是 | `normative`（标准/政策）、`observed`（观察）、`computed`（计算）、`interpretive`（解释） |
| `status` | 是 | `supported`、`partial`、`conflict`、`unverified` |
| `source_ids` | 是 | 支撑它的来源 ID，多个用数组或分号 |
| `record_ids` | 否 | 支撑它的原始记录 ID |
| `formula` | 否 | 计算主张的公式 |
| `confidence_score` | 是 | 0–100 的证据分数，不是概率 |
| `confidence_level` | 是 | `high`、`medium`、`low` |
| `gaps` | 否 | 缺少的材料或核验动作 |
| `conflicts` | 否 | 冲突记录 ID |
| `checked_at` | 是 | 最近核验时间 |

## source（来源）

`source_id`、`title`、`publisher`、`document_no_or_version`、`published_at`、`effective_from`、`effective_to`、`accessed_at`、`url`、`locator`（页/章/条款/段落）、`verbatim_excerpt`、`source_tier`、`local_copy_path`、`archived_at`。对规范性主张另存 `is_effective_at_claim_time`，不要用“已发布”代替“已生效”。

`source_tier` 建议：

- `A1`：与主张直接相关的主管机构原始文本，如现行标准、法规、监管原文或正式指南；
- `A2`：独立专业机构数据库、同行评审原文或高质量专业资料；
- `P1`：研究者直接采集的原始材料，如商品包装照片、现场观察记录或原始数据；它适合观察性主张，不替代规范性主张的 A1 来源。
- `B`：高质量机构解读、大学/医院等二手资料；
- `C`：新闻、营销、论坛、AI 摘要或未核验网页。

## record（原始材料/标签）

`record_id`、`item_id`、`captured_at`、`location_scope`、`image_path`、`raw_text_path`、`extracted_json_path`、`human_verified_by`、`human_verified_at`、`verification_status`、`notes`。

对于饮料标签，再加：`product_name`、`net_content_value`、`net_content_unit`、`nutrition_basis`、`carbohydrate_per_basis`、`sugar_per_basis`、`ingredients_raw`、`ingredient_order`、`front_claim_raw`、`raw_ocr`、`human_corrected`。

## conflict（冲突）

`conflict_id`、`object_id`、`field`、`version_a`、`version_b`、`evidence_a`、`evidence_b`、`resolution`、`resolved_by`、`resolved_at`、`open_action`。

## 最小 JSON 示例

```json
{
  "claim_id": "C-001",
  "claim_text": "某标签宣称与所引用标准条款的适用条件一致",
  "scope": "中国大陆；访问日；该包装批次",
  "claim_type": "normative",
  "status": "supported",
  "source_ids": ["S-GB-001"],
  "record_ids": ["R-P01"],
  "formula": null,
  "confidence_score": 86,
  "confidence_level": "high",
  "gaps": [],
  "conflicts": [],
  "checked_at": "2026-10-30"
}
```




