# -*- coding: utf-8 -*-
"""验证「手稿审阅」原生页面：真实导入手稿 → 核验 → 落盘，并逐页截图。

要点：退出前必须等在跑的 QThread 结束（model 列表线程 + 审阅线程），
否则解释器会在 QThread 仍运行时销毁对象而报 "Destroyed while thread is still running"。
"""
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

set_color_theme(ds.THEME_PATH)
set_appearance_mode("light")
install_button_skin()

win = ds.StudioWindow(demo=False)
win.show()
app.processEvents()

shots = []
STATE = {"deadline": time.time() + 300}


def snap(name):
    app.processEvents()
    p = os.path.join(HERE, name)
    win.grab().save(p)
    shots.append(p)
    print(f"  截图 {name}  {os.path.getsize(p) // 1024} KB", flush=True)


def wait_threads(then, tag=""):
    """等所有 QThread 结束再继续（轮询，不阻塞事件循环）。"""
    def poll():
        busy = [t for t in win.findChildren(QtCore.QThread) if t.isRunning()]
        mp = win.mr_page
        if mp.thread is not None and mp.thread.isRunning():
            busy.append(mp.thread)
        if busy and time.time() < STATE["deadline"]:
            QtCore.QTimer.singleShot(600, poll)
            return
        if busy:
            print(f"  [{tag}] 超时，仍有 {len(busy)} 个线程在跑", flush=True)
        then()
    QtCore.QTimer.singleShot(600, poll)


def s1():
    print("① 空态页面", flush=True)
    win.goto_step(4)
    app.processEvents()
    QtCore.QTimer.singleShot(500, lambda: (snap("native_1_empty.png"), s2()))


def s2():
    print("② 导入 → 确定性核验 → 报告 → 落盘 Word（后台线程）", flush=True)
    win.mr_page._start("all", path=SRC, skip_llm=True)
    wait_threads(s3, "run")


def s3():
    print("③ 三层明细逐个截图", flush=True)
    win.mr_page.pick(0)
    app.processEvents()
    snap("native_2_layer_omics.png")

    def nxt():
        win.mr_page.pick(1)
        app.processEvents()
        snap("native_3_layer_stat.png")
        QtCore.QTimer.singleShot(300, nxt2)
    QtCore.QTimer.singleShot(300, nxt)


def nxt2():
    win.mr_page.pick(2)
    app.processEvents()
    snap("native_4_layer_shape.png")
    QtCore.QTimer.singleShot(300, s4)


def s4():
    print("④ 回到工作台与总览，确认原有页面未受影响", flush=True)
    win.goto_step(3)
    app.processEvents()
    snap("native_5_overview.png")
    win.goto_step(0)
    app.processEvents()
    QtCore.QTimer.singleShot(300, lambda: (snap("native_6_workbench.png"), s5()))


def s5():
    p = win.mr_project
    print()
    print("=== 原生页面内结果 ===")
    if p:
        print("  项目    :", p.name)
        print("  段落    :", (p.manuscript or {}).get("paragraphs"), "段")
        print("  章节    :", len(p.outline or []))
        print("  信号    :", p.signal_summary)
        print("  缺陷    :", (p.summary or {}).get("total"))
        print("  批注    :", (p.applied or {}).get("comments_added"))
        print("  修订    :", (p.applied or {}).get("revisions_added"))
        print("  校验    :", (p.applied or {}).get("verify", {}).get("ok"))
    print("  截图:", *shots, sep="\n    ")
    print()
    print("流程条步数:", len(win.flow.steps))
    wait_threads(lambda: (win.close(), app.quit()), "exit")


QtCore.QTimer.singleShot(800, s1)
QtCore.QTimer.singleShot(360000, app.quit)
rc = app.exec()
print("退出码:", rc)
