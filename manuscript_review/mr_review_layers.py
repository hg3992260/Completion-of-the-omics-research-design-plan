# -*- coding: utf-8 -*-
"""手稿审阅 · 三层架构数据。

不新增任何规范内容：三层的审阅条目全部**派生自工作台已有的权威数据**，
保证「引导式组学 / 统计 / 撰写」三套架构与审阅口径永远同源、不会分叉。

    组学层  omics    ← stages_data.STAGES（十阶段：TRIPOD+AI / CLEAR / METRICS / IBSI）
    统计层  stat     ← stat_data.STAGES（9 阶段）与 stat_data.CHEATSHEET
    撰写层  shape    ← shape_data.SHAPE（Glasman-Deal 七章通用模型）

一条 requirement（审阅条目）就是一次「对照检查」：

    {
      "layer":     "omics" | "stat" | "shape",
      "req_id":    "omics:S4:R3"          全局唯一，用于回写与去重
      "ref":       "组学阶段 4 图像采集与质控"
      "spec":      "CLEAR 16 · METRICS #6"  规范出处（写进批注）
      "kind":      "reports" | "pitfall" | "check" | "must" | "must_not"
      "text":      "全部采集与重建参数"      要对照的那一条
      "anchors":   ["methods", "results"]  手稿中应出现该内容的章节 key
      "severity":  "关键" | "主要" | "一般"
      "signal":    "..."                   可确定性核验的信号名（无则 None）
    }

severity 判定口径（避免主观）：
    关键  —— 规范强制项，缺失即无法复现 / 无法通过同行评议
             （组学 reports、TRIPOD+AI 与 CLEAR 的必报项、统计 assumptions/pitfalls）
    主要  —— 规范推荐项，缺失会被审稿人质疑
    一般  —— 写作规范与语体问题（时态、内容边界、措辞强度）
"""

from __future__ import annotations

import stat_data
import stages_data
from shape_data import SHAPE

# --------------------------------------------------------------------------- 层元数据
LAYERS = {
    "omics": {
        "key": "omics",
        "name": "引导式组学",
        "sub": "十阶段 · TRIPOD+AI / CLEAR / METRICS / IBSI",
        "color": "#58a6ff",
        "icon": "🧬",
        "sections": ["methods", "results", "discussion"],
        "why": "组学流程的每一步都决定特征值与可复现性，缺失即无法被第三方重建。",
    },
    "stat": {
        "key": "stat",
        "name": "统计",
        "sub": "9 阶段 · SAP / 前提诊断 / 多重比较 / 报告规范",
        "color": "#a371f7",
        "icon": "📊",
        "sections": ["methods", "results", "discussion"],
        "why": "统计缺陷不会让文章写不下去，但会让结论站不住。",
    },
    "shape": {
        "key": "shape",
        "name": "撰写",
        "sub": "Glasman-Deal 七章通用模型 · 时态与内容边界",
        "color": "#3fb950",
        "icon": "✍️",
        "sections": ["title", "abstract", "introduction", "methods",
                     "results", "discussion", "conclusion"],
        "why": "结构、时态与内容边界是审稿人第一眼看到的东西。",
    },
}

LAYER_ORDER = ["omics", "stat", "shape"]

# 组学十阶段中，属于「报告与治理」而与手稿正文段落无关的阶段也照样审 ——
# 因为它们的 reports 正是手稿里必须出现的那几句话。
_OMICS_SEVERITY = {
    "reports": "关键",     # 必报参数：缺了就不可复现
    "pitfall": "关键",     # 常见缺陷：命中即硬伤
}

_STAT_SEVERITY = {
    "pitfall": "关键",
    "check": "主要",
}

_SHAPE_SEVERITY = {
    "must": "主要",
    "must_not": "主要",
    "check": "一般",       # 写作层检查项多为语体与结构，属一般
}


