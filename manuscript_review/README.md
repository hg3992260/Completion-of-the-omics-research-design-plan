# 手稿缺陷审阅工作台

把本仓库原有的**引导式组学 / 统计 / 撰写**三套架构**换一个用法**：

> 原来是从零陪研究者把设想打磨成方案；
> 现在是**导入一份已成稿的手稿（PDF / Word），逐条对照这三套架构找出缺陷，
> 并把缺陷直接落回 Word** —— 原生批注 + 四色 Track Changes 修订。

程序目录：`manuscript_review/`，启动入口：`启动_手稿审阅.bat`。
**原有组学研究设计工作台（十阶段 / 统计 / SCI Shape 三个页签）一行未改**，两者共用同一份规范数据。

---

## 1. 它到底做了什么

```
手稿.pdf  ──►  PDF→DOCX 转换稿  ──┐
手稿.docx ──────────────────────┤
                                ▼
                  ① 解析结构：段落 + 段号锚点 + 章节映射
                                ▼
        ② 确定性核验（不需要 LLM）      ③ LLM 语义审阅
        可证据化的硬缺陷：              语义判断：
        「没写 ICC」「没给管电压」        「摘要缺成就组件」
        「没报告校准」「没有注册号」      「Discussion 只是复述 Results」
        「数据可向作者索取」              「结论强度超过证据」
                   └────────┬───────────┘
                            ▼
                  合并去重（同一条只报一次）
                            ▼
        ④ 审阅报告 (Markdown / HTML / CSV)
        ⑤ Word 落盘：每条缺陷 = 一条批注；可采纳的修改 = 四色修订
                            ▼
              手稿_审阅修订版.docx  ← 作者在 Word 里逐条处理
```

### 举例：一条缺陷在 Word 里的样子

挂在该段的**批注**（Word 审阅窗格中可直接回复/解决）：

```
【引导式组学｜■ 关键】CLEAR 16 · METRICS #6
规范条目：组学阶段 4 图像采集与质控
缺陷：CLEAR 16 / METRICS #6 要求登记全部采集与重建参数。主稿只写「门静脉期增强CT」，
      机型、管电压、管电流、层厚、重建算法与卷积核均未说明，第三方无法复现特征值。
证据：所有患者均行门静脉期增强CT检查。扫描参数未作统一规定，由各台设备按常规设置执行。
建议：补全机型、kVp、mAs、层厚、重建核与期相触发方式；多中心需说明参数一致性处理。
（来源：确定性核验｜条目 signal:acquisition_params）
```

同一处的**修订**（Word「审阅→所有标记」下可见差异）：

| 修改类型 | 颜色 | 附加格式 | 本程序用在哪 |
|---|---|---|---|
| 新增内容 | 绿 `00B050` | 下划线 | 缺失的报告项 → 追加「【补正·…】」占位段，作者填数 |
| 删除内容 | 红 `FF0000` | 删除线 | 明确写错需删除的片段 |
| 修改（替换） | 蓝 `0070C0` | 下划线 | 明确写错且能唯一定位 → `find/replace` |
| 移动 / 格式变更 | 橙 `ED7D31` | — | 预留（当前版本未自动产生） |

> **诚信底线**：程序**不替作者编造数据**。缺失的统计量、未做的 ICC、待补的伦理批号，
> 一律以「占位待补 + 明确报告位点」的形式插入，并在批注里写清该补什么。
> 需要重算才能定稿的条目（如校准曲线、DCA）**只出批注、不动正文**。

---

## 2. 三层架构从哪来（不新增第二套标准）

审阅条目**全部派生自仓库已有的权威数据**，因此与原有工作台永远同源：

| 层 | 数据源 | 条目数 | 规范依据 |
|---|---|---|---|
| 引导式组学 | `stages_data.STAGES` | 89 | 十阶段 · TRIPOD+AI / CLEAR / METRICS / IBSI |
| 统计 | `stat_data.STAGES` | 117 | 9 阶段 · SAP / 前提诊断 / 多重比较 / 报告规范 |
| 撰写 | `shape_data.SHAPE` | 109 | Glasman-Deal《Science Research Writing》七章通用模型 |
| **合计** | | **315** | |


