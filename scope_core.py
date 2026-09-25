# -*- coding: utf-8 -*-
"""scope 页共用的纯数据逻辑（SCI Shape / Statistic 两页通用）。

一个「scope 数据集」是一组环节（环节 = 章节或统计阶段），每个环节至少含：
    id / key / title / spec / checks
自评记录存在项目的某个字段里（shape 或 stat）：
    {"<环节 key>": {"checks": {"0": true, ...}}}
"""

from __future__ import annotations

STATUS_LABEL = {"todo": "未开始", "doing": "进行中", "done": "已完成",
                "asked": "已追问", "drafted": "待采纳", "final": "已定稿"}

GUIDE_STATUS = {"todo": "未开始引导", "asked": "已追问 · 待回答",
                "drafted": "已生成定稿 · 待采纳", "done": "已定稿收录"}


def blank_scope_state() -> dict:
    """一个环节的完整状态：自检勾选 + 引导式对话（追问/回答/定稿/采纳）+ 真实计算记录。"""
    return {"checks": {}, "status": "todo", "assessment": "", "questions": [],
            "answers": [], "draft": "", "final": "", "risks": "", "suggested": [],
            "calc": [], "model": "", "updated": ""}


def node(store: dict, key: str) -> dict:
    """取出（必要时初始化）某环节的状态；旧项目只有 checks，这里补齐其余字段。"""
    d = store.setdefault(key, {})
    for k, v in blank_scope_state().items():
        d.setdefault(k, {} if k == "checks" else ([] if k in ("questions", "answers",
                                                              "suggested", "calc") else v))
    return d


def guide_status(store: dict, key: str) -> str:
    """引导状态：todo / asked / drafted / done。"""
    d = (store or {}).get(key) or {}
    st = d.get("status") or "todo"
    if d.get("final"):
        return "done"
    if d.get("draft"):
        return "drafted"
    if d.get("questions"):
        return "asked"
    return "todo"


def has_content(store: dict, key: str) -> bool:
    d = (store or {}).get(key) or {}
    return bool((d.get("final") or d.get("draft") or "").strip())


def parse_suggestions(block: str, checks: list) -> list[tuple[int, bool]]:
    """把模型的【检查表】解析成 (序号, 是否满足)。

    支持三种写法（按优先级）：
        1. `- [x] 3`            → 直接按编号
        2. `- [x] 3. 条目文本`   → 取编号
        3. `- [x] 条目文本`      → 与自检清单做文本匹配（完全/包含/相似度）
    """
    import difflib
    import re

    out: list[tuple[int, bool]] = []
    for raw in (block or "").splitlines():
        line = raw.strip()
        m = re.match(r"^[-*•]?\s*\[( |x|X)\]\s*(.*)$", line)
        if not m:
            continue
        ok = m.group(1).lower() == "x"
        body = m.group(2).strip()
        idx = None
        m2 = re.match(r"^(\d{1,2})\b", body)
        if m2 and 1 <= int(m2.group(1)) <= len(checks):
            idx = int(m2.group(1)) - 1
        if idx is None and body:
            want = re.sub(r"[\s　·、,，。.;；:：()（）\-—]+", "", body).lower()
            best, score = None, 0.0
            for i, c in enumerate(checks):
                have = re.sub(r"[\s　·、,，。.;；:：()（）\-—]+", "", str(c)).lower()
                if not have:
                    continue
                if want == have or want in have or have in want:
                    s = 0.95
                else:
                    s = difflib.SequenceMatcher(None, want, have).ratio()
                if s > score:
                    best, score = i, s
            if best is not None and score >= 0.6:
                idx = best
        if idx is not None:
            out.append((idx, ok))
    return out


def checked(store: dict, key: str) -> dict:
    """某环节的勾选记录 {索引字符串: True}。"""
    return ((store or {}).get(key) or {}).get("checks") or {}


def progress(store: dict, sec: dict) -> tuple[int, int]:
    """返回 (已勾选数, 总检查项数)。"""
    got = checked(store, sec["key"])
    total = len(sec["checks"])
    return sum(1 for i in range(total) if got.get(str(i))), total


def state(store: dict, sec: dict) -> str:
    """环节状态：done / doing / todo。

    判定依据（纯事实，不涉及任何跨页映射）：
      · done  —— 已有定稿（final / status=done），或自检项全部勾选；
      · doing —— 有自检勾选、或已产生追问（对话进行中）；
      · todo  —— 其余。
    """
    d = (store or {}).get(sec["key"]) or {}
    if (d.get("final") or "").strip() or d.get("status") == "done":
        return "done"
    got, total = progress(store, sec)
    if total and got >= total:
        return "done"
    if got or d.get("questions") or (d.get("draft") or "").strip():
        return "doing"
    return "todo"


def overall(store: dict, data: list) -> tuple[int, int, int]:
    """汇总：返回 (已完成环节数, 进行中环节数, 已勾选自检项数)。"""
    done = doing = ticks = 0
    for sec in data:
        st = state(store, sec)
        done += st == "done"
        doing += st == "doing"
        ticks += progress(store, sec)[0]
    return done, doing, ticks


def total_checks(data: list) -> int:
    return sum(len(s["checks"]) for s in data)


def set_check(store: dict, key: str, idx: int, on: bool) -> dict:
    """写勾选状态（True 记入，False 移除）。返回更新后的 checks。"""
    node = store.setdefault(key, {})
    checks = node.setdefault("checks", {})
    if on:
        checks[str(idx)] = True
    else:
        checks.pop(str(idx), None)
    return checks


def set_all(store: dict, sec: dict, on: bool) -> dict:
    store.setdefault(sec["key"], {})["checks"] = (
        {str(i): True for i in range(len(sec["checks"]))} if on else {})
    return store[sec["key"]]["checks"]
