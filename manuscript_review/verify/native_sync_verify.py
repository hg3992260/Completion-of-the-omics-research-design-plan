# -*- coding: utf-8 -*-
"""同步验证「手稿审阅」原生页面：主线程跑引擎 → 注入项目 → 刷新 → 截图。

不走 QThread：先确认页面渲染与三层数据展示正确；
线程链路单独验证（避免把线程时序问题误判成渲染问题）。
"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample
import os
import sys

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

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sample_manuscript()

set_color_theme(ds.THEME_PATH)
set_appearance_mode("light")
install_button_skin()

# ---- 先把引擎跑完（主线程，确定性强）
from manuscript_review.mr_engine import RevEngine, ReviewProject
from manuscript_review import mr_docx, mr_signals, mr_word, mr_reviewer

eng = RevEngine(None)
proj = ReviewProject()
ok, msg, proj = eng.ingest(SRC, proj)
print("ingest :", ok, msg)
ok, msg, proj = eng.run_signals(proj)
print("signals:", ok, msg)
ok, msg, proj = eng.build_report(proj)
print("report :", ok, os.path.basename(proj.report_path or ""))

ms = eng._manuscript(proj)
plan = mr_word.build_plan(ms, proj.defects, mode="comment_only")   # 只出批注，稳妥
res = mr_word.apply_plan(proj.docx_path, os.path.join(HERE, "native_验证_审阅版.docx"), plan)
proj.applied = res.to_dict()
proj.out_docx = res.out_path if res.ok else ""
print("apply  :", res.ok, f"批注 {res.comments_added} 条 / 修订 {res.revisions_added} 处")
print("defects:", len(proj.defects))

# ---- 建窗口并注入项目
win = ds.StudioWindow(demo=False)
win.mr_project = proj
win.show()
app.processEvents()
win.goto_step(4)
app.processEvents()
print("已切到手稿审阅页, index =", win.body_stack.currentIndex())

shots = []


def snap(name):
    app.processEvents()
    p = os.path.join(HERE, name)
    win.grab().save(p)
    shots.append(p)
    print(f"  截图 {name}  {os.path.getsize(p) // 1024} KB", flush=True)


def s1():
    snap("nat_1_omics.png")
    win.mr_page.pick(1)
    QtCore.QTimer.singleShot(400, s2)


def s2():
    snap("nat_2_stat.png")
    win.mr_page.pick(2)
    QtCore.QTimer.singleShot(400, s3)


def s3():
    snap("nat_3_shape.png")
    win.goto_step(3)
    QtCore.QTimer.singleShot(500, s4)


def s4():
    snap("nat_4_overview.png")
    print("流程条步数:", len(win.flow.steps))
    print("完成")
    win.close()
    app.quit()


QtCore.QTimer.singleShot(900, s1)
sys.exit(app.exec())