### 2.2 自主落盘：跑一次审阅就自动把批注写进 Word

**这是默认行为，不是附加步骤。** 点一次「★ 一键审阅并自动落批注」（或命令行跑一次），
导入 → 核验 → 语义审阅 → **自动写 Word 批注** → 出报告，全程不需要再点落盘按钮。

左栏「自主落盘」下拉框决定写到什么程度：

| 档位 | 行为 | 输出 |
|---|---|---|
| `revise`（默认） | 每条发现写一条 Word 批注 **+** 缺失报告项用 Track Changes 绿色补写占位段 | 45 段、31 批注、16 修订 |
| `comment` | 只挂批注，**不增删任何正文**（结构还在调整时用） | 29 段、31 批注、0 修订 |
| `report` | 只出报告，**完全不碰 Word** | 仅 Markdown/HTML/CSV |

```bat
python -m manuscript_review.cli 手稿.docx                    :: 默认 revise，自动落盘
python -m manuscript_review.cli 手稿.docx --autonomy comment  :: 只挂批注
python -m manuscript_review.cli 手稿.docx --autonomy report   :: 只出报告
python -m manuscript_review.cli 手稿.docx --incremental       :: 增量：只写新发现
```

**增量 vs 重跑**：默认每次都是**完整重审**（清空"已入稿"记录后整体重写，结果可复现）；
加 `--incremental` 则只把本次**新报出**的发现写到已有修订稿上 ——
适合"先审确定性核验，再补一轮语义审阅"的分步用法。
项目里用 `applied_keys`（`来源|条目号|段号` 指纹）记录已入稿的发现，避免重复挂批注。

三层可分别勾选：取消某一层就整轮不跑该层（省时间，也便于只盯一层）。

### 2.3 并入「审稿批注版」：把发现做成线程回复

如果手上是**带审稿意见的批注版手稿**，可以让我们的发现直接**作为回复挂在对应审稿意见下面**，
在 Word 审阅窗格里呈嵌套树状，审稿人一眼能看到「就我这条意见，补充了什么」。
审稿人原有批注**一个字都不动**。

**操作**：左栏点「选择审稿批注版…」选定文件 → 再点「并入批注版（线程回复）」。

```bat
:: 命令行
python -m manuscript_review.cli 手稿.docx --merge-into 审稿批注版.docx

:: 先看目标文件有没有批注、有几条、谁写的
python -m manuscript_review.cli 审稿批注版.docx --annotated-info
```

**发现挂到哪条审稿意见下**，用可解释的规则打分（报告与日志都会写明依据）：

| 依据 | 分值 | 说明 |
|---|---|---|
| 同段落 | +3.0 | 最强证据；且 Word 对同段多条批注本来就会串成一条线程 |
| 相邻段落 | +1.2 | 隔 1–2 段 |
| **强主题词**命中 | +0.9/个 | ICC / 校准 / 层厚 / 主模型 / 分割 / binWidth … |
| 弱主题词命中 | +0.25/个（需≥2） | 「参数」「特征」「模型」这类泛词单独命中不算数 |
| 主题同类加成 | +0.5 | 仅当已有词命中时才加 |

匹配不上的转为**独立批注**写在原段落，信息不丢。默认阈值 0.8、一条审稿意见最多收 4 条回复。

> **踩过的坑，值得记一笔**：主题词必须分强弱。早先把「参数」当强词，结果
> 「伦理批号」被挂到了「扫描参数」那条意见下面（两者都含"参数"）——
> 这种误挂靠比不挂靠更误导作者。

### 2.4 实现上的两个硬约束（都踩过）

**① 必须用 OfficeCLI 的 `parentId`，不要自己插标记。**
`reviewer-reply-docx` 技能文档说「OfficeCLI 的 parentId 不会原生嵌套」——
那是 **1.0.143 的旧行为**。实测 1.0.153 已经修好：它会同时写
`commentsExtended.xml` 的 `<w15:commentEx w15:paraIdParent="…"/>`，
并自动把回复的 commentRange 标记包在父批注外面。所以技能里那个
`inject_replies.py` 手工插标记的步骤**不需要**，照搬反而多一处出错点。

