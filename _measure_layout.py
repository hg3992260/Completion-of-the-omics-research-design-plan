# -*- coding: utf-8 -*-
"""量一下中栏/右栏各控件的实际宽度、高度与尺寸策略，定位"填不满"的原因。"""
import os
import sys

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication, QSizePolicy

import design_agent as da
import design_studio as ds

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=False)
win.resize(1638, 830)
p = os.path.join(da.PROJECT_DIR, "未命名课题.json")
if os.path.exists(p):
    win.project = da.Project.load(p)
    win._refresh_all()
win.show()


def pol(w):
    sp = w.sizePolicy()
    return f"{sp.horizontalPolicy().name}/{sp.verticalPolicy().name}"


def dump():
    out = []
    for name in ("center_col", "transcript", "work_scroll", "work",
                 "right_col", "doc_view", "left_col"):
        w = getattr(win, name, None)
        if w is None:
            out.append(f"{name}: 不存在")
            continue
        g = w.geometry()
        out.append(f"{name:12s} x={g.x():5d} y={g.y():4d} w={g.width():5d} h={g.height():4d}"
                   f"  策略={pol(w)}  minW={w.minimumWidth():5d} maxW={w.maximumWidth():5d}"
                   f"  minH={w.minimumHeight():4d} maxH={w.maximumHeight():5d}")
    print("\n".join(out))
    open(r"_layout_measure.txt", "w", encoding="utf-8").write("\n".join(out))
    app.quit()


from PySide6 import QtCore                                          # noqa: E402
QtCore.QTimer.singleShot(1200, dump)
sys.exit(app.exec())
