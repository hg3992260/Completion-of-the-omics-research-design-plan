# -*- coding: utf-8 -*-
"""量测 SCI Shape 中栏/右栏控件的真实宽度与高度，并单独抓取两栏图像。"""
import os
import sys

sys.argv = ["x", "--demo"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_studio as ds
from ui_kit import RefitLabel, text_height

SEC = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3
os.makedirs("_shots", exist_ok=True)
app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=True)
win._no_flush = True
win.resize(1520, 960)
win.show()


def dump():
    win.show_sci_shape()
    win.shape_page.pick(SEC)
    win.layout().activate()
    QApplication.processEvents()
    QtCore.QTimer.singleShot(300, dump2)


def dump2():
    win.shape_page.detail_host.grab().save("_shots/_shape_detail.png")
    win.shape_page.check_host.grab().save("_shots/_shape_checks.png")
    lines = []
    host = win.shape_page.detail_host
    lines.append(f"detail host: w={host.width()} h={host.height()}")
    bad = 0
    for lbl in host.findChildren(RefitLabel):
        inner = lbl.label()
        need = text_height(inner.text(), lbl._font_size, max(40, lbl.width() - 12),
                           lbl._font_style == "bold")
        innerh = inner.height()
        flag = "  <== 不足" if need > innerh + 1 else ""
        if flag:
            bad += 1
        lines.append(f"w={lbl.width():4d} 给定高={innerh:4d} 需要高={need:4d}{flag}"
                     f" | {inner.text()[:46]}")
    lines.append(f"\n高度不足的标签数：{bad}")
    txt = "\n".join(lines)
    open("_shape_measure.txt", "w", encoding="utf-8").write(txt)
    print(txt[:3000])
    app.quit()


QtCore.QTimer.singleShot(1200, dump)
sys.exit(app.exec())
