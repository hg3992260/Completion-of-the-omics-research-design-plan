# -*- coding: utf-8 -*-
"""opencode 内核客户端（Qt-free）—— 宿主与内嵌内核之间的唯一接缝。

架构关系（详见 opencode-embedding-plan.md §2.1）：
    方向 A：内核 → 宿主   走 MCP（内核是客户端，宿主是服务端）
    方向 B：宿主 → 内核   走 HTTP + SSE（本模块）
    方向 D：宿主托管内核进程（本模块）

本模块只负责方向 B 与 D。方向 A 由 mcp_server 暴露端点实现。

设计约束（均已核实源码，锚点以 opencode 仓库根为准）：
  · 隔离 home：XDG_* 指向 <app_home>/opencode/*，绝不写用户真实的
    ~/.local/share/opencode（xdg-basedir@5.1.0 无 Windows 特判，
    默认是 os.homedir()/.local/share —— 见 global.ts:9-45）
  · 不设 OPENCODE_TEST_HOME：保留用户已有的 ~/.claude/skills 与
    ~/.agents/skills（skill/index.ts:191 走 Global.Path.home；D8 决策）
  · OPENCODE_CLIENT=desktop：让 question 工具注册（registry.ts:207）
  · 密码只走环境变量，不进命令行 —— 否则会暴露在进程列表里（风险 21）
  · 端口不预选：opencode 的 --port 默认 0（network.ts:10），从 stdout
    解析实际端口（serve.ts:20 会打印 "listening on http://host:port"）
  · 环境变量在 opencode 模块加载时求值，运行中改无效 ——
    因此 server 与 TUI 必须共用同一份 kernel_env()（风险 15/20）

依赖：仅标准库（与 llm_client.py 的既有风格一致）。
"""

from __future__ import annotations

import base64
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from app_paths import app_home, data_path, is_frozen

# --------------------------------------------------------------------------- 路径

KERNEL_DIR_NAME = "opencode"
_EXE_NAME = "opencode.exe" if os.name == "nt" else "opencode"


def kernel_home() -> str:
    """内核的隔离 home（可写）。所有内核状态都落在它下面。"""
    d = data_path(KERNEL_DIR_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def kernel_state_file() -> str:
    """记录当前内核实例 {pid, port, password} 的状态文件。

    用途：宿主崩溃/被强杀后，下一次启动可以据此清理孤儿进程。
    """
    return data_path(KERNEL_DIR_NAME, "kernel_instance.json")


def opencode_exe() -> str | None:
    """定位 opencode 可执行文件。

    查找顺序（与 app_paths 的只读资源纪律一致）：
      1. 环境变量 PCL_OPENCODE_EXE（显式覆盖，调试用）
      2. 冻结产物同级 opencode/opencode.exe
      3. 打包内置（resource_path → _internal/opencode/opencode.exe）
      4. 内核 home 下 opencode.exe（源码运行/手动放置）
      5. PATH
    """
    override = os.environ.get("PCL_OPENCODE_EXE")
    if override and os.path.exists(override):
        return override

    candidates: list[str] = []

    if is_frozen():
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)),
                                       KERNEL_DIR_NAME, _EXE_NAME))

    # 打包内置：onedir 下 _MEIPASS 即 _internal，也是 datas 目标 "opencode" 的落点
    try:
        from app_paths import resource_path
        candidates.append(resource_path(os.path.join(KERNEL_DIR_NAME, _EXE_NAME)))
    except Exception:                                                  # noqa: BLE001
        pass

    candidates.append(os.path.join(kernel_home(), _EXE_NAME))

    for cand in candidates:
        if cand and os.path.exists(cand):
            return cand

    return shutil.which("opencode")


# ------------------------------------------------------------------- 环境变量（隔离）

