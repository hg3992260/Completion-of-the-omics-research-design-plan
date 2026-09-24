# -*- coding: utf-8 -*-
"""收敛推理（reason 模式）验证：素材摘要、模型输出解析、总览联动与落盘。

要点：代码里**不存在**"哪一章该看哪几条"的映射表，全部由模型推断 —— 因此测试也据此验收：
  · 摘要里必须包含全部素材（不筛选）；
  · 提示词必须要求模型自行判断归属；
  · 解析器能容忍格式波动；
  · 结果落盘并在总览显示（章节卡、就绪度、下一批动作）。
"""
import os
import shutil
import sys
import time

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_agent as da

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_convtest")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
da.PROJECT_DIR = TMP

import design_studio as ds
import coupling as cp
import scope_core
import stat_data as stat
import shape_data as shape

CONV_REPLY = """【收敛总览】方法与结果两章已具备实质内容，讨论与结论仍缺统计推断结论；最大瓶颈是外部验证的效应量。
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
### Introduction
来源：设计工作台 · 01 研究问题与设计
已有：gap 与目的清楚
缺失：无
就绪度：80
理由：动机明确
### Methods
来源：设计工作台 · 06 预处理与特征提取；统计 · 前提条件诊断
已有：扫描参数、分割与特征流程、统计方案
缺失：缺具体重采样参数
就绪度：70
理由：主流程齐备
### Results
来源：统计 · 检验计算；统计 · 效应量与置信区间
已有：AUC 与置信区间
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
    """假客户端：记录是否以 reason 模式调用，并按提示词返回收敛推理结果。"""

    def __init__(self):
        self.model = "fake-reasoner"
        self.calls = []

    def chat(self, messages, stream=True, on_delta=None, max_tokens=None, reason=False):
        prompt = "\n".join(m.get("content", "") for m in messages)
        self.calls.append({"prompt": prompt, "reason": reason, "max_tokens": max_tokens})
        if on_delta:                        # 模拟推理过程 + 正文
            for piece in ("我先看有哪些素材…", "按主题归类…", "再判断每章缺口…"):
                on_delta(piece, "reasoning")
            for i in range(0, len(CONV_REPLY), 120):
                on_delta(CONV_REPLY[i:i + 120], "content")
        return {"content": CONV_REPLY, "reasoning": "我先看有哪些素材…按主题归类…再判断每章缺口…",
                "model": self.model, "elapsed": 1.23,
                "usage": {"total_tokens": 900}, "retried": False}

    def list_models(self):
        return [self.model]


app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=False)
win.client = FakeReasonClient()
win.agent.client = win.client
win.resize(1520, 960)
win.show()
RESULT = []


def check(name, cond):
    RESULT.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name)


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
        RESULT.append(("run() 抛异常", False))
    finally:
        fails = sum(1 for _, v in RESULT if not v)
        print(f"\n合计 {len(RESULT)} 项，失败 {fails} 项", flush=True)
        open("_convergence_test.txt", "w", encoding="utf-8").write(
            "\n".join(f"{'PASS' if v else 'FAIL'}  {k}" for k, v in RESULT)
            + f"\n\n合计 {len(RESULT)} 项，失败 {fails} 项\n")
        app.quit()


def _run():
    p = win.project
    # 造素材：工作台阶段定稿 + 统计定稿 + SCI 定稿
    p.stages["3"]["final"] = "样本量：按 Riley 公式，训练集 ≥240 例。"
    p.stages["3"]["status"] = "done"
    p.stages["6"]["final"] = "重采样 1×1×1 mm，binWidth 25。"
    p.stages["6"]["status"] = "done"
    scope_core.node(p.stat, "s7_effect").update(
        {"final": "AUC 0.86（95%CI 0.79–0.92）。", "status": "done"})
    scope_core.node(p.shape, "methods").update(
        {"final": "扫描参数与分割流程已定稿。", "status": "done"})

    # 1 素材摘要：全量、不筛选
    digest = cp.project_digest(p)
    check("摘要含初步设计", "【初步设计描述】" in digest)
    check("摘要含十阶段条目", "【设计工作台 · 十阶段】" in digest and "样本量" in digest)
    check("摘要含统计九阶段条目", "【统计 · 九阶段】" in digest and "AUC 0.86" in digest)
    check("摘要含 SCI 七章条目", "【SCI 结构 · 七章】" in digest and "扫描参数与分割流程" in digest)
    check("摘要不做筛选（同时含无关条目）",
          "特征稳定性" in digest or "报告与复现" in digest)

    # 2 解析器
    parsed = da.parse_convergence(CONV_REPLY)
    check("解析出总览", "最大瓶颈" in parsed["overall"])
    check("解析出判定依据", "按内容主题与终点判断" in parsed["basis"])
    check(f"解析出 7 章（实际 {len(parsed['chapters'])}）", len(parsed["chapters"]) == 7)
    c0 = parsed["chapters"][0]
    check("章节字段齐全",
          c0["title"] == "Title" and c0["readiness"] == 85 and "样本量" in c0["sources"]
          and c0["reason"])
    check("缺失为「无」也能解析", parsed["chapters"][2]["missing"] == "无")
    check(f"解析出下一批动作（{len(parsed['actions'])} 条）", len(parsed["actions"]) == 3)
    check("解析容忍格式波动",
          len(da.parse_convergence("【各章收敛】\n### Methods\n就绪度：abc\n缺失：x")["chapters"]) == 1)

    # 3 提示词：要求模型自行判断，不得出现固定映射
    msgs = win.agent.convergence_messages()
    prompt = msgs[-1]["content"]
    whole = "\n".join(m["content"] for m in msgs)
    check("提示词要求自行判断归属", "自行判断" in whole)
    check("提示词含英文章节名清单", "Conclusion" in prompt and "Discussion" in prompt)
    check("提示词明确否定预设映射", "不存在任何预设的对应关系" in whole)
    check("提示词带上了全部素材", "AUC 0.86" in prompt and "样本量" in prompt)

    # 3b reason 模式的请求参数（对真实客户端做单元验证）
    from llm_client import LLMClient
    real = LLMClient({"base_url": "http://x/v1", "model": "m", "temperature": 0.4,
                      "max_tokens": 8000, "timeout": 5})
    seen = {}
    real._once = lambda payload, stream, on_delta, t0: (
        seen.update(payload) or {"content": "ok", "reasoning": "", "usage": {},
                                 "model": "m", "elapsed": 0.1, "finish_reason": "stop"})
    real.chat([{"role": "user", "content": "x"}], stream=False, reason=True)
    check(f"reason 模式温度降到 0（实际 {seen.get('temperature')}）",
          seen.get("temperature") == 0.0)
    check(f"reason 模式预算抬到 ≥12000（实际 {seen.get('max_tokens')}）",
          int(seen.get("max_tokens", 0)) >= 12000)
    seen.clear()
    real.chat([{"role": "user", "content": "x"}], stream=False)
    check("非 reason 模式保持原温度与预算",
          seen.get("temperature") == 0.4 and int(seen.get("max_tokens", 0)) == 8000)

    # 4 reason 模式 + 总览联动
    win.show_overview()
    QApplication.processEvents()
    check("未推理时给出引导", "尚未推理" in win.conv_state.label().text())
    check("重新推理按钮在未推理时禁用", not win.btn_conv_re.isEnabled())
    win.run_convergence()
    wait_idle()
    call = win.client.calls[-1]
    check("以 reason 模式调用", call["reason"] is True)
    conv = win.project.convergence
    check("推理结果已保存到项目", len(conv.get("chapters") or []) == 7)
    check("推理过程也已留存", "按主题归类" in (conv.get("reasoning") or ""))
    check("状态行显示已更新", "已更新" in win.conv_state.label().text())
    check("总览摘要已渲染", "最大瓶颈" in win.conv_summary.label().text())
    check("章节卡片已渲染", win.conv_lay.count() >= 8)
    check("下一批动作已渲染", "下一批动作" in "".join(
        w.label().text() for w in win.conv_host.findChildren(ds.CLabel) if w.isVisible()))
    check("重新推理按钮已可用", win.btn_conv_re.isEnabled())

    # 5 SCI 页右栏引用模型结论（而非固定映射）
    win.show_sci_shape()
    win.shape_page.pick([i for i, s in enumerate(ds.SHAPE) if s["key"] == "methods"][0])
    QApplication.processEvents()
    extra = win.shape_page.extra_lbl.label().text()
    check("SCI 右栏显示模型判断的本章来源", "模型判断来源" in extra)
    check("SCI 右栏显示尚缺与就绪度", "尚缺" in extra and "就绪度" in extra)
    win.stat_page.pick(0)
    check("统计右栏不再声称固定映射",
          "固定映射" in win.stat_page.extra_text(ds.STAT_STAGES[0]))

    # 6 落盘
    win._flush_project()
    pr = da.Project.load(win.project.path)
    check("收敛推理结果已落盘（含判定依据与动作）",
          len((pr.convergence or {}).get("chapters") or []) == 7
          and (pr.convergence or {}).get("basis")
          and len((pr.convergence or {}).get("actions") or []) == 3)


QtCore.QTimer.singleShot(1200, run)
QtCore.QTimer.singleShot(60000, lambda: (print("看门狗超时", flush=True), app.quit()))
sys.exit(app.exec())