**② 批注/回复必须在「补写段插入」之前写，否则线程必坏。**
插入补写段会改变段落序号：父批注在位移后落到了新段号，而回复还锚在旧段号，
两者分处不同段落 → OfficeCLI 无法嵌套 → Word 显示为平级。
所以落盘分三批：

| 批次 | 内容 | 段落数变化 |
|---|---|---|
| phase1 | `find/replace` 修订 + 修订补色 | 不变 |
| phase2 | 独立批注 + 线程回复（按原段号锚定，父子同段） | 不变 |
| phase3 | 补写「缺失报告项」段落（按原段号升序插入并补偿位移） | +N |

### 2.5 课题关联：手稿是课题的附件

导入时**自动**把这份手稿登记到工作台当前打开的设计项目下，
并**把课题背景带入语义审阅**（研究设想 + 各阶段定稿摘要）。

**为什么需要背景**：手稿缺陷有两类 ——
① 违反通用规范的（确定性核验能查）；
② **与课题自身意图不一致**的（例如课题预设了「外院外部验证 + 前瞻队列」，
手稿只报了单中心内部验证）。只有拿到课题背景，第②类才判得出来。

| 时机 | 动作 |
|---|---|
| 导入 | `ingest(design=...)` 把 `design_name / design_path / design_digest` 写进审阅项目，并登记为课题附件 |
| 全流程结束 | 用最终的缺陷数与产出文件**刷新**同一条附件记录（不会产生重复条目） |
| 语义审阅 | `design_digest` 作为「本手稿所属课题的背景」区块进入每批提示词；缓存键也带上它（换课题则重新审） |

课题 JSON 里新增 `manuscripts` 字段（旧项目加载得到 `[]`，向后兼容）：

```json
"manuscripts": [{
  "name": "sample_manuscript",
  "project_path": ".../manuscript_review/projects/sample_manuscript.json",
  "source": ".../sample_manuscript.docx",
  "out_docx": ".../sample_manuscript_审阅修订版.docx",
  "defects": 31, "key_defects": 16,
  "linked_at": "2026-10-05 12:30"
}]
```

左栏会显示关联状态（绿色=与当前课题一致，黄色=当前工作台已切到别的课题）。

#### 双向联动：切课题 ⇄ 切手稿

| 方向 | 触发 | 行为 |
|---|---|---|
| 课题 → 手稿 | 在工作台切换/打开课题 | 自动切到该课题**最近登记**的那份手稿审阅；该课题没有手稿则**清空**审阅视图（避免把上一个课题的手稿挂在本题下） |
| 手稿 → 课题 | 导入手稿 | 自动登记为当前课题的附件，并把课题背景快照进审阅项目 |

切换前会先把当前审阅项目落盘，所以来回切不会丢结论。绑定的审阅项目文件若被删掉，
会给出提示而不是崩 —— 内存里那份会被重新落盘（自愈）。

> **为什么"没有手稿就清空"**：不清空的话，切到课题 B 时左栏还挂着课题 A 的手稿，
> 用户很容易在错误的课题下继续改。宁可清空并提示，也不要留下误导性的旧状态。

> 关联发生在**导入那一刻的当前课题**；之后再切课题，联动会按各自绑定重新对齐。


其中 125 条可**确定性核验**（有对应的正则信号，见下节），其余交给 LLM 做语义判断。
派生逻辑集中在 `mr_review_layers.py::build_requirements()`，改一处即全链路同步。

---

## 3. 两层缺陷检测：为什么要分两层

纯靠 LLM 通读手稿找缺陷有三个硬伤：**不可复现、会漏、给不出证据**。
「手稿里有没有 ICC」这类检查完全可以确定性完成，而且比模型更可靠。
所以：

### 3.1 确定性核验层（`mr_signals.py`，41 个信号）

逐段正则检索，三条结论口径：

