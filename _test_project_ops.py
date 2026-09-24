# -*- coding: utf-8 -*-
"""一级 GUI 的项目命名 / 删除 功能验证（在临时目录里跑，不污染 projects/）。"""
import os
import shutil
import sys

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_agent as da

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_nametest")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
da.PROJECT_DIR = TMP

import design_studio as ds

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=False)
win.resize(1520, 960)
win.show()
RESULT = []


def check(name, cond):
    RESULT.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name)


def files():
    return sorted(os.listdir(TMP))


def run():
    try:
        _run()
    except Exception:                                       # noqa: BLE001
        import traceback
        print(traceback.format_exc(), flush=True)
        RESULT.append(("run() 抛异常", False))
    finally:
        fails = sum(1 for _, v in RESULT if not v)
        print(f"\n合计 {len(RESULT)} 项，失败 {fails} 项", flush=True)
        open("_name_test.txt", "w", encoding="utf-8").write(
            "\n".join(f"{'PASS' if v else 'FAIL'}  {k}" for k, v in RESULT)
            + f"\n\n合计 {len(RESULT)} 项，失败 {fails} 项\n")
        app.quit()


def _run():
    win.layout().activate()
    QApplication.processEvents()

    # 1 页头上确实有一级入口
    check("页头存在「重命名」按钮", hasattr(win, "rename_btn"))
    check("页头存在「删除」按钮", hasattr(win, "delete_btn"))
    check("按钮文案正确",
          win.rename_btn.button().text() == "改名"
          and win.delete_btn.button().text() == "删除")
    check("两个按钮在页头上可见",
          win.rename_btn.isVisible() and win.delete_btn.isVisible())

    # 2 重命名对话框能打开（不清空项目）
    win.rename_current_project()
    QApplication.processEvents()
    dlg = getattr(win, "_prompt_dlg", None)
    check("重命名对话框已弹出", dlg is not None and dlg.isVisible())
    check("对话框预填了当前项目名",
          dlg is not None and dlg.edit.line_edit().text() == win.project.name)
    if dlg is not None:
        dlg.close()
    QApplication.processEvents()

    # 3 空名不生效
    before = win.project.name
    win._rename_current("   ")
    check("空名称被忽略", win.project.name == before)

    # 4 真正建立项目并改名（落盘 → 文件同步改名）
    win._create_project("课题_原始名", "测试内容")
    QApplication.processEvents()
    check("新项目已落盘", os.path.exists(os.path.join(TMP, "课题_原始名.json")))
    win._rename_current("课题_新名字")
    QApplication.processEvents()
    check("项目名已更新", win.project.name == "课题_新名字")
    check("项目文件已同步改名", os.path.exists(os.path.join(TMP, "课题_新名字.json")))
    check("旧文件已移除", not os.path.exists(os.path.join(TMP, "课题_原始名.json")))
    check("下拉框已同步新名",
          win.project_box.combo_box().currentText() == "课题_新名字")

    # 5 重名自动加后缀，不覆盖已有项目
    win._create_project("课题_另一个", "")
    QApplication.processEvents()
    win._rename_current("课题_新名字")               # 与已有项目重名
    QApplication.processEvents()
    check(f"重名自动加后缀（实际「{win.project.name}」）",
          win.project.name != "课题_新名字" and win.project.name.startswith("课题_新名字"))
    check("同名文件未被覆盖",
          os.path.exists(os.path.join(TMP, "课题_新名字.json")))

    # 6 删除确认框能打开
    win.delete_current_project()
    QApplication.processEvents()
    cdlg = getattr(win, "_confirm_dlg", None)
    check("删除确认框已弹出", cdlg is not None and cdlg.isVisible())
    if cdlg is not None:
        cdlg.close()
    QApplication.processEvents()

    # 7 删除当前项目：文件消失 + 自动新建空项目
    target = os.path.join(TMP, f"{win.project.name}.json")
    check("待删项目文件存在", os.path.exists(target))
    n_before = len(files())
    win._delete_current()
    QApplication.processEvents()
    check("项目文件已删除", not os.path.exists(target))
    check("删除后自动新建空项目（内存中）", win.project.name.startswith("课题_"))
    check("删除后不留下多余文件", len(files()) <= n_before)

    # 8 删除「尚未落盘」的项目：只清空工作区，不产生垃圾文件
    win.project = da.Project(name="未保存的项目", model=win.client.model)
    win._refresh_all()
    n_now = len(files())
    win._delete_current()
    QApplication.processEvents()
    check("未落盘项目删除后仍是空项目", win.project.name.startswith("课题_"))
    check("未落盘项目删除不新增文件", len(files()) == n_now)


QtCore.QTimer.singleShot(1100, run)
QtCore.QTimer.singleShot(30000, lambda: (print("看门狗超时", flush=True), app.quit()))
sys.exit(app.exec())
