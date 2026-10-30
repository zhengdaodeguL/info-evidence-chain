# 信息证据链 · info-evidence-chain

让智能体代你检索、读网页、留证、核验和归档。遇到抓取不到内容、要手动填写检索式、筛选或翻页的网站，切换已连接的浏览器完成操作，保存页面截图并标出关键点；最后在会话展示标注图，并交付一键打开的本地证据索引。

默认采用 **AI 自动核验 + 异常转人工**：常规信息由智能体回到原始材料核对，人工集中处理不一致、模糊图、缺项和专业解释争议。

## 使用示例

安装后在支持 Skills 的 Codex 对话中输入：

> 用 $info-evidence-chain 检索中国大陆在 2026 年适用的饮料营养标签标准。需要站内检索时替我输入检索式、筛选和打开详情。保存原始页面截图，标注糖含量口径、适用条件和实施日期，自动核验字段；仅把异常列出来。在本地生成 index.html，并直接展示标注图、给我可以点击打开的路径。

也支持其他标准政策、文献资料、事实核查和图片结构化任务。Skill 是流程和本地工具集合，浏览器操作需要宿主提供可用的浏览器工具/MCP；不会凭空获得网站账号、付费权限或搜索 API。

## 哪些工作交给 AI

| 工作 | 默认执行方与结果 |
|---|---|
| 问题拆解、生成检索式 | AI 生成可追溯查询清单 |
| 直接读取网页 | AI 取原文，记录版本和定位 |
| 网站搜索框、筛选、分页、阅读器 | AI 通过已连接浏览器操作 |
| 页面取证 | 保存原图；生成空心框、编号与中文图例 |
| 字段核验、单位检查、复算 | AI 执行并保留方法和证据 ID |
| 来源管理、冲突队列、证据评分 | AI 记录并生成可解释结果 |
| 冲突、模糊图、专业适用争议 | 人工按异常清单处理；可对自动通过项抽样 |
| 交付 | 会话内标注图 + 本地离线证据索引 + 原图和 JSON |

自动通过标 `auto_verified`；人工确实看过才标 `human_verified`。同一模型重复作答不算独立证据；DOM 与截图互证检验的是提取一致性。证据分数 0–100 是解释性评分，不是统计概率或模型自报把握度。

## 安装

仓库地址：<https://github.com/zhengdaodeguL/info-evidence-chain>

Windows PowerShell 7，在目标目录尚不存在时：

```powershell
$ErrorActionPreference = 'Stop'
git clone https://github.com/zhengdaodeguL/info-evidence-chain.git (Join-Path $env:USERPROFILE '.codex/skills/info-evidence-chain')
```

macOS/Linux 可将仓库克隆到 `~/.codex/skills/info-evidence-chain`。已安装时在技能目录正常更新 Git 工作树，先检查自己的本地改动。安装后开启新对话以重新发现技能。

评分器和证据包使用 Python 3.9+ 标准库；截图标注需要 **Python 3.10+、Pillow 和支持中文的字体**（Windows 自动寻找微软雅黑，其他系统可指定 `--font`）。

```powershell
$ErrorActionPreference = 'Stop'
python -m pip install 'Pillow>=10'
```

## 本地工具

智能体调用这些工具；用户通常只需描述任务。先通过浏览器得到真实截图和对应坐标 JSON，接口见 [浏览器取证流程](references/browser-evidence-workflow.md)。

```powershell
$ErrorActionPreference = 'Stop'
python scripts/annotate_screenshot.py --image raw/E-001.jpg --annotations boxes.json --output annotated/E-001.png
python scripts/score_confidence.py claim.json
python scripts/build_evidence_pack.py --manifest manifest.json --output evidence-pack
```

证据包必须使用新的或空的输出目录。生成：

```text
evidence-pack/
├── index.html         # 双击即可打开；可搜索，点击看原图/标注图/来源
├── manifest.json      # 来源、检索日志、核验状态、评分与 SHA-256
├── raw/               # 未编辑截图，按内容哈希命名
├── annotated/         # 标注 PNG
├── annotations/       # 坐标与标注元数据（如果提供）
└── text/              # 提取原文（如果提供）
```

不需要服务器或在线图床。证据包在本地保存；原图与会话材料不随代码自动发布。截图哈希检查文件一致性，不证明内容真实性；标注不会提高置信分数。索引展示输入中已经执行的核验记录，不替你执行核验。

## 置信度与人工占比

[评分规则](references/confidence-rubric.md) 支持带证据引用的 `verification_checks`。常规观察可在自动核验通过后获得高证据等级；只设置 `auto_verified: true` 不生效。冲突、未知和缺少关键依据时进入待核队列。

实际减少多少人工时间由网站可访问性、截图清晰度、样本和问题决定。用真实任务计数/耗时衡量自动化占比，不预设百分比。

## 饮料案例的边界

[饮料标签流程](references/beverage-label-workflow.md) 区分糖和碳水化合物、发布和生效日期、无糖和 0 蔗糖。空搜索结果不等于标准不存在，未找到对应条款也不等于违法。2026 年样本所用标准必须按当时有效版本确认；WHO 的 25g 不能无条件当成所有人的个体化日限。

## 维护与许可

核心入口 [SKILL.md](SKILL.md)，设计与组件约定见 [DESIGN.md](DESIGN.md)，目录和验证方法见 [DEVELOPMENT.md](DEVELOPMENT.md)。使用 MIT License。
