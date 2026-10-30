# 开发规范：信息证据链

## 目录与复用

- `SKILL.md`：跨任务决策、自动核验分流和交付要求。
- `references/browser-evidence-workflow.md`：浏览器输入、筛选、分页、截图标注与本地索引。
- `references/evidence-schema.md`：来源、截图、查询、主张与核验字段。
- `references/confidence-rubric.md`：证据评分、硬闸门与自动/人工状态。
- `references/beverage-label-workflow.md`：饮料标签领域口径。
- `scripts/score_confidence.py`：标准库确定性评分，不读取网页或凭据。
- `scripts/annotate_screenshot.py`：Pillow 标注真实截图，不访问网页。
- `scripts/build_evidence_pack.py`：标准库复制材料、计算哈希、生成离线 HTML/JSON。
- `tests/`：覆盖会影响核验和归档可靠性的行为。

浏览器动作由宿主当前工具执行，不在脚本硬编码网站选择器或登录态。依赖名称和调用方法以当前工具文档为准。不要把多个同类大模型强制串成流程。

## 数据约定

UTF-8 文本和 JSON；JSON 读取接受 UTF-8 BOM。原始值、提取值、规范化值、自动核验值与人工修订分开。缺失字段用 `unknown`，布尔核验结果必须是严格 true/false；未知结果不能当通过。

每项自动检查带方法与可解析证据 ID。截图原图不覆盖，标注在独立 PNG；坐标采用原截图像素，先校验尺寸和边界，不直接把 CSS 坐标当作图片坐标。HTML 文本转义，来源链接仅支持 HTTP(S)，本地材料复制进包后采用相对链接。构建器只接受新的或空输出目录。

生成材料保存在研究项目的 `evidence/<run-id>/` 或用户指定目录，排除公开 Git；不要收集凭据和无关浏览器页面。仅开源脚本、说明和脱敏示例。

## 验证

在仓库中通过 PowerShell 7 运行：

```powershell
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
python -m unittest discover -s tests -v
python scripts/score_confidence.py --help
python scripts/annotate_screenshot.py --help
python scripts/build_evidence_pack.py --help
```

有 skill-creator 时再运行它的 `scripts/quick_validate.py` 检查技能结构。新增或修改脚本需要实际运行，不能仅编译。真实浏览器联调至少完成一条“输入检索式 → 检查结果 → 原文截图 → 标注 → 本地索引 → 打开”的链路，检查关键点位置、中文可读性和链接。空结果或受阻只记录实际状态，不为演示编造成功。临时产物放在仓库外。
