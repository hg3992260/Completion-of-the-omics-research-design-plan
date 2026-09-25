# -*- coding: utf-8 -*-
"""组学研究设计工作台 · Web 版内核（Phase 0 打通验证）。

为什么有这个东西
----------------
GUI 依赖 PySide6 / Qt 6，而 Qt 6 官方只支持 Windows 10 1809+ 与 Windows 11；
Windows 7 上连"内嵌浏览器"也走不通（WebView2 Runtime 109 是最后一个支持 Win7 的版本，
2023-01 之后不再更新，SDK 1.0.1519.0+ 直接不支持 Win7）。因此在 Win7 上唯一能拿到
现代界面的形态是：**本地起一个 HTTP 服务，用系统里已有的浏览器打开**。

设计口径（Phase 0）
------------------
* 业务逻辑一行不改：项目读写用 ``design_agent.Project``、收敛推理用
  ``DesignAgent`` + ``LLMClient``、进度统计用 ``coupling``、勾选/状态用 ``scope_core``。
* 纯标准库 + Python 3.8 兼容（Win7 上只能跑 Python 3.8）。
* 默认只绑 127.0.0.1，不对外网开放；需要局域网共享时显式 ``--host 0.0.0.0``。

路由
----
    GET  /                     单页界面（web/index.html）
    GET  /static/<file>        界面静态资源
    GET  /api/health           健康检查
    GET  /api/state[?project=] 整份界面状态（项目列表 + 十阶段完整内容 + 三条工作线 + 九阶段/七章 + 收敛结论）
    GET  /api/scope?page=&key= 一个 scope 环节的完整内容（结构内容）+ 当前状态与自检勾选（引导完善）
    GET  /api/export?fmt=md    导出 Markdown（无依赖）/ Word（需要 python-docx）→ 浏览器下载
    POST /api/project/new      新建空白项目
    POST /api/project/rename   项目改名
    POST /api/project/delete   删除项目
    POST /api/kickoff          速读研究设想（SSE 流式，结果记入对话记录）
    POST /api/stage/ask        十阶段追问（SSE 流式）
    POST /api/stage/answers    只保存研究者的回答
    POST /api/stage/rewrite    改写稿 + 检查表 + 风险提示（SSE 流式）
    POST /api/stage/save       保存编辑内容 / 采纳定稿
    POST /api/finalize         汇总完整设计草案（SSE 流式）
    POST /api/scope/ask        scope 环节追问（SSE 流式）
    POST /api/scope/rewrite    scope 定稿 + 自检判定（SSE 流式）
    POST /api/scope/answers    只保存 scope 回答
    POST /api/scope/save       保存 scope 编辑 / 勾选自检 / 采纳定稿（会自动按检查表勾选）
    POST /api/convergence      收敛推理（SSE 流式）

所有会改数据或调用模型的接口，成功时都会在 ``done`` 事件里回传整份 ``state``，
前端因此不需要做局部状态同步 —— 收到就整体重绘。

运行
----
    python web_server.py                     # 默认 127.0.0.1:8787，自动开浏览器
    python web_server.py --port 8899 --no-browser
    python web_server.py --browser "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from app_paths import APP_VERSION, app_home, is_frozen, resource_path   # noqa: E402

import coupling                                                    # noqa: E402
import scope_core                                                  # noqa: E402
import shape_data                                                  # noqa: E402
import stat_data                                                   # noqa: E402
from design_agent import (DesignAgent, Project, parse_checklist,    # noqa: E402
                          parse_convergence, parse_questions, parse_sections, pick)
from llm_client import LLMClient, load_config, mask                 # noqa: E402
from stages_data import STAGES                                      # noqa: E402

APP_TITLE = "组学研究设计工作台 · Web 预览版"
DEFAULT_PORT = 8787
PORT_TRIES = 12

STATIC_EXT = (".html", ".css", ".js", ".svg", ".png", ".ico", ".woff2", ".json", ".map")
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
        ".woff2": "font/woff2", ".map": "application/json; charset=utf-8"}

STATE = {"client": None, "started": time.time(), "verb": False}
RUN_LOCK = threading.Lock()          # 收敛推理单飞：同时只允许一次


# --------------------------------------------------------------------------- 数据
def web_dir() -> str:
    """界面资源目录（源码运行 / 冻结后都适用）。"""
    for cand in (resource_path("web"), os.path.join(HERE, "web")):
        if cand and os.path.isdir(cand):
            return cand
    return os.path.join(HERE, "web")


def client() -> LLMClient:
    if STATE["client"] is None:
        STATE["client"] = LLMClient(load_config())
    return STATE["client"]


def llm_info() -> dict:
    c = client()
    return {"model": c.model, "base_url": c.base_url,
            "key": mask(c.cfg.get("api_key", "")),
            "key_source": c.cfg.get("key_source", "none"),
            "ready": bool(c.cfg.get("api_key"))}


def resolve_project(sel: str):
    """按名字 / 文件名 / 完整路径找到项目。

    ★ 只在 sel 为空时才回退到"最近更新的那个" —— 指名要找却找不到时必须返回 None，
      否则「删除不存在的课题」会误删第一个项目。
    """
    sel = (sel or "").strip()
    metas = Project.list_all()
    if sel:
        if os.path.isfile(sel):
            try:
                return Project.load(sel)
            except Exception:                                      # noqa: BLE001
                return None
        base = os.path.basename(sel)
        for m in metas:
            if m["name"] == sel or os.path.basename(m["path"]) == base:
                try:
                    return Project.load(m["path"])
                except Exception:                                  # noqa: BLE001
                    continue
        return None
    if metas:
        try:
            return Project.load(metas[0]["path"])
        except Exception:                                          # noqa: BLE001
            return None
    return None


def _scope_rows(store: dict, data: list) -> list:
    rows = []
    for s in data:
        got, total = scope_core.progress(store, s)
        node = (store or {}).get(s["key"]) or {}
        rows.append({
            "id": s["id"], "key": s["key"], "title": s["title"],
            "spec": s.get("spec", ""), "desc": (s.get("desc") or s.get("goal") or "")[:200],
            "icon": s.get("icon", ""), "cat": s.get("cat", ""),
            "state": scope_core.state(store, s),
            "state_label": scope_core.STATUS_LABEL.get(scope_core.state(store, s), ""),
            "guide": scope_core.guide_status(store, s["key"]),
            "guide_label": scope_core.GUIDE_STATUS.get(scope_core.guide_status(store, s["key"]), ""),
            "checks_done": got, "checks_total": total,
            "has_final": bool((node.get("final") or "").strip()),
            "draft_len": len((node.get("draft") or "").strip()),
            "final_len": len((node.get("final") or "").strip()),
            "questions": len(node.get("questions") or []),
        })
    return rows


def scope_payload(page: str, key: str, project) -> dict:
    """一个 scope 环节的完整内容（结构内容模式）+ 当前状态（引导模式）。

    引导式对话的一切都由**该环节的规范内容**驱动：把 section 整段回传，
    前端"结构内容"页直接展示它，"引导完善"页把它作为追问/定稿的依据。
    """
    data = stat_data.STAGES if page == "stat" else shape_data.SHAPE
    sec = next((s for s in data if s["key"] == key), None) or data[0]
    store = (project.stat if page == "stat" else project.shape) or {}
    node = scope_core.node(store, sec["key"])
    got, total = scope_core.progress(store, sec)
    section = {k: v for k, v in sec.items() if k != "checks"}
    cat = stat_data.CATS.get(sec.get("cat", ""), {}) if page == "stat" else {}
    extra = {}
    if page == "stat" and sec.get("id") == 6:            # 「检验计算」阶段附速查表
        extra = {"cheatsheet": [list(r) for r in stat_data.CHEATSHEET],
                 "test_kinds": list(stat_data.TEST_KINDS)}
    out = {
        "ok": True, "page": page, "key": sec["key"],
        "section": section, "cat": cat,
        "checks": list(sec.get("checks") or []),
        "checked": scope_core.checked(store, sec["key"]),
        "progress": [got, total],
        "state": scope_core.state(store, sec),
        "state_label": scope_core.STATUS_LABEL.get(scope_core.state(store, sec), ""),
        "guide": scope_core.guide_status(store, sec["key"]),
        "guide_label": scope_core.GUIDE_STATUS.get(scope_core.guide_status(store, sec["key"]), ""),
        "suggestions": [[i, bool(ok)] for i, ok in
                        scope_core.parse_suggestions(node.get("checklist", ""),
                                                    sec.get("checks") or [])],
        "node": {"assessment": node.get("assessment", ""),
                 "questions": [q if isinstance(q, dict) else {"q": str(q), "why": ""}
                               for q in (node.get("questions") or [])],
                 "answers": list(node.get("answers") or []),
                 "draft": node.get("draft", ""), "final": node.get("final", ""),
                 "risks": node.get("risks", ""), "checklist": node.get("checklist", ""),
                 "next": node.get("next", ""), "model": node.get("model", ""),
                 "updated": node.get("updated", "")},
    }
    out.update(extra)
    return out


def _stage_rows(project) -> list:
    """十阶段的**完整**内容（含追问/回答/稿子/检查表），工作台视图据此渲染与编辑。"""
    rows = []
    for s in STAGES:
        st = (getattr(project, "stages", None) or {}).get(str(s["id"])) or {}
        status = st.get("status", "todo")
        body = (st.get("final") or st.get("draft") or "").strip()
        rows.append({
            "id": s["id"], "title": s["title"], "spec": s.get("spec", ""),
            "goal": s.get("goal", ""),
            "actions": list(s.get("actions") or []),
            "reports": list(s.get("reports") or []),
            "pitfalls": list(s.get("pitfalls") or []),
            "refs": list(s.get("refs") or []),
            "status": status,
            "label": scope_core.STATUS_LABEL.get(status, status),
            "assessment": st.get("assessment", ""),
            "questions": [q if isinstance(q, dict) else {"q": str(q), "why": ""}
                          for q in (st.get("questions") or [])],
            "answers": list(st.get("answers") or []),
            "draft": st.get("draft", ""),
            "final": st.get("final", ""),
            "risks": st.get("risks", ""),
            "next": st.get("next", ""),
            "checklist": list(st.get("checklist") or []),
            "model": st.get("model", ""),
            "updated": st.get("updated", ""),
            "body_len": len(body),
            "is_final": bool((st.get("final") or "").strip()),
        })
    return rows


def state_payload(sel: str, project=None) -> dict:
    """整份界面状态。每次写操作后都回传一次，前端只管整体重绘，不做局部状态同步。"""
    metas = Project.list_all()
    if project is None:
        project = resolve_project(sel)
    out = {
        "ok": True, "app": APP_TITLE, "version": APP_VERSION,
        "python": sys.version.split()[0], "frozen": is_frozen(),
        "projects": [{"name": m["name"], "file": os.path.basename(m["path"]),
                      "updated": m["updated"], "created": m["created"], "done": m["done"],
                      "raw_len": m["raw_len"], "size_kb": m["size_kb"],
                      "model": m.get("model", "")} for m in metas],
        "current": project.name if project else "",
        "current_file": os.path.basename(project.path_) if project else "",
        "llm": llm_info(),
        "overview": None, "convergence": {},
    }
    if project is None:
        return out
    stat_store = getattr(project, "stat", None) or {}
    shape_store = getattr(project, "shape", None) or {}
    s_done, s_doing, s_ticks = scope_core.overall(stat_store, stat_data.STAGES)
    h_done, h_doing, h_ticks = scope_core.overall(shape_store, shape_data.SHAPE)
    counts = project.status_counts()
    out["overview"] = {
        "name": project.name, "created": project.created, "updated": project.updated,
        "model": project.model, "raw_design": project.raw_design,
        "raw_len": len((project.raw_design or "").strip()),
        "has_final_doc": bool((project.final_doc or "").strip()),
        "lanes": coupling.lane_progress(project),
        "digest": coupling.digest_stats(project),
        "stages": _stage_rows(project),
        "stage_counts": counts,
        "stat": _scope_rows(stat_store, stat_data.STAGES),
        "shape": _scope_rows(shape_store, shape_data.SHAPE),
        "totals": {
            "stat_done": s_done, "stat_doing": s_doing, "stat_ticks": s_ticks,
            "stat_checks": scope_core.total_checks(stat_data.STAGES),
            "shape_done": h_done, "shape_doing": h_doing, "shape_ticks": h_ticks,
            "shape_checks": scope_core.total_checks(shape_data.SHAPE),
        },
        "transcript_len": len(getattr(project, "transcript", None) or []),
        "final_doc": getattr(project, "final_doc", "") or "",
    }
    out["convergence"] = getattr(project, "convergence", None) or {}
    return out


# --------------------------------------------------------------------------- 浏览器
def browser_candidates() -> list:
    """按"能跑现代界面"的优先级列出本机浏览器（Win7 上尤其重要：默认可能是 IE11）。"""
    out = []
    local = os.environ.get("LOCALAPPDATA") or ""
    pf = os.environ.get("ProgramFiles") or r"C:\Program Files"
    pf86 = os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)"
    for p in (os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
              os.path.join(pf, r"Google\Chrome\Application\chrome.exe"),
              os.path.join(local, r"Google\Chrome\Application\chrome.exe"),
              os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe"),
              os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe"),
              os.path.join(pf, r"Mozilla Firefox\firefox.exe"),
              os.path.join(pf86, r"Mozilla Firefox\firefox.exe")):
        if p and os.path.exists(p):
            out.append(p)
    try:                                                            # 用户自定安装路径
        import winreg
        for exe in ("chrome.exe", "msedge.exe", "firefox.exe"):
            key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\\" + exe
            for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(root, key) as k:
                        v = winreg.QueryValue(k, None)
                    if v and os.path.exists(v):
                        out.append(v)
                except OSError:
                    continue
    except Exception:                                               # noqa: BLE001
        pass
    seen, uniq = set(), []
    for p in out:
        if p.lower() not in seen:
            seen.add(p.lower())
            uniq.append(p)
    return uniq


def open_browser(url: str, force: str = "") -> str:
    """打开浏览器：优先会用现代内核的那几个，而不是系统默认（可能是 IE11）。"""
    if force:
        try:
            subprocess.Popen([force, url])
            return force
        except Exception:                                           # noqa: BLE001
            pass
    for exe in browser_candidates():
        try:
            subprocess.Popen([exe, url])
            return exe
        except Exception:                                           # noqa: BLE001
            continue
    try:
        webbrowser.open(url)
        return "system-default"
    except Exception:                                               # noqa: BLE001
        return ""


# --------------------------------------------------------------------------- 服务
class Handler(BaseHTTPRequestHandler):
    server_version = "PCL-Radiomics-Web/%s" % APP_VERSION
    protocol_version = "HTTP/1.1"

    # -- 基础设施 -----------------------------------------------------------
    def log_message(self, fmt, *args):
        if STATE["verb"]:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, ctype: str, body: bytes, extra: dict = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, payload: dict):
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return {}
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8", "ignore"))
        except Exception:                                           # noqa: BLE001
            return {}

    def _query(self) -> dict:
        q = {}
        if "?" in self.path:
            for part in self.path.split("?", 1)[1].split("&"):
                if not part:
                    continue
                k, _, v = part.partition("=")
                q[k] = unquote(v, encoding="utf-8", errors="replace")
        return q

    # -- GET ---------------------------------------------------------------
    def do_GET(self):                                               # noqa: N802
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self._static("index.html")
        if path.startswith("/static/"):
            return self._static(path[len("/static/"):])
        if path == "/favicon.ico":
            return self._static("favicon.svg")
        if path in ("/api/health", "/health"):
            return self._json(200, {"ok": True, "app": APP_TITLE, "version": APP_VERSION,
                                    "python": sys.version.split()[0],
                                    "uptime_s": round(time.time() - STATE["started"], 1),
                                    "llm": llm_info()})
        if path == "/api/state":
            return self._json(200, state_payload(self._query().get("project", "")))
        if path == "/api/scope":
            q = self._query()
            project = resolve_project(q.get("project") or "")
            if project is None:
                return self._json(400, {"ok": False, "error": "没有可操作的项目"})
            page = q.get("page") if q.get("page") in ("stat", "shape") else "stat"
            return self._json(200, scope_payload(page, q.get("key") or "", project))
        if path == "/api/export":
            return self._export()
        return self._json(404, {"ok": False, "error": "unknown path %s" % path})

    def _static(self, rel: str):
        base = web_dir()
        safe = os.path.normpath(rel).replace("\\", "/").lstrip("/")
        if safe.startswith("..") or os.path.isabs(safe):
            return self._json(403, {"ok": False, "error": "forbidden"})
        full = os.path.join(base, safe.replace("/", os.sep))
        if not os.path.isfile(full) or os.path.splitext(full)[1].lower() not in STATIC_EXT:
            return self._json(404, {"ok": False, "error": "not found: %s" % safe})
        try:
            with open(full, "rb") as fh:
                data = fh.read()
        except Exception as e:                                      # noqa: BLE001
            return self._json(500, {"ok": False, "error": str(e)})
        ctype = MIME.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
        return self._send(200, ctype, data)

    # -- POST --------------------------------------------------------------
    def do_POST(self):                                              # noqa: N802
        path = self.path.split("?")[0].rstrip("/")
        if path == "/api/project/new":
            return self._project_new()
        if path == "/api/project/rename":
            return self._project_rename()
        if path == "/api/project/delete":
            return self._project_delete()
        if path == "/api/kickoff":                   # 速读研究设想（SSE）
            return self._kickoff()
        if path == "/api/stage/ask":                 # 追问（SSE）
            return self._stage_ask()
        if path == "/api/stage/rewrite":             # 改写（SSE）
            return self._stage_rewrite()
        if path == "/api/stage/answers":             # 只存回答（JSON）
            return self._stage_answers()
        if path == "/api/stage/save":                # 存编辑内容 / 采纳定稿（JSON）
            return self._stage_save()
        if path == "/api/finalize":                  # 汇总完整草案（SSE）
            return self._finalize()
        if path == "/api/scope/ask":                 # scope 追问（SSE）
            return self._scope_ask()
        if path == "/api/scope/rewrite":             # scope 定稿 + 自检判定（SSE）
            return self._scope_rewrite()
        if path == "/api/scope/answers":             # 只存回答（JSON）
            return self._scope_answers()
        if path == "/api/scope/save":                # 存编辑 / 勾选自检 / 采纳定稿（JSON）
            return self._scope_save()
        if path == "/api/convergence":               # 收敛推理（SSE）
            return self._convergence()
        return self._json(404, {"ok": False, "error": "unknown path %s" % path})

    def _project_new(self):
        body = self._body()
        name = (body.get("name") or "").strip() or "未命名课题"
        model = client().model
        try:
            p = Project.new(name, raw=body.get("raw") or "", model=model)
        except Exception as e:                                      # noqa: BLE001
            return self._json(500, {"ok": False, "error": "%s: %s" % (type(e).__name__, e)})
        return self._json(200, {"ok": True, "project": p.name,
                                "file": os.path.basename(p.path_)})

    def _project_rename(self):
        body = self._body()
        p = resolve_project(body.get("project") or "")
        name = (body.get("name") or "").strip()
        if p is None or not name:
            return self._json(400, {"ok": False, "error": "需要 project 与 name"})
        try:
            p.rename(name)
            p.save()
        except Exception as e:                                      # noqa: BLE001
            return self._json(500, {"ok": False, "error": "%s: %s" % (type(e).__name__, e)})
        return self._json(200, {"ok": True, "project": p.name})

    def _project_delete(self):
        body = self._body()
        p = resolve_project(body.get("project") or "")
        if p is None:
            return self._json(400, {"ok": False, "error": "找不到项目"})
        try:
            p.delete()
        except Exception as e:                                      # noqa: BLE001
            return self._json(500, {"ok": False, "error": "%s: %s" % (type(e).__name__, e)})
        return self._json(200, {"ok": True})

    # -- SSE ---------------------------------------------------------------
    def _sse_head(self):
        self._buf = []
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

    def _write_sse(self, payload: dict):
        try:
            self.wfile.write(("data: %s\n\n" % json.dumps(payload, ensure_ascii=False))
                             .encode("utf-8"))
            self.wfile.flush()
        except Exception:                                           # noqa: BLE001
            pass

    def _emit(self, kind: str, piece: str):
        """合并小片段再发，避免上百次逐字刷新把浏览器拖死。"""
        if not piece:
            return
        if self._buf and self._buf[-1][0] == kind:
            self._buf[-1] = (kind, self._buf[-1][1] + piece)
        else:
            self._buf.append((kind, piece))
        if sum(len(x[1]) for x in self._buf) >= 160:
            self._flush_sse()

    def _flush_sse(self):
        for kind, piece in self._buf:
            self._write_sse({"type": kind, "text": piece})
        self._buf = []

    # -- LLM 动作（统一走 SSE 推流）------------------------------------------
    def _llm_action(self, kind, build, apply_fn, reason=False, max_tokens=None,
                    status="", pre_fn=None, scope=False):
        """跑一次 LLM 调用并把结果以 SSE 推给浏览器。

        * ``build(agent, ctx)``    组装 messages（用桌面版同一套提示词）
        * ``pre_fn(project, ctx)`` 调用前的落库（例如先把研究者的回答存下来）
        * ``apply_fn(project, out, ctx)`` 解析并落库，返回给前端的附加字段
        ``ctx`` = {"sid": 阶段号, "body": 请求体}；``scope=True`` 时另带
        {"page": stat|shape, "key": 环节 key, "sec": 环节数据}。
        结束后统一回传 ``state``（整份界面状态），前端只管整体重绘。
        """
        body = self._body()
        ctx = {"sid": self._sid(body), "body": body, "page": "", "key": "", "sec": None}
        if scope:
            page = body.get("page") if body.get("page") in ("stat", "shape") else "stat"
            data = stat_data.STAGES if page == "stat" else shape_data.SHAPE
            want = body.get("key") or ""
            sec = next((s for s in data if s["key"] == want), None) or data[0]
            ctx.update({"page": page, "key": sec["key"], "sec": sec})
        project = resolve_project(body.get("project") or "")
        if project is None:
            return self._json(400, {"ok": False, "error": "没有可操作的项目"})
        if not RUN_LOCK.acquire(False):
            return self._json(409, {"ok": False, "error": "已有一次推理在进行中，请稍候"})
        try:
            self._sse_head()
            info = llm_info()
            if not info["ready"]:
                self._write_sse({"type": "error",
                                 "text": "未配置 API Key：请在桌面版「设置」里填写，"
                                         "或设置环境变量 DEEPSEEK_API_KEY"})
                self._write_sse({"type": "done", "ok": False})
                return
            if pre_fn is not None:
                try:
                    pre_fn(project, ctx)
                    project.save()
                except Exception as e:                              # noqa: BLE001
                    self._write_sse({"type": "error",
                                     "text": "保存输入失败：%s: %s" % (type(e).__name__, e)})
                    self._write_sse({"type": "done", "ok": False})
                    return
            self._write_sse({"type": "status",
                             "text": (status or "%(model)s") % {"model": info["model"]}})
            agent = DesignAgent(client(), project)

            def on_delta(piece, k):
                self._emit("reasoning" if k == "reasoning" else "content", piece)

            try:
                out = client().chat(build(agent, ctx), stream=True, on_delta=on_delta,
                                    reason=reason, max_tokens=max_tokens)
            except Exception as e:                                  # noqa: BLE001
                self._flush_sse()
                self._write_sse({"type": "error",
                                 "text": "调用失败：%s: %s" % (type(e).__name__, e)})
                self._write_sse({"type": "done", "ok": False})
                return
            self._flush_sse()
            extra = {}
            try:
                extra = apply_fn(project, out, ctx) or {}
            except Exception as e:                                  # noqa: BLE001
                self._write_sse({"type": "error",
                                 "text": "解析模型输出失败：%s: %s" % (type(e).__name__, e)})
                self._write_sse({"type": "done", "ok": False})
                return
            saved, err = True, ""
            try:
                project.save()
            except Exception as e:                                  # noqa: BLE001
                saved, err = False, "%s: %s" % (type(e).__name__, e)
            payload = {"type": "done", "ok": True, "kind": kind, "sid": ctx["sid"],
                       "page": ctx["page"], "key": ctx["key"],
                       "saved": saved, "save_error": err,
                       "usage": out.get("usage") or {}, "model": out.get("model", ""),
                       "elapsed": round(float(out.get("elapsed") or 0), 1),
                       "content": out.get("content") or "",
                       "reasoning": (out.get("reasoning") or "")[:8000],
                       "state": state_payload("", project)}
            payload.update(extra)
            self._write_sse(payload)
        finally:
            RUN_LOCK.release()

    # -- 各动作 -------------------------------------------------------------
    def _sid(self, body) -> int:
        try:
            return max(1, min(len(STAGES), int(body.get("sid") or 1)))
        except (TypeError, ValueError):
            return 1

    def _convergence(self):
        def apply_fn(project, out, ctx):
            data = parse_convergence(out.get("content") or "")
            data["updated"] = time.strftime("%Y-%m-%d %H:%M")
            data["model"] = out.get("model", "")
            data["elapsed"] = round(float(out.get("elapsed") or 0), 1)
            data["reasoning"] = (out.get("reasoning") or "")[:8000]
            project.convergence = data
            return {"convergence": data,
                    "chapters": len(data.get("chapters") or []),
                    "actions": len(data.get("actions") or [])}

        return self._llm_action(
            "convergence", lambda a, c: a.convergence_messages(), apply_fn, reason=True,
            status="已连接 %(model)s · reason 模式（温度 0，推理过程实时显示）")

    def _kickoff(self):
        """速读研究设想：先存下原始设想，再让模型给出速读与首要关注点（记入对话记录）。"""
        def pre_fn(project, ctx):
            raw = ctx["body"].get("raw_design")
            if isinstance(raw, str):
                project.raw_design = raw.strip()

        def apply_fn(project, out, ctx):
            sec = parse_sections(out.get("content") or "")
            DesignAgent(client(), project).record("agent", out.get("content") or "",
                                                  None, "速读")
            return {"read": pick(sec, "设计速读"),
                    "focus": pick(sec, "首要关注点"),
                    "route": pick(sec, "路线说明")}

        return self._llm_action("kickoff", lambda a, c: a.kickoff_messages(), apply_fn,
                                pre_fn=pre_fn, status="正在速读研究设想 · %(model)s")

    def _stage_ask(self):
        def build(agent, ctx):
            return agent.ask_messages(ctx["sid"])

        def apply_fn(project, out, ctx):
            sid = ctx["sid"]
            st = project.stage(sid)
            sec = parse_sections(out.get("content") or "")
            st["assessment"] = pick(sec, "现状评估")
            st["questions"] = parse_questions(pick(sec, "必须澄清", "问题"))
            st["answers"] = ["" for _ in st["questions"]]
            st["status"] = "asked"
            st["model"] = out.get("model", "")
            st["updated"] = time.strftime("%H:%M")
            return {"questions": len(st["questions"]),
                    "assessment_len": len(st["assessment"])}

        return self._llm_action("ask", build, apply_fn,
                                status="第 %(model)s · 正在生成现状评估与追问")

    def _stage_answers(self):
        """只存研究者的回答（不调用模型），供「先存草稿」用。"""
        body = self._body()
        project = resolve_project(body.get("project") or "")
        if project is None:
            return self._json(400, {"ok": False, "error": "没有可操作的项目"})
        sid = self._sid(body)
        st = project.stage(sid)
        answers = body.get("answers")
        if isinstance(answers, list):
            st["answers"] = [str(a or "").strip() for a in answers]
        try:
            project.save()
        except Exception as e:                                      # noqa: BLE001
            return self._json(500, {"ok": False, "error": "%s: %s" % (type(e).__name__, e)})
        return self._json(200, {"ok": True, "sid": sid,
                                "state": state_payload("", project)})

    def _stage_rewrite(self):
        def build(agent, ctx):
            return agent.rewrite_messages(ctx["sid"])

        def pre_fn(project, ctx):
            answers = ctx["body"].get("answers")
            if isinstance(answers, list):       # 先落盘再改写，中途出错也不丢回答
                project.stage(ctx["sid"])["answers"] = [str(a or "").strip()
                                                        for a in answers]

        def apply_fn(project, out, ctx):
            sid = ctx["sid"]
            st = project.stage(sid)
            sec = parse_sections(out.get("content") or "")
            st["draft"] = pick(sec, "改写稿")
            st["risks"] = pick(sec, "风险提示")
            st["checklist"] = parse_checklist(pick(sec, "检查表"))
            st["next"] = pick(sec, "下一步")
            st["status"] = "drafted" if st["draft"] else st.get("status", "asked")
            st["updated"] = time.strftime("%H:%M")
            return {"draft_len": len(st["draft"]), "checks": len(st["checklist"])}

        return self._llm_action("rewrite", build, apply_fn, pre_fn=pre_fn,
                                status="第 %(model)s · 正在生成改写稿与检查表")

    def _finalize(self):
        def apply_fn(project, out, ctx):
            sec = parse_sections(out.get("content") or "")
            project.final_doc = pick(sec, "设计草案") or (out.get("content") or "")
            return {"final_len": len(project.final_doc),
                    "todo_list": pick(sec, "待补数据"),
                    "selfcheck": pick(sec, "投稿前自查")}

        return self._llm_action("finalize", lambda a, c: a.finalize_messages(), apply_fn,
                                max_tokens=14000,
                                status="正在把各阶段定稿整合成完整草案 · %(model)s")

    def _stage_save(self):
        """保存阶段的编辑内容（定稿框 / 草稿框 / 状态），不调用模型。"""
        body = self._body()
        project = resolve_project(body.get("project") or "")
        if project is None:
            return self._json(400, {"ok": False, "error": "没有可操作的项目"})
        sid = self._sid(body)
        st = project.stage(sid)
        for key in ("final", "draft", "risks", "assessment"):
            if isinstance(body.get(key), str):
                st[key] = body[key].strip()
        if isinstance(body.get("answers"), list):
            st["answers"] = [str(a or "").strip() for a in body["answers"]]
        if isinstance(body.get("checklist"), list):
            st["checklist"] = [str(c) for c in body["checklist"]]
        if body.get("status") in ("todo", "asked", "drafted", "done"):
            st["status"] = body["status"]
        if body.get("accept"):                  # 采纳：把定稿框内容当定稿收录
            st["final"] = (body.get("final") or st.get("draft") or "").strip()
            st["status"] = "done"
        if body.get("to_draft") and not st.get("draft"):
            st["draft"] = st.get("final", "")
        st["updated"] = time.strftime("%H:%M")
        raw = body.get("raw_design")
        if isinstance(raw, str):
            project.raw_design = raw.strip()
        try:
            project.save()
        except Exception as e:                                      # noqa: BLE001
            return self._json(500, {"ok": False, "error": "%s: %s" % (type(e).__name__, e)})
        return self._json(200, {"ok": True, "sid": sid, "status": st["status"],
                                "state": state_payload("", project)})

    # -- scope 环节（统计九阶段 / SCI 七章）----------------------------------
    def _scope_ask(self):
        def build(agent, ctx):
            return agent.scope_ask_messages(ctx["page"], ctx["sec"])

        def apply_fn(project, out, ctx):
            store = project.stat if ctx["page"] == "stat" else project.shape
            node = scope_core.node(store, ctx["key"])
            sec = parse_sections(out.get("content") or "")
            node["assessment"] = pick(sec, "现状评估")
            node["questions"] = parse_questions(pick(sec, "必须澄清", "问题"))
            node["answers"] = ["" for _ in node["questions"]]
            node["status"] = "asked"
            node["model"] = out.get("model", "")
            node["updated"] = time.strftime("%H:%M")
            return {"questions": len(node["questions"])}

        return self._llm_action("scope_ask", build, apply_fn, scope=True,
                                status="正在对照本环节规范生成现状评估与追问 · %(model)s")

    def _scope_answers(self):
        """只存回答（不调用模型）。"""
        body = self._body()
        project = resolve_project(body.get("project") or "")
        if project is None:
            return self._json(400, {"ok": False, "error": "没有可操作的项目"})
        page = body.get("page") if body.get("page") in ("stat", "shape") else "stat"
        data = stat_data.STAGES if page == "stat" else shape_data.SHAPE
        sec = next((s for s in data if s["key"] == (body.get("key") or "")), None) or data[0]
        store = project.stat if page == "stat" else project.shape
        node = scope_core.node(store, sec["key"])
        if isinstance(body.get("answers"), list):
            node["answers"] = [str(a or "").strip() for a in body["answers"]]
        node["updated"] = time.strftime("%H:%M")
        try:
            project.save()
        except Exception as e:                                      # noqa: BLE001
            return self._json(500, {"ok": False, "error": "%s: %s" % (type(e).__name__, e)})
        return self._json(200, {"ok": True, "scope": scope_payload(page, sec["key"], project),
                                "state": state_payload("", project)})

    def _scope_rewrite(self):
        def build(agent, ctx):
            return agent.scope_rewrite_messages(ctx["page"], ctx["sec"])

        def pre_fn(project, ctx):
            answers = ctx["body"].get("answers")
            if isinstance(answers, list):
                store = project.stat if ctx["page"] == "stat" else project.shape
                scope_core.node(store, ctx["key"])["answers"] = [str(a or "").strip()
                                                                 for a in answers]

        def apply_fn(project, out, ctx):
            store = project.stat if ctx["page"] == "stat" else project.shape
            node = scope_core.node(store, ctx["key"])
            sec = parse_sections(out.get("content") or "")
            node["draft"] = pick(sec, "定稿", "改写稿")
            node["risks"] = pick(sec, "风险提示")
            node["next"] = pick(sec, "下一步")
            node["checklist"] = pick(sec, "检查表")
            node["status"] = "drafted" if node["draft"] else node.get("status", "asked")
            node["model"] = out.get("model", "")
            node["updated"] = time.strftime("%H:%M")
            tips = scope_core.parse_suggestions(node["checklist"], ctx["sec"]["checks"])
            return {"draft_len": len(node["draft"]),
                    "suggestions": [[i, bool(ok)] for i, ok in tips]}

        return self._llm_action("scope_rewrite", build, apply_fn, scope=True, pre_fn=pre_fn,
                                status="正在按本环节规范生成定稿与自检判定 · %(model)s")

    def _scope_save(self):
        """保存 scope 环节的编辑：定稿/草稿/回答/自检勾选；accept 时按模型检查表自动勾选。"""
        body = self._body()
        project = resolve_project(body.get("project") or "")
        if project is None:
            return self._json(400, {"ok": False, "error": "没有可操作的项目"})
        page = body.get("page") if body.get("page") in ("stat", "shape") else "stat"
        data = stat_data.STAGES if page == "stat" else shape_data.SHAPE
        sec = next((s for s in data if s["key"] == (body.get("key") or "")), None) or data[0]
        store = project.stat if page == "stat" else project.shape
        node = scope_core.node(store, sec["key"])
        for k in ("assessment", "draft", "final", "risks", "next", "checklist"):
            if isinstance(body.get(k), str):
                node[k] = body[k].strip()
        if isinstance(body.get("answers"), list):
            node["answers"] = [str(a or "").strip() for a in body["answers"]]
        if isinstance(body.get("checks"), dict):        # 整体覆盖 {"0": true, ...}
            store[sec["key"]]["checks"] = {str(k): True for k, v in body["checks"].items() if v}
        if isinstance(body.get("set_check"), list):     # [[序号, 是否勾选], ...]
            for pair in body["set_check"]:
                try:
                    scope_core.set_check(store, sec["key"], int(pair[0]), bool(pair[1]))
                except (TypeError, ValueError, IndexError):
                    continue
        if body.get("set_all") in (True, False):
            scope_core.set_all(store, sec, bool(body["set_all"]))
        if body.get("status") in ("todo", "asked", "drafted", "done"):
            node["status"] = body["status"]
        ticked = 0
        if body.get("accept"):                          # 采纳：定稿 + 按检查表自动勾选
            node["final"] = (body.get("final") or node.get("draft") or "").strip()
            node["status"] = "done"
            for i, ok in scope_core.parse_suggestions(node.get("checklist", ""),
                                                      sec.get("checks") or []):
                scope_core.set_check(store, sec["key"], i, ok)
                ticked += 1 if ok else 0
        node["updated"] = time.strftime("%H:%M")
        try:
            project.save()
        except Exception as e:                                      # noqa: BLE001
            return self._json(500, {"ok": False, "error": "%s: %s" % (type(e).__name__, e)})
        return self._json(200, {"ok": True, "ticked": ticked, "page": page,
                                "scope": scope_payload(page, sec["key"], project),
                                "state": state_payload("", project)})

    def _export(self):
        """导出 Markdown / Word（走浏览器下载；Word 需要 python-docx）。"""
        q = self._query()
        project = resolve_project(q.get("project") or "")
        if project is None:
            return self._json(400, {"ok": False, "error": "没有可导出的项目"})
        fmt = (q.get("fmt") or "md").lower()
        safe = Project.sanitize(project.name)
        if fmt in ("md", "markdown"):
            body = project.render_doc().encode("utf-8")
            name = "研究设计_%s.md" % safe
            return self._send(200, "text/markdown; charset=utf-8", body,
                              self._dl_headers(name))
        if fmt in ("docx", "word"):
            try:
                import docx_export
            except Exception as e:                                  # noqa: BLE001
                return self._json(501, {
                    "ok": False,
                    "error": "导出 Word 需要 python-docx：%s。请执行 pip install python-docx，"
                             "或改用 Markdown 导出（无需任何依赖）。" % e})
            tmp = os.path.join(app_home(), "_export_tmp")
            try:
                os.makedirs(tmp, exist_ok=True)
            except Exception:                                       # noqa: BLE001
                tmp = app_home()
            path = os.path.join(tmp, "研究设计_%s.docx" % safe)
            try:
                path = docx_export.build(project, path)
                with open(path, "rb") as fh:
                    body = fh.read()
            except Exception as e:                                  # noqa: BLE001
                return self._json(500, {"ok": False,
                                        "error": "生成 Word 失败：%s: %s"
                                                 % (type(e).__name__, e)})
            finally:
                try:
                    os.remove(path)
                except Exception:                                   # noqa: BLE001
                    pass
            return self._send(200,
                              "application/vnd.openxmlformats-officedocument."
                              "wordprocessingml.document",
                              body, self._dl_headers("研究设计_%s.docx" % safe))
        return self._json(400, {"ok": False, "error": "fmt 只支持 md / docx"})

    @staticmethod
    def _dl_headers(name: str) -> dict:
        return {"Content-Disposition":
                "attachment; filename=\"design.%s\"; filename*=UTF-8''%s"
                % (os.path.splitext(name)[1].lstrip("."), quote(name))}


# --------------------------------------------------------------------------- 启动
def pick_port(host: str, port: int, tries: int = PORT_TRIES) -> int:
    for i in range(tries):
        p = port + i
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((host, p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:                                               # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=APP_TITLE)
    ap.add_argument("--host", default="127.0.0.1", help="默认仅本机可访问")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--project", default="", help="启动时选中的项目（名字或文件名）")
    ap.add_argument("--browser", default="", help="指定浏览器 exe（默认自动挑 Chrome/Edge/Firefox）")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    ap.add_argument("--verbose", action="store_true", help="打印每次请求")
    args = ap.parse_args()

    if args.verbose:
        STATE["verb"] = True
    wd = web_dir()
    if not os.path.isfile(os.path.join(wd, "index.html")):
        print("[错误] 找不到界面文件：%s" % os.path.join(wd, "index.html"))
        return 2
    port = pick_port(args.host, args.port)
    if not port:
        print("[错误] %d–%d 端口都被占用，请用 --port 指定其它端口"
              % (args.port, args.port + PORT_TRIES - 1))
        return 2

    info = llm_info()
    url = "http://%s:%d/" % (args.host, port)
    if args.project:
        url += "?project=" + quote(args.project)
    srv = ThreadingHTTPServer((args.host, port), Handler)
    srv.daemon_threads = True
    print("=" * 62)
    print(" %s" % APP_TITLE)
    print("=" * 62)
    print(" 地址： %s" % url)
    print(" 界面： %s" % wd)
    print(" Python：%s%s" % (sys.version.split()[0], "（冻结版）" if is_frozen() else ""))
    print(" 模型： %s → %s · 密钥 %s" % (info["model"], info["base_url"], info["key"]))
    if not info["ready"]:
        print(" [提示] 还没有可用的 API Key，界面能打开但无法推理。")
    print("-" * 62)
    print(" 关闭窗口即结束服务；Ctrl+C 亦可。")
    print("=" * 62)
    if not args.no_browser:
        used = open_browser(url, args.browser)
        print(" 已用浏览器打开：%s" % (used or "（没找到浏览器，请手动访问上面的地址）"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
