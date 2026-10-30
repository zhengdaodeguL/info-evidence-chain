# 开发规范：信息证据链

## 目录与复用规则

```text
info-evidence-chain/
├── SKILL.md                 # 路由与核心工作流
├── AGENTS.md                # 规则索引
├── DESIGN.md                # 设计方向、颜色和证据卡组件
├── DEVELOPMENT.md           # 目录、脚本和验证约定
├── agents/openai.yaml       # Codex UI 元数据
├── references/              # 只在相关模式下读取
│   ├── evidence-schema.md
│   ├── confidence-rubric.md
│   └── beverage-label-workflow.md
└── scripts/
    └── score_confidence.py  # 纯标准库的确定性评分器
```

入口只放跨任务规则；模式细节放在 `references/`。脚本只做确定性转换，不访问网络、不读取凭据、不替代人工核验。需要新增字段时先更新 schema 和示例，再更新脚本，避免同一字段出现多个名称。

## 数据约定

- 文本与 JSON 使用 UTF-8。
- 原始值、提取值、规范化值和人工确认值分列保存。
- URL、文号、版本、条款/页码和访问日期是来源记录的最小字段。
- `unknown` 表示尚未知道；空字符串表示输入缺失，不能混用。
- “证据分数”不是概率；硬闸门失败必须在输出中列出。

## 验证

修改后运行：

```text
python scripts/score_confidence.py --help
python C:\Users\11599\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\11599\.codex\skills\info-evidence-chain
```

再用一个包含规范性、OCR 和计算三类记录的临时 JSON 验证分数、硬闸门和输出字段。不要用测试通过替代原文核对。
