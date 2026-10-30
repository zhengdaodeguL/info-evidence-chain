# 信息证据链

一套面向 AI + 信息素养研究的 Codex Skill：把搜索线索变成可追溯来源，把图片/网页信息分层记录，保留人工修订和计算公式，并以证据依据给出高/中/低置信度。

## 能做什么

- 生成“主张—证据—检索式”清单，帮助减少重复搜索；
- 管理来源 ID、发布机构、版本、生效日期、条款定位和原文摘录；
- 为 OCR 数据保留原始值、结构化值、人工修订和最终判定；
- 对派生指标保存输入、单位和公式，便于复算；
- 输出证据分数与置信等级，并提示未过的核验闸门。

置信分数是解释性证据评分，不是统计概率，也不是模型自报的把握度。Skill 不代替人工核对原文、原图或领域专业判断。

## 安装（Codex）

将 `info-evidence-chain` 文件夹复制到 Codex skills 目录：

- Windows：`%USERPROFILE%\\.codex\\skills\\info-evidence-chain`
- macOS/Linux：`~/.codex/skills/info-evidence-chain`

或者从仓库根目录执行：

```powershell
$ErrorActionPreference = 'Stop'
Copy-Item -Recurse -LiteralPath . -Destination "$env:USERPROFILE\\.codex\\skills\\info-evidence-chain"
```

安装后在 Codex 新对话里使用 `$info-evidence-chain`，也可直接说“用信息证据链整理这项研究”。

## 仓库内容

- `SKILL.md`：核心工作流与工具路由；
- `references/evidence-schema.md`：来源、主张、原始记录和冲突字段；
- `references/confidence-rubric.md`：分数和硬闸门；
- `references/beverage-label-workflow.md`：饮料标签项目专用方法与版本提醒；
- `scripts/score_confidence.py`：Python 标准库评分器；
- `DESIGN.md`、`DEVELOPMENT.md`：输出设计与维护规则。

## 评分脚本

Python 3.9+，无需第三方依赖。输入一个 JSON 文件：

```json
{
  "claim_type": "normative",
  "source_tier": "A1",
  "url": "https://example.gov/standard",
  "effective_at_claim_time": true,
  "exact_locator": true,
  "independent_crosscheck": true,
  "raw_material": true,
  "human_verified": true,
  "source_ids": ["S-001"]
}
```

```powershell
python scripts/score_confidence.py claim.json
```

`claim_type` 支持 `normative`、`observed`、`computed`、`interpretive`。完整字段和计分含义见 [置信度规则](references/confidence-rubric.md)。未生效的标准不能通过规范性主张硬闸门；未核实的图片观察也不能标为高置信。

## 饮料标签示例

饮料标签工作流强调：AI 搜索只发现线索，标准判定回到适用版本原文；OCR 逐张人工复核；“0 蔗糖”不能自动等同“无糖”；“糖”不能用“碳水化合物”代替；没有检索到条款不自动说明违法。标准状态和健康参照随时间变化，实际提交前必须重新核对主管部门原文。

## 开源许可

本项目使用 [MIT License](LICENSE)。
