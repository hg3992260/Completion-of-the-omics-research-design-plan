# -*- coding: utf-8 -*-
"""验证双向联动：切课题 → 自动切到该课题绑定的手稿；无绑定时清空。"""
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
from design_agent import Project
from PyCt6 import set_appearance_mode, set_color_theme
from ui_kit import install_button_skin

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sample_manuscript()

set_color_theme(ds.THEME_PATH)
set_appearance_mode("light")
install_button_skin()

# ---- 先造两个课题：A 会绑定手稿，B 不绑
A, B = "联动课题A", "联动课题B"
paths = {}
for nm in (A, B):
    p = Project.unique_path(nm)
    if os.path.exists(p):
        os.remove(p)
    pr = Project.new(nm, raw=f"{nm} 的初步设想：回顾性单中心影像组学研究。")
    paths[nm] = pr.path
print("① 已造课题:", A, "|", B)

win = ds.StudioWindow(demo=False)
win.show()
app.processEvents()
mp = win.mr_page
shots = []


def snap(name):
    app.processEvents()
    p = os.path.join(HERE, name)
    win.grab().save(p)
    shots.append(p)
    print(f"  截图 {name}  {os.path.getsize(p) // 1024} KB", flush=True)


def state(tag):
    cur = win.project.name
    mr = win.mr_project.name if win.mr_project else None
    n = len(getattr(win.project, "manuscripts", []) or [])
    print(f"  [{tag}] 课题={cur!r} 绑定手稿数={n} 审阅项目={mr!r}", flush=True)
    print(f"        左栏提示: {mp.link_lbl.label().text()}", flush=True)


def switch_to(name):
    """走与下拉框完全相同的入口。"""
    win._on_project_pick(name)
    app.processEvents()
    for _ in range(5):
        app.processEvents()


def wait_import(then):
    def poll():
        th = mp.thread
        if th is not None and th.isRunning():
            QtCore.QTimer.singleShot(400, poll)
            return
        app.processEvents()
        QtCore.QTimer.singleShot(500, then)
    QtCore.QTimer.singleShot(400, poll)


def s1():
    print()
    print("② 切到课题 A，导入一份手稿（应自动登记为 A 的手稿）")
    switch_to(A)
    state("切到A")
    mp._start("import", path=SRC)
    wait_import(s2)


def s2():
    state("A 导入后")
    pa = win.project
    print(f"    A.manuscripts = {len(pa.manuscripts or [])} 条", flush=True)
    a_mr = win.mr_project.name if win.mr_project else None
    snap("duo_1_A_bound.png")
    print()
    print("③ 切到课题 B（B 没有手稿 → 应清空审阅视图）")
    switch_to(B)
    state("切到B")
    snap("duo_2_B_cleared.png")
    print()
    print("④ 切回课题 A（应自动切回 A 绑定的手稿）")
    switch_to(A)
    state("切回A")
    back = win.mr_project.name if win.mr_project else None
    print(f"    自动切回的手稿与导入时一致: {back == a_mr} （{a_mr!r} → {back!r}）",
          flush=True)
    snap("duo_3_back_to_A.png")
    print()
    print("⑤ 再切 B 再切 A 往返一次，确认稳定")
    switch_to(B)
    b1 = win.mr_project
    switch_to(A)
    a1 = win.mr_project.name if win.mr_project else None
    print(f"    B 时审阅项目={b1!r}；A 时={a1!r}", flush=True)
    print()
    print("⑥ 边界：把 A 登记的审阅项目文件删掉，再切到 A")
    ap = paths[A]
    rec = Project.load(ap).latest_manuscript()
    mrpath = rec.get("project_path") or ""
    if mrpath and os.path.exists(mrpath):
        os.remove(mrpath)
    print(f"    已删除绑定文件: {os.path.basename(mrpath)}", flush=True)
    switch_to(B)
    switch_to(A)
    print(f"    切到 A 后审阅项目={win.mr_project!r}（应保持 None，且不崩）", flush=True)
    print()
    print("截图:", *shots, sep="\n  ")

    # 清理
    for p in (paths[A], paths[B]):
        try:
            os.remove(p)
        except Exception:
            pass
    for f in (mrpath,):
        try:
            if f and os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
    print("（已清理测试课题）")
    win.close()
    app.quit()


QtCore.QTimer.singleShot(800, s1)
QtCore.QTimer.singleShot(180000, app.quit)
sys.exit(app.exec())
