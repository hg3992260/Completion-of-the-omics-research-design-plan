# -*- coding: utf-8 -*-
"""四个页面之间的收敛关系 —— **不再在代码里硬编码**。

设计口径（2026-09 调整）：
    页面之间"哪条内容该收敛到哪一章、还缺什么、结论能不能站住"这类判断，
    全部交给 LLM 的**推理模式**（reason）在运行时给出，代码不再维护任何映射表，
    也不再用映射表去反推收敛度与缺口。

本模块因此只做两件"事实性"的事（不做任何推理）：
    1. `lane_progress()`  三条工作线各自的完成计数（纯粹的勾选/定稿统计）；
    2. `project_digest()` 把项目里**全部**已有内容整理成一份摘要，原样交给模型 ——
       模型自己判断相关性，而不是由代码替它决定"这一章该看哪几条"。
"""

from __future__ import annotations

import scope_core
import shape_data as shape
import stat_data as stat
from stages_data import STAGES

# 三条工作线（仅用于展示"各自完成到哪"，不含任何跨页对应关系）
LANES = [
    ("work", "设计工作台", "十阶段：研究设计内容与报告条目"),
    ("stat", "统计", "九阶段：分析方案的提问、定稿与自检"),
    ("shape", "SCI 结构", "七章：各章的成稿、检查项与自检"),
]


def lane_progress(project) -> list[dict]:
    """三条线各自的完成计数（事实统计，非推理）。"""
    stages = getattr(project, "stages", None) or {}
    work_done = sum(1 for s in STAGES if (stages.get(str(s["id"])) or {}).get("status") == "done")
    stat_store = getattr(project, "stat", None) or {}
    shape_store = getattr(project, "shape", None) or {}
    stat_done = sum(1 for s in stat.STAGES if scope_core.state(stat_store, s) == "done")
    shape_done = sum(1 for s in shape.SHAPE if scope_core.state(shape_store, s) == "done")
    return [
        {"key": "work", "name": "设计工作台", "done": work_done, "total": len(STAGES),
         "unit": "阶段"},
        {"key": "stat", "name": "统计", "done": stat_done, "total": len(stat.STAGES),
         "unit": "阶段"},
        {"key": "shape", "name": "SCI 结构", "done": shape_done, "total": len(shape.SHAPE),
         "unit": "章"},
    ]


def _one_line(text: str, limit: int = 240) -> str:
    t = " ".join((text or "").split())
    return t[:limit] + ("…" if len(t) > limit else "")


def project_digest(project, *, full_limit: int = 900) -> str:
    """项目的**全量内容摘要**（不做任何"该收敛到哪里"的判断）。

    含：初步设计、十阶段（状态 + 定稿/改写稿）、统计九阶段（状态 + 定稿/待采纳稿 +
    追问与回答 + 自检进度）、SCI 七章（同）。这是喂给推理模型的唯一素材。
    """
    L: list[str] = []
    raw = (getattr(project, "raw_design", "") or "").strip()
    L.append("【初步设计描述】\n" + (raw if raw else "（空）"))

    L.append("\n【设计工作台 · 十阶段】")
    stages = getattr(project, "stages", None) or {}
    for s in STAGES:
        st = stages.get(str(s["id"])) or {}
        status = st.get("status", "todo")
        body = (st.get("final") or st.get("draft") or "").strip()
        line = f"- {s['id']:02d} {s['title']}［{status}］"
        if body:
            line += "：" + _one_line(body, 300)
        qs = st.get("questions") or []
        if qs and not body:
            ans = st.get("answers") or []
            qa = "；".join(f"{_one_line(str(q.get('q') if isinstance(q, dict) else q), 60)}"
                           f"→{_one_line(str(ans[i]) if i < len(ans) else '', 60)}"
                           for i, q in enumerate(qs[:3]))
            line += "｜追问：" + qa
        L.append(line)

    L.append("\n【统计 · 九阶段】")
    stat_store = getattr(project, "stat", None) or {}
    for s in stat.STAGES:
        node = stat_store.get(s["key"]) or {}
        d, t = scope_core.progress(stat_store, s)
        gst = scope_core.guide_status(stat_store, s["key"])
        body = (node.get("final") or node.get("draft") or "").strip()
        line = f"- {s['id']:02d} {s['title']}［{gst}，自检 {d}/{t}］"
        if body:
            line += "：" + _one_line(body, 300)
        elif node.get("questions"):
            ans = node.get("answers") or []
            qa = "；".join(f"{_one_line(str(q.get('q') if isinstance(q, dict) else q), 60)}"
                           f"→{_one_line(str(ans[i]) if i < len(ans) else '', 60)}"
                           for i, q in enumerate(node["questions"][:3]))
            line += "｜追问：" + qa
        L.append(line)

    L.append("\n【SCI 结构 · 七章】")
    shape_store = getattr(project, "shape", None) or {}
    for s in shape.SHAPE:
        node = shape_store.get(s["key"]) or {}
        d, t = scope_core.progress(shape_store, s)
        gst = scope_core.guide_status(shape_store, s["key"])
        body = (node.get("final") or node.get("draft") or "").strip()
        line = f"- {s['id']:02d} {s['title']}［{gst}，自检 {d}/{t}］"
        if body:
            line += "：" + _one_line(body, 300)
        L.append(line)

    final = (getattr(project, "final_doc", "") or "").strip()
    if final:
        L.append("\n【已生成的完整草案（节选）】\n" + _one_line(final, full_limit))
    return "\n".join(L)


def digest_stats(project) -> dict:
    """摘要里各部分的条目数，用于界面提示"素材有多少"（事实统计）。"""
    stat_store = getattr(project, "stat", None) or {}
    shape_store = getattr(project, "shape", None) or {}
    with_final = sum(1 for s in stat.STAGES
                     if (stat_store.get(s["key"]) or {}).get("final"))
    with_final += sum(1 for s in shape.SHAPE
                      if (shape_store.get(s["key"]) or {}).get("final"))
    return {
        "work_final": sum(1 for s in STAGES
                          if ((getattr(project, "stages", None) or {})
                              .get(str(s["id"])) or {}).get("final")),
        "stat_final": sum(1 for s in stat.STAGES
                          if (stat_store.get(s["key"]) or {}).get("final")),
        "shape_final": sum(1 for s in shape.SHAPE
                           if (shape_store.get(s["key"]) or {}).get("final")),
        "scope_final": with_final,
    }