def _sig(text: str) -> str:
    """按条目文本推断可以确定性核验的信号名。

    这里只做「关键词 → 信号名」的粗映射，真正的判定逻辑在 mr_signals.py。
    映射不到就返回空串，该条目交给 LLM 语义审阅。
    """
    t = text or ""
    table = (
        (("伦理批号", "伦理批准", "伦理审批"), "ethics_approval"),
        (("知情同意", "同意方式"), "informed_consent"),
        (("注册号", "注册"), "registration_id"),
        (("数据来源",), "data_source"),
        (("数据重叠", "重叠"), "data_overlap"),
        (("样本量依据", "样本量如何", "样本量及其由来", "功效"), "sample_size_rationale"),
        (("事件数", "例数"), "event_counts"),
        (("机型", "管电压", "管电流", "层厚", "重建算法", "卷积核",
          "采集与重建参数", "全部采集"), "acquisition_params"),
        (("对比剂", "期相"), "contrast_phase"),
        (("勾画者资质", "勾画者"), "reader_qualification"),
        (("ICC", "Dice", "一致性"), "icc_dice"),
        (("重采样", "体素间距"), "resampling"),
        (("binWidth", "离散化", "灰度离散"), "discretization"),
        (("归一化",), "normalization"),
        (("IBSI",), "ibsi"),
        (("特征类别与数量", "特征数量", "特征类别"), "feature_count"),
        (("参数文件", "完整参数文件", "YAML"), "param_file"),
        (("稳定性", "稳健"), "feature_stability"),
        (("共线性", "冗余特征", "相关"), "collinearity"),
        (("维度", "特征数与样本量"), "dimension_ratio"),
        (("交叉验证", "嵌套"), "nested_cv"),
        (("调参",), "tuning"),
        (("外部验证", "独立中心", "外部集"), "external_validation"),
        (("主模型",), "primary_model"),
        (("校准",), "calibration"),
        (("决策曲线", "DCA", "净获益"), "dca"),
        (("NRI", "IDI", "增量价值"), "incremental_value"),
        (("置信区间", "95%CI", "95% CI"), "confidence_interval"),
        (("统计比较", "DeLong"), "model_comparison"),
        (("软件及版本", "软件与版本", "版本"), "software_version"),
        (("随机种子", "seed"), "random_seed"),
        (("数据、代码", "可及性", "共享", "公开", "索取"), "open_science"),
        (("报告清单", "清单"), "reporting_checklist"),
        (("入排标准",), "inclusion_criteria"),
        (("缺失", "剔除"), "missing_data"),
        (("多重比较", "校正"), "multiplicity"),
        (("前提", "正态", "方差齐"), "assumption_check"),
        (("效应量",), "effect_size"),
        (("主要结局",), "primary_endpoint"),
        (("主要/", "主要结局唯一"), "primary_endpoint"),
    )
    for keys, name in table:
        if any(k.lower() in t.lower() for k in keys):
            return name
    return ""


def _req(layer, req_id, ref, spec, kind, text, anchors, severity_out):
    return {"layer": layer, "req_id": req_id, "ref": ref, "spec": spec,
            "kind": kind, "text": text, "anchors": anchors,
            "severity": severity_out, "signal": _sig(text)}


