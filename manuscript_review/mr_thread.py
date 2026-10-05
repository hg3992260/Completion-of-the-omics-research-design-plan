# -*- coding: utf-8 -*-
"""把审阅发现并入「审稿批注版」手稿 —— 作为**线程回复**挂在审稿意见下面。

关键结论（已用 Word COM 的 `Comment.Ancestor` 权威验证）
-----------------------------------------------------
**OfficeCLI 的 `parentId` 是够用的**，它会同时做两件事：
    1. `commentsExtended.xml` 写 `<w15:commentEx w15:paraIdParent="父批注段落paraId"/>`
    2. `document.xml` 自动把回复的 commentRange 标记**包在父批注外面**
       （Start(回复) > Start(父) … End(父) > End(回复)）

Word 读到的 `Ancestor` 正确指向原审稿批注。所以：
    · 不需要照搬 `reviewer-reply-docx` 的 inject_replies.py 手工插标记；
    · 该技能文档也明确说「OfficeCLI 的 parentId 不会原生嵌套」——
      那是 1.0.143 的旧行为，**1.0.153 已经修好**。

本模块因此只做三件必要的事：
    ① 读出手稿里已有的审稿批注（含它锚定在哪一段）
    ② 用可解释的规则，把我们的发现匹配到最相关的审稿意见上
    ③ 校验线程是否真的成立（4 项检查，含 Word 可读性口径）
"""

from __future__ import annotations

import os
import re
import zipfile
from dataclasses import dataclass, field

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_W15 = "http://schemas.microsoft.com/office/word/2012/wordml"


@dataclass
class ExistingComment:
    """审稿批注版里已有的一条批注。"""
    cid: int
    author: str = ""
    initials: str = ""
    text: str = ""
    para_idx: int = 0          # 锚定的段号（0 = 没解析出来）
    para_para_id: str = ""     # 锚定段落的 w14:paraId
    parent_cid: int = 0        # 若本身就是某条批注的回复

    def to_dict(self) -> dict:
        return {"id": self.cid, "author": self.author, "para": self.para_idx,
                "text": self.text[:90], "parent": self.parent_cid or None}


@dataclass
class ReplyPlan:
    parent_cid: int
    finding: dict
    score: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict:
        return {"parent": self.parent_cid, "title": self.finding.get("title"),
                "req_id": self.finding.get("req_id"),
                "severity": self.finding.get("severity"),
                "score": round(self.score, 2), "reason": self.reason}


@dataclass
class MergePlan:
    replies: list = field(default_factory=list)
    standalone: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"replies": [r.to_dict() for r in self.replies],
                "replies_count": len(self.replies),
                "standalone": len(self.standalone),
                "parents_used": sorted({r.parent_cid for r in self.replies}),
                "notes": list(self.notes)}


# --------------------------------------------------------------------------- 读取
def _text_of(xml_frag: str) -> str:
    """把批注正文里的 <w:t> 与 <w:br/> 还原成可读文本。"""
    s = re.sub(r"<w:br\s*/>", "\n", xml_frag)
    parts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", s)
    return "".join(parts)


def _para_id_at(doc_xml: str, pos: int) -> str:
    """pos 所在 <w:p> 的 w14:paraId。"""
    cands = [doc_xml.rfind("<w:p ", 0, pos), doc_xml.rfind("<w:p>", 0, pos)]
    start = max(cands)
    if start < 0:
        return ""
    m = re.search(r'w14:paraId="([0-9A-Fa-f]+)"', doc_xml[start:start + 500])
    return m.group(1) if m else ""


def _para_index_at(doc_xml: str, pos: int) -> int:
    """pos 在第几个 <w:p> 里（1-based）。

    这是**唯一可靠的段号来源**：它与 OfficeCLI 的 ``/body/p[N]`` 是同一套编号，
    不依赖 w14:paraId。
    为什么不能只靠 paraId：用 python-docx 生成的 .docx 根本没有 paraId，
    而 OfficeCLI 写入批注时会顺手给段落补上 paraId —— 两边的 paraId 体系对不上，
    必须按 body 里的出现顺序数。
    """
    body_start = doc_xml.find("<w:body")
    if body_start < 0:
        return 0
    n = 0
    for m in re.finditer(r"<w:p(?=[\s/>])", doc_xml):
        if m.start() >= pos:
            break
        if m.start() > body_start:
            n += 1
    return n


