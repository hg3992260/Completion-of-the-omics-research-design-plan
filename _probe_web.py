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

S1 = stat_data.STAGES[0]["key"]          # 问题定义与假设形式化
S3 = stat_data.STAGES[2]["key"]          # 样本量与检验效能
S6 = stat_data.STAGES[5]["key"]          # 检验计算（附速查表；演示项目里是"待采纳"状态）

CASES = [
    ("web_ov_dark", "view=ov&theme=dark", 1600, 1250),
    ("web_ov_light", "view=ov&theme=light", 1600, 1250),
    ("web_work_dark", "view=work&theme=dark&sid=3", 1600, 1400),
    ("web_work_light", "view=work&theme=light&sid=3", 1600, 1400),
    ("web_stat_content", "view=stat&mode=content&key=" + S1 + "&theme=dark", 1600, 1250),
    ("web_stat_guide", "view=stat&mode=guide&key=" + S6 + "&theme=light", 1600, 1400),
    ("web_stat_cheat", "view=stat&mode=content&key=" + S6 + "&theme=dark", 1600, 1500),
    ("web_shape_content", "view=shape&mode=content&key=title&theme=dark", 1600, 1400),
    ("web_shape_guide", "view=shape&mode=guide&key=methods&theme=light", 1600, 1400),
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
            node["assessment"] = ("本环节的检验方法与缺失值处理尚未写明，"
                                  "EPV 口径也需要与样本量环节对齐。")
            node["draft"] = ("待采纳稿：" + sec["title"] +
                             " 的初步方案：主要结局为病理证实的恶性，EPV≥10 控制变量数。")
            node["questions"] = [{"q": "用参数法还是非参数法？", "why": "分布未知"},
                                 {"q": "缺失值如何处理？", "why": "影响方差与偏倚"}]
            node["answers"] = ["先做正态性检验，按结果选择。", "多重插补 m=20。"]
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
    p.convergence = {        "overall": "素材集中在方法学与统计方案，结果尚未产生，最大瓶颈是缺少可复现的建模细节与"
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
    p.final_doc = ("一、研究问题：增强 CT 影像组学预测胰腺囊性病变恶性，辅助手术决策。\n"
                   "二、数据与人群：2016-2023 单中心 212 例，参考标准为术后病理或 24 个月随访。\n"
                   "三、影像与组学流程：胰腺期薄层 1 mm 重建，两名医师分割并计算 ICC，"
                   "按 IBSI 编号提取 1316 个特征。\n"
                   "四、统计与建模：EPV≥10 估算样本量，逻辑回归与多层感知机对比，5 折交叉验证。\n"
                   "五、验证策略：内部交叉验证 + 时间外部验证。\n"
                   "六、预期产出：模型、校准曲线、决策曲线与可复现脚本。")
    p.save()
    return p


# ------------------------------------------------------------------ 交互自测
# 用真实的点击跑一遍工作台闭环：把这段脚本注入界面的临时副本，用无头 Chrome 打开，
# 脚本点按钮 → 等流式结束 → 把结果写进 document.title，--dump-dom 就能读到。
AUTOTEST_JS = r"""
(function () {
  var mode = new URLSearchParams(location.search).get('autotest') || '';
  if (!mode) { return; }
  // 无头模式里 confirm/prompt 会挂住（虚拟时间在等对话框）→ 直接短路掉
  window.confirm = function () { return false; };
  window.prompt = function () { return null; };
  window.alert = function () { };
  function fail(msg) { document.title = 'AUTOTEST:' + mode + ':FAIL ' + msg; }
  function ok(msg) { document.title = 'AUTOTEST:' + mode + ':OK ' + msg; }
  function waitFor(pred, then, tries) {
    tries = tries || 0;
    var v = null;
    try { v = pred(); } catch (e) { return fail('predicate: ' + e.message); }
    if (v) { return then(); }
    if (tries > 600) { return fail('timeout'); }
    setTimeout(function () { waitFor(pred, then, tries + 1); }, 40);
  }
  function click(sel) {
    var b = document.querySelector(sel);
    if (!b) { fail('no element ' + sel); return null; }
    b.click();
    return b;
  }
  function qaCount() { return document.querySelectorAll('#wDetail textarea.qa').length; }
  function draftLen() { var d = document.getElementById('draftBox'); return d ? d.value.length : 0; }
  function status() {
    var t = document.getElementById('wState');
    return t ? t.textContent : '';
  }
  setTimeout(function () {
    try {
      var sid = new URLSearchParams(location.search).get('sid') || '1';
      if (mode === 'ask') {
        if (!click('#wActions button[data-act="ask"]')) { return; }
        waitFor(function () { return qaCount() >= 1; }, function () {
          ok('qa=' + qaCount() + ' status=' + status() +
             ' live=' + document.getElementById('wText').textContent.length);
        });
      } else if (mode === 'kickoff') {          // 速读 → 自动追问（两步串联）
        document.getElementById('rawDesign').value =
          '回顾性收集 212 例胰腺囊性病变增强 CT，做影像组学预测恶性。';
        if (!click('#btnKickoff')) { return; }
        waitFor(function () { return qaCount() >= 1; }, function () {
          ok('qa=' + qaCount() + ' status=' + status() +
             ' live=' + document.getElementById('wText').textContent.length);
        });
      } else if (mode === 'rewrite') {
        if (!click('#wActions button[data-act="rewrite"]')) { return; }
        waitFor(function () { return draftLen() >= 50; }, function () {
          ok('draft=' + draftLen() + ' status=' + status());
        });
      } else if (mode === 'accept') {
        if (!click('#wActions button[data-act="accept"]')) { return; }
        waitFor(function () { return status().indexOf('已完成') >= 0; }, function () {
          fetch('/api/state?project=' + encodeURIComponent(
                  document.getElementById('projSel').value))
            .then(function (r) { return r.json(); })
            .then(function (d) {
              var st = (d.overview.stages || []).filter(function (x) {
                return String(x.id) === sid;
              })[0] || {};
              if (st.status !== 'done') { return fail('落盘状态仍是 ' + st.status); }
              ok('status=' + st.status + ' final=' + (st.final || '').length);
            });
        });
      } else if (mode === 'finalize') {
        if (!click('#btnFinalize')) { return; }
        waitFor(function () {
          var b = document.getElementById('finalDoc');
          return b && b.textContent.length >= 50;
        }, function () {
          var box = document.getElementById('finalDoc');
          var ex = document.getElementById('finalExtra').textContent.length;
          if (ex < 10) { return fail('待补数据清单没有渲染'); }
          ok('len=' + box.textContent.length + ' extra=' + ex);
        });
      } else if (mode === 'scopeask' || mode === 'scoperewrite' || mode === 'scopeaccept'
                 || mode === 'scopetick') {
        // ---- scope 页（统计 / SCI）：page 由 URL 给出 ----
        var page = new URLSearchParams(location.search).get('page') || 'stat';
        var key = new URLSearchParams(location.search).get('key') || '';
        var proj = document.getElementById('projSel').value;
        function qa() { return document.querySelectorAll('#' + page + 'Body textarea.qa').length; }
        function draftId() { return page + 'DraftBox'; }
        function draftVal() {
          var el = document.getElementById(draftId());
          return el ? el.value.length : 0;
        }
        function stateTag() {
          var el = document.getElementById(page + 'State');
          return el ? el.textContent : '';
        }
        if (mode !== 'scopeask') {
          // 定稿/采纳只需要引导模式；先切过去（同步渲染）
          var mg = document.getElementById(page + 'ModeGuide');
          if (mg) { mg.click(); }
        } else {
          var mc = document.getElementById(page + 'ModeContent');
          if (mc) { mc.click(); }
          if (!document.querySelector('#' + page + 'Body .catpill') &&
              !document.querySelector('#' + page + 'Body .modelrow')) {
            return fail('结构内容模式没有渲染规范内容');
          }
          var mg2 = document.getElementById(page + 'ModeGuide');
          if (mg2) { mg2.click(); }
        }
        if (mode === 'scopeask') {
          if (!click('#' + page + 'Actions button[data-act="ask"]')) { return; }
          waitFor(function () { return qa() >= 1; }, function () {
            ok('qa=' + qa() + ' state=' + stateTag());
          });
        } else if (mode === 'scoperewrite') {
          if (!click('#' + page + 'Actions button[data-act="rewrite"]')) { return; }
          waitFor(function () { return draftVal() >= 50; }, function () {
            var ck = document.querySelectorAll('#' + page + 'Body .ckitem').length;
            if (ck < 1) { return fail('自检清单没有渲染'); }
            ok('draft=' + draftVal() + ' checks=' + ck + ' state=' + stateTag());
          });
        } else if (mode === 'scopeaccept') {
          if (!click('#' + page + 'Actions button[data-act="accept"]')) { return; }
          waitFor(function () { return stateTag().indexOf('已完成') >= 0; }, function () {
            fetch('/api/scope?page=' + page + '&key=' + encodeURIComponent(key) +
                  '&project=' + encodeURIComponent(proj))
              .then(function (r) { return r.json(); })
              .then(function (d) {
                if (!d.node || !d.node.final) { return fail('定稿没有落盘'); }
                if (!d.progress || d.progress[0] < 2) {
                  return fail('自检没有被自动勾选：' + JSON.stringify(d.progress));
                }
                ok('final=' + d.node.final.length + ' checks=' + d.progress.join('/'));
              });
          });
        } else if (mode === 'scopetick') {
          var items = document.querySelectorAll('#' + page + 'Body .ckitem');
          var target = null, i;
          for (i = 0; i < items.length; i++) {
            if (items[i].className.indexOf('on') < 0) { target = items[i]; break; }
          }
          if (!target) { return fail('没有可勾选的条目'); }
          var idx = String(target.getAttribute('data-idx'));
          var before = document.querySelectorAll('#' + page + 'Body .ckitem.on').length;
          target.click();
          var tries = 0;
          (function poll() {                     // 勾选是异步落盘的 → 轮询服务端确认
            fetch('/api/scope?page=' + page + '&key=' + encodeURIComponent(key) +
                  '&project=' + encodeURIComponent(proj))
              .then(function (r) { return r.json(); })
              .then(function (d) {
                if (d.checked && d.checked[idx]) {
                  return ok('idx=' + (parseInt(idx, 10) + 1) + ' checks=' +
                            d.progress.join('/') + ' before=' + before);
                }
                if (tries++ > 60) { return fail('服务端没有记录勾选 ' + idx); }
                setTimeout(poll, 50);
              });
          })();
        }
      } else {
        fail('unknown mode');
      }
    } catch (e) { fail(e.message); }
  }, 400);
})();
"""


def make_autotest_dir():
    """web/ 的临时副本 + 注入的交互自测脚本（不改动仓库里的正式界面文件）。"""
    dst = os.path.join(HERE, "_tmp_web_auto")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(os.path.join(HERE, "web"), dst)
    with open(os.path.join(dst, "autotest.js"), "w", encoding="utf-8") as fh:
        fh.write(AUTOTEST_JS)
    p = os.path.join(dst, "index.html")
    with open(p, encoding="utf-8") as fh:
        html = fh.read()
    html = html.replace("</body>", '<script src="/static/autotest.js"></script>\n</body>')
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(html)
    return dst


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


AUTOTEST_CASES = [
    ("ask", "view=work&sid=1&autotest=ask", "工作台追问：点按钮 → 出现回答输入框"),
    ("kickoff", "view=work&sid=1&autotest=kickoff", "速读完成后自动串到第一阶段追问"),
    ("rewrite", "view=work&sid=3&autotest=rewrite", "改写：点按钮 → 出现改写稿与检查表"),
    ("accept", "view=work&sid=3&autotest=accept", "采纳：点按钮 → 状态变已完成并落盘"),
    ("finalize", "view=work&autotest=finalize", "汇总：生成完整草案 + 待补清单"),
    ("scopeask", "view=stat&key=" + S3 + "&autotest=scopeask&page=stat",
     "统计追问：结构内容可见 → 引导追问出问题"),
    ("scoperewrite", "view=stat&mode=guide&key=" + S6 + "&autotest=scoperewrite&page=stat",
     "统计定稿：提交回答 → 定稿 + 自检清单"),
    ("scopeaccept", "view=stat&mode=guide&key=" + S6 + "&autotest=scopeaccept&page=stat",
     "统计采纳：定稿收录 + 按检查表自动勾选"),
    ("scopetick", "view=stat&mode=guide&key=" + S6 + "&autotest=scopetick&page=stat",
     "自检勾选：点条目 → 落盘并刷新进度"),
    ("shapeask", "view=shape&key=methods&autotest=scopeask&page=shape",
     "SCI 追问链路可用（同一套模板）"),
]


def autotest_checks(chrome, base):
    """真实点击跑一遍工作台闭环（注入脚本，不改仓库里的正式界面文件）。"""
    import re
    from _test_web import FakeClient

    web_server.STATE["client"] = FakeClient()          # 让点击链路有"模型"可调
    proj = web_server.resolve_project("")
    if proj is not None and proj.final_doc:
        proj.final_doc = ""                            # 让"汇总草案"这一步必须真的重新生成
        proj.save()
    auto_dir = make_autotest_dir()
    old = web_server.web_dir
    web_server.web_dir = lambda: auto_dir
    bad = 0
    try:
        for _, qs, label in AUTOTEST_CASES:
            dom = dump_dom_budget(chrome, base + "?" + qs, 40000)
            m = re.search(r"<title>([^<]*)</title>", dom)
            title = m.group(1) if m else ""
            good = ":OK " in title
            print("  %s %s　%s%s" % ("✔" if good else "✘", label,
                                     title or "（脚本没有写回结果）",
                                     "" if good else "　→ DOM %d 字符" % len(dom)))
            if not good:
                bad += 1
    finally:
        web_server.web_dir = old
        shutil.rmtree(auto_dir, ignore_errors=True)
    return bad


def dump_dom_budget(chrome, url, budget):
    prof = os.path.join(HERE, "_shots", "_chrome_profile")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
           "--no-default-browser-check", "--disable-extensions",
           "--user-data-dir=" + prof, "--virtual-time-budget=%d" % budget,
           "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return r.stdout or ""


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
    # 工作台：第三阶段（演示项目里是"待采纳"状态，带追问与改写稿）
    dom3 = dump_dom(chrome, base + "?view=work&theme=dark&sid=3")
    secs3 = re.findall(r'<section class="view" id="view-(\w+)"( hidden="")?>', dom3)
    ck("切到工作台后只有工作台可见", [k for k, h in secs3 if not h] == ["work"],
       str([k for k, h in secs3 if not h]))
    ck("阶段导轨渲染出 10 项", len(re.findall(r'data-sid="\d+"', dom3)) == 10,
       str(len(re.findall(r'data-sid="\d+"', dom3))))
    ck("导轨选中第三阶段", 'class="railitem sel" type="button" data-sid="3"' in dom3,
       str(re.findall(r'class="railitem[^"]*" type="button" data-sid="\d+"', dom3)))
    block3 = re.search(r'id="wDetail"(.*?)id="wLive"', dom3, re.S)
    det = block3.group(1) if block3 else ""
    ck("阶段详情渲染出回答输入框", det.count('class="ta qa"') >= 1,
       str(det.count('class="ta qa"')))
    ck("阶段详情渲染出改写稿编辑框", 'id="draftBox"' in det)
    ck("阶段详情渲染出检查表", "检查表" in det)
    ck("阶段详情渲染出规范条目", "必做动作" in det)
    acts = re.search(r'id="wActions"[^>]*>(.*?)</div>', dom3, re.S)
    html_acts = acts.group(1) if acts else ""
    ck("动作按钮含改写与采纳",
       'data-act="rewrite"' in html_acts and 'data-act="accept"' in html_acts,
       html_acts[:200])
    ck("原始设想输入框已填充", 'id="rawDesign"' in dom3 and "胰腺囊性病变" in dom3)
    ck("完整草案框已填充", "研究问题" in (re.search(r'id="finalDoc"[^>]*>(.*?)</pre>', dom3,
                                              re.S) or [None, ""])[1])

    def part(dom, key, nxt):
        """取出两个 id 之间的片段，避免把另一个（隐藏）视图的元素也数进来。"""
        m = re.search(r'id="%s"(.*?)id="%s"' % (key, nxt), dom, re.S)
        return m.group(1) if m else ""

    # 统计页：结构内容 + 引导完善
    d4 = dump_dom(chrome, base + "?view=stat&mode=content&key=" + S1)
    n_rail = part(d4, "statRail", "statTitle").count('class="railitem')
    ck("统计页渲染出 9 个环节", n_rail == 9, "环节=%s" % n_rail)
    body4 = part(d4, "statBody", "statLive")
    ck("统计「结构内容」渲染出分类色带与要点",
       'class="catpill"' in body4 and "常见陷阱" in body4 and "对应工具" in body4,
       body4[:200])
    ck("统计页有「结构内容 / 引导完善」两个模式按钮",
       'id="statModeContent"' in d4 and 'id="statModeGuide"' in d4)
    d5 = dump_dom(chrome, base + "?view=stat&mode=guide&key=" + S6)
    body5 = part(d5, "statBody", "statLive")
    n_ck = len(re.findall(r'class="ckitem', body5))
    ck("统计「引导完善」渲染出完整自检清单",
       n_ck == len(stat_data.STAGES[5]["checks"]), "条目=%s" % n_ck)
    ck("引导模式渲染出现状评估与追问输入框",
       "现状评估" in body5 and 'class="ta qa"' in body5)
    ck("引导模式渲染出定稿编辑框", 'id="statDraftBox"' in body5)
    d8 = dump_dom(chrome, base + "?view=stat&mode=content&key=" + S6)
    ck("「检验计算」环节渲染出检验速查表",
       'class="cheat"' in part(d8, "statBody", "statLive"))
    d6 = dump_dom(chrome, base + "?view=shape&mode=content&key=title")
    n_rail2 = part(d6, "shapeRail", "shapeTitle").count('class="railitem')
    body6 = part(d6, "shapeBody", "shapeLive")
    ck("SCI 页渲染出 7 章", n_rail2 == 7, "章=%s" % n_rail2)
    ck("SCI「结构内容」渲染出通用模型、内容边界与语言时态",
       'class="modelrow"' in body6 and "内容边界" in body6 and "语言与时态" in body6,
       body6[:200])
    d7 = dump_dom(chrome, base + "?view=shape&mode=guide&key=methods")
    n_ck2 = len(re.findall(r'class="ckitem', part(d7, "shapeBody", "shapeLive")))
    ck("SCI「引导完善」渲染出自检清单",
       n_ck2 == len(shape_data.SHAPE[3]["checks"]), "条目=%s" % n_ck2)
    return bad, 30


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

    print("\n交互核对（真实点击：追问 / 速读串联 / 改写 / 采纳 / 汇总）：")
    i_bad = autotest_checks(chrome, base)

    print("\n截图目录：%s" % shots)
    srv.shutdown()
    srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)
    total = len(CASES) + n_total + len(AUTOTEST_CASES)
    print("通过 %d/%d" % (total - len(bad) - n_bad - i_bad, total))
    return 1 if (bad or n_bad or i_bad) else 0


if __name__ == "__main__":
    sys.exit(main())
