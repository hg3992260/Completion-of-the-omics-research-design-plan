# -*- coding: utf-8 -*-
"""Statistic —— 科学问题统计计算与归纳的 9 阶段架构（供 GUI 的 Statistic 页使用）。

来源（全部为工作区/本机已有产物，未联网、未杜撰）：
  · `helm-main/stat-pipeline.html` —— 9 阶段方法学内容（目标/核心动作、示例化表述、
    常见陷阱、公式、输出）与 12 行「常用检验速查表」
  · `helm-main/HANDOVER.md` —— 该 pipeline 的封装记录（9 阶段 + 工具映射）
  · `F:\\RSNA\\stat_pipeline_mcp\\mcp_stat_pipeline\\state.py` —— 权威阶段定义（id/类别/图标）
  · `F:\\RSNA\\stat_pipeline_mcp\\mcp_stat_pipeline\\tools.py` —— 12 个工具及其归属阶段
  · `F:\\RSNA\\stat_pipeline_mcp\\mcp_stat_pipeline\\stats.py` —— 计算层支持的检验种类

阶段类别（5 类）沿用原架构：design 问题与设计 / data 数据与探索 / method 建模与检验 /
infer 归纳推断 / report 报告与复现。
"""

CATS = {
    "design": {"n": "问题与设计", "c": "#58a6ff"},
    "data": {"n": "数据与探索", "c": "#39d2c0"},
    "method": {"n": "建模与检验", "c": "#a371f7"},
    "infer": {"n": "归纳推断", "c": "#3fb950"},
    "report": {"n": "报告与复现", "c": "#db6d28"},
}

# 12 个工具（7 控制 + 5 计算），来自 tools.py 的 register_all
TOOLS = {
    "会话控制": ["stat_session_start", "stat_resume", "stat_status",
             "stat_stage_complete", "stat_stage_note", "stat_conclude",
             "stat_export_report"],
    "统计计算": ["stat_sample_size", "stat_describe", "stat_run_test",
             "stat_effect_ci", "stat_correct_pvalues"],
}

