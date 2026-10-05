# v1.2.1 · 手稿审阅可用性修复

v1.2.0 的打包产物（exe / dmg）**不含本页的任何修复** —— 那些资产由 v1.2.0 tag
（较早的提交）构建。本版重建全部产物。

---

## 修了什么

### 1. 一键审阅现在共享当前项目已导入的 Word

**症状**：已经导入过 Word 的项目，再点「★ 一键审阅并自动落批注」仍会弹出文件选择框；
更糟的是项目被换掉，已选定的「审稿批注版」与落盘记录都丢了。

**两处独立缺陷**：

- 界面层 `_start("all")` 只看「项目是否为 None」，所以已导入时仍走弹框分支；
- 引擎层 `run_all` 调 `ingest(path, design=...)` 时**没把当前项目传进去**，直接新建空白项目。

**现在**：已导入且文件在位 → 直接复用（并跳过重复解析）；文件被移走 → 提示并把对话框
默认开到原目录；从未导入 → 才弹框。关键是在**同一个项目对象上继续**，因此沿用
`annotated_path`（已选审稿批注版）、课题关联、落盘记录与报告路径。

**安全边界**：复用只在**同一份稿件**（`source_path` 完全一致）时发生，换稿会新建项目，
绝不把两份手稿的缺陷与批注混进一个项目。

### 2. 流式响应被中途掐断（`IncompleteRead`）自动重试

**症状**：审阅跑到某批报 `LLMError: 请求失败：IncompleteRead(0 bytes read)`，该批 0 条缺陷。

**根因**：`_chat_stream` 的 `try` 只包住 `urlopen`，而响应体是在 `with resp:` 的 for 循环里读的
—— 循环毫无保护，连接被掐在半路就整批白跑。

**现在**：整个「发请求 + 读流」都在重试保护内，指数退避 1s → 2s → 4s（封顶 8s），
默认重试 2 次（`retries` 可配）。4xx/5xx 不重试。重试提示以 `note` 事件显示，**不会混进正文**。

> `http.client.IncompleteRead` **不是 `OSError` 子类**（只继承 `HTTPException`），
> 必须单独列进可重试集合，否则重试逻辑不会生效。

**顺带修掉一个更隐蔽的问题**：服务端声明 `Content-Length` 却只发一半、或 chunked 发一半就断时，
**urllib 不抛任何异常**，半截正文会被当成完整结果写进定稿 —— 比抛错更危险。
现在额外校验「流确实正常结束」：既无 `data: [DONE]`、也无 `finish_reason` 即判为传输故障并重试。

### 3. 失败不再静默

`on_failed` 原先只往右栏「执行流水」写一行，中栏仍显示「还没有导入手稿」、左栏状态行不动，
观感就是「导入了却说没导入」。现在**状态行 + 流水 + 弹窗**三处同时报错，并补一次 `refresh()`。

### 4. 打包版可直接命令行审阅

新增 `manuscript_review` 子命令（别名 `mr`），解决「打包成 exe 后没法用
`python -m manuscript_review.cli`、排查缺模块又没有不依赖界面的入口」：

```bat
PCLRadiomics.exe manuscript_review --selfcheck      :: 逐个子模块自检
PCLRadiomics.exe manuscript_review --toolchain      :: OfficeCLI / PyMuPDF 就绪情况
PCLRadiomics.exe manuscript_review --layers-info    :: 三层条目统计
PCLRadiomics.exe manuscript_review 手稿.docx        :: 直接跑审阅并自动落盘
PCLRadiomics.exe mr 手稿.docx                       :: 别名
```

### 5. 构建与依赖加固

- `pclradiomics.spec` / `pclradiomics_macos.spec`：显式收集 `manuscript_review` 全部子模块
  （原先前者的包内 `cli` 子模块没被收进去），并新增**打包前置校验** ——
  硬编码进 `hiddenimports` 的本地模块逐个真实导入，任一失败即**中止打包**，
  不再产出「能编译但缺功能」的坏包。
- CI（`.github/workflows/build-windows.yml` / `build-macos.yml`）：导入自检补上
  `manuscript_review` 与 `docx_export`；打包后对**冻结产物**执行
  `manuscript_review --selfcheck`，不齐备就让构建失败。这正是当初漏掉问题的原因。
- `requirements.txt` 补上 **PyMuPDF**（`fitz`）—— 它是导入 PDF 的依赖，原先只在本地环境有。
- `.gitignore`：忽略 `_dl/`、`_repro/`、`_fixed/` 与 `标准流程检查表_*.md` 等产物。

---

## 验证

| 项目 | 结果 |
|---|---|
| 一键审阅共享已导入稿 | 文件对话框被调 **0** 次；跳过重复解析；`annotated_path` 保住并仍走「并入批注版」；产物真实存在 |
| 复用安全边界 | 同一稿 → 复用同一对象、标记保住；换稿 → 新建项目、标记被清空 |
| 传输中断重试 | 前 2 次抛 `IncompleteRead` → 第 3 次成功（`attempts=3`，2 条 note，正文未污染） |
| 重试耗尽 | 报「已重试 2 次仍失败：…0 bytes read」 |
| 静默截断检测 | 只发一半且无 `[DONE]` → 识别并重试，最终拿到完整正文（修复前返回半截却当成功） |
| 正常流不误判 | 4 种正常结束形态全部一次成功，误判 0 例 |
| 冻结包自检 | `manuscript_review --selfcheck` → **11/11** 子模块可导入 |
| 冻结包实跑 | 合成样例 29 段 → **31 批注 + 16 修订**，修订稿与报告正确落盘 |
| 回归 | `_test_convergence` 33/33 · `_test_guide` 33/33 · `_test_web` 201/201 |

---

## 已知限制（未变）

1. **PDF 转换必然有损**：公式、复杂表格、图注可能失真；修订落在**转换稿**上。
2. **程序不替作者造数据**：缺失报告项的补正段是**占位待补**文字。
3. **LLM 判据不是金标准**：语义层可能误报漏报，每条批注都标了来源便于区分。

> 完整技术说明见
> [`manuscript_review/README.md`](https://github.com/hg3992260/Completion-of-the-omics-research-design-plan/blob/main/manuscript_review/README.md)；
> 可复现的端到端验证脚本见
> [`manuscript_review/verify/`](https://github.com/hg3992260/Completion-of-the-omics-research-design-plan/tree/main/manuscript_review/verify)，全部基于纯合成样例。
