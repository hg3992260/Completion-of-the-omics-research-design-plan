# -*- coding: utf-8 -*-
"""组学研究设计工作台 —— MCP 服务器（stdio）。

把工作台的能力暴露成 agent 可调用的 MCP 工具，分三层：
    1. 知识层：十阶段标准流程、规范条目（不需要网络）
    2. 领域层：追问 / 改写 / 汇总三个 agent 环节 + 项目读写（走 DeepSeek）
    3. 通道层：llm_chat / llm_models 原样透传，agent 可把本服务当 LLM 网关用

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


if __name__ == "__main__":
    main()