| verdict | 含义 | 生成的缺陷严重度 |
|---|---|---|
| `reported` | 手稿里找到了明确表述 | **不生成缺陷**（只作正向确认留痕） |
| `weak` | 提到了但信息不足（只写「增强CT」不给参数） | 主要 |
| `missing` | 完全找不到 | 关键 |

覆盖的信号举例：伦理批号、知情同意、注册号、数据重叠、样本量依据、事件数、
采集与重建参数、对比剂期相、勾画者资质、ICC/Dice、分割策略、重采样、binWidth、
归一化、IBSI、特征数量、软件版本、参数文件、特征稳定性、共线性、维度比、主模型、
嵌套交叉验证、调参、外部验证、置信区间、校准、DCA、增量价值、多重比较、前提诊断、
效应量、缺失数据、随机种子、数据与代码可及性、报告清单……

### 3.2 LLM 语义审阅层（`mr_reviewer.py`）

- **分层分批**：每批 ≤10 条规范条目，只喂该层相关的带段号正文（共 32 批）；
- **强制 JSON**：解析器支持围栏代码块、前后废话、括号配平扫描三种容错；
- **可缓存**：按「层 + 条目 + 正文 + 模型」哈希缓存，同一份手稿重跑不再花钱；
- **不重复报**：确定性层已报的信号会 `skip_signals` 跳过，避免同一条挂两条批注；
- **两层合并去重**：同一信号/条目 + 同段落只保留确定性层那条（它带可核验证据）。

---

## 4. 安装与运行

### 依赖

| 组件 | 用途 | 缺失时 |
|---|---|---|
| Python ≥ 3.8（推荐 `D:\python\envs\mar`，3.11 + PySide6） | 运行 | 无法启动 |
| `PySide6` | 桌面界面 | 只能用 `cli.py` |
| `python-docx` | DOCX 解析与转换稿生成 | 无法解析 |
| `PyMuPDF` (`fitz`) | PDF → DOCX | 不能导入 PDF |
| **OfficeCLI** `npm i -g officecli` | **Word 批注 + Track Changes 修订** | 只能出报告，不能落盘 |
| LLM 配置（`llm_config.json` 或环境凭据） | 语义审阅层 | 自动退化为只跑确定性核验 |

自检：

```bat
python -m manuscript_review.cli --toolchain     :: OfficeCLI / PyMuPDF 是否就绪
python -m manuscript_review.cli --layers-info   :: 三层条目统计
```

### 启动

桌面界面**就是原来的组学研究设计工作台**（`design_studio.py`），
手稿审阅是它的**第 5 个原生视图**，与「设计工作台 / Statistic / SCI Shape / 总览」
共用同一套 PyCt6 + ui_kit 原生组件与浅色主题：

```bat
启动_设计工作台.bat
:: 启动后点顶部流程条第 5 步「手稿审阅」
```

该页沿用原有页面模板：左栏 `StageRail` 三层架构步骤条、中栏 `Card` 缺陷明细、
右栏统计与 `TranscriptView` 执行流水；顶部流程条会显示 `缺陷 n·关键 m` 角标。
**原有的四个视图未做任何改动。**

#### 审阅进行中的状态显示

审阅（尤其语义审阅）是长任务，原先只有一行灰色小字，看着像没在干活。现在三处同时提示：

| 位置 | 表现 |
|---|---|
| 底部左下角 `BusyIndicator` | 橙色胶囊 + 均衡器律动 + 流光，显示当前步骤（如「正在做语义审阅（LLM）」）并**带秒级计时** |
| 左栏状态行 | `⏳ 正在做语义审阅（LLM）…　已 12 秒　（请稍候，不要关闭窗口）`，强调色加粗 |
| 页脚「继续」按钮 | 文案变为「审阅中…」并置灰，防止重复触发 |

完成后自动恢复为 `缺陷 31 条（关键 16）　·　引导式组学 25　统计 6　撰写 0` 这类事实摘要。

#### 右下角三个按钮

原来只有 `Space 继续 · Ctrl+S 保存 · Ctrl+E 导出` 这种**纯文字提示**（看不出能点、
也不知道该敲哪个键）。现在全部做成真按钮并带快捷键角标：

