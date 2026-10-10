# -*- coding: utf-8 -*-
"""自检：底部「MCP 状态 / 操作日志」可折叠面板的渲染与缩放。"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PCL_KERNEL_AUTOSTART"] = "0"
sys.argv = ["x", "--demo"]

from PySide6.QtWidgets import QApplication                              # noqa: E402
from PySide6 import QtCore                                              # noqa: E402
import design_studio as ds                                              # noqa: E402

os.makedirs("_shots", exist_ok=True)
app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=True)
win._no_flush = True
win.resize(1400, 900)
win.show()
for _ in range(3):
    win.layout().activate()
    QApplication.processEvents()

ok = True


def run():
    global ok
    try:
        print("has console_log =", hasattr(win, "console_log"), flush=True)
        win.gui_log("测试：UI 自检开始")
        win.set_current(3)                      # 触发一条阶段切换日志
        win.refresh_console()
        head = win.console_head.label().text()
        print("head =", head, flush=True)
        win.toggle_console()                    # 展开
        QApplication.processEvents()
        win.grab().save("_shots/_console_open.png")
        print("expanded visible =", win.console_body.isVisible(), flush=True)
        ok = hasattr(win, "console_log") and win.console_body.isVisible()
        win.toggle_console()                    # 折叠
        QApplication.processEvents()
        win.grab().save("_shots/_console_closed.png")
        print("collapsed visible =", win.console_body.isVisible(), flush=True)
        ok = ok and (not win.console_body.isVisible())
    except Exception as e:                                          # noqa: BLE001
        ok = False
        print("EXC:", type(e).__name__, e, flush=True)
    print("结论：" + ("通过" if ok else "未通过"), flush=True)
    app.quit()


QtCore.QTimer.singleShot(800, run)
app.exec()
sys.exit(0 if ok else 1)