def kernel_env(password: str | None = None, extra: dict | None = None) -> dict:
    """生成内核的隔离环境。

    server 进程与 TUI 进程必须共用本函数的结果 —— 否则 TUI 会去读
    用户真实 home 的配置，与隔离实例对不上（风险 20）。
    """
    home = kernel_home()
    env = dict(os.environ)

    # 隔离：四个 XDG 根全部指向内核 home（global.ts:9-45）
    env["XDG_DATA_HOME"] = os.path.join(home, "data")
    env["XDG_CONFIG_HOME"] = os.path.join(home, "config")
    env["XDG_STATE_HOME"] = os.path.join(home, "state")
    env["XDG_CACHE_HOME"] = os.path.join(home, "cache")
    # 更精确的 config 杠杆（global.ts:40-57 的 Flag.OPENCODE_CONFIG_DIR）
    env["OPENCODE_CONFIG_DIR"] = os.path.join(home, "config", KERNEL_DIR_NAME)

    # 客户端身份：决定 question 工具是否注册（registry.ts:207）
    env["OPENCODE_CLIENT"] = "desktop"
    # 嵌入式必须禁自更新，否则会尝试替换自己
    env["OPENCODE_DISABLE_AUTOUPDATE"] = "1"
    # 不设 OPENCODE_TEST_HOME（D8）：保留用户 ~/.claude/skills、~/.agents/skills

    if password:
        env["OPENCODE_SERVER_PASSWORD"] = password
        env["OPENCODE_SERVER_USERNAME"] = "opencode"

    for key, value in (extra or {}).items():
        env[key] = str(value)
    return env


def ensure_home_layout() -> dict:
    """建立内核 home 的目录骨架，并返回关键路径（便于自检打印）。"""
    home = kernel_home()
    paths = {
        "home": home,
        "data": os.path.join(home, "data", KERNEL_DIR_NAME),
        "config": os.path.join(home, "config", KERNEL_DIR_NAME),
        "state": os.path.join(home, "state", KERNEL_DIR_NAME),
        "cache": os.path.join(home, "cache", KERNEL_DIR_NAME),
        "logs": os.path.join(home, "logs"),
    }
    for key in ("data", "config", "state", "cache", "logs"):
        os.makedirs(paths[key], exist_ok=True)
    return paths


# ----------------------------------------------------------------------- 实例状态

class KernelState:
    """一个内核实例的可序列化描述。"""

    def __init__(self, pid: int, port: int, password: str, version: str = "", home: str = ""):
        self.pid = pid
        self.port = port
        self.password = password
        self.version = version
        self.home = home or kernel_home()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def as_dict(self) -> dict:
        return {"pid": self.pid, "port": self.port, "password": self.password,
                "version": self.version, "home": self.home}

    def __repr__(self) -> str:
        return f"<KernelState pid={self.pid} port={self.port} version={self.version!r}>"


class KernelError(RuntimeError):
    pass


# ------------------------------------------------------------------------- 客户端

