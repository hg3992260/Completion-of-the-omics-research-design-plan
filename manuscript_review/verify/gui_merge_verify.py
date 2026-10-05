# -*- coding: utf-8 -*-
"""验证原生 GUI 的「并入审稿批注版」路径：选文件（绕过对话框）→ 跑 apply → 截图。"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample
import os
import sys
import time

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
ANN = annotated_sample()

set_color_theme(ds.THEME_PATH)
set_appearance_mode("light")
install_button_skin()

win = ds.StudioWindow(demo=False)
win.show()
app.processEvents()
shots = []


def snap(name):
    app.processEvents()
    p = os.path.join(HERE, name)
    win.grab().save(p)
    shots.append(p)
    print(f"  截图 {name}  {os.path.getsize(p) // 1024} KB", flush=True)


def s1():
    print("① 注入审阅结果（主线程跑引擎）", flush=True)
    from manuscript_review.mr_engine import RevEngine, ReviewProject
    eng = RevEngine(None)
    p = ReviewProject(name="gui_merge_test")
    ok, msg, p = eng.ingest(SRC, p)
    print("   ingest:", ok, flush=True)
    ok, msg, p = eng.run_signals(p)
    print("   signals:", ok, msg, flush=True)
    win.mr_project = p
    print("② 模拟「选择审稿批注版…」（绕过文件对话框）", flush=True)
    win.mr_merge_into = ANN
    from manuscript_review import mr_thread
    info = mr_thread.probe(ANN)
    win.mr_page._log(f"已选定并入底板：{os.path.basename(ANN)}"
                     f"（审稿批注 {info['count']} 条｜作者："
                     f"{'、'.join(info['authors'])}）", "ok")
    win.goto_step(4)
    app.processEvents()
    print("   左栏状态:", win.mr_page.left_status.label().text(), flush=True)
    snap("guiM_1_selected.png")
    QtCore.QTimer.singleShot(300, s2)


def s2():
    print("③ 点「并入批注版（线程回复）」", flush=True)
    win.mr_page._start("apply")
    QtCore.QTimer.singleShot(1500, snap_busy)


def snap_busy():
    print("   忙碌态:", win.busy.is_busy(), "| 状态行:",
          win.mr_page.left_status.label().text(), flush=True)
    snap("guiM_2_busy.png")
    QtCore.QTimer.singleShot(1000, wait_done)


_deadline = time.time() + 240


def wait_done():
    th = win.mr_page.thread
    if th is not None and th.isRunning() and time.time() < _deadline:
        QtCore.QTimer.singleShot(700, wait_done)
        return
    app.processEvents()
    QtCore.QTimer.singleShot(600, s3)


def s3():
    print("④ 结束后检查", flush=True)
    p = win.mr_project
    ap = (p.applied if p else {}) or {}
    print("   comments_added:", ap.get("comments_added"),
          "| replies_added:", ap.get("replies_added"), flush=True)
    print("   threading ok:", (ap.get("threading") or {}).get("ok"),
          (ap.get("threading") or {}).get("problems"), flush=True)
    mp = ap.get("merge_plan") or {}
    print("   merge_plan: 回复", mp.get("replies_count"),
          "父", mp.get("parents_used"), "独立", mp.get("standalone"), flush=True)
    print("   out_docx:", p.out_docx if p else "", flush=True)
    print("   状态行:", win.mr_page.left_status.label().text(), flush=True)
    snap("guiM_3_done.png")
    # 顺带看「执行日志」页
    win.tabs.setCurrentWidget(win.mr_transcript) if False else None
    win.mr_page.pick(0)
    app.processEvents()
    snap("guiM_4_layer.png")
    print("截图:", *shots, sep="\n  ")
    win.close()
    app.quit()


QtCore.QTimer.singleShot(900, s1)
sys.exit(app.exec())
