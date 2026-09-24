# SCI 论文结构写作手册（编纂版）

> **底本**：Glasman-Deal, *Science Research Writing for Non-Native Speakers of English*, 2nd ed.（全书 385 页）
> **编纂来源**：`docs/_extract/` 下 8 份已完成的中文方法学提取（Unit 1–8），仅依据这 8 份总结编纂；不引入书中没有的规则，凡原总结标注「原文未明确」者，本手册一并标注。
> **页码口径（重要）**：本手册**统一使用书内印刷页码**（原书页眉页脚印出的页码，形如 `w 58` / `58 v`）。
> **换算规则：书内页 = PDF 页 − 29**。首次出现处必要时在括号内给出 PDF 页，如 `书 p17（PDF 46）`。
> **已验证的换算锚点**（以印张页眉为准，非以子代理自述为准）：PDF 46→书 17、PDF 87→书 58、PDF 117→书 88、PDF 144→书 115、PDF 165→书 136、PDF 184→书 155、PDF 214→书 185、PDF 219→书 190、PDF 237→书 208、PDF 271→书 242、PDF 274→书 245、PDF 286→书 257、PDF 315→书 286、PDF 333→书 304、PDF 339→书 310、PDF 344→书 315、PDF 359→书 330。
> **前言部分例外**：原书前言用罗马数字单独编页（PDF 14 = 书 xiii，PDF 15 = xiv，PDF 18 = xvii），**不适用 −29**。
> **English 原词一律原样保留**（含原书拼写，如 `calcinated`、`decribed`），以便直接做模板。

---

## 如何使用本手册

| 你在做什么 | 用哪一部分 |
|---|---|
| 动笔前搞清"这本书的方法论到底是什么" | **Part 0**（叙事骨架/叙事包裹、reverse-engineering 四步法、磁南、章节对照表） |
| 写某一章（Title/Abstract/…/Conclusion） | **Part 1** 对应小节：功能定位 → 通用模型 → 内容边界 → 时态语态 → 词块库 → 检查清单 |
| 语言层面的疑难（时态、情态、冠词、介词、指代、-ing、信号词…） | **Part 2**（跨章节合并去重版，每个主题注明原出现单元，章内只写一份） |
| 全稿定稿前的统一自检 | **Part 3**（4 层可勾选清单） |
| 写自动检查脚本、定阈值 | **Part 4**（全部量化基准表 + 不得外推的说明） |
| 遇到"原书到底怎么说的/页码对不上/某单元缺东西" | **Part 5**（待核实与原文矛盾项） |

**三条使用纪律**

1. **先规划，后造句**：`Step away from the keyboard and invest in time to plan the order of each section before you start typing whole sentences`（书 p315）。
2. **一切以目标文章（target articles）为最终判据**：本手册给的是通用模型（菜单），每一项细节都必须回目标期刊近期成功论文核对（书 pp.7–8、80、142、319）。
3. **组织优先**：`Good organisation and good writing can compensate for language errors, but error-free language does not compensate for poor organisation or poor writing.`（书 p314）

---

## 目录

- **Part 0 方法论总纲**（0.1 两个支柱｜0.2 reverse-engineering 四步法｜0.3 组织优先的单向补偿原则｜0.4 magnetic south｜0.5 写作/阅读顺序 ≠ IMRaD 印刷顺序｜0.6 Unit ↔ SCI 章节对照表｜0.7 全局量化坐标速查）
- **Part 1 逐章节写作规范**（1.1 Title｜1.2 Abstract｜1.3 Introduction｜1.4 Methods｜1.5 Results｜1.6 Discussion｜1.7 Conclusion；每章固定 6 项子结构，不省略）
- **Part 2 跨章节语言层**（2.1 verb tense 总表｜2.2 certainty continuum｜2.3 modal verbs 六组分级｜2.4 ownership/贡献归属｜2.5 冠词 a/an/Ø/the｜2.6 介词｜2.7 -ing 歧义｜2.8 指代 reference｜2.9 adverb location｜2.10 弱动词与词汇准确性｜2.11 signalling connectors｜2.12 段落与句子组织｜2.13 评价性语言与"裸数字"）
- **Part 3 全稿统一检查清单**（3.1 结构/叙事层｜3.2 句子层｜3.3 语法词汇层｜3.4 全局收口层）
- **Part 4 机检规则候选：量化基准总表**（4.1 篇幅与长度｜4.2 计数、语料规模与组件数｜4.3 无阈值的"测量型"检查｜4.4 语料与练习规模｜4.5 不得外推的说明）
- **Part 5 待核实与原文矛盾项**（5.1 页码口径裁决｜5.2 原书自身编号不一致｜5.3 单元级缺口｜5.4 跨单元内容张力｜5.5 本手册的编辑判断）

---

# Part 0 方法论总纲

## 0.1 两个支柱：narrative scaffold（叙事骨架）与 narrative wrap（叙事包裹）

| 支柱 | 原文表述与出处 | 含义 |
|---|---|---|
| **Planning = 叙事骨架** | 规划阶段用 reverse engineering 为目标文本抽取"句子的功能序列"，即骨架（书 p302：`Look at how the paragraphs and sentences start and how they link together. You will start to see the scaffold that holds the information`；书 p182 同义） | 骨架 = 组件清单 + 顺序 + 各组件占篇幅的比例；它是**信息容器的形状**，与内容无关（模型里不得出现 content words） |
| **Writing = 叙事包裹** | `The key to a successful Discussion section is a forward-moving, well-organised narrative wrap … that leads the reader patiently, logically and explicitly from the results to the conclusions.`（书 p191）；`the more the narrative 'wrap' is reduced, the less coherent that data or information becomes.`（书 p289） | 包裹 = 用衔接、评价、信号词把骨架里的信息"串成一条向前的路"；数据本身没有功能（书 p314：`Data and information alone have no intrinsic or obvious function for the reader without a narrative.`） |

**核心主张（全书写作目标，逐字）**

- `The aim of writing is not to make it possible for the reader to understand what you have written. The aim is to make it impossible for the reader not to understand.`（书 p314；语言技能版见书 p114）
- 摘要加码版：`your aim is not to make it possible for the reader to understand the Abstract; it is to make it impossible for the reader not to understand the Abstract AND identify your contribution.`（书 p266）

**由此推出的三条操作律**

1. `Knowing WHAT to write is not the same as knowing HOW to write it.`（书 p314）——组件清单解决 WHAT，叙事包裹解决 HOW。
2. `The fact that you and your colleagues understand what you have written makes it harder for you to see potential ambiguities.`（书 p314）——熟人是盲区来源；作者永远看得懂自己写的东西。
3. `The space between a full stop and the next capital letter is a dangerous space for you and for your reader.`（书 p316）——句间空隙必须用 §2.11 的衔接手段封住。

## 0.2 reverse-engineering 四步法（把"阅读"变成"建模"）

| 步 | 动作 | 原文依据 | 可执行要求 |
|---|---|---|---|
| **第 1 步：建句子功能模型** | 对目标文章中**至少两篇**同类文本的每一句，写出"作者在这一句**做什么**（function）"，**不是**"这句话说了什么（content）" | 书 pp.4–5、77、142、193–194 | 描述必须简短；识别功能的抓手是**主动词的时态**（`What is that verb tense normally used for? Is the verb in the same tense as in the previous sentence? If not, why has the writer changed the tense?`，书 pp.4–5、77）；**模型不许含内容词**（`don't include content words such as polymer or you won't be able to use the model to generate Introductions for your own research articles.`，书 p5）；最后把自建清单与通用模型**整合**（书 pp.154、193–194） |
| **第 2 步：挖词块（word chunks）** | 在目标文章与自己文本中划出各功能对应的英文词块与句型，与书中的清单对照、扩充 | 书 p45、99、169、221、290 | 清单来源：`analysis of over 2,500 published research articles in different disciplines`，只收录高频因而"normal and acceptable"的用法（书 p45）；**必须**用目标文章持续扩充（`Add to the list from your target article Abstracts.`，书 p290） |
| **第 3 步：定语法/时态与句法技能** | 用目标文章核定时态、语态、冠词、介词、指代、句长/段长、信号词用法 | 书 pp.53、113–126、319–328 | 关键纪律：时态不是语法命令而是意义表态（书 p53：`The decision of which of these three tenses to use is rarely determined by the rules of grammar; in most cases the decision is made on the basis of meaning.`）；`Tense changes are always meaningful… so don't choose or change tense randomly.`（书 p55） |
| **第 4 步：持续用领域阅读更新模型** | 把建模变成终身的"为写作而读"的习惯工具，随领域与出版方式变化自动更新 | 书 p302 | 原句：`You will start to see the scaffold that holds the information, and this will develop into a lifelong reading-for-writing tool that updates automatically every time you read a review article, a research paper, a conference abstract or any other text.`；原书末端复述：`Whatever type of document you are planning to write, use the strategy in this book to reverse engineer some recently-published examples in order to generate a robust, reliable model.`（书 p330） |

**为什么必须逆向工程而不是背规则**：原书反对规定性建议（Results 一章说得最直白，书 p142：成功发表的论文"并不总是、甚至常常不"遵守 Results 不得解释、只能用过去时等规条）；规条会随读者阅读方式（尤其中文检索与网络阅读）快速过时，而描述性方法可自行更新（书 pp.142–143）。

**两条配套动作**

- 搜索引擎自检（标题）：`Before you submit your article, type your title and keyword list into a search engine and check which research articles appear. Are they aimed at the same readership as yours? Is that your target audience?`（书 p301）
- 术语自检（正文）：把术语加/不加引号分别丢进 Google Scholar 对比，确认它准确且当前仍在使用（书 pp.326–327）。

## 0.3 组织优先于语言的**单向补偿**原则

> `Good organisation and good writing can compensate for language errors, but error-free language does not compensate for poor organisation or poor writing.`（书 p314）

- **方向是单向的**：好组织能"补"语言错误；语言无错**不能**"补"组织差。所以自检的预算应优先投在 Part 3 的 3.1（结构与叙事）层。
- 推论：语法层面的隐形错误（冠词、-ing、副词位置、指代）虽然危险，但其**危害等级低于**段落功能混乱、数据无叙事这类组织问题（书 pp.314、329）。
- 原文给出的时间收益：`Effective, patient planning will increase both the speed and the quality of your writing.`（书 p315）；`getting lost in the middle of a paragraph or subsection wastes time and may result in a muddled, incoherent text.`（书 p315）

## 0.4 magnetic south（磁南 = 终点主张）

> `Everything in the text, whether it is a research article, conference abstract, thesis or other text type, should be consistent with and lead towards the destination point — the 'magnetic south'.`（书 p314）

- **含义**：全文（含标题）只有一个终点；所有句子、段落、图形都必须与它一致、并向它推进。
- **写作前先定磁南**：`Stepping back` 明确研究的主要价值/贡献属四类中的哪一类（书 p191）：
  1. 与他人结果相同/相似但用了更好或更新的方法 → 主要贡献是**方法**；
  2. 得到比别人更好（如更精确）的结果 → 主要贡献是**结果本身**；
  3. game-changer（开辟新方向/推翻既有工作）→ 主要贡献是对**文献/研究界的影响**；
  4. 发现或创造了新的、延伸的应用 → 主要贡献是对**产业/现实世界的影响**。
- **磁南的显性化三件套**（书 p315）：achievement（做了什么）／contribution（对知识、研究、现实世界的增量）／impact（后果）；`there should be an explicit and consistent take-home message about the value of the study.` 三者可以重叠、可以缺失，但**不允许沉默**。
- **标出方向而不是只报数据**：`Consider the magnetic south, i.e. where your text is going, and show the reader the direction of travel by commenting on data and information rather than just stating it.`（书 p316）
- **磁南要复核**：拿到结果后回看 Introduction 的 aim 是否与结果相符（书 p157：`Review the Introduction after you have obtained your results`）；标题承诺必须在正文（尤其 Conclusion）兑现（书 p310）。

## 0.5 论文各部分的阅读/写作顺序 ≠ IMRaD 印刷顺序

**印刷顺序（Fig. 1.1 的"对称形状"，书 p2 / p140 / p244 / 书 p265 同）**

`TITLE → ABSTRACT → INTRODUCTION → METHODS → RESULTS → CONCLUSION* → DISCUSSION`
（脚注：部分期刊称 CONCLUSION、部分称 CONCLUSIONS，`this does not seem to reflect the number of conclusions that are drawn`——命名不反映结论条数。）

> 注意：**Conclusion 在印刷上位于 Discussion 之前（或并入 Discussion 末 1–2 段）**，这正是全书把 Results / Discussion / Conclusion 分开训练的原因（书 pp.141、191）。

**读者的真实阅读顺序（决定各节必须"自足"）**

| # | 事实 | 出处 |
|---|---|---|
| 1 | 研究者读一篇论文通常**少于 30 分钟** | 书 p191 |
| 2 | 读者常从 Title/Abstract **直接跳到 Results**，绕过 Introduction 和/或 Methods（information-surfing approach） | 书 p75、书 p145 |
| 3 | 许多读者**只读 Title、Abstract、Discussion/Conclusion**，故这三者必须能作为独立自足的交流单元 | 书 p197、书 p159 |
| 4 | 读者可能像读侦探小说先翻最后一页一样，**从 Conclusion 起读**，甚至从 Abstract 或标题直接跳到 Conclusion | 书 p260 |
| 5 | 医学中 `treatment decisions are sometimes made on the basis of the Abstract alone` | 书 p265 |
| 6 | 论文量 >300 万篇/年，读者在标题与摘要间滚动竞争注意力 | 书 p265、书 p75 |

**写作顺序（不是印刷顺序）**

1. **先定磁南与 value 三件套**（书 p315）。
2. **规划各节信息顺序**，再造句（书 p315）。
3. **摘要通常在正文写完后创建**：`The Abstract is normally created after the rest of the writing is finished.` 理由：正文改动会使已写摘要不一致；摘要内容/风格/长度取决于投稿目标期刊（可能后期才定）；（书 pp.267–268）**`The Abstract derives from the paper, not the other way around.`**
4. **结果出来后回改 Introduction 的 aim**（书 p157）。
5. **定稿前**用 Part 3 清单 + Part 4 脚本过一遍，并清口头禅（书 pp.329–330）。

## 0.6 Unit ↔ SCI 章节对照表（含每章通用模型所在书页）

| Unit | 全书覆盖（书内页） | 对应 SCI 章节 | 通用模型（组件数与来源句数） | 模型所在书页 | 词块库 | 语言技能 |
|---|---|---|---|---|---|---|
| Unit 1 | pp.1–72（正文 pp.2–71） | Introduction | **GENERIC INTRODUCTION MODEL：4 个 basic components**（由 11 句功能描述 streamline 而来） | **书 p17**（PDF 46） | 书 pp.45–52 | 书 pp.53–68 |
| Unit 2 | pp.73–138 | Methods | **A METHODS MODEL：6 个组件**（由 9 句功能分析精简；另加"图形内容"一项） | **书 p88**（PDF 117） | 书 pp.99–112 | 书 pp.113–126 |
| Unit 3 | pp.139–188 | Results | **GENERIC RESULTS MODEL：4 个段落组 / 11 个组件条目**（示例 12 句） | **书 p155**（PDF 184） | 书 pp.169–182 | 书 pp.183–186（certainty continuum） |
| Unit 4 | pp.189–242 | Discussion | **GENERIC DISCUSSION MODEL：9 个组件**（示例 10 句） | **书 p208**（PDF 237） | 书 pp.221–228 | 书 pp.229–241（modal verbs） |
| Unit 5 | pp.243–262 | Conclusion | **GENERIC CONCLUSIONS MODEL：11 个组件**（6 篇样例） | **书 p257**（PDF 286） | **无独立词块表**，11 个组件全部交叉引用 Units 1–4（书 p258） | 书 pp.259–262 |
| Unit 6 | pp.263–298 | Abstract | **GENERIC ABSTRACT MODEL：3 个区块 × 3 = 9 个组件**（6 个组件标 `+ J`，共 7 处标记） | **书 p286**（PDF 315） | 书 pp.290–296 | 书 pp.266–267、286–289 |
| Unit 7 | pp.299–312 | Title | 无模型框；**检查点 7.1–7.6**（原文自称 "7 points"，实存 6 步，见 Part 5.2） | 书 pp.304–310（PDF 333–339） | 标题结构模式 + 关键词列表对照（书 pp.306–309） | 书 p303（句标题时态）、书 p310（情态动词） |
| Unit 8 | pp.313–330 | 全稿 Checklist & Tips | 无模型；**4 层清单**（8.1 组织 / 8.2 句子 / 8.3 语法词汇 / 8.4 全局） | 书 pp.315–330（PDF 344–359） | 无词块表（引用前 7 单元） | 书 pp.321–328 |

**模型页的交叉引证（原书自身也这样做）**：Unit 7 用 Conclusion 核验标题预期（书 p310）；Unit 4 在建模时**复述** Unit 1 的通用 Introduction 模型（书 p192）；Unit 6 的 6.5 检查项要求与"generic Abstract model on page 286"对位（书 p297）；Unit 8 末尾要求回到 reverse engineering（书 p330）。

## 0.7 全局量化坐标速查（详见 Part 4）

| 对象 | 数值（忠实原文） | 书页 |
|---|---|---|
| 平均句长（STEMM 研究论文） | 约 **23** 词 | p58 |
| 平均句长（多数期刊） | **20–26** 词 | pp.318–319 |
| 平均句长（18 篇范文摘要） | **22** 词 | p267 |
| 句子首读理解率 | <20 词 → 90%；>40 词 → 10% | p58 |
| 平均段长 | **150–170** 词（>230 或 <80 词者不常见） | p66、p317 |
| Abstract 长度 | **80–250** 词，单段 | p267 |
| Conclusion 长度 | **100–200** 词、1–2 个短段（Option 4 例外） | p245 |
| Title 平均长度 | 约 **12** 词（"many journals"） | p304 |

---

# Part 1 逐章节写作规范

> **每章固定 6 项子结构，不得省略**：A 功能定位（原文观点，一句式）→ B 通用模型（逐条组件，英文原词 + 中文，标注组件数与书页）→ C 内容边界（必写/禁写/与邻章分工）→ D 时态与语态规则（逐组件表格）→ E 词块库（按功能分类，英文原短语 + 中文说明）→ F 该章检查清单（可勾选）。
> **去重说明**：凡语言技能已在 **Part 2** 合并成一份者（时态、情态、冠词、介词、-ing、指代、副词、信号词、弱动词），本章只在 D/E 中给出**组件级**规则与交叉引用，不重复完整词表。

## 1.1 Title（标题）

### A. 功能定位

标题是**被阅读最多的文本单元**（`many more people will read the title than will ever read any other part of the paper`，书 p301），因此必须让滚动的读者一眼看出**研究的产出与价值**，而不是研究对象或研究活动（书 pp.301–302）。

### B. 通用模型：无模型框，改为 **6 个检查点**（原文自称 "7 points"，见 Part 5.2）

| # | 组件（英文原词 + 中文） | 打开做什么 | 书页 |
|---|---|---|---|
| 0 | **前置：REVERSE ENGINEER CURRENT TITLES**（逆向拆解目标期刊/同类主题近期标题） | 原文策略原句：`the best strategy is to begin by reverse engineering current examples of titles in the journal you wish to publish in and/or titles of research articles that deal with similar subject matter.` | p303 |
| 7.1 | **CHECK AVERAGE LENGTH**（核对平均长度） | 统计目标期刊同类标题词数；`In many journals, for example, the average number of words is around 12, but as always, averages hide acceptable variation.` | p304 |
| 7.2 | **USING ACRONYMS**（缩写取舍） | `the decision to use an acronym in the title depends on correctly gauging the level of knowledge shared by both current and future readers.` | p305 |
| 7.3 | **COMPARE THE TITLE KEYWORDS TO THE KEYWORD LIST**（关键词列表与标题对照） | `Keywords are marketing tools`；关键词是标题的 `valuable complement`，故 `creating one which simply repeats the keywords in the title is not a productive strategy.` | p306 |
| 7.4 | **CHECK THE GRAMMAR OF THE TITLE**（语法检查） | 复合名词链、介词过载、歧义；`the title must make sense to the reader` | pp.307–308 |
| 7.5 | **MAP AND MODEL THE STRUCTURAL CONTENT OF THE TITLES IN TARGET ARTICLES**（结构建模） | 7 个计数维度：A/An 开头？冒号？含方法？含目的/应用？含 happy words？含缩写？面向受限微社区？ | p309 |
| 7.6 | **CHECK THAT EXPECTATIONS THAT THE TITLE SUGGESTS ARE FULFILLED IN THE PAPER**（承诺兑现） | `The expectations set up by the title must be met in the paper itself.`；`it should not overstate or exaggerate the achievement of the study.` | p310 |

**7.5 归纳出的标题结构模式（可直接套用）**

| 模式 | 特征 | 英文原题例（书页） |
|---|---|---|
| method / technique-based | 含 `using …` / `of … technique` / `study of` / `modeling` | `3D reconstruction of SOFC anodes using a focused ion beam lift-out technique`（p309）；`Mathematical modeling of the circulation in the liver lobule`（p312） |
| purpose / application-based | `for + 目标` / `to + 动词` | `A random phased array device for delivery of high intensity focused ultrasound`（p309）；`A brain controlled wheelchair to navigate in familiar environments`（p310） |
| tool / system / new-offer | `A/An + 新物` 开头 | `A new procedure for analyzing the nucleation kinetics of freezing in computer simulation`（p310） |
| colon：大主题 : 焦点/贡献 | 冒号前为大领域，后为本文焦点 | `Life cycle inherent toxicity: a novel LCA-based algorithm for evaluating chemical synthesis pathways`（p309） |
| colon：新术语 : 描述/定义 | 冒号后是术语定义 | `GridSpice: a distributed simulation platform for the smart grid`（p309）；`LungGENS: a web-based tool for mapping single-cell gene expression in the developing lung`（p302） |
| sentence title（句子标题） | 有主语+动词（+宾语），**Present Simple** | `Gamma-range synchronization of fast-spiking interneurons enhances detection of tactile stimuli.`（p303） |
| topic-only（纯主题名词短语） | 无产出承诺，风险接近 working title | `Unsteady flows in pipes with finite curvature`（p312） |
| happy words 价值信号 | cost-effective / rapid / reliable / robust / novel / efficient / new | `Cost-effective multimode polymer waveguides for high-speed on-board optical interconnects`（p309） |

### C. 内容边界

**必须写**

1. **研究产出（the product）**，而不是研究活动或研究对象：`the product — and therefore the value — of the study is unlikely to be the investigation itself but rather the outcome of that investigation.`（书 p302）
2. 让所有目标读者（含未来读者）都能判断文章内容与贡献的表述（书 p301、p305）。
3. 与关键词列表**互补**的关键词分布（书 p306）。

**不得写 / 高风险**

1. **不要直接沿用 working title**：它只反映研究领域或研究活动。反例 `Unsteady flow in pipe networks` → 正例 `A hydraulic analysis of unsteady flow in pipe networks`；`Mapping single-cell gene expression in the lung`（只描述活动，读者无法判断文章类型）（书 p302）。
2. **不要为缩短标题而滥用缩写**：读者可能 `simply find the use of the acronym in the title off-putting and scroll down to the next article.`（书 p305）
3. **关键词列表不得照抄标题关键词**（书 p306）。
4. **不得名词堆叠/介词过载**：`may overload the title with nouns`，`This tends to scatter the key message, as readers cannot decide where the central focus lies.`（书 p306）
5. **不得夸大**：标题建立的所有预期必须在正文兑现（书 p310）。
6. **句子标题有条件**：`used when the findings are strong`；`Sentence titles … are acceptable in some journals but they are not common — as always, check your target journal.`（书 p303）。为出版速度，编辑有时接受结论尚未完全确立的句子标题（如 `Mechanically modulated cartilage growth may regulate joint surface morphogenesis.`）。
7. **大小写、问句标题、动名词 vs 名词化的优劣**：**原文未明确**（书 p299 脚注仅说明书中标题大小写已统一化处理；问句标题在 Unit 7 范围内未提及）——见 Part 5.3。

**与相邻章节的分工**

- 与 Abstract：标题承诺 → 摘要兑现（两处都属"独立自足单元"）。
- 与 Conclusion：7.6 的验收方法就是**用标题预测内容，再去核对 Conclusion**：`Look at the titles of your target research articles and predict what you expect to understand or gain from the article. Then check the Conclusion. How correct was your prediction?`（书 p310）
- 与 keyword list：把次要条目**分流到关键词列表**以给标题减负（书 p306、p307）。

### D. 时态与语态规则（逐组件）

| 组件 | 时态/语态 | 依据（书页） |
|---|---|---|
| 名词短语标题（占绝大多数） | 无时态 | p304–309 的 36 条语料 |
| sentence title（陈述发现） | **Present Simple**（`usually in the Present Simple tense`） | p303 |
| sentence title（结论尚未确立/预测方向） | **modal verbs `may/might/could`** | p310（例 `Diminished circadian rhythms in hippocampal microglia may contribute to age-related neuroinflammatory sensitization.`） |
| 标题中的价值信号 | 无时态限制；`A/An` 首词用于传达 `a new offer` | p309 |
| 语态 | **原文未明确**给出主动/被动的标题规则；语料中被动式标题罕见（多为名词短语） | — |

### E. 词块库（标题专用）

**（1）产出导向骨架（把"活动"改成"产出"）**

- `A hydraulic analysis of …`（一项对…的力学分析）；`A computer algorithm for computing …`（用于计算…的算法）；`A new procedure for analyzing …`（分析…的新流程）；`A novel technique for efficient …`（高效…的新技术）；`Development of … for …`（为…而开发…）；`… : a web-based tool for mapping …`（…：一个用于绘制…的网页工具）（书 pp.302、309–310）

**（2）方法/手段标记**

- `using + 手段`（使用…）；`with + 材料/手段`（用…）；`based on + 依据`（基于…）；`of … technique`（…技术）；`Mathematical modeling of …`（…的数学建模）；`A molecular dynamics study of …`（…的分子动力学研究）（书 pp.309–312）

**（3）目的/应用标记**

- `for + 名词`（用于…）；`to + 动词`（以…）；`for delivery of …`（用于递送…）；`to navigate in familiar environments`（在熟悉环境中导航）（书 pp.309–310）

**（4）价值信号（happy words）**

- `cost-effective`（高性价比）、`rapid`（快速）、`reliable`（可靠）、`robust`（稳健）、`novel`（新颖）、`efficient`（高效）、`new`（新）、`accurate`（准确）、`data-driven`（数据驱动）（书 pp.306、309–310）

**（5）冒号两侧的常见搭配**

- `←大主题→ : a novel X-based algorithm for …`；`←主题→ : a combined experimental and theoretical study`；`←断言句→ : a model of …`；`←新术语→ : a distributed simulation platform for …`（书 pp.309–310）

### F. Title 检查清单

- [ ] 已完成标题 reverse engineering：收集目标期刊/同类主题近期真实标题作语料（书 p303）
- [ ] 已把"标题 + 关键词列表"输入搜索引擎，确认出现的文章与目标读者一致（书 p301）
- [ ] 标题反映的是**研究产出/贡献**，不是研究活动或研究对象（书 p302）
- [ ] 统计了目标期刊近期同类标题的词数（参照：many journals 平均约 12 词），并记录**变异范围**而非只盯平均值（书 p304）
- [ ] 已考虑该刊在线首页是否含 Significance Statement / Research in Context 等成分（可能影响标题功能与中位长度）（书 p304）
- [ ] 每个缩写都经过"是否必要"判断，并用"当前 + 未来读者共享知识水平"衡量（书 p305）
- [ ] 关键词列表不是标题关键词的重复；已判断关键词应更泛（拓宽读者面）还是更技术化（吸引专家）（书 p306）
- [ ] 已把可移出的条目分流到关键词列表，以 `thin out` 过载的标题（书 p306、p307）
- [ ] 标题中没有难以逐层展开的复合名词串（自检：能否像 `an oil can opener repair technician training programme funding problem` 那样逐层还原）（书 p307）
- [ ] 介词数量受控；已尝试用 that 从句/实词替换歧义介词（`Low-complexity domain interactions that control gene transcription` 优于 `… interactions in gene transcription`）（书 pp.307–308）
- [ ] 已统计 7.5 的 7 个维度（A/An、冒号、方法、目的/应用、happy words、缩写、微社区）（书 p309）
- [ ] 冒号若使用，已明确其功能是"大主题 : 焦点"还是"新术语 : 定义"（书 p309）
- [ ] 句子标题仅在目标期刊接受且发现足够强时使用；结论未定时用 may/might/could（书 pp.303、310）
- [ ] 标题不夸大；所有预期能在正文（尤其 Conclusion）兑现（书 p310）
- [ ] 逐条过 5 项评估：是否预示焦点与内容 / 名词数量 / 对全部目标读者易懂 / 语法无歧义 / 贡献或潜在应用清晰（书 p310）
- [ ] 大小写与标点格式按目标期刊要求执行（本书未给规则）（书 p299）

## 1.2 Abstract（摘要）

### A. 功能定位

摘要是一份**高风险文本**，通常被**孤立阅读**、必须作为 `a standalone, independent text` 独立发挥作用，并要在读者滚动标题与摘要时**竞争注意力**（书 p265）。

> 原文：`The Abstract is a high-stakes document: many more people will read the Abstract — or briefly look at it — than the whole paper. A good Abstract enhances the visibility of the study, whereas a poor Abstract may result in the study being overlooked.`（书 p265）

### B. 通用模型：GENERIC ABSTRACT MODEL（3 个区块 / 共 **9 个组件**；6 个组件标 `+ J`，共 **7 处** `+ J` 标记）

| 区块 | # | 组件（英文原词 + 中文） | J 标记 | 书页 |
|---|---|---|---|---|
| 1 | 1 | **SIGNIFICANCE OF THE TOPIC / ESSENTIAL FACTUAL BACKGROUND**（主题重要性/必需的事实背景） | — | p286 |
| 1 | 2 | **THE CHALLENGE / PROBLEM**（挑战/问题） | — | p286 |
| 1 | 3 | **WHAT THE PAPER/STUDY DOES**（论文/研究做了什么；may include ACHIEVEMENT/VALUE + J） | **+ J** | p286 |
| 2 | 4 | **METHOD/MATERIALS**（方法/材料） | **+ J** | p286 |
| 2 | 5 | **RESULTS / COMPARISONS WITH EXISTING RESULTS**（结果 / 与已有结果的比较） | **+ J + J**（两处） | p286 |
| 2 | 6 | **IMPLICATIONS**（含义/推论） | — | p286 |
| 3 | 7 | **MAPPING TO EXISTING KNOWLEDGE**（与已有知识的对接/映射） | **+ J** | p286 |
| 3 | 8 | **ACHIEVEMENT/VALUE/CONTRIBUTION**（成就/价值/贡献） | **+ J** | p286 |
| 3 | 9 | **APPLICATIONS**（应用） | **+ J** | p286 |

> 原文提示：`Note the number of potential locations for 'happy words' J that communicate the value of the study quickly and unmistakably.`（书 p286）
> 组件 1、2、6 未标 J。

**四种摘要类型（同一功能模型的四种外壳，书 p269）**

| 类型 | 结构 | 适用场景 | 语言差异 |
|---|---|---|---|
| Simple/Standard | 单段连续文本，无标题 | 多数期刊默认 | 靠叙事衔接；功能句连续（书 pp.269–276，范例 1–10） |
| Structured | 带小标题：`Background/Aims/Method/Results`；范例用 `Objective / Approach / Main results / Significance` 与 `Background / Methods / Results / Conclusions` | 期刊强制结构化（多为医学/临床） | 功能标签外置 → 每段更短、连接词更少；**是否另有专属时态规则：原文未明确**（书 pp.276–278，范例 11–12） |
| + Significance Statement / Highlights | Abstract + 段落式声明 或 项目符号清单 | 期刊要求/鼓励"重要性说明"或"要点" | Significance 偏"为什么重要/更广意义"；Highlights 是 `►` 要点清单，可省略主语（`Shown preferential consumption of carbide over that of the bulk metal.`）（书 pp.278–281，范例 13–15） |
| Graphical Abstract | 单幅图（可含短文字） | 期刊接受/鼓励图形摘要 | 非文字；`communicates the main point right at the start`；`should use colour judiciously, and grab attention visually by minimising clutter and unnecessary elements.`（书 pp.282–285，范例 16–18） |

### C. 内容边界

**必须写**

1. **核心成就/贡献必须显式出现**：`Prioritise the central achievement or contribution and signal it explicitly to the reader.`（书 p267）；`Most Abstracts contain at least one sentence that makes the achievement/value/contribution of the study clear.`（书 p294）
2. 让读者能据以判断"是否要读全文"的必要方法信息：`if the reader cannot decide whether to read the paper without knowing whether you used simulations, models, or field data, include that information. If the value of your study is that you carried out a range of experiments rather than a single case study, include that information.`（书 pp.287–288）
3. 必要时的**极简背景**：`combine and summarise the relevant points in as few words as possible`（书 p287）。
4. 与正文**一致**：`What you say in the Abstract should be consistent with what you report in the paper.`（书 p288）
5. 数值**必须配语言**：`Adding language to numbers (e.g. only 38% or as high as 38%) ensures that the numbers will not be misinterpreted at this crucial stage.`（书 p288）
6. 含义强度不得超过数据：`the implications as stated in the Abstract must not be so strong as to be misleading or inconsistent with the data itself.`（书 p288）

