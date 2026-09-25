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
    GET  /api/state[?project=] 总览数据（项目列表 + 三条工作线 + 十阶段 + 缓存的收敛结论）
    POST /api/project/new      新建空白项目
    POST /api/project/rename   项目改名
    POST /api/project/delete   删除项目
    POST /api/convergence      收敛推理（SSE 流式：status / reasoning / content / done）

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

from app_paths import APP_VERSION, is_frozen, resource_path        # noqa: E402

import coupling                                                    # noqa: E402
import scope_core                                                  # noqa: E402
import shape_data                                                  # noqa: E402
import stat_data                                                   # noqa: E402
from design_agent import DesignAgent, Project, parse_convergence    # noqa: E402
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


def _stage_rows(project) -> list:
    rows = []
    for s in STAGES:
        st = (getattr(project, "stages", None) or {}).get(str(s["id"])) or {}
        status = st.get("status", "todo")
        body = (st.get("final") or st.get("draft") or "").strip()
        rows.append({
            "id": s["id"], "title": s["title"], "spec": s.get("spec", ""),
            "goal": (s.get("goal") or "")[:200], "status": status,
            "label": scope_core.STATUS_LABEL.get(status, status),
            "body_len": len(body),
            "is_final": bool((st.get("final") or "").strip()),
            "questions": len(st.get("questions") or []),
            "answers": len([a for a in (st.get("answers") or []) if str(a).strip()]),
            "checks": len(st.get("checklist") or []),
            "updated": st.get("updated", ""),
        })
    return rows


def state_payload(sel: str) -> dict:
    metas = Project.list_all()
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
        if path == "/api/convergence":
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

    def _convergence(self):
        body = self._body()
        project = resolve_project(body.get("project") or "")
        if project is None:
            return self._json(400, {"ok": False, "error": "没有可推理的项目"})
        if not RUN_LOCK.acquire(False):
            return self._json(409, {"ok": False, "error": "已有一次推理在进行中，请稍候"})
        try:
            self._sse_head()
            info = llm_info()
            if not info["ready"]:
                self._write_sse({"type": "error",
                                 "text": "未配置 API Key：请在 GUI 的「设置」里填写，"
                                         "或设置环境变量 DEEPSEEK_API_KEY"})
                self._write_sse({"type": "done", "ok": False})
                return
            self._write_sse({"type": "status",
                             "text": "已连接 %s · reason 模式（温度 0，推理过程实时显示）"
                                     % info["model"]})
            agent = DesignAgent(client(), project)

            def on_delta(piece, kind):
                self._emit("reasoning" if kind == "reasoning" else "content", piece)

            try:
                out = client().chat(agent.convergence_messages(), stream=True,
                                    on_delta=on_delta, reason=True)
            except Exception as e:                                  # noqa: BLE001
                self._flush_sse()
                self._write_sse({"type": "error",
                                 "text": "调用失败：%s: %s" % (type(e).__name__, e)})
                self._write_sse({"type": "done", "ok": False})
                return
            self._flush_sse()
            text = out.get("content") or ""
            data = parse_convergence(text)
            data["updated"] = time.strftime("%Y-%m-%d %H:%M")
            data["model"] = out.get("model", "")
            data["elapsed"] = round(float(out.get("elapsed") or 0), 1)
            data["reasoning"] = (out.get("reasoning") or "")[:8000]
            project.convergence = data
            saved, err = True, ""
            try:
                project.save()
            except Exception as e:                                  # noqa: BLE001
                saved, err = False, "%s: %s" % (type(e).__name__, e)
            self._write_sse({"type": "done", "ok": True, "saved": saved, "save_error": err,
                             "convergence": data, "usage": out.get("usage") or {},
                             "chapters": len(data.get("chapters") or []),
                             "actions": len(data.get("actions") or [])})
        finally:
            RUN_LOCK.release()


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
