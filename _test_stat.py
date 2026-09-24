# -*- coding: utf-8 -*-
"""Statistic 页功能验证：9 阶段数据、渲染、工具映射、速查表、勾选联动、落盘与独立性。"""
import json
import os
import shutil
import sys

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_agent as da

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_stattest")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
da.PROJECT_DIR = TMP

import design_studio as ds
import stat_data as stat
import scope_core

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
            open("_stat_test.txt", "w", encoding="utf-8").write(
                "\n".join(f"{'PASS' if v else 'FAIL'}  {k}" for k, v in RESULT)
                + f"\n\n合计 {len(RESULT)} 项，失败 {fails} 项\n")
        except Exception:                                   # noqa: BLE001
            pass
        app.quit()


def _run():
    win.layout().activate()
    QApplication.processEvents()
    page = win.stat_page

    # 1 数据完整性
    check("9 个阶段齐备", len(ds.STAT_STAGES) == 9)
    check("阶段 id 连续 1..9", [s["id"] for s in ds.STAT_STAGES] == list(range(1, 10)))
    check("key 唯一", len({s["key"] for s in ds.STAT_STAGES}) == 9)
    check("每阶段均有 desc/goal/pitfalls/checks",
          all(s.get("desc") and s["goal"] and s["pitfalls"] and s["checks"]
              for s in ds.STAT_STAGES))
    check("每阶段自检项 ≥ 6",
          all(len(s["checks"]) >= 6 for s in ds.STAT_STAGES))
    cats = {s["cat"] for s in ds.STAT_STAGES}
    check("类别均属 5 大类", cats <= set(stat.CATS))
    check("5 大类都被用到", cats == set(stat.CATS))
    check("速查表 12 行 × 5 列",
          len(stat.CHEATSHEET) == 12 and all(len(r) == 5 for r in stat.CHEATSHEET))
    check("stat_run_test 支持 16 种 kind", len(stat.TEST_KINDS) == 16)
    all_tools = [t for v in stat.TOOLS.values() for t in v]
    check("工具共 12 个（7 控制 + 5 计算）", len(all_tools) == 12)

    # 2 页面渲染：九个阶段逐个切换
    win.show_stat()
    check("Statistic 视图索引 = 1", win.body_stack.currentIndex() == 1)
    ok_head, ok_detail = True, True
    for i in range(9):
        page.pick(i)
        QApplication.processEvents()
        head = page.head.label().text()
        if not head.startswith(f"{ds.STAT_STAGES[i]['icon']} {i + 1:02d}"):
            ok_head = False
        if page.detail_lay.count() < 3:
            ok_detail = False
    check("九个阶段标题均正确渲染（图标 + 序号）", ok_head)
    check("九个阶段详情区均有内容", ok_detail)

    # 3 工具映射
    page.pick(5)                                   # 检验计算
    QApplication.processEvents()
    extra = page.extra_lbl.label().text()
    check("阶段 6 右栏显示对应工具", "stat_run_test" in extra and
          "stat_correct_pvalues" in extra)
    page.pick(2)                                   # 数据预处理（无工具）
    QApplication.processEvents()
    check("阶段 3 明确标注无计算工具",
          "无计算工具" in page.extra_lbl.label().text())

    # 4 速查表落在阶段 6
    page.pick(5)
    QApplication.processEvents()
    from ui_kit import RefitLabel
    texts = " ".join(l.label().text() for l in page.detail_host.findChildren(RefitLabel))
    check("阶段 6 含速查表内容（Welch / Mann–Whitney / Cox）",
          "Welch" in texts and "Mann–Whitney" in texts and "Cox" in texts)
    check("阶段 6 列出 16 种 kind", "binom_prop" in texts and "kendall" in texts)

    # 5 勾选联动 + 独立性
    page.pick(0)
    for i in range(4):
        page.on_check(i, True)
    QApplication.processEvents()
    d, t = scope_core.progress(win.project.stat, ds.STAT_STAGES[0])
    check(f"阶段 1 勾选 4 项（实际 {d}/{t}）", d == 4)
    check("阶段 1 状态为进行中",
          scope_core.state(win.project.stat, ds.STAT_STAGES[0]) == "doing")
    check("SCI Shape 的自评未被连带修改", win.project.shape == {})
    check("Statistic 与 SCI Shape 使用不同存储字段",
          page.store_key == "stat" and win.shape_page.store_key == "shape")

    # 6 全选 / 清空
    page.bulk(True)
    check("阶段 1 全选后为已完成",
          scope_core.state(win.project.stat, ds.STAT_STAGES[0]) == "done")
    page.bulk(False)
    check("阶段 1 清空后回到未开始",
          scope_core.state(win.project.stat, ds.STAT_STAGES[0]) == "todo")

    # 7 落盘与重载
    page.on_check(0, True)
    page.on_check(1, True)
    QApplication.processEvents()
    path = win._flush_project()
    raw = json.load(open(path, encoding="utf-8"))
    check("JSON 含 stat.s1_question.checks",
          bool((raw.get("stat") or {}).get("s1_question", {}).get("checks")))
    pr = da.Project.load(path)
    d2, t2 = scope_core.progress(pr.stat, ds.STAT_STAGES[0])
    check(f"重载后进度保持（实际 {d2}/{t2}）", d2 == 2)
    states = {s["id"]: scope_core.state(pr.stat, s) for s in ds.STAT_STAGES}
    check("重载后阶段 1 为进行中", states[1] == "doing")
    check("重载后其余阶段仍为未开始", states[9] == "todo")

    # 8 汇总计数
    done, doing, ticks = scope_core.overall(pr.stat, ds.STAT_STAGES)
    check(f"汇总：已完成 {done} · 进行中 {doing} · 自检 {ticks}",
          done == 0 and doing == 1 and ticks == 2)
    check("九阶段自检项总数为 59" if scope_core.total_checks(ds.STAT_STAGES) == 59
          else f"九阶段自检项总数 = {scope_core.total_checks(ds.STAT_STAGES)}",
          scope_core.total_checks(ds.STAT_STAGES) >= 50)


QtCore.QTimer.singleShot(1100, run)
QtCore.QTimer.singleShot(30000, lambda: (print("看门狗超时退出", flush=True), app.quit()))
sys.exit(app.exec())