**不得写 / 可省略**

1. **不填满字数上限**：`The word limit is not a target.`（书 p267）；`filling up the space to the maximum permitted number of words irrespective of relevance or narrative coherence makes the take-home message of the study unclear`。
2. **不必概括全文**：`The Abstract does not have to summarise the whole paper.`（书 p267）
3. **通常不放实际引用**：`it is rare to include actual citations in the Abstract. However, if your article follows directly from an existing published paper or is a major advance or contradiction relating to a specific work or theory, cite the relevant paper.`（书 p287）
4. **不做"全部工作的总结"**：那会导致 `a shapeless, uneven Abstract`，读者无法判断哪些是关键方法与关键结果（书 p288）。
5. **不用难以消解的指代与术语滑坡**（见 D 与 §2.8、§2.10）。
6. **缩写节制**：`Editors do not appreciate acronym-laden Abstracts`；若必须用，首次出现给一次全称（书 p268）。
7. **"如何避免与 Conclusion 重复"的专门规则：原文未明确**（书 p288 仅要求与正文数据一致、不过度）——反向约束见 §1.7 C（Conclusion 不得以 Abstract 为主要素材）。

**与相邻章节的分工**

- 与 Title：标题承诺 → 摘要兑现（书 p310）。
- 与 Introduction：摘要的组件 1–2 是 Introduction 组件 1、3 的压缩版（书 pp.290–291）。
- 与 Results/Discussion：摘要的结果/含义=压缩，正文=展开；摘要可在正文用过去时处**改用现在时**（书 p286）。
- 与 Conclusion：**功能同源但不同**；摘要不得成为结论的素材来源（书 p246），结论也不得只是摘要的改写（书 p245）。

### D. 时态与语态规则（逐组件）

| 组件 | 时态（原文规则） | 书页 |
|---|---|---|
| 1 SIGNIFICANCE / FACTUAL BACKGROUND | **Present Simple**：`Verbs in the Present Simple tense also communicate the factual background.` | p290 |
| 2 CHALLENGE / PROBLEM | **原文未明确**（6.3.1 未单列；6.4 该组词块为现在时系动词/形容词式，如 `is limited`、`is expensive`） | pp.291–292 |
| 3 WHAT THE PAPER/STUDY DOES | **Present Simple**（`most writers use the Present Simple tense`；偶用被动） | p286、p292 |
| 4 METHOD/MATERIALS（做了什么/用了什么） | **Past Simple** | p286 |
| 5 RESULTS / COMPARISONS | **Past Simple 或 Present Simple 皆可**；`the Present Simple tense is sometimes used for results and implications in the Abstract even if those are expressed in the Past Simple tense in the body of the paper.` | p286 |
| 6 IMPLICATIONS | 同组件 5（过去时或现在时皆可） | p286 |
| 7 MAPPING TO EXISTING KNOWLEDGE | **原文未明确** | — |
| 8 ACHIEVEMENT/VALUE/CONTRIBUTION | **Present Perfect（have + ed）或 Present Simple** | p287 |
| 9 APPLICATIONS | **原文未明确**（6.4 例句多用 `should`/`will`/`potential`：`Our method should find a broad range of applications…`、`…will enable the design of…`、`…have considerable potential for use as…`） | pp.295–296 |
| 语态 | 主动（we）**优于**被动以减少"谁做的"歧义（书 p266）；但组件 3 原文注明 `(sometimes in the passive)`，两种语态均可接受（书 p292） | pp.266、292 |
| **消歧总则** | 一般现在时会让**自己的结果**显得像"人所共知"，故描述自己的分析/结果时改用 **Past Simple / Present Perfect** 或 **we 主动式**：`Analysis shows concordance for 74% of mutation calls`（不清楚谁做的） vs `Analysis showed concordance for 74% of mutation calls`（明确是作者做的） | p266 |

### E. 词块库（6.4 组件分组，英文原短语 + 中文功能）

**（1）SIGNIFICANCE / FACTUAL BACKGROUND（书 pp.290–291）**
`is assumed to`（被认为）｜`is based on`（基于）｜`is determined by`（由…决定）｜`is fundamental to`（对…至关重要）｜`is influenced by`（受…影响）｜`is known to`（已知会）｜`is related to`（与…相关）｜`is regarded as`（被视为）｜`it has recently been shown that`（近期已表明）｜`it is known that`（已知）｜`it is widely accepted that`（被广泛接受）｜频度修饰：`a number of studies`、`central`、`common`、`currently`、`dominant`、`emerging`、`frequently`、`generally`、`increasing`、`key`、`many`、`often`、`popular`、`recent`、`typically`、`widely`、`worldwide`

**（2）THE CHALLENGE / PROBLEM（书 pp.291–292）**
`(an) alternative approach`｜`(a) key problem`｜`a need for`｜`challenge`｜`complicated`｜`critical`｜`debate`｜`desirable`｜`difficulty`｜`disadvantage`｜`drawback`｜`essential`｜`expensive`｜`impractical`｜`inaccurate`｜`inadequate`｜`inconvenient`｜`limited`｜`little (work)`｜`not able to`｜`previously`｜`problem`｜`require`｜`risk`｜`time-consuming`｜`unsuccessful`｜`until now`

**（3）WHAT THE PAPER/STUDY DOES（书 p292；sometimes in the passive）**
`address`（处理）｜`analyse`（分析）｜`attempt to`（试图）｜`compare`（比较）｜`consider`（考虑）｜`define`（界定）｜`describe`（描述）｜`discuss`（讨论）｜`emphasise`（强调）｜`enable`（使能够）｜`examine`（考察）｜`extend`（扩展）｜`identify`（识别）｜`include`（包含）｜`introduce`（引入）｜`investigate`（研究）｜`present`（提出/展示）｜`propose`（提出）｜`provide`（提供）｜`report`（报告）｜`review`（综述/回顾）｜`show`（表明）
启动式：`In this paper, we …`｜`In this study, we …`｜`Here, we …`｜`We report herein …`｜`Within this paper, we …`｜`This paper presents …`｜`The paper includes …`

**（4）METHOD / MATERIALS（书 pp.292–293）**
`Instead of`（而非）｜`Rather than`（而不是）｜`Unlike`（与…不同）｜被动式：`are/were analysed`、`are/were applied`、`are/were assembled`、`are/were calculated`、`are/were constructed`、`are/were evaluated`、`are/were examined`、`are/were formulated`、`are/were measured`、`are/were modelled`、`are/were performed`、`are/were recorded`、`are/were selected`、`are/were studied`、`are/were treated`、`are/were used`

**（5）RESULTS（书 pp.293–294）**
主动：`cause`｜`decrease`｜`demonstrate`｜`exhibit`｜`increase`｜`occur`｜`produce`｜`reach`｜`result in`｜`reveal`｜`yield`
被动/系动：`are/was achieved`｜`are/was found`｜`are/was identical`｜`are/was identified`｜`are/was observed`｜`are/was obtained`｜`are/was present`｜`are/was unaffected (by)`

**（6）ACHIEVEMENT / VALUE / CONTRIBUTION（happy words 主词库，书 pp.294–295）**
形容词：`accurate`｜`affordable`｜`better`｜`comparable`｜`consistent`｜`cost-effective`｜`dramatic`｜`effective`｜`efficient`｜`exact`｜`fast`｜`(the) first`｜`good`｜`improved`｜`new`｜`novel`｜`powerful`｜`practical`｜`reliable`｜`robust`｜`significant`｜`similar`｜`simple`｜`suitable`｜`superior`
动词：`able to`｜`achieve`｜`allow`｜`confirm`｜`enable`｜`enhance`｜`ensure`｜`guarantee`｜`outperform`｜`simplify`｜`solve`｜`validate`｜`verify`

**（7）IMPLICATIONS（书 p295）**
`appear to`｜`indicate that`｜`may/might/could`｜`possible`｜`potentially`｜`seem to`｜`suggest that`｜`we conclude that`
原句：`It was concluded that strontium-substituted bioactive glasses promoted osteogenesis in a differentiating bone cell culture model.`

**（8）APPLICATIONS（书 pp.295–296）**
`apply`｜`employ`｜`enable`｜`implement`｜`potential`｜`relevant for/in`｜`suitable for/in`｜`use`｜`wide range of`
原句：`The workflows, inversion strategy, and algorithms that we have used have broad application to invert a wide range of analogous data sets.`

**（9）可合并的句子功能（提高字数利用率，书 p289）**
`WHAT THE PAPER DOES + ACHIEVEMENT`｜`ACHIEVEMENT + GAP`｜`METHOD + RESULT`｜`RESULT + IMPLICATION`
例：`In animals lacking functional sensory neurons (TRPV1−/−), BMP2-mediated increases in SP and CGRP were suppressed as compared to the normal animals, and HO was dramatically inhibited in these deficient mice, suggesting that neuroinflammation plays a functional role.`

### F. Abstract 检查清单（原 6.5 的 12 项 + 消歧三条，书 pp.266–268、p297）

- [ ] 结构对位：与 GENERIC ABSTRACT MODEL（书 p286）的符合/偏离程度（书 p297）
- [ ] 重复比例：摘要中重复/重述方法与结果的比例（**原文未给阈值**）（书 p297）
- [ ] 首句功能：摘要第一句承担什么功能（书 p297）
- [ ] happy 语言量：标识研究价值/成就的 happy 语言有多少（对照 §1.2 B 的 7 处 J）（书 p297）
- [ ] 风险削减语言：是否使用 `may` 类情态动词等（书 p297）
- [ ] 核心成就优先级：主要成就如何被前置/优先呈现（书 p267、p297）
- [ ] 逐句时态：每句用什么时态、为什么（对照 §1.2 D）（书 p297）
- [ ] 归属歧义：是否因时态或被动语态造成"谁做的"归属歧义（书 p297）
- [ ] 指代歧义：是否因 `this / it / which` 造成歧义（书 p297）
- [ ] 平均句长：统计平均句长（参照 22 词）（书 p267、p297）
- [ ] 缩写可接受性：哪些缩写可接受（书 p297）
- [ ] take-home message 是否清晰（`Whether the key take-home message of the study is clear.`）（书 p297）
- [ ] 未写满字数上限（`The word limit is not a target.`）（书 p267）
- [ ] 消歧①：是否用 Past Simple/Present Perfect 或 we 主动式标明"自己的分析/结果"（书 p266）
- [ ] 消歧②：`this/it/which` 有歧义处是否已加名词或重复名词（范例中 `the hybrid method` 在 140 词摘要内重复 4 次）（书 p266）
- [ ] 消歧③：同一事物是否始终用同一术语（approach / scheme / framework / model / method / tool / device 不混用）（书 p266）

## 1.3 Introduction（引言）

### A. 功能定位

引言用**由宽到窄**的方式把读者带入研究：先确立主题的重要性与必要背景，再沿"研究地图"叙事到 gap，最后落位到本研究（书 p3：`in the Introduction you start out by being fairly general and gradually narrow your focus towards your own study`）。

> 原文：`The structure of the Introduction is similar in most research fields, and the content links directly to the structure.`（书 p4）
> 重要性的明示**不是自信问题**：`it is not a question of confidence; it is about writing in an accepted, conventional way.`（书 p6）

### B. 通用模型：GENERIC INTRODUCTION MODEL（**4 个 basic components**，由 11 句功能描述 streamline 而来）

| 组件 | 英文原词（书 p17 原样） | 中文 | 子项 |
|---|---|---|---|
| **1** | **ESTABLISH THE IMPORTANCE OF THE TOPIC/FIELD / PROVIDE BACKGROUND FACTUAL INFORMATION / PRESENT THE GENERAL PROBLEM AREA/CURRENT RESEARCH FOCUS** | 确立主题/领域重要性、提供背景事实信息、呈现一般性问题域或领域当前焦点 | 3 个子项 |
| **2** | **PRESENT PREVIOUS AND/OR CURRENT RESEARCH AND CONTRIBUTIONS: the research 'map'** | 呈现前人/当前研究与贡献 = 研究地图 | 1 项（含三种组织模式与 25 条句块） |
| **3** | **LOCATE A GAP IN THE RESEARCH / DESCRIBE THE PROBLEM YOU WILL ADDRESS / PRESENT YOUR MOTIVATION AND/OR HYPOTHESIS / IDENTIFY A RESEARCH OPPORTUNITY** | 定位 gap、描述将解决的问题、给出动机/假设、识别研究机会 | 4 个子项 |
| **4** | **DESCRIBE THE PRESENT PAPER**（sometimes mentioning aims/results/methods/conclusions, and often including 'happy' J words） | 描述本文（可提及 aim/结果/方法/结论，常含 happy words） | 1 项 |

> 模型地位（原文）：**"It's not necessary to use everything when you write an Introduction; the model should be considered as a flexible menu."**（书 p16）——组件是**菜单**不是清单。
> 四条经验观察（书 p17）：**almost all** Introductions **begin** with something in Component 1；**almost all end** with something in Component 4；部分 Component 2 是"当前知识综述"（多为 Present Simple，仍可能需引用）；部分 Component 3 的 gap/problem **不明说**（动机只是延伸前人研究，或 gap 隐含于对本研究及 aim 的描述）。背景事实（Present Simple）可在**任何**作者认为读者需要处补入。

**组件 2 的三种组织模式（书 pp.12–13）**

| 模式 | 说明 | 原文评价 |
|---|---|---|
| General-to-specific | 从领域一般研究（possibly a review article）逐步走向接近本研究问题/gap 的研究 | **`This is the most common pattern.`** |
| Different approaches/theories/models | 按所用方法/理论/模型分组同类研究 | 避免 `the 'tennis match' effect`（每句都以 However / On the other hand 来回跳） |
| Chronological order | 适用于领域发展与政策法规挂钩的情形 | — |

**组件 3 的关键规则**：`in professional writing it is unusual to put the gap or problem in the form of a question; it is normally stated as a prediction, suggestion or hypothesis.`（书 p14）

### C. 内容边界

**必须交代（7 项，书 pp.6–17）**

1. 主题/领域为何重要或有用（若目标期刊惯例如此）；或以**具体研究焦点 / 关键术语定义 / 必要事实**开场（领域很窄、读者都是小同行时后者更合适，书 pp.6–7）。
2. 使不同背景读者都能读懂的必要背景事实：`As a general rule it is better to provide slightly too much background information than slightly too little.`（书 p8）
3. 领域当前的 general problem area / current research focus（**注意：①②③都不是你自己论文要解决的 specific problem**，书 p10）。
4. 与前人研究的关系及本研究在研究地图上的位置（书 p12）。
5. gap / problem / motivation / hypothesis / research opportunity（可隐含，书 p17）。
6. 本文做什么、目的或焦点、结构、aim（可提及主要结果/方法，书 pp.14–15）。
7. 明确的 citation，用于支撑背景事实与重要性主张（书 p9）。

**不得写**

1. **不要一上来就描述自己要解决的 specific problem**：`Most authors don't`——读者尚未获得理解该问题所需的背景（书 p9）。
2. **方法细节不要过多**：可提及方法，但细节过多会使引言`very long and lose focus`（书 p15）。
3. **结果数据不要详列**：同一条规则涵盖 results（书 p15）。
4. **不是文献清单/读书摘要**：`The literature and contributions review in a research article is not a list or a summary of what you have read. It is a carefully-narrated journey through selected relevant research…`（书 p11）；否则 `it will look like a shopping list`（书 p12）。
5. **不要跳步**：`if you jump straight from very general to very specific information early in the Introduction this is likely to cause difficulties, particularly for the interdisciplinary reader.`（书 p8）图像比喻：`Always show your readers the general picture before you proceed to the details: show them the wall before you start to talk about the bricks!`（书 p8）
6. **gap 不写成问句**（书 p14）。注意：样本中有论文在**描述本研究**（组件 4）时列出 `The following questions are addressed: (a)… (b)… (c)…`，这与"gap 不用问句"不冲突——问句出现在组件 4 而非组件 3（原文未就此差异作评论）。
7. **不要无意义换时态**：`Tense changes are always meaningful… so don't choose or change tense randomly.`（书 p55）

**与相邻章节的分工（书 p3 的成对功能表）**

| Introduction 做什么 | Discussion 做什么 |
|---|---|
| 用 opening sentence 让读者"get in" | 结尾"get out"，找到合适的收束方式 |
| 呈现过去/当前的研究与知识 | 说明本研究如何贡献/推进该知识 |
| 陈述 specific problem 或指出 gap | 讨论该问题被解决到什么程度 |
| 结尾让读者进入 central section（通常 Methods 和/或 Results） | 结尾让读者进入 Discussion |

**对齐要求**：`your Introduction and the research questions or gap you identify must align with the rest of the article, and particularly the Discussion/Conclusion.`（书 p71）

**期刊差异**：若改投别的期刊，**不能原样重投**——`the readership of that journal may be either narrower or wider… In particular, you may need to adjust the first sentence to ensure that it responds to the needs of a different readership.`（书 pp.7–8）；黄金法则：`check recent editions of the journal you are submitting to, and start your Introduction in the same way as other authors who have successfully submitted their work on similar topics to that journal.`（书 pp.7–8）

### D. 时态与语态规则（逐组件）

| 位置/功能 | 时态 | 原因与英文原例（书页） |
|---|---|---|
| 组件 1：指称近期时间（in recent years / in the past five years） | **Present Perfect** | `Much study in recent years has focused on…`；`The status and function of the port has evolved rapidly over the past three years.`（p6） |
| 组件 1：聚焦当前状况 | **Present Simple** | `There are substantial benefits to be gained from…`（p6） |
| 组件 1：希望论文五年后仍有相关性 | **改用可识别日期**（since 2018） | 因为 what is recent or current now will not be recent or current in five years' time（p6） |
| 组件 1：背景事实、被接受的事实 | **Present Simple** | `the verb tense used for accepted/established facts`（p7） |
| 组件 1：曾为研究发现的"事实" | Present Perfect（`Lawrence et al. have found that…`）或 Past Simple（`Lawrence et al. (2000) found that…`）→ 确立后转 **Present Simple + 引用** → 最终引用脱落成为公认背景 | `The only way to get this right is to check current usage in your field.`（pp.9–10） |
| 组件 2：引用某项研究的具体发现 | **Past Simple** | `The Past Simple just describes what the authors found in their study; the findings are linked to that study and are not presented as permanent truths.`（p53） |
| 组件 2：把该发现表述为可靠、恒久的事实 | **Present Simple** | `choosing the Present Simple reflects a belief that the findings are strong and reliable enough to constitute a permanent truth.`（p53） |
| 组件 2/3：强调"与当下相关" | **Present Perfect** | 由 `was demonstrated` 切成 `little attention has been paid`，`in order to communicate that the latter refers to a current gap in the research`；若仍用 Past Simple（`little attention was paid`）则意为"当时（两年前）无人关注"，此后可能已解决（p55） |
| 组件 3：研究机会 | 常用**情态动词 may/might/could/would** | `Research opportunities are often communicated by using modal verbs such as may/might/could/would.`（p50） |
| 组件 4：描述本文工作本身 | **Present Simple** | `This paper is organised as follows` / `This study focuses on…`（p15） |
| 组件 4：陈述 aim | **Past Simple** | `The aim of this project was… / Our aim was…`，**because in 'real time', the aim existed before the work was done**（p15） |
| 组件 4：aim 用 Present Simple 亦可能 | **Present Simple** | `The aim of this study/paper is…`，particularly in cases where the aim is only partially achieved（p15） |
| 时态自查动作 | — | 不要用五年前论文的时态；用 Google Scholar 等**只搜近期研究**核对当前惯用（pp.10、53） |

**语态（书 pp.64–65）**：引言末尾说"本文做什么/呈现什么"时，三种选项——① 用 **we/our**；② 用**被动**；③ **改写为以非人为主语的主动句**（`This study demonstrates that…` / `Section 1 presents…` / `The present paper describes an algorithm for clustering sequences into index classes` / `Section 2 reviews existing methods`）。判定依据是 **style + communicative accuracy**：先看目标期刊（科学写作传统偏好被动，但部分领域/期刊正在变化；被动在方法步骤描述中仍常见）；若用主动，必须**保持 we/our 指代一致**——它可能指"我和本文其他作者"（we investigated）、也可能是"我和同行 + 甚至读者"（our knowledge / when we consider）、还可能泛指（we know）；泛指时 `it may be clearer to use a construction with It (It is known/thought that…)`。

### E. 词块库（Section 1.4，书 pp.45–52）

> 清单来源：`This section lists words and phrases for the Introduction from analysis of over 2,500 published research articles in different disciplines. The list only includes words and phrases which appear frequently and are therefore considered normal and acceptable by writers and editors.`（书 p45）

**（1）ESTABLISHING SIGNIFICANCE（通常用于第一句，书 pp.46–47）**
名词性：`(an) advantage`｜`(an) attractive approach`｜`(a) central problem`｜`(a) challenging area`｜`(a) considerable number`｜`(a) crucial issue`｜`(a) current challenge`｜`(a) dramatic increase`｜`(an) essential element`｜`(a) focus on`｜`(a) fundamental issue`｜`(a) global concern`｜`(a) growth in popularity`｜`(an) increasing number`｜`(an) interesting aspect`｜`(a) key technique`｜`(a) leading cause (of)`｜`(a) number of`｜`(a) popular method`｜`(a) powerful tool/method`｜`(a) primary cause (of)`｜`(a) (wide) range (of)`｜`(a) rapid development`｜`(a) remarkable variety`｜`(a) significant increase`｜`(a) striking feature`｜`(a) traditional technique`｜`(a) useful method`｜`(a) variety of`｜`(a) vital aspect`｜`(a) worthwhile study`
形容词/副词/动词性：`attracted (much) attention`｜`benefit/beneficial`｜`common/ly`｜`cost-effective`｜`during the past (two) decades`｜`emerging`｜`extensively studied`｜`for many years`｜`frequent/ly`｜`great potential`｜`importance/important`｜`major`｜`many/most`｜`multidisciplinary interest`｜`much study in recent years`｜`now`｜`numerous investigations`｜`of growing/great interest`｜`often`｜`play a key/major role (in)`｜`principle`｜`recent/ly`｜`relevant`｜`several`｜`today`｜`typical`｜`valuable`｜`well-documented`｜`well-known`｜`wide/ly`｜`widespread`｜`worldwide`
首句范例：`The status and function of the port has evolved rapidly in recent years.`｜`Since the discovery of the first isolated graphene layer, many chemical approaches have been developed.`｜`The increasing pressure to eliminate lead has stimulated great interest in the search for lead-free solders.`｜`Fourier transforms are widely used in image processing to characterise textures in images.`｜`Control of serum phosphorus levels is a central goal in the management of patients with chronic renal failure.`｜`Heat transfer phenomena play an important role in welding.`
脚注提醒：`such numbers may change over time, so consider including a date (e.g. in 2019).`（书 p47）

**（2）VERBS：指称/描述前人及当前研究活动与贡献（书 pp.47–48）**
列表 A：`achieve`｜`address`｜`analyse`｜`apply`｜`argue`｜`assess`｜`assume`｜`attempt`｜`calculate`｜`categorise`｜`create`｜`deal with`｜`define`｜`demonstrate`｜`describe`｜`design`｜`detect`｜`determine`｜`develop`｜`discover`｜`focus on`｜`generate`｜`identify`｜`imply`｜`improve`｜`interpret`｜`introduce`｜`investigate`｜`measure`｜`mention`｜`produce`｜`propose`｜`prove`｜`provide`｜`put forward`｜`recognise`｜`report`｜`resolve`｜`reveal`｜`review`
列表 B：`carry out`｜`challenge`｜`claim`｜`clarify`｜`collect`｜`compare`｜`conclude`｜`conduct`｜`confirm`｜`consider`｜`discuss`｜`enhance`｜`establish`｜`estimate`｜`evaluate`｜`examine`｜`explain`｜`explore`｜`extend`｜`find`｜`model`｜`modify`｜`monitor`｜`note`｜`observe`｜`obtain`｜`perform`｜`point out`｜`predict`｜`present`｜`revise`｜`show`｜`solve`｜`state`｜`study`｜`suggest`｜`support`｜`test`｜`use`｜`verify`
使用理由：`You can't spend the rest of your life writing they did/showed/found; sometimes you need to be more specific, so look for verbs describing what exactly was done, for example calculated, monitored, identified.`（书 p45）
原文提醒：`Note: Use these verbs throughout, for example at the end of the Introduction, when you say what you did in your study or what is in your paper.`（书 p48）

**（3）组件 2 的衔接句块（25 条，书 p13 原文全列）**
`[ref] also observed that…`｜`[ref] resolved this by…`｜`[ref] were the first to…`｜`A pioneering study by [ref] demonstrated…`｜`A similar approach was used by [ref], who…`｜`An alternative approach was proposed by [ref], who…`｜`According to [ref], it is highly likely that…`｜`Importantly, [ref] noted that…`｜`In order to resolve this, [ref] analysed/developed...`｜`In that study, although…`｜`In their recent work, [ref] has suggested that…`｜`It was later shown by [ref] that…`｜`One [potential] implication of [ref]'s results is that…`｜`Other studies have focused on…, for example, [ref] and [ref] attempted to…`｜`Recently, it has been shown/suggested that…`｜`Soon after, [ref] proposed…`｜`Subsequently,…`｜`Taken together, these studies suggest that…`｜`The most systematic review is that in/of [ref]…`｜`These findings challenge the work of [ref], who…`｜`This approach was further developed by [ref], who…`｜`This methodology was adapted by…`｜`To address this issue, [ref]…`｜`To overcome these problems, a different approach was used by/in [ref].`｜`Within five years, [ref] developed a…`

**（4）GAP 类词块（书 pp.49–50）**
Group 1 PROBLEM/CRITICISM 形容词/短语：`absent`｜`complicated`｜`controversial`｜`costly`｜`deficient`｜`disappointing`｜`doubtful`｜`expensive`｜`false`｜`far from (ideal)`｜`fragile`｜`hard to (detect)`｜`impractical`｜`inaccurate`｜`inadequate`｜`incapable (of)`｜`incompatible`｜`inconsistent`｜`inconvenient`｜`incorrect`｜`ineffective`｜`inefficient`｜`inferior`｜`inflexible`｜`insufficient`｜`misleading`｜`not able to…`｜`not ideal`｜`not sufficiently…`｜`not/no longer useful`｜`of little value`｜`over-simplistic`｜`poor`｜`problematic`｜`restricted`｜`severe`｜`time-consuming`｜`unable to`｜`undesirable`｜`unnecessary`｜`unrealistic`｜`unsatisfactory`｜`unsuccessful`｜`unsuitable`｜`unsupported`
Group 1 名词/动词性：`(a) challenge`｜`(a) defect`｜`(a) difficulty`｜`(a) disadvantage`｜`(a) drawback`｜`(a) flaw`｜`(a) gap`｜`(a) lack`｜`(a) limitation`｜`(an) obstacle`｜`(a) problem`｜`(a) risk`｜`(a) shortcoming`｜`(a) weakness`｜`(to) be confined to`｜`(to) fail to`｜`(to) fall short of`｜`(to) ignore`｜`(to) lag behind`｜`(to) miscalculate`｜`(to) misjudge`｜`(to) misunderstand`｜`(to) neglect`｜`(to) overlook`｜`(to) suffer (from)`
提醒：`These are often signalled by words such as however, although, while, nevertheless, despite.`（书 p49）
Group 2 RESEARCH OPPORTUNITIES：`(an) alternative`｜`(the) next step`｜`(to) demand clarification`｜`(to) need to re-examine`｜`more work is needed`｜`not addressed`｜`not dealt with`｜`not studied`｜`(to) raise the question`｜`(to) remain controversial`｜`(to) remain unstudied`｜`(to) require (clarification)`｜`few studies have…`｜`ideal candidate`｜`incomplete`｜`it is/seems possible that…`｜`little evidence is available`｜`little work has been done`｜`not well understood`｜`suggest/s that…`｜`there is an urgent need…`｜`to the best of our knowledge`｜`unanswered`｜`unclear`｜`unexamined`｜`unproven`｜`unsolved`
原例：`Little attention has been paid to the selection of an alternative biocompatible material.`｜`How propofol acts on neural circuits to produce unconsciousness remains unclear.`｜`One of the limitations of electron triboemission experiments to date is that they provide only ensemble average values.`｜`However, the search for a stable oral prostaglandin preparation has been largely unsuccessful.`｜`The high absorbance makes this an impractical option.`｜`Determining the function of these proteins remains a challenge.`｜`Although there is general agreement regarding the timing of sea-level events, their amplitude remains controversial.`

**（5）THE PRESENT WORK 与 'happy' words（书 pp.51–52）**
动词/短语：`(to) attempt`｜`(to) compare`｜`(to) concentrate (on)`｜`(to) describe`｜`(to) determine`｜`(to) develop`｜`(to) discuss`｜`(to) enable`｜`(to) enhance`｜`(to) evaluate`｜`(to) facilitate`｜`(to) focus on`｜`(to) identify`｜`(to) improve`｜`(to) investigate`｜`(to) offer`｜`(to) outline`｜`(to) predict`｜`(to) present`｜`(to) propose`｜`(to) provide`｜`(to) report`｜`(to) reveal`｜`(to) solve`｜`(to) succeed`
结构/体裁性短语：`(is) organised as follows:`｜`(is) set out as follows:`｜`(our) approach`｜`(the) present work`｜`(this) paper`｜`(this) project`｜`(this) report`｜`(this) section`｜`(this) study`｜`(this) work`
aim 类名词：`aim`｜`goal`｜`intention`｜`objective`｜`purpose`
'happy' words J：`able to`｜`accurate`｜`advantage`｜`effective`｜`efficient`｜`excellent`｜`fully`｜`innovation`｜`new`｜`novel`｜`potential`｜`powerful`｜`practical`｜`promising`｜`relevant`｜`robust`｜`simple`｜`straightforward`｜`successful`｜`superior`｜`unique`｜`valuable`
原例：`Our study focuses on…`｜`The main objective of this study was to describe and examine…`｜`In this paper we present a robust method for…`｜`New correlations were developed with excellent results.`｜`To our knowledge, this is the first demonstration of the…`｜`Our design is both simple and accurate, and can be fully integrated into…`

**（6）段落/句子起始 intent 短语（18 条，书 p68）**
`According to this theory, …`｜`An alternative approach is…`｜`Another key feature is…`｜`Having collected the data, …`｜`Here, we present…`｜`In order to explore this, …`｜`On the basis of this finding, …`｜`Our next goal was…`｜`The first evidence for this is…`｜`These data suggest that…`｜`This is important because…`｜`This process occurs in two stages.`｜`To address this question, …`｜`To confirm…, we…`｜`Turning now to…`｜`We argue that…`｜`When we consider…`｜`With regard to…`

### F. Introduction 检查清单

**原文 TIPS（书 p71，逐条）**

- [ ] 在开始造句之前，**逐段规划整个 Introduction**
- [ ] 确认 Introduction 与所识别的 research questions/gap 与全文一致，尤其与 Discussion/Conclusion 一致
- [ ] 不要在开头过早从非常一般跳到非常具体
- [ ] 意识到自己熟悉主题，可能察觉不到读者对背景信息的需求，尤其面向跨学科读者时
- [ ] 考虑信息密度，让"眼读速度"匹配"脑处理速度"
- [ ] 段落如何开头、如何衔接上一段 → 打字前先想好
- [ ] 句子如何开头、如何衔接上一句 → 打字前先想好
- [ ] 记住你永远能看懂自己写的东西，但你不是为自己写

**模型与内容检查**

- [ ] 是否以 **Component 1** 起、以 **Component 4** 收（书 p17 两条"almost all"）
- [ ] 第一句/第一段是否给出被接受的背景事实或重要性陈述（书 pp.6–7）
- [ ] 开场句是否与目标期刊近期成功论文的开场方式一致（黄金法则，书 pp.7–8）
- [ ] 是否避免了"一上来就描述自己具体问题"（书 pp.6、9）
- [ ] 是否填补了开场各句之间的信息鸿沟（书 p8）
- [ ] 背景信息是否略多而非略少（书 pp.8、14）
- [ ] Component 2 是否不是清单/读书摘要，而是一条 carefully-narrated journey（书 pp.11–12）
- [ ] 每篇被提到的研究是否 relevant + essential 并指向本研究 motivation（书 p11）
- [ ] 是否采用明确组织模式（general-to-specific / 按方法分组 / 编年）并避免"tennis match"（书 pp.12–13）
- [ ] Component 3 是否用 However/Although 等 instant recognition 信号引入 gap（书 p14）
- [ ] gap 是否陈述为 prediction/suggestion/hypothesis 而非问句（书 p14）
- [ ] 批评前人时语言是否 respectful and impersonal（书 p14）
- [ ] 是否没有在 Introduction 塞入过多方法或结果细节（书 p15）
- [ ] Component 4 是否使用 'happy' words 明确标示成就（书 pp.15、51）
- [ ] 若提及 aims/results/methods/conclusions，是否控制在"提及"层级（书 p17）

**语言与行文检查**

