# -*- coding: utf-8 -*-
"""GUI ↔ opencode 内核的联动总控（用户澄清的架构，见 opencode-embedding-plan.md §2.1）。

用户明确要求的四条，本模块负责把它们串起来：

  1. **GUI 程序是 opencode 内核的 MCP 服务**
     → 启动时把宿主的进程内 MCP 端点注册进内核配置（方向 A）

  2. **打开 GUI 程序的同时 opencode 启动，并显示为系统的 console / mac 的 bash**
     → 启动即拉起内核（不是懒启动），并在**独立终端窗口**里 attach 它的 TUI
        Windows: 新的 PowerShell/conhost 窗口
        macOS:   Terminal.app 里的 bash

  3. **在 GUI 上切换项目，opencode 都能新建或切换到对应 session**
     → 项目 ↔ session 绑定表（kernel_config.projects.json）；
        切项目时确保该项目的 session 存在，并让 TUI 重新 attach 到它

  4. **可在那个终端里用 opencode 下达全自动命令，驱动本程序完成功能操作**
     → 由方向 A（MCP 21 个领域工具）保证；本模块只负责把链路拉起来

设计取舍：
  · 本模块 **Qt-free**，所有方法阻塞式，供 GUI 在后台线程里调用，
    结果字符串由调用方 marshal 回界面。这样也便于离线自检。
  · 全流程可关闭（PCL_KERNEL_AUTOSTART=0 / PCL_KERNEL_NO_TUI=1），
    且 `--shot/--e2e/--demo` 等自动化模式自动跳过，避免干扰既有自检脚本。
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

# GBK 控制台下 print("↔") 等字符会抛 UnicodeEncodeError，离线自检会中途中止。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import kernel_client as kc                                              # noqa: E402
import kernel_config as kcfg                                            # noqa: E402


# --------------------------------------------------------------------------- 日志

def boot_log_path() -> str:
    """联动的持久日志。

    为什么必须有：窗口化构建下 stderr 可能不可用，用户"双击后什么都没发生"
    时无法定位。把每一次启动尝试（含失败原因）落盘，是最低成本的诊断手段。
    """
    return os.path.join(kc.kernel_home(), "boot.log")


def boot_log_tail(lines: int = 60) -> list[str]:
    path = boot_log_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return [x.rstrip() for x in fh.readlines()[-lines:]]
    except OSError:
        return []


def log_attempt(message: str) -> None:
    """模块级的落盘日志（不经过 KernelBoot 实例也能记录，用于 import 失败等）。"""
    try:
        path = boot_log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [kernel] {message}\n")
    except Exception:                                                  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- 开关

def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("", "0", "false", "no", "off")


def autostart_enabled() -> bool:
    """GUI 启动时是否自动拉起内核（用户要求默认开）。"""
    return _flag("PCL_KERNEL_AUTOSTART", True)


def tui_enabled() -> bool:
    """是否自动弹出可见的终端窗口跑 opencode TUI（用户要求默认开）。"""
    return _flag("PCL_KERNEL_TUI", True)


def should_skip_for_mode(argv: list | None = None) -> str | None:
    """自动化模式下不打扰既有自检脚本；返回跳过的原因，None 表示可以启动。"""
    argv = list(sys.argv if argv is None else argv)
    for mode in ("--shot", "--e2e", "--demo"):
        if mode in argv:
            return f"{mode} 模式跳过内核联动"
    if not autostart_enabled():
        return "PCL_KERNEL_AUTOSTART=0"
    return None


# --------------------------------------------------------------------------- 总控

class KernelBoot:
    """把内核拉起来、注册宿主 MCP、绑定项目 session、弹出 TUI。

    线程安全：内部一把锁 + `_tui` 子进程句柄；可在后台线程反复调用 bind_project。
    """

    def __init__(self, exe: str | None = None) -> None:
        self._lock = threading.RLock()
        self._client: kc.KernelClient | None = None
        self._tui: subprocess.Popen | None = None
        self._tui_pid: int | None = None
        self._mcp_url: str | None = None
        self._project: str | None = None
        self._log: list[str] = []
        self._exe = exe
        self._driver = None

    # ---------------------------------------------------------------- 日志

    def _say(self, message: str) -> None:
        """写日志。三条出口，互为备份：

        1) 内存（GUI 可回显）
        2) 持久文件 <kernel_home>/boot.log —— 窗口化构建下 stderr 可能不可用，
           而且用户"看不到任何反应"时，只有落盘日志能定位问题
        3) stderr（若存在）
        """
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[kernel] {message}"
        self._log.append(line)
        try:
            path = boot_log_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"{stamp} {line}\n")
        except Exception:                                              # noqa: BLE001
            pass
        # 注意：windowed 构建里 sys.stderr 可能是 None，绝不能直接 .write
        stream = getattr(sys, "stderr", None)
        if stream is not None:
            try:
                stream.write(line + "\n")
                stream.flush()
            except Exception:                                          # noqa: BLE001
                pass

    def messages(self) -> list[str]:
        return list(self._log)

    # ------------------------------------------------------------ 方向 A

    def _ensure_host_mcp(self) -> str | None:
        """在本进程内起 MCP 端点，并把它注册进内核配置（方向 A）。"""
        try:
            import mcp_server
        except Exception as e:                                         # noqa: BLE001
            self._say(f"载入 mcp_server 失败，方向 A 不可用：{type(e).__name__}: {e}")
            return None

        r = mcp_server.serve_http_in_thread()
        if not r.get("ok"):
            self._say(f"起宿主 MCP 端点失败：{r.get('error')}")
            return None
        url = r["url"]
        try:
            kcfg.set_mcp_server(kcfg.HOST_MCP_NAME, url=url,
                                timeout_ms=kcfg.MCP_TIMEOUT_MS)
        except Exception as e:                                         # noqa: BLE001
            self._say(f"写内核 MCP 配置失败：{type(e).__name__}: {e}")
            return None
        tools = mcp_server.tool_count()
        self._say(f"方向 A 就绪：{tools} 个领域工具 → {url}"
                  f"（timeout={kcfg.MCP_TIMEOUT_MS}ms）")
        return url

    # ------------------------------------------------------- 启动 / 关停

    def start(self, project_name: str | None = None) -> dict:
        """启动内核 + 注册 MCP + 绑定项目 session + 弹 TUI。阻塞，供后台线程调用。"""
        with self._lock:
            out: dict = {"ok": False}
            self._say(f"--- 启动尝试 project={project_name!r} argv={sys.argv[1:]!r} ---")
            self._say(f"隔离 home = {kc.kernel_home()}")
            self._say(f"可执行文件 = {self._exe or kc.opencode_exe() or '(未找到)'}")
            try:
                assets = kcfg.install_builtin_assets()
                if assets.get("installed"):
                    self._say(f"已安装随包 agent/skill：{len(assets['installed'])} 项")
            except Exception as e:                                     # noqa: BLE001
                self._say(f"安装随包资产失败（忽略）：{type(e).__name__}: {e}")
            try:
                self._client = self._client or kc.KernelClient(exe=self._exe or kc.opencode_exe())
                if not self._client.exe:
                    out["error"] = (
                        "找不到 opencode 可执行文件。三种解决方式："
                        "① 使用含内核的产物（PCLRadiomics-windows-x64.zip 解压版，"
                        "或带内核的单文件版）；"
                        "② 设环境变量 PCL_OPENCODE_EXE 指向 opencode.exe；"
                        f"③ 把 opencode.exe 放到 {os.path.join(kc.kernel_home(), 'opencode.exe')}"
                    )
                    self._say("失败：" + out["error"])
                    return out

                state = self._client.ensure_running(timeout=180)
                # ready_seconds 在"接管已有实例"时为 None，绝不能直接 :.2f ——
                # 曾经因为这个 TypeError 打断整条启动流程（内核已起但界面无反应）
                if getattr(self._client, "adopted", False):
                    cost = "接管已在运行的实例，无启动计时"
                elif isinstance(self._client.ready_seconds, (int, float)):
                    cost = f"{self._client.ready_seconds:.2f}s"
                else:
                    cost = "未计时"
                self._say(f"内核已启动 {state.url}（{cost}）"
                          f" 版本 {state.version} pid={state.pid}")

                # 方向 A：必须在建会话之前把 MCP 注册好，内核启动时才连得上
                self._mcp_url = self._ensure_host_mcp()

                sid = None
                if project_name:
                    # 明确关掉这里的 TUI：是否弹终端由下面的 tui_enabled() 单点决定。
                    # （原先用默认 True，会在 PCL_KERNEL_TUI=0 时照样弹窗 ——
                    #   日志里会同时出现"已打开内核界面"和"不打开终端界面"两句自相矛盾的话。）
                    sid = self.ensure_project_session(project_name,
                                                      relaunch_tui=False)["sessionID"]

                if tui_enabled():
                    self._spawn_tui(sid)
                else:
                    self._say("已设 PCL_KERNEL_TUI=0，不打开终端界面")
                self._reap_extra_attach()      # 清掉上次遗留 / 多余的终端窗口

                out.update({"ok": True, "url": state.url, "sessionID": sid,
                            "mcp": self._mcp_url})
                self._say("启动完成")
                return out
            except Exception as e:                                     # noqa: BLE001
                out["error"] = f"{type(e).__name__}: {e}"
                self._say(f"内核联动启动失败：{out['error']}")
                import traceback
                self._say("堆栈：" + traceback.format_exc().replace("\n", " | ")[:800])
                return out

    def stop(self) -> None:
        """关掉我们拉起的 TUI，并停止内核（GUI 退出时调用）。"""
        with self._lock:
            self._kill_tui()
            if self._client:
                try:
                    self._client.stop()
                    self._say("内核已停止")
                except Exception as e:                                 # noqa: BLE001
                    self._say(f"停止内核失败：{type(e).__name__}: {e}")

    def _tui_alive(self) -> bool:
        """TUI 是否仍在运行：Windows 用 Popen 句柄；macOS/Linux 用发现的 attach pid。"""
        if self._tui_pid and kc.KernelClient._pid_alive(self._tui_pid):
            return True
        return self._tui is not None and self._tui.poll() is None

    def _discover_tui_pid(self, session_id: str | None, timeout: float = 6.0) -> int | None:
        """macOS/Linux：osascript/终端句柄不持久，用 `ps` 找到真正的 `opencode attach` pid。"""
        exe = (self._client.exe if self._client else "") or ""
        if not exe:
            return None
        exe_name = os.path.basename(exe) or "opencode"
        kernel_pid = self._client.state.pid if (self._client and self._client.state) else None
        deadline = time.time() + timeout
        while time.time() < deadline:
            for p in kc.list_processes(exe_name):
                cmd = (p.get("cmd") or "").lower()
                if p["pid"] == kernel_pid or "attach" not in cmd:
                    continue
                if session_id and "--session" in cmd and session_id.lower() not in cmd:
                    continue
                return p["pid"]
            time.sleep(0.4)
        return None

    def _kill_tui(self) -> None:
        # 树杀/强杀：只 terminate 父进程会留下孤儿窗口（Windows PowerShell / macOS Terminal）
        for pid in (self._tui_pid, self._tui.pid if self._tui else None):
            if pid and kc.KernelClient._pid_alive(pid):
                try:
                    kc.KernelClient._kill(pid)
                except Exception:                                      # noqa: BLE001
                    pass
        self._tui = None
        self._tui_pid = None

    def _reap_extra_attach(self) -> int:
        """只保留「内核进程 + 当前 TUI」，其余本程序同源的 opencode attach 窗口自动关闭。

        不碰用户自己安装的 opencode（exe 路径不同）。
        """
        try:
            exe = (self._client.exe if self._client else "") or ""
            if not exe:
                return 0
            keep = set()
            if self._client and self._client.state:
                keep.add(self._client.state.pid)
            if self._tui_pid:
                keep.add(self._tui_pid)
            if self._tui and self._tui.poll() is None:
                keep.add(self._tui.pid)
            exe_l = exe.lower()
            exe_name = os.path.basename(exe) or "opencode.exe"
            killed = 0
            for p in kc.list_processes(exe_name):
                if p.get("pid") in keep:
                    continue
                blob = ((p.get("exe") or "") + " " + (p.get("cmd") or "")).lower()
                if exe_l not in blob:
                    continue                       # 不是我们这份 opencode，别动
                if "attach" in (p.get("cmd") or "").lower():
                    try:
                        kc.KernelClient._kill(p["pid"])
                        killed += 1
                    except Exception:                                  # noqa: BLE001
                        pass
            if killed:
                self._say(f"已自动清理 {killed} 个无关的 opencode 终端窗口")
            return killed
        except Exception:                                              # noqa: BLE001
            return 0

    def _toast_tui(self, message: str, variant: str = "success") -> None:
        """在 TUI 里弹一条 toast（失败静默，不影响主流程）。"""
        try:
            if self._client:
                self._client.tui_show_toast(message, variant=variant)
        except Exception:                                              # noqa: BLE001
            pass

    def _ensure_tui(self, session_id: str | None, label: str | None = None) -> None:
        """保证有且仅有一个 TUI：已在运行则让它**内部切到**目标 session，不重开窗口。"""
        if not self._client:
            return
        if self._tui_alive() and session_id:
            try:
                self._client.tui_select_session(session_id)
                self._say(f"TUI 已切换到 session {session_id}（复用同一窗口）")
                self._toast_tui(f"已切换课题：{label}" if label
                                else f"已切换到会话 {session_id}")
                self._reap_extra_attach()
                return
            except Exception as e:                                     # noqa: BLE001
                self._say(f"TUI 切换会话失败，改为重开：{type(e).__name__}: {e}")
        self._spawn_tui(session_id)

    def _spawn_tui(self, session_id: str | None) -> None:
        if not self._client:
            return
        self._kill_tui()                     # 先收掉上一次的 TUI（树杀）
        try:
            # 直接 spawn opencode attach（不经 powershell）：一个进程=一个终端，
            # 既能被 _tui 句柄精确回收，也能被 _reap_extra_attach 识别清理。
            # macOS 走 osascript → Terminal.app（句柄不持久，靠 _discover_tui_pid 找 pid）。
            self._tui = self._client.spawn_tui(session_id=session_id,
                                               via_powershell=False)
            if os.name == "nt":
                self._tui_pid = self._tui.pid if self._tui else None
            else:
                self._tui_pid = self._discover_tui_pid(session_id)
            self._say("已在新终端窗口打开内核界面"
                      + (f"（session {session_id}）" if session_id else ""))
        except Exception as e:                                         # noqa: BLE001
            self._say(f"打开内核终端失败：{type(e).__name__}: {e}")
        self._reap_extra_attach()            # 只留最新这一个

    # ------------------------------------------------ 项目 ↔ 会话（要求 3）

    def ensure_project_session(self, project_name: str,
                               relaunch_tui: bool = True) -> dict:
        """确保该项目有对应 session；没有就新建。返回 {sessionID, created}。"""
        with self._lock:
            if not self._client:
                raise kc.KernelError("内核未启动")
            name = (project_name or "").strip() or "未命名项目"
            known = kcfg.get_project_session(name)
            created = False

            if known and self._client.session_exists(known):
                sid = known
            else:
                if known:
                    self._say(f"项目「{name}」的原 session {known} 已不存在，新建一个")
                # 用 legacy `POST /session` 建会话：V2 建出的 session 走 V1 prompt
                # 不一定被接受，而 legacy 会话与方向 B 的 legacy 投递同源（见 kernel_driver）。
                model = (kcfg.read_config() or {}).get("model")
                try:
                    got = self._client.create_session(title=name, model=model)
                    sid = (got or {}).get("id")
                except Exception:                                      # noqa: BLE001
                    got = self._client.new_session(title=name)
                    sid = (got.get("data") or got).get("id") if isinstance(got, dict) else None
                if not sid:
                    raise kc.KernelError(f"新建 session 失败：{got}")
                kcfg.bind_project_session(name, sid, title=name)
                created = True
                self._say(f"项目「{name}」→ 新建 session {sid}")

            self._project = name
            if relaunch_tui:
                self._ensure_tui(sid, label=name)
            return {"project": name, "sessionID": sid, "created": created}

    def switch_project(self, project_name: str) -> dict:
        """GUI 切项目时调用：切到该项目的 session，并让 TUI 跟过去。"""
        try:
            r = self.ensure_project_session(project_name, relaunch_tui=True)
            verb = "新建" if r["created"] else "切换"
            self._say(f"已{verb}到项目「{r['project']}」的 session {r['sessionID']}")
            return {"ok": True, **r}
        except Exception as e:                                         # noqa: BLE001
            self._say(f"切项目联动失败：{type(e).__name__}: {e}")
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    # --------------------------------------------------- 方向 B 驱动（GUI 用）

    def driver(self):
        """返回方向 B 驱动（惰性创建），供 GUI 把任务投给 opencode。

        未启用内核（跳过联动）时返回 None，调用方据此回落到宿主自身流程。
        """
        with self._lock:
            if self._client is None or not self._client.state:
                return None
            if self._driver is None:
                import kernel_driver as _kd
                self._driver = _kd.KernelDriver(self._client)
            return self._driver

    def run_task(self, project_name: str, text: str, on_event=None,
                 timeout: float = 900.0):
        """把一段任务投给该项目的 session（确保 session 存在后投递）。

        返回事件列表；未启用内核返回 None。
        """
        drv = self.driver()
        if drv is None:
            return None
        r = self.ensure_project_session(project_name, relaunch_tui=False)
        sid = r["sessionID"]
        model = (kcfg.read_config() or {}).get("model")
        return drv.run_turn(sid, text, on_event=on_event, timeout=timeout, model=model)

    def rename_project(self, old_name: str, new_name: str) -> dict:
        """课题改名联动：迁移 session 绑定并让终端跟到**同一个** session（不新建）。"""
        try:
            entry = kcfg.rename_project_session(old_name, new_name)
            if not entry:
                self._say(f"改名：课题「{old_name}」无 session 绑定，跳过")
                return {"ok": True, "migrated": False}
            sid = entry.get("sessionID")
            self._say(f"课题改名：{old_name} → {new_name}（沿用 session {sid}）")
            try:
                self._client.update_session_title(sid, new_name)
                self._say(f"已更新 opencode 会话标题 → {new_name}")
            except Exception as e:                                     # noqa: BLE001
                self._say(f"更新会话标题失败（忽略）：{type(e).__name__}: {e}")
            if self._project == old_name:
                self._project = new_name
                try:
                    self._ensure_tui(sid, label=new_name)
                except Exception as e:                                 # noqa: BLE001
                    self._say(f"改名后重挂终端失败：{type(e).__name__}: {e}")
            return {"ok": True, "migrated": True, "sessionID": sid}
        except Exception as e:                                         # noqa: BLE001
            self._say(f"改名联动失败：{type(e).__name__}: {e}")
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    # ---------------------------------------------------------------- 状态

    def status(self) -> dict:
        return {
            "kernel": self._client.state.as_dict() if (self._client and self._client.state) else None,
            "ready_seconds": self._client.ready_seconds if self._client else None,
            "mcp_url": self._mcp_url,
            "project": self._project,
            "tui_pid": (self._tui_pid if self._tui_pid
                        else (self._tui.pid if (self._tui and self._tui.poll() is None) else None))
                       if self._tui_alive() else None,
            "projects": kcfg.read_projects_map(),
            "autostart": autostart_enabled(),
            "tui_enabled": tui_enabled(),
        }


# ------------------------------------------------------------------ 进程级单例

_BOOT: KernelBoot | None = None
_BOOT_LOCK = threading.Lock()


def instance() -> KernelBoot:
    global _BOOT
    with _BOOT_LOCK:
        if _BOOT is None:
            _BOOT = KernelBoot()
        return _BOOT


# ------------------------------------------------------------------ 离线自检

def selftest() -> int:
    """不联网、不需密钥的自检：配置层 + 二进制 + 项目映射 + 宿主 MCP 端点。"""
    ok = True
    print("== 开关 ==")
    print(f"  自动启动   {autostart_enabled()}")
    print(f"  自动 TUI   {tui_enabled()}")
    print(f"  跳过原因   {should_skip_for_mode() or '（无，可启动）'}")
    print("== 项目 ↔ 会话映射 ==")
    mapping = kcfg.read_projects_map()
    print(f"  文件       {kcfg.projects_map_file()}")
    if mapping:
        for name, entry in sorted(mapping.items()):
            sid = entry.get("sessionID") if isinstance(entry, dict) else entry
            print(f"  {name:32s} → {sid}")
    else:
        print("  （空）")
    print("== 二进制与配置 ==")
    exe = kc.opencode_exe()
    if exe and os.path.exists(exe):
        print(f"  OK  {exe}  {round(os.path.getsize(exe)/1024/1024,1)} MB")
    else:
        print("  FAIL 未找到 opencode 可执行文件")
        ok = False
    try:
        import mcp_server
        print(f"== 方向 A ==\n  工具数 {mcp_server.tool_count()}"
              f"  端点 {mcp_server.http_status().get('url') or '(未启动)'}")
    except Exception as e:                                             # noqa: BLE001
        print(f"== 方向 A ==\n  FAIL 导入 mcp_server：{type(e).__name__}: {e}")
        ok = False
    print("\n结论：" + ("通过" if ok else "存在问题"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest())
