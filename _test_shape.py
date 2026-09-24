# -*- coding: utf-8 -*-
"""SCI Shape 页功能验证：页签索引 / 勾选联动 / 状态推进 / 落盘与重载 / 与总览共存。

在临时目录里跑，不污染 projects/。
"""
import json
import os
import shutil
import sys

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_agent as da

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shapetest")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
da.PROJECT_DIR = TMP

import design_studio as ds
import shape_data as shape

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
        try:
            open("_shape_test.txt", "w", encoding="utf-8").write(
                "\n".join(f"{'PASS' if v else 'FAIL'}  {k}" for k, v in RESULT)
                + f"\n\n合计 {len(RESULT)} 项，失败 {fails} 项\n")
        except Exception:                                   # noqa: BLE001
            pass
        app.quit()


def _run():
    win.layout().activate()
    QApplication.processEvents()
    midx = [i for i, s in enumerate(ds.SHAPE) if s["key"] == "methods"][0]
    sec = ds.SHAPE[midx]

    # 1 四个视图的索引与共存
    win.show_stat()
    check("Statistic 视图索引 = 1", win.body_stack.currentIndex() == 1)
    win.show_sci_shape()
    check("SCI Shape 视图索引 = 2", win.body_stack.currentIndex() == 2)
    win.show_overview()
    check("总览视图索引 = 3（已顺延）", win.body_stack.currentIndex() == 3)
    check("总览表格仍为十阶段 10 行", win.ov_table.rowCount() == 10)
    win.show_workspace()
    check("工作台视图索引 = 0", win.body_stack.currentIndex() == 0)

    # 2 七章数据完整
    check("七个环节齐备（Title→Conclusion）",
          [s["key"] for s in ds.SHAPE] == ["title", "abstract", "introduction",
                                           "methods", "results", "discussion",
                                           "conclusion"])
    check("每章都有模型组件与检查项",
          all(s["model"] and s["checks"] for s in ds.SHAPE))
    check("自检项总数 = 59", shape.total_checks() == 59)

    # 3 勾选联动
    win.show_sci_shape()
    win.shape_page.pick(midx)
    check("选中章节正确", win.shape_page.head.label().text().startswith("04"))
    for i in range(3):
        win.shape_page.on_check(i, True)
    QApplication.processEvents()
    d, t = shape.section_progress(win.project, sec)
    check(f"勾选 3 项后进度 = 3（实际 {d}/{t}）", d == 3)
    check("状态推进为「进行中」", shape.section_state(win.project, sec) == "doing")
    check("右栏进度条已更新", abs(win.shape_page.prog._value - 3 / t) < 1e-6)

    # 4 全选 → 已完成
    win.shape_page.bulk(True)
    check("全选后状态为「已完成」", shape.section_state(win.project, sec) == "done")
    win.shape_page.bulk(False)
    check("清空后回到「未开始」", shape.section_state(win.project, sec) == "todo")

    # 5 落盘与重载
    win.shape_page.on_check(0, True)
    win.shape_page.on_check(1, True)
    QApplication.processEvents()
    path = win._flush_project()
    check("非空项目已落盘", bool(path) and os.path.exists(path))
    raw = json.load(open(path, encoding="utf-8"))
    check("JSON 含 shape.methods.checks",
          bool((raw.get("shape") or {}).get("methods", {}).get("checks")))
    pr = da.Project.load(path)
    d2, t2 = shape.section_progress(pr, sec)
    check(f"重载后进度保持（实际 {d2}/{t2}）", d2 == 2)
    states = {s["id"]: shape.section_state(pr, s) for s in ds.SHAPE}
    check("重载后 rail 状态一致（methods=doing）", states[sec["id"]] == "doing")
    check("未勾选章节仍为 todo", states[1] == "todo")

    # 6 汇总
    done, doing, ticks = shape.overall(pr)
    check(f"全书汇总：已完成 {done} · 进行中 {doing} · 自检 {ticks}",
          done == 0 and doing == 1 and ticks == 2)

    # 7 与总览推理的联动（不再有固定映射表）
    check("未推理时模型结论为空（不存在硬映射）",
          win.shape_page.inferred_for_section(sec) is None)
    win.project.convergence = {"chapters": [
        {"title": "Methods", "sources": "设计工作台 · 06 预处理与特征提取",
         "have": "扫描参数与流程", "missing": "重采样参数", "readiness": 70,
         "reason": "主流程齐备"}]}
    got = win.shape_page.inferred_for_section(sec)
    check("有推理结果时按模型输出的章节名匹配", got is not None
          and got.get("readiness") == 70 and "重采样参数" in got.get("missing", ""))
    win.project.convergence = {}


QtCore.QTimer.singleShot(1100, run)
QtCore.QTimer.singleShot(20000, lambda: (print("看门狗超时退出", flush=True), app.quit()))
sys.exit(app.exec())