- [ ] 第一句指近期时间是否用 Present Perfect；指当前状况是否用 Present Simple；是否需要改用可识别日期（书 p6）
- [ ] 背景事实是否用 Present Simple；该事实当前是否仍需要引用（书 pp.7、9–10）
- [ ] 引用是否放在能明确归属的位置（必要时句中引用），没有把整句信息归给句末所有引用（书 p11）
- [ ] 描述本文工作是否用 Present Simple、陈述 aim 是否用 Past Simple（书 p15）
- [ ] 是否没有无意义地换时态（书 p55）
- [ ] 若写 `little attention has been paid`，是否确实要表达"当前的 gap"；若想表达"当时"则用 Past Simple（书 p55）
- [ ] 是否用只搜近期研究的方式核对了本领域当下的惯用时态（书 pp.10、53）
- [ ] 句子长度是否在 20–23 词量级；用分号连接后是否检查了整句长度（书 p58）
- [ ] pro-form 是否重复了同一个名词（`this device` 而非 `this technique/method`）（书 p57）
- [ ] 是否避免了 `This`/`They`/`These` 指代不明（书 p58）
- [ ] 信号词是否用对功能（Moreover 与前句同功能；Therefore/Consequently 必须有可识别原因）（书 p59）
- [ ] 是否没有每句都用信号词开头（会显得 jerky、over-emphatic、formulaic）（书 p61）
- [ ] 是否避开 `as`/`since`/`while` 的歧义用法；是否误用 `on the contrary`/`conversely` 表达单纯差异（书 pp.59–60）
- [ ] we/our 的指代在全文是否一致；泛指时是否改用 `It is known/thought that…`（书 p65）
- [ ] 段落是否有单一 unifying function、无 loose/irrelevant 内容（书 p66）
- [ ] 是否避免成串短段/单句段与过长段落（参考：平均 150–170 词）（书 p66）
- [ ] 每段是否有清晰的 entry sentence 呈现 topic/function/aim（书 p67）

**EXERCISE 5 的成文要求（书 pp.69–70）**

- [ ] 严格按书 p17 的 streamlined model 写，**必须包含四个主要组件**
- [ ] 每个组件使用本手册 §1.3 E 的词汇
- [ ] 篇幅约 **250–350 词**（题目要求）
- [ ] 参考范文结构：第 1 段＝组件 1；第 2 段＝组件 2（按年份 `In 1999, Wang et al. … and in 2002 Martinez introduced…`）；第 3 段＝组件 3+4

## 1.4 Methods（方法）

### A. 功能定位

Methods 的 **primary function** 是 `to contain enough detailed information to ensure that other researchers can replicate the work done and obtain similar results`（书 p76）；同时承担双重沟通任务：`This is exactly what I did/used` 与 `I had good reasons for making those decisions`（书 p81）。

> 可复现性绑定可信度：`The readers' acceptance of those results and conclusions is linked to their acceptance of the method.`（书 p75）
> 名称弹性：同一章可能叫 `Methods`、`Materials and methods`、`Experimental`、`Test methods`、`Simulations`、`Model`、`Experimental design`、`Experimental work`、`Experimental techniques`、`Methodology`，甚至 `Calibration`、`Model-controlled test`（书 p75）。

### B. 通用模型：A METHODS MODEL（**6 个组件**，由 9 句功能分析精简；另加"图形内容"增补项）

| # | 组件（英文原词 + 中文） | 子项 | 书页 |
|---|---|---|---|
| **1** | **PROVIDE AN OVERVIEW OF/STATEMENT ABOUT THE METHODS**（给出方法总览/陈述） | RESTATE THE AIM/GAP FROM THE INTRODUCTION（重述引言的 aim/gap）；DESCRIBE/GIVE THE SOURCE OF MATERIALS/EQUIPMENT USED（说明材料/设备来源） | p88 |
| **2** | **PROVIDE DETAILS OF THE MATERIALS/METHODS**（给出材料/方法细节，如温度、序列） | ± **justify choices**（为选择辩护）；± **indicate that you took appropriate care**（表明操作严谨） | p88 |
| **3** | **DESCRIBE/DISCUSS THE CONTENT OF A FIGURE/TABLE**（描述/讨论图表内容） | — | p88 |
| **4** | **REFER TO MATERIALS/METHODS IN OTHER STUDIES**（引用他人材料/方法） | to compare（作比较）；to justify your choices（为选择辩护） | p88 |
| **5** | **PROVIDE BACKGROUND INFORMATION IN THE PRESENT SIMPLE TENSE**（用一般现在时给背景信息） | to support the reader；to justify your choices | p88 |
| **6** | **INDICATE ISSUES OR PROBLEMS**（指出问题/局限） | — | p88 |
| 增补 | **含图/表/照片/地图等图形内容**（原文把 figures, maps, photographs, tables 作为一项加入模型） | — | 书 p87 |

> 模型地位：Methods 模型是 **"菜单（a 'menu'）"**——按选题与目标期刊规范挑选适用项；例如没遇到问题就不用第 6 项（书 p88）。

**顺序原则（top-down）**：先给"做了什么/用了什么"的概述，再展开细节。金句：`show your reader the wall before you start to talk about the bricks!`（书 p79）——先细节（bottom-up）会让每个读者自行拼出不同的方法理解，而"这不是读者的工作"。

**三种常见的 Methods 开头方式（书 pp.79–80）**

1. Offer a general overview by outlining the parameters of the work（试验次数、材料/设备）and perhaps **the purpose**；
2. Provide information about **the source of the materials/equipment** 或 **the properties, characteristics**；
3. **Refer back to something in the previous section**（项目的 aim 或你正在处理的问题）。
   ——当研究焦点和/或期刊读者群很窄、读者熟悉此类方法时，也可**直接从方法/材料/材料来源写起**（书 p79）。

**组件 2 的内部顺序**：细节 → 序列 →（± 理由/优势）→（± 显示谨慎），并用 `prior to`、`until`、`at which point` 等**精确序列语言**而非仅 `then/next`（书 p82）。
**组件 4 与 5 的位置**：通常在给出具体步骤前或穿插于步骤中（书 p80、p90）。
**组件 6 的位置**：放在相关步骤之后（示例在末句），并在全文结尾（Discussion/Conclusion）再次呼应（书 pp.78、85）。
**收尾方式**：原文未给固定模板；示例结尾走向为（i）说明问题/局限；（ii）以"比较既有方法 + 本方法优势"收束；（iii）用 sequence + measurement 的细节句自然结束（书 pp.85、93、132–133）。**"最常见的结尾"清单原文未明确。**

### C. 内容边界

**必须提供**

1. **材料/样品的来源**：`GIVE THE SOURCE OF THE MATERIALS/SAMPLES/EQUIPMENT USED`；常用 `provided by`、`purchased from`、`a kind gift from`、`supplied by`（书 pp.100、129）。
2. **材料/设备的背景与性质**：必要时详细描述设备/装置，或描述照片、示意图让读者 `visualise it`（书 pp.100–101）。
3. **具体且精确的细节**：`A total of 18 3 mL samples were collected`；仪器型号与厂商及产地 `a pH meter (Sartorius AG, Professional Meter PP-50, Gottingen, Germany)`；软件 `CELLQUEST`、`Avizo Fire 8.0`、`LabVIEW`（书 pp.78、82、89–93、97–98）。
4. **序列（sequence）与每步耗时**（书 pp.82、104）。
5. **统计/计算方法**：如 `The standard deviation was calculated from at least four qPCRs from three independent experiments.`；`The relative gene expression levels were calculated by calibrating their Ct values with those of housekeeping genes, HPRT and GAPDH, and then normalized to undifferentiated hESCs.`（书 p89）——**原书未设专门的"统计方法"词块分类**（散见于技术动词、序列语言与比较类语言中；统计专用句式清单**原文未明确**）。
6. **样本/受试者**：细胞系、`23 cadaveric knees`、健康受试者、问卷量表（书 pp.89、95、100、111）。**纳入/排除标准、伦理审批、知情同意的写法：原文未明确。**
7. **方法比较**：与同领域他人材料/方法的异同是 Methods 的重要主题，分 Option 1/2/3（见 E-7）。
8. **引用**：方法源于他人方法时，即使众所周知通常仍需给引用；当方法已成背景知识时引用可省略——`as a method becomes more and more established, the citation occurs less frequently, and the method eventually becomes part of the background information`（书 p83）。

**详略取舍（判据）**

- 判据是对**特定他人**知道什么的合理准确判断（`a reasonably accurate idea about what specific other people know`，书 p82）；**但读者不是你的同事**（搜索引擎使读者群更广、更跨学科）→ 结论：`it is better to give slightly too much information than too little.`（书 p82）
- 两个自问（书 p80）：**What can ALL potential readers be assumed to know about this method in general? What do they ALL need to know in order to understand your specific method?**
- 若某部分方法与已知方法相同/众所周知：**不必全写，但仍应给引用**；折中写法：`The assay was carried out as in [1]. Briefly, samples were…`（书 p84）。因为**要求读者为读懂本文去查引用是不专业的**。
- 现有/标准方法常用 **Present Simple** 描述（书 p84）。
- **不要用实验室笔记的详略**：`Don't confuse your lab notes with the Methods section. The first was written for you; the second needs to be written for a reader.`（书 p136）
- 单位符号（如 `mL` vs `ml`）按目标期刊最新版或 SI 规定（书 p81）。

**与 Results / Discussion 的边界**

1. 大量"理由/优势"语言属于 Methods，而非 Results（书 p81）。
2. Methods 也承担"让 Results 可理解的背景信息"；正文与补充材料（supplementary materials）的配比由**目标文章**决定（书 pp.75–76）。
3. 文献线索贯穿全文：Introduction 铺背景 → **Methods 与 Results 通过与他人方法、结果比较** → Discussion/Conclusion 指出贡献（书 p84）。即"比较"两处都做，但 Methods 比的是**方法/材料**，Results 比的是**结果**。
4. 图表若含方法信息（流程图、装置图、粒度分布表），其描述可在 Methods 出现，**其进一步解读留给 Results/Discussion**（书 pp.91、130）。
5. 结果数据的计算细节（std dev、normalisation）在示例中落在 Methods（书 p89）。

**problems/limitations 的处理（原书专门讨论）**

- **为什么写**（书 pp.85–86）：① 文章结尾常给 future work 建议，而这些建议常与研究中记录的问题/局限相连；先提再末处呼应，能让其他研究者接手；**切忌把问题/局限第一次就放到文章最末尾**（会打击读者对你工作的信心），更有效的做法是**在它出现的地方先提——即 Methods——再在文末重提**。② **不提会显得你不知道这些问题**；反之，提及体现 self-awareness，**提升研究的可靠性**。
- 原文金句：`Science does not truly exist until it is published`（书 p85）。
- **怎么写得不像失败**：弱化问题及其影响、弱化自己的责任、放大好的方面、和/或给出解决办法；示例用语 `brief contact`、`negligible`（书 p86）。
- 呼应句示例：`Future studies should further reduce the risk of CFC contamination by removing plastic and other anthropogenic materials from the source location prior to collecting samples.`（书 p86）
- `Future work should` vs `Future work will`：**should 提出方向、邀请学界接手；will 表达作者自己的计划、意图或正在进行的工作**（书 p111）。

### D. 时态与语态规则（2.5.1，书 pp.113–115）

**五条基础规则（书 p113）**

1. 动笔前先查目标文章与 Guide for Authors，判断该刊 Methods 主要用被动还是主动。
2. 主动（`we investigated`/`we conclude`）在科研写作中常见，**但部分过程在 Methods 中仍习惯用被动**。
3. 科技作者一般用 **agentless passive（`was/is found`）**，而**不用 passive + agent**（`was/is found by us`）——于是"谁做的"多数情况下不被提及。
4. **歧义风险 1（归属）**：agentless passive 在描述自己工作与描述他人工作时形式完全相同（两句话字面一样：`samples were collected using a sterile swab`）→ 会丧失对自己贡献的 ownership，或无意中把功劳记到别人头上。
5. **歧义风险 2（时态）**：**Past Simple 报告"你做了什么"；Present Simple 描述标准流程或设备**：
   - Reporting what you did: `A flexible section was inserted in the pipe.`（Past Simple agentless passive）
   - Describing a standard procedure: `A flexible section is inserted in the pipe.`（Present Simple agentless passive）
6. 原则：**`THE AIM IS NOT SIMPLY TO MAKE IT POSSIBLE FOR THE READER TO UNDERSTAND; THE AIM IS TO MAKE IT IMPOSSIBLE FOR THE READER NOT TO UNDERSTAND.`** 标记自己贡献的一种语言手段是 **`In this study`**（书 p114）。

**逐组件时态表**

| 组件/内容 | 时态 | 书页 |
|---|---|---|
| 组件 1 总览、aim/gap 重述 | 视 aim 规则（引言 aim 用 Past Simple；见 §1.3 D） | pp.15、88 |
| 组件 1 材料/设备来源 | 多为 **Past Simple**（`was provided by`、`was purchased from`） | p100 |
| 组件 2 你做了什么 | **Past Simple**（agentless passive 或主动） | pp.113–114 |
| 组件 2 标准流程/设备 | **Present Simple** | pp.113–114 |
| 组件 2 现有/标准方法描述 | **Present Simple** | p84 |
| 组件 3 图表内容 | 依图表性质；多为 Present Simple（`Fig. 1 summarises…`） | pp.130、132 |
| 组件 4 他人方法 | 依引用情形；过去研究用 Past Simple，既定方法用 Present Simple | pp.83–84 |
| 组件 5 背景信息 | **Present Simple**（模型明文） | p88 |
| 组件 6 问题/局限 | 多为 Past Simple（发生过的）+ 情态（should/will 区分见 C） | pp.85–86、111 |
| 完成 Methods 后 | **逐句检查时态**，确认它传递的是你想要的功能/含义 | p115 |

**五种 agentless passive 的处置表（书 pp.114–115，原文表格照录要点）**

| # | 想表达的意思 | 如何使其清楚 |
|---|---|---|
| 1 | X was (collected/modified) **by me**, in the procedure or work that I carried out | 改主动 `We collected/modified X`；加 `here / in this work / in our model`；用"假主语"如 `This experiment / The procedure described above` |
| 2 | X was … **by the person whose procedure I am using as a basis or comparing with mine** | 给引用；加 `in their work / in that model`；用假主语如 `That experiment / The probe used in their study` |
| 3 | X **is** … normally, as part of an established or standard procedure | 视该流程的知名程度决定是否仍给引用；用 `using standard procedures / as in 5` |
| 4 | X is … **as you can see in Fig. 1, and it was done by me** | 明确把图内容定义为自己的工作：`The experimental setup used here is shown in Fig. 3.`；或改主动 `We collect/modify X` |
| 5 | X was … by me, **but in my field/this journal the Present Simple is used** | 改主动 `We collect/modify X`；加 `here / in this work / in our model`；用假主语如 `This equation / The model` |

### E. 词块库（2.4 Language for the Methods section，书 pp.99–112）

**（1）GIVE THE SOURCE OF THE MATERIALS/SAMPLES/EQUIPMENT USED（书 p100）**
`is commercially available`｜`was a kind gift (from)`｜`was acquired`｜`was carried out`｜`was chosen`｜`was conducted`｜`was collected`｜`was devised`｜`was/were found (in)`｜`was generated`｜`was modified`｜`was obtained`｜`was performed (by/in)`｜`was provided (by)`｜`was purchased (from)`｜`was supplied (by)`｜`was used as received`｜`was used as supplied`
原句：`The fetal bovine serum used in this study was provided by Gibco, UK.`｜`Dextran standard 5000 was purchased from Sigma Aldrich.`｜`The cell lines were a kind gift from Dr David Louis (Massachusetts General Hospital, MA, USA).`｜`The inclusion criteria used here are a modified version of those in a previous study22.`

**（2）SUPPLY BACKGROUND / DESCRIBE MATERIALS, SAMPLES, EQUIPMENT —— 空间关系语言（书 pp.101–102）**
位置介词/短语：`above, over, on top (of), adjacent, adjoining, across, along, against, at the front, on the front, in the front, below, under, underneath, beside, alongside, boundary, edge, border, circular, rectangular, conical, downstream, upstream (of), equidistant, equally spaced, exterior, interior, in the vicinity, in close proximity, nearby, inside, within, lateral, sideways, horizontal, on each side, on either side, on both sides, on the right/left, to the right/left, opposite, facing, out of range, within range, parallel (to/with), perpendicular (to), symmetrical, asymmetrical`
动词：`align, arrange, assemble, attach to, bisect, connect, converge, couple, embed, encase, enclose, fasten, fit, fix, install, intersect, join, locate, mount, orient, place, position, situate, space, surround`
原句：`The apparatus consists of a circular tube fitted with rectangular-winglet tape (RWT) vortex generators.`｜`Measuring stations were spaced 20 cm apart, starting 2 cm downstream of the pipe entrance.`｜`A scanner was mounted on top of a metal structure, while pots were placed underneath, over a cart moving at constant speed in the direction perpendicular to the line of acquisition.`
精确度辨析练习：`against / alongside / beside / flush with / in contact with / next to / right against the wall`；`just / slightly / immediately / directly / right above the door`（书 p102）

**（3）PROVIDE SPECIFIC AND PRECISE DETAILS —— 跨学科技术动词（书 pp.102–103）**
`was adapted, was added, was administered, was adopted, was adjusted, was altered, was analysed, was applied, was arranged, was assembled, was assessed, was assumed, was attached, was calculated, was calibrated, was carried out, was characterised, was collected, was combined, was compared, was computed, was conducted, was connected, was constructed, was controlled, was converted, was created, was defined, was derived, was designed, was determined, was discarded, was distributed, was divided, was eliminated, was employed, was estimated, was evaluated, was examined, was excluded, was exposed, was extracted, was fabricated, was filtered, was formulated, was generated, was immersed, was implemented, was included, was incorporated, was initiated, was input, was inserted, was installed, was inverted, was isolated, was located, was maintained, was maximised, was measured, was minimised, was modelled, was modified, was monitored, was normalised, was obtained, was operated, was optimised, was performed, was placed, was plotted, was positioned, was prepared, was processed, was produced, was quantified, was recorded, was recovered, was regulated, was removed, was repeated, was represented, was restricted, was retained, was retrieved, was sampled, was scored, was selected, was separated, was simulated, was solved, was stabilised, was substituted, was synthesised, was tracked, was transferred, was treated, was varied, was utilised`
> 原文把 Methods 动词分三类：① 通用学术研究动词（`attempt, consider, conduct, determine, investigate, report, verify`）→ 见 Appendix B: Research Verbs；② **高度学科专有动词**（`anneal, clone, dissect, ionise, infuse`）——**不收录，因为对其他学科无用**；③ 上表的跨学科技术动词。**跨学科方法描述必须用第三类 + 精确参数，而不是依赖本学科行话**（书 pp.102–103）。

**（4）SEQUENCE LANGUAGE —— 8 组（书 pp.104–106）**
前言要点：精确描述每一步的时间与顺序是让读者与同行评议者能 `visualise` 并复现的前提；`then/next` 只表达顺序，**不表达间隔长短**；序列语言在描述 Results 时同样重要。

| 组 | 功能 | 词块 |
|---|---|---|
| 1 | 实验/模拟开始之前 | `beforehand, earlier, formerly, in advance, originally, previously, prior to, initially` |
| 2 | 开始/第一步 | `at first, at the beginning, at the start, firstly, in the beginning, initially, to begin with, to start with` |
| 3 | 仅表顺序，不含时间信息 | `after, afterwards, earlier, followed by, following, formerly, next, previously, prior to, secondly (etc.), subsequently, then` |
| 4 | 短间隔后 | `quickly, shortly after, soon` |
| 5 | 晚/较晚阶段、较长等待后 | `eventually, in due course, in time, later, later on, subsequently, towards the end` |
| 6 | 同时/同一时段，或一事件恰在另一事件结束时开始（接口处） | `as, as soon as, at once, at that point, at the same time, directly, immediately, instantly, in the meantime, meanwhile, once, simultaneously, straight away, until, when, while` |
| 7 | 序列结束 | `at the end, eventually, finally, in the end, lastly` |
| 8 | 实验/模拟结束后，或观测结果结束后 | `afterwards, eventually, later, later on, subsequently` |

跨组重复项（原书 KEY 如实标注）：`initially`（G1、G2）、`previously/formerly/earlier/prior to`（G1、G3）、`eventually`（G5、G7、G8）、`afterwards`（G3、G8）、`later/later on/subsequently`（G5、G8）。
原句：`The temperature was increased to 49°C and then reduced to 30°C.`｜`The temperature increased to 49°C but soon dropped to 30°C.`｜`The temperature was increased to 49°C and later reduced to 30°C.`｜`The temperature dropped sharply when we reduced the pressure.`｜`At the end there was a noticeable drop in temperature but it was decided afterwards to omit this from the input data.`

**（5）JUSTIFY CHOICES（书 pp.107–108）**
引出理由：`by doing…, we were able to`｜`chosen for/to`｜`designed for/to`｜`for brevity`｜`for convenience`｜`for maximum effect`｜`for (the sake of) simplicity`｜`for the following reasons:`｜`in an attempt to`｜`in order to`｜`offer a means of`｜`our aim was to`｜`provide a way of/to`｜`selected on the basis of`｜`so as to`｜`so/such that`｜`the advantage of`｜`the reason for`｜`thereby`｜`thus`｜`to take advantage of`｜`to this end`｜`which/this allowed`｜`which/this permitted`｜`which meant that`｜`with the aim of`
'happy' words（表达选择优势的褒义词）：`accurate, consistent, direct, easy, excellent, important, precise, relevant, robust, satisfactory, simple, suitable, useful`
Cause & Result 连接词与动词：`achieve, allow, avoid, compensate (for), confirm, determine, enable, enhance, ensure, establish, facilitate, guarantee, improve, include, increase, limit, minimise, obtain, overcome, permit, prevent, provide, reduce, remove, simplify, validate`
原句：`For brevity, these equations are not included in this paper.`｜`To make the problem tractable, we reduced the number of possible scenarios.`｜`A highly conductive filler is added to the matrix in order to ensure electrical conductivity above the required level.`｜`The advantage of using three-dimensional analysis was that the out-of-plane stress field could be obtained.`｜`By partitioning the array, we were able to identify all the multipaths.`｜`The survey was administered during the spring, which avoided problems of low activity during the summer months.`

**（6）INDICATE THAT APPROPRIATE CARE WAS TAKEN（书 pp.108–109）**
`accurately, always, appropriately, at least, both/all, carefully, completely, constantly, correctly, directly, entirely, every/each, exactly, firmly, frequently, freshly, fully, gently, good, identical, immediately, independently, individually, never, only, precisely, randomly, rapidly, reliably, repeatedly, rigorously, separately, smoothly, strictly, successfully, suitably, tightly, thoroughly, uniformly, vigorously`
原句：`Care was taken to maintain strict anaerobic conditions during extract preparation.`｜`These cells were then washed thoroughly at least three times.`｜`To prevent an emulsion from forming, only gentle, repeated inversion was used.`｜`The specimen was tightly clamped at two corners to minimize any unexpected gaps.`｜`6 pristine specimens were handpicked under a microscope.`

**（7）COMPARE WITH / REFER TO MATERIALS/METHODS IN OTHER STUDIES —— Option 1/2/3（书 pp.109–111）**
Option 1（完全相同）：`according to`｜`as described by/in*`｜`as detailed by/in`｜`as explained by/in`｜`as in`｜`as proposed by/in`｜`as reported by/in`｜`as reported previously`｜`as suggested by/in`｜`can be found in`｜`described elsewhere`｜`details are given in`｜`following x et al.`｜`given by/in`｜`identical to`｜`in accordance with`｜`previously shown in/by`｜`the same as that of*/in`｜`using the method of/in`
　\*原文注：**`by` 与 `of` 后接研究者/团队名（`as described by Ross` / `using the method of Ross et al.`），`in` 后接文献（`as described in Ross et al. [2020]`）**。另一做法是直接在句内相应位置给引用：`We used the Shapiro-Wilk test11 to determine whether a given sample was from a normal population.`
Option 2（相似）：`a (modified) version of`｜`adapted from`｜`almost the same as`｜`based on`｜`essentially identical`｜`essentially the same`｜`except for/that`｜`largely the same`｜`more or less identical`｜`partly based on`｜`practically the same`｜`similar (to)`｜`slightly modified`｜`virtually the same`｜`(to) adapt, (to) adjust, (to) alter, (to) change, (to) modify, (to) refine, (to) resemble, (to) revise, (to) vary`｜`in essence`｜`in line with`｜`in principle`｜`with some adjustments / alterations / changes / modifications`
Option 3（显著不同）：`a novel step was…`｜`adapted from`｜`although in many ways similar`｜`although in some ways similar`｜`although similar to`｜`based on`｜`except for/that`｜`instead (of)`｜`loosely based on`｜`partly based on`｜`unlike`｜`with the following modifications:`；对比连接词 `however, whereas, by contrast`
　**原文注**：多数词在 Option 2 与 3 通用；**用 Option 2 时可不说明差异，用 Option 3 时差异重大、应明确说出差异所在，特别是当它改进了该方法时**（书 p110）。
原句：`The method was essentially the same as that previously described elsewhere5 for use in X. tropicalis.`｜`The analytical method was adapted from British Pharmacopeia7.`｜`We modified the Du and Parker filter to address these shortcomings and we refer to this modified filter as the MaxCurve filter.`｜`However, in this study, instead of using a coil around the membrane cell, we placed the coil on top of the cell.`

**（8）INDICATE WHERE PROBLEMS OCCURRED（书 pp.111–112）**
minimise problem（no big deal）：`did not align precisely, immaterial, it is recognised that, less than ideal, minimal, minor deficit, negligible, not identical, not perfect, not significant, only approximate, rather time-consuming, slightly disappointing, slightly problematic, unimportant, (very) small`
minimise responsibility（not my fault）：`as far as possible, impossible, impractical, inevitably, (it was) difficult to, (it was) hard to, limited by, necessarily, not possible, problematic, unavoidable, unworkable`
maximise good aspects：`acceptable, fairly well, quite good, reasonably robust`
refer to a possible solution：`Future work should…` / `Future work will…`
回避/范围划定（Results/Discussion 通用）：`not examined, not explored in this study, not investigated, not possible, not within the scope of this study`
原句：`Despite our routine of monthly examinations, follow-up was not perfect.`｜`It was slightly difficult to deposit a uniform film of the liquid, probably owing to its low viscosity.`｜`Although some duplication was unavoidable, this was minimized by the frequent use of cross references.`｜`The probability is very small, and hence we believe such contaminants have only a negligible effect on this study.`｜`Due to the lack of multiwavelength data it was not possible to apply additional broad-band selections.`

### F. Methods 检查清单（书 pp.136–137 TIPS + 正文规则）

**定位与配比**

- [ ] 查过目标文章中 Methods 的**平均篇幅**，据此确定该类型实验/模拟应有的细节量（书 p136）
- [ ] 查过 Methods 在目标期刊中的**位置**：印刷版正文，还是离线补充材料（书 p136）
- [ ] 正文与补充材料的信息配比与目标文章一致（书 p76）
- [ ] 动笔前先规划整个 Methods 节（书 p136）
- [ ] 没有把实验笔记当成 Methods（书 p136）

**内容**

- [ ] 开头给了总览/参数（试验次数、材料设备、目的），或按目标文章直接从方法/材料写起（书 pp.79–80）
- [ ] 重述了 Introduction 的 aim/gap（书 p88 组件 1）
- [ ] 给了材料/样品/设备的来源（供应商、型号、产地、kind gift 等）（书 p100）
- [ ] 给了精确细节：数量、浓度、温度、时间、压力、软件与版本（书 pp.78、82、97–98）
- [ ] 用精确序列语言（`prior to`、`until`、`at which point`…）而非仅 `then/next`（书 pp.82、104）
- [ ] 每处关键选择都给了 **WHY**（`in order to`、`with the aim of`、`the advantage of`…）（书 pp.81、137）
- [ ] 用 `tightly`、`gently`、`separately`、`directly`、`at least` 等语言体现操作严谨（书 pp.82–83、108–109）
- [ ] 对既有方法给了适度描述 + 引用（`The assay was carried out as in [1]. Briefly, samples were…`）（书 p84）
- [ ] 与既有方法的比较选对了 Option 1/2/3；Option 3 时明确说出差异（书 pp.84、110）
- [ ] 引用位置经检查，没有把他人（或你自己）的工作误记到别人头上（书 pp.84–85）
- [ ] 描述了图/表内容并在 Methods 中恰当引用（书 p88 组件 3）
- [ ] 遇到的问题/局限在 Methods 中首次提及，并在文末呼应（`Future studies should…`）（书 p86）
- [ ] 单位/缩写符合目标期刊最新规定或 SI（如 `mL` 而非 `ml`）（书 p81）

**语言**

- [ ] 已查目标期刊 Guide for Authors：本节主要用主动还是被动（书 p113）
- [ ] 使用 agentless passive 而非 `by us`；并用 `here / in this study / in this work / in our model`、引用、假主语消解归属歧义（书 pp.113–115）
- [ ] 逐句检查时态：Past Simple＝你做了什么；Present Simple＝标准流程/设备（书 pp.114–115、137）
- [ ] 已明确区分"自己的工作 / 他人工作 / 既有知识"（书 p137）
- [ ] 检查动词+介词搭配（仿目标文章 `was …ed + prep` 清单）（书 p118；完整介词规则见 §2.6）
- [ ] 句首介词已尽量替换为意义清晰的词（`From this estimation` → `Using this estimation`）（书 p118）
- [ ] 没有介词短语连缀造成的歧义（书 p120）
- [ ] 冠词经检查（首次提及的单数可数名词用 a/an；泛指复数/不可数用 Ø；`the` 基于"唯一可能/读者已知/显然共享"）（书 pp.124–125；见 §2.5）
- [ ] 对跨学科宽读者群的期刊，关键术语首次出现时用 a/an 并定义或解释（书 p126）
- [ ] 不确定处标注并回查目标文章，而不是凭直觉

## 1.5 Results（结果）

> **页码提示**：本节 §3.1–3.3 的内容在原总结中页码混用 PDF 与书内页（见 Part 5.1），本手册改以**节号 + 书内页区间**标注：§3.1–3.3 = 书 pp.140–158；§3.4（词块库）= 书 pp.169–182；§3.5（certainty continuum）= 书 pp.183–186；TIPS = 书 pp.186–187。已按印张核对的精确页另标（如"项目故事"= 书 p145，"results do not speak for themselves" = 书 p148，模型 = 书 p155）。

### A. 功能定位

Results 不是"写结果"，而是写**结果的导览（a guide to the results）**：用叙事把读者逻辑自然地引向你要得出的结论（书 p148：`results do not speak for themselves`）。

> `In the Results section, explanations tend to be limited to direct explanations of the data; the implications are often mentioned briefly in the Results, but a full discussion of what the results suggest or imply is generally kept for the Discussion.`（书 pp.151–152）
> 目标：让读者最容易"通行（negotiate）"这一节，展示结果与研究目的的关系，并为 Conclusion 铺一条清晰的路（书 p141）。

### B. 通用模型：GENERIC RESULTS MODEL（**4 个段落组 / 11 个组件条目**）

| 组 | 组件（英文原词 + 中文） | 书页 |
|---|---|---|
| **1**（开场与定位） | `REVISITING THE LITERATURE/AIM/PREDICTION/HYPOTHESIS/GAP`（回顾文献/目的/预测/假设/gap） | p155 |
| | `REVISITING/SUMMARISING THE METHOD`（回顾/概括方法） | p155 |
| | `GENERAL STATEMENT ABOUT THE RESULTS`（对结果的一般性陈述） | p155 |
| | `INVITATION TO VIEW GRAPHIC + CONTENT OF GRAPHIC`（邀请看图 + 图形内容） | p155 |
| **2**（核心结果与解释） | `SPECIFIC/KEY RESULTS ± EVALUATIVE LANGUAGE/COMMENTS`（具体/关键结果 ± 评价性语言/评论） | p155 |
| | `COMPARISON WITH RESULTS IN OTHER STUDIES/HAPPY WORDS J`（与其他研究结果比较 + happy words） | p155 |
| | `COMPARISON WITH MODEL/SIMULATION/PREDICTED RESULTS`（与模型/模拟/预测结果比较） | p155 |
| | `EXPLANATION OF RESULTS VIA KNOWN FACTS/METHOD DETAILS`（用已知事实或方法细节解释结果） | p155 |
| **3**（问题） | `PROBLEMS/ISSUES WITH RESULTS ± REASONS`（结果的问题/议题 ± 原因） | p155 |
| **4**（启示） | `POSSIBLE IMPLICATIONS OF RESULTS/HAPPY WORDS J`（结果的启示 + happy words） | p155 |

> **计数口径**：4 个编号段落组；组件行按原文计数为 11 条（第 1 组 4 条 + 第 2 组 4 条 + 第 3 组 1 条 + 第 4 组 1 条，另第 3 组附注 `focus on a solution or a reason` 见书 p151 词块表）。
> **附带的职业收益**：按当前结构模型投稿，`identifies you as a researcher who is up to date with the literature`（书 p155）。
> **模型要整合**：把通用模型与自建清单整合；例如目标期刊 Methods 仅在补充材料时，可能需要在 Results 开头给出**大段方法综述**；目标期刊要求 **Research in Context** 栏目专门承载与他研究的比较（书 pp.154–155）。

