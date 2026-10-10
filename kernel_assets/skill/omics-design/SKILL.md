---
name: omics-design
description: PCLRadiomics 十阶段研究设计与手稿审阅工作流（调用 radiomics-workbench MCP 工具）
---
# 组学研究设计工作流

当任务涉及组学研究设计、统计方案、SCI 写作结构或手稿缺陷审阅时使用本技能。
宿主程序通过 MCP 服务器 `radiomics-workbench` 提供领域工具。

## 十阶段流程

用 `list_stages` 获取完整清单（十阶段，覆盖 CLEAR / METRICS / TRIPOD+AI /
PROBAST+AI / CLAIM / RQS / IBSI / MIAPE / MSI 等报告规范）。

## 工具速查

| 目的 | 工具 |
|---|---|
| 流程/项目现状 | `list_stages`、`project_overview`、`project_get_stage` |
| 生成与改写设计 | `design_ask`、`design_rewrite`、`design_finalize` |
| 写回阶段 | `project_set_stage`（status/final/checklist） |
| 手稿审阅 | `manuscript_review`、`manuscript_defects`、`manuscript_apply`、`manuscript_report` |
| 导出 | `export_markdown`、`export_docx` |
| 临时问答 | `llm_chat`、`llm_models` |

## 规则

- 需要用户澄清时**用 question 工具**，不要自行假设。
- 先读现状再改写；写完用 `project_set_stage` 落盘。
- 报告缺陷必须可证据化（引用手稿中的具体位置/数据）。
