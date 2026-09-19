# -*- coding: utf-8 -*-
"""管线视图（表格）自检：行数/列数/状态分布/只读属性 + 截图。"""
import sys

_argv = sys.argv[1:]
sys.argv = ["x", "--demo"]
from PySide6.QtWidgets import QApplication, QAbstractItemView
from PySide6 import QtCore

import design_studio as ds
import omics_pipeline as op

W = int(_argv[0]) if _argv and _argv[0].isdigit() else 1520
H = int(_argv[1]) if len(_argv) > 1 and _argv[1].isdigit() else 960

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
a = ds.StudioWindow(demo=True)
a.resize(W, H)
a.show()
b = op.MainWindow()
b.resize(W, H)
b.show()

info = []


def step():
    a.show_overview()
    QApplication.processEvents()

    def check():
        t = a.ov_table
        info.append(f"视图索引={a.body_stack.currentIndex()}（1=表格视图）")
        info.append(f"表头={a.ov_cols}")
        info.append(f"行数={t.rowCount()} 列数={t.columnCount()}")
        info.append(f"只读: 编辑触发={t.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers}"
                    f" 选择模式={t.selectionMode().name} 焦点策略={t.focusPolicy().name}")
        info.append(f"行高={t.verticalHeader().defaultSectionSize()} "
                    f"表头高={t.horizontalHeader().height()}")
        for r in range(t.rowCount()):
            vals = [t.item(r, c).text() if t.item(r, c) else "" for c in range(t.columnCount())]
            info.append("  " + " | ".join(vals))
        info.append(f"汇总={a.ov_summary.label().text()}")
        a.grab().save(f"_shots/_table_{W}x{H}.png")
        t.grab().save(f"_shots/_table_only_{W}x{H}.png")
        open("_ov_check.txt", "w", encoding="utf-8").write("\n".join(info))
        print("done")
        app.quit()

    QtCore.QTimer.singleShot(800, check)


QtCore.QTimer.singleShot(900, step)
sys.exit(app.exec())