**示例 Results 的 12 句功能（建模示范，书 pp.144–152）**

| 句 | 功能（原文表述） |
|---|---|
| 1–2 | the writer **repeats/revisits the methods and findings of studies mentioned earlier in the article**（重述前文已提及研究的方法与发现） |
| 3–4 | the writer **briefly summarises the method used in this study**（简述本研究方法） |
| 5 | the writer **invites the reader to look at a Results graphic**（邀请读者看图） |
| 6–7 | the writer **compares the results with those in other studies, using subjective, evaluative language**（用主观评价性语言与他研究比较） |
| 8 | the writer **directs the reader's attention to a specific result, describing it with strongly evaluative language**（把注意力引向具体结果，用强评价性语言） |
| 9 | the writer **selects a specific result to present in more detail, and comments on it**（选出具体结果详述并评论） |
| 10 | the writer **mentions a possible implication of the results**（提及可能启示） |
| 11 | the writer **mentions a possible limitation, minimising its potential impact on the results**（提及可能局限，弱化其影响） |
| 12 | the writer **focuses the reader's attention away from the problem and towards the positive value of the study**（把注意力从问题转向研究正面价值） |

### C. 内容边界

**原文的立场**：反对僵化的规定性建议。成功发表的论文"并不总是、甚至常常不"遵守下列常见规条（Results 不得有任何解释、只能用过去时、不得重复段落结构、Results 只谈结果是什么而 Discussion 只谈含义）。因此以下边界是**倾向性（tendency）而非禁令**（书 p142）。

| # | 边界 | 原文依据 |
|---|---|---|
| 1 | **完整的解释、含义与启示讨论不属于 Results**；解释限于对数据的直接解释，启示只可**简短提及**，完整讨论留给 Discussion | 书 pp.151–152 |
| 2 | 但**几乎所有作者都会在 Results 里对含义给出某种指示**（常用 `suggest`/`indicate`，作用是打开通往 Discussion 的路径） | 书 p153 |
| 3 | **问题/局限不能在 Discussion 才第一次出现**：`it isn't appropriate to mention them for the first time when you are discussing suggestions for future work in the Discussion/Conclusion.`（即 Results 里就要承认数据问题） | 书 p152 |
| 4 | 大段方法细节一般不属于 Results；**但 Methods 很长或只在 Supplementary Materials 时例外** | 书 p145 |
| 5 | **单纯复述图形内容"没有为读者增加任何东西"**：`if you simply describe what is in the graphic, you have not added anything to what the reader can already see, so why bother?` | 书 p149 |
| 6 | **与文献的完整"定位/映射"（positioning on the research map）属于 Discussion**；Results 中与文献比较只是先把结果放到已有结果旁边 | 书 p148 |
| 7 | **不要按时间顺序讲项目故事**：`The aim of a paper is not to tell the story of your project in the order it occurred.`（书 p145） | 书 p145 |
| 8 | **不能全都详述**：`your job is to provide a guide to the results, not simply a description of the results.` 全详述会使结果看似同等重要 | 书 p151 |

**必须做（内容要求）**

1. **图文分工**：`results do not speak for themselves`；图形的**位置（location）与包住它的叙述（framing narrative）同样重要**（书 p147–148）。读者读到 `As can be seen in Fig. 3.1, ...` 时会停下来看图、自行解释、再带着解释回到文本。
2. **先图还是先评论**（书 p147）：数据视觉上非常清晰无歧义 → 可在节首先给总结性图形；图形可被多于一种方式解读 → **最好先评论数据再邀请读者看图**，否则读者可能做出与你不同的解读。
3. **评价性语言是必需的**：同一对曲线，写 `the two curves are very similar` 读者就注意相似，写 `the two curves are significantly different` 读者就注意差异；只写 `the effect occurred in 23% of cases` 而无评价语，读者可能自行判断 23% 很低（书 pp.148–149）。
4. **开篇的几种成功做法**（书 pp.145–146）：① 以总体趋势的概括陈述开头（`In most cases` / `In general` / `Overall`），可能同时指向总结性图表——`sees the 'wall' before you — and they — look at the individual 'bricks'`；② **重述研究目的**（看完结果后甚至可回到 Introduction 重新定义/改写 aim）；③ **回顾方法要点**（Methods 只在补充材料时尤其常见，也照顾从 Title 直接跳到 Results 的读者）。
5. **分小节的连接**：用一句 linking statement 引入每一组结果（书 p146）。
6. **解释"为什么"的两种来源**：解释结果**如何获得**可能含方法细节；解释**为何发生**可能含所研究材料的性质信息（书 p151）。
7. **承认问题并弱化**：除非确定问题既不重要又不可见，否则不要忽略；常见做法是提及它、尽量弱化其重要性、并给出原因或解决方案。收益：不提及会显得你并不完全理解自己的研究；提及显示你**掌控自己的研究并能清晰评估**，并为 Discussion/Conclusion 提供 future research directions（书 pp.152–153）。发表节奏：`Lab-to-journal speed is critical.`（书 p152）

### D. 时态与语态规则

**模型附注（书 p155）**

| 内容 | 时态 |
|---|---|
| 描述**图形中可见内容** | **Present Simple** |
| 描述**图形信息如何获得** | **Past Simple** |
| 解释结果的**背景事实**（如材料性质）：`This occurred because material X is able to…` | **Present Simple** |
| 涉及**方法**的"为什么"：`This occurred because we used a…` | **Past Simple** |
| 结果传达作者对**永久价值/永久真理性**的信心 | Past Simple 报告"作者发现了什么"；Present Simple 反映"该发现可靠到足以构成永久真理"这一信念 |
| 描述模型如何"运行"（how a model 'runs'） | 可**全节用 Present Simple**（查目标文章） |

**原文对照（书 p156）**

- `We found that sunbathing was related to cancer.` —— Past Simple 只是描述**本研究中**的发现，发现与该研究绑定，**不作为普遍接受或既定真理**呈现。
- `We found that sunbathing is related to cancer.` —— Present Simple 反映作者相信该发现**可靠到足以构成永久真理**。

**时态随时间漂移**：`The verb tense may change as time passes and knowledge and information develop.` 五年前论文里的 `X has been found to occur4`，现在可能写作 `X occurs4` 甚至直接 `X occurs`（书 p180）。

### E. 词块库（3.4 Language for the Results section，书 pp.169–182）

> 来源：`over 2,500 published research articles`；只收录高频、被作者与编辑视为正常可接受的词与短语（书 p169）。

**（1）INVITATION TO VIEW RESULTS（书 pp.169–171）**
介词短语框架：`according to the data in Fig. 1,`｜`as can be seen from/in* Fig. 1,`｜`based on (data in) Fig. 1,`｜`can be found in Fig. 1`｜`can be identified from/in Fig. 1`｜`can be observed in Fig. 1`｜`can be seen from/in Fig. 1`｜`(close) inspection of Figure 1 indicates`｜`data in Fig. 1 suggest that`｜`(data not shown)`｜`evidence for this is in Fig. 1`｜`(Fig. 1)`｜`in/from Fig. 1 (it can be seen that)`｜`in Fig. 1 we (compare etc.)`｜`is/are apparent from/in Fig. 1`｜`is/are clearly visible in Fig. 1`｜`is/are evident in the figure`｜`is/are given in Fig. 1`｜`is/are shown in Fig. 1`｜`is/are visible in Fig. 1`｜`results are given in Fig. 1`｜`(see Fig. 1)`｜`we observe from/in Fig. 1 that`
动词 + Fig. 1：`contains`, `demonstrates`, `displays`, `illustrates`, `lists`, `plots`, `presents`, `represents`, `reveals`, `shows`, `summarises`
**★ 关键注释**：*from* 表示可从图形数据中**理解/推断**出；*in* 表示**确实出现在/可见于**图形本身（书 p170）。
原句：`As is apparent from Fig. 1, the extractibility of the dehydroisoandrosterone did not change significantly.`｜`The data in Fig. 18 reveal that H3K36 can repair damaged DNA.`｜`The coefficients given in Table 1 represent mean values from both spectrophotometers.`｜`ZnO thin-film islands which cover the substrate surface can be observed in Fig. 3a.`｜`The lack of correlation between IR and PLFA patterns can be seen by comparing Figs 1 and 5.`

**（2）OBJECTIVE DESCRIPTIONS OF RESULTS（书 pp.171–172）**
系动词/被动式：`is/was absent`, `is/was constant`, `is/was different`, `is/was equal`, `is/was higher, etc.`, `is/was highest, etc.`, `is/was identical`, `is/was obtained`, `is/was present`, `is/was seen`, `is/was unchanged`, `is/was uniform`
实义动词：`change/d`, `decline/d`, `decrease/d`, `delay/ed`, `drop/ped`, `exceed/ed`, `exhibit/ed`, `exist/ed`, `expand/ed`, `fall/fell`, `find/found`, `increase/d`, `match/ed`, `occur/red`, `peak/ed`, `precede/d`, `prevent/ed`, `produce/d`, `reduce/d`, `remain/ed`, `resume/d`, `rise/rose`, `take/took place`, `vary/varied`
原句：`Protein expression peaked at day 3 after infection.`｜`The frequencies of the jets were constant, and did not change linearly with velocity.`｜`It was observed that the female rats exhibited higher levels of plasma corticosterone than male rats.`｜`Mean SAOC values rose to 682 moI/L within the first hour.`

**（3）SUBJECTIVE DESCRIPTIONS —— general comments（书 pp.172–173）**
形容词/副词：`abrupt`, `acceptable`, `adequate`, `appropriate`, `brief`, `broadly`, `by and large`, `clear`, `comparable`, `comparatively`, `consistent`, `distinct`, `dramatic`, `effectively`, `equivalent`, `essentially`, `excessive`, `extensive`, `generally`, `gradual`, `important`, `in general`, `in principle`, `in the main`, `inadequate`, `likelihood`, `mainly`, `major`, `measurable`, `merely`, `minor`, `more or less`, `obvious`, `perceptible`, `poor`, `powerful`, `profound`, `pronounced`, `predominant/ly`, `rapid`, `reasonable`, `remarkable`, `serious`, `severe`, `sharp`, `similar`, `steep`, `striking`, `strong/ly`, `subtle`, `sudden`, `sufficient`, `suitable`, `unexpected`, `unlikely`, `unremarkable`, `unusual`, `virtually`, `weak/ly`
Useful verbs：`emphasise`, `highlight`, `reflect`, `resemble`
句首评论语：`Importantly,`, `In fact,`, `Indeed,`, `Interestingly,`, `Intriguingly,`, `It is noteworthy that...`, `Notably,`, `Overall,`, `Significantly,`, `Surprisingly,`
**★ 客观 vs 主观判据**：`higher` 是**客观**的真/假判断，而 `high` 是**主观**的量级评估（书 p172）。

**（4）SUBJECTIVE DESCRIPTIONS —— comments about quantities（5 组，书 pp.172–174）**

| 组 | 功能 | 示例句 | 词块 |
|---|---|---|---|
| 1 | 放大 size/quantity | `A considerable amount of residue remained in the pipe.` | `a great deal (of)`, `a number (of)`, `abundant`, `appreciable`, `as many as`, `at least`, `considerable`, `greater (than)`, `high`, `large`, `marked`, `more (than)`, `most`, `much`, `noticeable`, `numerous`, `over (half/25%)`, `plenty of`, `quite a few`, `quite a lot`, `several`, `significant`, `substantial`, `upwards of` |
| 2 | 缩小 size/quantity | `Barely 74% of the residue remained in the pipe.` | `a few`, `a little`, `as few as`, `barely`, `below`, `few`, `fewer (than)`, `hardly`, `just`, `less`, `little`, `low`, `marginal`, `minimal`, `minor`, `modest`, `only`, `scarcely`, `slight`, `small`, `under` |
| 3 | 强调大小/高低程度 | `The amount that remained in the pipe was even higher/even lower than predicted.` | `appreciably`, `considerably`, `easily (over/under)`, `even (higher/lower)`, `exceptionally`, `extremely`, `far (more/less)`, `markedly`, `much (higher/lower)`, `noticeably`, `particularly`, `remarkably`, `significantly`, `so (high/low)`, `substantially`, `very`, `well (over/under)` |
| 4 | 相近/接近 | `Almost half of the residue remained in the pipe.` | `approximately`, `close (to)`, `few (i.e. close to none)`, `imperceptible`, `just (over/under)`, `little (i.e. close to none)`, `minimal`, `near/ly`, `negligible`, `practically`, `roughly`, `slightly (more/less)`, `virtually` |
| 5 | 不解读大小，用于回避判断 | `Some of the residue remained in the pipe.` | `fairly`, `in some cases`, `moderate`, `quite (high/low)`, `rather (high/low)`, `reasonably`, `relatively`, `some`, `somewhat`, `to some extent` |

（完整待分组词表另含 `a great deal (of)`, `appreciably`, `approximately`, `at least`, `below`, `close (to)`, `considerably`, `easily (over/under)`, `even (higher/lower)`, `exceptionally`, `extremely`, `fairly`, `far (more/less)`, `fewer (than)`, `greater (than)`, `hardly`, `imperceptible`, `in some cases`, `just*`, `little`, `low`, `marginal`, `marked`, `markedly`, `minimal*`, `minor`, `moderate`, `modest`, `much*`, `near/ly`, `noticeable`, `noticeably`, `numerous`, `only`, `over (half/25%)`, `particularly`, `plenty of`, `practically`, `quite a few`, `quite a lot`, `rather (high/low)`, `reasonably`, `relatively`, `remarkably`, `roughly`, `scarcely`, `several`, `significant`, `significantly`, `slight`, `slightly (more/less)`, `small`, `so (high/low)`, `some`, `somewhat`, `substantial`, `substantially`, `to some extent`, `under`, `upwards of`, `very`, `virtually`, `well (over/under)`；带 `*` 者出现在两个组。）—— 书 p173

**（5）'happy' words J（书 p175）**
`accurate`, `advantageous`, `beneficial`, `better`, `effective`, `efficient`, `excellent`, `feasible`, `improve`, `precise`, `reliable`, `satisfactory`, `simple`, `successful`, `superior`, `useful`, `valuable`, `viable`, `worthwhile`
（原文另处提到 'happy words' 清单见书 pp.51, 107, 175, 225, 294。）

**（6）comments about frequency —— 10 级频率（书 pp.175–177）**

| 级别 | 含义提示 | 词块 |
|---|---|---|
| 1 | 每次/毫无例外 | `each/every time`, `without exception`, `on each/every occasion`, `always`, `invariably` |
| 2 | 通常/照例 | `habitually`, `as a rule`, `generally`, `normally`, `usually` |
| 3 | 经常/频繁 | `regularly`, `repeatedly`, `frequently`, `often`, `commonly` |
| 4 | 多半 | `more often than not` |
| 5 | 一半一半（中性） | `as often as not` |
| 6 | 有时 | `sometimes`, `on some occasions`, `at times` |
| 7 | 偶尔 | `occasionally`, `now and then`, `from time to time` |
| 8 | 很少 | `infrequently`, `rarely`, `seldom` |
| 9 | 几乎从不 | `hardly ever`, `barely ever`, `almost never`, `scarcely ever` |
| 10 | 从不 | `on no occasion`, `not once`, `at no time`, `never` |

**频率判断是主观的**（书 p176）：同一 22% 的发生率，若既有研究认为该结果**不太可能**发生，你可呈现为 frequent occurrence；若既有研究认为**很可能**发生，你可呈现为 rare occurrence。若只写 `x occurred` 而**不加频率修饰**，读者可能无法恰当评价结果（书 p175–176）。
原句：`Minor clinical abnormalities of nerve function were fairly common in the rheumatoid group.`｜`In several cases the chromaticity of exposed skin was noticeably different from that of unexposed skin.`｜`These abnormalities were invariably preceded by symptoms of toxicity.`｜`There was a striking difference in the image contrast between the gradient echo image and the spin echo image.`

**（7）COMPARISON WITH RESULTS IN OTHER RESEARCH / MODELLED / PREDICTED（书 pp.179–180）**
短语/形容词性框架：`as expected,`, `better than`, `broadly similar to`, `comparable to`, `comparatively (low/high etc.)`, `consistent with`, `contrary to`, `(effectively) the same as`, `(essentially) identical`, `in accordance with`, `in (good) agreement with`, `in contradiction to`, `in contrast to`, `in line with`, `much the same as`, `not dissimilar`, `not unlike`, `relative to`, `similar`, `unlike`, `well known`
Verbs：`accord with`, `align with`, `compare well with`, `confirm`, `contradict`, `correlate with`, `corroborate`, `deviate from`, `differ`, `disprove`, `mirror`, `prove`, `refute`, `reinforce`, `resemble`, `substantiate`, `support`, `validate`, `verify`
原句：`These data appear to confirm the prevalence of Vitamin D deficiency in the normal population.`｜`Our results differ from those in the literature, and agree better with published CDF data.`｜`These new results are consistent with, and substantially more sensitive than, previously published anisotropy measurements.`｜`The accumulation rates we observed are in line with those reported from sulfate incorporation methods.`

**（8）PROBLEM/S and ISSUE/S（书 pp.180–182）**
minimise problem（no big deal）：`acceptable`, `did not align precisely`, `immaterial`, `insignificant`, `less than ideal`, `less than perfect`, `marginal/ly`, `minimise`, `minor deficit`, `negligible effect`, `non-ideal/not ideal`, `not complete`, `not identical`, `not perfect`, `not significant`, `of no consequence`, `of no significance`, `reasonable`, `slightly (disappointing)`, `(some) imperfection/s`, `somewhat (problematic)`, `technicality`, `unimportant`
minimise responsibility（not my fault）：`as far as possible`, `difficult to (simulate)`, `hard to (control)`, `impossible`, `impractical`, `inevitable/ly`, `(it was) difficult to`, `(it was) hard to`, `limited by`, `necessarily`, `unavoidable`, `unpredictable`, `unreachable`, `unworkable`
maximise good aspects：`despite this`, `fairly well`, `nevertheless`, `quite good`, `reasonably robust`
…and focus on a solution or a reason：`future work should...`, `future work will…`, `further work is required`, `(is) currently in progress`, `(is) currently underway`, `[this] was because…`
回避/范围划定：`not examined`, `not explored in this study`, `not investigated`, `not possible`, `not within the scope of this study`；其他：`unexpected`, `unfortunately`
原句：`Inevitably, considerable computation was involved.`｜`Unfortunately, it was not possible to quantify the extent of Zn loss from the experimental charges.`｜`Although centrifugation could not remove all the excess solid drug, the amount remaining was negligible.`｜`While the anode layer was slightly thicker than 13 μm, this was a minor deficit.`｜`Future work should therefore include numerical diffusion effects in the calculation of permeability.`｜`This type of control saturation is fairly common and therefore of no significance.`

**（9）IMPLICATIONS AND EXPLANATIONS OF RESULTS（书 p182）**
（风险/可能性）形容词与副词：`likely`, `perhaps`, `possible`, `presumably`, `probably`, `unlikely`, `apparently,`, `evidently,`, `in part due to…`
Verbs：`deduce`, `imply`, `indicate`, `infer`, `mean`, `signify`, `suggest`
句型：`could* be explained by`｜`could* be interpreted as`｜`could* be seen as`｜`it appears that…`｜`it could* be inferred that…`｜`it is [fairly/abundantly] evident that…`｜`it is [very/highly] probable/likely that…`｜`it is logical that…`｜`it is thought/believed that…`｜`it may (well) be that…`｜`it may be concluded that…`｜`it may/can be assumed that…`｜`it seems (very/highly) probable/likely that…`｜`it seems that…`｜`it would seem/appear that…`｜`the evidence suggests that…`｜`there is evidence to indicate that…`｜`this implies/seems to imply/may imply that…`｜`this is (compelling) evidence for…`｜`this is indicative of…`｜`this seems to suggest that…`｜`we have confidence that…`｜`we propose that…`
★ 注释：`could` 可替换为 `may` 或 `might`，有时可用 `can`（情态动词系统用法见 §2.3）。
**转向正面价值的示例句**：`Nevertheless, the data obtained here suggest that using a portable emissions measurement system to measure BC and NO2 exposures hourly may provide more accurate information for traffic management strategies than traditional on-site measurement.`（书 p153）

### F. Results 检查清单

**原文 TIPS（书 pp.186–187，逐条照录）**

- [ ] Check the format of Results sections in your target articles in terms of **length, subsections and subtitles**
- [ ] Check **where the Methods section normally appears** in your target journal, and how this impacts the content of the Results section
- [ ] **Plan the structure of the entire Results section before you start creating whole sentences**：presentation order、subsections and headings、location of graphics
- [ ] **Review the Introduction after you have obtained your results** to ensure that the aim as stated matches the outcome
- [ ] Remember that many readers will move **directly from the title or Abstract to the Results** → include enough information for the Results to function as a **standalone section**
- [ ] Remember that **data and results do not speak for themselves**
- [ ] Check the **amount of commenting/evaluative language** in the Results sections of your target articles
- [ ] **Decide where your results and the implications of your results fit on the certainty continuum**（见 §2.2）

**由正文规则汇总的补充检查项**

- [ ] 结果与 aim 清晰相连；必要时回 Introduction 重写 aim（书 p146）
- [ ] 开篇用了一般性陈述 / 重述目的 / 回顾方法之一提供平滑过渡（书 pp.145–146）
- [ ] 先给读者"墙"再看"砖"：以 `In most cases` / `In general` / `Overall` 建立框架（书 pp.145–146）
- [ ] 每组结果前有 linking statement（书 p146）
- [ ] 图形顺序/位置与目标文章一致，且图形前后有叙述框住（书 pp.146–147）
- [ ] 可多解解读的图形已先加评论再邀请看图（书 p147）
- [ ] 对关键结果用了评价性语言与句首评论语（书 pp.149–151）
- [ ] 只详述重要结果，避免所有结果看来同等重要（书 p151）
- [ ] 报告数值时提供了评价性/频率/数量修饰（`only 23 ml` / `in as many as 23% of cases` / `often`）（书 pp.148、175–177）
- [ ] 承认了结果中的问题/局限并弱化影响，或给出原因/解决方向；未把问题第一次留到 Discussion（书 pp.152–153）
- [ ] 结尾以 `suggest` / `indicate` 打开通往 Discussion 的路径，并以 `more accurate` 一类 happy words 呼应 Introduction/Abstract 的目的（书 p153）
- [ ] 时态恰当：图形可见内容 Present Simple ↔ 获得方式 Past Simple（书 p155）
- [ ] 核查了小节数量、长度、段落功能、标题长度与是否为完整句（书 p156）
- [ ] 因果动词准确反映因果方向与强度；注意 `a/the cause of` 与 `results from/results in` 的差别（书 p155；见 §2.2）
- [ ] 每条陈述都在 certainty continuum 上定位，并用相应语言（含 risk-reducers）表达（书 pp.183–186）
- [ ] 因 Methods 在补充材料而在 Results 开头补足方法综述；目标期刊是否要求 Research in Context 栏目（书 pp.154–155）

## 1.6 Discussion（讨论）

### A. 功能定位

Discussion 的核心是**把讨论包进一条"叙事包裹"（narrative wrap）**：把读者"耐心地、符合逻辑地、显式地"从结果带到结论（书 p191）。

> `The key to a successful Discussion section is a forward-moving, well-organised narrative wrap … that leads the reader patiently, logically and explicitly from the results to the conclusions.`（书 p191）
> `Saying what your results are is the central function of the Results section; going on to talk about or explore what they mean is the central function of the Discussion.`（书 p203）
> 与 Introduction 构成**镜像（symmetrical / mirror）结构**（书 pp.192–194）：

| Introduction 的块 | Discussion 中对应做的工作 |
|---|---|
| Block 4 DESCRIBE THE PRESENT PAPER | 常从"回顾研究目的/空白或关键结果"开始，反向建立一个"接口"，把文章推离正文核心区 |
| Block 3 LOCATE A GAP | 说明本研究在多大程度上回应了该空白或解决了该问题 |
| Block 2 研究地图（research map） | 把本研究定位到该地图上（positioning） |
| Block 1 重要性与背景（进入文章的"接口"） | 结尾处再建一个"接口"，让读者带着关键信息**走出**文章，进入真实世界/研究界 |

（镜像图：THE FIELD/TOPIC ←→ YOUR CONTRIBUTION TO THE FIELD/TOPIC；EXISTING RESEARCH/KNOWLEDGE ←→ MAP YOUR STUDY TO EXISTING RESEARCH/KNOWLEDGE；GAP ←→ YOUR RESPONSE TO GAP；YOUR PAPER/STUDY ←→ REVISIT YOUR PAPER/STUDY。）

**审稿风险点（原文明确）**：`If the language you use to discuss the meaning of your results does not match or reflect the power of the results this is likely to be a point of criticism at the peer-review stage.`（书 p203）；同时 `it is equally important not to underplay the implications of your work just to be on the safe side`（书 p203）。

### B. 通用模型：GENERIC DISCUSSION MODEL（**9 个组件**）

| # | 组件（英文原词 + 中文） | 书页 |
|---|---|---|
| 1 | **ANNOUNCE THE STRUCTURE OR CONTENT OF THE DISCUSSION SECTION**（宣告本节结构或内容） | p208 |
| 2 | **STATE THE ACHIEVEMENT/CONTRIBUTION OF THE STUDY\***（陈述研究的成就/贡献） | p208 |
| 3 | **REVISIT BACKGROUND INFORMATION/LITERATURE TO 'REBOOT' READER**（回顾背景信息/文献以"重启"读者） | p208 |
| 4 | **REVISIT GAP/AIM/METHOD**（回顾空白/目的/方法） | p208 |
| 5 | **REVISIT RESULTS AND EXPLORE THEIR IMPLICATIONS**（回顾结果并探究其含义） | p208 |
| 6 | **MAP TO LITERATURE/KNOWLEDGE FOR COMPARISON/SUPPORT**（映射到文献/知识以作比较或支撑） | p208 |
| 7 | **IDENTIFY POTENTIAL LIMITATIONS AND SUGGESTIONS FOR FUTURE WORK**（指出潜在局限与未来工作建议） | p208 |
| 8 | **RESTATE THE ACHIEVEMENT/CONTRIBUTION/IMPACT OF THE STUDY**（重述成就/贡献/影响） | p208 |
| 9 | **IDENTIFY POTENTIAL APPLICATIONS**（指出潜在应用） | p208 |

> \*原文注释：**ACHIEVEMENT/CONTRIBUTION 是最"自由流动"的组件**——在本模型中同时出现在开头与结尾；在别的文章里也可能贯穿整节：`The ACHIEVEMENT/CONTRIBUTION of the study is the most free-flowing component — in some cases it occurs both at the start and at the end, as in this model; in others it occurs throughout the Discussion.`（书 p208）
> 顺序规律：排在上面的组件倾向出现在 Discussion 前部，排在下面的倾向出现在后部或末尾（书 p207）；组件顺序灵活，但组件本身相对明确，并遵循研究论文的对称"形状"（书 p192）。

**相关概念区分（书 p208）**

- **achievement 是对内的**：成功解决了 Introduction 中提出的具体研究问题（例：目的是 identify 某物，identify 它就是 achievement）。
- **contribution 是对外的**：研究在应用或知识层面如何影响真实世界/研究世界。`The contribution is more outward-facing, essentially how the study affects the real or research world in terms of applications or knowledge.`
- **用词一致性**：成就表述应**复用 Introduction 中的同一个动词**（不要换成 find、detect）；回顾前文时也不要为"风格"改写语言——重复相同词语反而有利，因为"创造成回声（echo）"（书 pp.208、222）。

**Discussion 开头的两种做法（书 pp.196–197）**

1. **点明研究的成就、贡献或潜在应用**——建立"主题框架（thematic framework）"，回应读者选择性阅读时的核心疑问：`What exactly did this study manage to achieve?` / `How does this study affect my own research?` / 跨学科读者更实际的 `What are the potential applications of these findings?`
2. **'Rebooting' the reader**——回顾：revisiting relevant background factual information；revisiting the gap in the literature or the aim of the study；revisiting key features of results or methods。
> 选择依据由**控制性叙事**与"主要贡献是什么"决定：贡献是改进了既有方法 → 从回顾该方法困难或新方法优势开始；成就是结果更准确/揭示新信息 → 从回顾结果开始；贡献是回应 Introduction 的空白 → 从回顾该空白开始。建议**使用与被回顾部分相似的句子**制造"回声"（书 p197）。
> 以"本节将讨论什么"总述开头**并不常见**（书 p196）。

### C. 内容边界

**与前节的边界**

1. 与 Results 存在"相当大的重叠"（considerable overlap）：**几乎所有 Discussion 都会重复或概括关键结果**，用以"锚定（anchor）"解释与启示（书 p203）。
2. 但 **仅重复/改写关键结果是不够的**：`repeating or even re-wording key results is not sufficient; the Discussion should move on from the Results.`（书 p202）
3. Results 说明"结果是什么"；Discussion 说明"结果意味着什么"，以及它们与 Introduction 中原始问题/假设/目标的关系（书 p203）。
4. 处理"该不该重复"的两难，用**逆向工程**取代主观纠结——看成功发表的文章实际怎么做（书 p203）。
5. **映射（mapping）是 Discussion 的中心功能**：`Mapping the study onto the existing literature and knowledge identifies where your 'product' sits in the research 'market'.`（书 p198）三类典型关系：方法更快 → 可能影响既有方法的地位与应用；**confirm** 他人结果 → 验证该研究；**contradict** 他人结果 → 对该结果提出疑问，并可能为研究设定新方向。

**必须做**

1. **显式认领价值**：`The achievement and contribution may overlap or be identical, and some studies have no easily identifiable impact or applications; nevertheless, there should be an explicit and consistent take-home message about the value of the study.`（书 p315）
2. **引用须可被读者追责**：`Every citation should be relevant, and its relevance should be made explicit to the reader via the narrative.`（书 p198）可通过**平均目标文章 Discussion 的引用条数**获得本领域常规值，同时关注每条引用的功能、位置、重复频次（书 p198）。
3. **首次引用许可**：若某引用谈论的是**另一项研究对数据的解释**或**另一项研究中讨论的应用**，则它与 Discussion 高度相关，**可以在 Discussion 中首次出现**（书 p201）。
4. **applications 可放结尾也可放开头**：结尾是常规位置，但"有一种日益增长的趋势：在 Discussion 开头就陈述主要贡献或应用"；若潜在应用本身就是主要贡献或本节核心主题，更有理由前置（书 p204）。
5. **没有明显应用时的查找路径**：查目标文章**以及自己**的 Introduction（常提到这类研究可被如何使用）；查目标文章的 Discussion/Conclusion（常含对未来应用的推测）。原文也提醒某些研究"在当前阶段、甚至永远"不会有明确应用（书 p205）。
6. **未来工作要"指定方向"**（书 p206）：三大好处——给研究者一个**理性、界定清晰**的项目（比模糊建议更可能被执行）；鼓励与你的研究形成**直接延续**（后续研究引用你的论文，提升地位）；回应你遇到的困难/局限的研究，可能为你的当前与后续工作提供有用数据。

**limitations 的位置规则（书 pp.205–206、216）**

- **默认位置**：多数局限源自研究过程中遇到的问题，通常在**相应小节中首次提及**。
- **允许在 Discussion 首次提及的两种例外**：① 该局限并非正式的、有意设计的数据收集步骤的一部分，也未被当作结果呈现（如 anecdotal evidence），且它与未来研究建议相连时；② 你因为"需要进一步工作"而难以对结论下定论时的局限——这类局限可在 Discussion 提及，并与"邀请研究界继续推进"相连。
- 语气：应链接到未来工作/邀请，而不是简单罗列。
- 示范句：`Some questions remain… However, this was not addressed formally during the study.`；`Within the limitations of this study (confined range of applied heat treatments, OM investigations, etc.)…`（书 p210）
- 也应在 Discussion 中处理 **challenges / discrepancies**，并注意其位置与用语（书 p242）。

**语言警戒线**

- `further work is planned / future work will / is being investigated / work is (currently) underway / work is in progress` 表示**作者自己正在做**，**不是**给别人的建议，也不是对他人的邀请（书 p225）。
- **情态动词的误用/不一致/随意选择会使 take-home message 含糊**：`Incorrect, inconsistent, indiscriminate or careless choices make the take-home message of the study unclear or ambiguous at this crucial point.`（书 p231）
- `to our knowledge` 与"最大/首次"类断言：投稿前必须用多种关键词尽可能彻底检索，`it is unprofessional to make a mistake in a sentence like this`；若投稿/评审/返修期间出现同类研究，"don't panic"，只需 review and clarify 异同以分离出本研究的贡献（书 p195）。

### D. 时态与语态规则

