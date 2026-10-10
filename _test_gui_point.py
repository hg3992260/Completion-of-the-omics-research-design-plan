# -*- coding: utf-8 -*-
"""P2 点验：真实 StudioWindow（offscreen）走 opencode 驱动链路。

验证 PCL_DRIVER=opencode 时：kernel_boot_async → opencode_available →
opencode_run_task 的 Qt 信号回流（kernel_event）与完成后 _oc_busy 复位。
不弹 TUI（PCL_KERNEL_TUI=0）。
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

os.environ["PCL_DRIVER"] = "opencode"
os.environ["PCL_KERNEL_TUI"] = "0"
os.environ["PCL_KERNEL_AUTOSTART"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.argv = ["x"]                        # 不能带 --demo，否则 should_skip_for_mode 跳过内核

from PySide6.QtWidgets import QApplication                              # noqa: E402
from PySide6 import QtCore                                              # noqa: E402
import design_studio as ds                                              # noqa: E402

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=True)
win._no_flush = True
win.show()

seen: list[str] = []
win.kernel_event.connect(lambda t: seen.append(t))
RESULT = {"done": False}


def phase2():
    print("kboot_ready =", win._kboot_ready, flush=True)
    print("driver_mode =", win._driver_mode(), "available =", win.opencode_available(), flush=True)
    if not win.opencode_available():
        print("结论：未通过（opencode 不可用）", flush=True)
        _finish(1)
        return
    win.opencode_run_task(
        "请调用 project_sections 工具，然后只回复 stat 分节的个数（一个数字）。",
        on_done=lambda: QtCore.QTimer.singleShot(500, phase3))


def phase3():
    RESULT["done"] = True
    joined = " | ".join(seen)
    hit_tool = "project_sections" in joined
    hit_num = any(s.strip().isdigit() for s in seen)
    print("oc_busy =", win._oc_busy, flush=True)
    print("events =", joined[:400], flush=True)
    print("tool_seen =", hit_tool, "num_seen =", hit_num, flush=True)
    ok = hit_tool and not win._oc_busy
    print("结论：" + ("通过" if ok else "未通过"), flush=True)
    _finish(0 if ok else 1)


def _finish(code):
    try:
        win.kernel_shutdown()
    except Exception:                                                   # noqa: BLE001
        pass
    RESULT["code"] = code
    app.quit()


def guard():
    if not RESULT.get("done"):
        print("结论：未通过（超时）", flush=True)
        _finish(1)


QtCore.QTimer.singleShot(1500, lambda: win.kernel_boot_async())
QtCore.QTimer.singleShot(25000, phase2)
QtCore.QTimer.singleShot(90000, guard)
app.exec()
sys.exit(RESULT.get("code", 1))