def build_requirements() -> list[dict]:
    """把三层规范数据摊平成审阅条目列表。每次调用重新派生，保证与源数据同步。"""
    out: list[dict] = []

    # ---------------------------------------------------------------- 组学层
    for st in stages_data.STAGES:
        ref = f"组学阶段 {st['id']} {st['title']}"
        spec = st.get("spec", "")
        for i, t in enumerate(st.get("reports", []), 1):
            out.append(_req("omics", f"omics:S{st['id']}:R{i}", ref, spec,
                            "reports", t, ["methods", "results"],
                            _OMICS_SEVERITY["reports"]))
        for i, t in enumerate(st.get("pitfalls", []), 1):
            out.append(_req("omics", f"omics:S{st['id']}:P{i}", ref, spec,
                            "pitfall", t, ["methods", "results", "discussion"],
                            _OMICS_SEVERITY["pitfall"]))
        for i, t in enumerate(st.get("actions", []), 1):
            out.append(_req("omics", f"omics:S{st['id']}:A{i}", ref, spec,
                            "action", t, ["methods"], "主要"))

    # ---------------------------------------------------------------- 统计层
    for st in stat_data.STAGES:
        ref = f"统计阶段 {st['id']} {st['title']}"
        spec = st.get("spec", "")
        for i, t in enumerate(st.get("pitfalls", []), 1):
            out.append(_req("stat", f"stat:S{st['id']}:P{i}", ref, spec,
                            "pitfall", t, ["methods", "results", "discussion"],
                            _STAT_SEVERITY["pitfall"]))
        for i, t in enumerate(st.get("checks", []), 1):
            out.append(_req("stat", f"stat:S{st['id']}:C{i}", ref, spec,
                            "check", t, ["methods", "results", "discussion"],
                            _STAT_SEVERITY["check"]))
        for i, t in enumerate(st.get("goal", []), 1):
            out.append(_req("stat", f"stat:S{st['id']}:G{i}", ref, spec,
                            "goal", t, ["methods"], "主要"))

    # ---------------------------------------------------------------- 撰写层
    for ch in SHAPE:
        ref = f"写作章节 {ch['id']} {ch['title']}"
        spec = ch.get("spec", "")
        key = ch["key"]
        for i, t in enumerate(ch.get("must", []), 1):
            out.append(_req("shape", f"shape:{key}:M{i}", ref, spec,
                            "must", t, [key], _SHAPE_SEVERITY["must"]))
        for i, t in enumerate(ch.get("must_not", []), 1):
            out.append(_req("shape", f"shape:{key}:N{i}", ref, spec,
                            "must_not", t, [key], _SHAPE_SEVERITY["must_not"]))
        for i, t in enumerate(ch.get("checks", []), 1):
            out.append(_req("shape", f"shape:{key}:C{i}", ref, spec,
                            "check", t, [key], _SHAPE_SEVERITY["check"]))

    return out


REQUIREMENTS: list[dict] = build_requirements()


def by_layer(layer: str) -> list[dict]:
    return [r for r in REQUIREMENTS if r["layer"] == layer]


def by_id(req_id: str) -> dict | None:
    for r in REQUIREMENTS:
        if r["req_id"] == req_id:
            return r
    return None


def stats() -> dict:
    """三层条目数概览（界面与 MCP 都用它保持一致）。"""
    out = {}
    for k in LAYER_ORDER:
        rows = by_layer(k)
        out[k] = {
            "name": LAYERS[k]["name"], "sub": LAYERS[k]["sub"],
            "total": len(rows),
            "关键": sum(1 for r in rows if r["severity"] == "关键"),
            "主要": sum(1 for r in rows if r["severity"] == "主要"),
            "一般": sum(1 for r in rows if r["severity"] == "一般"),
            "with_signal": sum(1 for r in rows if r["signal"]),
        }
    out["total"] = len(REQUIREMENTS)
    return out


# 严重度排序（报告里按此降序）
SEVERITY_RANK = {"关键": 0, "主要": 1, "一般": 2}

# 手稿章节 key → 中文名（结构识别与报告共用）
CHAPTER_TITLES = {
    "title": "标题", "abstract": "摘要", "keywords": "关键词",
    "introduction": "引言", "methods": "方法", "results": "结果",
    "discussion": "讨论", "conclusion": "结论",
    "references": "参考文献", "acknowledgements": "致谢",
    "funding": "基金", "coi": "利益冲突", "data_availability": "数据可用性",
    "ethics": "伦理声明", "supplementary": "补充材料", "other": "其他",
}

if __name__ == "__main__":
    import json
    print(json.dumps(stats(), ensure_ascii=False, indent=1))
