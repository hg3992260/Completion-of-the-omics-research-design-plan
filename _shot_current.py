# -*- coding: utf-8 -*-
"""渲染真实项目下的界面（稳健版）：整窗 + 三栏分别截图。"""
import os
import sys
import traceback

_argv = sys.argv[1:]
sys.argv = ["x"]

from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_agent as da
import design_studio as ds

W = int(_argv[0]) if _argv and _argv[0].isdigit() else 1638
H = int(_argv[1]) if len(_argv) > 1 and _argv[1].isdigit() else 830
PROJ = _argv[2] if len(_argv) > 2 else "未命名课题.json"

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=False)
win.resize(W, H)
path = os.path.join(da.PROJECT_DIR, PROJ)
if os.path.exists(path):
    win.project = da.Project.load(path)
    win._refresh_all()
win.show()


def shot():
    try:
        QApplication.processEvents()
        win.grab().save(f"_shots/_cur_{W}x{H}.png")
        print("saved full")
        # 报告各栏几何，便于量化
        for name in ("left_col", "side_col", "work_scroll", "doc_view", "transcript",
                     "body_stack"):
            wdg = getattr(win, name, None)
            if wdg is None:
                continue
            g = wdg.geometry()
            print(f"  {name}: x={g.x()} y={g.y()} w={g.width()} h={g.height()}")
            try:
                wdg.grab().save(f"_shots/_cur_{name}.png")
            except Exception:
                pass
    except Exception:
        traceback.print_exc()
    finally:
        app.quit()


QtCore.QTimer.singleShot(1600, shot)
sys.exit(app.exec())
