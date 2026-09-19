# -*- coding: utf-8 -*-
"""Windows 下的标准流接管：让"一个 exe 既当图形程序又当 stdio 服务"成立。

背景：PyInstaller 的 windowed（GUI 子系统）构建里 `sys.stdout/stdin/stderr` 都是 None。
- MCP stdio 传输：客户端是用**管道**拉起我们的（STARTUPINFO 里给了句柄），
  句柄其实有效，只是 Python 没把它包成流 —— 这里包回来。
- 从 cmd/PowerShell 手敲命令：父进程有控制台，`AttachConsole(-1)` 附加上去，
  重新打开 CONOUT$/CONIN$，日志照常显示。
- 双击启动图形界面：两者都没有 → 落到 devnull，进程安安静静跑 GUI，
  不会出现黑框（Win11 上控制台由 Windows Terminal 托管，靠 ShowWindow 是藏不掉的）。

这样就不必为了 stdio 而把整个程序编成 console 子系统，图形模式永远干净。
"""

from __future__ import annotations

import os
import sys

_INVALID = (0, -1)


def _wrap_handle(handle: int, name: str) -> bool:
    """把内核句柄包成 Python 文本流（带 .buffer，MCP SDK 会用到）。"""
    import io
    import msvcrt

    try:
        if name == "stdin":
            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            sys.stdin = io.TextIOWrapper(open(fd, "rb", buffering=0, closefd=False),
                                         encoding="utf-8", errors="replace")
        else:
            fd = msvcrt.open_osfhandle(handle, os.O_WRONLY | getattr(os, "O_BINARY", 0))
            stream = io.TextIOWrapper(open(fd, "wb", buffering=0, closefd=False),
                                      encoding="utf-8", errors="replace",
                                      write_through=True, line_buffering=True)
            setattr(sys, name, stream)
        return True
    except Exception:                                              # noqa: BLE001
        return False


def attach_inherited_stdio() -> dict:
    """接管父进程通过 STARTUPINFO 传下来的管道（MCP stdio 场景）。"""
    if os.name != "nt":
        return {}
    import ctypes
    k32 = ctypes.windll.kernel32
    kinds = {"stdin": -10, "stdout": -11, "stderr": -12}
    got = {}
    for name, hid in kinds.items():
        if getattr(sys, name, None) is not None:
            continue
        h = k32.GetStdHandle(hid)
        if h in _INVALID or h is None:
            continue
        if k32.GetFileType(h) == 0:                  # FILE_TYPE_UNKNOWN → 句柄无效
            continue
        got[name] = _wrap_handle(h, name)
    return got


def attach_parent_console() -> bool:
    """从 cmd/PowerShell 启动时附加上父进程的控制台（GUI 子系统默认不附加）。"""
    if os.name != "nt":
        return False
    import ctypes
    if not ctypes.windll.kernel32.AttachConsole(-1):   # ATTACH_PARENT_PROCESS
        return False
    ok = False
    for name, dev, mode in (("stdin", "CONIN$", "r"), ("stdout", "CONOUT$", "w"),
                            ("stderr", "CONOUT$", "w")):
        if getattr(sys, name, None) is not None:
            continue
        try:
            setattr(sys, name, open(dev, mode, encoding="utf-8", errors="replace",
                                    buffering=1 if mode == "w" else -1))
            ok = True
        except Exception:                                          # noqa: BLE001
            continue
    return ok


def silence_streams() -> None:
    """都没有 → 补 devnull，避免任何 write 崩在 None 上。"""
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            try:
                setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
            except Exception:                                      # noqa: BLE001
                pass
    if getattr(sys, "stdin", None) is None:
        try:
            sys.stdin = open(os.devnull, "r", encoding="utf-8")
        except Exception:                                          # noqa: BLE001
            pass


def setup_stdio() -> str:
    """按 管道 → 父控制台 → devnull 的顺序接好标准流，返回接管方式。"""
    pipe = attach_inherited_stdio()
    if pipe.get("stdin") and pipe.get("stdout"):
        silence_streams()
        return "inherited-pipe"                       # MCP 客户端用管道拉起
    if attach_parent_console():
        silence_streams()
        return "parent-console"                       # 从终端手敲命令
    silence_streams()
    return "none"                                     # 双击图形界面：静默
