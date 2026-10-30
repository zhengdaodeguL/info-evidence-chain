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

`record_id`、`item_id`、`captured_at`、`location_scope`、`image_path`、`raw_text_path`、`extracted_json_path`、`auto_verified_values`、`verification_checks`、`human_verified_by`、`human_verified_at`、`verification_status`、`notes`。

`verification_status` 使用 `unverified`、`auto_verified`、`human_verified`、`needs_review`、`blocked`。自动通过不填人工确认人；人工修订保留自动提取的旧值。

对于饮料标签，再加：`product_name`、`net_content_value`、`net_content_unit`、`nutrition_basis`、`carbohydrate_per_basis`、`sugar_per_basis`、`ingredients_raw`、`ingredient_order`、`front_claim_raw`、`raw_ocr`、`human_corrected`。

## conflict（冲突）

`conflict_id`、`object_id`、`field`、`version_a`、`version_b`、`evidence_a`、`evidence_b`、`resolution`、`resolved_by`、`resolved_at`、`open_action`。

## browser evidence（浏览器证据包）

`manifest.json` 顶层包含 `title`、`scope`、`search_log` 和 `evidence`。`search_log` 是真实动作数组，每项记录 `at`、`action`、`query`、`outcome`，可以增加站点、筛选条件、翻页范围与阻塞原因。

可选 `conclusions` 与 `limitations` 均为字符串数组，在索引顶部显示本次结论和限制。待处理队列由各条 `verification_status` 与 `review_reason` 汇总，避免用户逐张寻找异常。

`evidence` 每项包含：

| 字段 | 用途 |
|---|---|
| `evidence_id` | 唯一截图/页面证据 ID |
| `title`、`url`、`query`、`captured_at` | 标题、实际 URL、实际检索式和采集时间 |
| `locator` | 条款/页码/表格行/屏幕位置 |
| `excerpt` | 截图上能直接读出的逐字摘录 |
| `finding` | 智能体解释，不能与原文混写 |
| `result_status` | `results`、`empty`、`source_text`、`blocked` 等页面结果 |
| `screenshot_path` | 未编辑原图，必填；相对路径以输入 manifest 所在目录为基准 |
| `annotated_path`、`annotations_path` | 标注 PNG 和坐标元数据 |
| `text_path` | 同页面正文/DOM 提取文件（可选） |
| `verification_status` | 自动通过/人审/待核/阻塞等，不能由截图工具代设 |
| `verification_checks` | 实际执行的核验记录 |
| `review_reason` | 异常、缺口或下一步动作 |
| `confidence` | 评分器实际返回值（可选，不传则显示尚未评分） |

证据包构建器复制原始材料，保存文件 SHA-256 并将路径转为包内相对路径；哈希证明保存后文件的一致性，不证明网页或内容真实。

最小输入（路径换成实际截图）：

```json
{
  "title": "GB 28050 检索证据",
  "scope": "中国大陆；本次访问时点；仅记录页面显示",
  "search_log": [{"at": "实际时间", "action": "submit_search", "query": "GB 28050", "outcome": "实际结果"}],
  "evidence": [{
    "evidence_id": "E-001", "title": "站内检索结果",
    "url": "https://example.gov/search", "query": "GB 28050",
    "captured_at": "实际时间", "locator": "结果列表首屏",
    "excerpt": "逐字摘录", "finding": "只描述当前页面支持的发现",
    "screenshot_path": "raw/E-001.jpg", "verification_status": "unverified"
  }]
}
```

## 自动核验记录

评分输入沿用 `source_ids`、`record_ids`、`screenshot_ids`，并可增加 `evidence` 注册表（每项有 `evidence_id` 和 `path`/`url`/`locator`）。每个 `verification_checks` 记录 `check_id`、`method`、严格布尔值 `passed` 和能解析的 `evidence_refs`；只写 `auto_verified: true` 不视为核验。评分器支持的具体方法与闸门见 [confidence-rubric.md](confidence-rubric.md)。

同一网页的 DOM 与截图互证提高提取可靠性，不算两个独立来源；转载、镜像和多模型复述同样不能伪装成独立佐证。原文生效日、适用范围、缺失字段、单位与计算等检查必须分别保留依据。

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




