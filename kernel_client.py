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


def _stabilize_extracted(path: str) -> str:
    """把「从 onefile 临时解包目录里取到的」内核复制到稳定位置。

    为什么必须这么做（P0 实测）：
        onefile 会把内置文件解包到 %TEMP%\\_MEIxxxx。若直接从那里启动内核，
        内核进程会**锁住**那个 opencode.exe，导致 PyInstaller 退出时无法删除
        临时目录，父进程挂死 —— 实测同一命令：
            onedir  6 s 正常退出
            onefile 90 s+ 不退出（功能其实成功，日志已显示 session 建好）
        复制到 <kernel_home> 后从那里启动，临时目录不再被锁，退出即正常；
        同时内核也不再随父进程的临时目录一起消失。

    仅当路径确实位于 _MEIPASS 之下时才动作；否则原样返回（onedir 不需要）。
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return path
    try:
        if os.path.commonpath([os.path.abspath(path), os.path.abspath(meipass)]) \
                != os.path.abspath(meipass):
            return path
    except ValueError:
        return path

    stable = os.path.join(kernel_home(), _EXE_NAME)
    try:
        same = (os.path.exists(stable)
                and os.path.getsize(stable) == os.path.getsize(path))
        if not same:
            tmp = stable + ".tmp"
            shutil.copyfile(path, tmp)
            os.replace(tmp, stable)        # 原子替换，避免半个文件被启动
        if os.name != "nt":
            os.chmod(stable, 0o755)
        return stable
    except Exception:                                                  # noqa: BLE001
        return path                        # 复制失败就退回原路径（功能优先）


def opencode_exe() -> str | None:
    """定位 opencode 可执行文件。

    查找顺序（与 app_paths 的只读资源纪律一致）：
      1. 环境变量 PCL_OPENCODE_EXE（显式覆盖，调试用）
      2. 冻结产物同级 opencode/opencode.exe
      3. 打包内置（resource_path → _internal/opencode/opencode.exe）
      4. 内核 home 下 opencode.exe（源码运行/手动放置）
      5. PATH

    注意：onefile 场景会经 _stabilize_extracted 复制到 <kernel_home> 再返回，
    否则内核会锁住临时解包目录、导致本进程退出时挂死。
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
            return _stabilize_extracted(cand)

    found = shutil.which("opencode")
    return _stabilize_extracted(found) if found else None


def list_processes(exe_name: str = _EXE_NAME) -> list[dict]:
    """列出同名进程 [{pid, exe, cmd}]（Windows 用 CIM，macOS/Linux 用 ps）。

    用于「只保留一个内核终端」时识别与本程序同源的 opencode 进程，
    避免误伤用户自己安装的 opencode（exe 路径不同）。
    """
    return (_list_processes_windows(exe_name) if os.name == "nt"
            else _list_processes_posix(exe_name))


def _list_processes_windows(exe_name: str) -> list[dict]:
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='%s'\" | "
          "ForEach-Object { \"$($_.ProcessId)`t$($_.ExecutablePath)`t$($_.CommandLine)\" }"
          % exe_name)
    try:
        out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=30).stdout
    except Exception:                                                  # noqa: BLE001
        return []
    procs: list[dict] = []
    for line in (out or "").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].strip().isdigit():
            procs.append({"pid": int(parts[0]), "exe": parts[1],
                          "cmd": parts[2] if len(parts) > 2 else ""})
    return procs


def _list_processes_posix(exe_name: str) -> list[dict]:
    """macOS/Linux：`ps -axo pid=,comm=,args=`（comm 多为完整路径）。"""
    try:
        out = subprocess.run(["ps", "-axo", "pid=,comm=,args="],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=20).stdout
    except Exception:                                                  # noqa: BLE001
        return []
    procs: list[dict] = []
    for line in (out or "").splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        pid, comm = int(parts[0]), parts[1]
        cmd = parts[2] if len(parts) > 2 else ""
        exe_base = os.path.basename(comm)
        argv0 = os.path.basename(cmd.split()[0]) if cmd.split() else ""
        if exe_name in (exe_base, argv0):
            procs.append({"pid": pid, "exe": comm, "cmd": cmd})
    return procs


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