def read_existing(docx_path: str) -> list[ExistingComment]:
    """读出手稿里已有的批注（审稿意见），含锚定段号。"""
    if not docx_path or not os.path.exists(docx_path):
        return []
    z = zipfile.ZipFile(docx_path)
    try:
        names = z.namelist()
        if "word/comments.xml" not in names:
            return []
        cm = z.read("word/comments.xml").decode("utf-8", "replace")
        doc = z.read("word/document.xml").decode("utf-8", "replace")
        ext = (z.read("word/commentsExtended.xml").decode("utf-8", "replace")
               if "word/commentsExtended.xml" in names else "")
    finally:
        z.close()

    # paraId → 父 paraId（判断已有回复链）
    parent_of_pid = {}
    for m in re.finditer(r'<w15:commentEx\b([^>]*)/>', ext):
        a = m.group(1)
        pid = re.search(r'w15:paraId="([0-9A-Fa-f]+)"', a)
        ppid = re.search(r'w15:paraIdParent="([0-9A-Fa-f]+)"', a)
        if pid and ppid:
            parent_of_pid[pid.group(1)] = ppid.group(1)

    out: list[ExistingComment] = []
    pid_to_cid: dict[str, int] = {}
    for m in re.finditer(r"<w:comment\b([^>]*)>(.*?)</w:comment>", cm, re.S):
        attrs, body = m.group(1), m.group(2)
        mid = re.search(r'w:id="(-?\d+)"', attrs)
        if not mid:
            continue
        am = re.search(r'w:author="([^"]*)"', attrs)
        im = re.search(r'w:initials="([^"]*)"', attrs)
        c = ExistingComment(cid=int(mid.group(1)),
                            author=am.group(1) if am else "",
                            initials=im.group(1) if im else "",
                            text=_text_of(body))
        pm = re.search(r'w14:paraId="([0-9A-Fa-f]+)"', body)
        if pm:
            c.para_para_id = pm.group(1)
            pid_to_cid[c.para_para_id] = c.cid
        # 段号：优先按 commentRangeStart 在 body 中的位置数段落
        sm = re.search(r'<w:commentRangeStart[^>]*w:id="%d"[^>]*/>' % c.cid, doc)
        if sm:
            c.para_idx = _para_index_at(doc, sm.start())
            if not c.para_para_id:
                c.para_para_id = _para_id_at(doc, sm.start())
        out.append(c)

    # 已有回复链
    for c in out:
        ppid = parent_of_pid.get(c.para_para_id)
        if ppid and ppid in pid_to_cid:
            c.parent_cid = pid_to_cid[ppid]
    out.sort(key=lambda x: x.cid)
    return out


def _para_id_to_idx(manuscript) -> dict:
    return {p.para_id: p.idx for p in manuscript.paragraphs if p.para_id}


def probe(docx_path: str) -> dict:
    """探测一份手稿是否带审稿批注 —— 界面据此决定是否给出「并入」选项。"""
    info = {"path": os.path.abspath(docx_path) if docx_path else "",
            "has_comments": False, "count": 0, "authors": [], "comments": []}
    if not docx_path or not os.path.exists(docx_path):
        return info
    cs = read_existing(docx_path)
    info["has_comments"] = bool(cs)
    info["count"] = len(cs)
    info["authors"] = sorted({c.author for c in cs if c.author})
    info["comments"] = [c.to_dict() for c in cs[:40]]
    return info


