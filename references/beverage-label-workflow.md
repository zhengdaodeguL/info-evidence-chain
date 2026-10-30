# 饮料标签项目工作流

## 工具压缩

原方案中的 DeepSeek、秘塔、Kimi、豆包、通义、表格、可视化和扣子可以压缩为：

- 一个发现入口：`smart-search` 或 `firecrawl-search` 任选其一；
- 官方原文：国家标准全文公开系统、监管部门/卫健委等原始页面，作为证据库；
- 一个 OCR/多模态工具：批量提取标签字段；
- 一个表格：保存原图、OCR、人工修订、规范化单位、公式和判定；
- 一个可选智能体：只查询已核验台账，时间不足时用录屏原型。

AI 搜索只负责找线索；标准条件必须回到当前有效原文。OCR 必须逐张看图。任何“无糖/低糖/0 蔗糖”判定都要把包装原词、标准原词、版本、条款定位和适用范围放在同一行。

## 推荐台账列

`item_id`、`category`、`photo_front`、`photo_nutrition`、`photo_ingredients`、`net_content_ml`、`nutrition_basis`、`carbohydrate_per_100ml`、`sugar_per_100ml`、`sugar_per_bottle`、`ingredients_raw`、`hidden_sugar_terms`、`hidden_sugar_position`、`front_claim_raw`、`claim_source_id`、`claim_decision`、`ocr_raw`、`human_correction`、`verification_status`、`formula`、`confidence_score`、`confidence_level`、`notes`。

## 计算与单位

先确认营养成分表基准是每 100 mL、每份还是整瓶，再统一到项目采用的比较基准。常见计算：

```text
sugar_per_bottle = sugar_per_basis × net_content_ml / basis_ml
load_percent = sugar_per_bottle / chosen_reference_g × 100
```

`chosen_reference_g` 必须在方法页注明来源、版本、适用人群和是否只是研究参照。不要把“添加糖建议”与标签中的“糖”自动画等号；如果标签只给总糖或碳水化合物，结论应写成“标签显示的糖/碳水化合物”，并说明无法从标签单独确认添加糖。

## 三类人工闸门

1. **OCR 闸门**：对配料表前三位、糖/碳水数值、净含量、宣称逐项回看原图；错误保留在 `ocr_raw`，修订写入 `human_correction`。
2. **标准闸门**：对每个声称回到当前原文，记录标准版本和条款；“标准未找到对应规定”只能写成检索结果，不能自动升级为违法或欺骗。
3. **结论闸门**：抽样回看包装，三人或双人复核争议条目；记录样本范围、城市、店铺类型、时间点和未覆盖产品。

## 输出三件套

- **标签解码卡**：先看营养成分表基准，再统一规格，再看配料表顺序，最后看正面宣称与原文条款是否对应。
- **选购地图**：只按本项目定义的标签信息分组，不写医疗/膳食许可；用编号和适用条件表达。
- **扫标签小助手**：输入品名或图片后，只返回台账中已核验字段、`source_id`、记录日期、置信等级和“需人工复核”提示；未知品必须明确说未知。

## 作品中要展示的证据

至少展示一条 OCR 纠错、一条 AI 条款转述被原文纠正、一条人工与 AI 判定不一致的处理记录。这样能证明 AI 用于扩大检索和提取，人用于核验和边界控制。

## 风险措辞

编号代替品牌；不作安全性、疗效或个体化建议；说明单城市、单时点、样本规模和抽样方式；把当前标准版本和访问日期写进作品。若标准或健康建议在提交前发生变化，重新核验并记录版本差异。
