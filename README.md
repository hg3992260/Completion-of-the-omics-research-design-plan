# 组学研究工具包：设计工作台 + 标准流程管线

两个 PyCt6 / PySide6 桌面程序，共用一个十阶段标准流程知识库（CLEAR / METRICS / TRIPOD+AI / PROBAST+AI /
CLAIM / RQS / IBSI / MIAPE / MSI）：

| 程序 | 作用 | 启动 |
|---|---|---|
| **`design_studio.py`** | **主界面**：贴入初步实验设计 → LLM agent 按十阶段逐段追问与改写 → 输出可执行研究设计 | `启动_设计工作台.bat` |
| `omics_pipeline.py` | 管线视图：十阶段检查表、评分与自评进度 | `启动.bat` |

![设计工作台](_shots/studio_01_draft_dark.png)

---

## 版本

**当前版本：`v1.1.0`** —— 单一版本来源是 `app_paths.APP_VERSION`，与 git tag / GitHub Release 保持一致
（推理 API 的 `Server` 头与 macOS 打包的 `CFBundleVersion` 都读它）。

### v1.1.0 · 四个视图的统一工作台

- **新增 `Statistic` 页**：把「科学问题 → 统计学计算与归纳」的 **9 阶段**架构
  （问题与设计 / 数据与探索 / 建模与检验 / 归纳推断 / 报告与复现）做成可勾选自评页，
  含 **12 行常用检验速查表**与 `stat_run_test` 支持的 **16 种检验类型**清单。
- **新增 `SCI Shape` 页**：把 Glasman-Deal《Science Research Writing》的**七章通用模型**
  （Title → Abstract → Introduction → Methods → Results → Discussion → Conclusion）做成 scope 页，
  含通用模型组件、内容边界、语言与时态规则、词块组与 **59 项自检**。
- **引导式对话**：两个 scope 页都有了 `开始引导 → 提交回答 → 生成定稿 → 采纳并收录` 闭环 ——
  提示词携带**本环节的规范内容**与**项目全部已有素材**，产出可直接采纳的正文
  （统计环节是统计分析方案段落，SCI 章节是该章成稿），采纳时按模型的检查表**自动勾选自检项**。
- **收敛关系交给 LLM 推理（不再硬耦合）**：总览新增「**收敛推理（reason 模式）**」——
  模型通读全部素材后自行判断每条内容收敛到哪一章、各章的来源 / 已有 / 缺失 / 就绪度与理由，
  并给出下一批动作。**代码中不存在任何章节↔阶段/统计的映射表**（`coupling.py` 只做事实统计与素材摘要）。
- **reason 模式**：温度降到 0、token 预算抬到 ≥12000，模型的推理过程（`reasoning_content`）
  以弱化色实时显示。
- **拟物化三维界面**：三维卡片（多层投影 + 渐变面 + 上亮下暗倒角）、流程条（四步键帽 + 进度填充 +
  角标）、金属旋钮步骤条、内嵌凹槽进度条与勾选框、按钮立体皮肤、页面底衬径向渐变。
- **一级界面项目管理**：页头直接 `新建 / 改名 / 删除 / 管理`；改名同步重命名项目文件
  （重名自动加 `(2)` 且显示名与文件名一致），删除二次确认且清空后不落空文件。
- **总览升级**：收敛推理面板 + 三条工作线完成度 + 十阶段评分明细表（整页可滚动）。
- **修复**：深色模式部分「白底白字」（颜色被冻结在创建时的主题）；`RefitLabel` 换行高度按外层宽度
  估算导致临界换行被压；`Project.save()` 无路径时反复生成副本；页头/页脚/按钮的溢出与重叠。
- **自检工具**：`_check_overlap.py`（4 尺寸 × 4 视图遮挡几何判定）、`_check_theme.py`
  （主题一致性 + 像素级对比度验收 + 负向自检）、`_test_guide.py`、`_test_convergence.py`、
  `_test_shape.py`、`_test_stat.py`、`_test_project_ops.py`、`_probe_views.py`。

### v1.0.1 / v1.0.0

- 十阶段设计工作台 + 管线视图（评分与检查表）；LLM 流式追问 / 改写 / 采纳闭环；
  导出 Markdown 与 Word；MCP 服务（stdio + HTTP）；OpenAI 兼容推理 API；Windows / macOS 打包脚本。

---

## 系统要求（含 Windows 7 说明）

| 用途 | 最低系统 | 原因 |
|---|---|---|
| **图形界面**（`design_studio.py` / `omics_pipeline.py` / 合并版 exe） | **Windows 10 / 11（64 位）** | 界面基于 PySide6 6.x（**Qt 6 不支持 Windows 7**）；构建用的 Python ≥ 3.9 也已放弃 Win7 |
| **推理 API**（`api_server.py`） | Windows 7 **SP1** 可行 | 无 Qt 依赖；用 **Python 3.8** 构建即可（见下） |
| **MCP 服务**（`mcp_server.py`） | 取决于 `mcp` 包的 Python 下限 | 一般要求 ≥ 3.10 |
| macOS | macOS 11+ | PySide6 6.x 要求 |

### Windows 7 上报「计算机中丢失 api-ms-win-core-path-l1-1-0.dll」怎么办

`api-ms-win-core-path-l1-1-0.dll` 是 **Windows 8 起才提供的 API set**，而 **Python 3.9+ 的
`python3XX.dll` 会直接导入它**（CPython 自 3.9 起官方不再支持 Windows 7）。PyInstaller 会把
`python311.dll` 一起打进产物，于是 Win7 在**加载阶段**就失败 —— 报错发生在我们的代码运行之前，
程序内部无法拦截，也无法给出更友好的提示。

本仓库自带工具可以实测这一点：

```bat
:: 3.11 的运行时 → 会列出 Win8+ 专有 API set（正是你看到的报错）
python _check_win_target.py D:\python\envs\mar\python311.dll

:: 3.8 的运行时 → 干净，可在 Win7 上运行
python _check_win_target.py <某个 Python 3.8 环境的>\python38.dll
```

**单独补一个 `api-ms-win-core-path-l1-1-0.dll` 解决不了问题**：图形界面还卡在 Qt 6
（Qt 5.15 是最后一个支持 Win7 的版本），而本项目界面基于 PySide6 6.x + PyCt6，无法降到 Qt 5。

