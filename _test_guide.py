# -*- coding: utf-8 -*-
"""引导式对话（Statistic / SCI Shape）端到端验证。

用**假 LLM 客户端**跑完整个闭环，验证：提示词确实基于内容、追问/回答/定稿的解析与持久化、
采纳时按检查表自动勾选、以及收敛度随之提升。
"""
import os
import shutil
import sys
import time

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_agent as da

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_guidetest")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
da.PROJECT_DIR = TMP

import design_studio as ds
import scope_core
import stat_data as stat
import shape_data as shape
import coupling as cp

ASK_REPLY = (
    "【现状评估】本项目已有设计工作台第 3 阶段定稿（样本量 ≥240），但尚未说明比较结构与"
    "偏倚控制，也未给出功效分析输入。\n"
    "【必须澄清的问题】\n"
    "1. 主要比较是两组独立还是配对？｜为什么问：决定检验族与样本量公式。\n"
    "2. α 与目标功效取多少？｜为什么问：直接决定 n 的取值。\n"
    "【本阶段小结】回答后可补齐设计类型与功效分析参数。"
)
REWRITE_REPLY = (
    "【定稿】本拟采用多中心回顾性队列设计，训练集 262 例、外部验证 50 例；"
    "主分析为两组独立比较，α=0.05（双侧）、目标功效 0.80，最小可检出 AUC 差 0.05；"
    "训练集不满足所需例数时按 Riley 公式扩增至 ≥240 例。偏倚控制采用中心分层与盲法评估。\n"
    "【检查表】\n- [x] 1\n- [x] 2\n- [ ] 3\n- [x] 4\n- [ ] 5\n- [ ] 6\n- [ ] 7\n"
    "【风险提示】外部验证集偏小，置信区间会偏宽。\n"
    "【下一步】进入数据采集与预处理。"
)


class FakeClient:
    """按提示词内容返回预设回复（可检查提示词是否带上了耦合来源的定稿）。"""

    def __init__(self):
        self.calls = []
        self.model = "fake-model"

    def chat(self, messages, stream=True, on_delta=None, max_tokens=None,
             reason=False):
        prompt = "\n".join(m.get("content", "") for m in messages)
        self.calls.append(prompt)
        is_ask = "必须澄清的问题" in prompt and "【定稿】" not in prompt
        content = ASK_REPLY if is_ask else REWRITE_REPLY
        if on_delta:
            for i in range(0, len(content), 40):
                on_delta(content[i:i + 40], "content")
        return {"content": content, "model": self.model, "elapsed": 0.01,
                "usage": {"total_tokens": 12}, "retried": False}

    def list_models(self):
        return [self.model]


app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=False)
win.client = FakeClient()
win.agent.client = win.client
win.resize(1520, 960)
win.show()
RESULT = []


def check(name, cond):
    RESULT.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name)


def wait_idle(ms=8000):
    t0 = time.time()
    while win._busy() or (time.time() - t0) * 1000 < 300:
        QApplication.processEvents()
        time.sleep(0.02)
        if (time.time() - t0) * 1000 > ms:
            break


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
        open("_guide_test.txt", "w", encoding="utf-8").write(
            "\n".join(f"{'PASS' if v else 'FAIL'}  {k}" for k, v in RESULT)
            + f"\n\n合计 {len(RESULT)} 项，失败 {fails} 项\n")
        app.quit()


