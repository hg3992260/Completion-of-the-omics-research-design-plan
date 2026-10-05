# -*- coding: utf-8 -*-
"""复现：启动工作台后正常关闭，看退出码与 stderr。

怀疑点：__init__ 里的 _fetch_models() 起了一个 ModelListThread，
关闭窗口时若该线程仍在运行，shiboken 会在对象析构时报
"QThread: Destroyed while thread is still running" 并以非 0 退出。
"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PySide6 import QtCore, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
import design_studio as ds
from PyCt6 import set_appearance_mode, set_color_theme
from ui_kit import install_button_skin

set_color_theme(ds.THEME_PATH)
set_appearance_mode("light")
install_button_skin()

print("构建窗口…", flush=True)
win = ds.StudioWindow(demo=False)
win.show()
app.processEvents()
print("窗口已显示", flush=True)

# 列出当前在跑的 QThread
def running(tag):
    ts = [t for t in win.findChildren(QtCore.QThread) if t.isRunning()]
    print(f"  [{tag}] 运行中的 QThread: {len(ts)} -> "
          f"{[type(t).__name__ for t in ts]}", flush=True)
    return ts

running("显示后")
print("关闭窗口…", flush=True)
win.close()
app.processEvents()
running("close() 之后")
print("调用 app.quit()…", flush=True)
app.quit()
rc = app.exec() if False else 0
print("退出码:", rc, flush=True)
print("如果上面出现 'QThread: Destroyed while thread is still running'，就是关闭期崩溃点", flush=True)
