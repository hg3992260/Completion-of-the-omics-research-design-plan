# -*- coding: utf-8 -*-
"""验证 GUI 自主落盘：点一次「一键审阅全流程」→ 自动出批注稿，无需再点落盘。"""
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
    win.goto_step(4)
    app.processEvents()
    mp = win.mr_page
    print("① 左栏控件检查", flush=True)
    print("   审阅层次勾选:", mp.selected_layers(), flush=True)
    print("   自主落盘档位:", mp.autonomy(), flush=True)
    print("   说明:", mp.auto_note.label().text()[:80], flush=True)
    snap("auto_1_options.png")
    QtCore.QTimer.singleShot(300, s2)


def s2():
    print("② 选定审稿批注版（模拟文件对话框）", flush=True)
    win.mr_merge_into = ANN
    win.mr_page._sync_auto_note()
    app.processEvents()
    print("   说明更新为:", win.mr_page.auto_note.label().text()[:110], flush=True)
    QtCore.QTimer.singleShot(200, s3)


def s3():
    print("③ 点「一键审阅全流程」（走真实入口，只跳 LLM 省钱）", flush=True)
    # 走与按钮完全相同的入口：_start('all', path=...)
    win.mr_page._start("all", path=SRC, skip_llm=True)
    QtCore.QTimer.singleShot(1200, snap_busy)


def snap_busy():
    print("   忙碌:", win.busy.is_busy(), "| 状态行:",
          win.mr_page.left_status.label().text()[:60], flush=True)
    snap("auto_2_busy.png")
    QtCore.QTimer.singleShot(1200, wait_done)


_deadline = time.time() + 300


def wait_done():
    th = win.mr_page.thread
    if th is not None and th.isRunning() and time.time() < _deadline:
        QtCore.QTimer.singleShot(700, wait_done)
        return
    app.processEvents()
    QtCore.QTimer.singleShot(700, s4)


def s4():
    p = win.mr_project
    ap = (p.applied if p else {}) or {}
    th = ap.get("threading") or {}
    print("④ 结果（注意：没有再点任何落盘按钮）", flush=True)
    print("   独立批注:", ap.get("comments_added"),
          "| 线程回复:", ap.get("replies_added"),
          "| 正文修订:", ap.get("revisions_added"), flush=True)
    mp = ap.get("merge_plan") or {}
    print("   匹配计划: 回复", mp.get("replies_count"),
          "父", mp.get("parents_used"), "独立", mp.get("standalone"), flush=True)
    print("   线程校验: ok=", th.get("ok"), "嵌套正常=", th.get("nested_ok"),
          "异常=", th.get("nested_bad"), flush=True)
    print("   输出:", p.out_docx if p else "", flush=True)
    print("   报告:", os.path.basename(p.report_path) if p and p.report_path else "", flush=True)
    print("   已入稿指纹:", len(p.applied_keys or []) if p else 0, flush=True)
    snap("auto_3_done.png")
    print("   截图完成，准备收尾", flush=True)
    QtCore.QTimer.singleShot(300, s5)


def s5():
    # 关掉可能弹出的菜单
    for w in app.topLevelWidgets():
        if isinstance(w, QtWidgets.QMenu):
            w.close()
    app.processEvents()
    win.mr_page.pick(1)
    app.processEvents()
    snap("auto_5_layer_stat.png")
    print("截图:", *shots, sep="\n  ")
    win.close()
    app.quit()


QtCore.QTimer.singleShot(900, s1)
sys.exit(app.exec())
