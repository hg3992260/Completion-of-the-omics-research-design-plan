# -*- coding: utf-8 -*-
"""渲染 Statistic 页并截图（浅色 / 深色 / 含速查表的阶段 6），供肉眼核对。"""
import os
import sys

_argv = sys.argv[1:]
sys.argv = ["x", "--demo"]

from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_studio as ds

W = int(_argv[0]) if len(_argv) > 0 and _argv[0].isdigit() else 1520
H = int(_argv[1]) if len(_argv) > 1 and _argv[1].isdigit() else 960
os.makedirs("_shots", exist_ok=True)

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=True)
win._no_flush = True
win.resize(W, H)
win.show()


def shoot(tag):
    win.layout().activate()
    QApplication.processEvents()
    win.grab().save(f"_shots/_stat_{tag}.png")
    print("saved", tag, flush=True)


def step1():
    win.show_stat()
    win.stat_page.pick(0)                      # 阶段 1
    shoot("light")
    win.stat_page.pick(5)                      # 阶段 6：检验计算（含速查表）
    QApplication.processEvents()
    win.stat_page.detail_host.grab().save("_shots/_stat_stage6_detail.png")
    shoot("stage6")


def step2():
    win.stat_page.pick(0)
    win.toggle_mode()
    QApplication.processEvents()
    win.stat_page.refresh()
    shoot("dark")
    win.stat_page.check_host.grab().save("_shots/_stat_checks.png")
    app.quit()


QtCore.QTimer.singleShot(1200, step1)
QtCore.QTimer.singleShot(2200, step2)
sys.exit(app.exec())
