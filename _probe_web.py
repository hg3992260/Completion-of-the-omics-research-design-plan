# -*- coding: utf-8 -*-
"""Web 版（Phase 0）渲染检查：造一个内容饱满的演示项目，起服务，用无头 Chrome 截图 + 核对 DOM。

用途：验证界面在真实浏览器里的排版（深浅两色 + 宽窄两档），并让 Chrome 真正执行 JS 后
检查"到底显示了哪些视图、渲染出多少章节卡片"，人工看图确认没有遮挡、没有白底白字。
截图落在 _shots\\web_*.png（该目录已在 .gitignore 里）。

    python _probe_web.py            # 起服务 + 截图 + 核对 DOM + 退出
    python _probe_web.py --keep     # 只起服务，Ctrl+C 结束（自己用浏览器看）

注意：无头 Chrome 需要命名管道（mojo IPC），受限沙箱里会被拒绝，需要放宽文件权限后运行。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import design_agent                                                    # noqa: E402
import shape_data                                                      # noqa: E402
import stat_data                                                       # noqa: E402
import web_server                                                      # noqa: E402

CASES = [
    ("web_ov_dark", "view=ov&theme=dark", 1600, 1250),
    ("web_ov_light", "view=ov&theme=light", 1600, 1250),
    ("web_stat_dark", "view=stat&theme=dark", 1600, 1150),
    ("web_shape_dark", "view=shape&theme=dark", 1600, 1150),
    ("web_work_light", "view=work&theme=light", 1600, 1150),
    ("web_ov_narrow", "view=ov&theme=dark", 1024, 1000),
]

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def demo_project():
    """造一个"看起来像真做过"的项目：原始设想 + 若干定稿 + 勾选 + 收敛结论。"""
    p = design_agent.Project.new(
        "胰腺囊性病变 CT 影像组学预测恶性（演示）",
        raw="回顾性收集 2016-2023 年单中心 212 例胰腺囊性病变（IPMN/MCN/SCN）"
            "增强 CT，提取 1316 个影像组学特征，构建预测恶性的模型，"
            "并与 2018 年 Fukuoka 指南高危征象做对比。")
    p.stages["1"].update({"status": "done", "final":
                          "目标人群为增强 CT 检出的、拟行手术或密切随访的胰腺囊性病变成人患者；"
                          "预期用途是辅助判断是否需要手术切除；按 TRIPOD+AI 3 报告临床情境。"})
    p.stages["2"].update({"status": "done", "final":
                          "回顾性单中心队列，2016-01 至 2023-06 连续入组；纳入标准与排除标准已列明，"
                          "缺失数据处理采用多重插补（m=20）。"})
    p.stages["3"].update({"status": "drafted", "draft":
                          "样本量以 EPV≥10 估算，恶性事件预计 60 例，允许 6 个自由度。",
                          "questions": [{"q": "恶性事件数按病理还是随访定义？",
                                         "why": "标签定义决定事件率"}],
                          "answers": ["按术后病理；未手术者以 24 个月随访影像进展为复合终点。"]})
    p.stages["4"].update({"status": "asked",
                          "questions": [{"q": "平扫还是增强？期相如何选？",
                                         "why": "纹理特征对期相敏感"},
                                        {"q": "重建核与层厚是否统一？",
                                         "why": "影响 IBSI 可比性"}],
                          "answers": ["胰腺期（45-50 s）薄层 1 mm 重建。",
                                      "部分 3 mm，将做敏感性分析。"]})
    for s in p.stages.values():
        s["checklist"] = ["写明扫描参数与重建核 ｜ 依据：CLEAR 16", "记录分割者一致性 ICC"]

    for i, sec in enumerate(stat_data.STAGES):
        node = p.stat.setdefault(sec["key"], {})
        if i < 3:
            node["status"] = "done"
            node["final"] = ("本环节已定稿：" + sec["title"] +
                             "。变量口径、检验方法与报告格式均已写明，可直接落到统计脚本。")
            node["checks"] = {str(k): True for k in range(len(sec["checks"]))}
        elif i < 5:
            node["questions"] = [{"q": "这里用参数法还是非参数法？", "why": "分布未知"}]
            node["answers"] = ["先做正态性检验，按结果选择。"]
            node["checks"] = {str(k): True for k in range(max(1, len(sec["checks"]) - 1))}
        elif i < 6:
            node["draft"] = "待采纳稿：" + sec["title"] + " 的初步方案。"
            node["checks"] = {str(k): True for k in range(1)}
    for i, sec in enumerate(shape_data.SHAPE):
        node = p.shape.setdefault(sec["key"], {})
        if i == 0:
            node["status"] = "done"
            node["final"] = ("Pancreatic cystic lesions: a CT radiomics model for predicting "
                             "malignancy compared with the Fukuoka guidelines")
            node["checks"] = {str(k): True for k in range(len(sec["checks"]))}
        elif i == 3:
            node["final"] = ("Methods 已写完数据来源、分割流程、特征提取（IBSI 编号）、"
                             "模型构建与内部验证。")
            node["checks"] = {str(k): True for k in range(len(sec["checks"]) - 2)}
        elif i == 2:
            node["draft"] = "Introduction 待采纳稿：临床背景 + 缺口 + 本研究目的。"
    p.convergence = {
        "overall": "素材集中在方法学与统计方案，结果尚未产生，最大瓶颈是缺少可复现的建模细节与"
                   "分割一致性证据。",
        "basis": "按内容主题判断：方法学与统计方案归入 Methods，指标与阈值归入 Results；"
                 "不存在预设对应表，归属由模型自行推断。",
        "chapters": [
            {"title": "Title", "sources": "研究设想；SCI 结构 title", "have": "已能定稿正式标题。",
             "missing": "无", "readiness": 92, "reason": "标题已与关键词表对齐。"},
            {"title": "Abstract", "sources": "研究设想；统计 s1_question",
             "have": "可写背景与方法一句。",
             "missing": "主要结局的效应量与 95%CI", "readiness": 34, "reason": "结果尚未产生。"},
            {"title": "Introduction", "sources": "研究设想；SCI 结构 intro（待采纳稿）",
             "have": "临床问题与缺口清楚。", "missing": "既往研究的定量对照", "readiness": 55,
             "reason": "缺文献层面的证据定位。"},
            {"title": "Methods", "sources": "设计工作台 01–04；统计 s1_question–s4_missing",
             "have": "数据来源、入排、分割、特征提取、建模与内部验证均已定稿，含 IBSI 编号与参数。",
             "missing": "扫描参数与重建核需补齐；分割者一致性 ICC 未做", "readiness": 78,
             "reason": "主干完整，细节与一致性证据待补。"},
            {"title": "Results", "sources": "统计 s5_compare",
             "have": "可写基线表结构与模型性能指标口径。",
             "missing": "全部实测结果", "readiness": 12, "reason": "尚无数据产出。"},
            {"title": "Discussion", "sources": "无", "have": "无",
             "missing": "与 Fukuoka 指南的对比；局限性；临床含义", "readiness": 8,
             "reason": "需结果先行才能讨论。"},
            {"title": "Conclusion", "sources": "设计工作台 01", "have": "可写一句方向性结论。",
             "missing": "需结果支撑", "readiness": 15, "reason": "结论依赖结果。"},
        ],
        "actions": ["补齐 CT 扫描参数与重建核，写入设计工作台阶段 4。",
                    "明确主要结局与效应量口径，落到统计 s5_compare。",
                    "制定分割者一致性方案（ICC），两人各 50 例。",
                    "先产出基线表与模型性能表，再启动 Results 写作。"],
        "updated": "2026-09-18 11:02", "model": "deepseek-v4-pro", "elapsed": 41.7,
        "reasoning": "先通读素材，再按内容主题判断归属……",
    }
    p.save()
    return p


def find_chrome():
    for p in CHROME_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return ""


def shoot(chrome, url, out, w, h):
    prof = os.path.join(HERE, "_shots", "_chrome_profile")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--no-first-run", "--no-default-browser-check", "--disable-extensions",
           "--user-data-dir=" + prof,
           "--window-size=%d,%d" % (w, h),
           "--virtual-time-budget=5000",
           "--screenshot=" + out, url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    size = os.path.getsize(out) if os.path.exists(out) else 0
    return size, (r.stderr or "")[-300:]


def dump_dom(chrome, url):
    """让 Chrome 真正执行 JS，再输出渲染后的 DOM —— 用来核对"到底显示了哪些视图"。"""
    prof = os.path.join(HERE, "_shots", "_chrome_profile")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
           "--no-default-browser-check", "--disable-extensions",
           "--user-data-dir=" + prof, "--virtual-time-budget=6000",
           "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.stdout or ""


def dom_checks(chrome, base):
    """在真实浏览器里核对视图切换、章节卡片、进度条等渲染结果。返回 (失败数, 检查数)。"""
    import re
    bad = 0

    def ck(name, ok, detail=""):
        nonlocal bad
        print("  %s %s%s" % ("✔" if ok else "✘", name,
                             ("　→ " + detail) if detail and not ok else ""))
        if not ok:
            bad += 1

    dom = dump_dom(chrome, base + "?view=ov&theme=dark")
    print("  渲染后 DOM %d 字符" % len(dom))
    secs = re.findall(r'<section class="view" id="view-(\w+)"( hidden="")?>', dom)
    hidden = [k for k, h in secs if h]
    shown = [k for k, h in secs if not h]
    ck("渲染后四个视图都在 DOM 里", len(secs) == 4, str(secs))
    ck("只有总览视图可见（.view[hidden] 生效）", shown == ["ov"],
       "显示=%s 隐藏=%s" % (shown, hidden))
    ck("流程条渲染出 4 步", len(re.findall(r'class="step[ "]', dom)) == 4,
       str(re.findall(r'class="step[^"]*"', dom)))
    ck("收敛结论渲染出 7 章卡片", dom.count('class="chap"') == 7, str(dom.count('class="chap"')))
    ck("总览渲染出就绪度 78%", "78%" in dom)
    ck("总览渲染出三条工作线", dom.count('class="lane"') == 3, str(dom.count('class="lane"')))
    ck("十阶段表格渲染出 10 行",
       len(re.findall(r"<tr>", dom.split('id="ovStages"')[-1])) >= 10)
    ck("课题下拉框渲染出演示项目", "胰腺囊性病变" in dom)
    ck("模型状态出现在顶栏", "fake" in dom or "deepseek" in dom or "●" in dom)

    dom2 = dump_dom(chrome, base + "?view=stat&theme=light")
    secs2 = re.findall(r'<section class="view" id="view-(\w+)"( hidden="")?>', dom2)
    shown2 = [k for k, h in secs2 if not h]
    ck("切到统计页后只有统计可见", shown2 == ["stat"], str(shown2))
    block = re.search(r'id="statRows"(.*?)id="shapeRows"', dom2, re.S)
    n_stat = block.group(1).count('class="srow"') if block else -1
    ck("统计页渲染出 9 行环节", n_stat == 9, "统计行=%s" % n_stat)
    return bad, 11


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="只起服务不截图")
    ap.add_argument("--port", type=int, default=8791)
    args = ap.parse_args()

    tmp = os.path.join(HERE, "_tmp_web_demo")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    design_agent.PROJECT_DIR = tmp
    demo_project()

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), web_server.Handler)
    srv.daemon_threads = True
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/" % port
    print("演示服务：%s（课题目录 %s）" % (base, tmp))
    print("提示：收敛推理需要真实 API Key；本演示用的是预置结论。")

    if args.keep:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)
        return 0

    chrome = find_chrome()
    if not chrome:
        print("[跳过截图] 没找到 Chrome/Edge。请手动打开：%s" % base)
        time.sleep(2)
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)
        return 0

    shots = os.path.join(HERE, "_shots")
    os.makedirs(shots, exist_ok=True)
    bad = []
    for name, qs, w, h in CASES:
        out = os.path.join(shots, name + ".png")
        try:
            size, err = shoot(chrome, base + "?" + qs, out, w, h)
        except Exception as e:                                          # noqa: BLE001
            size, err = 0, "%s: %s" % (type(e).__name__, e)
        ok = size > 20000
        print("  %s %-16s %7d bytes  %dx%d%s" % ("✔" if ok else "✘", name, size, w, h,
                                                 "" if ok else "  " + err))
        if not ok:
            bad.append(name)

    print("\n渲染核对（真实浏览器执行 JS 后的 DOM）：")
    n_bad, n_total = dom_checks(chrome, base)

    print("\n截图目录：%s" % shots)
    srv.shutdown()
    srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)
    total = len(CASES) + n_total
    print("通过 %d/%d" % (total - len(bad) - n_bad, total))
    return 1 if (bad or n_bad) else 0


if __name__ == "__main__":
    sys.exit(main())
