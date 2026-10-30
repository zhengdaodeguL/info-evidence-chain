# 浏览器代检索与页面证据工作流

当目标网站没有可直接调用的 API、需要在网页表单中输入检索式，或搜索结果必须保留页面上下文时，使用本工作流。它把“智能体代用户检索”变成可审计的浏览器证据，而不是把搜索摘要当作结论。

## 触发条件

- 站点需要 JavaScript 渲染、分页、点击搜索或表单提交；
- 页面没有稳定的下载接口，但浏览器中可以正常查看；
- 需要向评委展示检索过程、原页面和关键字段；
- 需要把证据发送到当前会话，或留在本地供团队复核。

## 路由顺序

1. 先用一个主发现入口（`smart-search`、`firecrawl-search` 或 `agent-reach`）生成候选 URL 和检索式。
2. 已知 URL 直接抓取正文；若抓取失败，使用浏览器技能（`browser-cdp`、`opencli-browser`、`playwright` 或桌面 CUA）打开页面。
3. 在浏览器中由智能体输入检索式、提交表单、翻页或展开结果。每个动作记录在输入 manifest 的 `search_log` 数组，包括时间、动作、检索式和结果；不要记录密码、Cookie 或令牌。
4. 页面稳定后截取包含标题、查询条件、结果、日期或条款定位的完整证据图。必要时分为“全页图”和“关键区域图”。
5. 对关键区域使用 `scripts/annotate_screenshot.py` 画框、编号和短标签；原始截图必须保留，标注图另存，禁止覆盖原图。
6. 准备输入 manifest，运行 `scripts/build_evidence_pack.py` 生成 `manifest.json` 和 `index.html`，把每张图、原文摘录、URL、查询式、访问时间、定位信息和置信度关联起来。输入文件与输出包放在不同目录。
7. 在会话中发送标注图；同时给出证据索引的绝对路径。若当前环境支持 `open_in_codex`，打开 `index.html` 或证据目录，让用户一键查看。

先确认宿主是否允许本地文件预览。若浏览器工具限制为 HTTP(S) 并拒绝 `file://`，保留文件面板和会话中的本地路径链接交付，不换通道规避该拒绝；如实区分“已生成文件”和“已在浏览器渲染验证”。

## 最小证据包

```text
evidence/<run-id>/
  manifest.json          # 机器可读元数据和证据关系
  index.html             # 本地一键查看页
  raw/<sha256>.png       # 原始截图的字节一致副本
  annotated/<sha256>.png # 标注图
  annotations/<sha256>.json
  text/<sha256>.txt      # 页面逐字摘录
```

输出的 `manifest.json` 保留顶层 `title`、`scope`、`search_log` 和 `evidence`，将资产路径改为包内相对路径并补充 `sha256`。每条证据至少提供唯一 `evidence_id` 与 `screenshot_path`；建议同时记录 `claim_id`、`query`、`url`、`captured_at`、`title`、`locator`、`excerpt`、`finding`、`source_tier`、`capture_method`、`result_status`、`verification_status`、`verification_checks`、`review_reason` 和 `confidence`。

截图只证明页面在指定时间显示了什么，不证明页面内容永远正确或仍然有效。不要把评分与截图文件的完整性校验混为一谈。

## 标注规则

- 每个框只标注一个可核对事实，如标准编号、发布日期、阈值、搜索条件或结果标题；
- 标签使用短句和稳定编号（如 `K1 条款号`、`K2 阈值`），正文摘录中引用同一编号；
- 框外保留页面标题、域名和访问时间，避免裁剪后失去上下文；
- 关键数字同时抄录到原文文件，通过 `text_path` 关联，并记录字符级或段落级定位；
- OCR 或模型读图不清时标为 `unknown`，不凭截图猜字；
- 登录墙、验证码、地区限制或结果变化要写入 `limitations`，必要时把状态截图作为失败证据。

## 截图标注脚本

依赖 Python 3.10+ 和 Pillow（`python -m pip install Pillow`）。先从实际截图或浏览器返回的尺寸读取原图宽高，再建立 JSON；坐标必须对应未缩放的原始截图像素，左上角为 `(0, 0)`，不要将浏览器 CSS 坐标直接当成截图坐标。文件扩展名和实际格式必须一致；例如当前浏览器工具返回 JPEG 字节时保存为 `.jpg`，不要误写为 `.png`。

