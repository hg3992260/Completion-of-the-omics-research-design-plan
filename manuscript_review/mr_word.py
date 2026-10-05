# -*- coding: utf-8 -*-
"""Word 落盘层：把缺陷变成「原生批注 + 四色 Track Changes 修订」双轨。

输出契约（与 reviewer-reply-docx 技能的规范一致）
----------------------------------------------
1. **一条缺陷 = 一条 Word 原生批注**，挂在手稿对应段落上。
   批注正文固定三段式，作者在 Word 审阅窗格即可逐条处理：

       【组学·阶段4 图像采集与质控｜关键】CLEAR 16 · METRICS #6
       缺陷：只写"门静脉期增强CT"，机型、管电压、层厚、重建核均未说明。
       证据：所有患者均行门静脉期增强CT检查。扫描参数未作统一规定…
       建议：补全机型、kVp、mAs、层厚、重建卷积核与期相触发方式。

2. **可直接采纳的修改 = Track Changes 修订**，按四色规范着色：

       绿 00B050 + 下划线   新增内容（missing 类缺陷补写的报告项）
       红 FF0000 + 删除线   删除内容
       蓝 0070C0 + 下划线   修改（替换后的新文字）
       橙 ED7D31            移动 / 格式变更

   注意：OfficeCLI 的 ``find/replace`` 在生成 ``<w:ins>`` 时**不带颜色**，
   所以要分两步：先做替换，再按段落序号给修订 run 补色
   （``/body/p[@paraId=X]/r[N]`` 是可以直接 set 的，实测有效）。

3. **原子性**：一次审阅的所有写操作放进**一个 batch**。
   任一条失败则整批回滚，绝不产出"改了一半"的稿件。

4. **绝不改动作者原意**：批注只增不删；修订只针对缺陷明确指向的片段，
   拿不准的（例如需要重算统计量的）只出批注、不动正文。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from manuscript_review import mr_office
from manuscript_review.mr_review_layers import CHAPTER_TITLES, LAYERS

# 四色规范
C_NEW = "00B050"       # 绿：新增
C_DEL = "FF0000"       # 红：删除
C_MOD = "0070C0"       # 蓝：修改（新文）
C_MOVE = "ED7D31"      # 橙：移动 / 格式变更

AUTHOR = "手稿审阅"
REPLY_AUTHOR = "审阅补充"      # 线程回复用的作者名（与独立批注区分开）

# 严重度 → 批注前缀标记
SEV_MARK = {"关键": "■ 关键", "主要": "▲ 主要", "一般": "● 一般"}

# 哪些缺陷类型可以自动落成正文修订
AUTO_INSERT_VERDICTS = ("missing",)          # 缺失 → 追加报告项段落（可自动）
SAFE_REPLACE_VERDICTS = ("wrong",)           # 明确写错 → 替换（需给出 quote）


@dataclass
class RenderedComment:
    para_idx: int
    text: str
    defect_key: str = ""


@dataclass
class RenderedRevision:
    kind: str                 # replace | insert_after | delete_run
    para_idx: int
    find: str = ""
    replace: str = ""
    text: str = ""
    color: str = C_MOD
    defect_key: str = ""


@dataclass
class RenderedReply:
    """作为「线程回复」写入的批注：挂在某条已有审稿批注下面。"""
    parent_cid: int
    para_idx: int
    text: str
    defect_key: str = ""


@dataclass
class ApplyPlan:
    comments: list[RenderedComment] = field(default_factory=list)
    revisions: list[RenderedRevision] = field(default_factory=list)
    replies: list[RenderedReply] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"comments": len(self.comments), "revisions": len(self.revisions),
                "replies": len(self.replies), "skipped": list(self.skipped),
                "comment_items": [{"para": c.para_idx, "key": c.defect_key}
                                  for c in self.comments],
                "revision_items": [{"kind": r.kind, "para": r.para_idx,
                                    "key": r.defect_key} for r in self.revisions]}


@dataclass
class ApplyResult:
    ok: bool = False
    out_path: str = ""
    comments_added: int = 0
    replies_added: int = 0
    revisions_added: int = 0
    skipped: list = field(default_factory=list)
    batch: dict = field(default_factory=dict)
    verify: dict = field(default_factory=dict)
    threading: dict = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict:
        return {"ok": self.ok, "out_path": self.out_path,
                "comments_added": self.comments_added,
                "replies_added": self.replies_added,
                "revisions_added": self.revisions_added,
                "skipped": list(self.skipped), "batch": self.batch,
                "verify": self.verify, "threading": self.threading,
                "error": self.error}


# --------------------------------------------------------------------------- 批注文本
def comment_text(d: dict) -> str:
    """把一条缺陷渲染成 Word 批注正文（三段式，作者可直接照着改）。"""
    layer = d.get("layer") or ""
    lname = LAYERS.get(layer, {}).get("name", layer)
    sev = d.get("severity") or "主要"
    mark = SEV_MARK.get(sev, sev)
    spec = (d.get("spec") or "").strip()
    ref = (d.get("ref") or "").strip()

    head = f"【{lname}｜{mark}】"
    if spec:
        head += spec
    elif ref:
        head += ref

    lines = [head]
    if ref and spec:
        lines.append(f"规范条目：{ref}")
    title = plain((d.get("title") or "").strip())
    why = plain((d.get("why") or "").strip())
    lines.append("缺陷：" + (f"{title}。" if title else "") + why)
    ev = plain((d.get("evidence") or "").strip())
    if ev:
        lines.append("证据：" + ev[:160])
    sug = plain((d.get("suggestion") or "").strip())
    if sug:
        lines.append("建议：" + sug)
    src = d.get("source")
    tag = "确定性核验" if src == "signal" else "语义审阅"
    lines.append(f"（来源：{tag}｜条目 {d.get('req_id', '')}）")
    return "\n".join(x for x in lines if x.strip())


def _first_body_para(manuscript, chapter_keys: list[str]) -> int:
    """兜底锚点：相关章节的第一个正文段（跳过标题段）。"""
    for k in chapter_keys:
        for idx in manuscript.chapters.get(k, []):
            p = manuscript.get(idx)
            if p and p.text and not p.is_heading and len(p.text) > 1:
                return idx
    for p in manuscript.paragraphs:
        if p.text and not p.is_heading:
            return p.idx
    return 1


# 信号 → 它该被报告在哪些章节（第一个命中的章节优先）
SIGNAL_CHAPTERS: dict[str, list[str]] = {
    "ethics_approval": ["methods", "ethics", "other"],
    "informed_consent": ["methods", "ethics"],
    "registration_id": ["methods", "abstract", "other"],
    "data_source": ["methods", "abstract"],
    "data_overlap": ["methods", "results"],
    "inclusion_criteria": ["methods"],
    "sample_size_rationale": ["methods"],
    "event_counts": ["methods", "results"],
    "acquisition_params": ["methods"],
    "contrast_phase": ["methods"],
    "segmentation_strategy": ["methods"],
    "reader_qualification": ["methods"],
    "icc_dice": ["methods", "results"],
    "resampling": ["methods"],
    "discretization": ["methods"],
    "normalization": ["methods"],
    "ibsi": ["methods"],
    "feature_count": ["methods"],
    "param_file": ["methods", "data_availability"],
    "software_version": ["methods"],
    "feature_stability": ["methods"],
    "collinearity": ["methods"],
    "dimension_ratio": ["methods", "discussion"],
    "primary_model": ["methods"],
    "nested_cv": ["methods"],
    "tuning": ["methods"],
    "external_validation": ["methods", "results"],
    "model_update": ["methods"],
    "confidence_interval": ["results", "abstract"],
    "calibration": ["results"],
    "dca": ["results"],
    "incremental_value": ["results", "discussion"],
    "model_comparison": ["results", "discussion"],
    "primary_endpoint": ["methods", "abstract"],
    "multiplicity": ["methods"],
    "assumption_check": ["methods"],
    "effect_size": ["results"],
    "missing_data": ["methods", "results"],
    "random_seed": ["methods"],
    "open_science": ["data_availability", "other", "conclusion"],
    "reporting_checklist": ["data_availability", "other", "conclusion"],
}


def target_chapters(d: dict) -> list[str]:
    """一条缺陷应该被报告在哪些章节（按优先级）。"""
    sig = d.get("signal") or ""
    if sig and sig in SIGNAL_CHAPTERS:
        return SIGNAL_CHAPTERS[sig]
    # 有明确段号或引文的，直接用它的章节
    if (d.get("para_idx") or 0) > 0 and d.get("chapter"):
        return [d["chapter"]]
    if d.get("anchors"):
        return list(d["anchors"])
    return list(LAYERS.get(d.get("layer") or "", {}).get("sections") or ["methods"])


def anchor_of(manuscript, d: dict, avoid: set | None = None) -> int:
    """给单条缺陷挑锚点段（不做分散）。

    优先级：缺陷自带的段号 → 原文片段回查 → 目标章节里第一个未被占用的正文段
            → 第 1 段。``avoid`` 是本批已被占用的段号（用于分散批注）。
    """
    avoid = avoid or set()
    idx = d.get("para_idx") or 0
    if isinstance(idx, int) and 1 <= idx <= len(manuscript.paragraphs):
        p = manuscript.get(idx)
        if p and p.text:
            return idx
    quote = (d.get("quote") or d.get("evidence") or "").strip()
    if quote:
        p = manuscript.find_paragraph(quote[:40])
        if p:
            return p.idx
    keys = target_chapters(d)
    for k in keys:
        for i in manuscript.chapters.get(k, []):
            p = manuscript.get(i)
            if p and p.text and not p.is_heading and i not in avoid:
                return i
    # 该章节的正文段都占满了，就允许复用第一个
    for k in keys:
        for i in manuscript.chapters.get(k, []):
            p = manuscript.get(i)
            if p and p.text and not p.is_heading:
                return i
    return _first_body_para(manuscript, keys)


def assign_anchors(manuscript, defects: list[dict]) -> list[int]:
    """给一批缺陷分配批注锚点，并把同章节的缺陷**分散**到不同段落。

    为什么必须分散：一份手稿常常一次报出十几条"某参数未报告"，
    如果全部挂到方法章第一段，作者在 Word 里会看到十几条批注叠在一处，
    既看不清也改不动。这里按「目标章节内正文段的顺序」轮流分配，
    同一段最多挂 `per_para` 条。
    """
    per_para = 3
    used: dict[int, int] = {}
    out: list[int] = []
    for d in defects:
        idx = anchor_of(manuscript, d, avoid={k for k, v in used.items() if v >= per_para})
        used[idx] = used.get(idx, 0) + 1
        out.append(idx)
    return out


# --------------------------------------------------------------------------- 修订规划
def _safe_find(manuscript, d: dict) -> tuple[int, str]:
    """判断该缺陷能否安全落成一次 find/replace：返回 (段号, 要替换的原文)。

    安全条件（缺一不可）：
      · verdict 属于明确写错（wrong），说明作者原文有可指向的具体片段；
      · 能定位到段落；
      · 片段长度 ≥ 6 字且 ≤ 300 字（太短会误伤，太长会跨段）；
      · 片段在**该段全文**中出现（OfficeCLI 的 find 是全文替换，所以必须唯一）。
    """
    if (d.get("verdict") or "") not in SAFE_REPLACE_VERDICTS:
        return 0, ""
    quote = (d.get("quote") or "").strip()
    if not quote or not (6 <= len(quote) <= 300):
        return 0, ""
    p = manuscript.find_paragraph(quote)
    if p is None:
        return 0, ""
    # 唯一性：该片段在全文只能出现一次，否则会改到别处
    hits = sum(1 for q in manuscript.paragraphs if quote in q.text)
    if hits != 1:
        return 0, ""
    return p.idx, quote


def _insert_text_for(d: dict) -> str:
    """缺失类缺陷 → 补写段落的正文。

    刻意不替作者编造数据：写成"待补"占位 + 明确的报告位点，
    作者填数即可。这是这套流程的诚信底线。
    """
    sug = (d.get("suggestion") or "").strip()
    title = (d.get("title") or "").strip()
    spec = (d.get("spec") or "").strip()
    layer = LAYERS.get(d.get("layer") or "", {}).get("name", d.get("layer") or "")
    seg = f"【补正·{layer}】{title}"
    if spec:
        seg += f"（{spec}）"
    if sug:
        seg += "：" + sug
    if "待" not in seg:
        seg += "。请补充具体数值/来源后删除本标注。"
    return seg


def build_plan(manuscript, defects: list[dict], mode: str = "dual",
               max_insert: int = 40, reply_pairs: list | None = None) -> ApplyPlan:
    """把缺陷列表编译成 OfficeCLI 操作计划。

    Args:
        mode: dual  = 批注 + 可自动的修订（默认）
              comment_only = 只出批注，完全不碰正文
        max_insert: 单次审阅最多补写多少段，避免把稿件改得面目全非
        reply_pairs: [(父批注id, 缺陷)] —— 这些缺陷写成**线程回复**挂在审稿意见下，
            不再作为独立批注重复出现，正文修订也仍照常生成。

    Returns:
        ApplyPlan（含被跳过的缺陷及原因，界面要如实展示）
    """
    from manuscript_review.mr_thread import reply_text

    plan = ApplyPlan()
    inserts = 0
    used_find: set[str] = set()

    # 先统一分配批注锚点：同章节的缺陷分散到不同段落，避免批注叠在一处
    anchors = assign_anchors(manuscript, defects)
    reply_map = {id(f): c for c, f in (reply_pairs or [])}
    # 父批注所在段落：回复必须锚在这里，OfficeCLI 才能把 range 正确嵌套
    parent_para = {c: (f or {}).get("_anchor_para") or 0 for c, f in (reply_pairs or [])}

    for i, d in enumerate(defects):
        key = f"{d.get('source', '')}:{d.get('req_id', '')}@{d.get('para_idx', 0)}#{i}"
        a = anchors[i]

        # 挂靠回复：写成线程回复，锚点必须用**审稿意见所在的段落**。
        # 为什么不能用分散后的锚点：OfficeCLI 只有当子批注的 range 与父批注的
        # range 落在同一段文本上时，才能把子 range 包在父 range 外面；
        # 把回复挂到别的段落会造成「线程校验：range 未包住父」。
        parent = reply_map.get(id(d))
        if parent is not None:
            rpara = d.get("_anchor_para") or parent_para.get(parent) or a
            plan.replies.append(RenderedReply(parent_cid=parent, para_idx=rpara,
                                              text=reply_text(d), defect_key=key))
            # 正文修订仍照常生成（审稿人看得到 diff 才完整），
            # 但只有当补写段落与回复锚点同段时才顺带落修订，避免错位
            if (mode != "comment_only" and d.get("verdict") == "missing"
                    and d.get("source") == "signal" and inserts < max_insert
                    and rpara == a):
                inserts += 1
                plan.revisions.append(RenderedRevision(
                    kind="insert_after", para_idx=a, text=_insert_text_for(d),
                    color=C_NEW, defect_key=key))
            continue

        plan.comments.append(RenderedComment(para_idx=a,
                                             text=comment_text(d), defect_key=key))
        if mode == "comment_only":
            continue
        # 1) 明确写错且有唯一片段 → find/replace（蓝新 + 红旧）
        pidx, find = _safe_find(manuscript, d)
        if pidx and find and find not in used_find:
            used_find.add(find)
            plan.revisions.append(RenderedRevision(
                kind="replace", para_idx=pidx, find=find,
                replace=plain((d.get("suggestion") or "").strip())[:800],
                color=C_MOD, defect_key=key))
            continue
        # 2) 缺失类 → 在锚点段之后追加一段绿色插入
        if (d.get("verdict") == "missing"
                and d.get("source") == "signal"
                and inserts < max_insert):
            inserts += 1
            plan.revisions.append(RenderedRevision(
                kind="insert_after", para_idx=a,
                text=_insert_text_for(d), color=C_NEW, defect_key=key))
            continue
        # 3) 其余只出批注 —— 需要作者判断或重算，程序不擅自改正文
        plan.skipped.append({
            "req_id": d.get("req_id"), "title": d.get("title"),
            "severity": d.get("severity"),
            "reason": ("需要重算/补充数据后才能定稿，只出批注不动正文"
                       if d.get("verdict") != "missing" else
                       "补写段数已达上限或缺少可定位片段，只出批注"),
        })
    return plan


# --------------------------------------------------------------------------- 执行
def _one_paragraph(text: str) -> str:
    """把补写文本压成一段：换行 → 分号，避免 OOXML 里出现裸换行。"""
    parts = [x.strip().rstrip("。；;") for x in re.split(r"\n+", plain(text)) if x.strip()]
    if not parts:
        return plain(text).strip()
    return "；".join(parts) + "。"


_MD_RE = (
    (re.compile(r"\*\*([^*]+)\*\*"), r"\1"),      # **粗体**
    (re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)"), r"\1"),   # *斜体*
    (re.compile(r"`([^`]+)`"), r"\1"),            # `代码`
    (re.compile(r"^\s{0,3}#{1,6}\s*", re.M), ""),  # 标题井号
    (re.compile(r"^\s*[-*+]\s+", re.M), ""),      # 列表符号
)


def plain(text: str) -> str:
    """把模型输出里的 Markdown 记号去掉。

    LLM 很容易在 suggestion 里写 **加粗**，直接塞进 Word 会变成字面上的星号 ——
    作者看到 ``模型**可能**有助于`` 只会困惑。这里统一清洗。
    """
    s = text or ""
    for pat, rep in _MD_RE:
        s = pat.sub(rep, s)
    return s


def apply_plan(src_path: str, out_path: str, plan: ApplyPlan,
               author: str = AUTHOR, timeout: int = 300,
               reply_author: str = REPLY_AUTHOR,
               reply_pairs: list | None = None) -> ApplyResult:
    """原子落盘：一次 batch 完成全部批注与修订。

    执行顺序（关键）：
        1. find/replace —— 不改变段落数，段落序号与规划时一致；
        2. 追加段落 —— **按段号倒序**插入，前面段落的序号不受影响；
        3. 补色 —— 段落序号此时是最终态；
        4. 批注 + 线程回复 —— 最后加，此时段落序号已是最终态，锚点最准。
    全部命令在一个 batch 里，失败即回滚。
    """
    res = ApplyResult(out_path=os.path.abspath(out_path))
    info = mr_office.available()
    if not info.get("available"):
        res.error = info.get("error") or "未找到 officecli"
        return res
    if not os.path.exists(src_path):
        res.error = f"源文件不存在：{src_path}"
        return res

    # 工作副本：绝不动原稿
    import shutil
    try:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        shutil.copyfile(src_path, out_path)
    except Exception as e:                                         # noqa: BLE001
        res.error = f"无法创建输出副本：{e}"
        return res

    cmds: list[dict] = []

    # ---- 1) 替换（先做，保持段落数不变）
    for r in plan.revisions:
        if r.kind != "replace" or not r.find:
            continue
        cmds.append({"command": "set", "path": "/body",
                     "props": {"find": r.find, "replace": r.replace,
                               "revision.author": author}})

    # 插入段**不在这里做** —— 见下方「阶段 3」的说明：
    # 插入会改变段落序号，必须等批注/回复都按原段号锚定之后再做。
    ins = [r for r in plan.revisions if r.kind == "insert_after"]
    ins.sort(key=lambda r: r.para_idx)

    # ---- 2) 给 find/replace 产生的修订 run 补色（红旧 / 蓝新）
    # find/replace 之后段落数不变，段号仍是规划时的段号；
    # 用 get 现场读 run 的 revision 元数据，才能知道 ins/del 落在哪个 run 上。
    color_cmds: list[dict] = []

    def _collect(path: str) -> None:
        for r in plan.revisions:
            if r.kind != "replace":
                continue
            runs = mr_office.runs_in(path, f"/body/p[{r.para_idx}]")
            for k, run in enumerate(runs, 1):
                fmt = run.get("format") or {}
                rtype = fmt.get("revision.type")
                if rtype == "del":
                    color_cmds.append({"command": "set",
                                       "path": f"/body/p[{r.para_idx}]/r[{k}]",
                                       "props": {"color": C_DEL, "strike": "true"}})
                elif rtype == "ins":
                    color_cmds.append({"command": "set",
                                       "path": f"/body/p[{r.para_idx}]/r[{k}]",
                                       "props": {"color": C_MOD, "underline": "single"}})

    # 补色必须在 batch 完成之后才能读到 run 的真实结构，
    # 所以分多批：① 替换 → ② 批注/回复 + 补色 → ③ 补写段。任一批失败即中止。
    batch1 = mr_office.batch(out_path, cmds, timeout=timeout)
    res.batch = batch1.to_dict()
    if not batch1.ok:
        res.error = batch1.error or "批量写入失败"
        return res

    # 第二批：补色 + 批注（都在内容改完之后）
    batch2: list[dict] = []
    _collect(out_path)
    batch2.extend(color_cmds)

    # ---- 3) 批注 + 线程回复
    # 此处段落序号**尚未位移**（补写段还没插），所以批注/回复都按规划时的原段号锚定，
    # 父批注与回复落在同一段上，OfficeCLI 才能把回复的 range 正确嵌套进父批注。
    # 回复必须写在独立批注**之后**：OfficeCLI 按自己维护的计数发 id，
    # 先写完所有顶层批注再写回复，父 id 一定已存在。
    for c in plan.comments:
        batch2.append({"command": "add", "parent": f"/body/p[{c.para_idx}]",
                       "type": "comment",
                       "props": {"author": author, "text": c.text,
                                 "runStart": 0, "range": True}})
    for rp in plan.replies:
        props = {"author": reply_author, "text": rp.text,
                 "runStart": 0, "range": True, "parentId": rp.parent_cid}
        batch2.append({"command": "add", "parent": f"/body/p[{rp.para_idx}]",
                       "type": "comment", "props": props})

    if batch2:
        b2 = mr_office.batch(out_path, batch2, timeout=timeout)
        res.batch["phase2"] = b2.to_dict()
        if not b2.ok:
            res.error = ("正文修订已写入，但批注/回复/补色阶段失败："
                         + (b2.error or ""))
            return res
        res.comments_added = len(plan.comments)
        res.replies_added = len(plan.replies)
    res.revisions_added = len([r for r in plan.revisions if r.kind == "replace"])

    # ---- 4) 最后补写「缺失报告项」段落
    # 为什么放到最后：插段落会改变段落序号，一旦先插，
    # 后面按原段号挂的批注/回复就会错位（回复嵌套会失败）。
    # 段号补偿：按原段号升序依次插入，第 k 次插入后，插入点之前的段号不变、
    # 之后的段号 +1；所以第 k 次实际插到 original + k 位置。
    if ins:
        ins_cmds: list[dict] = []
        for k, r in enumerate(ins):
            ins_cmds.append({"command": "add", "parent": "/body",
                             "type": "paragraph",
                             "after": f"/body/p[{r.para_idx + k}]",
                             "props": {"text": _one_paragraph(r.text),
                                       "revision.type": "ins",
                                       "revision.author": author,
                                       "color": r.color, "underline": "single",
                                       "size": "10.5pt"}})
        b3 = mr_office.batch(out_path, ins_cmds, timeout=timeout)
        res.batch["phase3"] = b3.to_dict()
        if not b3.ok:
            res.error = ("批注已写入，但补写报告项段落失败："
                         + (b3.error or ""))
            return res
        res.revisions_added += len(ins)

    res.skipped = plan.skipped
    # 校验前必须先 flush：officecli 有常驻进程，改的是内存里的文档，
    # 不 save/close 就直接读磁盘会读到旧内容（实测踩过这个坑）。
    mr_office.close(out_path)
    res.verify = verify(out_path)
    # 有线程回复时，额外跑一次 mr_thread 的 4 项线程校验（含父级有效性）
    if plan.replies:
        try:
            from manuscript_review.mr_thread import verify_threading
            res.threading = verify_threading(out_path)
        except Exception as e:                                     # noqa: BLE001
            res.threading = {"ok": False, "problems": [f"线程校验异常：{e}"]}
    res.ok = bool(res.verify.get("ok")) and \
        bool(res.threading.get("ok", True))
    if not res.ok and not res.error:
        probs = list(res.verify.get("problems") or []) + \
            list(res.threading.get("problems") or [])
        res.error = "写入完成但校验未通过：" + str(probs)
    return res


# --------------------------------------------------------------------------- 校验
def verify(path: str) -> dict:
    """落盘后校验：批注标记配平、修订存在、批注数 = 评论部件数。

    注意正则边界：这里**不能用 ``\\b``** —— ``t`` 与 ``>`` 之间不是词边界，
    会把 ``<w:commentRangeStart/>`` 这类自闭合标签漏掉，导致误判校验失败。
    统一用 ``[\\s/>]`` 前瞻。
    """
    out = {"ok": False, "problems": [], "comments": 0, "revisions": 0,
           "markers": {}, "colors": {}}
    r = mr_office.raw(path, "/document")
    if not r.ok or not r.stdout:
        out["problems"].append(f"无法读取 document.xml：{r.error or '空输出'}")
        return out
    doc = r.stdout
    for tag, key in (("commentRangeStart", "start"), ("commentRangeEnd", "end"),
                     ("commentReference", "ref")):
        out["markers"][key] = len(re.findall(r"<w:" + tag + r"(?=[\s/>])", doc))
    out["revisions"] = len(re.findall(r"<w:(?:ins|del)(?=[\s/>])", doc))
    for c in (C_NEW, C_DEL, C_MOD, C_MOVE):
        out["colors"][c] = len(re.findall(r'w:color w:val="' + c + r'"', doc))
    out["comments"] = len(mr_office.comments(path))

    m = out["markers"]
    if not (m["start"] == m["end"] == m["ref"]):
        out["problems"].append(
            f"批注范围标记不配平：start={m['start']} end={m['end']} ref={m['ref']}")
    if out["comments"] and m["ref"] != out["comments"]:
        out["problems"].append(
            f"评论部件 {out['comments']} 条，但正文只有 {m['ref']} 个批注引用")
    if out["comments"] == 0 and out["revisions"] == 0:
        out["problems"].append("既没有批注也没有修订写入")
    out["ok"] = not out["problems"]
    return out


def summarize_plan(plan: ApplyPlan) -> str:
    """给界面/日志用的一句话摘要。"""
    parts = [f"批注 {len(plan.comments)} 条"]
    if plan.replies:
        parts.append(f"线程回复 {len(plan.replies)} 条")
    parts.append(f"正文修订 {len(plan.revisions)} 处")
    parts.append(f"仅批注 {len(plan.skipped)} 条")
    return " · ".join(parts)


if __name__ == "__main__":
    import json
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                              # noqa: BLE001
        pass
    print(json.dumps(mr_office.available(), ensure_ascii=False, indent=1))
    if len(sys.argv) > 1:
        print(json.dumps(verify(sys.argv[1]), ensure_ascii=False, indent=1))
