# -*- coding: utf-8 -*-
"""模拟用户双击：图形模式下到底会不会弹出黑色控制台窗口。"""
import ctypes
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(ROOT, "dist", "PCLRadiomics")
EXE = os.path.join(APP_DIR, "PCLRadiomics.exe")
OUT = os.path.join(ROOT, "_console_check.txt")
lines = []

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32


def visible_windows():
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _):
        if not u32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd, cls, 256)
        title = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(hwnd, title, 256)
        pid = ctypes.c_ulong()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        out.append((cls.value, title.value.strip(), pid.value))
        return True

    u32.EnumWindows(WNDENUMPROC(cb), None)
    return out


before = visible_windows()
consoles_before = [w for w in before if "Console" in w[0] or "Terminal" in w[0]]
lines.append(f"启动前可见控制台/终端窗口：{len(consoles_before)} 个"
             f" {[t or c for c, t, p in consoles_before][:4]}")

# pythonw 方式启动（等价于双击，不继承本会话的控制台）
subprocess.Popen([EXE, "gui"], cwd=APP_DIR,
                 creationflags=0x00000008 | 0x08000000,   # DETACHED_PROCESS | CREATE_NO_WINDOW
                 close_fds=True)
time.sleep(16)
after = visible_windows()
new_windows = [w for w in after if w not in before]
lines.append("启动后新增的可见窗口：")
for c, t, p in new_windows:
    lines.append(f"   class={c!r} title={t[:40]!r} pid={p}")
consoles_after = [w for w in after if "Console" in w[0] or "Terminal" in w[0]]
lines.append(f"启动后可见控制台/终端窗口：{len(consoles_after)} 个")
lines.append("结论：" + ("没有多出控制台窗口 —— 图形模式干净"
                     if len(consoles_after) <= len(consoles_before) else
                     "多出了控制台窗口，需要改方案"))

# 收尾：关掉刚启动的进程
import json
subprocess.run(["taskkill", "/F", "/IM", "PCLRadiomics.exe"],
               capture_output=True)
open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