### 目标机是 Windows 7 时怎么做

1. **只需要推理 API**（把 Win7 机器当作 OpenAI 兼容服务端，供 Win10 机器或其他客户端调用）：
   运行 **`编译_Win7_API版.bat`** —— 用 Python 3.8 打包 `api_server.py`，
   **不含 Qt**，并在 spec 里排除 `PySide6 / shiboken6 / PyCt6 / mcp / docx` 整条链路。
   目标机需要：Win7 **SP1**(x64) + **KB2533623** + **KB2999226**(UCRT) + **VC++ 2015-2019 运行库**(x64)。
   构建机需要：Python **3.8**（`py -3.8 -m pip install "pyinstaller==6.10" certifi`；
   PyInstaller 6.11+ 要求 ≥3.9，故 3.8 上请用 6.10 或 5.13）。
2. **需要图形界面**：升级到 Windows 10/11；或在一台 Win10 机器上运行主程序，
   用 `PCLRadiomics.exe api --port 8788` / `mcp` 让 Win7 机器以客户端方式使用。
3. 任何构建完成后都建议自检一次：

   ```bat
   python _check_win_target.py dist\PCLRadiomicsAPI\PCLRadiomicsAPI.exe
   :: ✓ 未发现 Win8+/Win10+ 专有 API set  → 该产物可以在 Win7 上跑
   ```

---

## 一、设计工作台（主界面）

### 它怎么工作

1. **输入**：把初步设想（数据类型、例数、中心、终点、打算怎么建模）贴进中间输入框，点「开始分析」。
2. **速读**：agent 先复述这项研究要做什么、属诊断还是预后，并给出 3 条首要关注点。
3. **逐阶段推进**（十阶段，每段两轮）：
   - **第一轮 · 追问**：产出【现状评估】【必须澄清的问题】（2–4 条，每条附"为什么问"）【本阶段小结】；
   - **你来回答**：下方为每条问题生成一个输入框，可只答部分、也可写"不确定"；
   - **第二轮 · 改写**：产出【改写稿】（300–500 字，含参数 / 时间窗 / 判定标准）【检查表】（带 CLEAR、TRIPOD+AI 等条目号）【风险提示】【下一步】；
   - **采纳**：改写稿可直接编辑，点「采纳并收录 → 下一阶段」写入右侧研究设计文档，自动进入下一阶段。
4. **收口**：右侧「生成完整草案」把十个阶段定稿整合成一份研究设计草案 + 待补数据清单 + 投稿前自查。

### 分辨率与文字不遮挡

- **窗口自适应屏幕**：启动时按当前显示器可用区域计算尺寸（`ui_kit.screen_size()`），
  最大 1520×960 且不超过屏幕 96%×94%，并居中显示 —— 不会再出现窗口比屏幕高、底部被任务栏切掉的情况。
- **窄窗口响应式**：宽度 < 1420（管线视图 1340）时自动收起进度条、收窄左右两栏（292/322）
  与下拉框、按钮，表头高度从 96 加到 112 让副标题正常换行；按钮文案统一用短版
  （开始分析 / 提交回答 / 采纳并收录 / 跳过本阶段），任何宽度都不会被截断。
- **文字永不裁切**：所有文字标签改用 `RefitLabel` —— 宽度变化时按**实际宽度**重算换行高度，
  而不是按创建时的估算宽度；步骤条与详情区都放进带滚动条的容器，窗口变矮时滚动而不是压到相邻控件上。
- **自检脚本**：`python _probe_view.py 1200 700` 可在指定尺寸渲染两个界面截图，
  用于核对文字遮挡；`python design_studio.py --demo --shot` 出全套状态截图。

### 项目管理

- **新建**：顶部「新建」→ 输入项目名（默认 `课题_MMDD_HHMM`）+ 可直接粘贴初步设计（也可以先建空项目）。
  新建即落盘，不会因为没保存而丢失。
- **切换**：顶部下拉框直接切换，或点「管理」在列表里双击打开。
- **管理对话框**：列出全部项目（名称 / 完成度 n/10 / 更新时间 / 文件大小 / 模型），支持搜索，按钮包括
  **打开、重命名、创建副本、打开文件夹、删除、新建项目**。
- **重命名**：改显示名的同时**移动项目文件**（`projects/<名称>.json`），旧文件自动移除；
  重名会自动加 `(2)` 后缀，不会覆盖已有项目。
- **删除**：二次确认后移除文件；删的是当前项目时会自动新建一个空项目接续。
- **状态保护**：切换项目、新建、删除、关闭窗口前都会先自动保存当前项目的改动
  （包括还没提交的"初步设计"输入框内容）；项目完成度未满时会自动定位到下一个待完成阶段继续。

项目文件为纯 JSON，可随意备份/迁移；文件损坏的项目会在列表里自动跳过。
**空白项目不会自动落盘**（开窗关窗不再产生空副本）；`--demo` 演示模式也不写入 `projects/`。

### 界面

- **左栏**：十阶段步骤条，颜色即状态 —— 灰=未开始、黄=已追问、青=待采纳、绿✓=已收录；点任意阶段可跳转或重做。
  底部主按钮会**跟随阶段换文案**（开始分析 / 提交回答 / 采纳并收录 / 开始本阶段），
  **等待模型响应时整颗按钮变成"正在思考"动画**：旋转弧线 + 呼吸省略号 + 底部不定量流光条，
  比单纯置灰更直观；请求结束自动恢复为可点击状态。
- **中栏**：对话工作区（流式输出）+ 随阶段切换的输入区（初步设计 / 逐条回答 / 改写稿编辑 / 自由追问）。
  回答阶段每条问题**完整换行显示**（编号 + 问题全文 + "为什么问" + 可多行作答框），
  一屏放不下时工作区自带滚动条，不会出现文字被截断；工作区高度会按中栏空间自动伸缩。