def model_ref(value) -> dict | None:
    """"provider/model" → {id, providerID}（Model.Ref）；dict 原样返回。"""
    if not value:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and "/" in value:
        provider, mid = value.split("/", 1)
        return {"providerID": provider, "id": mid}
    return None


def legacy_model_ref(value) -> dict | None:
    """同 model_ref，但转成 V1 SessionPrompt.ModelRef = {providerID, modelID}。"""
    ref = model_ref(value)
    if not ref:
        return None
    return {"providerID": ref.get("providerID"), "modelID": ref.get("id")}


# ------------------------------------------------------------------------- 客户端

class KernelClient:
    """方向 B（HTTP+SSE 控制面）与方向 D（进程托管）。"""

    #: 从 opencode serve 的 stdout 里抓端口（serve.ts:20 的打印格式）
    _LISTEN_RE = re.compile(r"listening on http://[^:]+:(\d+)")
    #: 打印的警示行（未设密码）不应被当成错误
    _WARN_RE = re.compile(r"^\s*(Warning|!)\s", re.I)

    def __init__(self, exe: str | None = None, state: KernelState | None = None,
                 verbose: bool = False, directory: str | None = None,
                 extra_env: dict | None = None):
        self.exe = exe or opencode_exe()
        self.state = state
        self.verbose = verbose
        #: 追加到内核环境（如 OPENCODE_CONFIG_CONTENT 注入 provider.apiKey）
        self.extra_env = dict(extra_env or {})
        #: 显式钉住的实例目录（x-opencode-directory）。为空则由内核按 cwd/项目根推断。
        #: 事件流（/api/event）会按 event.location.directory === instance.directory
        #: 过滤，钉住目录可避免"会话事件被静默丢弃"。
        self.directory = directory
        self._proc: subprocess.Popen | None = None
        self._log_lines: list[str] = []
        #: 实测数字（P0 关注）：从 spawn 到打印端口 / 到 health 通过。
        #: 注意：走 adopt_state() **接管**来的实例没有计时，两者保持 None ——
        #: 调用方必须先判空再格式化（曾经因为直接 :.2f 而抛 TypeError，
        #: 把整条联动启动流程打断，症状就是"内核其实起来了但界面毫无反应"）。
        self.listen_seconds: float | None = None
        self.ready_seconds: float | None = None
        #: 是否为接管（而非本进程拉起）的实例
        self.adopted = False

    # ---------------------------------------------------------------- 日志

    def _log(self, message: str) -> None:
        if self.verbose:
            sys.stderr.write(f"[kernel] {message}\n")

    def logs(self) -> list[str]:
        return list(self._log_lines)

    # ------------------------------------------------------------ 孤儿清理

    def adopt_state(self) -> KernelState | None:
        """若状态文件记录的实例仍存活且健康，**接管**它。

        为什么必须接管：`cli.py kernel ...` 每次都是新进程，若只"报告复用"
        而不接管，每个命令都会再起一个内核 —— 实测踩到连跑三条命令留下三个
        内核进程（各占 300+ MB）。GUI 是长驻进程所以不明显，控制台用法会漏。
        """
        path = kernel_state_file()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                old = json.load(fh)
        except Exception:                                              # noqa: BLE001
            return None
        pid = int(old.get("pid") or 0)
        port = int(old.get("port") or 0)
        password = old.get("password") or ""
        if not (pid and port and password):
            return None
        if not self._pid_alive(pid):
            return None
        st = KernelState(pid, port, password,
                         version=str(old.get("version") or ""),
                         home=old.get("home") or kernel_home())
        if not self._healthy(st):
            return None
        self.state = st
        self.adopted = True
        return st

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
            return f"上一实例仍在运行（pid={pid} port={port}），将由 adopt_state 接管"
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
        """懒启动：已在本进程内运行则复用；状态文件里有存活实例则接管；
        否则拉起并等到 health 通过。"""
        if self.state and self._pid_alive(self.state.pid) and self._healthy(self.state):
            self._log("复用本进程已持有的内核")
            return self.state

        adopted = self.adopt_state()
        if adopted:
            self._log(f"接管已运行的内核 {adopted.url}（pid={adopted.pid}）")
            return adopted

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
        env = kernel_env(password, extra=self.extra_env)
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
        if self.directory:
            headers["x-opencode-directory"] = self.directory
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

    def new_session(self, title: str | None = None, location: dict | None = None,
                    model: dict | str | None = None, agent: str | None = None) -> dict:
        """建会话。model 为 Model.Ref = {id, providerID}（payload 支持）。

        ⚠️ 不显式给 model 时，V2 会话会落到内核默认模型（实测是 opencode/exo-free，
        已废弃，HTTP 410）。因此宿主/控制台应总是传自己配的模型。
        """
        body: dict = {}
        if title:
            body["title"] = title
        if location:
            body["location"] = location
        if model:
            body["model"] = model
        if agent:
            body["agent"] = agent
        return self.request("POST", "/api/session", body or None)

    def session_exists(self, session_id: str) -> bool:
        sid = urllib.parse.quote(session_id, safe="")
        try:
            self.request("GET", f"/api/session/{sid}", timeout=20)
            return True
        except KernelError:
            return False

    def session_get(self, session_id: str) -> dict:
        sid = urllib.parse.quote(session_id, safe="")
        return self.request("GET", f"/api/session/{sid}", timeout=20)

    def context(self, session_id: str) -> list:
        """当前上下文消息（含 assistant 的 finish/content）。

        用途：① 完成判定（末条 assistant 有 finish 即本轮结束）——
        因为实测 `POST /session/:id/wait` 在此构建返回 503 "not available yet"；
        ② 兜底取正文（SSE 若未收到/被目录过滤）。
        """
        sid = urllib.parse.quote(session_id, safe="")
        got = self.request("GET", f"/api/session/{sid}/context", timeout=30)
        return (got or {}).get("data") or []

    def switch_model(self, session_id: str, model) -> dict:
        """切换会话模型（protocol/groups/session.ts:189）。model 为 'provider/id' 或 {id,providerID}。"""
        sid = urllib.parse.quote(session_id, safe="")
        ref = model_ref(model)
        if not ref:
            raise KernelError(f"非法 model：{model!r}（应为 'provider/model' 或 {{id,providerID}}）")
        return self.request("POST", f"/api/session/{sid}/model", {"model": ref}, timeout=30)

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

    def wait_session(self, session_id: str, timeout: float = 900.0) -> dict:
        """阻塞到该会话的 agent loop 变为 idle（protocol/groups/session.ts:241）。

        比"轮询 session.status"更权威：内核自己判定 drain 结束。
        """
        sid = urllib.parse.quote(session_id, safe="")
        return self.request("POST", f"/api/session/{sid}/wait", None, timeout=timeout)

    # ---------------------------------------------------- 问答 / 权限（回灌）
    #  内核会**阻塞等待**这两类请求的回复。GUI 就地答题经此回灌（plan §5），
    #  不建立第二套真值：写回的是 opencode 自己的请求队列。
    #    question:   GET  /api/session/:id/question
    #                POST /api/session/:id/question/:rid/reply   {answers: [[label,...]]}
    #                POST /api/session/:id/question/:rid/reject
    #    permission: GET  /api/session/:id/permission
    #                POST /api/session/:id/permission/:rid/reply {reply, message?}
    #  字段形状见 packages/schema/src/question.ts、permission.ts：
    #    Question.Request { id, sessionID, questions:[{question,header,options:[{label,description}],multiple?,custom?}], tool? }
    #    Question.Reply   { answers: [[label,...]] }  —— 按 questions 顺序，各给一个"已选标签"数组
    #    Permission.Request { id, sessionID, action, resources:[str], save?, metadata?, source? }
    #    Permission.Reply   "once" | "always" | "reject"

    def session_questions(self, session_id: str) -> list:
        sid = urllib.parse.quote(session_id, safe="")
        got = self.request("GET", f"/api/session/{sid}/question", timeout=30)
        return (got or {}).get("data") or []

    def reply_question(self, session_id: str, request_id: str,
                       answers: list) -> dict:
        """answers: [[label,...], ...]，按问题顺序（Question.Reply）。"""
        sid = urllib.parse.quote(session_id, safe="")
        rid = urllib.parse.quote(request_id, safe="")
        return self.request("POST", f"/api/session/{sid}/question/{rid}/reply",
                            {"answers": answers}, timeout=30)

    def reject_question(self, session_id: str, request_id: str) -> dict:
        sid = urllib.parse.quote(session_id, safe="")
        rid = urllib.parse.quote(request_id, safe="")
        return self.request("POST", f"/api/session/{sid}/question/{rid}/reject",
                            None, timeout=30)

    def session_permissions(self, session_id: str) -> list:
        sid = urllib.parse.quote(session_id, safe="")
        got = self.request("GET", f"/api/session/{sid}/permission", timeout=30)
        return (got or {}).get("data") or []

    def reply_permission(self, session_id: str, request_id: str,
                         reply: str, message: str | None = None) -> dict:
        """reply ∈ {once, always, reject}（Permission.Reply）。"""
        sid = urllib.parse.quote(session_id, safe="")
        rid = urllib.parse.quote(request_id, safe="")
        body: dict = {"reply": reply}
        if message:
            body["message"] = message
        return self.request("POST", f"/api/session/{sid}/permission/{rid}/reply",
                            body, timeout=30)

    # ------------------------------------------------- legacy V1 HTTP 会话面
    #  为什么用它：V2 /api/session 的模型解析在本构建里只认 opencode/* 自有模型
    #  （实测 ModelUnavailableError），而 legacy /session/:id/message 走 V1
    #  SessionPrompt（服务端执行、读 auth.json），能直接用用户配的 deepseek，
    #  且 question/permission 都发生在服务端，可经 /question、/permission 回灌。
    #  —— 这是「opencode 驱动 + GUI 就地答题」可行的通道。

    def create_session(self, title: str | None = None,
                       model=None, agent: str | None = None) -> dict:
        body: dict = {}
        if title:
            body["title"] = title
        if model:
            body["model"] = legacy_model_ref(model) or model
        if agent:
            body["agent"] = agent
        return self.request("POST", "/session", body or None, timeout=30)

    def update_session_title(self, session_id: str, title: str) -> dict:
        """PATCH /session/:id {title} —— 改 opencode 会话显示标题（groups/session.ts:227）。"""
        sid = urllib.parse.quote(session_id, safe="")
        return self.request("PATCH", f"/session/{sid}", {"title": title}, timeout=30)

    def tui_select_session(self, session_id: str) -> dict:
        """POST /tui/select-session {sessionID} —— 让**已在运行的 TUI** 切到该会话。

        这样切课题时复用同一个终端窗口（不重开、不闪窗）。
        """
        return self.request("POST", "/tui/select-session",
                            {"sessionID": session_id}, timeout=30)

    def tui_show_toast(self, message: str, variant: str = "info",
                       title: str | None = None) -> dict:
        """POST /tui/show-toast —— 在 TUI 里弹一条提示（可选）。"""
        body: dict = {"message": message, "variant": variant}
        if title:
            body["title"] = title
        return self.request("POST", "/tui/show-toast", body, timeout=15)

    def prompt_legacy(self, session_id: str, text: str, model=None,
                      agent: str | None = None, timeout: float = 900.0) -> dict:
        """POST /session/:id/message —— **阻塞到本轮结束**，返回 SessionV1.WithParts。

        用 legacy 而非 V2：V1 SessionPrompt 在服务端执行，用 auth.json 的 provider；
        返回 {info:{role,finish,modelID,providerID,...}, parts:[step-start,text,tool,...]}。
        question/permission 会经 /event 推送并可经 /question、/permission 回灌。
        """
        sid = urllib.parse.quote(session_id, safe="")
        body: dict = {"parts": [{"type": "text", "text": text}]}
        ref = legacy_model_ref(model)
        if ref:
            body["model"] = ref
        if agent:
            body["agent"] = agent
        return self.request("POST", f"/session/{sid}/message", body, timeout=timeout)

    def post_noreply(self, session_id: str, text: str, model=None,
                     timeout: float = 60.0) -> dict:
        """向会话发一条**不触发模型回复**的消息（GUI 操作日志用）。

        PromptInput 有 noReply 字段：消息进入会话历史/TUI，但模型不回话。
        """
        sid = urllib.parse.quote(session_id, safe="")
        body: dict = {"parts": [{"type": "text", "text": text}], "noReply": True}
        ref = legacy_model_ref(model)
        if ref:
            body["model"] = ref
        return self.request("POST", f"/session/{sid}/message", body, timeout=timeout)

    def legacy_questions(self) -> list:
        """GET /question —— 服务端待决问题（Question.Request[]）。"""
        got = self.request("GET", "/question", timeout=30)
        return got if isinstance(got, list) else ((got or {}).get("data") or [])

    def legacy_reply_question(self, request_id: str, answers: list) -> dict:
        rid = urllib.parse.quote(request_id, safe="")
        return self.request("POST", f"/question/{rid}/reply", {"answers": answers}, timeout=30)

    def legacy_reject_question(self, request_id: str) -> dict:
        rid = urllib.parse.quote(request_id, safe="")
        return self.request("POST", f"/question/{rid}/reject", None, timeout=30)

    def legacy_permissions(self) -> list:
        """GET /permission —— 待决权限（PermissionV1.Request[]）。"""
        got = self.request("GET", "/permission", timeout=30)
        return got if isinstance(got, list) else ((got or {}).get("data") or [])

    def legacy_reply_permission(self, request_id: str, reply: str,
                                message: str | None = None) -> dict:
        """reply ∈ {once, always, reject}（PermissionV1.Reply）。"""
        rid = urllib.parse.quote(request_id, safe="")
        body: dict = {"reply": reply}
        if message:
            body["message"] = message
        return self.request("POST", f"/permission/{rid}/reply", body, timeout=30)

    # ------------------------------------------------------------- SSE

    def events(self, session_id: str | None = None, timeout: float = 300.0,
               max_events: int | None = None, on_open=None, stop_event=None,
               poll: float = 2.0, legacy: bool = False):
        """迭代服务端事件（SSE）。

        session_id 为空走实例级 /api/event；否则走
        /api/session/:id/event（protocol/groups/session.ts:327）。
        产出已解析的 dict；无法解析的行以 {"_raw": ...} 形式产出。

        事件体形状是 **{id, type, properties}** —— 见
        server/routes/instance/httpapi/handlers/event.ts 的
        `Stream.map((event) => ({ id, type, properties: event.data }))`，
        即业务字段在 `properties` 下（不是 `data`）。

        on_open     连接建立后回调一次（subscribe-then-prompt 的同步点）
        stop_event  threading.Event；置位后尽快返回
        poll        读超时（秒）。服务端每 10s 发一次 server.heartbeat，
                    这里用较短的读超时轮询，让 stop_event 更灵敏。
        """
        st = self.state
        if not st:
            raise KernelError("内核未启动")
        if legacy:
            path = "/event"
        else:
            path = f"/api/session/{urllib.parse.quote(session_id, safe='')}/event" if session_id else "/api/event"
        req = urllib.request.Request(
            st.url + path,
            headers={"Authorization": self._auth_header(st), "Accept": "text/event-stream"},
        )
        if self.directory:
            req.add_header("x-opencode-directory", self.directory)
        count = 0
        with urllib.request.urlopen(req, timeout=15) as res:
            # 连接建立后再把底层 socket 读超时调小，便于 stop_event 及时生效
            try:
                res.fp.raw._sock.settimeout(poll)
            except Exception:                                          # noqa: BLE001
                pass
            if on_open is not None:
                try:
                    on_open()
                except Exception:                                      # noqa: BLE001
                    pass
            while True:
                if stop_event is not None and stop_event.is_set():
                    return
                try:
                    raw = res.readline()
                except (socket.timeout, TimeoutError):
                    continue
                except OSError:
                    return
                if not raw:
                    return
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
        env = kernel_env(st.password if st else None, extra=self.extra_env)
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
        proc = subprocess.run([self.exe, "models"], env=kernel_env(st.password if st else None, extra=self.extra_env),
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
                              env=kernel_env(st.password if st else None, extra=self.extra_env),
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
        """拉起内核 TUI：新终端窗口 + `opencode attach` 到隔离实例。

        必须用 attach 而不是裸跑 opencode —— 裸跑会自建 server，
        与常驻实例争用同一个 sqlite（风险 19）。
        密码走 OPENCODE_SERVER_PASSWORD，不进命令行（风险 21）。

        平台差异（用户要求"显示为系统的 console 或 mac 的 bash"）：
          Windows  新控制台窗口（CREATE_NEW_CONSOLE），默认套 PowerShell
          macOS    用 osascript 让 Terminal.app 执行同一条 attach 命令
          Linux    无统一终端，回落为直接 spawn（继承当前终端）
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

        env = kernel_env(st.password, extra=self.extra_env)  # 与 server 共用同一份环境（风险 20）

        # ---- macOS：走 Terminal.app，得到用户熟悉的 bash ----
        if sys.platform == "darwin":
            import shlex
            inner = " ".join(shlex.quote(a) for a in attach)
            # 用 env 前缀把密码与隔离 home 一起带过去；密码不进命令行
            env_prefix = " ".join(
                f"{k}={shlex.quote(env[k])}"
                for k in ("OPENCODE_SERVER_PASSWORD", "OPENCODE_SERVER_USERNAME",
                          "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME",
                          "XDG_CACHE_HOME", "OPENCODE_CONFIG_DIR", "OPENCODE_CLIENT")
                if k in env
            )
            script = (f'tell application "Terminal" to do script '
                      f'"cd {shlex.quote(target)} && {env_prefix} {inner}"')
            self._log("拉起 TUI（macOS Terminal）")
            return subprocess.Popen(["osascript", "-e", script],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # ---- Windows / Linux ----
        if via_powershell and os.name == "nt":
            quoted = " ".join(f"'{a}'" for a in attach)
            cmd = ["powershell.exe", "-NoExit", "-Command", f"& {quoted}"]
        else:
            cmd = attach

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        self._log(f"拉起 TUI：{' '.join(cmd[:4])} ...")
        return subprocess.Popen(cmd, env=env, cwd=target, creationflags=creationflags)

    # ------------------------------------------------------------- 停止

    def stop(self, timeout: float = 8.0) -> str:
        """优雅停止：先 terminate，超时再强杀。

        没有本进程句柄时（例如 `cli.py kernel stop` 是独立进程），
        退回到状态文件记录的实例并强杀 —— 否则跨进程根本停不掉内核。
        """
        proc = self._proc
        if not proc:
            st = self.state or self.adopt_state()
            if st and self._pid_alive(st.pid):
                self._kill(st.pid)
                self._remove_state_file()
                self.state = None
                return f"已停止 pid={st.pid}（无本进程句柄，按强杀处理）"
            self._remove_state_file()
            return "无运行中的内核"
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._kill(proc.pid)
                self._remove_state_file()
                self.state = None
                return f"超时，已强杀 pid={proc.pid}"
        self._remove_state_file()
        self.state = None
        return "已优雅停止"

    @staticmethod
    def _remove_state_file() -> None:
        try:
            os.remove(kernel_state_file())
        except OSError:
            pass


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