```json
{
  "image_width": 1280,
  "image_height": 800,
  "boxes": [
    {"id": "K1", "x": 120, "y": 180, "width": 680, "height": 80, "label": "检索条件：标准编号和关键词"},
    {"id": "K2", "x": 120, "y": 320, "width": 680, "height": 120, "label": "结果条目：标题、版本与状态"}
  ]
}
```

在仓库根目录执行（文件路径按实际替换）：

```powershell
$ErrorActionPreference = 'Stop'
python scripts/annotate_screenshot.py --image captures/run-001/001-page.png --annotations captures/run-001/boxes.json --output captures/run-001/001-page-annotated.png
```

脚本只在原图上画空心框，把编号和可换行的中文说明放在右侧独立图例中，保留原始截图文件。它会拒绝尺寸不匹配、越界坐标、重复编号、覆盖原图或已有输出，并同时导出 `.annotations.json` 记录坐标、原图 SHA-256 与输出尺寸。自动查找 Windows 微软雅黑、macOS 苹方或 Linux Noto CJK；未找到时通过 `--font` 指定支持中文的字体路径。

运行后必须视觉检查标注图：确认框对应实际关键字段，中文可读，图例没有截断。脚本验证坐标有效，不能验证智能体圈选的内容是否正确。

## 生成本地一键查看页

输入 manifest 与采集文件放在同一输入目录，如 `captures/run-001/`。下面的资产路径相对于输入 manifest 所在目录；`confidence` 必须使用实际评分器结果，不填示例分数。

```json
{
  "title": "饮料标签：标准检索证据",
  "scope": "中国大陆；本次访问日；信息核验",
  "search_log": [
    {"at": "实际访问时间", "action": "提交站内检索", "query": "GB 28050", "outcome": "结果页已加载"}
  ],
  "evidence": [
    {
      "evidence_id": "E-001",
      "claim_id": "C-001",
      "title": "实际页面标题",
      "query": "GB 28050",
      "url": "https://example.org/replace-with-real-source",
      "captured_at": "实际截图时间",
      "locator": "实际页码、条款或结果条目",
      "excerpt": "从页面逐字核对的摘录",
      "finding": "摘录能够支持的有限结论",
      "screenshot_path": "001-page.png",
      "annotated_path": "001-page-annotated.png",
      "annotations_path": "001-page-annotated.annotations.json",
      "text_path": "S-001.txt",
      "verification_status": "unverified",
      "verification_checks": [],
      "review_reason": "尚未完成自动核验或必要复核",
      "confidence": null
    }
  ]
}
```

把示例 URL、时间、标题和摘录替换成真实采集值，删除暂时没有生成的可选资产字段；`screenshot_path` 必须存在。之后在仓库根目录执行：

```powershell
$ErrorActionPreference = 'Stop'
python scripts/build_evidence_pack.py --manifest captures/run-001/manifest-input.json --output evidence/run-001
```

脚本仅使用 Python 标准库，输出目录必须不存在或为空。它复制所关联的资产而不移动原文件，使用 SHA-256 命名并记录摘要，生成包含筛选框、原图、标注大图、逐字摘录、核验状态和动作日志的离线 HTML。不要把输入 manifest 放进非空的目标目录后再以同目录作为输出。

`verification_status` 只接受 `auto_verified`、`human_verified`、`needs_review`、`unverified`、`blocked`。`auto_verified` 表示已完成且有记录的自动核验，不表示人工审阅；`result_status` 单独描述页面采集结果，例如 `screen-captured`。

## 失败降级

- 抓取失败但浏览器可读：保留浏览器截图和动作日志，将 `result_status` 记为 `screen-captured`；`verification_status` 仍按实际核验程度填写；
- 浏览器无法自动化：请用户手动打开页面并提供截图，或只交付可复核的检索式和候选 URL，状态为 `unverified`；
- 页面内容随时间变化：保存访问时间、查询式和页面快照；不要把动态结果写成永久事实；
- 网站禁止自动化或需要绕过访问控制：停止自动操作，不尝试规避限制。

## 会话交付格式

每条结论按以下格式返回：

```text
[C-001] 结论（置信度：78/100，中）
证据：S-001，K1/K2；原文摘录：……
页面截图：<当前会话中的标注图>
本地索引：[打开证据包](绝对路径/index.html)
限制：……
```

置信度仍按 `confidence-rubric.md` 计算。页面截图能提高可追溯性，不能替代现行官方原文、原始包装图或必要的人工复核。
