# 可解释置信度与异常复核

证据分数是 0–100 的解释性评分，不是统计概率。默认让智能体完成取证、原图回看、提取比对、逐字引文核对、版本与范围检查、公式复算；只有缺口、冲突或解释争议进入人工队列。不得为了减少人工而把未执行的检查标为通过。

## 自动核验必须留下记录

输入仍接受旧字段 `human_verified`、`raw_material`、`source_ids` 等。新流程增加：

```json
{
  "claim_type": "observed",
  "source_tier": "P1",
  "raw_material": true,
  "exact_locator": true,
  "record_ids": ["R-001"],
  "evidence": [
    {"evidence_id": "E-PAGE", "path": "raw/page.png", "locator": "营养表第2行"},
    {"evidence_id": "E-TEXT", "path": "extracted/record.json", "locator": "sugar_per_100ml"}
  ],
  "verification_checks": [
    {"check_id": "V-001", "method": "grounded", "passed": true, "evidence_refs": ["E-PAGE"]},
    {"check_id": "V-002", "method": "quote_match", "passed": true, "evidence_refs": ["E-PAGE", "E-TEXT"]}
  ]
}
```

每个 check 必须有唯一 ID、已执行的方法、布尔结果和可解析的证据 ID。`evidence_refs` 引用 `source_ids`、`record_ids`、`screenshot_ids` 或 `evidence` 中带路径/URL 的 `evidence_id`。这些 ID 必须在台账中指向真实保存的材料；脚本只检查引用完整性，不能替代读取页面和图片的执行器。不得伪造 ID、截图或核验日志。

支持的方法：

| method | 执行要求 |
|---|---|
| `grounded` | 打开原始材料，确认提取字段或引用确实出现在对应定位；保留原图/原文路径 |
| `quote_match` | 将目标引文/数值与原文定位逐字或按明确数值规则比对，单位与限定词同时匹配 |
| `extraction_agreement` | 两次独立提取结果一致，至少引用两份独立提取产物；不能把复制结果当成独立提取 |
| `independent_source` | 实际核对独立来源，记录双方 ID；转载或同一原文的不同网页不算独立 |
| `formula_recalculation` | 使用已保存输入与单位重新运行公式，对照结果 |
| `scope_match` | 核对地区、对象、产品分类与适用条件 |
| `version_match` | 核对发布、生效、废止时间与主张时间点 |
| `unit_check` | 核对单位、基准与换算结果 |

同一模型重复说“已核验”、仅设置 `auto_verified: true`、搜索摘要、无证据引用的自评分均不构成自动核验。单一 `grounded` 检查也不等于完成提取核验：常规事实至少需要 `grounded` 加 `quote_match` 或 `extraction_agreement`。核验检查结果未知、证据 ID 不存在或检查失败时不得标为高置信。

## 四项评分

1. **来源权威性**：A1/P1=25，A2=20，B=12，C=5，无来源=0。P1 只能支撑直接观察，不能替代规范性 A1 原文。
2. **原文定位与版本**：精确定位=25；规范性主张还须确认主张时间点已生效；只有 URL=15；只有摘要=5；无=0。
3. **独立交叉或原始材料**：完成独立来源核查=25；一条原始来源/原图=15；只有模型提取=5；无=0。两次 OCR 一致不会自动变成两条独立来源。
4. **可追溯核验与可复算性**：完成本类型的自动核验，或人工核验且有可复算公式=25；人工核验、可复算公式或已执行的原文 grounding 其中一项=15；只有模型提取=5；无=0。

独立来源方法日志可以支持 `independent_crosscheck`，实际填值前必须完成核查。保留旧布尔字段是为了兼容已有台账，不表示允许未经执行就赋值。

等级为 `high`（80–100、闸门通过、无待复核异常）、`medium`（55–79，或更高但存在缺口）、`low`（0–54，或有冲突/失败检查）。高分但存在 `unknown_fields`、无效核验记录或强指控时仍不会得到高等级。

## 类型闸门与人审边界

- `normative`：A1 原文、主张时已生效、精确条款定位、`scope_applicable: true`。常规条款提取可自动核验；“没有搜到条款”不支持“违法”，`negative_search_only: true` 不能通过规范性闸门。
- `observed`：原始材料，加人工核验，或“精确定位 + grounded + quote_match/extraction_agreement”。原始截图、提取产物和核验记录齐全时可以直接标为 `auto_verified`，无需逐条人工确认。
- `computed`：`complete_inputs: true` 与 `reproducible_formula: true`；自动核验还要求 `grounded` 与 `formula_recalculation`。输入来源不明或糖数据未知时，不得用碳水化合物代算糖。
- `interpretive`：明确来源与前提；语义解释需要人工确认。`interpretation_disputed: true` 或 `strong_allegation: true`（违法、欺诈等）进入 `needs_review`；普通条款摘录与违法判断必须分开。

`unresolved_conflict: true`、`status: conflict` 或 `passed: false` 的检查会将等级封顶为 low。`human_verified: true` 不能覆盖未解决冲突。`unknown_fields` 非空、`status: unknown`、未知检查结果会进入待复核且不能高置信。不要把字符串 `"unknown"`、`"false"` 写入布尔字段，脚本只认可 JSON `true`。

## 输出

保留原输出字段 `score`、`level`、`gate_passed`、`reasons`、`gaps`、`next_check`；新增：

- `review_status`：`auto_verified`、`human_verified` 或 `needs_review`；
- `review_reasons`：具体异常、缺口或解释争议，供智能体分派复核；
- `accepted_check_ids`：通过结构与证据引用检查的核验 ID。

`auto_verified` 表示材料和检查链完整，不代表保证事实永真。无需人工逐项重做已完成检查；用户收到的是异常清单、原始证据链接和可以直接打开的标注截图。
