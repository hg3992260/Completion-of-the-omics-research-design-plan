# -*- coding: utf-8 -*-
"""SCI Shape —— 七章通用结构与本稿自评数据。

来源：Glasman-Deal, *Science Research Writing* (2nd ed., Imperial College London)。
本模块只收录**经过核验**的内容：7 个 GENERIC MODEL 组件框、各章内容边界、时态规则、
检查项与已确证的词块组。页码一律为**书内页码**（书页 = PDF 页 − 29）。

字段说明
    id / key        环节序号与短键
    title           章节名（中文 + 英文）
    spec            单元与书页区间
    goal            功能定位（一句话，为什么这一章存在）
    model           通用模型组件（en 原文 / zh 中文）
    must            必须写进去的内容
    must_not        不得写进去的内容（边界）
    language        时态与语言规则（rule + 书页）
    phrases         词块组（group + items；仅收录已逐条核验的表达）
    checks          可勾选自检项（完成度由此计算）
    stages          与十阶段管线的对应（Methods/Results 由既有环节覆盖）
    note            补充说明
"""

from __future__ import annotations

import scope_core

STATUS_LABEL = scope_core.STATUS_LABEL


SHAPE = [
    # ------------------------------------------------------------------ 01 标题
    {
        "id": 1,
        "key": "title",
        "title": "标题 Title",
        "spec": "Unit 7 · 书 p299–311",
        "goal": "标题决定读者是否继续读：必须说明读者能获得什么（研究产出），而不是只描述研究活动。",
        "model": [
            {"en": "CHECK AVERAGE LENGTH", "zh": "检查平均长度（目标期刊近期标题的统计值）"},
            {"en": "USING ACRONYMS", "zh": "缩写使用是否对当前与未来读者都可懂"},
            {"en": "COMPARE THE TITLE KEYWORDS TO THE KEYWORD LIST",
             "zh": "标题关键词与关键词表对齐"},
            {"en": "CHECK THE GRAMMAR OF THE TITLE",
             "zh": "检查语法：复合名词、介词、冠词、冒号、大小写"},
            {"en": "MAP AND MODEL THE STRUCTURAL CONTENT OF TARGET TITLES",
             "zh": "反向建模目标期刊标题的结构成分"},
            {"en": "CHECK THAT EXPECTATIONS THE TITLE SUGGESTS ARE FULFILLED",
             "zh": "核对标题给出的预期是否在正文兑现"},
        ],
        "must": [
            "说清研究产出与本研究的贡献（价值在 outcome，不在 investigation 本身）",
            "与投稿期刊的关键词表保持一致",
            "标题承诺的内容在 Conclusion 中全部兑现",
            "结论尚未完全确立时，用 may / might / could 限定",
        ],
        "must_not": [
            "沿用最初的工作标题（working title）而不加修改",
            "overstate：标题的断言强于结果能支持的程度",
            "在跨学科读者面前使用本领域小圈子才懂的缩写",
        ],
        "language": [
            {"rule": "多数期刊标题平均词数约 12；平均值会掩盖可接受的变化范围", "page": "p304"},
            {"rule": "句子标题（sentence title）直接陈述关键发现，用 Present Simple；仅在结论足够强时使用", "page": "p303–304"},
            {"rule": "冒号只有两种功能：大主题:焦点贡献（如 Life cycle inherent toxicity: a novel LCA-based algorithm…）；新术语:描述定义（如 GridSpice: a distributed simulation platform…）", "page": "p309"},
        ],
        "phrases": [],
        "checks": [
            "标题说明的是「读者能得到什么」，而不是「我做了哪方面研究」",
            "已统计目标期刊近期同类标题的词数（参考约 12 词）",
            "标题中的缩写，当前与未来读者都能理解",
            "标题关键词与投稿期刊的关键词表一致",
            "复合名词与介词搭配已逐条核对",
            "若使用冒号，其功能属于「大主题:焦点贡献」或「新术语:描述定义」之一",
            "先只看标题预测能获得什么，再核对 Conclusion —— 二者一致",
            "结论未定时已用 may / might / could 限定，未 overstate",
        ],
        "note": "原书 p332 写 “following 7 points”，但正文只有 7.1–7.6（属原书编号不一致）。",
    },
    # ------------------------------------------------------------------ 02 摘要
    {
        "id": 2,
        "key": "abstract",
        "title": "摘要 Abstract",
        "spec": "Unit 6 · 书 p263–297",
        "goal": "摘要是独立可见的最小单元：用最少字数让读者立刻看见本研究做了什么、得到什么、价值在哪。",
        "model": [
            {"en": "SIGNIFICANCE OF THE TOPIC / ESSENTIAL FACTUAL BACKGROUND", "zh": "主题重要性 / 必需的事实背景"},
            {"en": "THE CHALLENGE / PROBLEM", "zh": "挑战 / 问题"},
            {"en": "WHAT THE PAPER/STUDY DOES (may include ACHIEVEMENT/VALUE)", "zh": "本文做了什么（可含成就/价值）"},
            {"en": "METHOD/MATERIALS", "zh": "方法 / 材料"},
            {"en": "RESULTS / COMPARISONS WITH EXISTING RESULTS", "zh": "结果 / 与已有结果的比较"},
            {"en": "IMPLICATIONS", "zh": "含义 / 推论"},
            {"en": "MAPPING TO EXISTING KNOWLEDGE", "zh": "与已有知识的对接"},
            {"en": "ACHIEVEMENT / VALUE / CONTRIBUTION", "zh": "成就 / 价值 / 贡献"},
            {"en": "APPLICATIONS", "zh": "应用"},
        ],
        "must": [
            "9 个组件按 3 个区块组织（背景与问题 → 本研究的做法与结果 → 对接知识与价值）",
            "happy words 放在模型标注的位置（共 6 个组件可放）",
            "长度控制在 80–250 词、多数为单段",
            "在正文完成后撰写，投稿前再复核一致性",
        ],
        "must_not": [
            "把摘要当成全文的压缩版 —— 摘要不必概括整篇论文",
            "用一般现在时描述自己的结果与做法，造成贡献归属歧义（Analysis shows vs Analysis showed）",
            "为省字数删掉消歧短语（In this study / Here / It is known that）",
            "正文未完成就先写摘要",
        ],
        "language": [
            {"rule": "本文做什么（WHAT THE PAPER DOES）→ Present Simple", "page": "p286"},
            {"rule": "方法（做了什么/用了什么）→ Past Simple", "page": "p286"},
            {"rule": "结果与含义 → Past Simple 或 Present Simple 皆可；摘要中可改用现在时（即使正文用过去时），以立刻抓住读者注意", "page": "p286"},
            {"rule": "成就/价值/贡献 → Present Perfect 或 Present Simple", "page": "p287"},
            {"rule": "字数上限不是目标（The word limit is not a target）；<20 词的句子 90% 读者一遍读懂，>40 词仅 10%", "page": "p267"},
            {"rule": "一般现在时会让人看不出谁做的：Analysis shows… 无法判断归属，Analysis showed… 明确是作者所做", "page": "p266"},
        ],
        "phrases": [
            {"group": "IMPLICATIONS", "page": "p295",
             "items": ["appear to", "seem to", "indicate that", "suggest that",
                       "may/might/could", "potentially", "possible", "we conclude that"]},
            {"group": "ACHIEVEMENT / VALUE / CONTRIBUTION（happy words）", "page": "p294–295",
             "items": ["novel", "accurate", "improved", "reliable", "robust", "effective",
                       "efficient", "cost-effective", "practical", "comparable", "superior",
                       "outperform", "validate", "verify", "(the) first"]},
            {"group": "APPLICATIONS", "page": "p295",
             "items": ["apply", "employ", "implement", "use", "enable", "potential",
                       "suitable for/in", "relevant for/in", "wide range of"]},
            {"group": "METHOD / MATERIALS", "page": "p293",
             "items": ["result in", "reveal", "yield", "are/was unaffected (by)"]},
        ],
        "checks": [
            "9 个组件已齐全（缺失的组件已明确判定为不需要）",
            "逐句核对了时态：本文做什么→现在时；方法→过去时；结果/含义→过去或现在；成就→现在完成或现在时",
            "所有成就句都能看出是本研究做的（无 Analysis shows 式归属歧义）",
            "反指已消歧：this / it 均能明确指向具体对象",
            "happy words 放在了模型允许的位置，且数量不夸张",
            "长度在 80–250 词之间，多为单段",
            "未把摘要写成全文压缩版，与 Conclusion 未重复",
            "摘要中的结果与正文结果一致（数字、方向、限定语）",
        ],
        "note": "摘要类型谱系（Simple/Standard、Structured、含 Significance Statement/Highlights、Graphical）差异见 Unit 6 6.2 与手册 Part 1。",
    },
    # ------------------------------------------------------------------ 03 引言
    {
        "id": 3,
        "key": "introduction",
        "title": "引言 Introduction",
        "spec": "Unit 1 · 书 p1–71",
        "goal": "把读者从「领域的一般认识」带到「本研究要解决的问题」，并明确本研究的位置。",
        "model": [
            {"en": "ESTABLISH THE IMPORTANCE OF THE TOPIC/FIELD · PROVIDE BACKGROUND FACTUAL INFORMATION · PRESENT THE GENERAL PROBLEM AREA/CURRENT RESEARCH FOCUS",
             "zh": "①确立主题重要性 · 提供背景事实 · 提出一般问题域/当前研究焦点"},
            {"en": "PRESENT PREVIOUS AND/OR CURRENT RESEARCH AND CONTRIBUTIONS: the research ‘map’",
             "zh": "②呈现前人/当前研究与贡献（研究地图）"},
            {"en": "LOCATE A GAP IN THE RESEARCH · DESCRIBE THE PROBLEM YOU WILL ADDRESS · PRESENT YOUR MOTIVATION AND/OR HYPOTHESIS · IDENTIFY A RESEARCH OPPORTUNITY",
             "zh": "③指出研究空白 · 描述要解决的问题 · 给出动机/假设 · 指出研究机会"},
            {"en": "DESCRIBE THE PRESENT PAPER, sometimes mentioning aims/results/methods/conclusions, and often including ‘happy’ words",
             "zh": "④描述本文（可含目的/结果/方法/结论，常用 happy words）"},
        ],
        "must": [
            "以组件 1 开头、以组件 4 收尾（几乎所有研究论文引言都如此）",
            "gap 用陈述句表达（prediction / suggestion / hypothesis），并说明它为何是当前的问题",
            "背景事实的量按「读者需要知道什么才能读懂本研究」确定",
        ],
        "must_not": [
            "把 gap 写成问句（按惯例不用问句）",
            "在引言里塞入过多方法与结果细节",
            "让组件 3 的 gap 缺失却又不说明动机（仅当动机是「延伸前人研究」时可隐含）",
        ],
        "language": [
            {"rule": "Past Simple = 该发现只属于那项研究；Present Simple = 可靠、恒久的事实；Present Perfect = 与当下相关", "page": "p24–26"},
            {"rule": "little attention has been paid → 表示这是本研究要填的当前空白；改成 was paid 就变成两年前的旧情况", "page": "p25"},
            {"rule": "aim 用 Past Simple（aim 在真实时间上先于工作存在）；描述本文做了什么用 Present Simple", "page": "p15"},
            {"rule": "信号词不是胶水，不可每句都用；首选 repetition / echo linkage（重复同一名词让概念可追踪）", "page": "p30–31"},
            {"rule": "平均段长 150–170 词；句子 <20 词 90% 读者一遍读懂，STEMM 平均约 23 词", "page": "p29 / p66"},
        ],
        "phrases": [
            {"group": "GAP · Group 1: PROBLEM/CRITICISM", "page": "p49",
             "items": ["however", "although", "while", "nevertheless", "despite"]},
            {"group": "GAP · Group 2: RESEARCH OPPORTUNITIES", "page": "p49",
             "items": ["more work is needed", "the next step", "not addressed",
                       "not dealt with", "(an) alternative", "clarification",
                       "to demand", "to need to"]},
            {"group": "SIGNALLING CONNECTORS · CAUSE", "page": "p59",
             "items": ["because", "since", "as", "due to (the fact that)",
                       "on account of (the fact that)", "in view of (the fact that)"]},
            {"group": "SIGNALLING CONNECTORS · RESULT", "page": "p60",
             "items": ["therefore", "hence", "thus", "consequently", "as a result", "so"]},
            {"group": "SIGNALLING CONNECTORS · CONTRAST/DIFFERENCE", "page": "p60",
             "items": ["however", "on the other hand", "by contrast", "whereas",
                       "while", "in contrast", "but"]},
            {"group": "SIGNALLING CONNECTORS · UNEXPECTEDNESS", "page": "p60–61",
             "items": ["although", "despite", "nevertheless", "even though",
                       "in spite of", "regardless of", "yet", "notwithstanding"]},
            {"group": "SIGNALLING CONNECTORS · ADDITION/LISTING", "page": "p61",
             "items": ["in addition", "also", "moreover", "furthermore",
                       "secondly", "what is more"]},
            {"group": "SIGNALLING CONNECTORS · TRANSITION", "page": "p61",
             "items": ["with regard to", "with respect to", "as to", "as for",
                       "regarding", "turning now to"]},
        ],
        "checks": [
            "组件 1–4 齐全，且顺序符合目标期刊惯例",
            "开篇第一句已对照目标期刊近期论文校准（不凭直觉）",
            "gap 是陈述句，且明确指向「当前仍待解决」",
            "前人的贡献被公正呈现（有引用支撑，未贬低他人）",
            "组件 4 明确交代本文做了什么，且含体现价值的表达",
            "各句时态与其功能匹配（背景/前人/空白/本文各有其时态）",
            "句间衔接以 repetition/echo 为主，未滥用 however/therefore 类信号词",
            "未出现本应放在 Methods/Results 的细节",
        ],
        "note": "模型是「头尾刚性、中间弹性」：Component 1 与 4 几乎必有，中间组件可调整顺序与详略。",
    },
    # ------------------------------------------------------------------ 04 方法
    {
        "id": 4,
        "key": "methods",
        "title": "方法 Methods",
        "spec": "Unit 2 · 书 p73–137",
        "goal": "让读者能复现你做了什么：先给整体，再给可执行的精确细节，并说明选择理由。",
        "model": [
            {"en": "PROVIDE AN OVERVIEW OF/STATEMENT ABOUT THE METHODS · RESTATE THE AIM/GAP · GIVE THE SOURCE OF MATERIALS/EQUIPMENT",
             "zh": "①给出方法概述 · 重述目的/空白 · 说明材料/设备来源"},
            {"en": "PROVIDE DETAILS OF THE MATERIALS/METHODS (e.g. temperature, sequence) ± justify choices ± indicate that you took appropriate care",
             "zh": "②提供材料/方法细节（温度、序列等）± 说明选择理由 ± 表明操作谨慎"},
            {"en": "DESCRIBE/DISCUSS THE CONTENT OF A FIGURE/TABLE", "zh": "③描述/讨论图或表的内容"},
            {"en": "REFER TO MATERIALS/METHODS IN OTHER STUDIES (to compare · to justify your choices)",
             "zh": "④引用他人的材料/方法（用于比较或论证选择）"},
            {"en": "PROVIDE BACKGROUND INFORMATION IN THE PRESENT SIMPLE TENSE (to support the reader · to justify your choices)",
             "zh": "⑤用一般现在时提供背景信息（帮助读者、论证选择）"},
            {"en": "INDICATE ISSUES OR PROBLEMS", "zh": "⑥指出问题或局限"},
        ],
        "must": [
            "先给「做了什么/用了什么」的概述，再展开细节（先给读者看墙，再谈砖）",
            "材料/样品/设备来源、仪器型号与厂商、软件与版本",
            "精确参数：温度、时间、压力、序列与每步耗时",
            "统计与计算方法；步骤有序列时用 prior to / until / at which point 等精确语言",
            "问题与局限在方法中首次提及，并在文末呼应",
        ],
        "must_not": [
            "把实验室笔记当方法写（笔记写给自己，方法写给读者）",
            "引用已知方法时只给文献号而完全不复述基本步骤（读者没有时间去查）",
            "用无施动者被动却让读者分不清哪一步是本研究做的、哪一步是标准流程",
            "把问题/局限第一次留到文章最末尾",
        ],
        "language": [
            {"rule": "Past Simple = 本研究做了什么；Present Simple = 标准流程、设备属性、背景知识", "page": "p113–114"},
            {"rule": "agentless passive 描述自己的工作与他人工作时字面相同；需用改主动、加 here/in this work/in our model、假主语 This experiment、给引用、加 in their work 五种方式之一消歧", "page": "p113–115"},
            {"rule": "方法源于他人时通常仍需引用；方法成为背景知识后引用随之减少", "page": "p83"},
            {"rule": "USING 比 with 更常见（was analysed USING a computing cluster）；避免介词串；substituted for / with 语义相反", "page": "p115–120"},
            {"rule": "冠词以「共享知识」为核心：a/an = 首次提及/不重要/单数泛指；Ø = 复数泛指/不可数；the = 唯一可能/读者已知/显然", "page": "p121–126"},
            {"rule": "细节取舍：宁多勿少（it is better to give slightly too much information than too little）", "page": "p82"},
        ],
        "phrases": [
            {"group": "GIVE THE SOURCE OF THE MATERIALS/SAMPLES/EQUIPMENT", "page": "p100 / p129",
             "items": ["provided by", "supplied by", "purchased from", "a kind gift from"]},
            {"group": "SEQUENCE · BEFORE", "page": "p104–105",
             "items": ["prior to", "beforehand", "previously", "initially", "in advance",
                       "originally", "formerly", "earlier"]},
            {"group": "SEQUENCE · BEGINNING", "page": "p105",
             "items": ["at first", "at the start", "in the beginning", "to begin with",
                       "firstly", "to start with"]},
            {"group": "SEQUENCE · ORDER/STEPS", "page": "p105–106",
             "items": ["after", "followed by", "next", "secondly", "afterwards",
                       "following", "subsequently", "until", "at which point"]},
            {"group": "INDICATE WHERE PROBLEMS OCCURRED", "page": "p109–111",
             "items": ["minimise", "(no big deal)", "responsibility", "(not my fault)",
                       "good aspects", "(I got good stuff anyway)", "unavoidable",
                       "inevitably", "limited by", "negligible", "less than ideal"]},
        ],
        "checks": [
            "开头先给整体概述，再进入细节",
            "材料/样品/设备来源与型号、厂商、产地齐全",
            "关键参数（温度、时间、浓度、序列、每步耗时）可被第三方复现",
            "统计与计算方法已交代，并说明了处理方式",
            "引用他人方法时，读者不必查文献也能读懂本文做了什么",
            "逐句核查过时态：本研究动作用过去时，标准流程与背景用现在时",
            "无施动者被动句已消歧，读者能判断哪一步是本研究做的",
            "问题与局限已在方法中首次提及（未留到文末）",
            "细节粒度符合「宁多勿少」，且未混入实验室笔记式内容",
        ],
        "note": "模型是「菜单」而非必选项：无问题可不用组件 6。本稿的 Methods 内容由十阶段中的伦理/样本量/采集/分割/特征/稳定性环节承载。",
    },
    # ------------------------------------------------------------------ 05 结果
    {
        "id": 5,
        "key": "results",
        "title": "结果 Results",
        "spec": "Unit 3 · 书 p139–188",
        "goal": "结果不会自己说话：作者必须引导读者看图、固定数字的含义，并说明结果意味着什么。",
        "model": [
            {"en": "REVISITING THE LITERATURE/AIM/PREDICTION/HYPOTHESIS/GAP · REVISITING/SUMMARISING THE METHOD · GENERAL STATEMENT ABOUT THE RESULTS · INVITATION TO VIEW GRAPHIC + CONTENT OF GRAPHIC",
             "zh": "①回溯文献/目的/假设/空白 · 重述方法 · 结果总述 · 引导读者查看图表并说明图表内容"},
            {"en": "SPECIFIC/KEY RESULTS ± EVALUATIVE LANGUAGE/COMMENTS · COMPARISON WITH RESULTS IN OTHER STUDIES + happy words · COMPARISON WITH MODEL/SIMULATION/PREDICTED RESULTS · EXPLANATION OF RESULTS VIA KNOWN FACTS/METHOD DETAILS",
             "zh": "②具体/关键结果 ± 评价性语言 · 与其他研究结果比较 · 与模型/模拟/预测结果比较 · 用已知事实或方法细节解释结果"},
            {"en": "PROBLEMS/ISSUES WITH RESULTS ± REASONS", "zh": "③结果的问题/议题 ± 原因"},
            {"en": "POSSIBLE IMPLICATIONS OF RESULTS + happy words", "zh": "④结果的可能启示"},
        ],
        "must": [
            "每个关键结果都配评价性语言，明确数字的含义（in as many as 23% / in only 23% 是两个结果）",
            "引导读者查看图表（location statements），并说明图表中该看什么",
            "报告统计量与不确定性；多个结果按逻辑组织",
            "问题与局限必须在 Results 内承认，理由可一并给出",
        ],
        "must_not": [
            "只做客观描述 —— 没给读者任何「看图看不到」的信息",
            "把讨论、文献比较与临床建议整段搬进 Results",
            "把结果的问题第一次留到 Discussion 谈未来工作时才提",
        ],
        "language": [
            {"rule": "The Certainty Continuum 三步法：选因果动词 → 选时态 → 加 risk-reducing language", "page": "p182–186"},
            {"rule": "因果方向由动词锁定：X produced Y ≠ X originated in Y；linked / connected / related 不指明因果方向", "page": "p183–184"},
            {"rule": "冠词区分因果强度：a cause of（还有其他因素）vs the cause of（唯一原因）", "page": "p184"},
            {"rule": "results from 与 results in 方向相反；时态即信心：was related（仅本研究发现）vs is related（视为恒久真理）", "page": "p184"},
            {"rule": "图表引用语义区分：from = 可从数据推断出；in = 可见于图形本身", "page": "p141"},
            {"rule": "频率表达有 10 级强度；数量评价词分 5 组，用于把数字「框」成强或弱结果", "page": "p172–176"},
        ],
        "phrases": [
            {"group": "INVITATION TO VIEW RESULTS", "page": "p169–170",
             "items": ["as can be seen from/in Fig. 1", "as is apparent from Fig. 1",
                       "based on (the data in) Fig. 1", "according to the data in Fig. 1",
                       "(close) inspection of Figure 1 indicates", "data in Fig. 1 suggest that"]},
            {"group": "PROBLEM/S and ISSUE/S", "page": "p180–181",
             "items": ["minimise", "(no big deal)", "responsibility", "(not my fault)",
                       "good aspects"]},
            {"group": "'happy' words（19 词）与频率 10 级、数量 5 组", "page": "p175–176",
             "items": ["见书 p175 的 happy words 表与 p175–176 的频率分级表（完整清单见解析文件）"]},
        ],
        "checks": [
            "每组结果都先引导读者看图表，再陈述结果",
            "关键数字都带评价性语言，含义被明确「固定」",
            "报告了统计量与不确定性（如 95% 置信区间）",
            "与他研究结果比较时使用了恰当的对比语言",
            "因果动词与因果强度匹配（未用 linked/related 暗示因果）",
            "时态与信心一致（was related vs is related 未混用）",
            "结果的问题/局限在 Results 内首次承认，并给了原因",
            "启示与讨论未越界（Details 留给 Discussion）",
            "图表引用用词正确（from = 可推断；in = 图形可见）",
        ],
        "note": "两个必须按目标期刊现场调整的变量：Methods 是否只在补充材料（决定 Results 开头方法综述的详略）；是否要求 Research in Context 比较栏。",
    },
    # ------------------------------------------------------------------ 06 讨论
    {
        "id": 6,
        "key": "discussion",
        "title": "讨论 Discussion",
        "spec": "Unit 4 · 书 p189–241",
        "goal": "把结果向前推进成结论：与文献映射、明确贡献与影响，并诚实交代局限。",
        "model": [
            {"en": "ANNOUNCE THE STRUCTURE OR CONTENT OF THE DISCUSSION SECTION", "zh": "①宣告本节结构或内容"},
            {"en": "STATE THE ACHIEVEMENT/CONTRIBUTION OF THE STUDY", "zh": "②陈述研究的成就/贡献"},
            {"en": "REVISIT BACKGROUND INFORMATION/LITERATURE TO ‘REBOOT’ READER", "zh": "③回顾背景/文献以「重启」读者"},
            {"en": "REVISIT GAP/AIM/METHOD", "zh": "④回顾空白/目的/方法"},
            {"en": "REVISIT RESULTS AND EXPLORE THEIR IMPLICATIONS", "zh": "⑤回顾结果并探究其含义"},
            {"en": "MAP TO LITERATURE/KNOWLEDGE FOR COMPARISON/SUPPORT", "zh": "⑥映射到文献/知识以作比较或支撑"},
            {"en": "IDENTIFY POTENTIAL LIMITATIONS AND SUGGESTIONS FOR FUTURE WORK", "zh": "⑦指出潜在局限与未来工作建议"},
            {"en": "RESTATE THE ACHIEVEMENT/CONTRIBUTION/IMPACT OF THE STUDY", "zh": "⑧重述成就/贡献/影响"},
            {"en": "IDENTIFY POTENTIAL APPLICATIONS", "zh": "⑨指出潜在应用"},
        ],
        "must": [
            "与 Introduction 成镜像：从结果向外扩展，直到结论",
            "明确认领贡献：方法与结果本身、对文献界的影响、对产业与现实世界的影响（四类之一）",
            "把结果与既有文献对照（一致 / 矛盾 / 补充 / 延伸）",
            "局限与未来工作；语言强度与结果强度匹配",
        ],
        "must_not": [
            "只重复或改写 Results（必须 move on from the Results）",
            "语言强度超过结果能支持的程度（会成为审稿批评点）",
            "把成就写成无人称主语的现在时句 —— 会被读成背景或研究空白",
        ],
        "language": [
            {"rule": "情态动词六组分级：①ABLE（can / be able to）②POSSIBLE/OPTIONAL（may / might / could；it is possible）③EXPECTED/LIKELY（should）④OBVIOUS/IMPOSSIBLE（must / cannot）⑤ADVISABLE/RECOMMENDED（should）⑥NECESSARY/ESSENTIAL（must / need to / have to）", "page": "p232–241"},
            {"rule": "must 看似最强，实际传达「缺乏证据」；can 有歧义；can not ≠ cannot；must not = 不允许（非不可能）；have to 偏口语", "page": "p232–239"},
            {"rule": "Present Simple vs Past Simple 的确定性差异无法靠查阅目标文章解决：was related（仅本研究）vs is related（恒久真理）", "page": "p201–204"},
            {"rule": "引用句首模板可复用：We first demonstrated that ___, consistent with the literature (2,4,45).", "page": "p198"},
            {"rule": "future work 的 * 标注句表示作者自己在做（further work is planned / work is underway），不是对他人的邀请", "page": "p225"},
        ],
        "phrases": [
            {"group": "MAP TO LITERATURE / KNOWLEDGE", "page": "p222–223",
             "items": ["consistent with", "in line with", "to the best of our knowledge",
                       "shed new light on", "unlike", "substantiate", "support", "verify",
                       "contradict", "extend", "complement"]},
            {"group": "REFINE / EXPLORE IMPLICATIONS", "page": "p223–224",
             "items": ["plausible", "tentative", "it is conceivable that"]},
            {"group": "ACHIEVEMENT / CONTRIBUTION", "page": "p224–226",
             "items": ["'happy' words（约 50 个）与 '!' 替代词（约 22 个），完整清单见书 p224–226"]},
            {"group": "CURRENT AND FUTURE WORK", "page": "p225–226",
             "items": ["further work is planned", "work is underway"]},
            {"group": "APPLICATIONS / USE / APPLICABILITY / IMPLEMENTATION", "page": "p227–228",
             "items": ["applicable", "to implement", "to enable"]},
            {"group": "MODAL VERBS · 原书例句", "page": "p232–239",
             "items": ["The model can predict a wide range of experimental data.",
                       "= The model is able to predict a wide range of experimental data.",
                       "This intervention may/could/might lead to effective treatments.",
                       "= It is possible that this intervention will lead to effective treatments.",
                       "The ratio should remain constant if the expansion is uniform.",
                       "The tubes must/need to/have to be centrifuged before the experiment.",
                       "= It is necessary to centrifuge the tubes before the experiment."]},
        ],
        "checks": [
            "开头即点明本研究的成就/贡献，或明确「重启读者」所回顾的内容",
            "九个组件齐备（成就/贡献可按目标期刊惯例在开头、结尾或贯穿）",
            "结果与既有文献逐条对照，说明了是一致的、矛盾的还是补充的",
            "对不一致的结果给出了可能解释，未回避",
            "局限写得诚实且具体，并给出未来工作方向",
            "情态动词的确定性等级与结果强度匹配",
            "成就句的贡献归属清晰（读者清楚这是本研究做的）",
            "结尾落在应用/影响上，与标题和摘要的承诺一致",
            "Discussion 未变成 Results 的复述（每段都向前推进）",
        ],
        "note": "写作前先判定主要贡献属四类之一：方法 / 结果本身 / 对文献界的影响 / 对产业与现实世界的影响。",
    },
    # ------------------------------------------------------------------ 07 结论
    {
        "id": 7,
        "key": "conclusion",
        "title": "结论 Conclusion",
        "spec": "Unit 5 · 书 p243–261",
        "goal": "用最少的字交付明确的 take-home message：本研究达成了什么、影响在哪。",
        "model": [
            {"en": "WHAT IS IN THE PAPER", "zh": "①论文包含什么"},
            {"en": "WHAT THE PAPER/STUDY HAS ACHIEVED", "zh": "②本研究已达成什么"},
            {"en": "RELEVANT BACKGROUND INFORMATION", "zh": "③相关背景信息"},
            {"en": "THE GAP/AIM/NEED FOR THE STUDY", "zh": "④空白/目的/研究之必要"},
            {"en": "THE METHOD/APPROACH", "zh": "⑤方法/路径"},
            {"en": "KEY RESULTS WITH EVALUATIVE COMMENTS", "zh": "⑥关键结果并加评价"},
            {"en": "IMPLICATIONS OF THE RESULTS", "zh": "⑦结果的启示"},
            {"en": "POTENTIAL OR ACTUAL LIMITATIONS", "zh": "⑧潜在或实际局限"},
            {"en": "POTENTIAL OR ACTUAL APPLICATIONS", "zh": "⑨潜在或实际应用"},
            {"en": "HOW THE STUDY ADVANCES KNOWLEDGE", "zh": "⑩本研究如何推进知识"},
            {"en": "POTENTIAL FUTURE DIRECTIONS FOR RESEARCH", "zh": "⑪未来研究方向"},
        ],
        "must": [
            "11 个组件按目标文章的实际顺序与占比组织",
            "聚焦 outcome 与 impact 的 take-home message",
            "长度通常 100–200 词、1–2 个短段",
        ],
        "must_not": [
            "把 Abstract 当作写 Conclusion 的主要素材（原书明确禁止）",
            "只做重复或摘要 —— Conclusion 必须 go beyond either repetition or summary",
            "引入正文未呈现的新数据或新论证",
        ],
        "language": [
            {"rule": "成就/论断/论文内容 → Present Simple 或 Present Perfect", "page": "p259"},
            {"rule": "方法要点与关键结果复述 → Past Simple（但较不常见）", "page": "p259"},
            {"rule": "Owning your contribution：非人称主语 + 现在时的成就句会被读成背景或空白；解药是过去时/现在完成时、主动语态、人称主语、显式指向本文（This study… / In the present paper… / here）", "page": "p260–262"},
            {"rule": "It is argued that 存在归属歧义（原书脚注点名）", "page": "p250"},
        ],
        "phrases": [
            {"group": "词块来源说明", "page": "p258",
             "items": ["Unit 5 不设独立词块表：组件 1 → Units 1&2；2 → Unit 4；3 → all Units；"
                       "4 → Unit 1；5 → Units 2&3；6 → Units 2&3；7 → Unit 3；8 → Units 2&3；"
                       "9 → Unit 4；10 → Unit 4；11 → Unit 4"]},
        ],
        "checks": [
            "长度控制在 100–200 词、1–2 段（目标期刊另有规定时从其规定）",
            "交付了明确的 take-home message（读者能一句话复述）",
            "成就句的贡献归属清晰，未被读成背景或空白",
            "时态正确：成就/内容用现在时或现在完成时，方法/结果复述用过去时",
            "未从 Abstract 直接搬运句子",
            "未超出正文呈现的内容（无新数据、新论证）",
            "应用的取舍有据：与目标期刊惯例一致（有的重应用，有的重局限与未来工作）",
            "与标题、摘要的承诺一致，未 overstate",
        ],
        "note": "本单元的六篇样例把 Synopsis / Highlights / Abstract 与 Conclusion 并置，正是为了暴露「摘要≠结论」的差异。",
    },
]


def by_key(key: str) -> dict:
    for s in SHAPE:
        if s["key"] == key:
            return s
    raise KeyError(key)


# ---- 状态助手：统一委托给 scope_core（与 Statistic 页共用同一套逻辑）----
def _store(project) -> dict:
    return getattr(project, "shape", None) or {}


def _checked(project, key: str) -> dict:
    """读取某章的勾选记录（{索引: True}）。"""
    return scope_core.checked(_store(project), key)


def section_progress(project, sec: dict) -> tuple[int, int]:
    """返回 (已勾选数, 总检查项数)。"""
    return scope_core.progress(_store(project), sec)


def section_state(project, sec: dict) -> str:
    """环节状态：done / doing / todo。"""
    return scope_core.state(_store(project), sec)


def overall(project) -> tuple[int, int, int]:
    """全书汇总：返回 (已完成章节数, 进行中章节数, 总检查项已勾选数)。"""
    return scope_core.overall(_store(project), SHAPE)


def total_checks() -> int:
    return scope_core.total_checks(SHAPE)