# --------------------------------------------------------------------------- 匹配
# 主题词分两档 —— 这个区分很关键：
#   强词：一个字就能说明在谈同一件事（ICC / 校准 / 层厚 / 主模型 …）
#   弱词：太泛，单独命中不代表相关（"参数""特征""模型""数据""验证" …）
# 教训：把泛词当强词用会闹出「伦理批号」被挂到「扫描参数」下面这种乌龙
# （两者都含"参数"）。所以弱词必须**成对**才计分，且主题同类只作加成。
_STRONG_WORDS = (
    "icc", "dice", "一致性", "重复勾画", "勾画", "分割", "重采样", "binwidth",
    "离散化", "归一化", "ibsi", "稳定性", "共线", "冗余", "维度", "样本量",
    "事件数", "epv", "功效", "校准", "dca", "决策曲线", "净获益", "nri",
    "idi", "增量", "置信区间", "auc", "delong", "外部验证", "重叠", "lasso",
    "主模型", "调参", "嵌套", "交叉验证", "泄露", "泄漏", "伦理", "知情同意",
    "注册", "层厚", "管电压", "kvp", "管电流", "重建", "卷积核", "机型",
    "对比剂", "期相", "过拟合", "偏倚", "偏性", "随机森林", "xgboost",
    "摘要", "标题", "时态", "因果",
)
_WEAK_WORDS = (
    "参数", "特征", "模型", "数据", "验证", "训练集", "验证集", "扫描",
    "软件", "版本", "代码", "共享", "公开", "结论", "讨论", "引言", "局限",
    "预测", "偏", "svm",
)
_TOPIC_WORDS = _STRONG_WORDS + _WEAK_WORDS
_LAYER_WORDS = {
    "omics": {"层厚", "管电压", "kvp", "管电流", "重建", "卷积核", "机型",
              "扫描", "对比剂", "期相", "勾画", "分割", "icc", "dice",
              "重采样", "binwidth", "离散化", "归一化", "ibsi", "特征",
              "稳定性", "共线", "冗余", "维度", "参数", "软件", "版本"},
    "stat": {"样本量", "事件数", "epv", "功效", "校准", "dca", "决策曲线",
             "净获益", "nri", "idi", "增量", "置信区间", "auc", "delong",
             "外部验证", "验证集", "训练集", "重叠", "模型", "lasso",
             "主模型", "调参", "嵌套", "交叉验证", "泄露", "泄漏",
             "过拟合", "预测"},
    "shape": {"摘要", "结论", "讨论", "引言", "标题", "时态", "因果",
              "局限", "偏倚", "偏性"},
}


def _strong(text: str) -> set:
    low = (text or "").lower()
    return {w for w in _STRONG_WORDS if w in low}


def _weak(text: str) -> set:
    low = (text or "").lower()
    return {w for w in _WEAK_WORDS if w in low}


def _words(text: str) -> set:
    """兼容旧用法：任意命中（强+弱）。"""
    return _strong(text) | _weak(text)


def score_pair(finding: dict, comment: ExistingComment, fpara: int) -> tuple[float, str]:
    """给「一条发现 × 一条审稿意见」打分。规则可解释，不做语义猜测。

    计分口径（防止泛词误挂靠）：
        同段落         +3.0   最强证据（还在 Word 里天然成链）
        相邻段落       +1.2
        强词命中       +0.9/个（上限 2.7）
        弱词命中       +0.25/个（且必须≥2 个才计分）
        主题同类加成   +0.5（仅当已有词命中时才加，避免"只靠主题"挂靠）
    """
    score, why = 0.0, []
    if fpara and comment.para_idx and fpara == comment.para_idx:
        score += 3.0
        why.append("同段落")
    elif fpara and comment.para_idx and abs(fpara - comment.para_idx) <= 2:
        score += 1.2
        why.append("相邻段落")

    ft = " ".join(str(finding.get(k) or "") for k in
                  ("title", "why", "suggestion", "ref", "spec"))
    st = _strong(ft) & _strong(comment.text)
    wk = _weak(ft) & _weak(comment.text)
    if st:
        score += min(2.7, 0.9 * len(st))
        why.append("强词 " + "/".join(sorted(st)[:4]))
    if len(wk) >= 2:
        score += min(0.75, 0.25 * len(wk))
        why.append("弱词 " + "/".join(sorted(wk)[:3]))

    if (st or len(wk) >= 2) and \
            (_LAYER_WORDS.get(finding.get("layer") or "", set()) & _words(comment.text)):
        score += 0.5
        why.append("主题同类")
    return score, "；".join(why)


