# -*- coding: utf-8 -*-
"""审阅编排引擎：把「导入 → 解析 → 三层对照 → 落回 Word」串成一条流水线。

流水线（每一步都落盘，可中断、可续跑、可审计）
------------------------------------------
    1. ingest    导入 PDF/Word：PDF 先用 mr_pdf 转成 DOCX 转换稿
    2. parse     解析结构：段落 + 段号锚点 + 章节映射
    3. signals   确定性核验：可证据化的硬缺陷（快、可复现）
    4. review    LLM 语义审阅：确定性覆盖不到的条目（分层分批 + 缓存）
    5. report    生成审阅报告（Markdown / JSON）
    6. apply     落回 Word：原生批注 + 四色 Track Changes 修订

关键设计
-------
· **段号即锚点**：mr_docx 解析出的段号就是 OfficeCLI 的 /body/p[N]，
  所以缺陷从产生到落盘全程带着同一个段号，不存在"对不上"的可能。
· **两层去重**：LLM 不再重复报确定性层已报的信号（skip_signals），
  避免同一条缺陷出现两次批注。
· **结果全量落盘**：defects 列表写进项目目录，
  界面、MCP、报告三处读的是同一份数据。
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field


# --------------------------------------------------------------------------- 项目存储
def projects_root() -> str:
    try:
        from app_paths import data_path
        d = data_path("manuscript_review", "projects")
    except Exception:                                              # noqa: BLE001
        d = os.path.join(os.path.expanduser("~"), "PCLRadiomics", "manuscript_review",
                         "projects")
    os.makedirs(d, exist_ok=True)
    return d


def exports_root() -> str:
    try:
        from app_paths import export_dir
        d = os.path.join(export_dir(), "手稿审阅")
    except Exception:                                              # noqa: BLE001
        d = os.path.join(projects_root(), "exports")
    os.makedirs(d, exist_ok=True)
    return d


@dataclass
class ReviewProject:
    """一次审阅的全部产物。存成一个 JSON，界面/报告/MCP 都读它。"""
    name: str = "未命名手稿"
    created: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M"))
    updated: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M"))
    source_path: str = ""              # 原稿（PDF 或 DOCX）
    docx_path: str = ""                # 用于审阅的 DOCX（可能是转换稿）
    converted: bool = False
    converted_from: str = ""
    manuscript: dict = field(default_factory=dict)      # Manuscript.to_dict()
    outline: list = field(default_factory=list)
    signals: list = field(default_factory=list)         # 确定性核验全量结果
    signal_summary: dict = field(default_factory=dict)
    defects: list = field(default_factory=list)         # 合并去重后的缺陷
    summary: dict = field(default_factory=dict)
    calls: list = field(default_factory=list)           # LLM 调用审计
    layers: list = field(default_factory=list)
    applied: dict = field(default_factory=dict)         # mr_word.ApplyResult
    applied_keys: list = field(default_factory=list)     # 已写入 Word 的发现指纹
    applied_at: str = ""                                 # 最近一次落盘时间
    annotated_path: str = ""                             # 选定的「审稿批注版」底板
    report_path: str = ""
    out_docx: str = ""
    # 课题关联：这份手稿属于工作台里的哪个设计项目（导入时自动登记）
    design_name: str = ""
    design_path: str = ""
    design_digest: str = ""      # 课题背景快照（研究设想 + 各阶段定稿摘要）
    warnings: list = field(default_factory=list)
    log: list = field(default_factory=list)

    # -- 序列化 -------------------------------------------------------------
    def to_dict(self, with_body: bool = False) -> dict:
        d = dict(self.__dict__)
        if not with_body:
            ms = dict(d.get("manuscript") or {})
            ms.pop("body", None)
            d["manuscript"] = ms
        return d

    def save(self, path: str = "") -> str:
        self.updated = time.strftime("%Y-%m-%d %H:%M")
        p = path or self.path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(with_body=True), fh, ensure_ascii=False, indent=1)
        return p

    def path(self) -> str:
        safe = _safe_name(self.name)
        return os.path.join(projects_root(), f"{safe}.json")

    @staticmethod
    def load(path: str) -> "ReviewProject":
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        p = ReviewProject()
        for k, v in d.items():
            if hasattr(p, k):
                setattr(p, k, v)
        return p

    @staticmethod
    def list_all() -> list[dict]:
        out = []
        for fn in sorted(os.listdir(projects_root())):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(projects_root(), fn)
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    d = json.load(fh)
                defects = d.get("defects") or []
                # summary 可能是旧版项目缺的字段，直接从 defects 兜底统计
                summ = d.get("summary") or {}
                key_cnt = summ.get("关键")
                if key_cnt is None:
                    key_cnt = sum(1 for x in defects if x.get("severity") == "关键")
                out.append({
                    "name": d.get("name"), "path": fp,
                    "created": d.get("created"), "updated": d.get("updated"),
                    "defects": len(defects),
                    "关键": key_cnt,
                    "source": os.path.basename(d.get("source_path") or ""),
                    "out_docx": d.get("out_docx") or "",
                    "applied": bool((d.get("applied") or {}).get("ok")),
                    "bytes": os.path.getsize(fp),
                })
            except Exception:                                      # noqa: BLE001
                continue
        out.sort(key=lambda x: x.get("updated") or "", reverse=True)
        return out

    def add_log(self, step: str, msg: str) -> None:
        self.log.append({"ts": time.strftime("%H:%M:%S"), "step": step, "msg": msg})
        if len(self.log) > 400:
            self.log = self.log[-400:]


def _safe_name(name: str) -> str:
    import re
    s = re.sub(r'[\\/:*?"<>|\s]+', "_", (name or "").strip())
    return (s.strip("._") or "未命名手稿")[:80]


def _finding_key(d: dict) -> str:
    """发现指纹：用于「已入稿」去重，让重复跑审阅时只写新增结论。

    用 (来源, 条目号, 段号) 而不是标题文本 —— 标题可能被模型改写，
    但条目号与段号是稳定的。
    """
    return "|".join([
        str(d.get("source") or ""),
        str(d.get("req_id") or ""),
        str(d.get("para_idx") or 0),
    ])


def _design_digest(design, limit: int = 4000) -> str:
    """把课题背景压成一段上下文：研究设想 + 各阶段定稿摘要。

    用途：语义审阅时把「这个课题本来打算怎么做」一并交给模型，
    这样它才能判断出**手稿与课题意图不一致**这类缺陷
    （例如课题预设了外部验证，手稿却只报了内部验证）。
    """
    if design is None:
        return ""
    parts = []
    raw = (getattr(design, "raw_design", "") or "").strip()
    if raw:
        parts.append("【课题的初步设想】\n" + raw[:1500])
    done = []
    try:
        from stages_data import STAGES
        for s in STAGES:
            st = (getattr(design, "stages", {}) or {}).get(str(s["id"])) or {}
            body = (st.get("final") or st.get("draft") or "").strip()
            if body:
                done.append(f"{s['id']:02d} {s['title']}：{body[:260]}")
    except Exception:                                              # noqa: BLE001
        pass
    if done:
        parts.append("【课题已定稿的阶段】\n" + "\n".join(done))
    txt = "\n\n".join(parts).strip()
    return txt[:limit]


# --------------------------------------------------------------------------- 引擎
class RevEngine:
    """审阅引擎。所有方法都返回 (ok, message)，异常不往上抛，便于界面直接显示。"""

    def __init__(self, client=None):
        self.client = client

    # -- 1+2 导入与解析 ------------------------------------------------------
    def ingest(self, path: str, project: ReviewProject | None = None,
               max_pages: int = 0, design=None) -> tuple[bool, str, ReviewProject | None]:
        """导入并解析手稿。

        design: 工作台当前的设计项目（design_agent.Project）。给了它就把本次审阅
            与该课题关联起来，并快照课题背景，供语义审阅时作为上下文。
        """
        from manuscript_review import mr_docx, mr_pdf

        if not os.path.exists(path):
            return False, f"文件不存在：{path}", None
        p = project or ReviewProject()
        p.source_path = os.path.abspath(path)
        p.name = os.path.splitext(os.path.basename(path))[0]
        p.add_log("ingest", f"导入 {os.path.basename(path)}")

        # ---- 课题关联（自动登记，无需人工操作）
        if design is not None:
            p.design_name = getattr(design, "name", "") or ""
            p.design_path = getattr(design, "path", "") or ""
            p.design_digest = _design_digest(design)
            p.add_log("link", f"已关联课题「{p.design_name}」"
                              f"（背景 {len(p.design_digest)} 字）")

        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            conv = mr_pdf.to_docx(path, max_pages=max_pages)
            if not conv.ok:
                return False, conv.error or "PDF 转换失败", p
            p.docx_path = conv.docx_path
            p.converted = True
            p.converted_from = conv.pdf_path
            p.warnings.extend(conv.warnings)
            p.add_log("ingest", f"PDF → DOCX：{os.path.basename(conv.docx_path)}"
                                f"（{conv.pages} 页 / {conv.paragraphs} 段）")
        elif ext in (".docx",):
            p.docx_path = os.path.abspath(path)
        elif ext == ".doc":
            return False, ("不支持旧版 .doc，请先在 Word 中另存为 .docx 再导入。"), p
        else:
            return False, f"不支持的格式：{ext}（支持 .pdf / .docx）", p

        try:
            ms = mr_docx.load(p.docx_path)
        except Exception as e:                                     # noqa: BLE001
            return False, f"解析 DOCX 失败：{type(e).__name__}: {e}", p

        p.manuscript = ms.to_dict()
        p.outline = ms.outline()
        p.warnings.extend(ms.warnings)
        p.add_log("parse", f"解析 {len(ms.paragraphs)} 段 / {ms.word_count} 字；"
                           f"识别章节 {len(p.outline)} 个")
        if design is not None:
            self._register_attachment(p, design)
        p.save()
        return True, f"已导入并解析：{len(ms.paragraphs)} 段，{len(p.outline)} 个章节", p

    # -- 课题附件登记 --------------------------------------------------------
    def _register_attachment(self, project: ReviewProject, design) -> None:
        """把这份手稿登记成设计项目的附件（课题 → 手稿 可回溯）。

        设计项目保存失败（例如只读目录）不应影响审阅本身，所以这里吞掉异常并记日志。
        """
        if design is None or not hasattr(design, "link_manuscript"):
            return
        try:
            key = sum(1 for d in (project.defects or [])
                      if d.get("severity") == "关键")
            rec = design.link_manuscript(
                project_path=project.path(),
                name=project.name,
                source=project.source_path,
                docx=project.docx_path,
                out_docx=project.out_docx,
                report=project.report_path,
                annotated=project.annotated_path,
                defects=len(project.defects or []),
                key_defects=key)
            design.save()
            project.add_log("link", f"已登记为课题「{design.name}」的手稿附件"
                                    f"（{len(design.manuscripts)} 份）")
            _ = rec
        except Exception as e:                                     # noqa: BLE001
            project.add_log("link", f"课题附件登记失败（不影响审阅）：{e}")

    # -- 3 确定性核验 --------------------------------------------------------
    def run_signals(self, project: ReviewProject) -> tuple[bool, str, ReviewProject]:
        from manuscript_review import mr_signals

        ms = self._manuscript(project)
        if ms is None:
            return False, "尚未导入手稿", project
        hits = mr_signals.check(ms)
        project.signals = [h.to_dict() for h in hits]
        project.signal_summary = mr_signals.summarize(hits)
        det = mr_signals.defects(hits)
        # 保留 LLM 缺陷，只替换确定性缺陷
        project.defects = det + [d for d in project.defects if d.get("source") != "signal"]
        # 只跑确定性核验时也必须刷新汇总，否则界面与 MCP 会读到空 summary
        from manuscript_review.mr_reviewer import sort_defects, summarize
        project.defects = sort_defects(project.defects)
        project.summary = summarize(project.defects)
        project.add_log("signals",
                        f"确定性核验 {len(hits)} 项：缺失 {project.signal_summary.get('missing', 0)}"
                        f" · 不完整 {project.signal_summary.get('weak', 0)}"
                        f" · 已报告 {project.signal_summary.get('reported', 0)}")
        project.save()
        return True, (f"确定性核验完成：{project.signal_summary.get('missing', 0)} 项缺失、"
                      f"{project.signal_summary.get('weak', 0)} 项信息不完整"), project

    # -- 4 LLM 语义审阅 -----------------------------------------------------
    def run_review(self, project: ReviewProject, layers: list[str] | None = None,
                   use_cache: bool = True, max_batches: int = 0,
                   on_progress=None, on_delta=None) -> tuple[bool, str, ReviewProject]:
        from manuscript_review import mr_reviewer, mr_signals

        ms = self._manuscript(project)
        if ms is None:
            return False, "尚未导入手稿", project
        if self.client is None:
            return False, "未配置 LLM（检查 llm_config.json / 密钥）", project

        # 确定性层已报的信号，LLM 不再重复报
        skip = set()
        for h in project.signals:
            if h.get("verdict") in ("missing", "weak"):
                skip.add(h.get("signal"))

        defects, calls = mr_reviewer.review(
            self.client, ms, layers=layers, use_cache=use_cache,
            skip_signals=skip, max_batches=max_batches,
            on_progress=on_progress, on_delta=on_delta,
            design_context=project.design_digest or "")

        det = [d for d in project.defects if d.get("source") == "signal"]
        project.defects = mr_reviewer.merge_defects(det, defects)
        project.calls = [c.to_dict() for c in calls]
        project.defects = mr_reviewer.sort_defects(project.defects)
        project.summary = mr_reviewer.summarize(project.defects)
        project.layers = layers or ["omics", "stat", "shape"]
        ok_calls = sum(1 for c in calls if c.ok)
        project.add_log("review",
                        f"LLM 审阅 {len(calls)} 批（成功 {ok_calls}）→ 新增缺陷 "
                        f"{len(defects)} 条；合并后共 {len(project.defects)} 条")
        project.save()
        errs = [c.error for c in calls if not c.ok and c.error]
        if ok_calls == 0 and errs:
            return False, "LLM 审阅全部失败：" + errs[0], project
        msg = (f"语义审阅完成：{ok_calls}/{len(calls)} 批成功，"
               f"新增 {len(defects)} 条缺陷（合并后 {len(project.defects)} 条）")
        if errs:
            msg += f"；{len(errs)} 批失败：{errs[0][:80]}"
        return True, msg, project

    # -- 5 报告 -------------------------------------------------------------
    def build_report(self, project: ReviewProject) -> tuple[bool, str, ReviewProject]:
        from manuscript_review import mr_report

        ms = self._manuscript(project)
        if ms is None:
            return False, "尚未导入手稿", project
        try:
            path = mr_report.write_markdown(project, ms)
        except Exception as e:                                     # noqa: BLE001
            return False, f"生成报告失败：{type(e).__name__}: {e}", project
        project.report_path = path
        project.add_log("report", f"审阅报告：{os.path.basename(path)}")
        project.save()
        return True, f"报告已生成：{path}", project

    # -- 6 落回 Word --------------------------------------------------------
    def apply_to_word(self, project: ReviewProject, mode: str = "dual",
                      out_path: str = "", max_insert: int = 25,
                      merge_into: str = "", reply_mode: str = "reply",
                      per_parent: int = 4, min_match: float = 0.8,
                      only_defects: list | None = None
                      ) -> tuple[bool, str, ReviewProject]:
        """把缺陷写进 Word。

        Args:
            mode: dual / comment_only
            merge_into: 指定「审稿批注版」手稿路径。给了它就以此为底板，
                把发现并入（保留审稿人原有批注，不动它一个字）。
            reply_mode: 仅当 merge_into 有效时起作用
                reply      = 匹配得上的发现作为**线程回复**挂在审稿意见下（默认）
                standalone = 只做独立批注，不挂靠
            per_parent: 一条审稿意见最多收几条回复
            only_defects: 只写这一批（增量落盘用）；None = 写全部
        """
        from manuscript_review import mr_docx, mr_reviewer, mr_thread, mr_word

        if not project.defects:
            return False, "还没有缺陷可落盘，请先跑「确定性核验」或「语义审阅」", project
        ms = self._manuscript(project)
        if ms is None:
            return False, "尚未导入手稿", project

        # 增量落盘：只写这批新发现（其余已在稿上，重复写会产生重复批注）
        if only_defects is not None:
            defects = mr_reviewer.sort_defects(only_defects)
            if not defects:
                return True, "没有新增发现需要落盘", project
        else:
            defects = mr_reviewer.sort_defects(project.defects)

        # 底板：默认审阅用的 DOCX；指定了批注版则换用批注版
        merge_target = ""
        if merge_into:
            if not os.path.exists(merge_into):
                return False, f"批注版手稿不存在：{merge_into}", project
            merge_target = os.path.abspath(merge_into)
            src = merge_target
        else:
            src = project.docx_path
        if not src or not os.path.exists(src):
            return False, f"审阅用的 DOCX 不存在：{src}", project
        if not out_path:
            base = _safe_name(project.name)
            suffix = "_并入批注版.docx" if merge_target else "_审阅修订版.docx"
            out_path = os.path.join(exports_root(), f"{base}{suffix}")

        if not isinstance(project.applied, dict):
            project.applied = {}

        # ---- 计算「哪些发现挂到哪条审稿意见下」
        reply_pairs: list[tuple[int, dict]] = []
        merge_note = ""
        if merge_target and reply_mode == "reply":
            existing = mr_thread.read_existing(merge_target)
            if not existing:
                merge_note = "该文件没有审稿批注，已按独立批注处理。"
                project.add_log("apply", merge_note)
            else:
                plan = mr_thread.build_merge_plan(
                    defects, existing, manuscript=ms, per_parent=per_parent,
                    min_score=min_match)
                reply_pairs = [(r.parent_cid, r.finding) for r in plan.replies]
                project.applied["merge_plan"] = plan.to_dict()
                project.add_log(
                    "apply",
                    f"并入批注版：{len(existing)} 条审稿意见；"
                    f"挂靠回复 {len(plan.replies)} 条，独立批注 {len(plan.standalone)} 条")
                for n in plan.notes:
                    project.add_log("apply", n)
                merge_note = (f"并入审稿批注版：{len(plan.replies)} 条作为线程回复挂在"
                              f"{len(plan.to_dict()['parents_used'])} 条审稿意见下，"
                              f"另有 {len(plan.standalone)} 条作独立批注")
                by_cid = {c.cid: c for c in existing}
                for cid, f in reply_pairs:
                    c = by_cid.get(cid)
                    if c and c.para_idx:
                        f["_anchor_para"] = c.para_idx

        # 关键：必须把 reply_pairs 交给 build_plan，否则挂靠的发现会被当成普通批注写
        plan = mr_word.build_plan(ms, defects, mode=mode, max_insert=max_insert,
                                  reply_pairs=reply_pairs)
        project.add_log("apply", f"计划：{mr_word.summarize_plan(plan)}（模式 {mode}）")
        res = mr_word.apply_plan(src, out_path, plan, timeout=420)
        project.applied.update(res.to_dict())
        project.applied["reply_pairs"] = [
            {"parent": c, "title": (f or {}).get("title")} for c, f in reply_pairs]
        project.out_docx = res.out_path if res.ok else ""
        project.add_log("apply", ("成功：" if res.ok else "失败：")
                        + (res.error or f"批注 {res.comments_added} 条（其中回复 "
                                        f"{res.replies_added} 条）/ 修订 "
                                        f"{res.revisions_added} 处"))
        project.save()
        if not res.ok:
            return False, res.error or "落盘失败", project
        # 摘要口径：批注总数 = 独立批注 + 线程回复（两者都是 Word 批注）
        total_notes = (res.comments_added or 0) + (res.replies_added or 0)
        detail = f"独立批注 {res.comments_added} 条"
        if res.replies_added:
            detail += f" + 线程回复 {res.replies_added} 条"
        if res.revisions_added:
            detail += f"，正文修订 {res.revisions_added} 处"
        tail = f"；{merge_note}" if merge_note else ""
        return True, (f"已生成 Word：{res.out_path}"
                      f"（批注共 {total_notes} 条：{detail}）{tail}"), project

    # -- 一键全流程（自主落盘） ----------------------------------------------
    def run_all(self, path: str, layers: list[str] | None = None,
                mode: str = "dual", use_cache: bool = True,
                max_batches: int = 0, skip_llm: bool = False,
                autonomy: str = "auto", merge_into: str = "",
                reply_mode: str = "reply", per_parent: int = 4,
                fresh: bool = True, design=None, project: ReviewProject | None = None,
                on_step=None
                ) -> tuple[bool, str, ReviewProject]:
        """导入 → 核验 → 语义审阅 → 自主落 Word 批注 → 报告。

        autonomy 决定「写到什么程度」（都不需要人再点一步）：
            report  只出报告，不碰 Word
            comment 自主把发现写成 Word 批注（不增删正文）
            revise  自主写批注 **并** 用 Track Changes 补写缺失报告项（默认推荐）
            auto    等同 revise；但若两层审阅都没成功，自动降级为 comment
        merge_into 给定时，发现会作为**线程回复**并入该审稿批注版。

        fresh: True（默认）—— 这是**一次完整的新审阅**，清空「已入稿」记录后
               重新把全部发现写进 Word（重跑同一稿件时用它，结果可完全复现）。
               False —— **增量追加**：只把本次新报出的发现写到已有修订稿上，
               适合"先审确定性核验、再补一轮语义审阅"的分步用法。
        project: 当前已有的审阅项目。给了它就在**同一份项目上继续**，
               从而沿用该项目已设定的：审稿批注版（annotated_path）、
               上一次的修订稿/报告路径、课题关联、落盘模式等。
               早先这里无条件新建空白项目，导致「一键审阅」与用户刚导入的项目脱节。
        on_step(step, msg) 用于界面进度。
        """

        def step(name: str, msg: str):
            if on_step:
                on_step(name, msg)

        # 复用已有项目时跳过重复解析：同一份稿子已经解析过，没必要再读一遍
        # （也避免 outline/signals 被无谓重置）
        reusable = (project is not None and project.manuscript
                    and project.source_path
                    and os.path.abspath(project.source_path) == os.path.abspath(path))
        if reusable:
            p = project
            p.add_log("ingest", f"复用已导入的手稿「{p.name}」"
                                f"（{os.path.basename(path)}）")
            step("ingest", f"复用当前项目已导入的手稿：{p.name}"
                           f"（{len((p.manuscript or {}).get('body') or [])} 段，无需重新解析）")
        else:
            ok, msg, p = self.ingest(path, design=design)
            step("ingest", msg)
            if not ok:
                return False, msg, p
        if fresh:
            # 新审阅：重置落盘记录，让这次结果从零写全（不残留上一轮的指纹）
            p.applied_keys = []
            p.add_log("apply", "全新审阅：已重置落盘记录（将完整写入全部发现）")

        ok, msg, p = self.run_signals(p)
        step("signals", msg)
        if not ok:
            return False, msg, p

        llm_ok = False
        if not skip_llm:
            llm_ok, msg, p = self.run_review(p, layers=layers,
                                             use_cache=use_cache,
                                             max_batches=max_batches)
            step("review", msg)
            if not llm_ok:
                p.add_log("review", "语义审阅未成功，本次仅落确定性缺陷")
        else:
            p.defects = [d for d in p.defects if d.get("source") == "signal"]
            p.save()
            step("review", "已跳过语义审阅（只落确定性核验结论）")

        # ---- 自主落盘：不等人工点击
        eff = autonomy
        if eff == "auto":
            eff = "revise"
        if eff not in ("report", "comment", "revise"):
            eff = "revise"
        if not p.defects:
            step("apply", "本次没有报出缺陷，跳过 Word 落盘")
        elif eff == "report":
            step("apply", "按 autonomy=report：只出报告，未写入 Word")
        else:
            # revise 需要至少一层审阅成功；否则降级为 comment（只挂批注，不动正文）
            if eff == "revise" and not (llm_ok or p.signal_summary.get("total")):
                eff = "comment"
            ok2, msg2, p = self.review_to_word(
                p, autonomy=eff, merge_into=merge_into or p.annotated_path,
                reply_mode=reply_mode, per_parent=per_parent)
            step("apply", msg2)
            p.add_log("apply", f"自动落盘（autonomy={eff}）："
                               + ("成功" if ok2 else "失败"))

        ok, msg, p = self.build_report(p)
        step("report", msg)
        # 落盘/报告都完成后，再刷新一次课题附件记录（此时缺陷数与产出文件才是最终的）
        if design is not None:
            self._register_attachment(p, design)
        p.save()
        # 整体成功判定：报告出了就算流程完成（Word 失败已在 step 里说明）
        return bool(p.out_docx) or eff == "report", msg, p

    # -- 自主落盘（审阅流程的最后一环，不需要人工触发） ----------------------
    def review_to_word(self, project: ReviewProject, autonomy: str = "revise",
                       merge_into: str = "", reply_mode: str = "reply",
                       per_parent: int = 4, force: bool = False
                       ) -> tuple[bool, str, ReviewProject]:
        """把本次审阅的发现自主写进 Word。

        与 apply_to_word 的区别：这里面向「审阅完就自动落」的场景，
        负责三件事：
            ① 决定写多少（autonomy: comment / revise）
            ② 决定写到哪份文件（有审稿批注版就并入它，否则写审阅稿副本）
            ③ 记录「哪些发现已入稿」，避免同一批发现反复写、重复挂批注

        autonomy:
            comment  只挂批注（不增删正文），适合还在改结构的阶段
            revise   批注 + 用 Track Changes 补写缺失报告项（默认，最完整）
        """
        mode = "comment_only" if autonomy == "comment" else "dual"

        # 已入稿的发现不重复写（增量落盘：跑第二次只写新增结论）
        pending = project.defects or []
        if project.applied_keys and not force:
            done = set(project.applied_keys)
            pending = [d for d in pending if _finding_key(d) not in done]
        if not pending:
            return True, (f"没有新增发现需要落盘"
                          f"（已入稿 {len(project.applied_keys)} 条）"), project

        ok, msg, project = self.apply_to_word(
            project, mode=mode, merge_into=merge_into, reply_mode=reply_mode,
            per_parent=per_parent, only_defects=pending)
        if ok:
            done = set(project.applied_keys or [])
            done.update(_finding_key(d) for d in pending)
            project.applied_keys = sorted(done)
            project.applied_at = time.strftime("%Y-%m-%d %H:%M")
            if merge_into:
                project.annotated_path = os.path.abspath(merge_into)
            project.save()
        return ok, msg, project

    # -- 内部 ---------------------------------------------------------------
    def _manuscript(self, project: ReviewProject):
        from manuscript_review.mr_docx import Manuscript, Paragraph
        d = project.manuscript or {}
        if not d.get("body"):
            # 内存里没正文（项目是从精简 JSON 读出来的）→ 重新解析
            if project.docx_path and os.path.exists(project.docx_path):
                from manuscript_review import mr_docx
                ms = mr_docx.load(project.docx_path)
                project.manuscript = ms.to_dict()
                return ms
            return None
        ms = Manuscript(path=d.get("path", ""), fmt=d.get("fmt", "docx"),
                        title=d.get("title", ""), word_count=d.get("word_count", 0),
                        warnings=list(d.get("warnings") or []),
                        converted_from=d.get("converted_from", ""))
        for item in d["body"]:
            ms.paragraphs.append(Paragraph(
                idx=item.get("idx", 0), text=item.get("text", ""),
                chapter=item.get("chapter", "other"), style=item.get("style", ""),
                para_id=item.get("para_id", ""),
                is_heading=bool(item.get("is_heading")),
                runs=item.get("runs", 1), char_len=item.get("char_len", 0)))
        ms.chapters = {}
        for p in ms.paragraphs:
            ms.chapters.setdefault(p.chapter, []).append(p.idx)
        return ms


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                              # noqa: BLE001
        pass
    print("项目目录：", projects_root())
    print("导出目录：", exports_root())
    print("已有项目：")
    for x in ReviewProject.list_all():
        print(f"  {x['name']} · 缺陷 {x['defects']} · 更新 {x['updated']}")