| 按钮 | 作用 |
|---|---|
| **继续 ␣**（强调色） | 按当前视图推进：手稿审阅页走「导入 → 核验 → 语义审阅 → 落盘 → 报告」，其余视图走工作台主流程；文案跟着阶段变（`① 导入` / `② 核验` / `③ 语义审阅` / `审阅中…`） |
| **保存 ⌃S** | 手稿审阅页保存审阅项目（含缺陷与落盘结果），其余视图保存设计项目 |
| **导出 ⌃E** | 弹菜单按当前视图给可用项：审阅页给「审阅报告 / 修订稿 Word / 打开修订稿 / 打开审阅报告」，其余给「Markdown / Word」 |

#### 解释器问题（启动「一闪就没」的根因）

本机 PATH 里的 `python` 是 **miniconda base 3.14.6，没有 PySide6**；而 PySide6
装在 `D:\python\envs\mar`（3.11）。所以：

| 启动方式 | 结果 |
|---|---|
| 双击 `启动_设计工作台.bat` | 正常（bat 里写死了 mar 解释器） |
| `python design_studio.py`（PATH 里的 base） | 只报 `ModuleNotFoundError: No module named 'PySide6'` 后立刻退出 → 表现为**窗口一闪就没** |

现在 `design_studio.py` 顶部加了**解释器自举**：导入 PySide6 前先探测
`D:\python\envs\mar` 等候选路径（以及 PATH 里其它 python），
找到带 PySide6 的就把自己重启过去（用 `PCLRADIOMICS_RELAUNCHED` 防循环）。
因此 `python design_studio.py` 与双击 bat 现在行为一致；
确实找不到可用解释器时，会打印一段带**具体命令**的提示并以退出码 2 结束，
不再是一句无从下手的 `ModuleNotFoundError`。

### 命令行（批处理 / 服务器）

```bat
:: 一键全流程：导入 → 三层审阅 → 报告 → Word 批注+修订
python -m manuscript_review.cli 手稿.pdf

:: 只跑确定性核验（不联网、不花钱，适合先看硬伤）
python -m manuscript_review.cli 手稿.docx --skip-llm

:: 只审写作层、最多 3 批（快速试跑）
python -m manuscript_review.cli 手稿.pdf --layers shape --max-batches 3

:: 只出批注，完全不碰正文
python -m manuscript_review.cli 手稿.docx --mode comment_only

:: 结果以 JSON 输出（便于管道）
python -m manuscript_review.cli 手稿.docx --skip-llm --json
```

### MCP 工具（保留原有 bridge，新增 6 个）

原有 14 个工具完全保留，`mcp_server.py` 新增：

| 工具 | 作用 |
|---|---|
| `manuscript_layers` | 列出三层审阅条目统计 |
| `manuscript_review` | **一条命令跑完**：导入手稿 → 三层对照 → 自主写 Word 批注 → 出报告。用 `autonomy` 选落盘档位（`revise`/`comment`/`report`），`merge_into` 走线程并入 |
| `manuscript_defects` | 查询缺陷清单，可按层 / 严重度过滤 |
| `manuscript_annotated_info` | 探测手稿是否带审稿批注（决定能否做线程回复并入） |
| `manuscript_apply` | 落回 Word：`merge_into` 给定审稿批注版时做成**线程回复** |
| `manuscript_report` | 生成 Markdown / HTML / CSV 报告 |
| `manuscript_projects` | 列出历史审阅项目 |
| `manuscript_toolchain` | OfficeCLI / PDF 依赖就绪情况 |

Agent 典型调用链（**一次调用即完成审阅 + 落盘**）：

```
# 独立批注：跑完即有带批注的 Word
manuscript_review(path="稿件.pdf", layers="omics,stat,shape", autonomy="revise")

# 并入审稿批注版：发现挂成线程回复
manuscript_annotated_info(path="审稿批注版.docx")     # 先确认有批注
manuscript_review(path="稿件.docx", skip_llm=True,
                  autonomy="comment", merge_into="审稿批注版.docx")

# 只读查询（不重复落盘）
manuscript_defects(layer="omics", severity="关键")
manuscript_report()
```