def build_merge_plan(findings: list[dict], comments: list[ExistingComment],
                     manuscript=None, per_parent: int = 4,
                     min_score: float = 0.8) -> MergePlan:
    """把发现分配到审稿意见下；匹配不上的转为独立批注（不丢信息）。

    min_score 为什么定 0.8：实测（Word COM）**同一段落的多条批注 Word 会自动
    串成一条线程**，所以「同章节 + 主题同类」这种 0.8 分的弱匹配也值得挂靠 ——
    挂上去比留在外面更符合审稿人「就这条意见，作者补充了什么」的阅读习惯。
    只有连主题都对不上（0 分）的才作为独立批注。
    """
    plan = MergePlan()
    if not comments:
        plan.standalone = list(findings)
        plan.notes.append("目标稿件没有审稿批注：全部作为独立批注写入。")
        return plan

    # 补全审稿批注的段号
    if manuscript is not None:
        pid2idx = _para_id_to_idx(manuscript)
        for c in comments:
            if not c.para_idx and c.para_para_id:
                c.para_idx = pid2idx.get(c.para_para_id, 0)
        for c in comments:
            if not c.para_idx and c.text:
                p = manuscript.find_paragraph(c.text[:24])
                if p:
                    c.para_idx = p.idx

    # 已有回复的批注不再接收新回复（避免把回复挂到回复上造成多层混乱）
    roots = [c for c in comments if not c.parent_cid] or comments
    used: dict[int, int] = {}
    for f in findings:
        fpara = f.get("para_idx") or 0
        best, best_score, best_why = None, 0.0, ""
        for c in roots:
            if used.get(c.cid, 0) >= per_parent:
                continue
            s, why = score_pair(f, c, fpara)
            if s > best_score:
                best, best_score, best_why = c, s, why
        if best is not None and best_score >= min_score:
            used[best.cid] = used.get(best.cid, 0) + 1
            plan.replies.append(ReplyPlan(best.cid, f, best_score, best_why))
        else:
            plan.standalone.append(f)
    if plan.standalone:
        plan.notes.append(
            f"{len(plan.standalone)} 条发现与审稿意见匹配度不足（阈值 {min_score}），"
            f"作为独立批注写在原段落。")
    return plan


# --------------------------------------------------------------------------- 回复文本
def reply_text(finding: dict, prefix: str = "【审阅补充】") -> str:
    """把发现写成适合做「回复」的批注文本（比独立批注短，聚焦要点）。"""
    from manuscript_review.mr_review_layers import LAYERS
    from manuscript_review.mr_word import SEV_MARK, plain
    layer = LAYERS.get(finding.get("layer") or "", {}).get(
        "name", finding.get("layer") or "")
    sev = finding.get("severity") or "主要"
    head = f"{prefix}{layer}·{SEV_MARK.get(sev, sev)}"
    if finding.get("spec"):
        head += f"（{finding['spec']}）"
    parts = [head]
    if finding.get("title"):
        parts.append("缺陷：" + plain(finding["title"]))
    if finding.get("why"):
        parts.append(plain(finding["why"])[:150])
    if finding.get("suggestion"):
        parts.append("建议：" + plain(finding["suggestion"])[:220])
    return "\n".join(x for x in parts if x)