| 内容 | 时态 | 书页 |
|---|---|---|
| 背景事实信息（Present Simple） | **Present Simple**——4.6 清单专门统计其**数量与位置** | pp.201、242 |
| 回顾结果并评论 | Past Simple 或 Present Simple 皆可，**是选择而非事件时间** | pp.202–204 |
| Present Simple 的语义 | 传达作者对该陈述的**永久价值/永久真理性**的信心；Past Simple 把结果绑定到该项研究本身 | pp.201、204 |
| 三句对照 | `A key finding was that some post-V2D health issues appeared to be age-related…` / `…appear to be…` / `A key finding is that…appear to be…` | p204 |
| **重要例外** | 多数写法惯例可由目标文章决定，但**这一项"无法真正通过查阅目标文章解决"**——需作者自行判断数据是否牢固到足以支撑 Present Simple 陈述 | p202 |
| 缓冲 | 即使使用 Present Simple，也可加入降低承诺度的缓冲词（disclaimers），如 `often present with a closely-related symptom` | p202 |
| 情态动词 | 用于表达可能的解释、潜在应用、显而易见的解读、推荐的未来工作方向、很可能的含义（全套见 §2.3）；**不要只为保险而用 may/might/could**，结果支持解释时升级为 `highly likely / probable / almost certain` | pp.230–231、235 |
| 反向工程动作 | 在目标文章 Discussion 中标出动词/时态并自问：`Does the verb tense seem to 'match' the power of the results?` | p204 |

### E. 词块库（4.4 Language for the Discussion section，书 pp.221–228）

> 说明（书 p221）：清单基于 **2,500+ 篇**不同学科论文；**部分组件的语言在前面单元已出现**，原文给出交叉索引：
> ANNOUNCE STRUCTURE OR CONTENT → **Unit 1**；[REVISIT] LITERATURE → **Unit 1**；[REVISIT] GAP/AIM → **Unit 1**；[SUMMARISE/REVISIT] KEY FEATURES OF RESULTS/METHOD → **Units 2 与 3**；RESULTS + EXPLANATION → **Unit 3**；RESULTS + INTERPRETATION/IMPLICATION → **Unit 3**；LIMITATIONS → **Units 2 与 3**。
> **首次出现在 Discussion 的五个组件**（书 pp.221–222）：1 MAP TO LITERATURE/KNOWLEDGE；2 REFINE/EXPLORE IMPLICATIONS；3 ACHIEVEMENT/CONTRIBUTION TO LITERATURE/KNOWLEDGE；4 CURRENT AND FUTURE WORK；5 APPLICATIONS/USE/APPLICABILITY/IMPLEMENTATION。

**（1）MAP TO LITERATURE/KNOWLEDGE（书 pp.222–223）**
形容词/介词框架：`an alternative scheme/strategy`｜`analogous to`｜`comparable to`｜`consistent with`｜`contrary to`｜`distinct from`｜`entirely different`｜`equivalent to`｜`except for`｜`fundamentally the same as`｜`identical to`｜`in accordance with`｜`in agreement with`｜`in conflict with`｜`in contrast to`｜`in good agreement (with)`｜`in line with`｜`new/novel`｜`previously described/reported/suggested`｜`rather than`｜`recently`｜`significantly different (to/from)`｜`similar`｜`the first time/first of its kind`｜`to the best of our knowledge`｜`unlike`｜`shed new light on`
动词（主语常为 This study / These results）：`challenge`｜`compare well (with)`｜`complement`｜`confirm`｜`conflict (with)`｜`contradict`｜`correspond to`｜`corroborate`｜`differ from`｜`disprove`｜`expand`｜`extend`｜`improve`｜`mirror`｜`modify`｜`pave the way for`｜`prove`｜`provide insight into`｜`provide support for`｜`refute`｜`resemble`｜`substantiate`｜`support`｜`verify`
备注：简单的比较级（`stronger` / `more accurate` / `quicker`）同样有效；Unit 1 的 GAP/PROBLEM 语言可用于回顾既有/当前知识，或说明文献空白如何被填补（书 p223）。
原句：`Rather than being excluded as is often suggested, the sulfate reducers seemed to be thriving.`｜`Unlike existing control schemes, in this scheme the parameters can be freely changed during operation.`｜`Our data therefore provide support for the theory proposed by Stephen Robbins [Robbins et al., 2013].`｜`This study extends previous research by analysing corporate brand and industry image simultaneously.`｜`On the basis of these results, we challenge the assumptions made by existing physical-layer security systems.`

**（2）REFINE/EXPLORE IMPLICATIONS（书 pp.223–224）**
完整清单见书 p182（IMPLICATIONS AND EXPLANATIONS OF RESULTS）。Discussion 中的 implication 有时表达得**更抽象、更一般或更理论化**，或使用**允许"基于证据推测"**的语言。
词块：`plausible`｜`potential`｜`tentative`｜`to hypothesise`｜`to postulate`｜`to speculate`｜`to theorise`｜**modal verbs (esp. may/might/could)**｜`it is conceivable that…`｜`it is reasonable to assume that…`｜`this is reinforced by…`｜`this is substantiated by…`｜`this points to…`｜`we cannot rule out…`｜`Clearly,`｜`Indeed,`｜`Perhaps`
原句：`It is conceivable that such a mechanism could play a role in many other disease states.`｜`We postulate that Brownian motion of nanoparticles in nanofluids produces convectionlike effects at the nanoscale.`｜`A tentative explanation is that the colloidal system may be agglomerated at that treatment level.`｜`It is intriguing to speculate that brown fat progenitors may also reside in peripheral nerves.`｜`However, we do not rule out the possibility of a reaction with hemicellulose and lignin.`

**（3）ACHIEVEMENT/CONTRIBUTION（书 pp.224–226）**
(i) Positive language（'happy' words）形容词/副词：`accurate`｜`advantage`｜`appealing`｜`appropriate`｜`attractive`｜`beneficial`｜`clear`｜`comprehensive`｜`convenient`｜`convincing`｜`correct`｜`cost-effective`｜`direct`｜`easy`｜`economical`｜`effective`｜`efficient`｜`encouraging`｜`entirely`｜`exact`｜`fast`｜`favourable`｜`feasible`｜`flexible`｜`important`｜`intuitive`｜`low-cost`｜`new`｜`novel`｜`practical`｜`precise`｜`productive`｜`realistic`｜`relevant`｜`reliable`｜`robust`｜`significant`｜`simple`｜`smooth`｜`stable`｜`straightforward`｜`strong`｜`successful`｜`superior`｜`systematic`｜`unambiguous`｜`useful`｜`valid`｜`valuable`｜`versatile`｜`viable`
(i) 动词/动词短语：`allow`｜`avoid`｜`compare well with`｜`confirm`｜`enable`｜`enhance`｜`ensure`｜`explain`｜`facilitate`｜`help to`｜`improve`｜`is able to`｜`offer`｜`outperform`｜`prove`｜`provide a first step`｜`provide a framework`｜`provide evidence of`｜`provide insight into`｜`remove the need for`｜`resolve`｜`reveal`｜`solve`｜`streamline`｜`succeed in`｜`support`｜`validate`｜`yield`
(ii) **!-substitutes（'very happy' words）**：`compelling`｜`crucial`｜`dramatic`｜`excellent`｜`exceptional`｜`exciting`｜`extraordinary`｜`ideal`｜`invaluable`｜`outstanding`｜`perfect`｜`powerful`｜`remarkable`｜`superb`｜`surprising`｜`striking`｜`undeniable`｜`unique`｜`unusual`｜`unprecedented`｜`unquestionably`｜`vital`
原句：`This results in a cost-effective approach which significantly improves scalability.`｜`We describe not only neutral but also ionized systems with unprecedented accuracy.`｜`We achieved outstanding performance compared to similar catalysts reported in the literature.`｜`The analytical method described here removes the need for difficult and time‐consuming pre‐treatment.`

**（4）CURRENT AND FUTURE WORK（书 pp.225–227）**
`a/the need for`｜`at present`｜`currently`｜`encouraging`｜`fruitful`｜`promising`｜`urgent`｜`further work is needed`｜`future work/studies should`｜`holds promise`｜`possible direction`｜`research opportunities include…`｜`starting point`｜`the next stage`｜`we recommend`｜`we suggest`｜`worthwhile`｜`would be beneficial/useful`｜`would be of interest`｜`should be explored`｜`should be investigated`｜`should be replicated`｜`should be validated`
**表示"作者本人正在做"（非对他人的建议）**：`further work is planned*`｜`future work/studies will*`｜`is being investigated*`｜`work is (currently) underway*`｜`work is in progress*`（\*原文注：`These indicate that the writer is currently working on this; they are NOT suggestions for research by others, or invitations to other researchers.`，书 p225）
原句：`Future studies should investigate whether reducing household air pollution may lead to improvement in cardiac morbidity.`｜`Future work should focus on a qualitative analysis of patient-reported benefits of group therapy.`｜`Further work is in progress to determine whether a different drought response could help these trees to survive.`｜`In the future, it would be of interest to develop a more efficient numerical method for simulating these system dynamics.`｜`Recommendations for future studies include an investigation of polysaccharide redundancy during cell wall assembly.`

**（5）APPLICATIONS/USE/APPLICABILITY/IMPLEMENTATION（书 pp.227–228）**
时间/程度词：`eventually`｜`in due course`｜`in future`｜`soon`
动词：`to apply`｜`to enable`｜`to facilitate`｜`to generalise`｜`to generate`｜`to implement`｜`to lead to`｜`to operate/put into operation`｜`to produce`｜`to realise`｜`to serve as`｜`to use`｜`to utilise`
形容词：`applicable`｜`appropriate`｜`feasible`｜`operable`｜`practicable`｜`practical`｜`realistic`｜`suitable`｜`viable`
原句：`The study provides evidence-based guidance for realistic public health recommendations.`｜`The approach presented here is also suitable for problems where structural information is incomplete.`｜`The proposed technique could be implemented widely within the bioprocess industry, including in the production of antibiotics.`｜`This work shows that low-cost air quality sensor networks are feasible for widespread use.`｜`The data reported in this study could eventually lead to recommendations to guide optimal Clozapine use.`

**（6）重述发现/回顾结果的示范句（书 pp.196、202–203、207）**
`Our study is the first to…`｜`A key finding was that…`｜`This was particularly true in relation to…`｜`…appear to be…`｜`far less`
**（7）机制解释**：Unit 3 的 RESULTS + EXPLANATION 语言；Discussion 常以 `can be explained by…`、`can be attributed to…` 实现（书 pp.209–210、231）。
**（8）引用句首模板（围绕引用搭建叙事，书 p198）**
`We first demonstrated that _____, consistent with the literature (2, 4, 45).`｜`In particular, _____ was shown to _____ (40).`｜`Regarding this concern, Söderholm et al. (45) reported that _____.`｜`In contrast, O'Malley et al. (34) reported _____.`｜`To verify this assumption, _____ was used, as previously depicted for _____ (7, 38).`｜`Using _____, Lai et al. (27) demonstrated that _____.`｜`As a result, _____, as determined by Rahli et al. (36).`｜`In line with this, a recent in vivo study by Wrzosek et al. (47) clearly showed that _____.`｜`Likewise, the role of _____ has been proposed by Gaudier et al. (18).`

### F. Discussion 检查清单

**原文 4.6 Summary Discussion Exercise（书 p242，逐条）**

- [ ] 第一句的功能是什么？
- [ ] 结构在多大程度上符合、或在何处偏离书 p208 的通用 Discussion 模型？
- [ ] 现在时（Present Simple）背景事实信息的**数量与位置**
- [ ] Discussion 中**重复/回顾结果**的比例
- [ ] 是否**详细回顾方法**？
- [ ] Introduction 中的 aim/gap 与研究的 achievement 之间是否有清晰链接？
- [ ] 是否使用 **'happy' language** 显式点明研究的价值/成就？
- [ ] Introduction 呈现的文献/知识与本研究对该文献/知识的 contribution 之间是否有清晰链接？
- [ ] **映射**研究到既有文献/知识的引用条数
- [ ] 是否使用**降低风险的语言（risk-reducing language）**，包括 may 等情态动词
- [ ] limitations、weaknesses、discrepancies 被提及的**程度、位置与用语**

**其他可操作检查点**

- [ ] 已"退后一步"明确研究的主要价值/贡献属四类中的哪一类（method / results / impact on literature / impact on industry）（书 p191）
- [ ] take-home message 清晰、未被无关细节淹没（书 p191）
- [ ] 本节有一条**向前推进**的叙事，把读者"耐心地、符合逻辑地、显式地"从结果带到结论（书 p191）
- [ ] 开头采用两种有效方式之一（点明成就/贡献/应用；或 reboot the reader），而非罕见的"宣告将讨论什么"（书 pp.196–197）
- [ ] 回顾前人内容时沿用了相同的词语/动词以形成"回声"，而不是改写（书 pp.197、208、222）
- [ ] 每条引用相关，且相关性通过叙事显式表达；引用量与目标期刊惯例相当（书 p198）
- [ ] 避免了"仅重复/改写结果"；结果都被绑定到解释、映射、应用或局限（书 pp.202–203）
- [ ] 讨论结果含义的**语言强度**匹配结果本身的强度（审稿风险点）（书 p203）
- [ ] 无过度自信的概括，也无反向的过度弱化（书 p203）
- [ ] "首次/最大"类断言已尽可能彻底检索，必要时使用 `to our knowledge`（书 p195）
- [ ] limitations 的位置符合规范（一般在相应小节首次提及；仅两类例外在 Discussion 首次提及）（书 pp.205–206）
- [ ] 未来工作被"指定方向"（非模糊建议）；明确区分"自己正在做"与"邀请他人做"的语言（书 pp.206、225）
- [ ] 应用放在合适位置（结尾常规；若为主要贡献或核心主题则前置）；检查过目标期刊当前趋势（书 p204）
- [ ] 使用**适当且一致**的情态动词，并在歧义处改用替代结构（`It is possible…`、`is able to`）（书 pp.231–232；见 §2.3）
- [ ] 检查过 `can / can not / cannot`、`could not / cannot have / could not have`、`must not` vs `not necessary` 等易错区别（书 pp.234–239）

## 1.7 Conclusion（结论）

### A. 功能定位

Conclusion 必须交付 **清晰的 take-home message，焦点是研究的 outcome 与 impact**，其功能**超出重复与概括**，因此不能靠改写 Abstract 来生产。

> `Reviewers, editors and readers view the Conclusion as a key section that will deliver a clear take-home message focused on the outcome and impact of the study, and this expectation should be met in full by the writer.`（书 p245）
> `However, the function of the Conclusion is different from all of these, and goes beyond either repetition or summary.`（书 p245）

### B. 通用模型：GENERIC CONCLUSIONS MODEL（**11 个组件**，顺序即模型顺序）

| # | 组件（英文原词 + 中文） | 功能说明 | 语言参考（原文交叉引用） | 书页 |
|---|---|---|---|---|
| 1 | **WHAT IS IN THE PAPER**（论文包含什么） | 让未读全文的读者知道本文做了什么 | see Units 1 and 2 | p257、p258 |
| 2 | **WHAT THE PAPER/STUDY HAS ACHIEVED**（本论文/本研究取得了什么） | 宣告成果本身，是 Conclusion 的核心——用完成/成就类表述"认领"贡献 | see Unit 4 | p257、p258 |
| 3 | **RELEVANT BACKGROUND INFORMATION**（相关背景信息） | 仅提供理解成果所需的少量背景；可选且应极简 | all Units | p257、p258 |
| 4 | **THE GAP/AIM/NEED FOR THE STUDY**（研究空白/目的/必要性） | 复述研究为何必要，为成果提供坐标 | see Unit 1 | p257、p258 |
| 5 | **THE METHOD/APPROACH**（方法/路径） | 简要回忆所用方法，读者可能只读 Conclusion | see Units 2 and 3 | p257、p258 |
| 6 | **KEY RESULTS WITH EVALUATIVE COMMENTS**（关键结果 + 评价性评论） | 不只是给数字，还要给出对结果的判断 | see Units 2 and 3 | p257、p258 |
| 7 | **IMPLICATIONS OF THE RESULTS**（结果的含义/推论） | 由结果推出的一般性论断 | see Unit 3 | p257、p258 |
| 8 | **POTENTIAL OR ACTUAL LIMITATIONS**（潜在或实际局限） | 承认边界与不足 | see Units 2 and 3 | p257、p258 |
| 9 | **POTENTIAL OR ACTUAL APPLICATIONS**（潜在或实际应用） | 成果可落地的用途 | see Unit 4 | p257、p258 |
| 10 | **HOW THE STUDY ADVANCES KNOWLEDGE**（研究如何推进知识） | 上升到领域/学科层面的贡献 | see Unit 4 | p257、p258 |
| 11 | **POTENTIAL FUTURE DIRECTIONS FOR RESEARCH**（未来可能的研究方向） | 收口指向后续工作 | see Unit 4 | p257、p258 |

> **★ 词块维度的关键事实**：Unit 5 **不新增词块清单**——`Language suggestions for all the components of the Conclusions have appeared in previous Units.`（书 p258）。用本手册时，把上表"语言参考"列当作**指向 Part 1 各章的航标**：1 → §1.3 Introduction + §1.4 Methods；2 → §1.6 Discussion（成就/贡献语言）；3 → 全部章节；4 → §1.3；5 → §1.4 + §1.5；6 → §1.5（评价性语言）+ §2.13；7 → §1.5 + §2.2；8 → §1.4 C + §1.5 C；9/10/11 → §1.6 E。
> **使用模型的方法（书 p257）**：`Map components 1–11 onto the Conclusion sections of your target articles… Your analysis should consider **the order in which the components typically occur**, and **what proportion of the Conclusion section deals with each component**.`（顺序 + 各组件占篇幅比例，两者都是分析维度。）
> 组件可由**句子、句子片段或语言（词块）**承载，不必各占一句（书 p257 的问法是 `how many examples did you find of sentences, parts of sentences, or language that communicate or recall the components`）。

**Conclusion 的四种形态（与 Unit 3 的四个结构选项对应，书 p245）**

| 结构选项 | 小节序列 | Conclusion 的形态 |
|---|---|---|
| Option 1 | Results → Discussion → Conclusion/s | 独立 Conclusion，1–2 个短段落 |
| Option 2 | Results → Discussion（无 Conclusion 小节） | Discussion 的最后 1–2 段，形式与内容近似 Conclusion |
| Option 3 | Results and Discussion → Conclusion/s | 独立 Conclusion，1–2 个短段落 |
| Option 4 | Results → Discussion → Conclusion/s | 可能有一个**较长的** Conclusion 小节：开头在形式与内容上近似 Discussion，**以其后 1–2 段收尾，这 1–2 段近似 Conclusion** |

> Option 4 是唯一一个 Conclusion 长度不受 "1–2 短段" 约束的情形（书 p245）。

**长度**：`With the exception of Option 4, the Conclusion section averages **100–200 words in total** and is usually comprised of **one or two fairly short paragraphs**, even occasionally including **bullet points**.`（书 p245）；但 `the length of the Conclusion varies across different disciplines and in different journals within each discipline, so it is worth averaging the number of words in the Conclusion in your target articles as a guide.`（书 p245）
**位置**：`In some journals, the Conclusion section occurs as the last one or two paragraphs of the Discussion; in most it is a separate section.`（书 p245）
**命名**：CONCLUSION 与 CONCLUSIONS 的叫法不反映结论条数（书 p244 脚注）。

### C. 内容边界

**必须写**

1. 一句清晰的 **take-home message**，焦点是 **outcome 与 impact**（书 p245）。
2. 覆盖 11 组件并按目标期刊核对**顺序**与**篇幅比例**（书 p257）。
3. 关键结果要带**评价性评论**（组件 6）；语言即 Unit 2/3 的评价性语言（书 pp.257–258）。
4. **显式归属**（见 §2.4）：识别自己的贡献 `is not straightforward and requires you to be explicit and unambiguous`（书 p260）。

**不得写 / 红线（原文明确的三点）**

1. **不要把 Abstract 当作 Conclusion 的主要素材来源**。原句：`Each Conclusion section is preceded by the Abstract of that paper and, where relevant, the Synopsis or Highlights, **to help you see how these differ from the Conclusion section, and to emphasise that the Abstract should not be used as the primary source material for the Conclusion**.`（书 p246）
2. **不要只做重复或概括**（书 p245）。
3. **不要留下"归属不明"的句子**（书 pp.260–261）：非人称主语 + Present Simple、且 `contain nothing to tell the reader that these are in fact conclusions from this study`，读者快速阅读时 `risks loss of ownership at this critical point`；反例：`Kinetic analyses suggest that these probes are active site directed and inactivate a broad range of PTPs in a time- and concentration-dependent fashion. Direct in-gel fluorescence scanning indicates that the fluorescent probes form a covalent adduct with the PTPs.`
4. 除此之外**未给出**完整的"禁止清单"（例如是否可引入新数据、是否可重复引用文献）——**原文未明确**（见 Part 5.3）。

**与 Abstract / Synopsis / Highlights 的分工（书 pp.245–246、248–256；实证对照）**

| 对照维度 | Abstract / Synopsis / Highlights | Conclusion |
|---|---|---|
| 开场 | 常从背景或空白起笔 | 多从"本研究做了什么/发现了什么"起笔 |
| 内容深度 | Synopsis/Highlights 是**压缩体**；Highlights 为 `►`/`·` 项目符号、名词短语或省略主语的过去分词式 | **论证体**：加推论与意义、加评价、加未来方向 |
| 量化细节 | Highlights 常无数据 | 常**补 Abstract 所无**的量化细节（如 `100 attomole`、`nearly 3 orders of magnitude`） |
| 可信度论证 | 常无 | 常补（如 `confirmed by agreement between three different analyses`） |
| 评价方向 | 多为正向 | 可双向（既 `clearly demonstrates…` 又 `highlights the **modest** catalytic properties…`） |
| hedging | 几乎无 | 保留 hedging 与局限（`Both were found to have significant deficiencies for this system.`） |
| 非学术元素 | 摘要里可能出现经费致谢 | **结论中不出现致谢** |
| 第六篇样例 | 结构化 Abstract（Aim / Methods / Results / Conclusions）+ Key notes | 完整段落、含第一人称与显式指代 |

> **功能差异 ≠ 内容零重叠**：原文承认重叠存在（书 p245），重叠本身不是问题，**把 Abstract 当作主要素材来源**才是（书 p246）。

**六个样例的收口方式（用于决定 applications / implications / limitations / future work 的取舍，书 pp.248–256）**

| # | 末句功能类型 | 原文末句（节选） |
|---|---|---|
| 1 | 未来应用 + 推进知识 | `Further application of the activity-based fluorescent probes will accelerate global characterization of PTPs, thereby increasing our understanding of PTPs in cell signaling and in diseases.` |
| 2 | 未来工作（正在进行） | `Further work is currently in progress with different materials and overlayers…` |
| 3 | 设计建议 / 应用条件 | `The results indicate that through appropriate mix design reductions in strength can be minimised to acceptable levels.` |
| 4 | 对既往文献差异的解释（implication） | `…disparities between previous studies of the uranium–water reaction may be attributable to differential purities of uranium metal used by different research groups…` |
| 5 | 对替代方法的负面评价（limitation） | `Both were found to have significant deficiencies for this system.` |
| 6 | 研究机会 + 可检验假设 | `…fMRI now offers the opportunity to investigate the ontogeny of olfaction in the human newborn with millimetre-scale precision, and to address specific hypotheses…` |

> **取舍规则原文未明确**（写几个、按什么顺序、可否省略）；可依据的原文事实是：模型要求统计"what proportion of the Conclusion section deals with each component"，说明**取舍体现在篇幅比例**上，而不是写不写（书 p257）。编辑判断：唯一硬性要求是收口必须服务于 outcome + impact 这一 take-home message（书 p245）。

### D. 时态与语态规则（5.4.1，书 pp.259–260）

**规则 A：Present Simple 与 Present Perfect 是主用态。**

> `In the Conclusion section, the Present Simple and Present Perfect tenses are commonly used to state **what is in the paper**, **what is implied by the results**, and **what has been achieved in the study**.`（书 p259）

**规则 B：Past Simple 较少见，用于复述方法或关键结果。**

> `The Past Simple tense is **less common**, but is sometimes used to repeat key aspects of **the method** or **key results**`（书 p260）

| 组件 | 时态 | 原例（书页） |
|---|---|---|
| 1 what is in the paper | Present Perfect / Present Simple | `We have synthesized and characterized two fluorescent rhodamine-containing PTP probes…`（p259）；`In the present paper, … have been highlighted, and … has been introduced.`（p259） |
| 2 what the study has achieved | Present Perfect（人称或显式主语）/ Present Simple | `We have designed, constructed and implemented a fully automated and programmable olfactometer…`（p259） |
| 3 relevant background | Present Simple（极简） | — |
| 4 gap/aim/need | 依 Unit 1 规则（Past Simple 述 aim / Present Simple 述 gap 状态） | 见 §1.3 D |
| 5 method/approach | **Past Simple**（复述要点，次要选择） | `The phase behavior of (CO2 + H2O) was measured at temperature from 298.15 K to 448.15 K,…`（p260） |
| 6 key results + 评价 | Past Simple 复述；评价用评价性语言 | `In some cases complete decomposition of the surface carbides was observed.`；`…a detection limit nearly 3 orders of magnitude more sensitive than that of the biotin-conjugated probes.`（pp.248、260） |
| 7 implications | Present Simple | `It is argued that this rate law is consistent with reaction mechanisms based on recent observations…`（p259；**注意 p250 脚注的归属歧义风险**） |
| 8 limitations | 同 Unit 2/3 的局限语言 | `Both were found to have significant deficiencies for this system.`（p255） |
| 9 applications | 依 Unit 4 应用语言（含 `will`/`could`/`should`） | `Our findings will help to tailor the design of metal oxide anodes and photoanodes…`（p250） |
| 10 advances knowledge | Present Simple / Present Perfect | `This study clearly demonstrates the ability of a metal oxide semiconductor surface, such as hematite, to drive a multihole reaction,…`（p262） |
| 11 future directions | `will` / `is currently in progress` / `should` | `Further work is currently in progress with different materials and overlayers…`（p250） |
| **混用** | 同一篇 Conclusion 内通常**混用**：成就类用完成态、机制与论断类用现在时、方法/结果复述用过去时 | pp.248、253、255 |

**归属（Owning your contribution，书 pp.260–262）**

问题诊断：`Identifying your own contribution in the Conclusion is not straightforward and requires you to be **explicit and unambiguous**.`
作者误判的两个来源：① `a belief that the reader has read the rest of the paper before reading the Conclusion`；② `the writer's own familiarity with the project and its conclusions.`
读者行为：`Most readers do not read the entire paper before reading the Conclusion.`；`even if the reader has read the entire paper up to the Conclusion, it is not safe to assume that they retain all the information in earlier sections with perfect accuracy.`
心理障碍要克服：`you may even feel that it appears condescending or patronising`——**不要因为觉得多余或居高临下而省略明确化**。

> **四条可执行修正手段（原文四项）**：`writers can avoid ambiguity by using one or more of the following: the Past Simple or Present Perfect / the active rather than the passive / a human grammatical subject / explicit sentence start-up or language that explicitly refers to the paper or study`（书 p261）

| 手段 | 原例 |
|---|---|
| Past Simple 或 Present Perfect | `Examination of cast α-uranium surfaces after exposure to water vapour in an ESEM instrument at 19 mbar and 20 °C indicated that surface corrosion had occurred,…`（p261） |
| 主动而非被动 | `We have synthesized and characterized two fluorescent rhodamine-containing PTP probes that are highly sensitive for direct in-gel visualization of PTP activity.`（p261） |
| 人称主语 | 同上（We） |
| 显式启动语/明确指向本文 | `Finally, it is shown here that…`（`here` 明示本文）；`This study clearly demonstrates…`；`In the present paper, … have been highlighted…`；`From the results of the current study it is apparent that the carbide particles reacted more readily with the water vapour than the metal.`（同时示范"主语非人称但显式指本研究"这一例外路径）；`This transition was confirmed by agreement between three different analyses.`（明确回指本研究内容）（pp.261–262） |

### E. 词块库（Unit 5 无独立清单 → 全部交叉引用 + 本单元样例可直接复用句）

**（A）论文内容/研究动作（Present Perfect，人称或显式主语）**
`We have synthesized and characterized…`｜`We have designed, constructed and implemented…`｜`The rate order of the water oxidation reaction has been investigated on…`｜`In the present paper, … have been highlighted, and … has been introduced.`｜`This paper has demonstrated the potential for…`｜`This paper has shown that…`

**（B）结果蕴含的论断/机制解释（Present Simple）**
`It is argued that this rate law is consistent with…`（**注意归属歧义**）｜`The third order reaction is rationalized by considering…`｜`The results indicate that through appropriate mix design reductions in strength can be minimised to acceptable levels.`｜`These data suggest that fMRI now offers the opportunity to investigate…`｜`This study clearly demonstrates the ability of…, but also highlights the modest catalytic properties of…`｜`From the results of the current study it is apparent that…`｜`it is suggested that disparities between previous studies … may be attributable to…`

**（C）与既有数据/文献对照**
`The experimental results are compared comprehensively with literature data and found to agree with those literature sources identified in earlier reviews as being of the highest reliability.`｜`Our results fill key gaps in terms of accurate and high-quality data … and pave the way for measurements on (CO2 + brine) systems.`｜`Both were found to have significant deficiencies for this system.`

**（D）关键结果复述（Past Simple）**
`The phase behavior of (CO2 + H2O) was measured at temperature from 298.15 K to 448.15 K,…`｜`In some cases complete decomposition of the surface carbides was observed.`｜`The system was found to induce a well-localized pattern of…`｜`A transition from first order to third order in photogenerated holes has been identified…`｜`This transition was confirmed by agreement between three different analyses.`

**（E）方法/步骤回忆**
`…by photoinduced absorption of accumulated holes and photocurrent densities recorded simultaneously.`｜`The results are modeled accurately with a γ−ϕ approach incorporating the Peng–Robinson EoS…`｜`The Krichevsky–Kasarnovsky (KK) (simplified γ−ϕ approach) was also studied as well as the empirical correlation of Duan et al.`

**（F）归属显式化句型（本单元最核心的工具）**
`Finally, it is shown here that…`｜`This study clearly demonstrates…`｜`From the results of the current study it is apparent that…`｜`In the present paper, … have been highlighted…`｜`The described system is safe, has been designed to minimize infective risks and produces…`

**（G）应用/意义/推进知识**
`This highlights the potential to use the fluorescent probes to identify new PTP markers and targets for the diagnosis and treatment of human diseases.`｜`Our findings will help to tailor the design of metal oxide anodes and photoanodes for water oxidation with regards to achieving high localized hole concentration, and the need for cocatalysts to enhance function.`｜`…thereby increasing our understanding of PTPs in cell signaling and in diseases.`｜`This material is furthermore cost effective to produce and comes widely available as a waste material in many markets.`

**（H）未来方向/收口句**
`Further application of the activity-based fluorescent probes will accelerate global characterization of PTPs…`｜`Further work is currently in progress with different materials and overlayers to determine their function and abilities to catalyze this complex but fascinating reaction.`｜`…pave the way for measurements on (CO2 + brine) systems.`｜`…fMRI now offers the opportunity to investigate the ontogeny of olfaction in the human newborn with millimetre-scale precision, and to address specific hypotheses concerning the development of mature olfactory responses.`

**（I）定量/评价性表述（组件 6 的落点）**
`…a detection limit nearly 3 orders of magnitude more sensitive than that of the biotin-conjugated probes.`｜`…can detect on the order of 100 attomole of rhodamine-labeled PTP…`｜`…the fluorescent probes also exhibit extremely high selectivity toward PTPs while remaining inert to other proteins.`｜`…provide superior sensitivity, quantifiability, and throughput for activity-based PTP profiling.`｜`…the most promising overall performance.`｜`…occurred at rates significantly faster than that of the metal.`

### F. Conclusion 检查清单

> 说明：抽取范围（书 pp.243–262）内**没有**独立的 Checklist 小节（Unit 5 正文止于 5.4.2）；全稿清单在 Unit 8。以下条目逐条由本单元规则转化。

**定位与长度**

- [ ] 已按目标期刊确认 Conclusion 是"独立小节"还是"Discussion 末 1–2 段"（书 p245）
- [ ] 已确认所属结构选项（Option 1–4）；若为 Option 4，已按"前段似 Discussion + 末 1–2 段似 Conclusion"组织（书 p245）
- [ ] 已统计目标期刊 Conclusion 的平均词数并据此控制篇幅；非 Option 4 情形控制在约 100–200 词 / 1–2 个短段落（书 p245）
- [ ] 已确认单复数用 CONCLUSION 还是 CONCLUSIONS 与该刊惯例一致（书 p244）

**内容与模型覆盖**

- [ ] 已用逆向工程逐句标注句子功能，并与 11 组件模型对照（书 pp.246、257）
- [ ] 已核对每个出现组件的**出现顺序**是否符合目标期刊惯例（书 p257）
- [ ] 已核对各组件占 Conclusion 的**篇幅比例**（书 p257）
- [ ] 组件 6（关键结果）配有评价性评论，而非只列数据（书 pp.257–258）
- [ ] 已决定 7 implications / 9 applications / 11 future directions 各自写多少，且服务于 outcome + impact（书 pp.245、257）

**红线**

- [ ] **未把 Abstract 当作主要素材来源**；Conclusion 不是 Abstract 的改写或压缩（书 p246）
- [ ] Conclusion 的功能超出"重复与概括"（书 p245）
- [ ] 未出现"非人称主语 + Present Simple 且无归属信号"的成就句（书 p260）
- [ ] 未使用可产生归属歧义的无人称结构（如指代不清的 `It is argued that`，书 p250 脚注）

**语言**

