# AGENTS.md

本目录是 `info-evidence-chain` 技能。修改前先读：

- [DESIGN.md](./DESIGN.md)：设计方向、主色、证据卡组件和信息层级。
- [DEVELOPMENT.md](./DEVELOPMENT.md)：目录、数据字段、脚本边界和验证命令。
- [SKILL.md](./SKILL.md)：对外技能入口和工具路由。

不要把 AI 摘要升级成权威证据，不要删除原始材料，不要把证据分数写成概率。食品标签项目还要读取 `references/beverage-label-workflow.md`。

默认让智能体完成公开站内查询、截图标注、归档和带证据引用的自动核验，仅将异常转人工。`auto_verified` 不等于 `human_verified`。浏览器与标注调用见 `references/browser-evidence-workflow.md`；不得伪造截图、人工确认或自动化比例。生成材料与会话数据放在仓库外或项目忽略目录。