# --------------------------------------------------------------------------- 校验
def verify_threading(docx_path: str) -> dict:
    """4 项线程校验：标记配平 / parentId 有效 / 嵌套区间合法 / 线程完整。"""
    out = {"ok": False, "problems": [], "markers": {}, "total_comments": 0,
           "roots": 0, "replies": 0, "nested_ok": 0, "nested_bad": 0}
    if not docx_path or not os.path.exists(docx_path):
        out["problems"].append("文件不存在")
        return out
    z = zipfile.ZipFile(docx_path)
    try:
        names = z.namelist()
        if "word/document.xml" not in names:
            out["problems"].append("缺少 document.xml")
            return out
        doc = z.read("word/document.xml").decode("utf-8", "replace")
        cm = (z.read("word/comments.xml").decode("utf-8", "replace")
              if "word/comments.xml" in names else "")
        ext = (z.read("word/commentsExtended.xml").decode("utf-8", "replace")
               if "word/commentsExtended.xml" in names else "")
    finally:
        z.close()

    for tag, key in (("commentRangeStart", "start"), ("commentRangeEnd", "end"),
                     ("commentReference", "ref")):
        out["markers"][key] = len(re.findall(rf"<w:{tag}\b", doc))
    out["total_comments"] = len(re.findall(r"<w:comment\b", cm))
    m = out["markers"]
    if not (m["start"] == m["end"] == m["ref"]):
        out["problems"].append(
            f"标记不配平：start={m['start']} end={m['end']} ref={m['ref']}")
    if out["total_comments"] and m["start"] != out["total_comments"]:
        out["problems"].append(
            f"评论部件 {out['total_comments']} 条，但正文有 {m['start']} 个 Start")

    # paraId → cid，再解析 parent 链
    pid2cid, cid2pid = {}, {}
    for mm in re.finditer(r"<w:comment\b([^>]*)>(.*?)</w:comment>", cm, re.S):
        cid = re.search(r'w:id="(-?\d+)"', mm.group(1))
        pid = re.search(r'w14:paraId="([0-9A-Fa-f]+)"', mm.group(2))
        if cid and pid:
            pid2cid[pid.group(1)] = int(cid.group(1))
            cid2pid[int(cid.group(1))] = pid.group(1)

    parents: dict[int, int] = {}
    for mm in re.finditer(r'<w15:commentEx\b([^>]*)/>', ext):
        a = mm.group(1)
        pid = re.search(r'w15:paraId="([0-9A-Fa-f]+)"', a)
        ppid = re.search(r'w15:paraIdParent="([0-9A-Fa-f]+)"', a)
        if pid and ppid:
            c = pid2cid.get(pid.group(1))
            p = pid2cid.get(ppid.group(1))
            if c is not None:
                parents[c] = p if p is not None else -1

    out["replies"] = len(parents)
    out["roots"] = out["total_comments"] - len(parents)
    for c, p in parents.items():
        if p == -1:
            out["problems"].append(f"批注 {c} 的父 paraId 找不到对应批注（孤儿）")
        elif p == c:
            out["problems"].append(f"批注 {c} 的父指向自己（成环）")

    # 嵌套区间：回复的 range 必须把父批注的 range 包住（OfficeCLI 的写法）
    for c, p in parents.items():
        if p == -1:
            continue
        def pos(kind, cid):
            mm = re.search(rf'<w:{kind}\b[^>]*w:id="{cid}"[^>]*/>', doc)
            return mm.start() if mm else -1
        cs, ce = pos("commentRangeStart", c), pos("commentRangeEnd", c)
        ps, pe = pos("commentRangeStart", p), pos("commentRangeEnd", p)
        if min(cs, ce, ps, pe) < 0:
            out["nested_bad"] += 1
            out["problems"].append(f"批注 {c} 或父 {p} 缺少 range 标记")
            continue
        if cs < ps < pe < ce:
            out["nested_ok"] += 1
        else:
            out["nested_bad"] += 1
            out["problems"].append(f"批注 {c} 的 range 未包住父 {p} 的 range")
    out["ok"] = not out["problems"]
    return out


if __name__ == "__main__":
    import json
    import sys as _s
    try:
        _s.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                              # noqa: BLE001
        pass
    if len(_s.argv) < 2:
        print("用法: python -m manuscript_review.mr_thread <手稿.docx>")
        _s.exit(2)
    print(json.dumps(probe(_s.argv[1]), ensure_ascii=False, indent=1))
    print(json.dumps(verify_threading(_s.argv[1]), ensure_ascii=False, indent=1))