- **右栏**：研究设计文档实时预览；`导出 .md`（**弹出保存对话框自选路径**，默认落在「文档/PCLRadiomics」并记住上次位置；未写扩展名会自动补 `.md`；取消则什么都不做）、
  `导出 Word`（`.docx`：一/二/三级标题层级，检查表排成「# / 条目 / 依据」三列表格，追问与回答排成「问题 / 回答」两列表格，适合伦理申请与论文附件；快捷键 **Ctrl+Shift+E**，Markdown 是 **Ctrl+E**）、
  `生成完整草案`、`打开管线视图（评分与检查表）`。
- **Statistic（统计九阶段与本稿自评）**：顶部「工作台 / Statistic / SCI Shape / 总览」四个视图中的第二个——
  把「科学问题 → 统计学计算与归纳」的 **9 阶段**架构做成可勾选自评页（与 SCI Shape 共用同一套三栏模板）：
  - **左栏**：九阶段步骤条，颜色即状态（灰=未开始、黄=进行中、绿✓=已完成），底部汇总「已完成 n/9 阶段 · 进行中 n · 自检 n/58 项」；
  - **中栏**：所选阶段的目标与核心动作、示例化表述、公式与参数、常见陷阱、输出；
    阶段 6（检验计算）另附**常用检验速查表**（12 行：场景 → 方法 ｜ 前提 ｜ scipy ｜ R）与
    `stat_run_test` 支持的 16 种检验类型；
  - **右栏**：该阶段自检清单（可勾选）、完成度进度条与状态、`全选` / `清空`，以及**该阶段对应的统计工具**
    （12 个：7 控制 + 5 计算，计算层为纯 numpy + scipy）。
  
  9 个阶段按 5 大类着色：**问题与设计 / 数据与探索 / 建模与检验 / 归纳推断 / 报告与复现**。
  勾选结果写入项目 JSON 的 `stat` 字段，与 SCI Shape 的 `shape` 字段相互独立、各记各的进度。
- **SCI Shape（七章结构与本稿自评）**：顶部「工作台 / Statistic / SCI Shape / 总览」标签中的第三个视图——
  按论文印刷顺序列出 **Title → Abstract → Introduction → Methods → Results → Discussion → Conclusion**
  七个环节（沿用与工作台相同的三栏模板与步骤条控件）：
  - **左栏**：七章步骤条，颜色即状态（灰=未开始、黄=进行中、绿✓=已完成），底部汇总「已完成 n/7 章 · 进行中 n · 自检 n/59 项」；
  - **中栏**：所选章节的 scope —— **功能定位**、**通用模型组件**（英文原文 + 中文，按原书顺序）、
    **内容边界**（✓ 必须写 / ✕ 不得写）、**语言与时态**（逐条带书内页码）、**词块组**（英文原短语 + 页码）；
  - **右栏**：该章**自检清单**（可勾选，点整行即可切换）、完成度进度条与状态、`全选` / `清空`，
    以及 Methods / Results 与十阶段管线的对应关系（两处进度分别记录，互不覆盖）。
  
  勾选结果写入项目 JSON 的 `shape` 字段（`projects/<项目名>.json`），切换项目、重启后保持。
  内容取自 Glasman-Deal《Science Research Writing》(2nd ed.) 的 7 个 GENERIC MODEL，页码为书内页码。
- **管线视图（只读表格）**：顶部「工作台 / Statistic / SCI Shape / 总览」标签，或点右栏「打开管线视图（评分与检查表）」——
  以**表格**列出十个阶段，列固定为：

  | # | 阶段 | 状态 | 规范出处 | 结果 / 待办 | 检查表 | 更新 |
  |---|---|---|---|---|---|---|
  | 01 | 研究问题与设计 | ● 已完成 | TRIPOD+AI 3–4 · 18c–d | 定稿：研究类型：诊断准确性研究… | — | 23:06 |
  | 02 | 伦理与数据治理 | ● 已追问 | CLEAR 8 · 13–14 | 已完成追问，等待回答 | — | 23:07 |
  | 03 | 样本量与事件数 | ● 待采纳 | TRIPOD+AI 10 · 21 | 已有改写稿，等待采纳 | 2 | — |

  状态用**红/黄/绿**着色：**绿 = 已完成（已收录定稿）**、**黄 = 已追问 / 待采纳**、**红 = 未开始**；
  表头汇总「● 绿 n 已完成 · ● 黄 n 进行中 · ● 红 n 未开始 · 共 n/10 阶段定稿」+ 进度条。
  表格**完全只读**（禁用编辑、选择与焦点），数据只来自十阶段的结果，随项目状态与深浅色自动重绘。
- **顶部**：**项目命名与删除直接在一级界面完成** ——
  `项目` 下拉框切换当前项目；`新建`（弹窗填名称，可同时粘贴初步设计）、
  `改名`（弹窗预填当前名，确认后**同时重命名项目文件**，重名自动加 `(2)` 后缀且显示名与文件名保持一致）、
  `删除`（二次确认弹窗，说明是否已落盘；删除当前项目后自动换成空白项目，
  且**空白项目不落盘**，不会留下空副本）、`管理`（批量管理弹窗：打开/重命名/创建副本/打开文件夹/删除）。
  窄窗口下自动隐藏「项目 / 模型」两个说明标签、压缩按钮宽度，保证这些入口始终可用且不重叠。
  另有模型切换、LLM 设置、深浅色。

### 拟物化三维界面与流程条

界面按「实体工作台」的思路做了三维化，并把四个视图的**先后顺序**显式画出来：

- **页面底衬**：中心亮、边缘暗的径向渐变，让整块界面有被照亮的纵深；
- **三维卡片**（`ui_kit.Card`）：多层柔和投影 + 竖向渐变面 + 上缘高光/下缘暗边的倒角。
  **投影画在卡片自身矩形内预留的 9px 边距里**（`CARD_PAD`），绝不越出控件边界 —— 这是"不遮挡邻居"的结构性保证；
- **流程条**（`ui_kit.FlowStepper`）：四个视图做成凹槽里的键帽，`设计工作台 → 统计 → SCI 结构 → 总览`，
  当前步骤抬起（强调色渐变 + 投影），已走过的步骤打勾并用强调色填充连接段与箭头，每步下方挂进度角标
  （阶段 n/10、自评 n/58、自评 n/59、定稿 n/10）；点击任意步骤即跳转；