class KernelClient:
    """方向 B（HTTP+SSE 控制面）与方向 D（进程托管）。"""

    #: 从 opencode serve 的 stdout 里抓端口（serve.ts:20 的打印格式）
    _LISTEN_RE = re.compile(r"listening on http://[^:]+:(\d+)")
    #: 打印的警示行（未设密码）不应被当成错误
    _WARN_RE = re.compile(r"^\s*(Warning|!)\s", re.I)

    def __init__(self, exe: str | None = None, state: KernelState | None = None,
                 verbose: bool = False):
        self.exe = exe or opencode_exe()
        self.state = state
        self.verbose = verbose
        self._proc: subprocess.Popen | None = None
        self._log_lines: list[str] = []
        #: 实测数字（P0 关注）：从 spawn 到打印端口 / 到 health 通过
        self.listen_seconds: float | None = None
        self.ready_seconds: float | None = None

    # ---------------------------------------------------------------- 日志

    def _log(self, message: str) -> None:
        if self.verbose:
            sys.stderr.write(f"[kernel] {message}\n")

    def logs(self) -> list[str]:
        return list(self._log_lines)

    # ------------------------------------------------------------ 孤儿清理

    def cleanup_stale(self) -> str:
        """清掉上次遗留的内核实例。返回人类可读的处置说明。"""
        path = kernel_state_file()
        if not os.path.exists(path):
            return "无遗留状态文件"
        try:
            with open(path, "r", encoding="utf-8") as fh:
                old = json.load(fh)
        except Exception:                                              # noqa: BLE001
            return "状态文件损坏，已忽略"

        pid = int(old.get("pid") or 0)
        port = int(old.get("port") or 0)
        if pid and self._pid_alive(pid) and self._port_serving(port, pid):
            return f"上一实例仍在运行（pid={pid} port={port}），复用"
        if pid and self._pid_alive(pid):
            try:
                self._kill(pid)
                return f"已清理孤儿进程 pid={pid}"
            except Exception as e:                                     # noqa: BLE001
                return f"孤儿进程 pid={pid} 清理失败：{e}"
        return "无存活实例"

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            if os.name == "nt":
                out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                                     capture_output=True, text=True, timeout=10).stdout
                return str(pid) in out
            os.kill(pid, 0)
            return True
        except Exception:                                              # noqa: BLE001
            return False

    @staticmethod
    def _port_serving(port: int, pid: int | None = None) -> bool:
        if not port:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            return False

    @staticmethod
    def _kill(pid: int) -> None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=20)
        else:
            os.kill(pid, signal.SIGTERM)

    # ---------------------------------------------------------------- 启动

    def ensure_running(self, timeout: float = 90.0) -> KernelState:
        """懒启动：已在运行则复用，否则拉起并等到 health 通过。"""
        if self.state and self._pid_alive(self.state.pid) and self._healthy(self.state):
            self._log("复用已运行的内核")
            return self.state

        if not self.exe:
            raise KernelError(
                "找不到 opencode 可执行文件。请设置 PCL_OPENCODE_EXE，"
                f"或把 {_EXE_NAME} 放到 {os.path.join(kernel_home(), _EXE_NAME)}"
            )

        ensure_home_layout()
        self.cleanup_stale()

        started = time.time()
        deadline = started + timeout

        password = secrets.token_urlsafe(24)
        env = kernel_env(password)
        # 不传 --port：opencode 默认 0，由系统分配空闲端口（network.ts:10）
        cmd = [self.exe, "serve", "--hostname", "127.0.0.1"]

        self._log(f"启动 {self.exe} serve（隔离 home={kernel_home()}）")
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._proc = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=kernel_home(), text=True, encoding="utf-8", errors="replace",
            bufsize=1, creationflags=creationflags,
        )

        port = self._await_listen(self._proc, max(1.0, deadline - time.time()))
        state = KernelState(self._proc.pid, port, password)
        self.state = state
        self.listen_seconds = time.time() - started

        while time.time() < deadline:
            if self._healthy(state):
                break
            if self._proc.poll() is not None:
                raise KernelError("内核进程提前退出：\n" + "\n".join(self._log_lines[-20:]))
            time.sleep(0.2)
        else:
            raise KernelError(f"内核未在 {timeout}s 内就绪：\n" + "\n".join(self._log_lines[-20:]))
        self.ready_seconds = time.time() - started

        info = self.health()
        state.version = str(info.get("version") or "")
        self._write_state(state)
        self._log(f"内核就绪 {state.url} version={state.version} pid={state.pid}")
        return state

    def _await_listen(self, proc: subprocess.Popen, timeout: float) -> int:
        """读 stdout 直到出现 listening 行，返回端口。"""
        deadline = time.time() + timeout
        assert proc.stdout is not None
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    raise KernelError("内核进程退出且未打印端口：\n"
                                      + "\n".join(self._log_lines[-20:]))
                continue
            line = line.rstrip("\r\n")
            self._log_lines.append(line)
            self._log(line)
            match = self._LISTEN_RE.search(line)
            if match:
                return int(match.group(1))
            if proc.poll() is not None:
                raise KernelError("内核进程退出且未打印端口：\n"
                                  + "\n".join(self._log_lines[-20:]))
        raise KernelError(f"等待 listening 超时（{timeout}s）：\n"
                          + "\n".join(self._log_lines[-20:]))

    def _write_state(self, state: KernelState) -> None:
        try:
            path = kernel_state_file()
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(state.as_dict(), fh, ensure_ascii=False, indent=2)
            os.chmod(path, 0o600)                                      # 含密码
        except Exception as e:                                         # noqa: BLE001
            self._log(f"状态文件写入失败：{e}")

    # ---------------------------------------------------------------- HTTP

    def _auth_header(self, state: KernelState) -> str:
        raw = f"opencode:{state.password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def request(self, method: str, path: str, body: dict | None = None,
                timeout: float = 60.0, state: KernelState | None = None) -> dict:
        """发一个带 Basic 认证的 JSON 请求。返回解析后的 JSON（可能为空 dict）。"""
        st = state or self.state
        if not st:
            raise KernelError("内核未启动")
        url = st.url + path
        data = None
        headers = {"Authorization": self._auth_header(st), "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                raw = res.read()
                if not raw:
                    return {}
                try:
                    return json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    return {"_raw": raw.decode("utf-8", "replace")}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise KernelError(f"{method} {path} → HTTP {e.code}: {detail}") from None
        except urllib.error.URLError as e:
            raise KernelError(f"{method} {path} → {e.reason}") from None

    def health(self, state: KernelState | None = None) -> dict:
        """GET /global/health → {healthy, version}（httpapi/groups/global.ts:66-69）。"""
        return self.request("GET", "/global/health", timeout=10, state=state)

    def _healthy(self, state: KernelState) -> bool:
        try:
            return bool(self.health(state).get("healthy"))
        except KernelError:
            return False

    # --------------------------------------------------------------- 会话

    def sessions(self) -> list:
        got = self.request("GET", "/api/session")
        return got.get("data") or got if isinstance(got, dict) else got

    def new_session(self, title: str | None = None, location: dict | None = None) -> dict:
        body: dict = {}
        if title:
            body["title"] = title
        if location:
            body["location"] = location
        return self.request("POST", "/api/session", body or None)

    def prompt(self, session_id: str, text: str, *, delivery: str | None = None,
               resume: bool | None = None) -> dict:
        """POST /api/session/:id/prompt（protocol/groups/session.ts:205-224）。"""
        body: dict = {"prompt": {"text": text}}
        if delivery:
            body["delivery"] = delivery
        if resume is not None:
            body["resume"] = resume
        sid = urllib.parse.quote(session_id, safe="")
        return self.request("POST", f"/api/session/{sid}/prompt", body, timeout=120)

    def interrupt(self, session_id: str) -> dict:
        sid = urllib.parse.quote(session_id, safe="")
        return self.request("POST", f"/api/session/{sid}/interrupt", None, timeout=30)

    # ------------------------------------------------------------- SSE

    def events(self, session_id: str | None = None, timeout: float = 300.0,
               max_events: int | None = None):
        """迭代服务端事件（SSE）。

        session_id 为空走实例级 /api/event；否则走
        /api/session/:id/event（protocol/groups/session.ts:327）。
        产出已解析的 dict；无法解析的行以 {"_raw": ...} 形式产出。
        """
        st = self.state
        if not st:
            raise KernelError("内核未启动")
        path = f"/api/session/{urllib.parse.quote(session_id, safe='')}/event" if session_id else "/api/event"
        req = urllib.request.Request(
            st.url + path,
            headers={"Authorization": self._auth_header(st), "Accept": "text/event-stream"},
        )
        count = 0
        with urllib.request.urlopen(req, timeout=timeout) as res:
            for raw in res:
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload in ("", "[DONE]"):
                    continue
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    event = {"_raw": payload}
                yield event
                count += 1
                if max_events is not None and count >= max_events:
                    return

    # ------------------------------------------------------- 一次性运行

    def run_once(self, text: str, *, session_id: str | None = None,
                 agent: str | None = None, model: str | None = None,
                 timeout: float = 600.0) -> list[dict]:
        """用 `opencode run --format json` 跑一轮，返回逐行 JSON 事件。

        与 HTTP 的 SSE 面互补：这条路径的 stdout 契约明确，适合脚本化与自检。
        """
        if not self.exe:
            raise KernelError("找不到 opencode 可执行文件")
        st = self.state
        env = kernel_env(st.password if st else None)
        cmd = [self.exe, "run", "--format", "json"]
        if st:
            # 挂到常驻实例，避免另起一个 server。
            # 密码走环境变量（OPENCODE_SERVER_PASSWORD），不进命令行 —— run.ts:196-203
            cmd += ["--attach", st.url]
        if session_id:
            cmd += ["--session", session_id]
        if agent:
            cmd += ["--agent", agent]
        if model:
            cmd += ["--model", model]
        cmd.append(text)

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=timeout, creationflags=creationflags)
        events: list[dict] = []
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"_raw": line})
        if proc.returncode != 0 and not events:
            raise KernelError(f"run 失败（exit {proc.returncode}）："
                              + (proc.stderr or "")[:500])
        return events

    # ------------------------------------------------------------- TUI

    def models_cli(self, timeout: float = 180.0) -> list[str]:
        """用 CLI 列模型。

        ⚠️ P0 实测：`GET /api/model` 只返回 opencode 自有 provider（38 个
        opencode/*，目录视角），而 CLI 才会按凭据激活出可用的 provider
        （如 deepseek/*）。控制台的模型选择器应以本方法为准（plan §9.5②）。
        """
        if not self.exe:
            raise KernelError("找不到 opencode 可执行文件")
        st = self.state
        proc = subprocess.run([self.exe, "models"], env=kernel_env(st.password if st else None),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
        out = []
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if "/" in line and " " not in line:
                out.append(line)
        return out

    def mcp_list(self, timeout: float = 120.0) -> str:
        """`opencode mcp list` 的原始输出 —— 用来看宿主 MCP 是否被内核连上。"""
        if not self.exe:
            raise KernelError("找不到 opencode 可执行文件")
        st = self.state
        proc = subprocess.run([self.exe, "mcp", "list"],
                              env=kernel_env(st.password if st else None),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, cwd=kernel_home())
        return (proc.stdout or "") + (proc.stderr or "")

    def log_tail(self, lines: int = 80) -> list[str]:
        """内核自己的日志尾部（generic 错误只能从这里看清）。"""
        logdir = os.path.join(kernel_home(), "data", KERNEL_DIR_NAME, "log")
        if not os.path.isdir(logdir):
            return []
        files = sorted((os.path.join(logdir, f) for f in os.listdir(logdir)),
                       key=os.path.getmtime, reverse=True)
        if not files:
            return []
        try:
            with open(files[0], "r", encoding="utf-8", errors="replace") as fh:
                return [ln.rstrip() for ln in fh.readlines()[-lines:]]
        except OSError:
            return []

    def spawn_tui(self, project_dir: str | None = None,
                  session_id: str | None = None, continue_last: bool = False,
                  via_powershell: bool = True) -> subprocess.Popen:
        """拉起内核 TUI：新控制台窗口 + `opencode attach` 到隔离实例。

        必须用 attach 而不是裸跑 opencode —— 裸跑会自建 server，
        与常驻实例争用同一个 sqlite（风险 19）。
        密码走 OPENCODE_SERVER_PASSWORD，不进命令行（风险 21）。
        """
        if not self.exe or not self.state:
            raise KernelError("内核未启动")
        st = self.state
        target = project_dir or os.getcwd()

        attach = [self.exe, "attach", st.url, "--dir", target]
        if session_id:
            attach += ["--session", session_id]
        elif continue_last:
            attach += ["--continue"]

        if via_powershell and os.name == "nt":
            quoted = " ".join(f"'{a}'" for a in attach)
            cmd = ["powershell.exe", "-NoExit", "-Command", f"& {quoted}"]
        else:
            cmd = attach

        env = kernel_env(st.password)          # 与 server 共用同一份环境（风险 20）
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        self._log(f"拉起 TUI：{' '.join(cmd[:4])} ...")
        return subprocess.Popen(cmd, env=env, cwd=target, creationflags=creationflags)

    # ------------------------------------------------------------- 停止

    def stop(self, timeout: float = 8.0) -> str:
        """优雅停止：先 terminate，超时再强杀。"""
        state = self.state
        proc = self._proc
        if not proc and state:
            if self._pid_alive(state.pid):
                self._kill(state.pid)
                return f"已强杀 pid={state.pid}"
            return "无运行中的内核"
        if not proc:
            return "无运行中的内核"
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._kill(proc.pid)
                return f"超时，已强杀 pid={proc.pid}"
        try:
            os.remove(kernel_state_file())
        except OSError:
            pass
        self.state = None
        return "已优雅停止"


# ------------------------------------------------------------------ 便捷入口

def status() -> dict:
    """只读探测当前内核状态（不启动任何进程）。"""
    info = {"exe": opencode_exe(), "home": kernel_home(), "running": False}
    path = kernel_state_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                old = json.load(fh)
            info["recorded"] = {k: v for k, v in old.items() if k != "password"}
            client = KernelClient()
            st = KernelState(int(old.get("pid") or 0), int(old.get("port") or 0),
                             old.get("password") or "")
            if client._pid_alive(st.pid) and client._healthy(st):
                info["running"] = True
                info["state"] = {k: v for k, v in st.as_dict().items() if k != "password"}
                info["health"] = client.health(st)
        except Exception as e:                                         # noqa: BLE001
            info["error"] = f"{type(e).__name__}: {e}"
    return info


if __name__ == "__main__":
    print(json.dumps(status(), ensure_ascii=False, indent=2))