---

## 5. 模块结构

| 文件 | 职责 |
|---|---|
| `mr_review_layers.py` | 三层审阅条目（派生自 `stages_data` / `stat_data` / `shape_data`） |
| `mr_docx.py` | DOCX 结构解析：段落 + **段号锚点** + 章节映射 |
| `mr_pdf.py` | PDF → DOCX 转换（保版面顺序，弃噪声） |
| `mr_signals.py` | 确定性信号核验（41 个信号） |
| `mr_reviewer.py` | LLM 语义审阅：分层分批 + 缓存 + JSON 容错解析 |
| `mr_office.py` | OfficeCLI 封装（**全程参数列表，绝不经过 shell**） |
| `mr_word.py` | Word 落盘：批注 + 四色修订 + 原子批量 + 落盘后校验 |
| `mr_report.py` | 审阅报告（Markdown / HTML / CSV） |
| `mr_engine.py` | 审阅编排 + 项目存储 |
| `mr_thread.py` | 并入审稿批注版：读已有批注 / 匹配打分 / 线程校验 |
| `cli.py` | 命令行界面 |

桌面界面在 `design_studio.py` 的 `ManuscriptReviewPage`（第 5 个原生视图），
不是独立文件 —— 这样它天然继承工作台的原生组件、主题与流程条。

### 附带目录

| 目录 | 内容 |
|---|---|
| `examples/` | **纯合成**样例（`sample_manuscript.docx` 29 段含 16 处硬伤；`annotated_sample.docx` 3 条审稿意见）。生成脚本 `make_sample.py` / `make_annotated.py`。**不含任何真实患者数据或未发表手稿。** |
| `verify/` | 端到端验证脚本（18 个）+ 公共引导 `_bootstrap.py`。全部基于 `examples/` 的合成样例，可直接运行复现 README 第 8 节的验证结果。 |

验证脚本用法（从仓库根执行即可，`_bootstrap.py` 会自动定位仓库根与样例）：

```bat
python manuscript_review\verify\e2e_signals_word.py   :: 核验 → Word 批注 + 四色修订
python manuscript_review\verify\e2e_pdf.py            :: PDF → DOCX → 审阅落盘
python manuscript_review\verify\e2e_mcp.py            :: MCP 工具逐个调用
python manuscript_review\verify\test_auto.py          :: 自主落盘三档 + 增量去重
python manuscript_review\verify\test_duo_link.py      :: 课题 ⇄ 手稿 双向联动
```

脚本产物统一写到仓库根的 `_verify_out/`（已 gitignore），不污染源码目录。

---

## 6. 关键实现要点（都是实测踩过的坑）

1. **段号即锚点**：`mr_docx` 解析出的段号就是 OfficeCLI 的 `/body/p[N]`。
   正文改写走 `find/replace`（**不改变段落数**），新增段落**按段号倒序**插入，
   所以一次解析、一次算地址，后续所有回写都安全。
2. **绝不经过 shell**：批量操作写成 UTF-8 JSON 文件用 `--input` 传入。
   早先用命令行参数传中文会被 Windows 代码页变成乱码。
3. **原子性**：一次审阅的全部写操作放进**一个 OfficeCLI batch**，
   任一条失败则整批回滚，绝不产出「改了一半」的稿件。
4. **`find/replace` 生成的修订不带颜色**：所以分两批 —— 先改内容，
   再按段落序号给修订 run 补色（`/body/p[@paraId=X]/r[N]` 可直接 set）。
5. **校验前必须 flush**：OfficeCLI 有常驻进程，改的是内存文档，
   不 `save`/`close` 就读磁盘会读到旧内容。
6. **正则边界不能用 `\b`**：`<w:commentRangeStart/>` 里 `t` 与 `>` 之间不是词边界，
   用 `\b` 会把自闭合标签漏掉，导致校验误判失败。统一用 `[\s/>]` 前瞻。