STAGES = [
    {
        "id": 1, "key": "s1_question", "cat": "design", "icon": "🎯",
        "title": "问题定义与假设形式化",
        "spec": "问题与设计 · 阶段 1/9",
        "desc": "把模糊的科学问题翻译为可检验的 H₀/H₁ 与明确变量",
        "goal_title": "目标",
        "goal": [
            "判定研究问题类型：描述（估计总体参数）/ 差异比较 / 相关关联 / 预测 / 因果效应",
            "明确暴露或自变量 X、结局或因变量 Y，以及必须控制的混杂 C",
            "写出零假设 H₀ 与备择假设 H₁（应事先规定，避免事后讲故事）",
            "确定变量测量尺度：连续 / 有序 / 二分类 / 无序多分类",
            "锁定唯一主要结局指标（primary endpoint）",
        ],
        "example_title": "示例化表述",
        "example": "「与安慰剂相比，药物 A 是否降低 30 天死亡率？」\n"
                   "H₀: p_A = p_placebo；H₁: p_A ≠ p_placebo ｜ 结局 = 二分类，比较 = 两独立比例",
        "formula": [],
        "pitfalls": [
            "事后假设：看了数据再定 H₁",
            "结果变量过多导致多重比较失控",
            "暴露与结局的边界模糊",
            "假设不可证伪",
        ],
        "output_title": "输出",
        "output": ["可检验的 H₀/H₁", "X / Y / 混杂清单", "主要结局定义与测量尺度"],
        "tools": ["stat_session_start"],
        "checks": [
            "研究问题类型已明确（描述/比较/关联/预测/因果）",
            "自变量 X、结局 Y 与混杂 C 已逐一列明",
            "H₀ / H₁ 在拿到数据之前就已写定",
            "主要结局（primary endpoint）唯一且明确",
            "每个变量的测量尺度已标注（连续/有序/二分类/多分类）",
            "假设可被数据证伪（不是同义反复）",
        ],
        "note": "本阶段对应工具 stat_session_start：开始会话并在浏览器打开实时进度页。",
    },
    {
        "id": 2, "key": "s2_design", "cat": "design", "icon": "📐",
        "title": "研究设计与样本量",
        "spec": "问题与设计 · 阶段 2/9",
        "desc": "选择比较结构、控制偏倚，并用功效分析算出需要多少样本",
        "goal_title": "设计类型与比较结构",
        "goal": [
            "设计类型：实验（RCT）/ 准实验 / 观察性（队列、病例对照、横断面）",
            "组间结构：两组独立 / 配对 / 重复测量（前-后）/ ≥3 组 / 分层（block）",
            "偏倚控制：随机化、盲法、对照、配对或分层、限制混杂",
        ],
        "example_title": "功效分析（样本量 n）",
        "example": "两组均值比较：n = 2 (Z₁₋α/₂ + Z₁₋β)² σ² / δ²\n"
                   "需输入：显著性水平 α（常 0.05）、功效 1−β（常 0.80）、"
                   "最小可检出效应量 δ 与方差 σ²",
        "formula": ["两组均值比较：n = 2 (Z₁₋α/₂ + Z₁₋β)² σ² / δ²",
                    "效应量来源：既往文献 / 先导研究 / 最小临床意义差（MCID）"],
        "pitfalls": [
            "样本量不足 → 阴性结果可能只是功效低（应给出功效不足的解释）",
            "用观测到的效应量做「事后功效分析」属循环论证",
            "选择偏倚与信息偏倚污染推断",
        ],
        "output_title": "输出",
        "output": ["设计类型与组间结构", "偏倚控制措施", "既定 α/功效/δ 下的样本量（分组）"],
        "tools": ["stat_sample_size"],
        "checks": [
            "设计类型（实验/准实验/观察性）与比较结构已明确",
            "偏倚控制手段已写明（随机化、盲法、对照、配对或分层）",
            "样本量由功效分析得出，而非「经验值」",
            "α、功效、最小可检出效应量 δ 三个输入均已报告来源",
            "效应量来源可追溯（文献 / 先导研究 / MCID）",
            "未用观测效应量做事后功效分析",
            "分组样本量已分别列出（含失访或不完整数据预期）",
        ],
        "note": "对应工具 stat_sample_size（design: two_ind | paired | one；两比例比较传 p1、p2）。",
    },
    {
        "id": 3, "key": "s3_preprocess", "cat": "data", "icon": "🧹",
        "title": "数据采集与预处理",
        "spec": "数据与探索 · 阶段 3/9",
        "desc": "缺失值、异常值、类型与编码的决策必须可审计",
        "goal_title": "缺失值处理",
        "goal": [
            "判断缺失机制：MCAR 完全随机 / MAR 随机但依赖其他变量 / MNAR 非随机",
            "处理手段：完整案例分析（慎用）· 均值或中位数插补 · 多重插补（MICE）· 模型预测",
            "关键：建模前的任何预处理统计（标准化、插补）都应在训练折内拟合，防止数据泄漏",
        ],
        "example_title": "异常值与类型",
        "example": "异常值判定：物理边界 / IQR 规则（Q1 − 1.5·IQR）/ 稳健 z 分数\n"
                   "决策：保留（稳健方法或变换）/ 截断（winsorize）/ 剔除 —— 均须记录理由\n"
                   "类型转换：分类变量正确编码（哑变量或顺序编码），单位与小数位数统一",
        "formula": ["IQR 规则：低于 Q1 − 1.5·IQR 或高于 Q3 + 1.5·IQR 视为可疑异常"],
        "pitfalls": [
            "清洗决策不可复现（不写日志）",
            "整行删除在缺失非随机时引入偏倚",
            "把泄漏的全局统计（全样本均值/方差）用于分割后的训练",
        ],
        "output_title": "输出",
        "output": ["缺失概览与处理记录", "异常值判定与处置理由", "变量类型与编码表"],
        "tools": [],
        "checks": [
            "缺失机制已判断（MCAR / MAR / MNAR）并写明依据",
            "插补或删除的每一步都有记录，可被第三方复现",
            "未用整行删除处理非随机缺失",
            "异常值判定规则与处置方式（保留/截断/剔除）已记录理由",
            "标准化、插补等预处理只在训练折内拟合（无数据泄漏）",
            "分类变量编码方式已说明（哑变量/顺序），单位与小数位统一",
            "预处理脚本与参数已保存，可重跑",
        ],
        "note": "本阶段没有对应计算工具：由数据准备脚本承担，但决策必须留痕（可写回 stat_stage_note）。",
    },
    {
        "id": 4, "key": "s4_eda", "cat": "data", "icon": "📊",
        "title": "探索性分析 EDA",
        "spec": "数据与探索 · 阶段 4/9",
        "desc": "先看清分布与结构，再选检验——EDA 决定统计方法的适用性",
        "goal_title": "核心动作",
        "goal": [
            "描述统计：均值/中位数、SD/IQR、偏度、分位数（按分组拆开）",
            "分布形态：直方图、QQ 图、正态性检验（Shapiro–Wilk）",
            "组间比较可视化：箱线图 / 小提琴图 / 误差条；散点看相关与趋势",
            "检查聚类或嵌套结构（多中心、同一受试多观测）——影响独立性假设",
        ],
        "example_title": "输出",
        "example": "EDA 报告：样本量 n、各组 n、缺失概览、分布与相关图；"
                   "由此决定第 6 步的方法族（参数 / 非参 / 稳健）",
        "formula": [],
        "pitfalls": [
            "只看均值不看分布",
            "小样本下对某个离群点过度反应",
            "忽略嵌套结构，把非独立观测当独立",
        ],
        "output_title": "输出",
        "output": ["n 与各组 n", "分布图与相关图", "方法族选择依据"],
        "tools": ["stat_describe"],
        "checks": [
            "已给出各组样本量与总体样本量",
            "描述了分布形态，而不只是均值 ± SD",
            "分组比较有可视化（箱线/小提琴/误差条）支撑",
            "相关或趋势用散点图核查过（未只看相关系数）",
            "检查过聚类/嵌套结构（多中心、重复测量）",
            "已据 EDA 确定第 6 步的方法族（参数/非参/稳健）",
        ],
        "note": "对应工具 stat_describe（描述统计 + Shapiro 正态性初步诊断）。",
    },
    {
        "id": 5, "key": "s5_assumption", "cat": "method", "icon": "🧪",
        "title": "前提条件诊断",
        "spec": "建模与检验 · 阶段 5/9",
        "desc": "参数检验的适用前提需先验证；违背则换道而非硬跑",
        "goal_title": "前提逐项检查",
        "goal": [
            "独立性：观测是否相互独立（最常被违反、且无法事后补救）",
            "正态性：Shapiro–Wilk / QQ 图；注意大 n 下检验对轻微偏离过敏感，可用图形判断",
            "方差齐性：Levene / Bartlett（两独立组可直接用 Welch 绕开）",
            "线性与同方差（回归）：残差 vs 拟合值图、VIF 共线性诊断",
        ],
        "example_title": "违背时怎么办",
        "example": "非参替代（Mann–Whitney / Wilcoxon / Kruskal–Wallis）· Welch 校正 t · "
                   "数据变换（log / Box–Cox）· 置换检验或 bootstrap · 稳健估计",
        "formula": [],
        "pitfalls": [
            "把正态性检验的 p 当作「是否允许 t 检验」的唯一裁决"
            "（大样本轻微偏离无碍，中心极限定理兜底）",
            "忘记检验独立性",
        ],
        "output_title": "输出",
        "output": ["逐项前提检查结果", "违背时的替代方案与理由"],
        "tools": ["stat_run_test"],
        "checks": [
            "独立性已评估（含嵌套/重复测量结构）",
            "正态性用图形 + 检验共同判断，未只看 p 值",
            "方差齐性已检验（或直接采用 Welch 并在文中说明）",
            "回归类分析已检查线性、同方差与共线性（VIF）",
            "前提违背时说明了替代方案（非参/Welch/变换/置换/bootstrap）",
            "前提检查结果写进了方法与结果，而非省略",
        ],
        "note": "对应工具 stat_run_test(kind=\"levene\")（该调用会记入阶段 5）。",
    },
    {
        "id": 6, "key": "s6_test", "cat": "method", "icon": "🔬",
        "title": "检验计算",
        "spec": "建模与检验 · 阶段 6/9",
        "desc": "由「比较结构 + 尺度 + 前提」定位检验；算统计量、p 值，并校正多重比较",
        "goal_title": "要点",
        "goal": [
            "检验在拿到数据前预先登记（区分确认性 confirmatory 与探索性 exploratory）",
            "明确单侧或双侧；报告检验统计量、自由度或样本量、p 值、效应量",
            "多重比较校正：Bonferroni / Holm / Benjamini–Hochberg (FDR) 依场景选择",
        ],
        "example_title": "方法定位依据",
        "example": "比较结构（两组/多组/配对/相关/列联）× 变量尺度（连续/有序/二分类）"
                   "× 前提是否满足 → 决定用哪一族检验",
        "formula": [],
        "pitfalls": [
            "p-hacking：反复试方法直到显著",
            "对同一数据做多种检验，只挑好看的报告",
            "只报 p 不报效应量与区间",
            "把 p ≈ 0.06 说成「边缘显著」",
        ],
        "output_title": "输出",
        "output": ["检验统计量与自由度/样本量", "p 值（含单双侧说明）", "多重比较校正结果"],
        "tools": ["stat_run_test", "stat_correct_pvalues"],
        "checks": [
            "检验类型与比较结构、变量尺度、前提检查一致",
            "预先登记了主要检验（未在数据上游荡选方法）",
            "明确说明了单侧/双侧",
            "报告了检验统计量与自由度或样本量",
            "多重比较用 Bonferroni / Holm / FDR-BH 之一校正，并说明选择理由",
            "所有运行的检验都报告（含不显著与校正后不显著）",
            "未把 p ≈ 0.06 描述为「边缘显著」",
        ],
        "note": "对应工具：stat_run_test（16 种检验）与 stat_correct_pvalues（fdr_bh | bonferroni | holm）。",
    },
    {
        "id": 7, "key": "s7_effect", "cat": "method", "icon": "⚖️",
        "title": "效应量与置信区间",
        "spec": "建模与检验 · 阶段 7/9",
        "desc": "p 值回答「有没有」，效应量与置信区间回答「有多大、多准」",
        "goal_title": "效应量（随检验类型而定）",
        "goal": [
            "解释基准仅供参考，须结合领域意义：d ≈ 0.2 / 0.5 / 0.8（小/中/大）",
            "比率型指标：比值比 OR、相对风险 RR、风险比 HR（均给 95% CI）",
        ],
        "example_title": "不确定性量化",
        "example": "报告 95% 置信区间：θ̂ ± t·SE，或 bootstrap(BCa) / 剖面似然区间\n"
                   "频率派 CI 含义：重复抽样中约 95% 的区间会覆盖真实值 —— "
                   "不是「参数落在这个区间的概率是 95%」\n预测场景应额外给出预测区间（含个体波动）",
        "formula": ["Cohen d = (x̄₁ − x̄₂) / s_pooled",
                    "η² = SS_between / SS_total",
                    "r（Pearson）· OR / RR / HR",
                    "95% CI：θ̂ ± t·SE（或 bootstrap BCa）"],
        "pitfalls": [
            "只报 p 值（n 足够大时无意义差异也能显著）",
            "把统计显著等同于临床或实际重要差异",
        ],
        "output_title": "输出",
        "output": ["效应量及其类型", "95% 置信区间", "（预测场景）预测区间"],
        "tools": ["stat_effect_ci"],
        "checks": [
            "每个主要比较都给出了效应量（不只是 p 值）",
            "效应量的类型与检验匹配（d / η² / r / OR / RR / HR）",
            "报告了 95% 置信区间，并正确解读其含义",
            "未把统计显著直接说成临床重要",
            "预测类结论给出了预测区间（含个体波动）",
            "比率的区间是在正确尺度上构造的（OR/RR/HR 用 log 尺度）",
        ],
        "note": "对应工具 stat_effect_ci（transform: identity | log | logit）。",
    },
    {
        "id": 8, "key": "s8_infer", "cat": "infer", "icon": "🧠",
        "title": "归纳推断与结论",
        "spec": "归纳推断 · 阶段 8/9",
        "desc": "从样本到总体的推断，必须限定因果语言与外推边界",
        "goal_title": "统计关联 vs 因果效应",
        "goal": [
            "观察性数据默认只能做关联推断；声称因果需要：设计（RCT），"
            "或 DAG + 混杂调整 + 敏感性分析",
            "用 DAG 找最小充分调整集（区分混杂、中介、碰撞器 collider）",
            "中介（mediation）与交互（interaction）分析若在计划内，须预先声明",
        ],
        "example_title": "稳健性检验",
        "example": "换方法族复现（敏感性分析、多模型交叉验证、留一法）\n"
                   "结论措辞与证据强度匹配：样本能否外推到目标人群、缺失是否限制泛化",
        "formula": [],
        "pitfalls": [
            "把相关当因果",
            "忽略未测量混杂与选择偏倚",
            "把局限人群的结论过度外推",
            "显著性结果不报不确定性",
        ],
        "output_title": "输出",
        "output": ["关联或因果的明确措辞", "稳健性检验结果", "外推边界与局限"],
        "tools": ["stat_conclude"],
        "checks": [
            "结论措辞与设计相符（观察性研究未宣称因果）",
            "若声称因果，已给出 RCT 或 DAG + 混杂调整 + 敏感性分析",
            "做了稳健性检验（换方法族 / 敏感性分析 / 交叉验证）",
            "结论明确了外推的目标人群与边界",
            "局限（未测量混杂、选择偏倚、缺失）已写明",
            "显著性结论同时给出了不确定性",
        ],
        "note": "对应工具 stat_conclude：写入最终归纳结论（显示在进度页底部）。",
    },
    {
        "id": 9, "key": "s9_report", "cat": "report", "icon": "📦",
        "title": "报告与复现",
        "spec": "报告与复现 · 阶段 9/9",
        "desc": "方法可审计、结果可复现、假设与探索分开标注",
        "goal_title": "报告清单",
        "goal": [
            "样本量及其由来（功效分析）、入排标准、缺失或剔除数量",
            "统计方法逐项说明 + 软件及版本（如 Python scipy 1.14 / R 4.3）、随机种子",
            "确认性与探索性结果分开标注；报告所有运行的检验（含不显著的）",
            "遵循领域报告规范：医学用 CONSORT / STROBE / STARD，心理用 APA",
        ],
        "example_title": "复现三件套",
        "example": "数据（脱敏）+ 代码（固定 seed、固定依赖版本）+ "
                   "计算环境（requirements / lockfile / Docker）",
        "formula": [],
        "pitfalls": [
            "选择性报告（只报显著项）",
            "不固定随机种子导致无法复现",
            "把探索性发现包装成「先验假设的证实」",
        ],
        "output_title": "输出",
        "output": ["可分享的报告（HTML/表格 + 结论）", "数据+代码+环境三件套", "报告规范对照"],
        "tools": ["stat_stage_note", "stat_export_report"],
        "checks": [
            "样本量由来、入排标准、缺失与剔除数量均已报告",
            "统计方法逐项说明，并给出软件与版本号",
            "随机种子已固定并写入报告",
            "确认性与探索性结果分别标注",
            "所有检验（含不显著）都已报告，无选择性报告",
            "已按领域规范（CONSORT/STROBE/STARD/APA…）逐条自查",
            "数据、代码、计算环境可被第三方获取或重建",
        ],
        "note": "对应工具 stat_stage_note 与 stat_export_report（导出独立 HTML 报告副本）。",
    },
]