- **步骤条**（`StageRail` 三维化）：金属旋钮（受光面渐变 + 上缘高光 + 投影）+ 贯穿式凹槽轨道，
  已推进的段落被强调色填充；绿✓=已完成、橙=进行中、灰=未开始；
- **其他立体件**：进度条（内嵌凹槽 + 玻璃高光）、勾选框（凹陷空槽 ↔ 凸起绿钮 + 对勾）、
  按钮（渐变面 + 上亮下暗倒角，按下时凹陷）；
- **流程导航**：工作台有「◀ 上一阶段 / 下一阶段 ▶」，两个 scope 页有「◀ 上一环节 / 下一环节 ▶」，
  首/末位置自动置灰。

**遮挡自检**：`python _check_overlap.py` 会在 1120×700 / 1280×800 / 1520×960 / 1920×1080
四种尺寸下遍历四个视图的全部控件，检查①兄弟控件矩形相交 ②子控件溢出父容器 ③换行标签高度不足
④单行标签放不下（滚动区域内部的"超出视口"是设计使然，会跳过）。当前结果：**违规总数 0**。
截图核对用 `python _probe_views.py 1120 700`（可加 `--dark`）。

### 主题一致性（深浅色都不得出现"白字白底"）

PyCt6 的控件把颜色存成 **`(浅色, 深色)` 色对**，主题切换时由控件自己重算。因此**凡是需要在切换主题后
跟着变的颜色，必须传色对（`PAL["surface2"]`），不能传 `C("surface2")` 的求值结果** ——
后者是一个固定字符串，会被**冻结**在创建时的模式里。典型症状就是浅色启动、切到深色后：
底色还是浅色（如 `#F5F9FE`）、文字已变成深色模式的近白色（`#ECEDF0`）→ **白字白底，完全看不见**。

`python _check_theme.py` 专门检查这一类问题：浅色构建四个视图 → 切深色再全部过一遍 → 切回浅色，逐控件比对
①实际色 vs 应有色（冻结）②前景色 = 背景色（直接命中"看不见"）③深色下仍残留浅色底；
并对 Statistic / SCI Shape 两页的中栏与右栏做**像素级对比度验收**（抓取渲染结果逐行找文字带，
要求最大对比 Δ≥90，且用"稀疏性"排除描边与阴影线）。脚本自带**负向自检**：故意注入一个被冻结的浅色底，
必须能被检出，否则判定检查器失效。当前结果：**违规总数 0**（负向自检通过）。

  **默认浅色**（极简蓝白）；点「深色」切换为**亮橙科技配色**（近黑底 + #FF7A1A 主色，
  青绿/琥珀/珊瑚作状态色），两套配色共用同一套控件与图标，切换即时生效。
- **快捷键**：`Space` 开始/继续，`↑↓` 切换阶段，`Ctrl+S` 保存项目，`Ctrl+E` 导出。
- **左下角响应动画**：等待模型返回时，左下角出现**橙色律动胶囊**（4 根均衡器条 + 横向流光 + 实时计时，
  如"追问中 · 12s"），一眼可见程序正在工作；请求结束自动收起为低调灰点，并提示下一步
  （"等待你的回答" / "等待采纳改写稿" / "就绪 · 可随时追问"）。最小窗口宽度下也不与状态文字挤在一起。

项目自动保存在 `projects/<项目名>.json`，随时从顶部下拉框切回。

### LLM 服务

默认 **DeepSeek 官方 `deepseek-v4-pro`**（OpenAI 兼容），密钥**自动复用 agent 自身凭据**
（`~/.dsh/.credentials.yaml` 的 `DEEPSEEK_API_KEY`），无需手工填写。优先级：

```
llm_config.json 里手填的 key  >  环境变量 LLM_API_KEY / DEEPSEEK_API_KEY  >  ~/.dsh/.credentials.yaml
```

顶部「设置」可改 Base URL / API Key / 模型 / 温度，并带「测试连接」。任何 OpenAI 兼容端点都能接
（内网网关、自建服务等）。命令行临时覆盖：

```bat
set LLM_BASE_URL=https://your-gateway/v1
set LLM_MODEL=your-model
set LLM_API_KEY=sk-xxx
启动_设计工作台.bat
```

**注意（推理模型）**：`deepseek-v4-pro` 会把思考 token 也算进 `max_tokens`，预算给小了会出现
"只想不说、正文为空"。客户端已把默认预算设为 8000，并在检测到空正文时自动加倍重试一次；
温度默认 0.4。实测单次调用 30–60 秒、单阶段两轮约 90 秒。

模型选择上的体验差异：`deepseek-v4-pro` 输出更规整、几乎不夹带自我点评；
`deepseek-flash` 更快，但更容易在正文里混入写作说明（代码里已做逐行清洗，仍建议用 v4-pro）。

---

## 二、四个视图之间的收敛关系：由 LLM 推理，不在代码里硬编码

四个视图不是并排的四个工具，而是**三条工作线向同一份稿件收敛**：

| 工作线 | 页面 | 产出 |
|---|---|---|
| 设计工作台（十阶段） | 工作台 | 研究设计内容：设计决策、样本量、采集/分割/特征/建模/评价/开放科学条目 |
| 统计（九阶段） | Statistic | 数字与推断：检验、效应量、置信区间、因果措辞、报告与复现 |
| SCI 结构（七章） | SCI Shape | 写作结构：每章功能、模型组件、内容边界、语言与检查项 |

**"哪条内容该收敛到哪一章、还缺什么、能不能动笔"这类判断全部交给模型的推理模式**
（`reason=True`：温度降到 0、token 预算抬到 ≥12000、推理过程实时显示）。代码里**不存在**
任何章节与阶段/统计的对应表，也不再用映射表去推算收敛度 —— `coupling.py` 只保留两件事实性的事：

- `lane_progress()`：三条线各自的完成计数（纯勾选/定稿统计）；
- `project_digest()`：把项目**全部**已有内容整理成一份摘要原样交给模型
  （十阶段定稿/追问回答、统计九阶段定稿/自检、七章定稿/自检、初步设计与完整草案），
  **不做任何筛选** —— 相关性由模型自己判断。

**在总览里怎么用**（`总览 · 收敛视图与评分`，页面整体可滚动）：

