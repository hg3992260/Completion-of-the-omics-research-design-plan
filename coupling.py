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

import re

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
        calc = node.get("calc") or []
        if calc:                        # 真实算过的数字也算项目素材，交给模型引用
            line += "｜本地计算结果：" + _one_line(
                "；".join(str(c.get("sentence") or c.get("text") or "") for c in calc[-3:]), 400)
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


# --------------------------------------------------------------------------- 引用解析
# 说明：模型在【各章收敛】的"来源"里，会写它引用的是**项目里真实存在的条目**
# （例如"设计工作台 01–04；统计 s1_question–s4_missing；SCI 结构 title"）。
# 下面这些函数只做一件事：把这些**引用**解析成可跳转的目标。
# 代码里依然**没有**"哪一章对应哪一阶段"的对应表 —— 对应关系由模型给出，我们只做解析。

_WORK_CTX = re.compile(r"(?:设计工作台|工作台)\s*(?:的)?\s*(?:阶段)?\s*[·:：]?\s*"
                       r"([0-9]{1,2}(?:\s*[–—~\-至到]\s*[0-9]{1,2})?"
                       r"(?:\s*[、,，和]\s*[0-9]{1,2}(?:\s*[–—~\-至到]\s*[0-9]{1,2})?)*)")
_STAGE_WORD = re.compile(r"第\s*([0-9]{1,2})\s*阶段")
_STAT_TOKEN = re.compile(r"\bs([0-9]{1,2})(?![0-9])[A-Za-z_]*", re.I)
_RANGE_SEP = re.compile(r"^[\s–—~\-至到]*$")


def _expand(spec: str) -> list:
    """把 '01–04' / '1、3' 这类写法展开成 [1,2,3,4] / [1,3]。"""
    out = []
    for part in re.split(r"[、,，和]", spec or ""):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^([0-9]{1,2})\s*[–—~\-至到]\s*([0-9]{1,2})$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            out += list(range(min(a, b), max(a, b) + 1))
        elif part.isdigit():
            out.append(int(part))
    return out


def resolve_refs(text: str, project=None) -> list:
    """把一段文字里的"引用"解析成可跳转目标（事实解析，不含任何对应关系）。

    识别三类引用：
      · 十阶段：`设计工作台 01–04`、`工作台 3`、`第 4 阶段`
      · 统计九阶段：`s3_power`、`s1_question–s4_missing`、`统计 s5`
      · SCI 七章：章节英文名（Title / Methods…）或章节 key
    返回 [{"kind": "work|stat|shape", "target": "3"/"s3_power"/"methods", "label": "…"}]。
    """
    text = text or ""
    found = []                                     # (kind, target) 保序去重

    def add(kind, target):
        if (kind, target) not in found:
            found.append((kind, target))

    for m in _WORK_CTX.finditer(text):
        for n in _expand(m.group(1)):
            if 1 <= n <= len(STAGES):
                add("work", str(n))
    for m in _STAGE_WORD.finditer(text):
        n = int(m.group(1))
        if 1 <= n <= len(STAGES):
            add("work", str(n))

    hits = [(m.start(), m.end(), int(m.group(1))) for m in _STAT_TOKEN.finditer(text)]
    for i, (s0, e0, n0) in enumerate(hits):
        if i + 1 < len(hits):
            s1, _e1, n1 = hits[i + 1]
            if _RANGE_SEP.match(text[e0:s1]) and abs(n1 - n0) > 1:
                for n in range(min(n0, n1), max(n0, n1) + 1):
                    add("stat", str(n))
                continue
        add("stat", str(n0))
    by_id = {s["id"]: s for s in stat.STAGES}
    found = [(k, t) for k, t in found if not (k == "stat") or int(t) in by_id]

    low = text.lower()
    for sec in shape.SHAPE:
        eng = " ".join(re.findall(r"[A-Za-z][A-Za-z\-]*", sec.get("title", ""))).strip().lower()
        if not eng:
            continue
        if re.search(r"\b%s\b" % re.escape(eng), low) or sec["key"] in low:
            add("shape", sec["key"])

    stats = {s["id"]: s for s in stat.STAGES}
    shapes = {s["key"]: s for s in shape.SHAPE}
    works = {s["id"]: s for s in STAGES}
    out = []
    for kind, target in sorted(found, key=lambda x: ({"work": 0, "stat": 1, "shape": 2}[x[0]],
                                                     int(x[1]) if x[1].isdigit() else x[1])):
        if kind == "work" and int(target) in works:
            s = works[int(target)]
            out.append({"kind": "work", "target": target,
                        "label": "工作台 %02d · %s" % (s["id"], s["title"])})
        elif kind == "stat" and int(target) in stats:
            s = stats[int(target)]
            out.append({"kind": "stat", "target": s["key"],
                        "label": "统计 %02d · %s" % (s["id"], s["title"])})
        elif kind == "shape" and target in shapes:
            s = shapes[target]
            out.append({"kind": "shape", "target": s["key"],
                        "label": "SCI %02d · %s" % (s["id"], s["title"])})
    return out


def chapter_links(chapter: dict, project=None) -> list:
    """一章的跳转目标 = 它自己（按章节名匹配 SCI 环节）+ 它在"来源"里引用的条目。"""
    links = resolve_refs((chapter or {}).get("sources", ""), project)
    own = resolve_refs((chapter or {}).get("title", ""), project)
    for link in own:
        if link["kind"] == "shape" and link not in links:
            links.insert(0, link)
    return links


def cited_by(project) -> dict:
    """反查：每个环节/阶段被哪些章引用（用于 scope 页显示"模型认为本环节支撑哪一章"）。

    依据同样是**模型自己写的来源引用**，不是代码里的对应表。
    """
    out = {}
    for ch in ((getattr(project, "convergence", None) or {}).get("chapters") or []):
        title = ch.get("title") or ""
        for link in chapter_links(ch, project):
            key = (link["kind"], link["target"])
            out.setdefault(key, [])
            if title and title not in out[key]:
                out[key].append(title)
    return out
