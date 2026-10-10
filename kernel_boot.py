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
        self._mcp_url: str | None = None
        self._project: str | None = None
        self._log: list[str] = []
        self._exe = exe

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
                self._say(f"内核已启动 {state.url}（{self._client.ready_seconds:.2f}s）"
                          f" 版本 {state.version} pid={state.pid}")

                # 方向 A：必须在建会话之前把 MCP 注册好，内核启动时才连得上
                self._mcp_url = self._ensure_host_mcp()

                sid = None
                if project_name:
                    sid = self.ensure_project_session(project_name)["sessionID"]

                if tui_enabled():
                    self._spawn_tui(sid)
                else:
                    self._say("已设 PCL_KERNEL_TUI=0，不打开终端界面")

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

    def _kill_tui(self) -> None:
        if self._tui and self._tui.poll() is None:
            try:
                self._tui.terminate()
            except Exception:                                          # noqa: BLE001
                pass
        self._tui = None

    def _spawn_tui(self, session_id: str | None) -> None:
        if not self._client:
            return
        self._kill_tui()                     # 同一时刻只保留一个内核 TUI 窗口
        try:
            self._tui = self._client.spawn_tui(session_id=session_id)
            self._say("已在新终端窗口打开内核界面"
                      + (f"（session {session_id}）" if session_id else ""))
        except Exception as e:                                         # noqa: BLE001
            self._say(f"打开内核终端失败：{type(e).__name__}: {e}")

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
                got = self._client.new_session(title=name)
                sid = (got.get("data") or got).get("id") if isinstance(got, dict) else None
                if not sid:
                    raise kc.KernelError(f"新建 session 失败：{got}")
                kcfg.bind_project_session(name, sid, title=name)
                created = True
                self._say(f"项目「{name}」→ 新建 session {sid}")

            self._project = name
            if relaunch_tui:
                self._spawn_tui(sid)
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

    # ---------------------------------------------------------------- 状态

    def status(self) -> dict:
        return {
            "kernel": self._client.state.as_dict() if (self._client and self._client.state) else None,
            "ready_seconds": self._client.ready_seconds if self._client else None,
            "mcp_url": self._mcp_url,
            "project": self._project,
            "tui_pid": self._tui.pid if (self._tui and self._tui.poll() is None) else None,
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