1. **收敛推理（reason 模式）**：点「开始推理」，模型的推理过程以弱化色实时流式显示；
   结果落盘为 `project.convergence`，包含
   **收敛总览**、**判定依据**（它按什么规则判断归属）、
   **各章收敛**（每章：来源 / 已有 / 缺失 / 就绪度 0–100 / 理由）、**下一批动作**（按优先级）；
2. **三条工作线完成度**：设计工作台 n/10 阶段、统计 n/9 阶段、SCI 结构 n/7 章（事实计数）；
3. **十阶段评分与检查表明细表**保留在下方，作为设计工作台线的逐条依据。

流程条上「总览」的角标在有推理结果后显示为模型的**平均就绪度**；SCI 页右栏会显示
**模型给出的本章来源/缺失/就绪度/理由**（按模型自己输出的章节名匹配，不是固定映射）。

`python _test_convergence.py` 校验素材摘要的完整性、模型输出的解析（含格式波动容忍）、
总览渲染与落盘，以及 reason 模式的请求参数（33 项）。

### 两个 scope 页的「引导完善」：同样基于内容的引导式对话

Statistic 与 SCI Shape 页的中间栏都切换两种模式：

| 模式 | 内容 |
|---|---|
| **结构内容** | 该环节的规范内容（统计：要点/示例/公式/陷阱/输出；SCI：通用模型/内容边界/语言时态/词块组） |
| **引导完善** | 与工作台同构的闭环：**追问 → 回答 → 定稿 → 采纳** |

闭环的四步（按钮：`开始引导` / `提交回答` / `生成定稿` / `采纳并收录`）：

1. **追问**：模型先读**本环节的规范内容**（要点、通用模型组件、必写/禁写、时态规则、自检清单），
   再读**项目全部已有内容（摘要不做筛选）**（统计环节读它对应的工作台阶段定稿；SCI 章节读「工作台阶段 + 统计阶段」
   以及同页其他章节的定稿），产出【现状评估】（必须引用你的实际内容）+【必须澄清的问题】（每条附"为什么问"）；
2. **回答**：每个问题一个作答框，可只答部分；未答的模型会按常规做法给建议值并标注待确认；
3. **定稿**：产出可直接采纳的正文 —— 统计环节是**可放进统计分析方案（SAP）的段落**（含检验、参数、
   判定标准），SCI 章节是**该章的成稿文字**（按通用模型组件顺序、遵守该章时态与内容边界）；
   同时给出【检查表】判定（逐条标明自检清单是否已满足）与【风险提示】。定稿框可直接编辑；
4. **采纳并收录**：定稿写入项目（`project.stat` / `project.shape` 的 `final`），
   **并按模型的检查表自动勾选已满足的自检项** —— 于是总览的收敛度、缺口清单、流程条角标随之更新。

引导状态（未开始 → 已追问 → 待采纳 → 已定稿）显示在中间栏右上角与右栏；追问、回答、定稿、风险提示
全部持久化在项目 JSON 里，可随时切回继续。

`python _test_guide.py` 用**假 LLM** 跑完整闭环并校验 32 项（含"提示词确实带入了耦合来源的定稿"、
自动勾选、收敛度提升、落盘与重载）。

## 三、管线视图（评分与检查表）
![管线视图](_shots/01_dark_default.png)

左侧十阶段管线（自绘节点 + 连接箭头，已完成段落连线变青）、中间阶段详情（目标 / 可勾选的必做动作 /
必报参数）、右侧本案例达标-部分-缺失自评与常见缺陷；勾选计入进度，导出 Markdown 检查表，
状态存 `progress_state.json`。启动：`启动.bat`。

---

- **底部署名**：两个程序窗口底部都有一行署名
  `designed by christ.paul90@gmail.com ,all rights reserved`（右下角，浅/深色自适应；
  邮箱可点击，直接调起邮件客户端）。
- **图标与启动画面**：`LOGO.jpg`（PCL-Radiomics）已作为程序图标 —— 标题栏/任务栏/Alt-Tab 显示多尺寸
  图标，界面标题左侧有 28×28 角标；主界面启动时短暂显示启动画面（约 1.1 秒，`design_studio.SHOW_SPLASH`
  可关闭，`--shot/--e2e/--demo` 模式下自动跳过）。
  重新生成图标资源：把新图覆盖 `LOGO.jpg` 后运行 README 同目录的生成脚本即可（见下）。

## 三、把程序当作服务提供（MCP / OpenAI API）

程序的后端本来就是三层解耦的 —— `llm_client.py`（传输）/ `design_agent.py`（提示词与领域逻辑）/
`stages_data.py`（标准流程知识），所以两种对外服务都只是薄封装，**无需改动主程序**。

### 3.1 MCP 服务器（供 agent 调用）

```bat
启动_MCP服务.bat                          :: stdio，默认传输
D:\python\envs\mar\python.exe mcp_server.py --transport streamable-http --port 8765
D:\python\envs\mar\python.exe mcp_server.py --list-tools      :: 只看工具清单
```

12 个工具，分三层：

| 层 | 工具 | 说明 |
|---|---|---|
| 知识 | `list_stages` | 十阶段：规范出处、必做动作、必报参数、常见缺陷、参考条目 |
| 领域 | `design_ask` / `design_rewrite` / `design_finalize` | 追问 → 改写（含检查表/风险） → 汇总成完整设计草案 |
| 项目 | `list_projects` / `create_project` / `project_overview` / `project_get_stage` / `project_set_stage` / `export_markdown` | 项目读写；`project_overview` 即界面那张管线视图表格 |
| 通道 | `llm_chat` / `llm_models` | 原样调用背后的 DeepSeek，agent 可当 LLM 网关用 |

注册到 MCP 客户端（DSH / Claude Desktop / opencode 的 `mcpServers` 段，现成文件见 `mcp.json`）：

```json
{ "mcpServers": { "radiomics-workbench": {
    "command": "D:\\python\\envs\\mar\\python.exe",
    "args": ["I:\\文件\\CTCC\\HL\\omics_pipeline\\mcp_server.py"] } } }
```

### 3.2 独立推理服务（OpenAI 兼容 API）

