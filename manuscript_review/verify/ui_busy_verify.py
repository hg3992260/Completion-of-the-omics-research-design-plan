# -*- coding: utf-8 -*-
"""验证「审阅进行中」是否醒目 + 页脚按钮在各视图回归。

做法：先把审阅项目注入（不依赖线程时序），
再手动进入 busy 状态并让计时器跑几秒，截图看底部动画与左栏状态行。
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


def snap(name):
    app.processEvents()
    p = os.path.join(HERE, name)
    win.grab().save(p)
    shots.append(p)
    print(f"  截图 {name}  {os.path.getsize(p) // 1024} KB", flush=True)


def s1():
    print("① 注入审阅项目（主线程跑引擎，确定性）", flush=True)
    from manuscript_review.mr_engine import RevEngine, ReviewProject
    eng = RevEngine(None)
    p = ReviewProject()
    ok, msg, p = eng.ingest(SRC, p)
    print("   ingest:", ok, msg, flush=True)
    ok, msg, p = eng.run_signals(p)
    print("   signals:", ok, msg, flush=True)
    win.mr_project = p
    win.goto_step(4)
    app.processEvents()
    print("   左栏状态行:", win.mr_page.left_status.label().text(), flush=True)
    print("   继续按钮:", win.foot_btns['continue'].button().text(), flush=True)
    snap("uiB_1_idle_with_data.png")
    QtCore.QTimer.singleShot(400, s2)


def s2():
    print("② 进入忙碌状态，观察是否醒目", flush=True)
    win.mr_page._busy(True, "正在做语义审阅（LLM）")
    print("   底部动画忙碌:", win.busy.is_busy(), flush=True)
    print("   左栏状态行:", win.mr_page.left_status.label().text(), flush=True)
    print("   继续按钮:", win.foot_btns['continue'].button().text(),
          "可用=", win.foot_btns['continue'].isEnabled(), flush=True)
    snap("uiB_2_busy_t0.png")
    QtCore.QTimer.singleShot(3200, s3)


def s3():
    print("③ 3 秒后（计时应递增）", flush=True)
    print("   左栏状态行:", win.mr_page.left_status.label().text(), flush=True)
    snap("uiB_3_busy_t3.png")
    win.mr_page._busy(False)
    app.processEvents()
    print("④ 结束后状态行:", win.mr_page.left_status.label().text(), flush=True)
    print("   底部动画忙碌:", win.busy.is_busy(), flush=True)
    print("   继续按钮:", win.foot_btns['continue'].button().text(), flush=True)
    snap("uiB_4_done.png")
    QtCore.QTimer.singleShot(400, s4)


def s4():
    print("⑤ 各视图页脚按钮回归", flush=True)
    for i, name in enumerate(["设计工作台", "统计", "Shape", "总览", "手稿审阅"]):
        win.goto_step(i)
        app.processEvents()
        print(f"   {name}: 继续={win.foot_btns['continue'].button().text()!r} "
              f"保存可用={win.foot_btns['save'].isEnabled()} "
              f"导出可用={win.foot_btns['export'].isEnabled()}", flush=True)
    snap("uiB_5_last_view.png")
    print("完成")
    win.close()
    app.quit()


QtCore.QTimer.singleShot(900, s1)
sys.exit(app.exec())