7. **PDF 行分组不要自己重做**：按 `round(y0/3)` 给 span 分桶会把同一视觉行的
   「加粗字」（y0 略高）与「常规字」拆开，按 x 排序后字符交错 ——
   标题会被抽成「强组细预测」。直接用 PyMuPDF 的 blocks→lines 分组。
8. **双栏判定必须保守**：把单栏稿误判成双栏会打乱段落顺序，代价远大于漏判。
   现在要求「左右栏都有 ≥25% 的行」且「左栏起点靠边距」且「右栏起点显著右移」
   且「中缝确实空着」四条同时满足。
9. **批注锚点要分散**：一份手稿常一次报出十几条「某参数未报告」，
   全挂到方法章第一段会让作者在 Word 里看到十几条批注叠在一处。
   同章节内按正文段轮流分配，每段最多 3 条。
10. **Markdown 记号要清洗**：模型爱在 `suggestion` 里写 `**加粗**`，
    直接塞进 Word 会变成字面星号。统一过 `mr_word.plain()`。
11. **`StageRail` 的 id 必须是整数**（这个坑很贵，单独说明）：
    原组件在 `paintEvent` 里写的是 `f"{st['id']:02d}"`，只接受整数。
    原有三页的数据 id 恰好都是 `1..10`，所以一直没暴露；
    手稿审阅页最初传了字符串 id（`omics`/`stat`/`shape`），
    `ValueError` 在 `paintEvent` 内抛出 —— 等于在 **Qt 回调里抛异常**，
    结果是整个进程 `0xC000041D` 访问冲突硬崩，**连 Python 报错都看不到**。
    现在 `paintEvent` 已改为按类型分支（整数仍 `{:02d}`，字符串截断显示），
    但**新增任何 rail 数据时请优先用整数 id**。
    排查这类崩溃的可靠办法：`python -X faulthandler`，
    再用「只改一个变量」的 A/B 复现脚本定位（本次即靠 `id` int/str 对照锁定）。

---

## 7. 已知限制（务必向作者交代）

1. **PDF 转换必然有损**：公式、复杂表格、图注可能失真。
   审阅与修订都作用在**转换稿**上，最终定稿需把修订内容合并回原始排版稿。
   扫描件（无文字层）会明确报错，需先 OCR。
2. **程序不替作者造数据**：标为「缺失」的补正段是占位待补文字
   （形如「请补充具体数值/来源后删除本标注」），不是可直接投稿的内容。
3. **需要重算才能定稿的条目只出批注**：校准曲线、DCA、ICC 这类必须真做实验/重跑统计，
   程序不会伪造。
4. **LLM 判据不是金标准**：语义审阅可能误报或漏报；
   确定性层的结论可复现、可追责，语义层的结论请作者自行复核。
   每条批注都标了来源（确定性核验 / 语义审阅）便于区分。
5. **修订颜色在 WPS 下的渲染可能略有差异**，交付前建议用目标软件确认。
6. `officecli` 版本建议 ≥ 1.0.150（开发验证于 1.0.153）。

---

## 8. 验证记录

样例手稿（`manuscript_review/examples/sample_manuscript.docx`，29 段 / 1280 字，含 16 处硬伤）实测：