```bat
启动_推理API.bat                            :: http://127.0.0.1:8788/v1
D:\python\envs\mar\python.exe api_server.py --port 8788 --model deepseek-v4-pro
```

| 端点 | 作用 |
|---|---|
| `GET /health` | 模型、上游、密钥（脱敏）、调用/流式/token 计数 |
| `GET /v1/models` | 上游模型列表 |
| `POST /v1/chat/completions` | 对话补全，支持 `stream: true`（SSE 直通，`reasoning_content` 一并透传） |

任何支持自定义 base_url 的客户端可直接接入：

```python
from openai import OpenAI
cli = OpenAI(base_url="http://127.0.0.1:8788/v1", api_key="not-needed")
r = cli.chat.completions.create(model="deepseek-v4-pro", messages=[{"role": "user", "content": "你好"}])
```

**安全**：默认只绑 `127.0.0.1`（不对外网开放，避免把带密钥的代理暴露出去）；
局域网共享需显式 `--host 0.0.0.0 --token <口令>`，客户端带 `Authorization: Bearer <口令>`。
密钥解析复用 `llm_client.load_config()`（界面手填 > 环境变量 > agent 凭据），服务本身不另存密钥。

### 3.3 自检脚本

```bat
D:\python\envs\mar\python.exe _test_mcp_stdio.py     :: stdio 传输（与 DSH 拉起方式一致）
D:\python\envs\mar\python.exe _test_mcp_client.py    :: streamable-http 传输
D:\python\envs\mar\python.exe _test_api.py           :: /health、/v1/models、非流式、流式
D:\python\envs\mar\python.exe _test_api_stream.py    :: 流式细化（区分正文与思考分片）
```

> 注意：在受限沙箱里跑 stdio 自检会因 Windows 命名管道被拦而报 `WinError 5`；
> 由 DSH / Claude Desktop 作为父进程拉起时不受此限。

## 五、打包成 exe（一个 exe 承载全部模式）