- [ ] "论文内容 / 结果蕴含 / 已取得成就"用 Present Simple 或 Present Perfect（书 p259）
- [ ] "方法要点 / 关键结果"复述用 Past Simple，且未全篇使用（书 p260）
- [ ] 时态在同一篇 Conclusion 内按功能分工而非随机混用（书 pp.248、253、255）

**归属（Ownership）——至少使用以下一项（书 p261）**

- [ ] 使用 Past Simple 或 Present Perfect
- [ ] 使用主动语态而非被动语态
- [ ] 使用人称主语（如 We）
- [ ] 使用显式启动语或明确指向本文/本研究的语言（`This study…`, `In the present paper…`, `here`, `the current study`, `This paper has…`, `Our results…`）

**读者视角**

- [ ] 假设读者**没有**读过全文（可能从 Conclusion、Abstract 甚至标题跳入）仍能读懂贡献（书 p260）
- [ ] 假设读者即使读过全文也不会准确记住前文细节（书 p260）
- [ ] 已抵抗"读者当然知道这是我的结论"以及"写太明白显得居高临下"这两种心理（书 pp.260–261）
- [ ] 已请不熟悉该项目的同事快速阅读，检查是否每一处成就都能被正确归因给本研究（编辑建议：由书 p260 的"同事共享熟悉度导致盲区"推论，原文未明确给出该具体做法）

# Part 2 跨章节语言层（去重合并版）

> **编纂原则**：原书中大量语言技能重复出现在多个单元（最典型的是 -ing 歧义、冠词、介词同时出现在 Unit 2 与 Unit 8）。本部分**每个主题只写一份**，并在标题后标注「原出现单元」；内容不合并会丢的差异（例如 Unit 2 给系统规则、Unit 8 给新增陷阱）则分列「基础规则 / 新增陷阱」。
> **各章 D/E 节只保留组件级规则**，完整规则一律回到本部分。

## 2.1 verb tense 总表（跨章节）

**原出现单元**：Unit 1（pp.53–55）、Unit 2（pp.113–115）、Unit 3（pp.155–156、183–184）、Unit 4（pp.201–204）、Unit 5（pp.259–260）、Unit 6（pp.286–287、290）、Unit 7（pp.303、310）、Unit 8（p321）。

**三条元规则**

1. **时态是意义表态，不是语法命令**：`The decision of which of these three tenses to use is rarely determined by the rules of grammar; in most cases the decision is made on the basis of meaning.`（书 p53）
2. **改动必须有理由**：`Tense changes are always meaningful… so don't choose or change tense randomly.`（书 p55）；Unit 8 版：`If you switch to a different tense, make sure that you and the reader both know why.`（书 p321）
3. **时态 = 主张强度**：`We found that x occurred is simply a report of your findings, whereas We found that x occurs means that your findings can be considered as facts; the Present Simple tense is higher risk, but has more power.`（书 p321）

**总表（按句子功能索引）**

| 句子功能 | 时态 | 出处（书页） |
|---|---|---|
| 背景事实、已被接受的事实、公认知识 | **Present Simple** | pp.7、17、290 |
| 指称近期时间（in recent years / over the past three years） | **Present Perfect** | p6 |
| 聚焦当前状况 | **Present Simple** | p6 |
| 引用某项前人研究的**具体发现** | **Past Simple** | p53 |
| 把前人发现表述为**可靠恒久的事实** | **Present Simple** | p53 |
| 指出**当前的 gap** | **Present Perfect**（`little attention has been paid`） | p55 |
| 指"当时（某时点）"的状态 | **Past Simple**（`little attention was paid`） | p55 |
| 研究机会 | 情态动词 `may/might/could/would` | p50 |
| 描述**本文做什么/论文中有什么** | **Present Simple** | pp.15、286、292 |
| 陈述 **aim** | **Past Simple**（aim 在工作之前就存在）；aim 只部分达成时可用 **Present Simple** | p15 |
| Methods：**你做了什么** | **Past Simple** | pp.113–114 |
| Methods：**标准流程/设备** | **Present Simple** | pp.113–114、84 |
| Methods：背景信息 | **Present Simple**（模型明文） | p88 |
| Results：**图形中可见内容** | **Present Simple** | p155 |
| Results：**图形信息如何获得** | **Past Simple** | p155 |
| Results：解释结果的**材料性质等已知事实** | **Present Simple** | p155 |
| Results：涉及**方法**的"为什么" | **Past Simple** | p155 |
| Results：描述模型如何"运行" | 可**全节 Present Simple**（查目标文章） | p155 |
| 结果是否算"永久真理" | Present Simple（更强、更高风险）vs Past Simple（绑定本研究） | pp.53、155–156、204 |
| Discussion：背景事实 | **Present Simple**（4.6 清单专门统计数量与位置） | pp.201、242 |
| Discussion：回顾结果并评论 | Past 或 Present 皆可，**属作者判断**（唯一不能靠目标文章解决的项） | pp.202–204 |
| Conclusion：论文内容/结果蕴含/已取得成就 | **Present Simple 或 Present Perfect** | p259 |
| Conclusion：复述方法要点/关键结果 | **Past Simple**（次要选择，不可全篇） | p260 |
| Abstract：做了什么/有什么 | **Present Simple** | p286 |
| Abstract：方法（做了什么/用了什么） | **Past Simple** | p286 |
| Abstract：结果与含义 | **Past 或 Present 皆可**；摘要中可把正文的过去时改成现在时 | p286 |
| Abstract：成就/价值/贡献 | **Present Perfect 或 Present Simple** | p287 |
| Abstract：事实背景 | **Present Simple** | p290 |
| Abstract：挑战/问题 | **原文未明确**（词块多为现在时系动词/形容词式） | pp.291–292 |
| Abstract：mapping / applications | **原文未明确** | — |
| Title：句子标题陈述发现 | **Present Simple** | p303 |
| Title：结论未定/预测方向 | `may/might/could` | p310 |
| 时态随时间与知识发展漂移 | `X has been found to occur4` → `X occurs4` → `X occurs` | p180 |

**检查动作**：不要用五年前论文的时态；用 Google Scholar **只搜近期研究**核对当前惯例（书 pp.10、53）；在目标文章中标出动词/时态并自问 `Does the verb tense seem to 'match' the power of the results?`（书 p204）。

## 2.2 the certainty continuum（确定性连续统）

**原出现单元**：Unit 3（pp.183–186，主来源）、Unit 4（pp.229–241 modal verbs）、Unit 6（p288 implications 强度）、Unit 8（p329）。

**定义**：`The certainty continuum runs from speculation all the way to proof.`（书 p183）
**写作任务**：`Decide where your results and the implications of your results fit on the certainty continuum, and choose language that represents that location.`（书 p186）；Unit 8 版硬约束：`what is essential is that the language you choose follows logically from the results or achievements of the study.`（书 p329）

**（1）因果动词按强度分级（书 p183）**

| 强度 | 动词 |
|---|---|
| 直接/强因果 | `cause`, `produce`, `be due to` |
| 部分原因 | `contribute to`, `be a factor in` |
| 隐含因果过程 | `lead to` |
| 因果链的起始原因 | `originate in` |
| 指产物而非结果 | `produce` / `yield` |
| 间接/弱/隐含因果 | `be related to`, `be linked to` |

完整动词表（书 p183）：`(be) a factor in`, `(be) a/the cause of`, `(be) a/the consequence of`, `(be) a/the result of`, `(be) ascribed to`, `(be) associated with`, `(be) attributed to`, `(be) connected to`, `(be) due to`, `(be) linked to`, `(be) related to`, `accompany`, `account for`, `affect`, `arise from`, `cause`, `contribute to`, `create`, `drive`, `generate`, `give rise to`, `govern`, `influence`, `initiate`, `lead to`, `originate in`, `produce`, `result from`, `result in`, `yield`

**方向、冠词与介词的关键区分（书 p184）**

- 有些动词**固定了原因与结果的位置**：`X produced Y` 中 X 是因、Y 是果；`X originated in Y` 中 **X 是果、Y 是因**。
- `X is linked to Y` 只表示 X 与 Y **有某种联系**，**不指明因果方向**，甚至不必然意味着因果关系（同 `connected to`、`related to`）。
- 冠词：`X is **a** cause of / **a** result of …` 暗示**还有其他因素**；`X is **the** cause of / **the** result of …` 暗示 X 是**唯一**的原因/结果。
- 介词：`X results **from** Y` = X 是 Y 的结果；`X results **in** Y` = Y 是 X 的结果。

**（2）risk-reducing language（hedging，书 pp.184–185）**

- 基本手段：`it appears that…` / `there is evidence to indicate that…`
- **frequency qualifiers**：`often`, `commonly`（10 级频率表见 §1.5 E-6）
- **quantity qualifiers**：`in some cases`, `in virtually all cases`（5 组数量语言见 §1.5 E-4）
- **modal verbs**：`may`, `might`（全表见 §2.3）
- 其他 risk-reducing phrases：`appear to`, `seem to`, `tend to`（书 p180）
- **不要为保险而滥用**：`it is equally important not to underplay the implications of your work just to be on the safe side, as this undermines and diminishes it.`（书 p203）；若结果支持解释，就升级为 `highly likely / probable / almost certain`（书 p235）

**（3）全连续统示例句（书 p185，原文照录，从绝对确定到极谨慎）**

1. `We find/found that sunbathing causes cancer.`
2. `We find/found that sunbathing may cause cancer.`
3. `We find/found evidence to suggest that sunbathing may be related to cancer.`
4. `It appears therefore that in some cases, sunbathing may have been related to the onset of cancer.`
5. `The evidence points to the possibility that in some cases, excessive sunbathing may have contributed to the onset of certain types of cancer.`

**（4）真实论文 Results 中的确定性表达（书 pp.185–186，节选）**

`The temperature of the Ti target appeared to be somewhat critical.`｜`It seems therefore that the plating solution probably affects the ceria.`｜`The identified pattern is potentially indicative of altered cellular processes.`｜`It is therefore reasonable to suppose that the duplexity of pitch is a reflection of duplexity in the auditory process.`｜`The Zn correlations of the samples (Figs. 3, 4a–c) are hence most plausibly explained by indigenous processes.`｜`This provides strong evidence for the importance of NADW in glacial-interglacial climate change.`｜`We speculate that this reflects the increase in blood pressure that is known to occur in some of these patients.`｜`This suggests that the polysulfide may undergo more complicated electrochemical reactions with likely involvement of more polysulfide species.`｜`These results indicate that EGFR mutations may predict sensitivity to gefitinib.`｜`The differences in recurrence rates increased over time, suggesting that there is a carryover effect.`

**（5）四级确定性直观模型（书 p237，"同事走路回家"）**

| 离开时间 | 表述 | 语义 |
|---|---|---|
| 18 分钟前 | she **may/might/could** be home by now | **possibly** |
| 30 分钟前 | she **should** be home by now | **probably** |
| 50 分钟前 | she **must** be home by now | **obviously** |
| 只有 5 分钟前 | she **cannot** be home yet | **impossible** |

## 2.3 modal verbs 六组功能分级

**原出现单元**：Unit 4（pp.229–241，唯一系统来源）、Unit 3（p184 指向）、Unit 6（p288）、Unit 8（p329，**未列具体清单**）。

> 范围界定（书 p229）：4.5 节**只涉及 STEMM 研究写作或正式学术写作中相关的情态动词用法**；非正式/口语用法（如 may 表示"许可"）不包含在内。
> 各节功能分工（书 pp.230–231）：Introduction 提出假设（`could be due to…`）、指出空白（`may provide valuable insight into…`）；Methods 为选择辩护（`this meant that we could measure …`）；Results 解释结果（`this might have been affected by…`）；**Discussion 表达可能的解释、潜在的应用、显而易见的解读、推荐的未来工作方向、很可能的含义**。

**情态动词清单（原文列举）**：`may, might, could, can, should, need to, must`（书 p230）

### 第 1 组 ABLE（能力）——书 p232

| 时态 | 情态动词 | 例句 | 等价替代结构 |
|---|---|---|---|
| Present Simple | **CAN** | The model can predict a wide range of experimental data. | The model **is able to** predict… |
| Present Simple 否定 | **CANNOT** | This system cannot identify other pathogenic bacteria. | This system **is not able to** identify… |

要点（书 p233）：不确定用 can 还是 be able to → **用 be able to**（更安全、更不易被误解）；将来时 → **will be able to**；`could` 同时表示 possible 与 able，需判断是否造成歧义；`be capable of` 在某些语境下是 can/could 的替代。

### 第 2 组 POSSIBLE/OPTIONAL（可能/可选）——书 pp.233–235（**全书最容易出错的一组**）

| 时态 | 情态动词 | 例句 | 等价替代结构 |
|---|---|---|---|
| Present Simple | **MAY / MIGHT / COULD** | These interactions may/could/might be the same for each species. | **It is possible that** these interactions are the same… |
| Present Simple（将来可能） | — | This intervention may/could/might lead to effective treatments. | It is possible that this intervention **will** lead to… |
| Present Simple（可延伸） | — | The method presented here can/could/may be extended to other systems. | **It is possible to** extend the method… |
| Past Simple | **COULD** | The algorithm could convert unstructured data into spreadsheet format. | The algorithm **was able to** convert… |
| Past Simple | **COULD HAVE** | With a larger sample size, the method could have identified more infections. | …**would have been able to** identify… |
| Past Simple 否定 | **COULD NOT** | The robot could not react dynamically to changes in the environment. | …**was not able to** react… |
| Past Simple 否定 | **COULD NOT HAVE** | Without this data, we could not have detected the contamination. | …**would not have been able to** detect… |
| Present Simple 否定 | **MAY NOT / MIGHT NOT**（**但不用 COULD NOT 或 CANNOT**） | These interactions may not/might not be the same for each species. | It is possible that these interactions **are not** the same… |
| Present Simple 否定 | **MAY NOT / MIGHT NOT** | This intervention may not/might not lead to effective treatments. | It is possible that this intervention **will not** lead to… |
| Past Simple | **MAY HAVE / MIGHT HAVE / COULD HAVE**（**但不用 CAN HAVE**） | This response may have/might have/could have caused the reduction in the noise level. | It is possible that this response **caused**… |
| Past Simple 否定 | **MAY NOT HAVE / MIGHT NOT HAVE**（**但不用 COULD NOT HAVE 或 CANNOT HAVE**） | This response may not have/might not have caused… | It is possible that this response **did not cause**… |

要点（书 pp.234–235）：
- 现在时中 may/might/could 既可指**将来可能性**，也可指**当前/永久可能性**；
- **might 比 may 稍弱**，在研究写作中**不太常见**；
- **can 有歧义、因而有风险**：`Particle formation can occur in the boundary layer` 可表示 `may [possibly] occur` / `is able to occur` / `sometimes occurs` 三者之一 → 有潜在歧义时改写成其中一种；
- **can 适合表达选项/选择**：`An X or a Y can be used` = It is possible to use either an X or a Y；
- **`can not` 与 `cannot` 不同**：`can not` 与 may not / might not 一样表示"possibly not"；`cannot` 表示**不可能**；
- `could not / cannot have / could not have` 也表示**不可能**：`This cannot be due to a change in pressure.` / `This could not be due to a change in pressure.` / `This cannot have been due to…` / `This could not have been due to…`（均为 impossible）

### 第 3 组 EXPECTED/LIKELY/PROBABLE（预期/可能/很可能）——书 pp.235–236

| 时态 | 情态动词 | 例句 | 等价替代结构 |
|---|---|---|---|
| Present Simple | **SHOULD** | The ratio should remain constant if the expansion is uniform. | **is expected to / is likely to / will probably** remain constant… |
| Present Simple 否定 | **SHOULD NOT** | The ratio should not change unless the expansion changes. | **is not expected to / is not likely to / will probably not** change… |

要点（书 p236）：`should have` 常指**本应发生却没有发生**的事；`should not have` 常指**本不该发生却发生了**的事；`was likely/probable` 与 `was not likely/probable` **不指**某事是否发生，而指**对过去事件的确信程度**；`ought to` 与 should 相同，但在科学写作中**日益少见**。

### 第 4 组 OBVIOUS/IMPOSSIBLE（显然/不可能）——书 p236

| 时态 | 情态动词 | 例句 | 等价替代结构 |
|---|---|---|---|
| Present Simple | **MUST / HAVE TO** | This must be the result of direct collision between the electron and the nucleus. | **It is obvious that** this is the result of… |
| Present Simple 否定 | **CANNOT** | This cannot be a result of direct collision… | **It is impossible that** this is the result of… |
| Past Simple | **MUST HAVE** | This effect must have been due to the increased rate of synthesis. | It is obvious that this effect **was** due to… |
| Past Simple 否定 | **CANNOT HAVE / COULD NOT HAVE** | This effect cannot have been/could not have been due to… | It is impossible that this effect **was** due to… |

要点（书 p237）：该组用于表示**不存在其他解释**；**`must not` 表示"不允许"，不表示"不可能"**；**`have to` 只用于口语交流**。
**may vs must 的语义对照（书 p231）**：`The drop in pressure may have been caused by a crack in the pipe.` → 提供**一种可能原因**；`The drop in pressure must have been caused by a crack in the pipe.` → 你**确信**是这样，但**没有证据证明**。**must 看似给动词更多力量，其实传达了"缺乏证据"。**（书 p232：我们看时钟时不会说 `It must be ten o'clock`，而是直接说 `it is ten o'clock`。）

### 第 5 组 ADVISABLE/RECOMMENDED（可取/建议）——书 pp.237–238

| 时态 | 情态动词 | 例句 | 等价替代结构 |
|---|---|---|---|
| Present Simple | **SHOULD** | The tubes should be centrifuged before the experiment. | **It is advisable to** centrifuge… |
| Present Simple 否定 | **SHOULD NOT** | The tubes should not be centrifuged before the experiment. | **It is not advisable to** centrifuge… |
| Past Simple | **SHOULD HAVE** | We later realised that the samples should have been diluted with water. | …**it would have been advisable/a good idea to** dilute… |
| Past Simple 否定 | **SHOULD NOT HAVE** | The samples should not have been diluted with water. | …**it was not advisable/not a good idea to** dilute… |

**should 的两义辨析**：should 既可表示 EXPECTED/LIKELY/PROBABLE，也可表示 ADVISABLE/RECOMMENDED；原文给 13 句练习（书 p238），**原文未给出该练习的答案**（见 Part 5.3）。示例：`Each phial of cells should only be used once.`（建议）｜`Vegetation productivity in tundra should increase if shrubs become more abundant.`（预期）｜`The bias is the same for all groups, and therefore should not change the statistical results.`（预期）｜`All final solutions should be filtered through a fine-grain paper.`（建议）

### 第 6 组 NECESSARY/ESSENTIAL（必要/必须）——书 p239

| 时态 | 情态动词 | 例句 | 等价替代结构 |
|---|---|---|---|
| Present Simple | **MUST / NEED TO / HAVE TO** | The tubes must/need to/have to be centrifuged before the experiment. | **It is necessary to** centrifuge… |
| Present Simple 否定 | **DO NOT NEED TO / DO NOT HAVE TO / NEED NOT** | The tubes do not need to/do not have to/need not be centrifuged… | **It is not necessary to** centrifuge… |
| Past Simple | **NEEDED TO / HAD TO** | We found that the samples needed to/had to be diluted with water. | We found that **it was necessary to** dilute… |
| Past Simple 否定 | **DID NOT NEED TO / NEED NOT HAVE / DID NOT HAVE TO** | …did not need to be/did not have to be/need not have been diluted… | …**it was not necessary to** dilute… |

要点（书 p239）：**`must not` 表示"不允许"，不表示"不必要"**；**`did not need to` 通常表示"不必要且我们没做"**，而 **`need not have` 通常表示"不必要但我们做了"**；`did not have to` 在正式科研写作中**不太常见**。

### 替代结构与语法陷阱

- **替代结构趋势**（书 p232）：使用替代结构（如 `it is possible` 而非 `it may`）**日益普遍**，可能正是因为情态动词语法不规则、传递错误信息的风险高。
- 否定形式改变意义（书 p232）：`He must go home` = `He has to go home`；`He must not go home` = 必须**不**回家（禁止）；`He does not have to go home` = **不必**回家（不必要）。
- **练习要点（书 pp.239–241，可直接做训练清单）**：`is able to / is capable of` → can（否定 not able to → cannot）；`It is possible that + 过去` → may/might/could **have** + 过去分词；`It is essential/necessary` → must / need to / have to；`will probably / is likely to / is expected to` → should；`It is impossible that + 过去` → cannot have been / could not have been；`It is possible that … will not` → may not / might not（**不用** could not/cannot）；`It is not advisable` → should not；`not necessary + 已做` → need not have been / did not need to be；反事实条件（`If we had extended…, it would have been possible to…`）→ could have + 过去分词。
- **风险提示（书 p231）**：`Using the appropriate modal verb in the appropriate tense is essential. Incorrect, inconsistent, indiscriminate or careless choices make the take-home message of the study unclear or ambiguous at this crucial point.`

## 2.4 ownership / 贡献归属（谁做的、谁在说）

**原出现单元**：Unit 2（pp.113–115，agentless passive 五情形表）、Unit 5（pp.260–262，四条修正手段 + `It is argued that` 歧义）、Unit 6（p266，摘要消歧）、Unit 8（pp.321–322 与 p329）、Unit 1（p65，we/our 指代；p11 引用位置）、Unit 4（p198 引用相关性）。

> 核心命题：`Own your own work and contribution. Sentences with non-human grammatical subjects may risk your work being interpreted as common knowledge or other researchers' contributions.`（书 p322）
> 本主题与 §2.5（冠词）、§2.8（指代）、§2.11（信号词）共同构成"隐形错误"家族。**摘要被点名为最危险区域**：`Note that sentences like this are particularly dangerous in the Abstract.`（书 p322）

**（1）agentless passive 的五种含义与消歧手段（书 pp.114–115，完整表见 §1.4 D）**

- 无施动者被动（`was done`, `was studied` 不带 `by X`）**不说明谁做了该动作**；同一形式既可用于描述自己的工作，也可用于描述他人工作。
- 消歧手段：改用主动（`We collected/modified X`）；加 `here / in this study / in this work / in our model`；用引用或 `in their work / in that model`；用"假主语"（`This experiment` / `The procedure described above` / `That experiment` / `The probe used in their study` / `This equation` / `The model`）；把图内容明确定义为自己的工作（`The experimental setup used here is shown in Fig. 3.`）。
- **被动后置的认知代价**（书 p321）：`Placing a passive verb at the end of a long sentence requires the reader to wait until the end of the sentence to discover what happened.` 错误示范：`Images and patient data from seventeen patients who were suspected of having PH and who had also undergone cardiac MRI and right-sided heart catheterization between 2002 and 2008 were retrospectively reviewed.`

**（2）`we/us/our` 的双重身份（书 pp.321–322）**

`The impersonal use of we/us/our can refer to 'everyone in my field' or even 'everyone in the world'. This can cause ambiguity if you also use we/us/our in other sentences to refer to yourselves as authors.`
修改对照：`Instead of We can now design proteins with many functions to refer to 'everyone in my field', consider It is now possible to design proteins with new functions.`

**（3）非人主语与无人称结构的陷阱（三处原文并列）**

| 陷阱 | 原例 | 风险 |
|---|---|---|
| 非人主语 + Present Simple | `Theoretical modelling suggests formation of these bonds can be strongly reduced by coating the receptors on the nanoparticles` | `it is not clear whether or not it was the writers who carried out the modelling.`（书 p322） |
| `It is argued that` 型 | `It is argued that this rate law is consistent with reaction mechanisms…` | 可能意为 `We argue that…`，也可能是 `It is argued by others that…`（书 p322；Unit 5 脚注同：`It's likely that the authors are referring to themselves, i.e. We argue that, but the sentence could mean It is argued by others that…`，书 p250） |
| 无人称成就句（Conclusion） | `Kinetic analyses suggest that these probes are active site directed…` | `contain nothing to tell the reader that these are in fact conclusions from this study`（书 p260） |

**（4）Conclusion 的四条修正手段（书 p261）**：Past Simple 或 Present Perfect / 主动而非被动 / 人称主语 / 显式启动语或明确指向本文（`This study…`, `In the present paper…`, `here`, `the current study`, `This paper has…`, `Our results…`、`From the results of the current study it is apparent that…`）。
**（5）Abstract 的三条消歧手段（书 p266）**：用 Past Simple / Present Perfect 或 we 主动式（`Analysis shows…` vs `Analysis showed…`）；句首加归属性短语（**`In this study / Here`** 指向自己，**`It is known that / It has been previously demonstrated that`** 指向公认知识）；**不因字数限制而删掉这些短语**（`your aim is not to make it possible for the reader to understand the Abstract; it is to make it impossible for the reader not to understand the Abstract AND identify your contribution.`）。
**（6）引用位置也决定归属**（书 p329）：`Locate citations at the appropriate place in the sentence.`；`Placing a citation reference at the end of the sentence (or stacking all the citations there) can cause ambiguity about who did what.` Unit 1 版（书 p11）：当引用只对应句中**一部分信息**时把引用放在句中，`Your citation location should make it clear which part of the information comes from which study.`；把整句信息都归到句末所有引用之下是**误导**。原例：`…metals such as aluminium have been used to strengthen PLA for industrial applications5,6, these are not appropriate for biomedical use7.`
**（7）归属自查四问（书 p329）**：`Is this statement your own hypothesis/explanation?` / `Is it a known truth?` / `Will the reader know which of those it is?` / `Is a citation needed?`

## 2.5 冠词 a / an / Ø（零冠词）/ the

**原出现单元**：Unit 2（pp.121–126，系统来源）、Unit 8（p322，隐形错误）、Unit 3（p184，a/the cause 的意义差）、Unit 6（p266，首次提及与宽读者群）、Unit 7（p309，标题 A/An 的"新提议"功能）。

**三条元规则（书 p121）**

1. 冠词不只由语法决定，**具有强烈的交际功能**；一句话用 `the` 或 `a` 都语法正确，但意思不同。
2. 起点规则：**单数可数名词必须带冠词（a 或 the）**；但"哪些名词可数"本身并不显然。
3. 回答三问：① 什么是可数名词？② 该用 a/an、Ø 还是 the？③ 两者都可能时，意义差别在哪？

**Q1 什么是可数名词（书 pp.121–123）**

- 定义：**能构成复数的名词就是可数名词**；有的视用法而定：`There have been three deaths this year from pneumonia.`｜`Our childhoods were very different…`｜`Many industries rely on fossil fuels.`；材料类名词在行家手里可数：`We have developed steels containing only elements that produce certain radioactive isotopes.`
- 使用名词时**先停下来判断**：你指的是 industry **in general（不可数）** 还是 **particular industries（可数）**？
- **无法用作可数的名词**要改用"量词+名词"结构：`add another noun: items of equipment / methods of transport / types of evidence`（书 p123）。
- **STEMM 常用不可数名词表**（约 90 词，书 pp.122–123）：`absence, earth, industry, protection, advice, economy, information, purity, age, education, insurance, quantity, agriculture, electricity, intelligence, reality, aid, energy, knowledge, research, air, environment, life, risk, analysis, equipment, light, safety, atmosphere, evidence, loss, salt, behaviour, existence, machinery, sand, blood, experience, noise, science, business, failure, nutrition, strength, calculation, fear, oil, stuff, cancer, fire, organisation, technology, capacity, food, oxygen, temperature, childhood, fuel, paper, transport, concrete, harm, philosophy, treatment, danger, health, physics, trouble, death, heat, policy, truth, democracy, height, pollution, velocity, design, help, power, vision, disease, history, pressure, waste, distribution, independence, progress, water`
  > 原文以**粗体**标出"不能可数化"的名词；纯文本抽取未保留粗体 → **具体哪些词为粗体无法判别**（见 Part 5.3）。
- Unit 8 的相应提醒（书 p322）：**检查你正在当可数名词用的不可数名词**，如 `steel`、`environment`、`technology`，它们因此可能需要冠词。

**Q2 用 a/an、Ø 还是 the（书 pp.124–125）**

| 冠词 | 使用情形 | 原例 |
|---|---|---|
| **a/an** | (i) 单数可数名词**第一次提及** | `I bought a cheese sandwich and an apple. The sandwich was OK but the apple had a little worm in it.`（第一次 a/an，第二次 the——不是语法驱动，而是"共享知识"驱动） |
| | (ii) **不重要/你不知道/读者不知道是哪一个** | `Bring me a pen please.`｜`She works in a bank.`｜`The subject spoke to an interviewer.` |
| | (iii) 对单数可数名词作**一般性陈述** | `A semiconductor can conduct electricity under certain conditions.` |
| **Ø** | (i) 复数可数名词的一般性陈述 | `Ø Semiconductors can conduct electricity under certain conditions.` |
| | (ii) 不可数名词的一般性陈述 | `Ø Pollution is generally the result of human activity.` |
| | (iii) 复数可数名词**第一次提及** | `We conducted Ø DNA arrays on Ø silicon chips.` |
| | (iv) 完全不可数或取不可数含义 | `These acids may undergo Ø oxidation.`｜`We found many applications in Ø industry.` |
| **the** | (i) **实际上只有一种可能** | `The opening was located in the centre of each mesh.`｜`We report the discovery of the smallest possible carbon nanotube.` |
| | (ii) **读者确定知道** | `They arranged to meet in the café.`｜`Did she get the job?`｜`The cheese sandwich was very good.` |
| | (iii) **对读者显然，即使此前未提及**（共享知识） | `I bought a new computer but the keyboard was faulty.`——**准确、敏感地判断什么可安全假定为共享知识，是文本成败的核心** |

**Q3 a/an 与 the 都可能时的意义差异（书 pp.125–126）**

- `The nodes should be attached to Ø two receptor sites.`（存在许多受体位点中的两个）vs `The nodes should be attached to the two receptor sites.`（**只有两个** 或 **此前已确定的两个**）。
- 同理：`X is a cause of Y`（许多原因之一）vs `X is the cause of Y`（唯一原因）；`This effect may hide a connection between A and B.` vs `… hide the connection between A and B.`
- 有时意义无差别，**差别只在"假定的读者知识"**：`Ø Improvements in virus-detecting software have recently become very important.`（读者可能不知道这些改进）vs `The improvements in virus-detecting software have recently become very important.`（读者共享高知识水平）。
- **对期刊投稿的启示**：投给读者群宽的期刊，**不能假定关键术语与概念人人皆知**，首次提及时可能需要用 a/an，并**定义或解释**；反之，若领域很窄且确信读者都熟悉，用 the 可能可接受（书 p126）。

**指代与冠词的交叉**：Results 中 `a/the cause of` 的差异见 §2.2（1）；标题中 `A/An` 开头用于传达"a new offer"（书 p309）；Unit 8 的定性是**隐形错误**：`Watch out for errors that are invisible, i.e. when both a and the are grammatically correct but the choice will affect the meaning.`（原例：`The cords should be connected to φ /the two outlets.`，书 p322）

## 2.6 介词

**原出现单元**：Unit 2（pp.115–120，系统来源）、Unit 8（pp.322–323，新增陷阱）、Unit 7（pp.307–308，标题介词）、Unit 2 词块（p118 动词+介词搭配簇）、Unit 1（p61 信号词中的介词性连接）。

**（1）意义级对比（先记两条）**

- `evidence of` = 可测量的、存在的迹象；`evidence for` = 可能存在/或许存在的迹象（书 p115；Unit 8 重复，书 p322）。
- **`X was substituted for Y` 意为 X 取代了 Y；`X was substituted with Y` 意为 Y 取代了 X**（书 p115）。
- Unit 8 增加：`improved up to 3 times` vs `improved by up to 3 times`（书 p322）。

**（2）五条可执行策略（书 pp.115–120）**

1. **先开始注意介词**：原文练习统计一段文字中 `of for with on in through at over from about` 的次数（答案分别为 **8、11、15、11、20**）——用以训练敏感度（书 pp.115–116）。
2. **关注目标文章中的 verb + preposition clusters**（书 p118）。示例：`was applied across all cohorts`｜`was calcinated at 450°c`[原文如此]｜`was calcined in static air`｜`was calibrated against real-world data`｜`was considered for analysis`｜`was converted into fatty acids`｜`was cultured on coated plates`｜`was cured in an autoclave`｜`was degassed in a vacuum oven`｜`was degassed with argon`｜`was degreased in acetone`｜`was divided into rectangular cells`｜`was exposed to heat`｜`was extracted from frozen samples`｜`was extracted with a Hilbert transform`｜`was fitted with a plastic tube`｜`was grit-blasted with grade 60 grit`｜`was ground with a mortar and pestle`｜`was grown on a mineral medium`｜`was incubated for 2 h`｜`was infused within 5 minutes`｜`was input into a model`｜`was labelled with a dye`｜`was maintained in this condition`｜`was manufactured in mild steel`｜`was manufactured with steel pins`｜`was mapped against the reference genome`｜`was normalised for exon length`｜`was performed at quasi-static rates`｜`was performed on tissue samples`｜`was placed under vacuum`｜`was precipitated with isopropanol`｜`was propagated in 1:3 ratio`｜`was propagated with Invitrogen`｜`was replaced with feed gas`｜`was retrieved from the database`｜`was spread onto the surface`｜`was subjected to impact`｜`was transferred into a well plate`｜`was treated with primary antibodies`。原文要求 `Add to this list by mining your target articles.`
   Unit 8 的同一动作（书 p322）：从近期文献挖 `subject-specific verb + preposition clusters`：`normalised FOR exon length`、`performed AT quasi-static rates`、`performed ON tissue samples`、`placed UNDER vacuum`。