| 场景 | 结果 |
|---|---|
| DOCX 解析 | 29 段、8 个章节 100% 正确映射 |
| 确定性核验 | 41 项信号：缺失 16 · 不完整 15 · 已报告 10 |
| Word 落盘（dual） | 31 条批注 · 16 处绿色插入；标记配平 31/31/31，校验通过 |
| Word 落盘（find/replace） | 红 `FF0000` 删除线 2 + 蓝 `0070C0` 下划线 2；校验通过 |
| PDF → DOCX | 3 页 → 31 段，章节结构与原稿逐段一致 |
| 报告 | Markdown 27.9 KB + HTML + CSV |
| MCP 工具 | 20 个工具注册成功（原 14 + 新 6），逐个调用通过 |
| 原生 GUI（`design_studio.py` 第 5 视图） | 流程条 5 步与「缺陷 31·关键 16」角标正常；三层 rail 切换、章节映射、缺陷明细、统计与流水渲染正确；原有四页回归无异常 |
| **GUI 自主落盘** | 只点一次「★ 一键审阅并自动落批注」→ 21 独立批注 + 10 线程回复 + 16 修订 + 报告，全程无需再点落盘 |
| 自主档位（CLI/MCP/引擎三处一致） | `revise` 31 批注+16 修订 · `comment` 31 批注+0 修订 · `report` 0 批注+不产出 Word |
| 增量去重 | 同一项目重跑：`没有新增发现需要落盘（已入稿 31 条）` |
| 课题关联 | 导入后自动登记为课题附件（1 条）；重复登记原地更新不重复；旧项目 JSON 兼容（`manuscripts=[]`） |
| **双向联动** | 切到课题 A → 自动载入 A 绑定的手稿；切到无手稿的课题 B → 审阅视图清空；切回 A → 自动切回原手稿（`与导入时一致: True`）；往返多轮稳定不崩 |
| 页脚按钮视图感知 | 工作台/统计/Shape/总览显示工作台主流程文案；手稿审阅页显示「导入并开始 / ② 跑核验 / ③ 写批注 / ④ 出报告」，各有 tooltip |
| 课题背景带入 | `design_digest` 267 字；渲染后的提示词确实含「本手稿所属课题的背景」及课题里的「外部验证」「240 例」 |
| 两处导入入口 | 左栏「① 导入手稿」与页脚「导入并开始」调用**同一个 `do_import()`**；后者带自适应文案与 tooltip |
| 并入审稿批注版（`comment_only`） | 独立批注 21 + 线程回复 10；校验 `根 24 · 回复 10 · 嵌套正常 10 · 异常 0` |
| 并入审稿批注版（`dual`，含段号位移） | 独立批注 21 + 线程回复 10 + 补写 16 段（29→45 段）；校验 `嵌套正常 10 · 异常 0` |
| **Word COM 权威校验** | `Comment.Ancestor` 确认回复的父级正确指向审稿批注；作者分布 `手稿审阅 21 / 审阅补充 10 / 审稿人1 2 / 审稿人2 1` |
| 审稿人原有批注 | 并入前后逐条比对：**全部保留且文本未变** |
| LLM 语义审阅 | JSON 解析、`req_id` 匹配、缓存命中、批次进度回调均正常 |

复现：

```bat
:: 命令行全链路
python -m manuscript_review.cli manuscript_review\examples\sample_manuscript.docx --skip-llm --json
:: 原生界面（第 5 视图）同步渲染验证
python manuscript_review\verify\native_sync_verify.py
:: 其余分支
python manuscript_review\verify\e2e_signals_word.py
python manuscript_review\verify\e2e_replace.py
python manuscript_review\verify\e2e_pdf.py
python manuscript_review\verify\e2e_mcp.py
python manuscript_review\verify\repro_id.py str        :: StageRail 字符串 id 崩溃复现/回归
```

### 8.1 原生界面接线位置（便于日后维护）

`design_studio.py` 里与手稿审阅相关的改动只有这些，都很集中：

| 位置 | 内容 |
|---|---|
| `ManuscriptWorker` / `ManuscriptReviewPage` | 页面与后台线程（在 `ShapeScopePage` 之后） |
| `StageRail.paintEvent` | 编号渲染改为按 id 类型分支（字符串 id 防崩） |
| `_build_footer` / `footer_continue` / `footer_save` / `footer_export` | 右下角三个按钮（替换原文字提示） |
| `_toast` / `save_project` | 提示改走状态栏（原提示标签已不存在） |
| `StudioWindow.__init__` | `self.mr_project = None`；`body_stack` 增第 5 页 |
| `_build_mr_page` / `show_mr` | 建页与切页 |
| `_build_flow` / `goto_step` | 流程条第 5 步 |
| `_sync_flow` | 第 5 步角标 |
| `_apply_responsive` | 页脚按钮宽度随窗口宽度调整 |
| 两处主题/刷新守卫 | `idx == 4` 时刷新本页 |
