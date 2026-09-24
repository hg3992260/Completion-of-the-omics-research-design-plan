# -*- coding: utf-8 -*-
"""在指定尺寸下依次截取四个视图（默认 1120×700 最窄窗口），用于肉眼核对。"""
import os
import sys

_argv = sys.argv[1:]
sys.argv = ["x", "--demo"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_studio as ds

W = int(_argv[0]) if _argv and _argv[0].isdigit() else 1120
H = int(_argv[1]) if len(_argv) > 1 and _argv[1].isdigit() else 700
DARK = "--dark" in _argv
os.makedirs("_shots", exist_ok=True)

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("dark" if DARK else "light")
win = ds.StudioWindow(demo=True)
win._no_flush = True
win.resize(W, H)
win.show()

VIEWS = [("work", "show_workspace"), ("stat", "show_stat"),
         ("shape", "show_sci_shape"), ("over", "show_overview")]
tag0 = "dark" if DARK else "light"


def run():
    for name, fn in VIEWS:
        getattr(win, fn)()
        for _ in range(2):
            win.layout().activate()
            QApplication.processEvents()
        win.grab().save(f"_shots/_v{W}_{name}_{tag0}.png")
        print("saved", name, W, H, flush=True)
    app.quit()


QtCore.QTimer.singleShot(1200, run)
sys.exit(app.exec())