3. **把介词换成使意义明确的词**（句首尤其重要）（书 p118–119）：`From this estimation, we ranked…` → **`Using this estimation, we ranked the search results and then classified them according to size.`**；Unit 8 同例：`From this estimation we changed the temperature of the sample` → `Using this estimation we changed the temperature of the sample.`（书 pp.322–323）
   - `With the increase in computer processing speeds, …` 有歧义：是"由于"还是"同时"？（书 p119）
   - `With many attempts, we were able to position the probe…` 是"多次失败后"还是"在若干情形下"？（书 p119）
4. **找介词使用规律**（书 p119）：目标文章中 **`USING` 比 `with` 更常见**，**`by` 常出现在以 -ing 结尾的工艺描述前**。
   - USING 例：`was analysed USING a computing cluster`、`was assessed USING an Instron 4507`、`was calculated USING another`、`was carried out USING a Ministat 251`、`was computed USING a flow algorithm`、`was conducted USING an optical microscope`、`was controlled USING an automatic system`、`was designed USING an eArray platform`、`was developed USING a laser`、`was evaluated USING an analog scale`、`was evaporated USING a rotary evaporator`、`was extracted USING a reagent solution`、`was filtered USING a Butterworth filter`、`was generated USING clinical covariates`、`was improved USING a shielding gas mix`、`was modeled USING 13 elastic elements`、`was mounted USING adhesive tape`、`was optimised USING Bayesian criteria`、`was performed USING an X-ray diffractometer`、`was performed USING a mapping algorithm`、`was quantified USING the phase-locking factor`、`was removed USING a grinder`、`was reported USING the HGVS nomenclature`、`was selected USING a filter`、`was solved USING the penalty method`、`was sonicated USING a Branson Sonificator`
   - by + -ing 例：`was achieved BY electroplating`、`was assessed BY analysing…`、`was assessed BY angiography`、`was calculated BY dividing…`、`was confirmed BY immunostaining`、`was determined BY measuring ATP levels`、`was differentiated BY withdrawal of bFGF`、`was extracted BY applying a filter`、`was formed BY incorporating…`、`was initiated BY administering a drug`、`was precipitated BY adding…`、`was prepared BY chemical vapour deposition`、`was prepared BY dissolving…`、`was replaced BY bFGF`
5. **避免介词短语连缀（strings of prepositional phrases）**（书 p120）：连缀的介词短语互相"感染"造成语义混乱。
   - 差例 `He gave a lecture about liver cancer at the hospital last January` → 改 `Last January he gave a lecture at the hospital; the subject was liver cancer.`
   - 差例 `The tray with the samples was placed in the oven at 250°C with protective gloves to avoid injury for one hour.` → 改 `The tray containing the samples was placed in the oven for one hour at 250°C. Protective gloves were worn to avoid injury.`
   - 新颖性被淹没的例子：`This is the first study to use X-ray imaging over a period of five years to measure contact angles within oil-bearing rocks at reservoir conditions.`（"first"到底指哪一层？）

**（3）`with` 专项（书 p119；Unit 8 重复，书 p322）**

- `with` 有极宽的意义范围（USING / HAVING 等）：`a dog with one eye` 可指 USING 也可指 HAVING；`hit with a metal bar` 含故意，`hit by a metal bar` 暗示非故意。
- **`X was coated with Y` 中 Y 多为材料；若要表达"工艺"，写 `X was coated by (doing) Y` 更清楚。**
- Unit 8 给出的替换清单：`using, having, in combination with, together with, as a result of, at the same time as`（书 p322）。
- Unit 8 错误示范（原文用括号标出每个介词短语）：`We apply [in A] the concept [of B] [to C] [through D] [with E] to constrain the timing [of F] [for G].` → 完整句 `We apply in this approach the concept of host rock to intrusive relationships through seismic-stratigraphic analysis with conventional biostratigraphic dating to constrain the timing of the events for the first time.`（书 p323）

**（4）`for the first time` 的位置（书 p323，Unit 8 独有）**

- 错误示范：`X-ray imaging was used to measure contact angles within oil-bearing rocks at reservoir conditions for the first time.`
- 三层可能读法：首次**使用 X 射线成像测量接触角**？首次**在含油岩石中测量接触角**？还是首次**在储层条件下于含油岩石中测量接触角**？
- 规则：新颖性标记必须**紧贴**它所限定的成分，不得让读者无法判定新颖性的范围。

**（5）标题中的介词（书 pp.307–308）**

- 介词过载会让标题 `grammatically unwieldy`。反例：`A filter with a model for the contrast sensitivity of the visual system for modeling human performance in detection tasks with different viewing angles` —— `hard for the reader to deconstruct`；解决办法：`Including some items in the keyword list instead of the title may resolve the problem.`
- 介词"没有可辨识的内容，却不是把概念黏起来的胶水"（原文指向 Section 2.5.2，即本主题），**因介词使用草率造成的歧义在标题中尤其有害**。
- 消歧技术：**用意义明确的词替换介词**——`Low-complexity domain interactions that control gene transcription`（更清楚）vs `Low-complexity domain interactions in gene transcription`。
- 自查提问：`How many prepositions are in the titles of articles in your target journals? Which prepositions are most common? Can you identify any ambiguities?`

## 2.7 -ing 歧义

**原出现单元**：Unit 8（pp.324–325，系统来源）、Unit 8（p318，句首 -ing）、Unit 2（p119，`by + -ing` 搭配）。

**根因（书 p324）**：`-ing forms are inherently ambiguous in that they exhibit no verb tense or singular/plural marker.`

**错误示范 1（施动者不明）**（书 pp.324–325）
`MTCs are deposits resulting from creep, slide, slump and flow processes producing a variety of rheological units and strain sequences encapsulating extensional, translational and compressional domains.`
→ 不清楚是 deposits 还是 processes 在 `producing`，也不清楚究竟是什么在 `encapsulating`。

**错误示范 2（附着范围不明）**（书 p325）
`These dyes are notable for their small Stokes shift, high fluorescent quantum yields and sharp excitation and emission peaks contributing to overall brightness.`
→ 不清楚是三项特征共同 `contributing`，还是只有 sharp excitation and emission peaks，甚至只有 emission peaks。

**意义谱系也不唯一**（书 p325）
`Membranes remain flat storing elastic curvature stress.` → `(by storing? when storing? thereby storing?)`

**原文练习的 A–J 含义谱系（书 p325）**
A `by [verb]ing`；B `as a result of [verb]ing`；C `on the basis of [verb]ing`；D `when [verb]ing`；E `thereby [verb]ing`；F `therefore verbing`；G `which is/are capable of [verb]ing`；H `which/that [verb]`；I `if we/it/they [verb]`；J `because it/they [verb]`
待判断句：1. `The ions are coordinated by the C2 domain and by the phospholipids forming a ternary complex.` 2. 上文的 dyes 句 3. `The lipids can influence protein functions indirectly altering the biophysical properties of the membrane.`
→ **练习答案原文未明确**（见 Part 5.3）。

**两条附加规则**

1. **避免以 -ing 形式开句**：`Avoid beginning sentences with -ing forms (see pages 324–325) or prepositions (especially for and with).`（书 p318）
2. `by + -ing` 是合法的工艺描述结构，但必须保证施动者与附着范围唯一清晰（书 p119 的 `was achieved BY electroplating` 系列）。

**修正手段（由上述规则归纳）**：把 -ing 还原为显式从句（`which/that`、`because`、`when`、`thereby`）、补出施动者、把长串 -ing 拆成独立句。

## 2.8 指代 reference（this / these / that / those / it / which）

**原出现单元**：Unit 8（p323，系统来源）、Unit 6（p266，摘要高风险区）、Unit 1（pp.57–58，pro-form 与不清指代）。

**规则（书 p323）**

1. **给 this/these/that/those 补名词**：`Add a noun to this/these/that/those (e.g. this system/model/theory) so that the reader knows what you are referring to, especially at the start of a sentence or paragraph.`
2. **多种可能就还原名词**：`Replace it/which/this etc. with the noun or phrase it refers to if there is more than one possibility.`
3. **边界自检**：`Check for ambiguity. Where does the referent of your it/which/this etc. begin and end? Is that clear to the reader?`

**Unit 1 的 pro-form 规则（书 pp.57–58）**

- `when you use pro-forms, it is easier for the reader if you repeat exactly the same noun as you used the first time. If you have described something as a device, the pro-form you use to refer to it next time should be this device, not this technique or this method.`
- 粘合句子的示例：`This combination formed a novel lightweight copolymer…`｜`These patterns include increased delta power…`｜`This steady-state approach cannot distinguish…`｜`These methods rely on data structures…`｜`This shortcoming is, in part, responsible for…`
- 反例（指代不明）：`This suggests that…` 与 `they are easily detectable`。
- 分段/分句开头的 pro-form 最危险；`You can begin sentences with It, They, These or This, but it may be difficult…`（书 p58）

**Unit 6 的摘要专项（书 p266）**

- `it / which / this` 的指代对象对作者显而易见、对读者不清楚；有歧义时**在 this 后加名词或重复名词/短语**。
- 实证：摘要 4 为避免歧义，`the hybrid method is repeated no less than four times within a 140-word Abstract`。

## 2.9 adverb location（副词位置）

**原出现单元**：Unit 8（pp.323–324，唯一系统来源）、Unit 3（p150，功能信号在长句中的位置）。

**规则（书 p323）**：`Some adverbs such as just, only, simply change the meaning or focus of the information depending on their location.`

**六句六义配对（原文答案：1 = C, 2 = F, 3 = E, 4 = A, 5 = B, 6 = D；书 pp.323–324）**

| # | 句子 | 含义 |
|---|---|---|
| 1 | `Only we analysed models that can simulate the patient's molecular response.` | `No other researchers analysed models that can simulate the patient's molecular response.` |
| 2 | `We only analysed models that can simulate the patient's molecular response.` | `We didn't do anything else apart from analysing models…` |
| 3 | `We analysed only models that can simulate the patient's molecular response.` | `We didn't analyse any other models apart from those that can simulate…` |
| 4 | `We analysed models that can only simulate the patient's molecular response.` | `The models we analysed were not able to do anything else apart from simulating…` |
| 5 | `We analysed models that can simulate only the patient's molecular response.` | `…able to simulate just one parameter (the patient's molecular response), but not others.` |
| 6 | `We analysed models that can simulate the patient's only molecular response.` | `The patient had just one molecular response, and we analysed models that can simulate it.` |

> 模板要点：副词位置一旦移动，主张范围（谁做、做什么、做多少）随之改变，属"隐形错误"，必须逐句核对。

**功能信号的位置（书 p150）**：短句中 `However,` 放哪都行；**长句中信号应靠近句首**，因为长句以信号结尾会迫使读者"回环"重读整句。对比：`In such cases, the patient may require ... , unfortunately.` vs `Unfortunately, in such cases, the patient may require ...`

## 2.10 弱动词与词汇准确性

**原出现单元**：Unit 8（pp.326–328，系统来源）、Unit 1（p45 用精确动词代替 did/showed/found）、Unit 6（p266 术语一致）、Unit 4（p222 不要为风格改词）、Unit 8（p326 术语一致）。

**（1）弱动词替换表（书 p326，逐字保留）**

| 弱动词 | 可替换为 |
|---|---|
| `have` | `possess, contain, include` |
| `get` | `obtain, achieve, become` |
| `bring` | `provide, yield, cause` |
| `keep` | `retain, maintain, conserve` |
| `spread` | `distribute, diffuse, scatter, extend` |

> 与 Unit 1 的呼吁同源：`You can't spend the rest of your life writing they did/showed/found; sometimes you need to be more specific, so look for verbs describing what exactly was done, for example calculated, monitored, identified.`（书 p45）；通用学术动词见 Appendix B: Research Verbs（书 pp.102–103 指向）。

**（2）术语一致性（首要，书 p326）**

`Terminology should be used consistently. A tool should not become a strategy and then a device and then an approach and then a methodology and then a framework and then a technique.`
同一要求在三处出现：Unit 6（书 p266：`If something is described as an approach, it should not suddenly become a scheme; similarly, a scheme should not suddenly become a framework, a model should not suddenly become a method, and a tool should not suddenly become a device.` 否则 `blurs the identity of what you are offering`）；Unit 4（书 p222：回顾前文时**不要为风格改语言**，重复相同词语有利，因为"创造成回声"）；Unit 8（同上）。

**（3）同义词词典是敌人（书 p326）**

`The thesaurus is not your friend, and it is the global writer and reader's enemy. No two words have exactly the same meaning in every context so there is no such thing as a perfect synonym.`
- 替换词可能范围更宽，或更负面/更正面/更中性；非母语作者风险：`A non-native writer risks choosing a thesaurus option whose meaning is so distant from the original word that the reader does not recognise it as an alternate.`
- 例：`noticeable is not the same as conspicuous. famous is not the same as well-known.`
- 结论：`Don't be afraid to repeat the same word or phrase if that makes reading easier.`
- 正面示范（保持同一术语 `steady state` / `unconsciousness` 复用）：`Most studies have focused on a deep steady state of general anesthesia and have not used a systematic behavioral measure to track the transition into unconsciousness. This steady-state approach cannot distinguish between patterns that are characteristic of a deeply anesthetized brain and patterns that arise at the onset of unconsciousness. Unconsciousness can occur in tens of seconds, but many neurophysiological features continue to fluctuate for minutes after induction.`（书 p326）

**（4）术语验证：Google Scholar 双查（书 pp.326–327）**

`First put the term into Google Scholar in quotation marks (") to check where, when and how many times that exact phrase appears in the literature; then enter the same term again without quotation marks and compare the two sets of data.`
`New terminology is created very quickly in science, and the term you have been using may have been superseded or steamrollered by an influential research group who are naming it differently. Keep checking.`

**（5）包含关系、respectively、连字符（书 p327）**

- `comprise / consist of / be made up of / be composed of` 后接**全部**成分；`include` 后接**部分**成分。
- `respectively` 意为"按刚才提及的同一顺序"：`T helper and T suppressor cells are restricted by the A and E molecules respectively.`
- 连字符改变数量含义：`We used five centimetre-wide layers`（五层，每层一厘米宽）vs `We used five-centimetre wide layers`（所用每层都是五厘米宽）；原理：`Joining two or more words with a hyphen makes them act as a single concept to describe the noun that follows them.`

**（6）易混词对（书 pp.327–328，逐字保留）**

| 词对 | 区分 |
|---|---|
| `alternately` / `alternatively` | `alternately = one after the other or in sequence`；`alternatively = on the other hand, instead or as an alternative` |
| `beside` / `besides` | `beside = next/close to`；`besides = apart from/in addition to` |
| `criterion` / `criteria` | `criterion` 单数；`criteria` 复数 |
| `different` / `various` | `different = not the same`；`various = a range of` |
| `e.g.` / `i.e.` | `e.g. = for example`；`i.e. = in other words` |
| `effective` / `efficient` | `effective = it works`；`efficient = it works well` |
| `phenomenon` / `phenomena` | `phenomenon` 单数；`phenomena` 复数 |
| `to adapt` / `to adopt` | `to adapt = to modify/adjust`；`to adopt = to choose to use/follow` |
| `to affect` / `to effect` | `to affect = to influence/to have an effect on`；`to effect = to cause/bring about` |
| `to imply` / `to infer` | `to imply = to suggest, to indicate`；`to infer = to conclude, to deduce` |

## 2.11 signalling connectors（信号连接词）

**原出现单元**：Unit 1（pp.59–61，六组功能分类）、Unit 8（pp.319–320，三连自检 + 错误示范）、Unit 1（pp.56–58，四种衔接法）、Unit 3（p150，信号位置）。

**（1）通用警告（书 p319）**

`Signals such as moreover and therefore are not just glue to join ideas or sentences together; they are emphatic, and have specific and restricted meanings.` 用错则 `the reader sets off in the wrong direction and the text becomes unintelligible.`
用量警告（书 p61）：`It's not necessary (and it looks formulaic) to start every sentence with a signal. Signals are emphatic, and starting each sentence with one creates a jerky, over-emphatic text.` 替代方案是 **repetition linkage**——跨句重复词，尤其是句首重复。

**（2）六组功能分类（Unit 1，书 pp.59–61，含原文填空示例）**

| 功能 | 词块 | 原文填空示例 |
|---|---|---|
| **CAUSE** | `due to (the fact that)` / `on account of (the fact that)` / `in view of (the fact that)` / `as` / `because` / `since` | `The experiment was unsuccessful ________ the measuring instruments were inaccurate.` / `… ________ the inaccuracy of the measuring instruments.` |
| **RESULT** | `therefore` / `consequently` / `hence` / `as a result` / `thus` / `so` | `The measuring instruments were calibrated accurately, ________ the experiment was successful.` |
| **CONTRAST/DIFFERENCE** | `however` / `whereas` / `but` / `on the other hand` / `while` / `by contrast` / `in contrast` | `British students are all vegetarians, __________ Norwegian students eat meat every day.` |
| **UNEXPECTEDNESS** | A（从句首）`although` / `even though` / `though`；B（+名词）`despite` / `in spite of` / `regardless of` / `notwithstanding`；C（分号后）`nevertheless` / `however` / `yet` / `but` / `nonetheless` / `even so` | `_______ it was difficult, a solution was quickly found.` / `_______ the difficulty, …` / `It was difficult; ________ …` |
| **ADDITION/LISTING** | `in addition` / `moreover` / `furthermore` / `also` / `secondly (etc.)` / `in the second place (etc.)` / `what is more,` | — |
| **TRANSITION** | `with regard to` / `as to` / `regarding` / `with respect to` / `as for` / `turning now to` | — |

**易错提醒（书 pp.59–61）**：`as` 亦可表 when，`since` 亦可表 from that time，`while` 常表 at that/the same time——有混淆可能就换信号词；`on the contrary` / `conversely` 表达的是**正相反**，不能用来表达单纯差异；`however` / `but` 同时属 CONTRAST 与 UNEXPECTEDNESS，若要强调出乎意料，改用该组其他词；`besides` 与 ADDITION 组近义但 `more powerful`，更适合说服性语境。
**两条功能一致性规则（书 p59）**：`Moreover` 开头的句子必须与上一句**功能相同**；`Therefore / Consequently` 开头必须给出**与可识别原因直接相连**的结果，因果关系要显明或写明，`rather than existing mainly in the mind of the writer`。

**（3）三连自检问句（Unit 8，书 pp.319–320）**

- `therefore`：`When you begin a sentence or clause with therefore, ask yourself: is it really a direct consequence or result of the previous sentence or clause?` 错误示范：`The most important phenomenon is the breakup length, and therefore an electrical conductivity probe technique was used to calculate breakup length.`
- `for example`：`does it really illustrate or stand as an example of the general statement in the previous sentence?`
- `in other words`：`is it really the same thing in other words?`

**（4）四种句子衔接法（Unit 1，书 pp.56–58）**

| # | 方法 | 原例 | 操作规则 |
|---|---|---|---|
| 1 | **Overlap/重复前句信息** | `This steady-state approach cannot distinguish between patterns… **Unconsciousness** can occur in tens of seconds…`；`…information transfer between distant (>2 cm) cortical networks is impaired. **Cortical networks** therefore are fragmented…` | 句首重复前句尾部信息 |
| 2 | **Pro-form**（`This method`、`These systems`） | `This combination formed a novel lightweight copolymer…`；`This shortcoming is, in part, responsible for…` | **重复同一个名词**（见 §2.8） |
| 3 | **分号连接** | `…usually takes many hours; this means that tests are rarely repeated.`；`…cannot be identified; these unwanted reflections are a source of coherent noise…` | `Joining sentences with a semicolon works well when there are two consecutive sentences that are very closely related, particularly if one of them is short.` 但**分号会拉长句子**，须检查总长度 |
| 4 | **信号词** | `therefore`、`however` 等 | 见上；`signals are not simply 'glue' to hold sentences together; if they are not used accurately, they can do more harm than good.` |

**句间空隙的定性（书 p56）**：`The gap between sentences is a dangerous space. Your job as a writer is to close the gap as tightly as possible…`；Unit 8 版（书 p316）：`The space between a full stop and the next capital letter is a dangerous space for you and for your reader.` 原因：`There's thinking time in there, and a desire to move on to the next piece of information without really considering how it relates to the previous sentence.`
**自编辑用途**：检查句间是否显式衔接是**很有价值的自编辑工具**（书 p61）。

## 2.12 段落与句子组织

**原出现单元**：Unit 1（pp.56–68，段落规划 + 句长 + 衔接）、Unit 8（pp.316–320，句内信息顺序 + 段长 + 入口句）、Unit 3（pp.145–146，Results 开篇框架）、Unit 4（p191，forward-moving narrative）、Unit 6（p289，wrap 减少的代价）、Unit 2（p79，wall before bricks）。

**（1）段落（书 pp.66–68；Unit 8 pp.316–317 复述）**

- 段落是**有力的非语言文本元素**；好段落通常**只有一个 unifying function**，每句乃至每句的每个部分都须服务于该功能——`'loose' or irrelevant items interrupt the narrative and cause confusion`。
- **两大常见错误**：① 成串的短段/单句段（`very jerky`，因为每段都触发读者"要换话题了"的条件反射）；② 段落过长、迷失方向（一个想法开头、另一个想法结尾，或含太多想法，等于"dumping"信息）。
- **长度**：研究论文平均段落长约 **150–170 词**；`it is unusual to find a research article in which many or most paragraphs are over 230 words or under 80`；Unit 8 补充 `Avoid whole-page paragraphs and clusters of short or single-sentence paragraphs.` **务必按本领域目标文本核定。**
- **一段一功能**：`A paragraph which has a single function is more successful and easier to write and read than one with multiple functions.`
- **首句（entry sentence）规则**：学术写作惯例是**用首句/首短语呈现该段的 topic、function 或 aim**；**当主题偏离首句太远时，就开始新段落，通常配新的 entry sentence**。
- **顺序反转**：`Avoid making statements early in the paragraph that won't make sense until the reader sees the rest of the paragraph. Consider reversing the order.`
- **删除 loose sentences**：`Don't add loose sentences, i.e. sentences that are irrelevant to the function of the paragraph but that you include because they were in your notes or were suggested by a colleague.` → `delete it or create a narrative around it that respects the function of the paragraph.`
- **段落入口句示例**（书 p317）：`We now consider the connection between…`｜`To address this question, we used…`｜`Taken together, these studies suggest that…`｜`There are two potential alternatives to such an approach…`
- **段落规划操作步骤（书 p68）**：列出每个 topic/concept/idea 并按对读者最合理的逻辑排序；为每个 topic 列出 bullet points 并按逻辑排序；决定每个 topic 需要几段；检查每段在该 topic 中有明确功能（提供事实背景／描述优缺点／呈现理论／解释你为何同意某观点／提供详例／比较技术）；确保段落功能对读者清楚；考虑在段首使用 statement of intent（短语清单见 §1.3 E-6）。
- **读图与段落**：skim 的第 5 步即"快速看小标题与每段首句以得到全文地图"，故首句承担全篇"地图"功能（书 p67）。

**（2）句内信息顺序（书 p318）**

`Known information generally comes first and is used as a platform for launching new/unknown information later in the sentence.`
机理：`This facilitates sentence-to-sentence linkage, as the new information towards the end of the sentence then becomes the known/old information on which to build the next sentence.`（旧→新链式推进）

**（3）句长与密度（书 pp.318–319；另见 §2.1 与 Part 4）**

- 总纲：`The reading speed of the eye should correlate reasonably well with the processing speed of the brain.` 若读者频繁回读过长/过密句子就会变慢；`Consecutive long sentences are particularly problematic.`
- 五条理由：① 句子越长，作者越难控制语法、避免歧义；② 过长句子变得 `'flat'`，重点被淹没，读者看不到 principal focus；③ 组件太多，组件间关系作者难管、读者难懂；④ 过密句塞进太多名词与介词短语，**主动词被掩盖**；⑤ 风险因子：`more than one and, more than one which, too many prepositions, and too many nouns`。
- 错误示范（多重 which 叠套）：`Exploration risk in most inverted rift basins is related to uncertainties which stem from a poor understanding of the structural style and distribution of inversion structures, which are controlled by the presence and orientation of pre-existing structures and the magnitude and orientation of shortening stress.`
- 错误示范（名词与介词堆叠、动词淹没）：`This paper presents the fundamental framework to facilitate transition from traditional deterministic to innovative probabilistic electricity grid operating and design standards, through the paradigm shift in the provision of security from redundancy in assets to exploiting emerging Smart Grid technologies and advanced control systems.`
- `and / or` 的歧义：`and and or can drag things with it that you don't want, or fail to drag things that you do want, creating ambiguity.` 错误示范：`We found an increase in demand and deployment of non-renewable energy sources.`（是"需求与部署都上升"，还是"发现了两件事：需求上升、非可再生能源的部署——后者并未上升"？）→ 并列结构必须让读者唯一确定连接范围。

**（4）句子起始（书 pp.317–318）**

- 总纲：`The way sentences start is crucial to the readability of the text.`
- **三种衔接方式**：`Connect sentences by starting the sentence with an overlapping repeat, a pro-form such as This/These + noun, or a signalling connector such as However.`
- **用开头标记重要性**：`Interestingly,/Remarkably,/It is noteworthy that/It should be emphasised that/It is important to note that`
- **框架效应**：`The way you start a sentence provides a 'frame' that helps the reader to process the content.`
- **禁忌**：`Avoid beginning sentences with -ing forms (see pages 324–325) or prepositions (especially for and with).`（书 p318）

**（5）叙事包裹的三个层次（跨单元同源表述）**

| 层次 | 原文 | 书页 |
|---|---|---|
| 段内/句间 | `The gap between sentences is a dangerous space.` | p56 |
| 节内 | `The key to a successful Discussion section is a forward-moving, well-organised narrative wrap…` | p191 |
| 全篇 | `Data and information alone have no intrinsic or obvious function for the reader without a narrative.`；`the more the narrative 'wrap' is reduced, the less coherent that data or information becomes.` | p314、p289 |
| 起手式 | `show your reader the wall before you start to talk about the bricks!`（Methods）；`sees the 'wall' before you — and they — look at the individual 'bricks'`（Results） | p79、p145 |

## 2.13 评价性语言与"裸数字"

**原出现单元**：Unit 3（pp.148–149、175–177）、Unit 8（p316）、Unit 6（p288）、Unit 5（组件 6，书 p257）。

**规则**

1. **数据不会自己说话**：`data and results do not speak for themselves`（书 p148、p187）。
2. **禁止裸数字**：`don't just provide data in 'naked numbers'; add evaluative comments such as only 43% or as high as 43% to show what the data means in the context of the study.`（书 p316）；Abstract 同理：`Adding language to numbers (e.g. only 38% or as high as 38%) ensures that the numbers will not be misinterpreted at this crucial stage.`（书 p288）
3. **强/弱框架可选**（书 p149）：同样 23%，可写成强结果 `in as many as 23% of cases`，也可写成弱结果 `in only 23% of cases`。
4. **评价性语言可替代数字**：`in many cases`；也可与数字共现：`only 23 ml`（书 p148）。
5. **频率修饰是必需的**（书 p146）：若作者只写 `x occurred` 而不加频率修饰，读者可能无法恰当评价结果。
6. **评价性语言该放多少，用逆向工程决定**：在目标文章中**划线/高亮**评价性实例，从而明确"用不用、何时用、怎么用、用多少"；原文指出研究者常否认自己领域会这样做，直到被指出目标文章中的评价性语言为止（书 p149–150）。
7. **标出重要性的手段**：句首用 `It is important to note that… / Importantly, / It is significant that…`（书 p151）。
8. **"最佳结果当典型结果"的写法**（书 p151）：先给一般性陈述，再用 `for example` 引出最佳结果——`The SFS results are generally in very good agreement with their FE counterparts; for example, at midspan the values are almost identical.` 原文提醒读者在读文献时**留意这一手法**。
9. **不用感叹号，用 '!-substitutes'**（书 p150）：科学写作者一般不用感叹号，即使结果非常激动人心；他们用 `striking` 这类词制造"wow!"感；完整清单见书 pp.225–226（即 §1.6 E-3 的 `compelling / crucial / dramatic / exceptional / extraordinary / outstanding / remarkable / superb / striking / undeniable / unique / unprecedented / unquestionably / vital` 等）。
10. **主观/客观判据**（书 p143）：说一个量"高于"另一个是**客观真理**（`higher`）；说它"高"是**主观评价**（`high`）。客观描述比主观描述更难在目标文章中找到，且客观语言出现时往往带主观"附加成分"（`slightly lower`/`much lower` 比单独的 `lower` 更常见），因为纯客观描述"没有告诉读者任何他们看图不知道的事"。

# Part 3 全稿统一检查清单

> **来源合并**：Unit 1（书 pp.69–71）、Unit 2（书 pp.136–137）、Unit 3（书 pp.186–187）、Unit 4（书 pp.242 等）、Unit 5（规则转写）、Unit 6（书 p297）、Unit 7（书 pp.301–312）、Unit 8（书 pp.315–330）八份清单**去重合并**，按四层组织。
> **权重提示**：原则 5 明确"组织可补语言，语言不可补组织"，故 **3.1 层优先于 3.3 层**（书 p314）。

## 3.1 第一层：结构 / 叙事

- [ ] 已按重要性排序列出研究的 achievements，并分别写明对 (i) knowledge、(ii) research、(iii) the real world 的 contribution/impact（书 p315）
- [ ] 上述 value 三要素已同步嵌入标题与各部分规划（书 p315）
- [ ] 全文有一句显性、一致的 take-home message（magnetic south），且各节都朝它推进（书 p314）
- [ ] achievement/contribution 用明确的 happy words 而非暗示；contribution 具体、impact 显性（书 p315）
- [ ] 开始写整句之前，已完成各节信息顺序的规划（书 p315）
- [ ] 已按 Part 0.6 的 Unit ↔ 章节对照，为每一节选出对应的通用模型组件（Introduction 4／Methods 6+1／Results 4 组 11 条／Discussion 9／Conclusion 11／Abstract 9／Title 6 检查点）
- [ ] 已用目标文章（≥2 篇同类）逆向工程各节组件与顺序，并与通用模型整合（书 pp.5、77、142、154、193–194、246、269、303）
- [ ] 每个子节划分对读者有帮助；小标题准确代表内容（书 p316）
- [ ] 小标题关键词在小节开头尽早出现，并从中展开（书 p316）
- [ ] 小节开头没有从极 general 直接跳到极 specific/technical（书 p316）
- [ ] 句号与下一个大写字母之间的"危险空间"已检查：相邻句之间有显性逻辑衔接（书 p316）
- [ ] 每处数据都带评价性评论（only 43% / as high as 43%），没有"裸数字"（书 p316）
- [ ] 每段信息都让读者知道它在"做什么"（引入问题/解法？正例/反例？）（书 p316）
- [ ] 每句话都能回答读者心中的"so what?"；必要时补 `suggesting that.../which means that...`（书 p316）
- [ ] 已评估读者群（跨学科、非专家、未来读者）及其对前文内容的记忆假设（书 p317）
- [ ] 已规划每段的功能并按逻辑排序；一段一功能（书 pp.66、317）
- [ ] 无整页长段，也无连续短句段/单句段；段落均值约 150–170 词（书 pp.66、317）
- [ ] 每段以叙事入口句开头（`We now consider…` / `To address this question, we used…` / `Taken together, these studies suggest that…` / `There are two potential alternatives to such an approach…`）（书 p317）
- [ ] 段内没有"读到后面才说得通"的前置陈述；必要时已反转顺序（书 p317）
- [ ] 已删除所有 loose sentences（来自笔记或他人建议但与段落功能无关者）（书 p317）
- [ ] 每节都考虑过 graphic 的位置与包住它的叙述框架（书 pp.146–147）
- [ ] 关键信息未被埋在无关细节里；发现的问题已在"出现处"首次提及并在文末呼应（书 pp.85–86、152、205–206）
- [ ] 已复核 Introduction 的 aim 与最终结果一致；标题承诺在正文（尤其 Conclusion）兑现（书 pp.157、310）
- [ ] 标题关键词与 keyword list 互补而非重复（书 p306）

## 3.2 第二层：句子

- [ ] 句内信息按"旧信息在前、新信息在后"排列，且新信息成为下一句的旧信息（书 p318）
- [ ] 句子衔接使用重叠重复、`This/These + noun`、或信号连接词（书 p318）
- [ ] 重要信息以 `Interestingly,/Remarkably,/It is noteworthy that/It should be emphasised that/It is important to note that` 标记（书 pp.318、151）
- [ ] 没有以 `-ing` 形式开头，也没有以介词（尤其 for/with）开头（书 p318）
- [ ] 平均句长约 20–26 词；没有连续长句（书 pp.318–319）
- [ ] 无"扁平化"长句（重点被淹没）（书 p319）
- [ ] 无过密句（名词与介词短语堆叠导致主动词被掩盖）（书 p319）
- [ ] 已排查 4 项风险因子：>1 个 `and`、>1 个 `which`、过多介词、过多名词（书 p319）
- [ ] 所有 `and` / `or` 的连接范围唯一可解（书 p319）
- [ ] 每个 `therefore` 前自问：是否真是上句/上分句的直接结果（书 pp.319–320）
- [ ] 每个 `for example` 前自问：是否真是上句一般性陈述的例证（书 p320）
- [ ] 每个 `in other words` 前自问：是否真是"换句话说"（书 p320）
- [ ] 没有每句都用信号词开头；必要时改用 repetition linkage（书 p61）
- [ ] `Moreover` 与前句功能相同；`However/but` 若表"出乎意料"已改用 UNEXPECTEDNESS 组词（书 pp.59–61）
- [ ] 用分号连接后已检查整句长度（书 p58）
- [ ] 长句中的功能信号靠近句首（书 p150）