> **产物系统要求：Windows 10 / 11（64 位）。** 原因与 Windows 7 的处理办法见上面的
> 「[系统要求](#系统要求含-windows-7-说明)」小节 —— 简言之：Python 3.9+ 与 Qt 6 都不支持 Win7。
> 若目标机是 Win7 且只需要推理 API，用 `编译_Win7_API版.bat`（Python 3.8 + 无 Qt）。

```bat
build_exe.bat            :: 文件夹版（onedir，启动快，适合 MCP 常驻）
编译单文件版.bat          :: 单文件版（onefile，拷一个文件就能跑）
编译_Win7_API版.bat       :: Windows 7 专用：仅推理 API（Python 3.8，不含 Qt）
:: 或手动
D:\python\envs\mar\python.exe -m PyInstaller --noconfirm --clean pclradiomics.spec
set PCL_ONEFILE=1 && D:\python\envs\mar\python.exe -m PyInstaller --noconfirm --clean --distpath dist-onefile pclradiomics.spec
:: Win7 版（需先装 Python 3.8）
py -3.8 -m PyInstaller --noconfirm --clean pclradiomics_api_win7.spec
```

| 形态 | 体积 | 启动 | 适用 |
|---|---|---|---|
| 文件夹版 `dist\PCLRadiomics\PCLRadiomics.exe` | 148 MB 目录 | 0.3–1.5s | MCP 常驻（客户端会反复拉起） |
| **单文件版 `dist-onefile\PCLRadiomics.exe`** | **65 MB 单文件** | CLI 2.5–4.4s、GUI ~10s | 分发/临时试用（每次启动解包到 `%TEMP%`） |

两种形态**都支持全部模式**（实测）：图形界面、`mcp`（stdio 与 streamable-http）、
`api`（OpenAI 兼容，含 SSE 流式）、`check/net/stages/projects/paths`。

```bat
PCLRadiomics.exe                                    :: 图形界面（双击即可，无黑框）
PCLRadiomics.exe mcp                                :: MCP stdio —— 供 DSH / Claude Desktop 注册
PCLRadiomics.exe mcp --transport streamable-http --port 8765
PCLRadiomics.exe api --port 8788                    :: OpenAI 兼容推理服务
PCLRadiomics.exe check ^| net ^| stages ^| projects ^| paths
```

冻结版 MCP 注册片段：`mcp_frozen.json`。

### 「一个 exe 同时当界面程序和 stdio 服务」是怎么做到的

**矛盾点**：stdio 传输要求进程有真实 stdout，所以直觉上必须编成 console 子系统；
但 console 程序双击时会弹黑框，而 Win11 默认控制台由 Windows Terminal 托管
（窗口类 `CASCADIA_HOSTING_WINDOW_CLASS`，属于别的进程），
用 `ShowWindow(GetConsoleWindow())` **藏不掉**——实测确实会留下一个终端窗口。

**解法（`win_stdio.py`）**：编成 **windowed**（GUI 子系统，永远没有黑框），
再按需把标准流接回来：

| 启动方式 | 接管路径 | 结果 |
|---|---|---|
| MCP 客户端用管道拉起 | `GetStdHandle` 拿到父进程给的管道句柄 → `open_osfhandle` 包成文本流（带 `.buffer`） | stdio 传输正常 |
| 终端里手敲命令 | 没有管道 → `AttachConsole(-1)` 附加上父控制台，重开 `CONOUT$/CONIN$` | 日志照常显示 |
| 双击图形界面 | 两者都没有 → 落到 devnull | 干净无声，无黑框 |

实测：双击后新增的可见窗口**只有**「组学研究设计工作台」这一个（无任何终端窗口）；
同时 `mcp` stdio 握手成功、12 工具可调、`llm_chat` 真实返回。
需要控制台版调试时：`set PCL_CONSOLE=1`；想打成单文件：`set PCL_ONEFILE=1`。
只要小体积服务端（约 54 MB，不带界面）：`pclradiomics_service.spec`。

### 打包时必须处理的四件事（均已在代码里解决）

1. **可写路径要脱离 `__file__`** —— 冻结后 `__file__` 指向临时解包目录，写入会丢。
   `app_paths.py` 统一解析：只读资源（主题/图标）取 exe 同级 → 打包内置 → 源码目录；
   可写数据（`projects/`、`llm_config.json`、导出 md、`error.log`）一律放 exe 同级，
   不可写时退到 `%LOCALAPPDATA%\PCLRadiomics`，实现绿色便携。
2. **HTTPS 证书** —— 冻结后 `ssl` 枚举 Windows 证书库会报
   `SSLError: [ASN1: NOT_ENOUGH_DATA]`，导致所有上游调用失败（症状：`可用模型 []`）。
   已改为优先使用随包携带的 `certifi` 根证书（`llm_client.ssl_context()`）。
3. **PyCt6 自带主题 JSON** —— 不显式收集 `collect_data_files("PyCt6")`，
   图形版会因 `FileNotFoundError: _internal\PyCt6\widgets\themes\blue.json` **静默退出**。
4. **体积** —— PyInstaller 会顺带打包 numpy/PIL 及其 **Intel MKL（约 350 MB）**，
   本程序运行期完全用不到，已在 spec 里排除（592 MB → 148 MB）。

### windowed 构建的排错

图形版没有控制台，崩溃时界面直接消失。`cli.py` 会把未捕获异常写入
**exe 同级 `error.log`** 并弹系统对话框提示，先看这个文件。

### 自检脚本

```bat
D:\python\envs\mar\python.exe _test_merged.py        :: 一个 exe 的全部模式（CLI/API/MCP-http/GUI）
D:\python\envs\mar\python.exe _test_frozen_stdio.py  :: 冻结 exe 的 stdio MCP（与 DSH 拉起方式一致）
D:\python\envs\mar\python.exe _test_console.py       :: 双击时会不会冒黑框
```

> 受限沙箱里跑 stdio 自检会因命名管道报 `WinError 5`；由 MCP 客户端作为父进程拉起时不受影响。

## 六、macOS 版（.app / .dmg）

macOS 与 Windows 的差异**已在代码里处理**，不需要额外分支：

| 差异点 | 处理方式 |
|---|---|
| 中文字体 | `ui_kit` 在 darwin 上用 **PingFang SC**（Windows 用微软雅黑，Linux 用 Noto Sans CJK） |
| 窗口图标 | macOS 用 `logo_mark.png`（PNG），Windows 用多尺寸 `logo_icon.ico` |
| 数据目录 | macOS 冻结后写 **`~/Library/Application Support/PCLRadiomics`**（.app 包内只读，不能写）；Windows 写 exe 同级 |
| 标准流 | `win_stdio` 只在 Windows 生效；macOS 的二进制本身就有 stdout，stdio MCP 直接可用 |
| 崩溃提示 | Windows 用 MessageBox，macOS 用 `osascript` 弹窗，堆栈同样写 `error.log` |

打包（**必须在 macOS 上执行**，PyInstaller 不支持跨平台编译）：

```bash
python -m PyInstaller --noconfirm --clean pclradiomics_macos.spec
./make_dmg.sh                              # 生成可拖拽安装的 dmg
PCL_VERSION=1.2.0 ./make_dmg.sh            # 指定版本号
PCL_ARCH=universal2 python -m PyInstaller ... pclradiomics_macos.spec   # Intel+ARM 通用（依赖需有 universal2 轮子）
```

产物：

| 文件 | 说明 |
|---|---|
| `dist/PCLRadiomics.app` | 图形界面，拖进「应用程序」即可；内含 `Contents/MacOS/PCLRadiomics` 命令行入口 |
| `dist/pclradiomics-cli/pclradiomics` | 纯命令行版（不含 Qt，约 50 MB）——**MCP 注册建议用这个** |
| `PCLRadiomics-<版本>-macos-<架构>.dmg` | 拖拽安装镜像：左边应用图标、右边 Applications 快捷方式 |

macOS 上的 MCP 注册（指向命令行版最省事）：

```json
{ "mcpServers": { "radiomics-workbench": {
    "command": "/Applications/PCLRadiomics.app/Contents/MacOS/PCLRadiomics",
    "args": ["mcp"] } } }
```

> **Gatekeeper**：dmg 未做 Apple 签名与公证，首次打开可能被拦。
> 解决：右键点应用 → 打开；或执行 `xattr -dr com.apple.quarantine /Applications/PCLRadiomics.app`。
> 要做正式签名/公证需 Apple 开发者证书，可在 workflow 里加 secrets 后开启（暂未启用）。

CI：`.github/workflows/build-macos.yml`（默认 `macos-latest` = Apple Silicon；
手动触发可选 `macos-13` 出 Intel 版，或勾 `universal2` 试通用二进制）。

## 七、上传 GitHub 自动编译

仓库里已备好 CI：`.github/workflows/build-windows.yml`。
推上去就会在 GitHub 的 Windows 机器上自动装依赖、打包、校验并上传产物。

```bat
cd /d I:\文件\CTCC\HL\omics_pipeline
git init
git add .
git commit -m "PCL-Radiomics workbench: GUI + MCP + OpenAI-compatible API"
git branch -M main
git remote add origin https://github.com/<你的账号>/<仓库名>.git
git push -u origin main
```

- **触发**：推 `main`／发 PR／手动 Run workflow；推 `v*` tag 时额外创建 Release 并附 zip。
- **产物**：Actions 页面该次运行的 Artifacts 里下载 `PCLRadiomics-windows-x64.zip`
  （文件夹版）。
- **要单文件版（onefile）**：Actions → build-windows → **Run workflow → 勾选 `onefile`**，
  或直接双击 `触发云端单文件编译.bat`／执行
  `gh workflow run build-windows.yml -f onefile=true`。
  该次运行的产物里会同时有 `PCLRadiomics-windows-x64.zip` 与 **`PCLRadiomics.exe`（65 MB 单文件）**。
- **注意**：`.github/workflows/` 下的文件只有带 `workflow` 权限的令牌才能改；
  普通源码同步不受影响（`gh auth refresh -s workflow` 可补权限）。
- **想让 CI 顺带做真实模型连通性测试**：仓库 Settings → Secrets → Actions 添加
  `DEEPSEEK_API_KEY`；没配就自动跳过（不影响构建成功）。
- **应用在子目录时**：把 workflow 顶部的 `APP_DIR: "."` 改成子目录名即可。
- **隐私检查**：`.gitignore` 已排除 `projects/`（研究数据）、`llm_config.json`、
  `dist/`、`build/`、`_*.txt` 等；本仓库文件经检查**不含任何明文 API Key**
  （密钥由运行期从环境变量或 `~/.dsh/.credentials.yaml` 读取）。

## 七、文件说明

| 文件 | 作用 |
|---|---|
| `design_studio.py` | 主界面：三栏工作台、Statistic 与 SCI Shape 视图、流式对话、阶段状态机、设置弹窗、导出 |
| `design_agent.py` | agent 层：十阶段提示词、`【小节】`解析、输出清洗（剔除模型自我点评）、项目模型与文档渲染 |
| `llm_client.py` | OpenAI 兼容客户端：配置解析（含 agent 凭据）、流式 SSE、空正文自动重试、模型列表 |
| `ui_kit.py` | 共享 UI：配色、自适应标签、**三维卡片/流程条/勾选框与底衬绘制**、进度条、对话视图 |
| `omics_pipeline.py` | 管线视图（评分与检查表） |
| `stages_data.py` | **十阶段内容**（目标 / 必做动作 / 必报参数 / 常见缺陷 / 本案例状态 / 规范条目）——改这里即可换课题 |
| `shape_data.py` | **SCI 七章 scope**（功能定位 / 通用模型组件 / 内容边界 / 语言时态 / 词块组 / 自检项，均带书内页码）——SCI Shape 页的数据源，改这里即可换模板 |
| `stat_data.py` | **统计九阶段 scope**（目标与核心动作 / 示例化表述 / 公式 / 常见陷阱 / 输出 / 对应工具 / 自检项）+ 12 行常用检验速查表 —— Statistic 页的数据源 |
| `scope_core.py` | 两页共用的 scope 逻辑（勾选记录、进度、状态、汇总），UI 与数据都不依赖它以外的东西 |
| `theme_tech.json` | PyCt6 主题：**浅色 = 极简蓝白，深色 = 亮橙科技**（8 个控件段，深浅双色） |
| `LOGO.jpg` → `logo_icon.ico` / `logo_mark.png` / `logo_badge.png` / `logo_banner.png` | 由原图派生的图标资源：多尺寸 `.ico`（16–256）用于窗口/任务栏/快捷方式，方版徽标与 28×28 角标用于界面，全幅图用于启动画面 |
| `组学研究设计工作台.lnk` / `标准流程管线.lnk` | 带图标的 Windows 快捷方式，双击即启动（可拖到桌面/任务栏） |
| `projects/` | 课题项目存档（JSON，自动保存） |
| `llm_config.json` | 非敏感配置（模型、温度、预算）；密钥仅在手工填写时写入 |
| `启动_设计工作台.bat` / `启动.bat` | 一键启动（自动选用已装 PyCt6 的解释器） |
| `_shots/` | 界面截图（`--shot` / `--demo --shot` 自检生成） |

数据与界面完全分离：`stages_data.py` 换内容，`design_agent.py` 换提示词，UI 不用改。

## 四、自检命令

```bat
:: 主界面：离线假对话 + 截图（不调用网络）
D:\python\envs\mar\python.exe design_studio.py --demo --shot

:: 主界面：真实 LLM 端到端（无窗口，跑完三个阶段并写 _e2e_agent.log）
D:\python\envs\mar\python.exe _e2e_agent.py deepseek-v4-pro

:: LLM 连通性
D:\python\envs\mar\python.exe llm_client.py

:: 管线视图截图
D:\python\envs\mar\python.exe omics_pipeline.py --shot

:: 遮挡检查：4 种窗口尺寸 × 4 个视图，几何判定（相交/溢出/文字截断）
D:\python\envs\mar\python.exe _check_overlap.py

:: 主题一致性：浅色 → 深色 → 浅色，逐控件查冻结色与"前景=背景"，并做像素级对比度验收
D:\python\envs\mar\python.exe _check_theme.py

:: 收敛推理（reason 模式）：素材摘要 → 模型自行判断各章来源/缺口/就绪度
D:\python\envs\mar\python.exe _test_convergence.py

:: 引导式对话闭环（假 LLM，确定性）：追问→回答→定稿→采纳→自动勾选
D:\python\envs\mar\python.exe _test_guide.py

:: 四个视图与项目命名/删除的功能回归
D:\python\envs\mar\python.exe _test_stat.py
D:\python\envs\mar\python.exe _test_shape.py
D:\python\envs\mar\python.exe _test_project_ops.py

:: 多尺寸四视图截图（可加 --dark）
D:\python\envs\mar\python.exe _probe_views.py 1120 700

:: 目标系统检查：当前工具链的最低 Windows 要求 / 某个 exe 是否含 Win8+ 专有 API set
D:\python\envs\mar\python.exe _check_win_target.py
D:\python\envs\mar\python.exe _check_win_target.py dist\PCLRadiomics\PCLRadiomics.exe
```

## 五、规范依据

- **CLEAR**（58 项）Kocak B, et al. Insights Imaging 2023 · doi:10.1186/s13244-023-01415-8
- **METRICS**（30 项 / 9 类）Kocak B, et al. Insights Imaging 2024 · doi:10.1186/s13244-023-01572-w
- **TRIPOD+AI**（27 项）Collins GS, et al. BMJ 2024;385:e078378
- **PROBAST+AI** Moons KGM, et al. BMJ 2025 · doi:10.1136/bmj-2024-082505
- **CLAIM 2024** Radiol Artif Intell · doi:10.1148/ryai.240300
- **RQS**（16 项 / 36 分）Lambin P, et al. Nat Rev Clin Oncol 2017;14:749
- **IBSI** Zwanenburg A, et al. Radiology 2020;295:328 与 Radiology 2024 · doi:10.1148/radiol.231319
- **样本量** Riley RD, et al. BMJ 2020;368:m441 ｜ **MIAPE** Nat Biotechnol 2007 ｜ **MSI** Metabolomics 2007

> 案例数据来源：Cheng S, et al. Adv Sci 2025;12(20):e2409488（CC BY 4.0）。本工具为流程参考，
> 阶段内容依据上述公开规范整理，实际课题请按最新版本核对条目编号；agent 产出的建议需研究者自行复核。

