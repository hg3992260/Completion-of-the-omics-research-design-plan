# -*- coding: utf-8 -*-
"""确定性信号核验层：不需要 LLM 就能判定、且能给出证据的硬缺陷。

为什么要这一层
------------
纯靠 LLM 通读手稿找缺陷有三个问题：不可复现、会漏（长文里"没写某参数"极难被发现）、
无法给出可核验的证据。而「手稿里有没有出现 ICC」「有没有报告管电压」这类检查
完全可以确定性完成，且结论比 LLM 更可靠。

所以本层负责**可证据化的硬缺陷**，LLM 只负责它擅长的语义判断（见 mr_reviewer.py）。
两层结果在 mr_engine.py 里合并，确定性结论优先。

每个信号返回统一结构：

    {"signal": 名称, "verdict": "missing" | "weak" | "reported",
     "evidence": 命中的原文片段（缺失时为空）,
     "matched":  命中的正则/词,
     "note":     一句面向作者的中文说明}

verdict 语义
    reported  已报告 —— 不生成缺陷
    weak      提到了但信息不完整（例如只说"增强CT"不给参数）→ 生成主要缺陷
    missing   完全没提 → 生成关键缺陷
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- 词表
# 每个信号 = (必须命中的任一组正则) 的列表；组内可含多个候选写法。
# 说明：中文手稿与英文手稿混排，故中英并列。

SIGNALS: dict[str, dict] = {
    # ---------------------------------------------------------------- 治理与伦理
    "ethics_approval": {
        "label": "伦理批号与批准机构",
        "strong": [r"伦理(?:委员会)?(?:批号|批准号|编号|审批号)", r"批准号\s*[：:]?\s*[\w\(（]",
                   r"IRB\s*(?:approval|number|no)", r"ethics\s+(?:approval|committee)",
                   r"institutional\s+review\s+board"],
        "weak": [r"伦理", r"ethic"],
        "hint": "需写明伦理批号（含机构名）与知情同意方式",
    },
    "informed_consent": {
        "label": "知情同意方式",
        "strong": [r"知情同意", r"豁免知情同意", r"书面同意", r"informed\s+consent",
                   r"waiver\s+of\s+consent"],
        "weak": [r"同意"],
        "hint": "回顾性研究须说明是否豁免知情同意及依据",
    },
    "registration_id": {
        "label": "研究方案注册号",
        "strong": [r"(?:注册号|注册编号|试验注册|ChiCTR|NCT\d{6,}|ISRCTN\d+|"
                   r"registration\s+(?:number|no)|clinicaltrials\.gov|"
                   r"Chinese\s+Clinical\s+Trial\s+Registry)",
                   r"方案(?:已)?(?:在|于)\s*\S{2,20}\s*注册"],
        "weak": [r"注册", r"registr"],
        "hint": "前瞻性研究须给出注册平台与注册号；回顾性研究也建议说明是否注册",
    },
    "data_source": {
        "label": "数据来源与采集时间窗",
        "strong": [r"(?:回顾性|前瞻性|多中心|单中心)", r"retrospective|prospective"],
        "weak": [r"收集|纳入|enrolled|recruit"],
        "hint": "需说明数据来源（单/多中心、回顾/前瞻）与纳入时间窗",
    },
    "data_overlap": {
        "label": "训练/验证集数据重叠核查",
        "strong": [r"(?:数据)?重叠", r"overlap", r"无(?:患者|病例)?(?:交叉|重复)",
                   r"独立(?:的)?(?:外部)?(?:验证)?(?:集|队列|中心)"],
        "weak": [r"训练集|验证集|training\s+set|validation\s+set"],
        "hint": "必须声明训练/内部测试/外部测试之间有无患者级重叠",
    },
    # ---------------------------------------------------------------- 样本量与设计
    "sample_size_rationale": {
        "label": "样本量估算依据（功效分析）",
        "strong": [r"样本量(?:估算|计算|估计)", r"功效(?:分析|检验)", r"power\s+(?:analysis|calculation)",
                   r"sample\s+size\s+(?:calculation|estimation)", r"把握度"],
        "weak": [r"样本量|sample\s+size"],
        "hint": "预测模型的样本量不能沿用两组比较的估算思路，须给出公式与参数（α、power、EPV）",
    },
    "event_counts": {
        "label": "各分析步骤的实际例数与事件数",
        "strong": [r"(?:事件数|结局事件|阳性例数|恶性例数|MVI\s*阳性)", r"events?\s+per\s+variable",
                   r"EPV"],
        "weak": [r"\d+\s*例", r"n\s*=\s*\d+"],
        "hint": "需报告每一步分析的实际例数与结局事件数（不只给总数）",
    },
    "inclusion_criteria": {
        "label": "纳入与排除标准",
        "strong": [r"纳入标准", r"排除标准", r"inclusion\s+criteria", r"exclusion\s+criteria",
                   r"入组标准"],
        "weak": [r"纳入|排除|included|excluded"],
        "hint": "需逐条列出纳入与排除标准，而非概述",
    },
    # ---------------------------------------------------------------- 图像采集
    "acquisition_params": {
        "label": "采集与重建参数（机型/管电压/管电流/层厚/重建核）",
        "strong": [r"(?:管电压|kVp|kV\b)", r"(?:管电流|mAs\b|自动曝光)",
                   r"(?:层厚|slice\s+thickness)", r"(?:重建(?:算法|核|卷积核)|kernel|"
                   r"iterative\s+reconstruction|ASIR|ADMIRE|iDose|FBP)",
                   r"(?:机型|扫描仪|SOMATOM|Revolution|LightSpeed|Aquilion|Discovery\s+CT|"
                   r"Brilliance|scanner)"],
        "weak": [r"增强CT|CT\s+(?:scan|examination)|门静脉期|portal\s+venous"],
        "hint": ("CLEAR 16 / METRICS #6：必须登记机型、管电压、管电流、层厚、重建算法与"
                 "卷积核，否则特征值不可复现"),
    },
    "contrast_phase": {
        "label": "对比剂方案与期相定义",
        "strong": [r"(?:对比剂|造影剂|碘海醇|碘克沙醇|碘佛醇|iohexol|iodixanol)",
                   r"(?:期相|延迟时间|注射后\s*\d+\s*s|trigger)",
                   r"(?:动脉期|门静脉期|延迟期|平衡期)"],
        "weak": [r"增强|contrast"],
        "hint": "需说明对比剂种类/浓度/剂量/流率、期相判定方式与延迟时间",
    },
    # ---------------------------------------------------------------- 分割
    "reader_qualification": {
        "label": "勾画者资质、经验年限与盲法",
        "strong": [r"(?:年经验|年资|工作年限|主治医师|副主任医师|主任医师|住院医师)",
                   r"(?:放射科|影像科)?医师\s*[12１２]\s*名",
                   r"(?:双人|两名|2\s*名|独立)勾画",
                   r"blinded|盲法|单盲|双盲"],
        "weak": [r"勾画|分割|segment", r"感兴趣区|ROI", r"delineat"],
        "hint": "CLEAR 20 / METRICS #8：需给出勾画者数量、资质、经验年限与是否盲法",
    },
    "icc_dice": {
        "label": "分割一致性（ICC / Dice）",
        "strong": [r"\bICC\b", r"组内相关系数", r"intraclass\s+correlation",
                   r"\bDice\b", r"Dice\s+(?:系数|similarity)", r"\bJaccard\b",
                   r"观察者(?:内|间)", r"inter-?\s*observer", r"intra-?\s*observer"],
        "weak": [r"一致性|重复性|reproducib", r"复核"],
        "hint": ("CLEAR 19–20 / METRICS #8–#10：分割是误差最大的环节，"
                 "必须用 ICC 或 Dice 量化，不能只写「由高年资医师复核」"),
    },
    "segmentation_strategy": {
        "label": "分割策略与工具版本",
        "strong": [r"(?:手动|半自动|全自动|自动)分割", r"(?:manual|semi-?automatic|automatic)\s+"
                   r"(?:segmentation|delineation)", r"3D\s*Slicer|ITK-?SNAP|nnU-?Net|"
                   r"TotalSegmentator|U-?Net"],
        "weak": [r"勾画|分割|segment"],
        "hint": "CLEAR 19：需明确分割策略（手动/半自动/自动）与所用工具及版本",
    },
    # ---------------------------------------------------------------- 特征提取
    "resampling": {
        "label": "重采样体素间距",
        "strong": [r"重采样", r"体素(?:间距|尺寸|大小)", r"resampl", r"voxel\s+size",
                   r"isotropic\s+(?:resampling|voxel)", r"插值"],
        "weak": [r"预处理|preprocess"],
        "hint": "CLEAR 21–22：必须给出重采样方法与目标体素间距（如 1×1×1 mm³）",
    },
    "discretization": {
        "label": "灰度离散化（binWidth / binCount）",
        "strong": [r"binWidth", r"bin\s*width", r"binCount", r"bin\s*(?:number|count)",
                   r"灰度(?:离散|分级|量化)", r"离散化(?:参数|方式)", r"fixed\s+bin"],
        "weak": [r"离散|discretiz"],
        "hint": "CLEAR 23：必须声明固定 binWidth 或固定 binCount，以及是否绝对离散化",
    },
    "normalization": {
        "label": "强度归一化方式",
        "strong": [r"归一化", r"标准化(?:强度|灰度)", r"normaliz", r"standardiz",
                   r"(?:Z-?score|z\s*score)\s*(?:归一|normaliz|transform)",
                   r"重采样到\s*\d+\s*(?:个)?(?:灰度)?(?:级|level)"],
        "weak": [r"预处理|preprocess"],
        "hint": "CLEAR 24：需说明强度归一化方式（Z-score / 直方图匹配 / 无）",
    },
    "ibsi": {
        "label": "IBSI 合规性声明",
        "strong": [r"\bIBSI\b", r"Image\s+Biomarker\s+Standardization\s+Initiative"],
        "weak": [r"标准化(?:特征)?定义|feature\s+definition"],
        "hint": "CLEAR 25–28 / IBSI：需声明特征定义是否遵循 IBSI 及其合规级别",
    },
    "feature_count": {
        "label": "特征类别与数量",
        "strong": [r"\d+\s*个(?:影像组学)?特征", r"特征(?:类别|数量|总数)",
                   r"first\s+order|一阶(?:统计)?(?:量|特征)", r"GLCM|GLRLM|GLSZM|GLDM|NGTDM",
                   r"形状特征|shape\s+feature", r"\d+\s+features"],
        "weak": [r"特征|features"],
        "hint": "CLEAR 26–27：需给出特征类别（一阶/形状/纹理）、各滤波器数量与总数",
    },
    "software_version": {
        "label": "软件名称与版本号",
        "strong": [r"PyRadiomics\s*\d", r"Python\s*\d+\.\d+", r"\bR\s*(?:version\s*)?\d+\.\d+",
                   r"SPSS\s*\d+", r"MATLAB\s*R?\d", r"scikit-?learn\s*\d",
                   r"(?:版本|version)\s*[：:]?\s*\d+\.\d+"],
        "weak": [r"PyRadiomics|SPSS|Python|R\s*语言|MATLAB"],
        "hint": "CLEAR 25 / 统计报告规范：必须给出软件及版本号（含影像组学与统计软件）",
    },
    "param_file": {
        "label": "完整参数文件（YAML / 脚本）",
        "strong": [r"(?:参数|配置)(?:文件|脚本|setting)", r"YAML", r"\.yaml|\.yml",
                   r"parameter\s+file", r"(?:代码|脚本)(?:已)?(?:公开|上传|共享)"],
        "weak": [r"参数|parameter"],
        "hint": "CLEAR 28：非默认参数需给出完整参数文件，否则无法复现",
    },
    # ---------------------------------------------------------------- 稳定性与维度
    "feature_stability": {
        "label": "特征稳定性筛选",
        "strong": [r"稳定(?:性)?(?:筛选|评估|分析)", r"(?:不)?稳健(?:性)?(?:特征)?",
                   r"stability\s+(?:analysis|selection|test)", r"ICC\s*[<≤>≥]\s*0?\.\d",
                   r"重抽样(?:筛|选)", r"bootstrap\s+(?:stability|selection)",
                   r"test-?retest"],
        "weak": [r"筛选|selection|LASSO"],
        "hint": ("METRICS #14：应先用重复勾画或重抽样剔除不稳健特征，再谈降维；"
                 "直接把数百特征丢进 LASSO 是常见硬伤"),
    },
    "collinearity": {
        "label": "共线性与冗余特征处理",
        "strong": [r"共线(?:性)?", r"collinear", r"(?:高度)?相关(?:性)?(?:特征)?(?:剔除|筛除)",
                   r"\bVIF\b", r"冗余(?:特征)?", r"redundan",
                   r"相关系数\s*[>≥]\s*0?\.\d"],
        "weak": [r"相关|correlat"],
        "hint": "METRICS #15：需说明如何剔除高度相关的冗余特征",
    },
    "dimension_ratio": {
        "label": "特征数与样本量/事件数的匹配",
        "strong": [r"(?:特征数|变量数)(?:与|/)?(?:样本量|事件数)",
                   r"EPV", r"每(?:个)?(?:变量|特征)(?:的)?事件",
                   r"events?\s+per\s+(?:variable|predictor)",
                   r"维度(?:匹配|约简|控制)"],
        "weak": [r"过拟合|overfit"],
        "hint": "METRICS #16：最终特征数必须与样本量、事件数匹配，否则过拟合无法避免",
    },
    # ---------------------------------------------------------------- 建模与验证
    "primary_model": {
        "label": "预设主模型（非 best-of-N 择优）",
        "strong": [r"主(?:要)?模型", r"预设(?:的)?模型", r"primary\s+model",
                   r"pre-?specified\s+model", r"最终(?:选定|确定)(?:的)?模型"],
        "weak": [r"模型|model"],
        "hint": ("TRIPOD+AI 12 / METRICS #18：应预先指定主模型；"
                 "「并列构建 11 个模型取最好者」会让性能估计乐观偏倚"),
    },
    "nested_cv": {
        "label": "嵌套交叉验证与信息泄漏控制",
        "strong": [r"嵌套(?:交叉验证|cross)", r"nested\s+cross-?validation",
                   r"内层(?:交叉)?验证", r"inner\s+(?:loop|cv)",
                   r"(?:特征选择|调参)(?:在|放)(?:训练集|内层)"],
        "weak": [r"交叉验证|cross-?validation", r"k\s*折|10\s*折|五折|5-?fold"],
        "hint": ("TRIPOD+AI 12b / METRICS #18：特征选择与调参必须放进内层交叉验证；"
                 "用全体数据筛特征再划分 = 信息泄漏"),
    },
    "tuning": {
        "label": "超参数调优方式",
        "strong": [r"超参数|hyper-?parameter", r"(?:网格|随机)搜索|grid\s+search|"
                   r"random\s+search", r"调参|调优", r"贝叶斯优化|Bayesian\s+opt"],
        "weak": [r"参数|parameter"],
        "hint": "TRIPOD+AI 12c：需说明调参方式、搜索空间与选择依据",
    },
    "external_validation": {
        "label": "独立外部验证",
        "strong": [r"外部验证", r"external\s+validation", r"独立(?:的)?(?:验证)?(?:队列|中心|数据集)",
                   r"另一家?(?:医院|中心)", r"多中心(?:队列|验证)"],
        "weak": [r"验证集|validation\s+set", r"测试集|test\s+set"],
        "hint": "TRIPOD+AI 12e / METRICS #26–27：外部验证必须真正独立，不能是同一批数据再切一刀",
    },
    "model_update": {
        "label": "模型更新过程",
        "strong": [r"模型更新", r"model\s+update", r"重新校准|recalibrat",
                   r"系数(?:重新)?(?:估计|调整)"],
        "weak": [r"更新|update"],
        "hint": "TRIPOD+AI 12f：若在外部数据上更新模型，须说明更新内容与幅度",
    },
    # ---------------------------------------------------------------- 评价与效用
    "confidence_interval": {
        "label": "性能指标的 95% 置信区间",
        "strong": [r"95\s*%\s*(?:CI|置信区间)", r"95\s*%\s*confidence\s+interval",
                   r"\bCI\b\s*[：:]?\s*\d"],
        "weak": [r"置信区间|confidence\s+interval"],
        "hint": "CLEAR 40 / METRICS #21：AUC 等指标必须带 95% CI，只给点估计无法判断精度",
    },
    "calibration": {
        "label": "校准评估（校准曲线 / 斜率 / HL 检验）",
        "strong": [r"校准(?:曲线|度|分析)", r"calibration\s+(?:curve|plot|slope)",
                   r"Hosmer-?Lemeshow", r"校准截距|calibration-?in-?the-?large",
                   r"Brier\s+score"],
        "weak": [r"一致性|agreement"],
        "hint": ("TRIPOD+AI 12d / METRICS #23：判别力（AUC）只是起点，"
                 "必须评估校准，否则预测概率不可用于决策"),
    },
    "dca": {
        "label": "决策曲线与临床净获益",
        "strong": [r"决策曲线", r"\bDCA\b", r"decision\s+curve", r"净获益|net\s+benefit",
                   r"临床影响(?:曲线|分析)", r"clinical\s+impact"],
        "weak": [r"临床(?:效用|价值|应用)"],
        "hint": "CLEAR 41 / METRICS #24：需给出 DCA 或临床影响分析，说明是否真有净获益",
    },
    "incremental_value": {
        "label": "相对非组学模型的增量价值",
        "strong": [r"\bNRI\b", r"\bIDI\b", r"净重新分类", r"net\s+reclassification",
                   r"integrated\s+discrimination", r"增量(?:价值|效能)",
                   r"(?:临床|传统)(?:模型|因素)(?:与|vs\.?|联合)"],
        "weak": [r"优于|优于传统|compared\s+with"],
        "hint": "CLEAR 42 / METRICS #25：宣称优于临床模型必须有统计比较（DeLong / NRI / IDI）",
    },
    "model_comparison": {
        "label": "模型间统计比较方法",
        "strong": [r"DeLong", r"德隆", r"模型(?:间)?比较", r"统计学比较",
                   r"likelihood\s+ratio\s+test", r"似然比检验"],
        "weak": [r"比较|compar"],
        "hint": "CLEAR 41：模型间差异需给出检验方法，不能只比 AUC 数值大小",
    },
    # ---------------------------------------------------------------- 统计
    "primary_endpoint": {
        "label": "唯一的主要结局指标",
        "strong": [r"主要(?:结局|终点|指标)", r"主要研究终点", r"primary\s+(?:endpoint|outcome)"],
        "weak": [r"结局|终点|outcome|endpoint"],
        "hint": "统计阶段 1：必须锁定唯一主要结局，否则多重比较失控",
    },
    "multiplicity": {
        "label": "多重比较校正",
        "strong": [r"(?:Bonferroni|Holm|Benjamini|Hochberg|FDR|错误发现率)",
                   r"多重(?:比较|检验)(?:校正|调整)", r"multiple\s+(?:comparison|testing)\s+"
                   r"(?:correction|adjust)", r"校正后?\s*P"],
        "weak": [r"校正|adjust"],
        "hint": "统计阶段 5：多组/多次检验必须说明校正方法，否则假阳性不可控",
    },
    "assumption_check": {
        "label": "统计检验前提诊断",
        "strong": [r"(?:正态性|方差齐性)(?:检验|检验结果)?", r"Shapiro-?Wilk",
                   r"Kolmogorov-?Smirnov", r"Levene", r"正态分布检验",
                   r"normality\s+(?:test|assumption)", r"前提(?:检验|诊断|假设)"],
        "weak": [r"t检验|方差分析|卡方检验|非参数"],
        "hint": "统计阶段 4：用 t 检验/ANOVA 前须报告正态性与方差齐性检验结果",
    },
    "effect_size": {
        "label": "效应量与置信区间",
        "strong": [r"效应量|effect\s+size", r"\bOR\b\s*[=＝]", r"\bHR\b\s*[=＝]",
                   r"\bRR\b\s*[=＝]", r"Cohen'?s\s+d", r"标准化均数差|\bSMD\b",
                   r"均数差|mean\s+difference"],
        "weak": [r"OR|HR|RR"],
        "hint": "统计阶段 6：报告 P 值之外必须给效应量及其置信区间",
    },
    "missing_data": {
        "label": "缺失数据处理",
        "strong": [r"缺失(?:数据|值)?(?:处理|填补|插补|比例)", r"multiple\s+imputation",
                   r"多重插补", r"完整(?:病例|案例分析)", r"missing\s+data"],
        "weak": [r"缺失|missing"],
        "hint": "统计阶段 3 / 9：需报告缺失比例与处理方式（完整案例分析 / 多重插补）",
    },
    "random_seed": {
        "label": "随机种子与可复现设置",
        "strong": [r"随机种子", r"random\s+seed", r"set\.?seed", r"可复现(?:性|设置)",
                   r"reproducib"],
        "weak": [r"随机|random"],
        "hint": "统计阶段 9：固定随机种子才能复现划分与建模结果",
    },
    # ---------------------------------------------------------------- 开放科学
    "open_science": {
        "label": "数据与代码可及性",
        "strong": [r"(?:数据|代码)(?:已)?(?:公开|共享|上传|存于|存放)",
                   r"(?:公共|开源)(?:仓库|数据库|平台)", r"GitHub", r"Zenodo", r"Figshare",
                   r"\bDOI\b\s*[：:]?\s*10\.", r"data\s+availability",
                   r"available\s+(?:at|from)\s+https?"],
        "weak": [r"索取|on\s+request|available\s+on\s+request", r"数据可用性"],
        "hint": ("CLEAR 53–58 / TRIPOD+AI 18："
                 "「数据可向通讯作者索取」在多数期刊已不被接受，需给仓库与 DOI"),
    },
    "reporting_checklist": {
        "label": "报告清单自查（CLEAR / TRIPOD+AI / STROBE）",
        "strong": [r"(?:CLEAR|TRIPOD|STROBE|STARD|CONSORT|CLAIM|PROBAST)\s*(?:清单|checklist|"
                   r"声明|statement|指南)?",
                   r"报告(?:清单|规范|指南)"],
        "weak": [r"清单|checklist"],
        "hint": "CLEAR 58 / TRIPOD+AI 18：需随稿提交报告清单自查表并说明存放位置",
    },
}

# 全部弱信号的判定：仅当「强信号全不命中」时才算缺失，否则记为未报告
_SEV_BY_VERDICT = {"missing": "关键", "weak": "主要", "reported": ""}


@dataclass
class SignalHit:
    signal: str
    verdict: str
    evidence: str = ""
    matched: str = ""
    note: str = ""
    para_idx: int = 0
    chapter: str = ""

    def to_dict(self) -> dict:
        return {"signal": self.signal, "verdict": self.verdict,
                "evidence": self.evidence, "matched": self.matched,
                "note": self.note, "para_idx": self.para_idx,
                "chapter": self.chapter,
                "severity": _SEV_BY_VERDICT.get(self.verdict, "")}


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.I) for p in patterns]


_COMPILED: dict[str, dict] = {}
for _name, _spec in SIGNALS.items():
    _COMPILED[_name] = {
        "strong": _compile(_spec.get("strong", [])),
        "weak": _compile(_spec.get("weak", [])),
        "label": _spec.get("label", _name),
        "hint": _spec.get("hint", ""),
        "scope": _spec.get("scope", ("methods", "results", "abstract")),
    }


def signal_names() -> list[str]:
    return list(SIGNALS.keys())


def label_of(name: str) -> str:
    return _COMPILED.get(name, {}).get("label", name)


def hint_of(name: str) -> str:
    return _COMPILED.get(name, {}).get("hint", "")


def _para_hit(patterns: list[re.Pattern], paras: list,
              radius: int = 50) -> tuple[str, str, int, str]:
    """逐段检索，返回 (命中片段, 命中的正则, 段号, 章节)。

    逐段而不是在全文中检索，是为了让证据片段一定落在**单一自然段**内 ——
    缺陷批注要挂到具体段落上，跨段片段会导致定位失准、批注挂错位置。
    """
    for p in paras:
        for pat in patterns:
            m = pat.search(p.text)
            if m:
                a = max(0, m.start() - radius // 2)
                b = min(len(p.text), m.end() + radius)
                return p.text[a:b].strip(), pat.pattern, p.idx, p.chapter
    return "", "", 0, ""


def check(manuscript, scope_chapters: tuple[str, ...] = ("abstract", "methods", "results",
                                                        "discussion", "conclusion",
                                                        "title", "data_availability",
                                                        "ethics", "funding"),
          focus: list[str] | None = None) -> list[SignalHit]:
    """对整份手稿跑确定性核验。

    Args:
        manuscript: mr_docx.Manuscript
        scope_chapters: 只在这些章节里找证据（避免在引言里"找到"方法学声明）
        focus: 只核验这些信号名（None = 全部）

    Returns:
        SignalHit 列表；verdict == "reported" 的也会返回，
        便于界面展示"已报告项"（缺陷只在 missing/weak 时生成）。
    """
    from manuscript_review.mr_review_layers import CHAPTER_TITLES   # noqa: F401
    scope_set = set(scope_chapters)
    paras = [p for p in manuscript.paragraphs if p.chapter in scope_set and p.text]
    names = focus if focus else list(SIGNALS.keys())
    hits: list[SignalHit] = []

    for name in names:
        spec = _COMPILED.get(name)
        if not spec:
            continue
        ev, matched, pidx, pchap = _para_hit(spec["strong"], paras)
        if ev:
            verdict = "reported"
        else:
            wev, wm, widx, wchap = _para_hit(spec["weak"], paras)
            if wev:
                verdict, ev, matched, pidx, pchap = "weak", wev, wm, widx, wchap
            else:
                verdict = "missing"
        hits.append(SignalHit(signal=name, verdict=verdict, evidence=ev,
                              matched=matched, note=spec["hint"],
                              para_idx=pidx, chapter=pchap))
    return hits


def summarize(hits: list[SignalHit]) -> dict:
    """统计：已报告 / 不完整 / 缺失 各多少，并按严重度分组。"""
    out = {"reported": 0, "weak": 0, "missing": 0, "total": len(hits),
           "关键": 0, "主要": 0}
    for h in hits:
        out[h.verdict] = out.get(h.verdict, 0) + 1
        sev = _SEV_BY_VERDICT.get(h.verdict, "")
        if sev in out:
            out[sev] += 1
    return out


def defects(hits: list[SignalHit]) -> list[dict]:
    """把 missing/weak 的命中转成缺陷记录（与 LLM 缺陷同构，便于合并）。"""
    out = []
    for h in hits:
        if h.verdict == "reported":
            continue
        sev = _SEV_BY_VERDICT.get(h.verdict, "主要")
        if h.verdict == "missing":
            why = (f"手稿的摘要/方法/结果等章节中检索不到「{label_of(h.signal)}」"
                   f"的任何表述。")
        else:
            why = (f"手稿只提到「{label_of(h.signal)}」的笼统说法"
                   f"（命中：{h.evidence[:60]}），未给出可复现的具体信息。")
        out.append({
            "source": "signal",
            "layer": _layer_of(h.signal),
            "req_id": f"signal:{h.signal}",
            "ref": f"确定性核验 · {label_of(h.signal)}",
            "spec": _spec_of(h.signal),
            "severity": sev,
            "verdict": "missing" if h.verdict == "missing" else "insufficient",
            "title": label_of(h.signal),
            "why": why,
            "evidence": h.evidence,
            "suggestion": hint_of(h.signal),
            "para_idx": h.para_idx,
            "chapter": h.chapter,
            "anchors": [],
            "signal": h.signal,
        })
    return out


# 信号 → 层归属（用于报告与界面着色）
_SIGNAL_LAYER = {
    "ethics_approval": "omics", "informed_consent": "omics",
    "registration_id": "omics", "data_source": "omics", "data_overlap": "omics",
    "sample_size_rationale": "omics", "event_counts": "omics",
    "inclusion_criteria": "omics", "acquisition_params": "omics",
    "contrast_phase": "omics", "reader_qualification": "omics", "icc_dice": "omics",
    "segmentation_strategy": "omics", "resampling": "omics",
    "discretization": "omics", "normalization": "omics", "ibsi": "omics",
    "feature_count": "omics", "software_version": "omics", "param_file": "omics",
    "feature_stability": "omics", "collinearity": "omics",
    "dimension_ratio": "omics", "primary_model": "omics",
    "nested_cv": "omics", "tuning": "omics", "external_validation": "omics",
    "model_update": "omics", "confidence_interval": "omics",
    "calibration": "omics", "dca": "omics", "incremental_value": "omics",
    "model_comparison": "omics", "open_science": "omics",
    "reporting_checklist": "omics",
    "primary_endpoint": "stat", "multiplicity": "stat",
    "assumption_check": "stat", "effect_size": "stat", "missing_data": "stat",
    "random_seed": "stat",
}
_SIGNAL_SPEC = {
    "acquisition_params": "CLEAR 16 · METRICS #6",
    "icc_dice": "CLEAR 19–20 · METRICS #8–#10",
    "segmentation_strategy": "CLEAR 19",
    "resampling": "CLEAR 21–22",
    "discretization": "CLEAR 23",
    "normalization": "CLEAR 24",
    "ibsi": "CLEAR 25–28 · IBSI",
    "feature_count": "CLEAR 26–27",
    "software_version": "CLEAR 25",
    "param_file": "CLEAR 28",
    "feature_stability": "METRICS #14",
    "collinearity": "METRICS #15",
    "dimension_ratio": "METRICS #16",
    "primary_model": "TRIPOD+AI 12",
    "nested_cv": "TRIPOD+AI 12b · METRICS #18",
    "tuning": "TRIPOD+AI 12c",
    "external_validation": "TRIPOD+AI 12e · METRICS #26–27",
    "model_update": "TRIPOD+AI 12f",
    "confidence_interval": "CLEAR 40 · METRICS #21",
    "calibration": "TRIPOD+AI 12d · METRICS #23",
    "dca": "CLEAR 41 · METRICS #24",
    "incremental_value": "CLEAR 42 · METRICS #25",
    "model_comparison": "CLEAR 41",
    "open_science": "CLEAR 53–58 · TRIPOD+AI 18",
    "reporting_checklist": "CLEAR 58 · TRIPOD+AI 18",
    "ethics_approval": "CLEAR 8",
    "informed_consent": "CLEAR 8",
    "registration_id": "TRIPOD+AI 18c–18d",
    "data_source": "CLEAR 13",
    "data_overlap": "CLEAR 14",
    "sample_size_rationale": "TRIPOD+AI 10",
    "event_counts": "TRIPOD+AI 21",
    "inclusion_criteria": "TRIPOD+AI 5",
    "contrast_phase": "CLEAR 16",
    "reader_qualification": "CLEAR 20 · METRICS #8",
    "primary_endpoint": "统计阶段 1",
    "multiplicity": "统计阶段 5",
    "assumption_check": "统计阶段 4",
    "effect_size": "统计阶段 6",
    "missing_data": "统计阶段 3 / 9",
    "random_seed": "统计阶段 9",
}


def _layer_of(name: str) -> str:
    return _SIGNAL_LAYER.get(name, "stat")


def _spec_of(name: str) -> str:
    return _SIGNAL_SPEC.get(name, "")


if __name__ == "__main__":
    import json
    import sys

    # 控制台按 UTF-8 输出，避免 Windows GBK 代码页在打印 CJK / 特殊符号时炸掉
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                              # noqa: BLE001
        pass

    import manuscript_review            # noqa: F401  确保包初始化（挂上仓库根路径）
    from manuscript_review import mr_docx

    ms = mr_docx.load(sys.argv[1])
    hits = check(ms)
    print(json.dumps(summarize(hits), ensure_ascii=False, indent=1))
    for d in defects(hits):
        print(f"\n[{d['severity']}] {d['layer']:5s} {d['title']} (段{d['para_idx']})")
        print("  ", d["why"])
        print("   建议：", d["suggestion"])