## 3.3 第三层：语法与词汇

- [ ] 时态选择与信息功能一致；每次时态切换作者与读者都能知道原因（书 pp.53、55、321）
- [ ] `We found that x occurred`（报告）vs `We found that x occurs`（视为事实）的强度差异是有意选择（书 p321）
- [ ] 逐句核对过：Methods 的 Past Simple＝你做了什么；Present Simple＝标准流程/设备（书 pp.113–114）
- [ ] Results 的 Present Simple＝图形可见内容；Past Simple＝信息如何获得（书 p155）
- [ ] 无施动者不明的被动；已用 `here/in that study/in our model/in their approach` 标出施动者（书 pp.113–115、321）
- [ ] 被动动词没有拖到长句末尾（书 p321）
- [ ] `we/us/our` 的指代唯一（本作者 vs 本领域所有人）；泛指时改用 `It is now possible to…` 类结构（书 pp.321–322）
- [ ] 无"非人主语"抢走自己的贡献；`Theoretical modelling suggests…` 类句已明确施动者（书 p322）
- [ ] `It is argued that…` 类句子已明确是 `We argue that…` 还是 `It is argued by others that…`；**摘要中尤其已核查**（书 pp.322、250）
- [ ] Conclusion 的成就句至少用了四项归属手段之一（Past Simple/Present Perfect、主动、人称主语、显式指向本文的语言）（书 p261）
- [ ] 已排查"隐形冠词错误"：a/the 都合语法但改变含义处已确认（书 p322）
- [ ] 用 `the` 表达共享知识；宽读者群期刊首次提及关键术语用 a/an 并定义（书 pp.124–126、322）
- [ ] 不可数名词（steel, environment, technology 等）没有被当可数名词使用（书 pp.121–123、322）
- [ ] 介词选择未改变原意（`evidence of` vs `evidence for`；`improved up to` vs `improved by up to`；`substituted for` vs `substituted with`）（书 pp.115、322）
- [ ] 没有用介词承担实词功能（`From this estimation…` → `Using this estimation…`）（书 pp.118、322–323）
- [ ] 动词+介词搭配已对照本领域近期文献（`normalised FOR`、`performed AT/ON`、`placed UNDER` 式搭配簇）（书 pp.118、322）
- [ ] `with` 的歧义已消除（替换为 using/having/in combination with/together with/as a result of/at the same time as）（书 pp.119、322）
- [ ] 无介词短语串造成的歧义（书 pp.120、323）
- [ ] `for the first time` 等新颖性标记的位置不会误导读者的新颖性范围（书 p323）
- [ ] 主语与动词不相邻处已核查单复数一致；主谓在**逻辑上**可行（书 p323）
- [ ] `this/these/that/those` 均带名词；多种可能时 `it/which/this` 已还原为所指名词（书 pp.266、323）
- [ ] 指代对象的起止边界对读者清晰（书 p323）
- [ ] `just/only/simply` 等副词位置已逐句核对；主张范围未被意外改变（书 pp.323–324）
- [ ] 已删除或改写所有悬空 `-ing` 结构（施动者、附着范围、含义三方面均唯一）（书 pp.324–325）
- [ ] 已把 have/get/bring/keep/spread 等弱动词替换为精确动词（书 p326）
- [ ] 同一对象在全文中始终用同一术语（未在 tool→strategy→device→approach→methodology→framework→technique 之间滑动）（书 pp.266、326）
- [ ] 没有用同义词词典做机械替换；关键术语允许重复（书 pp.222、326）
- [ ] 技术术语已用 Google Scholar 加引号/不加引号对比验证（书 pp.326–327）
- [ ] `comprise/consist of/be made up of/be composed of`（全部成分）与 `include`（部分成分）使用正确（书 p327）
- [ ] `respectively` 的顺序与前文列举顺序一致（书 p327）
- [ ] 连字符用法未改变数量含义（`five centimetre-wide layers` vs `five-centimetre wide layers`）（书 p327）
- [ ] 易混词对已核对：alternately/alternatively、beside/besides、criterion/criteria、different/various、e.g./i.e.、effective/efficient、phenomenon/phenomena、adapt/adopt、affect/effect、imply/infer（书 pp.327–328）
- [ ] 单位/缩写符合目标期刊最新规定或 SI（如 `mL` 而非 `ml`；摘要中缩写首次给全称）（书 pp.81、268）
- [ ] 名词/复合名词能在标题与正文中逐层拆解（无 `oil can opener repair technician training programme funding problem` 式链条）（书 p307）

## 3.4 第四层：全局收口

- [ ] 每一句陈述的归属清晰：自己的假设/解释？已知真理？读者能分辨吗？需要引用吗？（书 p329）
- [ ] 确定性语言（certain vs speculating）与结果的证据强度逻辑一致（书 pp.183–186、329）
- [ ] 情态动词选择适当且一致；歧义处改用替代结构（`It is possible…`、`is able to`）（书 pp.231–232）
- [ ] 检查过 `can / can not / cannot`、`could not / cannot have / could not have`、`must not` vs `not necessary`、`did not need to` vs `need not have`（书 pp.234–239）
- [ ] 引用位于句中恰当位置；未把引用全部堆在句末造成"谁做了什么"的歧义（书 pp.11、329）
- [ ] 每条引用相关，且相关性通过叙事显式表达；引用量与目标期刊惯例相当（书 p198）
- [ ] "首次/最大"类断言已尽可能彻底检索；必要时使用 `to our knowledge`（书 p195）
- [ ] 未来工作被"指定方向"；明确区分"自己正在做"（`work is underway` 等）与"邀请他人做"（`future work should`）（书 pp.206、225）
- [ ] 已专项清除词汇性口头禅（indeed / in fact / basically / clearly 等）（书 p329）
- [ ] 已专项清除标点性口头禅：括号、成对破折号、多个逗号（书 pp.329–330）
- [ ] 成对破折号处已把含义"翻译"成语言（尤其面向国际读者）（书 p330）
- [ ] 括号内容已二次判断：重要则移出括号，不重要则删除（书 p330）
- [ ] 逗号堆叠处已拆分为若干相互良好衔接的独立句（书 p330）
- [ ] 摘要：12 项检查已完成（结构对位、重复比例、首句功能、happy 语言量、风险语言、成就优先级、逐句时态、归属歧义、指代歧义、平均句长、缩写可接受性、take-home message）（书 p297）
- [ ] 摘要：未写满字数上限；功能超出摘要自身范围（`The word limit is not a target.`）（书 p267）
- [ ] 结论：未把 Abstract 当作主要素材来源；结论不是摘要的改写或压缩（书 p246）
- [ ] 结论：非 Option 4 时控制在约 100–200 词 / 1–2 段（书 p245）
- [ ] 标题：7.5 七个维度已统计；7.6 承诺已在正文兑现（书 pp.309–310）
- [ ] 最后一步：用本书策略 reverse engineer 近期已发表范例，生成自己的稳健写作模型（书 p330）

# Part 4 机检规则候选：量化基准总表

> **使用方式**：本表供后续编写自检脚本。**数值一律忠实原文**，不外推、不四舍五入成"更好用"的整数；凡原文只说"要测量"而无阈值者，见 4.3，脚本只能**报告数值**、不能**判定违规**。

## 4.1 篇幅与长度类

| # | 指标 | 数值（原文） | 适用位置 | 书页（来源单元） | 机检用法建议 |
|---|---|---|---|---|---|
| 1 | 平均句长（STEMM 研究论文） | 约 **23** 词 | 全稿 | p58（U1） | 区间带外报警 |
| 2 | 平均句长（多数期刊） | **20–26** 词 | 全稿 | pp.318–319（U8） | 主阈值带 |
| 3 | 平均句长（18 篇范文摘要） | **22** 词 | Abstract | p267（U6） | 摘要专项参照 |
| 4 | 首读理解率 | <20 词 → **90%** 读者首读读懂；>40 词 → 仅 **10%** | 全稿 | p58（U1）；p267（U6）复述 | 超长句计数 |
| 5 | 平均段长 | **150–170** 词 | 全稿 | p66（U1）；p317（U8） | 段落均值 |
| 6 | 段落长度的"不常见"区间 | 多数段 **>230 词** 或 **<80 词**都不常见 | 全稿 | p66（U1） | 报警而非阻断 |
| 7 | Abstract 长度 | **80–250** 词，通常单段 | Abstract | p267（U6） | 区间外报警；同时查目标期刊均值 |
| 8 | Conclusion 长度 | **100–200** 词、1–2 个短段（Option 4 例外） | Conclusion | p245（U5） | 区间外报警 |
| 9 | Title 平均长度 | 约 **12** 词（"many journals"） | Title | p304（U7） | 均值比对 + 变异范围 |
| 10 | Introduction 练习范文长度 | 约 **250–350** 词（**训练基准，非期刊基准**） | Introduction | pp.69–70（U1） | 仅用于演练评分 |
| 11 | 摘要实例字数 | **140** 词（用于演示 `the hybrid method` 重复 4 次） | Abstract | p266（U6） | 说明性案例，非阈值 |
| 12 | 读者读一篇论文耗时 | **<30 分钟** | 全稿（决定自足性） | p191（U4） | 不可机检，用于设计理由 |

## 4.2 计数、语料规模与组件数

| # | 对象 | 数值 | 书页（来源单元） |
|---|---|---|---|
| 13 | 通用模型组件数：Introduction | **4** 个 basic components（由 **11** 句精简） | pp.16–17（U1） |
| 14 | 通用模型组件数：Methods | **6** 个组件（由 **9** 句功能分析精简）+ **1** 个图形增补项 | pp.86–88（U2） |
| 15 | 通用模型组件数：Results | **4** 个段落组 / **11** 个组件条目（示例 **12** 句） | pp.144–155（U3） |
| 16 | 通用模型组件数：Discussion | **9** 个组件（示例 **10** 句） | pp.194–208（U4） |
| 17 | 通用模型组件数：Conclusion | **11** 个组件（**6** 篇样例） | pp.246–257（U5） |
| 18 | 通用模型组件数：Abstract | **3** 区块 × 3 = **9** 个组件；**6** 个组件标 `+ J`，共 **7** 处 `+ J` | p286（U6） |
| 19 | Title 检查点 | 原文称 **"7 points"**，实存 7.1–7.6 共 **6** 步（见 Part 5.2） | p303（U7） |
| 20 | Results 结构组织选项 | **4** 种（Option 1–4） | p141（U3）；p245（U5 对应） |
| 21 | Abstract 类型 | **4** 类（Simple/Standard、Structured、+Significance/Highlights、Graphical） | p269（U6） |
| 22 | Discussion 分析清单项数 | **11** 项 | p242（U4） |
| 23 | Abstract 检查项数 | **12** 项 | p297（U6） |
| 24 | 摘要重复名词实例 | 同一术语在 **140** 词摘要内重复 **4** 次 | p266（U6） |
| 25 | 频率等级 | **10** 级（从"每次/毫无例外"到"从不"） | pp.175–177（U3） |
| 26 | 数量语言分组 | **5** 组（放大 / 缩小 / 强调程度 / 相近 / 不解读） | pp.172–174（U3） |
| 27 | certainty continuum 示例句 | **5** 级（从绝对确定到极谨慎） | p156（U3） |
| 28 | 情态动词功能组 | **6** 组（ABLE / POSSIBLE-OPTIONAL / EXPECTED-LIKELY / OBVIOUS-IMPOSSIBLE / ADVISABLE / NECESSARY） | pp.232–239（U4） |
| 29 | 四级确定性直观模型 | possibly / probably / obviously / impossible | p237（U4） |
| 30 | 不可数名词表 | 约 **90** 词 | pp.122–123（U2） |
| 31 | 长句风险因子 | **4** 项（>1 个 and、>1 个 which、过多介词、过多名词） | p319（U8） |
| 32 | 介词频次自测（同一段落） | `of` **8**、`for` **11**、`with` **15**、`on` **11**、`in` **20** | pp.115–116（U2） |
| 33 | `-ing` 含义谱系 | **10** 类（A–J） | p325（U8） |
| 34 | 易混词对 | **10** 组 | pp.327–328（U8） |
| 35 | 词块库来源规模 | 分析 **2,500+** 篇不同学科已发表论文 | p45（U1）、p99（U2）、p169（U3）、p221（U4）、p290（U6 指向前单元） |
| 36 | 年度论文总量 | **>3,000,000** 篇 | p75（U2）、p265（U6） |
| 37 | 可检索科研总量倍增周期 | 每 **10** 年翻一番 | p75（U2） |
| 38 | Unit 8 覆盖小节数 | **27** 个（8.1 的 8 + 8.2 的 4 + 8.3 的 10 + 8.4 的 5） | pp.315–330（U8） |
| 39 | Unit 8 高频错误排序 | **15** 项（**总结的编者综合排序，原书未给频次/严重度排名**） | pp.314–330（U8） |

## 4.3 无阈值的"测量型"检查（脚本只报告，不判定）

| # | 检查项 | 原文要求 | 书页 |
|---|---|---|---|
| 40 | Abstract 中重复/重述方法与结果的比例 | 要求量化分析，**未给阈值** | p297（U6） |
| 41 | happy language 的数量 | 要求评估 `The amount of 'happy' language that identifies the value/achievement of the study.`，**未给推荐数量或密度** | p297（U6） |
| 42 | Conclusion 各组件的篇幅比例 | `what proportion of the Conclusion section deals with each component`，**未给比例** | p257（U5） |
| 43 | Discussion 中重复/回顾结果的比例 | 要求核查，**未给比例** | p242（U4） |
| 44 | Discussion 引用条数 | 用**目标文章均值**估算本领域常规值，**无通用阈值**；同时看功能/位置/重复频次 | p198（U4） |
| 45 | 目标文章 Methods 平均篇幅 | 要求自查，**无通用值** | p136（U2） |
| 46 | 目标文章 Conclusion 平均词数 | `it is worth averaging the number of words in the Conclusion in your target articles as a guide` | p245（U5） |
| 47 | 目标期刊 Abstract 词数均值 | `Averaging the number of words in the Abstracts of your target journals will give you a rough idea.` | p267（U6） |
| 48 | Title 词数变异范围 | `averages hide acceptable variation`，**未给上下限** | p304（U7） |
| 49 | 段落长度（按领域校准） | `Check target texts to determine normal paragraph length for that type of text in your field.` | p66（U1） |
| 50 | 评价性语言的用量 | 在目标文章中**划线/高亮**统计，**未给阈值** | pp.149–150（U3） |
| 51 | 方法/结果细节量 | 依目标文章与读者群调整，**无通用值** | pp.81–82（U2） |
| 52 | 缩写可接受性 | 依"当前 + 未来读者共享知识水平"判断，**无清单** | pp.268、305（U6、U7） |
| 53 | 摘要与正文的一致性 | 逐句核对，**无数值标准** | p288（U6） |

## 4.4 语料与练习规模（可用于脚本的自测题库）

| # | 语料/练习 | 规模 | 书页 |
|---|---|---|---|
| 54 | Introduction 示例（功能分析） | **11** 句 | pp.16–17（U1） |
| 55 | Methods 示例（功能分析） | **9** 句 | pp.86–87（U2） |
| 56 | Results 示例（功能分析） | **12** 句 | pp.144–152（U3） |
| 57 | Discussion 示例（功能分析） | **10** 句 | pp.194–195（U4） |
| 58 | Conclusion 语料 | **6** 篇（每篇前附 Abstract，部分附 Synopsis/Highlights/Key notes） | pp.246–256（U5） |
| 59 | Abstract 语料 | **18** 篇（Simple/Standard 10 + Structured 2 + Significance/Highlights 3 + GA 3） | pp.269–285（U6） |
| 60 | Title 评估语料 | **36** 条 | pp.310–312（U7） |
| 61 | 情态动词配对练习 | **8** 个情态动词 ↔ 释义句（Key 6 句） | pp.229–230（U4） |
| 62 | 情态句改写练习 | **12** 题（含 Key） | pp.239–241（U4） |
| 63 | `should` 两义辨析 | **13** 句（**原文未给答案**） | p238（U4） |
| 64 | 副词位置配对 | **6** 句 6 义（含答案 1=C, 2=F, 3=E, 4=A, 5=B, 6=D） | pp.323–324（U8） |
| 65 | `-ing` 歧义练习 | **3** 句 × A–J 含义谱系（**原文未给答案**） | p325（U8） |
| 66 | 介词频次练习 | **1** 段（含答案 8/11/15/11/20） | pp.115–116（U2） |
| 67 | 空间精确度辨析 | **2** 组（against 系列；just 系列） | p102（U2） |
| 68 | Introduction 写作练习 | 依模型 + 词表成文，**250–350** 词 | pp.69–70（U1） |

## 4.5 不得外推的说明（脚本实现的硬约束）

1. **三个句长数值不可互相替代**：书 p58（约 23）＝ STEMM 研究论文总体均值；书 pp.318–319（20–26）＝ 多数期刊区间；书 p267（22）＝ 18 篇范文**摘要**均值。脚本应用 20–26 作带宽、22–23 作语料均值参照，**不得**合成一个更窄的"标准值"。
2. **150–170 词是平均值**，原文只说"多数段 >230 或 <80 词不常见"，因此脚本应**报警**而非阻断。
3. **80–250 词（摘要）与 100–200 词（结论）是"most/averages"口径**，必须优先查目标期刊均值（书 pp.245、267）。
4. **12 词（标题）是 "many journals" 的平均数**，原文明确 `averages hide acceptable variation`（书 p304）。
5. **原文未给出的数值一律不得补齐**：Results 字数上下限与图表数量标准（书 p187 只要求查目标文章）、Discussion 推荐篇幅/字数比例、各学科 Conclusion 推荐词数表、Abstract 方法与结果重复比例的阈值、happy words 密度阈值、Methods 通用细节量。
6. **组件计数存在"口径"问题**：Methods 为 6 组件 + 1 图形增补项（书 p87 原文把图形作为一项加入模型）；Results 的"11 条"是总结对 4 个段落组的条目计数。脚本比对时应以"段落组/区块"为主键，避免因切分不同误报。
7. **Part 4.2 第 39 项（Unit 8 高频错误 Top 15）是总结的编者综合排序**，原书未给频次或严重度排名——脚本不得把它当作原书优先级。
8. **第 10、11 项属训练/说明性数值**（250–350 词、140 词），不得作为期刊写作阈值。

# Part 5 待核实与原文矛盾项

## 5.1 页码口径裁决（本次编纂的关键核对结果）

**裁决**：书内页 = **PDF 页 − 29**，全书八单元与前言之外的所有页面一致成立。证据不是子代理的自述，而是原书**印张页眉**（形如 `w 58` / `58 v`）。锚点：

| PDF | 印张页眉（书内页） | 内容 |
|---|---|---|
| 46 | 17 | GENERIC INTRODUCTION MODEL |
| 87 | 58 | 句长/首读理解率基准 |
| 117 | 88 | GENERIC METHODS MODEL |
| 144 | 115 | 2.5.2 Prepositions |
| 150 | 121 | 2.5.3 冠词 |
| 165 | 136 | Unit 2 收尾 |
| 184 | 155 | GENERIC RESULTS MODEL |
| 214 | 185 | risk-reducers 复习项 |
| 219 | 190 | Unit 4 起始 |
| 237 | 208 | GENERIC DISCUSSION MODEL |
| 271 | 242 | 4.6 Summary Discussion Exercise |
| 274 | 245 | Conclusion 位置与长度 |
| 286 | 257 | GENERIC CONCLUSIONS MODEL |
| 315 | 286 | GENERIC ABSTRACT MODEL |
| 333 | 304 | 7.1 Check Average Length |
| 339 | 310 | 7.6 承诺兑现 |
| 344 | 315 | 8.1 Organising the Information |
| 359 | 330 | 全书最后建议 |

**逐单元核对结论**

| 单元 | 子代理声明 | 实际标签性质 | 裁决 |
|---|---|---|---|
| Unit 1 | 书内页，−29 | 书内页，正确 | ✅ 可直接使用（p17 模型、p45 词块、p58 句长、p66 段长、p71 TIPS） |
| Unit 2 | 标注 PDF，书内 = PDF − 29 | 标注 PDF，正确 | ✅ 本手册已全部 −29 转为书内页 |
| Unit 3 | 标注 PDF | **混用**：§3.1–3.3 的裸 `pN` 多为 PDF；§3.4–3.5 与 §6 的裸 `pN` 为书内页（多附 PDF 伴随值） | ⚠️ 本手册 §1.5 改以节号 + 书内页区间标注；4 处精确页已按印张核对（书 145、148、155、186–187） |
| Unit 4 | 自称"书内页 = PDF − 28" | **公式错误，但标签是书内页且符合 −29**（p190 = PDF 219 = `w 190`；p208 = PDF 237 = `w 208`；p242 = PDF 271 = `w 242`） | ✅ 引用可直接当书内页；仅需纠正其公式 |
| Unit 5 | 自称"采用书中页码" | **实际标签是 PDF 页码**（模型在 raw PDF 286，印张页眉 `257 v`；5.2/5.3/5.4 位于 PDF 286/287/288 = 书 257/258/259） | ❌ **最高风险项**：本手册已将 Unit 5 全部页码 −29 归一；若按书内页直读，`p286` 会误指向 **Abstract** 的模型页（书 286 = PDF 315） |
| Unit 6 | 标注 PDF | 标注 PDF，正确；且原书自引 "generic Abstract model on page 286"（书内页）独立验证 | ✅ 本手册已 −29 转换（如 p294→书 265、p315→书 286、p326→书 297） |
| Unit 7 | 标注 PDF | 标注 PDF，正确 | ✅ 已 −29 转换（p332→书 303、p333→书 304、p339→书 310、p341→书 312） |
| Unit 8 | 标注 PDF，逐条附"书 pN" | 正确 | ✅ 已 −29 转换（p343→书 314、p344→书 315、p347→书 318、p350→书 321、p358→书 329） |

**范围标注的两处起点偏差（不影响单页引用）**

- Unit 3 头部称 "PDF pp.168–217 即书内 pp.140–187"：两端各偏 1，正确为 **书 139–188**。
- Unit 8 头部称 "PDF 342–359 对应书内 314–330"：起点偏 1，正确为 **书 313–330**（PDF 343 = `w 314`）。

**前言例外（须单独处理）**：原书前言用罗马数字单独编页，**PDF = 罗马数字 + 1**（PDF 14 = 书 xiii、PDF 15 = xiv、PDF 16 = xv、PDF 17 = xvi、PDF 18 = xvii、PDF 19 = xviii），**不适用 −29**。Unit 1 与 Unit 4 提到的 reverse-engineering 原文（p xvii–xviii）与 narrative wrap 细节（"see page xiv"）均落在前言，而**这 8 份总结都未收录前言内容**——本手册 Part 0 的 scaffold / wrap 描述全部来自各单元正文的转述。

## 5.2 原书自身编号不一致（已核验，非抽取遗漏）

1. **Unit 7 的 "7 points" 与 6 个小节**：书 p303 写 `Use the following **7 points** to analyse recent comparable titles in your target journals`，但正文只有 **7.1–7.6** 六项。已核验：PDF 328–341 全范围内、以及全书 PDF 全文内均**不存在 7.7 或"第 7 点"标题**；目录（Contents）也只列 7.1–7.6。→ **结论：这是原书自身的编号不一致，不是子代理抽取遗漏。** 本手册在 §1.1 B 与 §1.1 F 均按"原文称 7 points / 实存 6 步"表述。
2. **Methods 模型计数口径**：原文把 **figures, maps, photographs, tables** 作为一项加入模型（书 p87），来源 9 句功能精简为 6 组件——故"6 组件"与"6 + 1 项"两种说法都能在原文找到依据；本手册记为"6 组件 + 1 图形增补项"。
3. **Results 模型的条目计数**：4 个编号段落组是原文明确的；"11 条"是总结对组件行的计数口径（第 3 组另附注 `focus on a solution or a reason`）。本手册同时给出组数与条数，避免单一口径争议。
4. **印刷顺序与章节顺序相反**：Fig. 1.1 的印刷顺序为 `… RESULTS → CONCLUSION* → DISCUSSION`，但全书把 Discussion 放 Unit 4、Conclusion 放 Unit 5（书 pp.2、141、244、265；Unit 5 亦称 `TITLE → ABSTRACT → INTRODUCTION → METHODS → RESULTS → CONCLUSION* → DISCUSSION`）。→ 本手册 Part 0.5 已按"阅读/写作顺序 ≠ 印刷顺序"处理。
5. **跨单元刻意重复的脚注**：CONCLUSION/CONCLUSIONS 命名脚注在 Unit 1、3、5、6、7 反复出现（书 pp.2、141、244、264、299）。这不是矛盾，而是原书对"命名不反映结论条数"的反复确认；本手册只在 §1.7 B 保留一次。
6. **narrative wrap 的页码指向不一致**：Unit 4 说细节见 "see page xiv"（前言），Unit 1 说 reverse-engineering 原文在 p xvii–xviii——两者都指前言不同页，且都不在各自抽取范围内；本手册按"原文未收录"标注（见 §5.1 末）。

## 5.3 单元级缺口（原文未明确 / 抽取范围外）

| 单元 | 缺口 | 本手册处理 |
|---|---|---|
| Unit 1 | 前言（p xvii–xviii）的 reverse-engineering 原论述未收录；review article / letter / clinical study 的引言体裁差异**未讨论**（仅 4 处零散提及"综述"）；非 STEMM 差异未展开 | Part 0.2 用单元正文的 EXERCISE 1/3/4/5 转述补足；体裁差异在本表标注 |
| Unit 2 | 统计方法的专用词块分类；样本纳入/排除标准、伦理审批、知情同意的写法；**影像组学/组学类研究的专有 Methods 规范**（原书未出现 omics / radiomics 术语）；"最常见的 Methods 结尾句"清单；2.5.3 不可数名词表中哪些词原为**粗体**（纯文本无法判别） | 在 §1.4 C/E 标注"原文未明确"；可迁移依据（图像处理流程类示例、计算类示例、宽读者群多给背景）在 §1.4 C 保留 |
| Unit 3 | Exercise 2 三篇跨学科 Results 的逐句标准答案；Results 字数上下限/图表数量标准；'!-substitutes' 完整清单（指向书 pp.225–226）；modal verbs 系统用法（指向 Unit 4） | 在 §1.5 B/E/F 标注；'!-substitutes' 已并入 §1.6 E-3 与 §2.13 |
| Unit 4 | Conclusion 节自身的模型与组件清单；Discussion 推荐篇幅/字数比例；`should` 两义辨析 13 句的答案；不同文章类型（纯理论/综述/方法学/病例报告）Discussion 的差异清单；narrative wrap 细节（见前言） | §1.6 B 标注指向 Unit 5；其余在本表标注 |
| Unit 5 | **无独立词块清单**（5.3 全部交叉引用 Units 1–4）；**无独立 Checklist**（正文止于 5.4.2）；applications/implications/limitations/future work 的显式取舍规则；Conclusion 可否引入新数据或新引用；各学科推荐词数表；p246 提到的加粗句功能线索在纯文本中不可见 | §1.7 E 采用"交叉引用航标 + 本单元样例句"双轨；§1.7 F 由规则转写并注明；其余在本表标注 |
| Unit 6 | 组件 2（CHALLENGE/PROBLEM）、7（MAPPING）、9（APPLICATIONS）的独立时态规则；"如何避免与 Conclusion 重复"的专门规则；方法/结果重复比例阈值；happy words 推荐数量/密度；结构化摘要是否有专属时态规则 | §1.2 D 逐行标"原文未明确"；反向约束（Conclusion 不得以 Abstract 为素材）在 §1.2 C 与 §1.7 C 交叉给出 |
| Unit 7 | 具体字数上下限、是否计入副标题；**大小写规则**（书 p299 脚注仅说明书中标题已统一化）；**question-based 问句标题**；动名词 vs 名词化的优劣；冒号前后字数比例、冒号是否仅限一次；"第 7 点"内容 | §1.1 B/C/D 逐处标注；"第 7 点"按 §5.2-1 裁决 |
| Unit 8 | `-ing` 练习 1–3 的答案；`Self-edit lexical writing tics` 仅有标题无正文细则；`The certainty continuum and modal verbs` 未列具体情态动词清单；原书未给错误频次/严重度排名 | §2.3 从 Unit 4 补入完整情态动词体系；其余在本表标注 |

## 5.4 跨单元内容张力（按节选用，不可压成单一规则）

1. **被动语态的地位冲突（本次编纂发现的第一大重复+冲突）**：Unit 2 要求 Methods 使用 **agentless passive**、不用 `by us`（书 pp.113–114）；Unit 8 与 Unit 5/6 则警告 agentless passive 与无人称主语**丢失 ownership**（书 pp.321–322、261、266），并点名**摘要最危险**。→ 合并规则：Methods 可 agentless passive 但必须用五情形处置表消歧（§1.4 D）；Abstract/Discussion/Conclusion 的成就句优先主动、人称主语或显式指代（§2.4）。
2. **limitations 的首次提及位置（第二大冲突）**：Unit 2 说应在 Methods（问题出现处）首次提及并文末呼应（书 pp.85–86）；Unit 3 说必须在 Results 承认，`it isn't appropriate to mention them for the first time` 留到 Discussion/Conclusion（书 p152）；Unit 4 给两类例外允许 Discussion 首次提及（书 pp.205–206）。→ 合并规则：默认"最早出现处"，Results 必须承接，Discussion 仅两类例外（§2.4 与 §1.6 C）。
3. **句长基准三个数值（第三大重复）**：书 p58（约 23）／书 pp.318–319（20–26）／书 p267（22，摘要）。→ 见 Part 4.5-1，禁止合并。
4. **时态：规则化 vs 作者判断**：Unit 1 给出版本化时态分工并强调"改动必有意义"；Unit 4 明确结果-含义的时态**"无法通过查目标文章解决"**，须作者自行判断（书 pp.202–204）。→ §2.1 保留该例外行。
5. **Results 能不能解释**：原书反对规定主义（书 p142：成功论文常常不遵守"Results 不得解释/只能用过去时"），同时又给"完整解释留给 Discussion"的倾向性规则（书 pp.151–152）。→ §1.5 C 按"倾向性而非禁令"表述。
6. **`-ing`、冠词、介词三主题在 Unit 2 与 Unit 8 双重覆盖**：Unit 2 给系统规则，Unit 8 给新增陷阱。→ 已合并为 §2.5/§2.6/§2.7 各一份，双出处标注。
7. **信号词**：Unit 1 六组功能分类（书 pp.59–61）+ Unit 8 三连自检与错误示范（书 pp.319–320）。→ 合并为 §2.11。
8. **happy words 跨五处清单**：书 pp.51（Intro）、107（Methods）、175（Results）、225–226（Discussion，含 !-substitutes）、294–295（Abstract）。→ 每章 E 各列本章侧重；"very happy"（!-substitutes）只在 §1.6 E-3 与 §2.13 出现一次。
9. **Abstract ↔ Conclusion 的单向约束**：Unit 5 明令 Abstract 不得作 Conclusion 的主要素材（书 p246）；Unit 6 无对等禁令（原文未明确），只要求与正文数据一致、不过度（书 p288）。→ 单向：结论不得抄摘要；摘要无同款禁令。
10. **模型页面的重号风险**：Unit 5 的模型在**书 257**、Unit 6 的模型在**书 286**；但两份总结都写 "p286"（前者是 PDF、后者是书内页）。→ 已裁决并写入 §5.1，脚本与人工引用时须以 Part 0.6 对照表为准。

## 5.5 本手册的编辑判断（供复核）

1. **Unit 5 页码一律 −29 处理**，并在 §1.7 内不直接呈现原总结页码，避免读者误引到 Abstract 的模型页。
2. **Unit 3 §3.1–3.3 不给逐句精确页**，改以节号 + 书内页区间（因原总结在该区间混用两种口径）；仅对已按印张核对的 4 处给精确页（书 145、148、155、186–187）。
3. **组件计数一律给出"组/条"两个口径**，不擅自裁定唯一数字。
4. **Part 4 中标注了哪些数值属"编者综合"或"训练/说明性"，不得用于机检判定**。
5. 凡原总结标注「原文未明确」者，本手册**不补规则、不外推**；凡本手册据原文规则转写为清单动作处（如 §1.7 F、Part 3），已在文中说明"由规则转化"。
6. 本手册**未使用** 8 份总结以外的任何来源；页码核对仅使用了 `docs/_extract/` 内 8 份总结所对应的原始抽取文本中的**印张页眉与目录页**，用于解决子代理自述的页码口径冲突（属于编纂核对，未引入任何新规则）。

