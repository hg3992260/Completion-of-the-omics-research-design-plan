# -*- coding: utf-8 -*-
"""组学研究设计工作台 —— MCP 服务器（stdio）。

把工作台的能力暴露成 agent 可调用的 MCP 工具，分四层：
    1. 知识层：十阶段标准流程、规范条目（不需要网络）
    2. 领域层：追问 / 改写 / 汇总三个 agent 环节 + 项目读写（走 DeepSeek）
    3. 通道层：llm_chat / llm_models 原样透传，agent 可把本服务当 LLM 网关用
    4. 手稿审阅层：导入 PDF/Word 手稿，按「引导式组学 / 统计 / 撰写」三层架构
       逐条对照找缺陷，并把缺陷落回 Word（原生批注 + 四色 Track Changes 修订）

运行（stdio）：
    D:\\python\\envs\\mar\\python.exe mcp_server.py
    # 或指定模型：--model deepseek-flash

注册到 MCP 客户端（DSH / Claude Desktop 的 mcpServers 段）：
    {
      "mcpServers": {
        "radiomics-workbench": {
          "command": "D:\\\\python\\\\envs\\\\mar\\\\python.exe",
          "args": ["I:\\\\文件\\\\CTCC\\\\HL\\\\omics_pipeline\\\\mcp_server.py"]
        }
      }
    }
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from design_agent import (Project, DesignAgent, parse_sections, pick,
                          parse_questions, parse_checklist, q_text)
from llm_client import LLMClient, load_config
from stages_data import STAGES
from app_paths import APP_VERSION

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:                                                # pragma: no cover
    sys.stderr.write("缺少 mcp 包：pip install mcp\n")
    raise

mcp = FastMCP("pcliomics-workbench")
# FastMCP 未暴露 version 参数：直接设置底层 Server 的版本，让 MCP 握手带上它
try:
    mcp._mcp_server.version = APP_VERSION
except Exception:  # noqa: BLE001
    pass
_client: LLMClient | None = None
_model_override: str | None = None


def client() -> LLMClient:
    global _client
    if _client is None:
        cfg = load_config()
        if _model_override:
            cfg["model"] = _model_override
        _client = LLMClient(cfg)
    return _client


def _find_project(name_or_path: str) -> Project | None:
    if not name_or_path:
        return None
    if os.path.exists(name_or_path):
        return Project.load(name_or_path)
    if not name_or_path.endswith(".json") and os.path.exists(name_or_path + ".json"):
        return Project.load(name_or_path + ".json")
    target = name_or_path.strip()
    for meta in Project.list_all():
        if meta["name"] == target or os.path.basename(meta["path"]) == target:
            return Project.load(meta["path"])
    return None


# --------------------------------------------------------------------- 知识层
@mcp.tool()
def list_stages() -> str:
    """列出十阶段标准流程：编号、名称、规范出处、必做动作、必报参数、常见缺陷。"""
    rows = []
    for s in STAGES:
        rows.append({
            "id": s["id"], "title": s["title"], "spec": s["spec"],
            "goal": s["goal"], "actions": s["actions"], "reports": s["reports"],
            "pitfalls": s["pitfalls"], "refs": s["refs"],
        })
    return json.dumps(rows, ensure_ascii=False, indent=1)


@mcp.tool()
def llm_models() -> str:
    """列出当前 LLM 后端可用的模型，以及正在使用的模型与端点。"""
    c = client()
    return json.dumps({"current": c.model, "base_url": c.base_url,
                       "models": c.list_models()}, ensure_ascii=False)


# --------------------------------------------------------------------- 领域层
@mcp.tool()
def design_ask(stage: int, raw_design: str, project: str = "") -> str:
    """对一个实验设计做第 stage 阶段的「追问」：返回现状评估、必须澄清的问题、小结。

    Args:
        stage: 阶段编号 1-10
        raw_design: 研究者的初步实验设计描述
        project: 可选，已有项目名或路径（会带上该项目已定稿阶段的摘要作为上下文）
    """
    proj = _find_project(project) or Project(name="mcp-session", raw_design=raw_design)
    if raw_design.strip():
        proj.raw_design = raw_design
    agent = DesignAgent(client(), proj)
    out = agent.run(agent.ask_messages(stage))
    sec = parse_sections(out["content"])
    return json.dumps({
        "stage": stage,
        "assessment": pick(sec, "现状评估"),
        "questions": parse_questions(pick(sec, "必须澄清", "问题")),
        "summary": pick(sec, "本阶段小结"),
        "model": out.get("model"), "elapsed": round(out["elapsed"], 1),
        "raw": out["content"],
    }, ensure_ascii=False, indent=1)


@mcp.tool()
def design_rewrite(stage: int, raw_design: str, answers: str,
                   project: str = "", save_final: bool = False) -> str:
    """在拿到研究者回答后产出第 stage 阶段的「改写稿 + 检查表 + 风险提示」。

    Args:
        stage: 阶段编号 1-10
        raw_design: 研究者的初步实验设计描述
        answers: 对追问的回答，多问用换行分隔（可写"不确定"）
        project: 可选，已有项目名或路径
        save_final: 为 True 时把改写稿写回项目并标记该阶段已完成
    """
    proj = _find_project(project)
    if proj is None:
        proj = Project(name="mcp-session", raw_design=raw_design)
    if raw_design.strip():
        proj.raw_design = raw_design

    st = proj.stage(stage)
    if not st.get("questions"):
        st["questions"] = []
    lines = [a.strip() for a in (answers or "").splitlines() if a.strip()]
    base = parse_questions(pick(parse_sections(proj.raw_design), "问题")) if False else []
    st["answers"] = lines
    if not st["questions"]:
        st["questions"] = [f"研究者补充说明 {i + 1}" for i in range(len(lines))]

    agent = DesignAgent(client(), proj)
    out = agent.run(agent.rewrite_messages(stage))
    sec = parse_sections(out["content"])
    draft = pick(sec, "改写稿")
    checklist = parse_checklist(pick(sec, "检查表"))
    st["draft"] = draft
    st["risks"] = pick(sec, "风险提示")
    st["checklist"] = checklist
    st["status"] = "done" if save_final else "drafted"
    if save_final:
        st["final"] = draft
    import time as _t
    st["updated"] = _t.strftime("%H:%M")
    saved = ""
    if project or save_final:
        saved = proj.save()
    return json.dumps({
        "stage": stage, "draft": draft, "checklist": checklist,
        "risks": st["risks"], "next": pick(sec, "下一步"),
        "saved_to": saved, "status": st["status"],
        "model": out.get("model"), "elapsed": round(out["elapsed"], 1),
    }, ensure_ascii=False, indent=1)


@mcp.tool()
def design_finalize(project: str, raw_design: str = "") -> str:
    """把项目已定稿的阶段整合成完整研究设计草案 + 待补数据清单 + 投稿前自查。"""
    proj = _find_project(project)
    if proj is None:
        return json.dumps({"error": f"找不到项目：{project}"}, ensure_ascii=False)
    if raw_design.strip():
        proj.raw_design = raw_design
    agent = DesignAgent(client(), proj)
    out = agent.run(agent.finalize_messages(), max_tokens=14000)
    sec = parse_sections(out["content"])
    proj.final_doc = pick(sec, "设计草案") or out["content"]
    proj.save()
    return json.dumps({"draft": proj.final_doc,
                       "missing_data": pick(sec, "待补数据"),
                       "self_check": pick(sec, "投稿前自查"),
                       "saved_to": proj.path}, ensure_ascii=False, indent=1)


# --------------------------------------------------------------------- 项目层
@mcp.tool()
def list_projects() -> str:
    """列出全部项目：名称、完成度、更新时间、文件大小、模型。"""
    return json.dumps(Project.list_all(), ensure_ascii=False, indent=1)


@mcp.tool()
def create_project(name: str, raw_design: str = "") -> str:
    """新建项目（立即落盘），返回项目信息。"""
    p = Project.new(name, raw=raw_design, model=client().model)
    return json.dumps({"name": p.name, "path": p.path, "created": p.created},
                      ensure_ascii=False, indent=1)


@mcp.tool()
def project_overview(project: str) -> str:
    """项目的十阶段状态表（等价于界面上的"管线视图 · 评分与检查表"）。

    Args:
        project: 项目名或项目 JSON 路径
    """
    p = _find_project(project)
    if p is None:
        return json.dumps({"error": f"找不到项目：{project}"}, ensure_ascii=False)
    tone = {"done": "绿-已完成", "drafted": "黄-待采纳", "asked": "黄-已追问", "todo": "红-未开始"}
    rows = []
    for s in STAGES:
        st = p.stage(s["id"])
        state = st.get("status", "todo")
        final = (st.get("final") or "").strip()
        rows.append({
            "id": f"{s['id']:02d}", "stage": s["title"], "spec": s["spec"],
            "status": tone.get(state, state),
            "result": (f"定稿：{final[:60]}" if final else
                       ("已有改写稿待采纳" if st.get("draft") else
                        ("已追问，等待回答" if state == "asked" else "尚未开始"))),
            "checklist": len(st.get("checklist") or []),
            "updated": st.get("updated") or "",
        })
    counts = p.status_counts()
    return json.dumps({"project": p.name, "path": p.path, "raw_len": len(p.raw_design),
                       "summary": {"done": counts["done"], "drafted": counts["drafted"],
                                   "asked": counts["asked"], "todo": counts["todo"]},
                       "rows": rows}, ensure_ascii=False, indent=1)


@mcp.tool()
def project_get_stage(project: str, stage: int) -> str:
    """读取项目某一阶段的完整内容（评估、问答、改写稿、检查表、风险提示、定稿）。"""
    p = _find_project(project)
    if p is None:
        return json.dumps({"error": f"找不到项目：{project}"}, ensure_ascii=False)
    st = p.stage(stage)
    return json.dumps({**st, "questions": [q_text(q) for q in st.get("questions", [])]},
                      ensure_ascii=False, indent=1)


@mcp.tool()
def project_set_stage(project: str, stage: int, status: str = "",
                      final: str = "", checklist: str = "") -> str:
    """写回某阶段：状态（todo/asked/drafted/done）、定稿正文、检查表（换行分隔）。"""
    p = _find_project(project)
    if p is None:
        return json.dumps({"error": f"找不到项目：{project}"}, ensure_ascii=False)
    st = p.stage(stage)
    if status:
        st["status"] = status
    if final:
        st["final"] = final
    if checklist:
        st["checklist"] = [c.strip() for c in checklist.splitlines() if c.strip()]
    import time as _t
    st["updated"] = _t.strftime("%H:%M")
    path = p.save()
    return json.dumps({"ok": True, "project": p.name, "stage": stage,
                       "status": st.get("status"), "saved_to": path}, ensure_ascii=False)


@mcp.tool()
def export_markdown(project: str) -> str:
    """把项目导出为 Markdown 文件，返回文件路径。"""
    p = _find_project(project)
    if p is None:
        return json.dumps({"error": f"找不到项目：{project}"}, ensure_ascii=False)
    from app_paths import export_dir
    path = os.path.join(export_dir(), f"研究设计_{p.name}.md")   # 用户可见目录
    open(path, "w", encoding="utf-8").write(p.render_doc())
    return json.dumps({"path": path, "chars": os.path.getsize(path)},
                      ensure_ascii=False)


@mcp.tool()
def export_docx(project: str) -> str:
    """把项目导出为 Word（.docx）：标题层级 + 检查表表格，适合伦理申请/论文附件。

    Args:
        project: 项目名或项目 JSON 路径
    """
    p = _find_project(project)
    if p is None:
        return json.dumps({"error": f"找不到项目：{project}"}, ensure_ascii=False)
    from app_paths import export_dir
    import docx_export
    path = os.path.join(export_dir(), f"研究设计_{p.name}.docx")
    try:
        path = docx_export.build(p, path)
    except Exception as e:                                         # noqa: BLE001
        return json.dumps({"error": f"导出 Word 失败：{e}"}, ensure_ascii=False)
    return json.dumps({"path": path, "bytes": os.path.getsize(path)}, ensure_ascii=False)


# --------------------------------------------------------------------- 手稿审阅层
# 一次会话里保留「当前审阅项目」，让 review / defects / apply 能接着上一步做。
_MR = {"project": None, "busy": False}
_MR_LOCK = threading.Lock()


def _mr_engine():
    from manuscript_review.mr_engine import RevEngine
    try:
        c = client()
    except Exception:                                              # noqa: BLE001
        c = None
    return RevEngine(c)


def _mr_load(name_or_path: str):
    """按项目名 / 路径 / 内存当前项目解析出一个 ReviewProject。"""
    from manuscript_review.mr_engine import ReviewProject
    if not name_or_path:
        return _MR["project"]
    if os.path.exists(name_or_path):
        return ReviewProject.load(name_or_path)
    stem = name_or_path.strip()
    for meta in ReviewProject.list_all():
        if meta["name"] == stem or os.path.basename(meta["path"]) == stem or \
                os.path.basename(meta["path"]) == stem + ".json":
            return ReviewProject.load(meta["path"])
    return _MR["project"]


@mcp.tool()
def manuscript_layers() -> str:
    """列出「手稿缺陷审阅」的三层审阅条目统计（组学 / 统计 / 撰写）。

    三层条目全部派生自本工作台已有的权威数据：
        组学 = stages_data.STAGES（十阶段 · TRIPOD+AI / CLEAR / METRICS / IBSI）
        统计 = stat_data.STAGES（9 阶段）
        撰写 = shape_data.SHAPE（Glasman-Deal 七章通用模型）
    """
    from manuscript_review.mr_review_layers import LAYERS, LAYER_ORDER, stats
    st = stats()
    return json.dumps({"layers": [
        {"key": k, "name": LAYERS[k]["name"], "sub": LAYERS[k]["sub"],
         "why": LAYERS[k]["why"], **{kk: vv for kk, vv in st[k].items()}}
        for k in LAYER_ORDER], "total": st["total"]}, ensure_ascii=False, indent=1)


@mcp.tool()
def manuscript_review(path: str, layers: str = "omics,stat,shape",
                      skip_llm: bool = False, max_batches: int = 0,
                      autonomy: str = "revise", merge_into: str = "",
                      reply_mode: str = "reply", per_parent: int = 4,
                      incremental: bool = False,
                      reuse_current: bool = True) -> str:
    """导入手稿（PDF / Word）→ 三层架构对照找缺陷 → **自主把批注写进 Word** → 出报告。

    这是「一条命令跑完整审阅」的入口：跑完即得到带批注（及可选修订）的 Word，
    不需要再单独调用落盘工具。PDF 会先转成 DOCX 转换稿，审阅与修订都作用于转换稿。

    Args:
        path: 手稿路径（.pdf / .docx）
        layers: 要审的层，逗号分隔，取值 omics / stat / shape
        skip_llm: True 时只跑确定性核验（不联网、不花钱，可证据化的硬缺陷照样报）
        max_batches: >0 时每层最多跑多少批 LLM（调试用）
        autonomy: **自主落盘程度** —— 审阅跑完自动写到什么程度
            revise  = 批注 + 用 Track Changes 补写缺失报告项（默认，最完整）
            comment = 只挂批注，不增删正文（结构还在调整时用）
            report  = 只出报告，完全不碰 Word
        merge_into: 「审稿批注版」路径。给了它就以该文件为底板，
            匹配得上的发现作为**线程回复**挂到审稿意见下面（保留审稿人原批注不动）
        reply_mode: reply（默认，线程回复）/ standalone（只做独立批注）
        per_parent: 一条审稿意见最多收几条回复
        incremental: True 时只把本次新报出的发现写到已有修订稿（默认每次完整重写）
        reuse_current: True（默认）时，若本次 path 与上一次审阅**是同一份手稿**，
            就在同一个项目上继续，沿用它已设定的审稿批注版与落盘路径，
            并跳过重复解析。稿件不同则自动不复用，避免两份手稿的结论混在一起。
        incremental: True 时只把本次新报出的发现写到已有修订稿（默认每次完整重写）
    """
    if _MR["busy"]:
        return json.dumps({"ok": False, "error": "已有审阅任务在进行中"}, ensure_ascii=False)
    with _MR_LOCK:
        _MR["busy"] = True
    try:
        eng = _mr_engine()
        lay = [x.strip() for x in (layers or "").split(",") if x.strip()] or None
        steps = []
        # reuse_current：长驻会话里对**同一份稿子**再跑时，复用已导入的项目，
        # 从而沿用它已设定的审稿批注版与上一次的落盘路径，不必重新解析。
        # 稿件不同则不复用（避免把两份手稿的结论混在一个项目里）。
        prev = _MR.get("project") if reuse_current else None
        if prev is not None and os.path.abspath(getattr(prev, "source_path", "") or "x") \
                != os.path.abspath(path):
            prev = None
        ok, msg, proj = eng.run_all(
            path, layers=lay, skip_llm=skip_llm, max_batches=max_batches,
            autonomy=autonomy, merge_into=merge_into, reply_mode=reply_mode,
            per_parent=per_parent, fresh=not incremental, project=prev,
            on_step=lambda s, m: steps.append({"step": s, "msg": m}))
        _MR["project"] = proj
        ap = proj.applied or {}
        return json.dumps({
            "ok": bool(proj.out_docx) or autonomy == "report",
            "steps": steps,
            "project": proj.name, "project_path": proj.path(),
            "autonomy": autonomy,
            "reused_project": prev is not None,
            "converted": proj.converted, "docx_path": proj.docx_path,
            "outline": proj.outline,
            "signal_summary": proj.signal_summary,
            "summary": proj.summary,
            "out_docx": proj.out_docx,
            "report_path": proj.report_path,
            "comments_added": ap.get("comments_added"),
            "replies_added": ap.get("replies_added"),
            "revisions_added": ap.get("revisions_added"),
            "merge_plan": ap.get("merge_plan"),
            "threading": ap.get("threading"),
            "applied_keys": len(proj.applied_keys or []),
            "defects": _mr_defect_rows(proj.defects),
            "warnings": proj.warnings,
        }, ensure_ascii=False, indent=1)
    finally:
        with _MR_LOCK:
            _MR["busy"] = False


def _mr_defect_rows(defects: list, limit: int = 0) -> list[dict]:
    rows = []
    for d in (defects or []):
        rows.append({
            "severity": d.get("severity"), "layer": d.get("layer"),
            "ref": d.get("ref"), "spec": d.get("spec"),
            "title": d.get("title"), "why": d.get("why"),
            "evidence": (d.get("evidence") or "")[:200],
            "suggestion": d.get("suggestion"),
            "para_idx": d.get("para_idx"), "chapter": d.get("chapter"),
            "source": d.get("source"), "req_id": d.get("req_id"),
        })
    return rows[:limit] if limit else rows


@mcp.tool()
def manuscript_defects(project: str = "", layer: str = "", severity: str = "",
                       limit: int = 0) -> str:
    """查询当前（或指定）审阅项目的缺陷清单，可按层与严重度过滤。

    Args:
        project: 项目名或项目 JSON 路径；留空=用本会话最近一次审阅结果
        layer: omics / stat / shape，留空=全部
        severity: 关键 / 主要 / 一般，留空=全部
        limit: 最多返回多少条（0=全部）
    """
    p = _mr_load(project)
    if p is None:
        return json.dumps({"ok": False,
                           "error": "没有审阅项目，请先调用 manuscript_review"},
                          ensure_ascii=False)
    ds = p.defects or []
    if layer:
        ds = [d for d in ds if d.get("layer") == layer]
    if severity:
        ds = [d for d in ds if d.get("severity") == severity]
    return json.dumps({
        "ok": True, "project": p.name,
        "summary": p.summary, "signal_summary": p.signal_summary,
        "returned": len(ds), "defects": _mr_defect_rows(ds, limit),
    }, ensure_ascii=False, indent=1)


@mcp.tool()
def manuscript_annotated_info(path: str) -> str:
    """探测一份手稿是否带**审稿批注**（决定能否做「线程回复」并入）。

    返回批注条数、作者、以及每条批注锚定在第几段。
    要并入线程回复时，先用它确认目标文件选对了。
    """
    from manuscript_review import mr_thread
    if not os.path.exists(path):
        return json.dumps({"ok": False, "error": f"文件不存在：{path}"},
                          ensure_ascii=False)
    info = mr_thread.probe(path)
    return json.dumps({"ok": True, **info}, ensure_ascii=False, indent=1)


@mcp.tool()
def manuscript_apply(project: str = "", mode: str = "dual",
                     max_insert: int = 25, merge_into: str = "",
                     reply_mode: str = "reply", per_parent: int = 4) -> str:
    """把缺陷落回 Word：原生批注 + 四色 Track Changes 修订，返回生成的文件路径。

    两种产出方式：
        1. 独立批注（默认）：我们的发现作为新批注挂在手稿对应段落上。
        2. **并入审稿批注版**（给 merge_into）：以那份文件为底板，
           匹配得上的发现作为**线程回复**挂到审稿意见下面（Word 审阅窗格会嵌套显示），
           审稿人原有批注一个字都不动。

    每条批注写清：层次+严重度 / 规范条目 / 缺陷 / 证据 / 建议。
    正文修订四色：绿 00B050 增 · 红 FF0000 删 · 蓝 0070C0 改 · 橙 ED7D31 移。

    Args:
        project: 项目名或路径；留空=本会话最近一次
        mode: dual（批注+修订，默认）/ comment_only（只出批注，不碰正文）
        max_insert: 最多补写多少段（默认 25）
        merge_into: 「审稿批注版」手稿路径。给了它就并入该文件（线程回复）
        reply_mode: reply（默认，做线程回复）/ standalone（只做独立批注）
        per_parent: 一条审稿意见最多收几条回复（默认 4）
    """
    p = _mr_load(project)
    if p is None:
        return json.dumps({"ok": False,
                           "error": "没有审阅项目，请先调用 manuscript_review"},
                          ensure_ascii=False)
    eng = _mr_engine()
    ok, msg, p = eng.apply_to_word(p, mode=mode, max_insert=max_insert,
                                   merge_into=merge_into,
                                   reply_mode=reply_mode, per_parent=per_parent)
    _MR["project"] = p
    ap = p.applied or {}
    return json.dumps({"ok": ok, "msg": msg, "out_docx": p.out_docx,
                       "comments_added": ap.get("comments_added"),
                       "replies_added": ap.get("replies_added"),
                       "revisions_added": ap.get("revisions_added"),
                       "merge_plan": ap.get("merge_plan"),
                       "threading": ap.get("threading"),
                       "applied": ap}, ensure_ascii=False, indent=1)


@mcp.tool()
def manuscript_report(project: str = "") -> str:
    """生成审阅报告：Markdown + HTML + 缺陷清单 CSV，返回三者的路径。"""
    p = _mr_load(project)
    if p is None:
        return json.dumps({"ok": False,
                           "error": "没有审阅项目，请先调用 manuscript_review"},
                          ensure_ascii=False)
    eng = _mr_engine()
    ok, msg, p = eng.build_report(p)
    _MR["project"] = p
    d = os.path.dirname(p.report_path or "")
    stem = os.path.splitext(os.path.basename(p.report_path or ""))[0]
    return json.dumps({"ok": ok, "msg": msg, "markdown": p.report_path,
                       "html": os.path.join(d, stem + ".html") if d else "",
                       "csv": os.path.join(d, stem.replace("_审阅报告", "_缺陷清单")
                                           + ".csv") if d else ""},
                      ensure_ascii=False, indent=1)


@mcp.tool()
def manuscript_projects() -> str:
    """列出所有手稿审阅项目（名称、缺陷数、更新时间、修订稿路径）。"""
    from manuscript_review.mr_engine import ReviewProject
    return json.dumps(ReviewProject.list_all(), ensure_ascii=False, indent=1)


@mcp.tool()
def manuscript_toolchain() -> str:
    """手稿审阅的外部依赖就绪情况：OfficeCLI（Word 批注/修订）与 PDF 转换。"""
    from manuscript_review import mr_office, mr_pdf, mr_word
    return json.dumps({"officecli": mr_office.available(),
                       "pdf": mr_pdf.available(),
                       "revision_colors": {"新增": mr_word.C_NEW,
                                           "删除": mr_word.C_DEL,
                                           "修改": mr_word.C_MOD,
                                           "移动": mr_word.C_MOVE},
                       "python": sys.version.split()[0]},
                      ensure_ascii=False, indent=1)


# --------------------------------------------------------------------- 通道层
@mcp.tool()
def llm_chat(prompt: str, system: str = "", model: str = "",
             temperature: float = 0.4, max_tokens: int = 4000) -> str:
    """原样调用本服务背后的 LLM（默认 DeepSeek），用于任意问答。

    这样 agent 也可以把它当 LLM 网关用，而不只是领域工具。
    """
    c = client()
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    out = c.chat(msgs, temperature=temperature, max_tokens=max_tokens)
    return json.dumps({"content": out["content"], "model": out.get("model"),
                       "elapsed": round(out["elapsed"], 1),
                       "usage": out.get("usage")}, ensure_ascii=False)


def main() -> None:
    global _model_override
    ap = argparse.ArgumentParser(description="组学研究设计工作台 MCP 服务器")
    ap.add_argument("--model", default="", help="覆盖默认模型，如 deepseek-flash")
    ap.add_argument("--list-tools", action="store_true", help="打印工具清单后退出")
    ap.add_argument("--transport", default="stdio",
                    choices=["stdio", "streamable-http", "sse"],
                    help="stdio（默认，供 DSH/Claude Desktop 等本地 MCP 客户端使用）"
                         "或 streamable-http（供容器/远程客户端使用）")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    _model_override = args.model or None
    if args.list_tools:
        import asyncio
        tools = asyncio.run(mcp.list_tools())
        for t in tools:
            print(f"- {t.name}: {(t.description or '').splitlines()[0]}")
        return
    if args.transport == "stdio":
        mcp.run()                                          # stdio transport
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport=args.transport)


# ---------------------------------------------------------------------------
#  进程内战 streamable-http（方向 A 用）
#
#  背景：内嵌的 opencode 内核是 MCP 客户端，它要调用本程序的 21 个领域工具。
#  因此宿主 GUI 进程必须在跑界面的同时，把 MCP 端点暴露出来，内核通过
#  <config>/opencode.json 的 mcp 段以 type:"remote" 连过来。
#
#  可行性已实测：uvicorn 的 Server.capture_signals() 在非主线程会直接跳过信号
#  捕获，因此 `mcp.run(transport="streamable-http")` 可以在后台线程里正常起，
#  并返回正确的 MCP initialize 响应（见 _mcp_thread_probe.py）。
#
#  已知限制：FastMCP 未暴露底层 uvicorn Server 句柄，所以**无法在进程内优雅
#  停止**该端点。它随 GUI 进程存活，进程退出即随之结束 —— 这对"GUI 进程同时
#  暴露端点"的语义是合适的，也避免了一个端口被反复抢占/释放的竞态。
# ---------------------------------------------------------------------------

_http_lock = threading.Lock()
_http_state: dict = {"thread": None, "host": None, "port": None, "url": None, "error": None}


def _free_port(host: str = "127.0.0.1") -> int:
    import socket
    with socket.socket() as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def serve_http_in_thread(host: str = "127.0.0.1", port: int | None = None,
                         wait: float = 30.0, attempts: int = 5) -> dict:
    """在后台线程里起 streamable-http 端点，返回 {ok, url, port, ...}。

    幂等：已在运行则直接返回既有状态（不重复起第二个端点）。
    port 为空则自动挑一个空闲端口（避免与 web_server 8787 / api_server 8788 /
    mcp 默认 8765 冲突）。
    """
    with _http_lock:
        if _http_state.get("url") and _http_state.get("thread") \
                and _http_state["thread"].is_alive() and _port_open(_http_state["host"], _http_state["port"]):
            return {"ok": True, "already": True, "url": _http_state["url"],
                    "port": _http_state["port"], "host": _http_state["host"]}

    last_error: BaseException | None = None
    for _ in range(max(1, attempts)):
        chosen = port or _free_port(host)
        errors: list[BaseException] = []

        def _run() -> None:
            try:
                mcp.settings.host = host
                mcp.settings.port = chosen
                mcp.run(transport="streamable-http")
            except BaseException as e:                                 # noqa: BLE001
                errors.append(e)

        t = threading.Thread(target=_run, name="pcl-mcp-http", daemon=True)
        t.start()

        deadline = time.time() + wait
        while time.time() < deadline:
            if errors:
                last_error = errors[0]
                break
            if not t.is_alive():
                last_error = RuntimeError("MCP HTTP 线程提前退出")
                break
            if _port_open(host, chosen):
                url = f"http://{host}:{chosen}/mcp"
                with _http_lock:
                    _http_state.update({"thread": t, "host": host, "port": chosen,
                                        "url": url, "error": None})
                return {"ok": True, "already": False, "url": url,
                        "port": chosen, "host": host}
            time.sleep(0.3)

    with _http_lock:
        _http_state["error"] = f"{type(last_error).__name__}: {last_error}" if last_error else "超时"
    return {"ok": False, "error": _http_state["error"]}


def http_status() -> dict:
    """当前进程内 MCP 端点状态（只读，不启动任何东西）。"""
    st = dict(_http_state)
    thread = st.get("thread")
    st["thread"] = bool(thread and thread.is_alive())
    if st.get("port"):
        st["serving"] = _port_open(st["host"], st["port"])
    else:
        st["serving"] = False
    return st


def tool_count() -> int:
    """已注册的 MCP 工具数（自检用）。"""
    import asyncio
    try:
        return len(asyncio.run(mcp.list_tools()))
    except Exception:                                                  # noqa: BLE001
        return -1


if __name__ == "__main__":
    main()
