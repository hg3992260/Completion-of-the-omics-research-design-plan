# -*- coding: utf-8 -*-
"""总览「收敛推理」面板截图（假 reason 客户端填充内容，浅色/深色各一张）。"""
import os
import shutil
import sys
import time

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_agent as da

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_convshot")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
da.PROJECT_DIR = TMP

import design_studio as ds

REPLY = """【收敛总览】方法与结果两章已具备实质内容，讨论与结论仍缺统计推断结论；最大瓶颈是外部验证的效应量。
【本章来源对照】按内容主题与终点判断：设计工作台的样本量与建模阶段支撑 Methods，统计的检验与效应量支撑 Results。
【各章收敛】
### Title
来源：设计工作台 · 03 样本量与事件数
已有：可写出"基于增强 CT 影像组学预测胰腺囊性病变恶性"的标题
缺失：无
就绪度：85
理由：产出与人群已明确
### Abstract
来源：设计工作台 · 03 样本量；统计 · 效应量与置信区间
已有：背景、方法、主要结果可以拼出
缺失：缺外部验证的效应量
就绪度：60
理由：关键数字尚不完整
### Methods
来源：设计工作台 · 06 预处理与特征提取；统计 · 前提条件诊断
已有：扫描参数、分割与特征流程、统计方案
缺失：缺具体重采样参数
就绪度：70
理由：主流程齐备
### Results
来源：统计 · 检验计算；统计 · 效应量与置信区间
已有：AUC 0.86（95%CI 0.79–0.92）
缺失：缺校准与 DCA
就绪度：45
理由：判别力有、临床效用缺
### Discussion
来源：统计 · 归纳推断与结论
已有：可与文献对照
缺失：缺局限与未来工作
就绪度：30
理由：结论尚未定稿
### Conclusion
来源：无
已有：暂无
缺失：需要先定稿讨论
就绪度：10
理由：依赖前序章节
【下一批动作】
1. 补外部验证的效应量与置信区间
2. 完成校准曲线与决策曲线分析
3. 定稿讨论章的局限与未来工作
"""


class FakeReasonClient:
    def __init__(self):
        self.model = "deepseek-v4-pro"

    def chat(self, messages, stream=True, on_delta=None, max_tokens=None, reason=False):
        if on_delta:
            for piece in ("先看有哪些素材…", "按主题把内容归到各章…", "再逐章判断缺口与就绪度…"):
                on_delta(piece, "reasoning")
            for i in range(0, len(REPLY), 130):
                on_delta(REPLY[i:i + 130], "content")
        return {"content": REPLY, "reasoning": "先看有哪些素材…按主题把内容归到各章…",
                "model": self.model, "elapsed": 12.4,
                "usage": {"total_tokens": 2600}, "retried": False}

    def list_models(self):
        return [self.model]


os.makedirs("_shots", exist_ok=True)
app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=False)
win.client = FakeReasonClient()
win.agent.client = win.client
win.client = win.client
win.resize(1520, 960)
win.show()


def wait_idle(ms=8000):
    t0 = time.time()
    while (win._busy() or (time.time() - t0) * 1000 < 400) and (time.time() - t0) * 1000 < ms:
        QApplication.processEvents()
        time.sleep(0.02)


def run():
    try:
        _run()
    except Exception:                                       # noqa: BLE001
        import traceback
        print(traceback.format_exc(), flush=True)
    finally:
        app.quit()


def _run():
    p = win.project
    p.stages["3"]["final"] = "样本量：按 Riley 公式，训练集 ≥240 例。"
    p.stages["6"]["final"] = "重采样 1×1×1 mm，binWidth 25。"
    for s in ("3", "6"):
        p.stages[s]["status"] = "done"
    import scope_core
    scope_core.node(p.stat, "s7_effect").update({"final": "AUC 0.86（95%CI 0.79–0.92）。",
                                                "status": "done"})
    scope_core.node(p.shape, "methods").update({"final": "扫描参数与分割流程已定稿。",
                                               "status": "done"})
    win.show_overview()
    QApplication.processEvents()
    win.run_convergence()
    wait_idle()
    for _ in range(3):
        win.layout().activate()
        QApplication.processEvents()
    win.ov_host.grab().save("_shots/_conv_host.png")
    win.grab().save("_shots/_conv_full.png")
    print("saved light", flush=True)
    win.toggle_mode()
    for _ in range(3):
        win.layout().activate()
        QApplication.processEvents()
    win.ov_host.grab().save("_shots/_conv_host_dark.png")
    print("saved dark", flush=True)


QtCore.QTimer.singleShot(1300, run)
sys.exit(app.exec())