# 常用检验速查表（场景 / 方法 / 前提 / scipy / R），取自 stat-pipeline.html 的 CHEATSHEET
CHEATSHEET = [
    ["两组独立 · 连续", "独立 t 检验（Welch 若方差不齐）", "正态+独立(+齐性)",
     "scipy.stats.ttest_ind", "t.test"],
    ["两组独立 · 非正态", "Mann–Whitney U", "独立", "mannwhitneyu", "wilcox.test"],
    ["配对 / 前-后", "配对 t 检验", "差值近似正态", "ttest_rel", "t.test(paired=T)"],
    ["配对 · 非正态", "Wilcoxon 符号秩", "对称分布", "wilcoxon", "wilcox.test(paired=T)"],
    ["≥3 组 · 连续", "单因素 ANOVA + Tukey 事后", "正态+方差齐",
     "f_oneway / tukey_hsd", "aov / TukeyHSD"],
    ["≥3 组 · 非正态", "Kruskal–Wallis + Dunn", "独立样本",
     "kruskal / scikit-posthocs", "kruskal.test / dunn.test"],
    ["两组/多组比例", "卡方独立性 / Fisher 精确", "期望频数≥5(卡方)",
     "chi2_contingency / fisher_exact", "chisq.test / fisher.test"],
    ["二分类结局·多变量", "逻辑回归 → OR(95%CI)", "线性对数优势比",
     "statsmodels.Logit", "glm(family=binomial)"],
    ["连续结局·预测/因果", "线性回归 / 多元回归", "线性+独立+同方差",
     "statsmodels.OLS / sklearn", "lm"],
    ["两个连续变量相关", "Pearson / Spearman / Kendall", "线性(Pearson)",
     "pearsonr / spearmanr / kendalltau", "cor.test"],
    ["生存时间→事件", "Cox 比例风险 → HR", "比例风险假设",
     "lifelines.CoxPHFitter", "coxph"],
    ["重复/嵌套数据", "混合效应模型 / GEE", "随机效应结构正确",
     "statsmodels.MixedLM / MERF", "lme4::lmer / geepack"],
]

# stat_run_test 支持的 kind（来自 tools.py 文档字符串）
TEST_KINDS = ["ttest_ind", "welch", "mannwhitney", "ttest_paired", "wilcoxon",
              "ttest_1samp", "wilcoxon_1samp", "anova", "kruskal", "levene",
              "pearson", "spearman", "kendall", "chisq", "fisher", "binom_prop"]


def by_key(key: str) -> dict:
    for s in STAGES:
        if s["key"] == key:
            return s
    raise KeyError(key)
