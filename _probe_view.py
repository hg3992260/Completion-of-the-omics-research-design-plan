# -*- coding: utf-8 -*-
"""在指定尺寸下渲染两个界面，供肉眼核对遮挡（渲染前强制完成布局）。"""
import sys

_argv = sys.argv[1:]
sys.argv = ["x", "--demo"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_studio as ds
import omics_pipeline as op

W = int(_argv[0]) if len(_argv) > 0 and _argv[0].isdigit() else 1200
H = int(_argv[1]) if len(_argv) > 1 and _argv[1].isdigit() else 700

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
a = ds.StudioWindow(demo=True)
a.resize(W, H)
a.show()
b = op.MainWindow()
b.resize(W, H)
b.show()


def shoot():
    a.layout().activate()
    b.layout().activate()
    QApplication.processEvents()
    a.grab().save(f"_shots/_view_{W}x{H}_studio.png")
    b.grab().save(f"_shots/_view_{W}x{H}_pipeline.png")
    print("saved", W, H)
    app.quit()


QtCore.QTimer.singleShot(1200, shoot)
sys.exit(app.exec())
