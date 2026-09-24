# -*- coding: utf-8 -*-
"""引导完善界面截图（用假 LLM 填出内容，浅色/深色各一张）。"""
import os
import shutil
import sys
import time

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_agent as da

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_guideshot")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
da.PROJECT_DIR = TMP

import design_studio as ds

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
    def __init__(self):
        self.model = "fake-model"

    def chat(self, messages, stream=True, on_delta=None, max_tokens=None,
             reason=False):
        prompt = "\n".join(m.get("content", "") for m in messages)
        content = ASK_REPLY if "【定稿】" not in prompt else REWRITE_REPLY
        if on_delta:
            for i in range(0, len(content), 40):
                on_delta(content[i:i + 40], "content")
        return {"content": content, "model": self.model, "elapsed": 0.01,
                "usage": {"total_tokens": 12}, "retried": False}

    def list_models(self):
        return [self.model]

os.makedirs("_shots", exist_ok=True)
app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=False)
win.client = FakeClient()
win.agent.client = win.client
win.resize(1520, 960)
win.show()


def wait_idle(ms=6000):
    """等 LLM 子线程真正跑完；必须有最小等待，否则会在线程启动前就返回。"""
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
    p.stages["3"]["final"] = "样本量：按 Riley 预测模型公式估算，训练集需 ≥240 例。"
    p.stages["3"]["status"] = "done"
    win.show_stat()
    page = win.stat_page
    page.pick([i for i, s in enumerate(ds.STAT_STAGES) if s["key"] == "s2_design"][0])
    QApplication.processEvents()
    page.start_guide()
    wait_idle()
    win._set_answer(page.guide_answer_rows[0], "两组独立比较")
    win._set_answer(page.guide_answer_rows[1], "α=0.05，功效 0.80")
    page.submit_guide_answers()
    wait_idle()
    for _ in range(3):
        win.layout().activate()
        QApplication.processEvents()
    win.grab().save("_shots/_guide_stat_light.png")
    page.center.grab().save("_shots/_guide_stat_center.png")
    print("saved light", flush=True)
    win.toggle_mode()
    for _ in range(3):
        win.layout().activate()
        QApplication.processEvents()
    page.center.grab().save("_shots/_guide_stat_center_dark.png")
    print("saved dark", flush=True)


QtCore.QTimer.singleShot(1300, run)
sys.exit(app.exec())