def _run():
    p = win.project
    # 造出耦合来源：工作台第 3 阶段定稿
    p.stages["3"]["final"] = "样本量：按 Riley 预测模型公式估算，训练集需 ≥240 例。"
    p.stages["3"]["status"] = "done"

    # ---------- Statistic 页：完整引导闭环 ----------
    win.show_stat()
    page = win.stat_page
    page.pick([i for i, s in enumerate(ds.STAT_STAGES) if s["key"] == "s2_design"][0])
    QApplication.processEvents()
    check("页面有「结构内容 / 引导完善」两种模式",
          hasattr(page, "btn_content") and hasattr(page, "btn_guide"))
    check("默认停在结构内容模式", page.center_stack.currentIndex() == 0)
    check("初始引导状态为未开始",
          scope_core.guide_status(page.store, "s2_design") == "todo")

    page.start_guide()
    wait_idle()
    node = scope_core.node(page.store, "s2_design")
    check("已切到引导完善模式", page.center_stack.currentIndex() == 1)
    check(f"追问已解析（{len(node['questions'])} 条）", len(node["questions"]) == 2)
    check("现状评估已保存", "设计工作台第 3 阶段定稿" in node["assessment"])
    check("状态推进为 asked", scope_core.guide_status(page.store, "s2_design") == "asked")
    check("回答框数量与问题一致", len(page.guide_answer_rows) == 2)
    # 提示词确实"基于内容"：带上了耦合来源的定稿
    check("提示词带入了耦合来源定稿",
          "Riley 预测模型公式" in win.client.calls[-1])
    check("提示词带入了本环节规范内容（自检清单）",
          "自检清单" in win.client.calls[-1] and "设计类型" in win.client.calls[-1])

    win._set_answer(page.guide_answer_rows[0], "两组独立比较")
    win._set_answer(page.guide_answer_rows[1], "α=0.05，功效 0.80")
    page.submit_guide_answers()
    wait_idle()
    node = scope_core.node(page.store, "s2_design")
    check("回答已保存", node["answers"][0] == "两组独立比较" and node["answers"][1].startswith("α=0.05"))
    check("定稿已解析", "多中心回顾性队列设计" in node["draft"])
    check("风险提示已解析", "外部验证集偏小" in node["risks"])
    check("状态推进为 drafted", scope_core.guide_status(page.store, "s2_design") == "drafted")
    check("定稿框已出现在工作区", page.guide_draft_box is not None)
    check("采纳按钮已可用", page.btn_guide_accept.isEnabled())
    # 定稿生成后工作区应自动滚到底（让用户直接看到定稿）
    bar = page.guide_scroll.verticalScrollBar()
    QApplication.processEvents()
    time.sleep(0.15)
    QApplication.processEvents()
    check(f"工作区已自动滚到定稿（{bar.value()}/{bar.maximum()}）",
          bar.maximum() > 0 and bar.value() >= bar.maximum() - 2)

    before = scope_core.progress(page.store, ds.STAT_STAGES[1])[0]
    page.accept_guide_draft()
    wait_idle()
    node = scope_core.node(page.store, "s2_design")
    after = scope_core.progress(page.store, ds.STAT_STAGES[1])[0]
    check("定稿已收录且状态为 done",
          bool(node["final"]) and scope_core.guide_status(page.store, "s2_design") == "done")
    check(f"按检查表自动勾选（{before} → {after}，应为 3）", after == 3)
    check("右栏显示引导状态", "已定稿" in page.guide_lbl.label().text())

    # ---------- SCI Shape 页：走完同样闭环 ----------
    win.show_sci_shape()
    sp = win.shape_page
    sp.pick([i for i, s in enumerate(ds.SHAPE) if s["key"] == "methods"][0])
    QApplication.processEvents()
    sp.start_guide()
    wait_idle()
    snode = scope_core.node(sp.store, "methods")
    check("SCI 页同样能追问", len(snode["questions"]) == 2)
    check("SCI 提示词带入了设计工作台定稿",
          "Riley 预测模型公式" in win.client.calls[-1])
    check("SCI 提示词带入了统计阶段定稿（跨页耦合）",
          "多中心回顾性队列设计" in win.client.calls[-1])
    sp.submit_guide_answers()
    wait_idle()
    check("SCI 页生成定稿", bool(scope_core.node(sp.store, "methods")["draft"]))
    sp.accept_guide_draft()
    wait_idle()
    mnode = scope_core.node(sp.store, "methods")
    md, mt = scope_core.progress(sp.store, ds.SHAPE[3])
    check("SCI 定稿已收录", bool(mnode["final"]))
    check(f"SCI 自检被自动勾选（{md}/{mt}）", md >= 3)

    # ---------- 事实性进度联动（不依赖任何映射表） ----------
    lanes = {l["key"]: l for l in cp.lane_progress(p)}
    check("统计线完成数提升（s2 定稿后 ≥1）", lanes["stat"]["done"] >= 1)
    check("SCI 线完成数提升（methods 定稿后 ≥1）", lanes["shape"]["done"] >= 1)
    check("工作台线完成数正确（只有第 3 阶段定稿）", lanes["work"]["done"] == 1)
    check("引导提示词携带全量素材（不再按固定映射筛选）",
          "【统计 · 九阶段】" in win.client.calls[-1]
          and "【SCI 结构 · 七章】" in win.client.calls[-1])

    # ---------- 持久化 ----------
    win._flush_project()
    path = win.project.path
    pr = da.Project.load(path)
    check("定稿与对话状态已落盘",
          bool((pr.stat.get("s2_design") or {}).get("final"))
          and bool((pr.shape.get("methods") or {}).get("final")))
    check("追问/回答也落盘",
          len((pr.stat.get("s2_design") or {}).get("questions") or []) == 2
          and (pr.stat.get("s2_design") or {}).get("answers", [""])[0] == "两组独立比较")
    check("自动勾选的自检项已落盘",
          len((pr.stat.get("s2_design") or {}).get("checks") or {}) == 3)


QtCore.QTimer.singleShot(1200, run)
QtCore.QTimer.singleShot(60000, lambda: (print("看门狗超时", flush=True), app.quit()))
sys.exit(app.exec())
