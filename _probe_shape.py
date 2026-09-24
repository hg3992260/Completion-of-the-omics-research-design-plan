# -*- coding: utf-8 -*-
"""渲染 SCI Shape 页面并截图，供肉眼核对布局（不写 projects/）。

用法：  python _probe_shape.py [宽] [高] [章节序号]
产出：  _shots/_shape_light.png / _shape_dark.png / _shape_checked.png
"""
import os
import sys

_argv = sys.argv[1:]
sys.argv = ["x", "--demo"]

from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_studio as ds

W = int(_argv[0]) if len(_argv) > 0 and _argv[0].isdigit() else 1520
H = int(_argv[1]) if len(_argv) > 1 and _argv[1].isdigit() else 960
SEC = int(_argv[2]) if len(_argv) > 2 and _argv[2].isdigit() else 3   # 默认引言

os.makedirs("_shots", exist_ok=True)
app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=True)
win._no_flush = True                    # 演示不落盘
win.resize(W, H)
win.show()


def shoot(tag: str):
    win.layout().activate()
    QApplication.processEvents()
    win.grab().save(f"_shots/_shape_{tag}.png")
    print("saved", tag)


def step1():
    win.show_sci_shape()
    win.shape_page.pick(SEC)
    shoot("light")
    # 勾选前两项，核对完成度与状态联动
    win.shape_page.on_check(0, True)
    win.shape_page.on_check(1, True)
    QApplication.processEvents()
    win.shape_page.refresh()
    shoot("checked")


def step2():
    win.toggle_mode()
    QApplication.processEvents()
    win.shape_page.refresh()
    shoot("dark")
    app.quit()


QtCore.QTimer.singleShot(1200, step1)
QtCore.QTimer.singleShot(2000, step2)
sys.exit(app.exec())
