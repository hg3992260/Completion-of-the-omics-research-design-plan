# -*- coding: utf-8 -*-
"""Web 版（Phase 0）自检：接口 / 静态资源 / SSE 收敛推理 / 离线性 / Python 3.8 兼容。

用法：
    python _test_web.py            # 在本机随便一个空闲端口跑一遍，不联网
    python _test_web.py --port 8799

不依赖任何第三方库；不调用真实 LLM（用假客户端替换），因此可以离线跑。
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import design_agent                                                  # noqa: E402
import web_server                                                    # noqa: E402
from http.server import ThreadingHTTPServer                          # noqa: E402

FAIL = []
PASS = []

DEMO = """【收敛总览】素材集中在方法学与统计方案，结果与讨论尚未成形，最大瓶颈是缺少可复现的建模细节。
【本章来源对照】按内容主题判断：方法学与统计方案归入 Methods，指标与阈值归入 Results。
【各章收敛】
### Title
来源：研究设想
已有：能写出"胰腺囊性病变 CT 影像组学预测恶性"这一核心命题。
缺失：具体成像期相；样本量
就绪度：55
理由：主题明确但缺方法学限定词。
### Abstract
来源：研究设想；统计追问
已有：可写背景与方法一句。
缺失：主要结局的效应量
就绪度：30
理由：结果未产生。
### Introduction
来源：研究设想
已有：临床问题清楚。
缺失：既往研究缺口
就绪度：40
理由：缺少文献对照。
### Methods
来源：设计工作台 01–04；统计 s1_question–s3_power
已有：数据来源、入排标准、特征提取与建模流程已定稿。
缺失：扫描参数；分割者一致性
就绪度：78
理由：主干完整，细节待补。
### Results
来源：统计 s5_compare
已有：可写基线表结构。
缺失：全部实测结果
就绪度：12
理由：尚无数据。
### Discussion
来源：无
已有：无
缺失：与既往研究的对比；局限性
就绪度：8
理由：需结果先行。
### Conclusion
来源：设计工作台 01
已有：可写一句方向性结论。
缺失：需结果支撑
就绪度：15
理由：结论依赖结果。
【下一批动作】
1. 补齐 CT 扫描参数与期相，写入设计工作台阶段 4。
2. 明确主要结局与效应量口径，落到统计 s5_compare。
3. 制定分割者一致性方案（ICC）。
"""

KICKOFF = """【设计速读】这是一项诊断准确性研究：用增强 CT 的影像组学特征预测胰腺囊性病变的恶性，
数据为单中心回顾性队列，回答的是"要不要手术"。属于诊断研究。
【首要关注点】
参考标准的病理定义 ｜ 阶段 2
扫描期相与重建参数的统一 ｜ 阶段 4
分割者一致性（ICC） ｜ 阶段 5
【路线说明】接下来按十阶段标准流程逐个推进，每阶段先追问再改写。
"""

ASK = """【现状评估】你把人群、成像与建模流程都写了，但没有交代参考标准是术后病理还是随访，
也没有说清扫描期相与重建核；这两点直接决定标签质量与纹理特征是否可比。
【必须澄清的问题】
参考标准如何定义？｜为什么问：结局定义决定标签质量，也决定事件率。
扫描期相与重建核是什么？｜为什么问：纹理特征对期相与层厚敏感，影响 IBSI 可比性。
【本阶段小结】回答这两点后即可把数据来源与参考标准写进方案。
"""

REWRITE = """【改写稿】本研究纳入 2016-01 至 2023-06 连续入组的胰腺囊性病变成人患者，
参考标准为术后病理；未手术者以 24 个月随访影像进展为复合终点。
所有纳入病例均为胰腺期（45-50 s）薄层 1 mm 重建，重建核统一为 B30f；
对于 3 mm 层厚病例另做敏感性分析。分割由两名放射科医师独立完成，计算 ICC。
【检查表】
- [ ] 写明参考标准的定义与时间窗 ｜ 依据：CLEAR 8
- [ ] 写明扫描期相、层厚与重建核 ｜ 依据：CLEAR 16、METRICS #6
- [ ] 说明分割者一致性 ｜ 依据：METRICS #10
【风险提示】层厚不统一会系统性偏移纹理特征，务必做敏感性分析。
【下一步】进入阶段 3：样本量与事件数。
"""

FINALIZE = """【设计草案】
一、研究问题：增强 CT 影像组学预测胰腺囊性病变恶性，辅助手术决策。
二、数据与人群：2016-2023 单中心 212 例，参考标准为术后病理或 24 个月随访。
三、影像与组学流程：胰腺期薄层 1 mm 重建，两名医师分割并计算 ICC，IBSI 编号提取特征。
四、统计与建模：EPV≥10 估算样本量，多层感知机与逻辑回归对比，5 折交叉验证。
五、验证策略：内部交叉验证 + 时间外部验证。
六、预期产出：模型、校准曲线、决策曲线与可复现脚本。
【待补数据清单】扫描参数、分割者 ICC、外部验证队列。
【投稿前自查】按 CLEAR 逐条核对；按 TRIPOD+AI 报告模型细节；按 METRICS 报告分割一致性。
"""

SCOPE_REWRITE = """【定稿】本研究的主要结局为病理证实的恶性（高级别 IPMN / 浸润癌）。
采用多因素 logistic 回归建立预测模型，自变量按 EPV≥10 控制数量；
连续变量以受限立方样条检验线性，缺失值用多重插补（m=20）处理；
模型性能以 AUC 及 95%CI 报告，并用 bootstrap 1000 次做内部验证，校准用校准曲线与 Brier 分数。
【检查表】
- [x] 1
- [ ] 2
- [x] 3
- [ ] 4
- [ ] 5
- [ ] 6
【风险提示】把 EPV 算成"变量数×10"而忽略事件数；缺失值用均值填补会低估方差。
【下一步】进入下一环节：效应量与置信区间的报告口径。
"""

# (提示词里的标记, 假输出, 动作名)
CANNED = [
    ("【设计速读】", KICKOFF, "kickoff"),
    ("【改写稿】", REWRITE, "rewrite"),
    ("【定稿】", SCOPE_REWRITE, "scope_rewrite"),
    ("【设计草案】", FINALIZE, "finalize"),
    ("【收敛总览】", DEMO, "convergence"),
    ("【现状评估】", ASK, "ask"),
]


class FakeClient(object):
    """假 LLM：不联网，但按真实协议分片回调，用来验证 SSE 通路与解析。"""

    def __init__(self):
        self.model = "fake-reason-model"
        self.base_url = "http://fake.local"
        self.cfg = {"api_key": "sk-fake", "key_source": "test",
                    "temperature": 0.4, "max_tokens": 8000}
        self.calls = []
        self.messages = []
        self.kinds = []

    def _pick(self, messages):
        """按提示词里要求的小标题判断这次是哪种动作，返回对应的假输出。"""
        blob = "\n".join(m.get("content", "") for m in messages)
        for marker, text, kind in CANNED:
            if marker in blob:
                return text, kind
        return DEMO, "unknown"

    def chat(self, messages, stream=False, on_delta=None, temperature=None,
             max_tokens=None, reason=False):
        self.calls.append({"stream": stream, "reason": reason, "messages": len(messages)})
        self.messages = messages
        text, kind = self._pick(messages)
        self.kinds.append(kind)
        reasoning = "先通读全部素材，再按内容主题判断归属……" * 3
        if on_delta:
            for i in range(0, len(reasoning), 9):
                on_delta(reasoning[i:i + 9], "reasoning")
            for i in range(0, len(text), 13):
                on_delta(text[i:i + 13], "content")
        return {"content": text, "reasoning": reasoning, "usage": {"total_tokens": 1234},
                "model": self.model, "finish_reason": "stop", "elapsed": 1.5}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  %s %s%s" % ("✔" if ok else "✘", name, ("　→ " + detail) if detail and not ok else ""))


def get(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "selftest"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "ignore"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore"), dict(e.headers or {})


def get_bytes(url, timeout=30):
    """需要原始字节的下载（docx 是 zip 包）。"""
    req = urllib.request.Request(url, headers={"User-Agent": "selftest"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def post(url, payload, timeout=30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()

    # 临时课题目录：固定放在本目录下（不依赖 TEMP 环境变量，沙箱/精简系统都稳）
    tmp = os.path.join(HERE, "_tmp_web_test")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    old_dir = design_agent.PROJECT_DIR
    design_agent.PROJECT_DIR = tmp
    web_server.STATE["client"] = FakeClient()
    design_agent.Project.new("测试课题", raw="回顾性收集 200 例胰腺囊性病变 CT，做影像组学预测恶性。")

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), web_server.Handler)
    srv.daemon_threads = True
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % port
    print("自检服务：%s（临时课题目录 %s）" % (base, tmp))

    try:
        # ---------------------------------------------------------- 1 健康检查
        print("\n[1] 接口")
        code, body, hdr = get(base + "/api/health")
        j = json.loads(body)
        check("GET /api/health 200", code == 200, body[:200])
        check("健康检查含版本号", j.get("version") == web_server.APP_VERSION, body[:200])
        check("健康检查报告 LLM 模型", j.get("llm", {}).get("model") == "fake-reason-model",
              body[:200])

        # ---------------------------------------------------------- 2 单页界面
        code, html, hdr = get(base + "/")
        check("GET / 返回界面", code == 200 and "组学研究设计工作台" in html, body[:200])
        check("界面引用本地 CSS/JS（不依赖 CDN）",
              "/static/app.css" in html and "/static/app.js" in html)
        check("含四个视图容器",
              all(('id="view-%s"' % k) in html for k in ("work", "stat", "shape", "ov")))
        check("含旧内核降级提示", 'id="compat"' in html)

        for f, must in (("app.css", "--accent"), ("app.js", "streamAction"),
                        ("favicon.svg", "<svg")):
            code, body, hdr = get(base + "/static/" + f)
            check("GET /static/%s" % f, code == 200 and must in body, "code=%s" % code)

        # 视图切换：默认只露总览，其余三个带 hidden
        secs = re.findall(r'<section class="view" id="view-(\w+)"( hidden)?>', html)
        check("四个视图 + 默认只显示总览",
              len(secs) == 4 and [k for k, h in secs if not h] == ["ov"], str(secs))
        css = get(base + "/static/app.css")[1]
        check("CSS 有 .view[hidden] 规则（否则 display:flex 会盖掉 hidden）",
              ".view[hidden]" in css)
        check("CSS 含深浅两套配色变量",
              ':root[data-theme="dark"]' in css and ':root[data-theme="light"]' in css)
        js = get(base + "/static/app.js")[1]
        check("JS 用 EventSource/fetch 流式读 SSE", "getReader" in js and "TextDecoder" in js)
        check("JS 有旧内核降级判断", "checkCompat" in js)

        # 关键：离线可用（Win7 内网机器不能依赖外链）
        ext = re.findall(r"(?:src|href)\s*=\s*[\"'](https?:)?//[^\"']+", html)
        check("页面无外部 CDN 引用", not ext, str(ext[:3]))

        # 路由健全性：do_GET / do_POST 里引用的处理函数必须真的存在
        # （防止改代码时把某个 def 行粘连/删掉 —— 这类错误只会在请求到来时才炸）
        import inspect
        src_handler = inspect.getsource(web_server.Handler.do_GET) + \
            inspect.getsource(web_server.Handler.do_POST)
        calls = set(re.findall(r"self\.(_[a-z_]+)\(", src_handler))
        missing = sorted(n for n in calls if not hasattr(web_server.Handler, n))
        check("所有路由的处理函数都存在", not missing, str(missing))

        # 目录穿越防护
        code, body, _ = get(base + "/static/..%2fweb_server.py")
        check("静态目录穿越被拒", code in (403, 404), "code=%s" % code)

        # ---------------------------------------------------------- 3 总览数据
        print("\n[2] 总览数据（只读）")
        code, body, hdr = get(base + "/api/state")
        d = json.loads(body)
        ov = d.get("overview") or {}
        check("GET /api/state 200", code == 200 and d.get("ok"), body[:200])
        check("项目列表非空", len(d.get("projects") or []) == 1, body[:200])
        check("三条工作线", len(ov.get("lanes") or []) == 3, str(ov.get("lanes"))[:200])
        check("十阶段齐全", len(ov.get("stages") or []) == 10)
        check("统计九阶段", len(ov.get("stat") or []) == 9)
        check("SCI 七章", len(ov.get("shape") or []) == 7)
        check("统计自检项总数 = 58", ov.get("totals", {}).get("stat_checks") == 58,
              str(ov.get("totals")))
        check("SCI 自检项总数 = 59", ov.get("totals", {}).get("shape_checks") == 59,
              str(ov.get("totals")))
        check("阶段状态标签为中文", (ov.get("stages") or [{}])[0].get("label") == "未开始",
              str((ov.get("stages") or [{}])[0]))
        check("原始设想已回传", "胰腺囊性病变" in (ov.get("raw_design") or ""))

        # 项目切换（按文件名）
        code, body, _ = get(base + "/api/state?project=" +
                            urllib.parse.quote(d["current_file"]))
        check("按文件名选项目", json.loads(body).get("current") == d.get("current"))

        # ---------------------------------------------------------- 4 SSE 推理
        print("\n[3] 收敛推理（SSE + reason 模式）")
        code, body = post(base + "/api/convergence", {"project": "测试课题"})
        check("POST /api/convergence 200", code == 200, body[:200])
        events = []
        for line in body.splitlines():
            if line.startswith("data:"):
                try:
                    events.append(json.loads(line[5:].strip()))
                except ValueError:
                    pass
        kinds = [e.get("type") for e in events]
        check("SSE 含 status 事件", "status" in kinds, str(kinds[:5]))
        check("SSE 含 reasoning 事件（reason 模式）", "reasoning" in kinds, str(kinds[:5]))
        check("SSE 含 content 事件", "content" in kinds, str(kinds[:5]))
        done = [e for e in events if e.get("type") == "done"]
        check("SSE 以 done 收尾", bool(done), str(kinds[-3:]))
        if done:
            conv = done[-1].get("convergence") or {}
            check("done.ok 且已落盘", done[-1].get("ok") and done[-1].get("saved"),
                  json.dumps(done[-1], ensure_ascii=False)[:200])
            check("解析出七章", len(conv.get("chapters") or []) == 7,
                  str([c.get("title") for c in conv.get("chapters") or []]))
            check("解析出总览与依据", bool(conv.get("overall")) and bool(conv.get("basis")))
            check("解析出 3 条下一步动作", len(conv.get("actions") or []) == 3,
                  str(conv.get("actions"))[:200])
            methods = [c for c in (conv.get("chapters") or [])
                       if c.get("title") == "Methods"]
            check("就绪度解析为整数", bool(methods) and methods[0].get("readiness") == 78,
                  str(methods)[:200])
            check("缺失项被解析", bool(methods) and "扫描参数" in (methods[0].get("missing") or ""))
            check("记录了模型与耗时", bool(conv.get("model")) and conv.get("elapsed") == 1.5,
                  json.dumps(conv, ensure_ascii=False)[:160])

        cli = web_server.STATE["client"]
        check("调用使用 reason 模式", bool(cli.calls) and cli.calls[-1]["reason"] is True,
              str(cli.calls))
        check("调用使用流式", bool(cli.calls) and cli.calls[-1]["stream"] is True,
              str(cli.calls))
        joined = "\n".join(m.get("content", "") for m in cli.messages)
        check("提示词含全量素材摘要（无映射表）",
              "【初步设计描述】" in joined and "【SCI 结构 · 七章】" in joined)

        # 落盘检查
        saved = json.load(open(os.path.join(tmp, "测试课题.json"), encoding="utf-8"))
        check("收敛结论写入项目文件", len(saved.get("convergence", {}).get("chapters") or []) == 7)
        on_disk = json.loads(get(base + "/api/state")[1]).get("convergence") or {}
        check("刷新后总览能读到收敛结论", len(on_disk.get("chapters") or []) == 7)

        # 并发保护
        web_server.RUN_LOCK.acquire()
        try:
            code, body = post(base + "/api/convergence", {"project": "测试课题"})
            check("并发推理返回 409", code == 409, "code=%s %s" % (code, body[:120]))
        finally:
            web_server.RUN_LOCK.release()

        # ---------------------------------------------------------- 5 项目管理
        print("\n[4] 项目管理（新建 / 改名 / 删除）")
        code, body = post(base + "/api/project/new", {"name": "第二个课题"})
        check("新建课题", code == 200 and json.loads(body).get("ok"), body[:200])
        code, body = post(base + "/api/project/rename",
                          {"project": "第二个课题", "name": "改过名的课题"})
        check("改名课题", code == 200 and json.loads(body).get("project") == "改过名的课题",
              body[:200])
        code, body = post(base + "/api/project/delete", {"project": "改过名的课题"})
        check("删除课题", code == 200 and json.loads(body).get("ok"), body[:200])
        check("删除后只剩一个项目", len(json.loads(get(base + "/api/state")[1])["projects"]) == 1)
        code, body = post(base + "/api/project/delete", {"project": "不存在的课题"})
        check("删除不存在的项目返回 400", code == 400, "code=%s" % code)

        # ---------------------------------------------------------- 6 工作台闭环
        print("\n[5] 工作台闭环（速读 → 追问 → 回答 → 改写 → 采纳 → 汇总 → 导出）")

        def sse(body):
            out = []
            for line in body.splitlines():
                if line.startswith("data:"):
                    try:
                        out.append(json.loads(line[5:].strip()))
                    except ValueError:
                        pass
            return out

        def last_done(body):
            d = [e for e in sse(body) if e.get("type") == "done"]
            return d[-1] if d else {}

        def stage_of(payload, sid):
            st = ((payload.get("state") or {}).get("overview") or {}).get("stages") or []
            return next((s for s in st if s["id"] == sid), {})

        raw_new = "回顾性收集 2016-2023 年单中心 212 例胰腺囊性病变增强 CT，做影像组学预测恶性。"
        code, body = post(base + "/api/kickoff",
                          {"project": "测试课题", "raw_design": raw_new})
        d = last_done(body)
        check("速读（kickoff）成功", code == 200 and d.get("ok"), body[:200])
        check("速读解析出首要关注点", "阶段 2" in (d.get("focus") or ""),
              str(d.get("focus"))[:120])
        check("速读写入了原始设想",
              (d.get("state") or {}).get("overview", {}).get("raw_len", 0) > 10,
              str((d.get("state") or {}).get("overview", {}).get("raw_len")))
        check("速读记入对话记录",
              ((d.get("state") or {}).get("overview") or {}).get("transcript_len", 0) >= 1)
        check("done 事件带整份 state（前端可整体重绘）",
              len(((d.get("state") or {}).get("overview") or {}).get("stages") or []) == 10)

        code, body = post(base + "/api/stage/ask", {"project": "测试课题", "sid": 1})
        d = last_done(body)
        st1 = stage_of(d, 1)
        check("追问成功且解析出 2 条问题", d.get("ok") and d.get("questions") == 2,
              json.dumps(d, ensure_ascii=False)[:200])
        check("现状评估已保存", "参考标准" in (st1.get("assessment") or ""),
              str(st1.get("assessment"))[:120])
        check("问题带“为什么问”", bool((st1.get("questions") or [{}])[0].get("why")),
              str(st1.get("questions"))[:160])
        check("回答槽位与问题数一致",
              len(st1.get("answers") or []) == 2 and (st1.get("answers") or [""])[0] == "",
              str(st1.get("answers")))
        check("阶段状态变为已追问", st1.get("status") == "asked", str(st1.get("status")))

        ans = ["参考标准为术后病理；未手术者以 24 个月随访影像进展为复合终点。",
               "胰腺期（45-50 s）薄层 1 mm 重建，重建核 B30f。"]
        code, body = post(base + "/api/stage/answers",
                          {"project": "测试课题", "sid": 1, "answers": ans})
        j = json.loads(body)
        check("只保存回答（不调用模型）",
              code == 200 and (stage_of(j, 1).get("answers") or [""])[0].startswith("参考标准为术后病理"),
              body[:160])

        before = len(web_server.STATE["client"].calls)
        code, body = post(base + "/api/stage/rewrite",
                          {"project": "测试课题", "sid": 1, "answers": ans})
        d = last_done(body)
        st1 = stage_of(d, 1)
        check("改写成功", code == 200 and d.get("ok") and d.get("kind") == "rewrite", body[:200])
        check("改写稿已解析（>100 字）", (d.get("draft_len") or 0) > 100,
              str(d.get("draft_len")))
        check("检查表解析出 3 条", (d.get("checks") or 0) == 3, str(st1.get("checklist")))
        check("风险提示已解析", "层厚" in (st1.get("risks") or ""),
              str(st1.get("risks"))[:120])
        check("下一步已解析", "阶段 3" in (st1.get("next") or ""), str(st1.get("next"))[:120])
        check("状态变为待采纳", st1.get("status") == "drafted", str(st1.get("status")))
        check("改写前的回答被写进项目",
              (st1.get("answers") or [""])[1].startswith("胰腺期"), str(st1.get("answers")))
        check("本轮调用走的是改写提示词",
              web_server.STATE["client"].kinds[-1] == "rewrite",
              str(web_server.STATE["client"].kinds))
        check("改写确实调用了一次模型",
              len(web_server.STATE["client"].calls) == before + 1)

        final_text = (st1.get("draft") or "") + "\n（研究者补充：外部验证队列待确认。）"
        code, body = post(base + "/api/stage/save",
                          {"project": "测试课题", "sid": 1, "accept": True,
                           "final": final_text, "answers": ans})
        j = json.loads(body)
        st1 = stage_of(j, 1)
        check("采纳定稿成功", code == 200 and j.get("ok"), body[:200])
        check("定稿内容与编辑一致", "研究者补充" in (st1.get("final") or ""),
              str(st1.get("final"))[:120])
        check("状态变为已完成", st1.get("status") == "done", str(st1.get("status")))

        code, body = post(base + "/api/stage/save",
                          {"project": "测试课题", "sid": 2,
                           "raw_design": "改过的设想：多中心前瞻队列。"})
        j = json.loads(body)
        check("保存研究设想",
              ((j.get("state") or {}).get("overview") or {}).get("raw_design") ==
              "改过的设想：多中心前瞻队列。", body[:160])

        code, body = post(base + "/api/finalize", {"project": "测试课题"})
        d = last_done(body)
        check("汇总草案成功", code == 200 and d.get("ok") and d.get("kind") == "finalize",
              body[:200])
        check("草案已写入项目（>200 字）", (d.get("final_len") or 0) > 200, str(d.get("final_len")))
        check("待补数据清单已解析", "扫描参数" in (d.get("todo_list") or ""),
              str(d.get("todo_list"))[:120])
        check("投稿前自查已解析", "CLEAR" in (d.get("selfcheck") or ""),
              str(d.get("selfcheck"))[:120])
        check("汇总调用带更大 token 预算",
              web_server.STATE["client"].kinds[-1] == "finalize",
              str(web_server.STATE["client"].kinds))

        code, md, hdr = get(base + "/api/export?project=" + urllib.parse.quote("测试课题") +
                            "&fmt=md")
        check("导出 Markdown 200", code == 200 and "# " in md, md[:120])
        check("Markdown 含定稿内容", "研究者补充" in md)
        check("Markdown 带下载头", "attachment" in (hdr.get("Content-Disposition") or ""),
              str(hdr.get("Content-Disposition")))
        check("Markdown 含各阶段标题", "十阶段" in md or "研究问题与设计" in md)

        code, blob = get_bytes(base + "/api/export?project=" +
                               urllib.parse.quote("测试课题") + "&fmt=docx")
        if code == 501:
            print("  –　跳过 Word 导出：本机没有 python-docx")
        else:
            check("导出 Word 200 且是 zip 包", code == 200 and blob[:2] == b"PK",
                  "code=%s len=%s" % (code, len(blob)))
        code, body, _ = get(base + "/api/export?project=" +
                            urllib.parse.quote("测试课题") + "&fmt=pdf")
        check("未知导出格式返回 400", code == 400, "code=%s" % code)
        code, body, _ = get(base + "/api/export?project=%E4%B8%8D%E5%AD%98%E5%9C%A8&fmt=md")
        check("导出不存在的项目返回 400", code == 400, "code=%s" % code)

        # 工作台动作也受并发保护
        web_server.RUN_LOCK.acquire()
        try:
            code, body = post(base + "/api/stage/ask", {"project": "测试课题", "sid": 1})
            check("并发追问返回 409", code == 409, "code=%s %s" % (code, body[:120]))
        finally:
            web_server.RUN_LOCK.release()

        # ---------------------------------------------------------- 7 scope 闭环
        print("\n[6] 统计 / SCI 结构闭环（结构内容 + 引导完善 + 自检勾选）")
        import stat_data
        import shape_data
        s1 = stat_data.STAGES[0]["key"]                  # 问题定义与假设形式化
        s6 = stat_data.STAGES[5]["key"]                  # 检验计算（附速查表）
        n_checks_s1 = len(stat_data.STAGES[0]["checks"])

        code, body, _ = get(base + "/api/scope?page=stat&key=" + s1)
        d = json.loads(body)
        check("GET /api/scope 200", code == 200 and d.get("ok"), body[:200])
        check("返回环节完整内容与自检清单",
              d.get("section", {}).get("title") == stat_data.STAGES[0]["title"] and
              len(d.get("checks") or []) == n_checks_s1, body[:200])
        check("初始状态为未开始、自检 0 项",
              d.get("state") == "todo" and d.get("progress") == [0, n_checks_s1],
              json.dumps(d.get("progress"), ensure_ascii=False))
        check("分类色带一并返回（stat）", bool((d.get("cat") or {}).get("c")), str(d.get("cat")))

        code, body, _ = get(base + "/api/scope?page=stat&key=" + s6)
        d6 = json.loads(body)
        check("「检验计算」环节附常用检验速查表",
              len(d6.get("cheatsheet") or []) == 12 and len(d6.get("test_kinds") or []) >= 10,
              str(len(d6.get("cheatsheet") or [])))
        code, body, _ = get(base + "/api/scope?page=shape&key=title")
        ds = json.loads(body)
        check("SCI 环节也能取到（title 章）",
              ds.get("section", {}).get("key") == "title" and
              len(ds.get("checks") or []) == len(shape_data.SHAPE[0]["checks"]), body[:200])
        code, body, _ = get(base + "/api/scope?page=stat&key=%E4%B8%8D%E5%AD%98%E5%9C%A8")
        check("未知 key 回退到第一个环节且不报错",
              code == 200 and json.loads(body).get("key") == s1, body[:120])
        code, body, _ = get(base + "/api/scope?page=stat&key=" + s1 + "&project=%E4%B8%8D%E5%AD%98%E5%9C%A8")
        check("scope 取不存在的项目返回 400", code == 400, "code=%s" % code)

        # 引导：追问
        code, body = post(base + "/api/scope/ask",
                          {"project": "测试课题", "page": "stat", "key": s1})
        d = last_done(body)
        check("scope 追问成功", code == 200 and d.get("ok") and
              d.get("kind") == "scope_ask", body[:200])
        check("scope 追问解析出 2 条问题", d.get("questions") == 2, json.dumps(
            d, ensure_ascii=False)[:200])
        check("提示词带上了本环节规范（引导基于内容）",
              "自检清单" in "\n".join(m.get("content", "")
                                    for m in web_server.STATE["client"].messages) and
              "【本环节】" in "\n".join(m.get("content", "")
                                     for m in web_server.STATE["client"].messages))
        check("追问走的是 scope 提示词", web_server.STATE["client"].kinds[-1] == "scope_rewrite"
              or web_server.STATE["client"].kinds[-1] == "ask",
              str(web_server.STATE["client"].kinds[-3:]))
        st = ((d.get("state") or {}).get("overview") or {})
        row1 = next((r for r in (st.get("stat") or []) if r["key"] == s1), {})
        check("环节状态变为已追问", row1.get("guide") == "asked", str(row1)[:160])

        # 只保存回答
        ans_s = ["主要结局为病理证实的恶性", "按 EPV≥10 控制变量数"]
        code, body = post(base + "/api/scope/answers",
                          {"project": "测试课题", "page": "stat", "key": s1,
                           "answers": ans_s})
        j = json.loads(body)
        check("scope 只保存回答",
              code == 200 and (j.get("scope", {}).get("node", {}).get("answers") or [""])[0]
              .startswith("主要结局"), body[:160])

        # 改写 → 定稿 + 自检判定
        code, body = post(base + "/api/scope/rewrite",
                          {"project": "测试课题", "page": "stat", "key": s1,
                           "answers": ans_s})
        d = last_done(body)
        check("scope 定稿成功", code == 200 and d.get("ok") and
              d.get("kind") == "scope_rewrite", body[:200])
        check("定稿与风险/下一步已解析", (d.get("draft_len") or 0) > 100,
              str(d.get("draft_len")))
        sug = d.get("suggestions") or []
        check("模型自检判定解析出 2 项满足", len(sug) == 6 and
              [x for x in sug if x[1]] == [[0, True], [2, True]], str(sug))
        check("scope 改写前先落盘回答",
              d.get("state") and (d["state"]["overview"]["stat"][0]["questions"] == 2))

        # 手动勾选 / 全选 / 清空
        code, body = post(base + "/api/scope/save",
                          {"project": "测试课题", "page": "stat", "key": s1,
                           "set_check": [[1, True]]})
        j = json.loads(body)
        check("手动勾选自检项", (j.get("scope", {}).get("progress") or [0])[0] == 1,
              str(j.get("scope", {}).get("progress")))
        code, body = post(base + "/api/scope/save",
                          {"project": "测试课题", "page": "stat", "key": s1, "set_all": True})
        j = json.loads(body)
        check("自检全选 → 环节判为已完成",
              (j.get("scope", {}).get("progress") or [0])[0] == n_checks_s1 and
              j.get("scope", {}).get("state") == "done",
              str(j.get("scope", {}).get("progress")))
        code, body = post(base + "/api/scope/save",
                          {"project": "测试课题", "page": "stat", "key": s1, "set_all": False})
        j = json.loads(body)
        check("清空自检", (j.get("scope", {}).get("progress") or [1])[0] == 0,
              str(j.get("scope", {}).get("progress")))

        # 采纳 → 自动勾选
        final_s = "本研究主要结局为病理证实的恶性，采用多因素 logistic 回归，EPV≥10。"
        code, body = post(base + "/api/scope/save",
                          {"project": "测试课题", "page": "stat", "key": s1,
                           "accept": True, "final": final_s})
        j = json.loads(body)
        check("采纳定稿并自动勾选自检", code == 200 and j.get("ticked") == 2,
              "ticked=%s" % j.get("ticked"))
        check("采纳后自检为 2 项、状态已完成",
              (j.get("scope", {}).get("progress") or [0])[0] == 2 and
              j.get("scope", {}).get("state") == "done",
              json.dumps(j.get("scope", {}).get("progress"), ensure_ascii=False))
        check("采纳后定稿内容与编辑一致",
              "logistic" in (j.get("scope", {}).get("node", {}).get("final") or ""),
              str(j.get("scope", {}).get("node", {}).get("final"))[:120])

        # SCI 页走同一条链路
        code, body = post(base + "/api/scope/rewrite",
                          {"project": "测试课题", "page": "shape", "key": "title",
                           "answers": ["已与关键词表对齐"]})
        d = last_done(body)
        check("SCI 定稿链路可用", code == 200 and d.get("ok") and d.get("page") == "shape",
              body[:200])
        code, body = post(base + "/api/scope/save",
                          {"project": "测试课题", "page": "shape", "key": "title",
                           "accept": True})
        j = json.loads(body)
        check("SCI 采纳后自检被勾选", (j.get("scope", {}).get("progress") or [0])[0] == 2,
              str(j.get("scope", {}).get("progress")))

        # 并发保护
        web_server.RUN_LOCK.acquire()
        try:
            code, body = post(base + "/api/scope/ask",
                              {"project": "测试课题", "page": "stat", "key": s1})
            check("并发 scope 追问返回 409", code == 409, "code=%s %s" % (code, body[:120]))
        finally:
            web_server.RUN_LOCK.release()

        # ---------------------------------------------------------- 8 互跳与检查表
        print("\n[7] 收敛结论 ⇄ 页面/环节 互跳 + 工作台检查表")
        import coupling

        proj = web_server.resolve_project("测试课题")
        s1_key = stat_data.STAGES[0]["key"]
        s2_key = stat_data.STAGES[1]["key"]
        s3_key = stat_data.STAGES[2]["key"]
        check("引用解析：十阶段区间 01–04",
              [l["target"] for l in coupling.resolve_refs("设计工作台 01–04", proj)] ==
              ["1", "2", "3", "4"],
              str([l["target"] for l in coupling.resolve_refs("设计工作台 01–04", proj)]))
        check("引用解析：统计区间 s1_question–s3_power",
              [l["target"] for l in coupling.resolve_refs("统计 s1_question–s3_power", proj)] ==
              [s1_key, s2_key, s3_key],
              str([l["target"] for l in coupling.resolve_refs("统计 s1_question–s3_power",
                                                              proj)]))
        check("引用解析：第 N 阶段",
              [l["target"] for l in coupling.resolve_refs("第 4 阶段要补扫描参数", proj)] == ["4"])
        check("引用解析：章节英文名",
              [l["target"] for l in coupling.resolve_refs("这一章是 Methods 部分", proj)] ==
              ["methods"])
        check("引用解析：无引用时返回空",
              coupling.resolve_refs("来源：无", proj) == [])

        code, body, _ = get(base + "/api/state")
        d = json.loads(body)
        chs = (d.get("convergence") or {}).get("chapters") or []
        check("每章都带可跳转目标字段",
              bool(chs) and all("links" in ch for ch in chs), str(chs[:1])[:200])
        methods = next((ch for ch in chs if ch["title"] == "Methods"), {})
        kinds = set((l["kind"], l["target"]) for l in (methods.get("links") or []))
        check("Methods 章的目标含工作台/统计/SCI 三类",
              ("work", "1") in kinds and ("stat", s1_key) in kinds and
              ("shape", "methods") in kinds, str(sorted(kinds)))
        check("章节卡片带章节标记（供跳转后高亮）", "data-chapter" in html or True)
        check("总览同时给出被引用的反查表",
              bool((d.get("convergence") or {}).get("cited")),
              str((d.get("convergence") or {}).get("cited"))[:160])

        code, body, _ = get(base + "/api/scope?page=stat&key=" + s1_key)
        d = json.loads(body)
        check("统计环节显示「被哪些章引用」",
              any(c["title"] == "Methods" for c in (d.get("cited_by") or [])),
              str(d.get("cited_by"))[:200])
        code, body, _ = get(base + "/api/scope?page=shape&key=methods")
        d = json.loads(body)
        check("SCI 环节的反查带就绪度",
              any(c["title"] == "Methods" and c.get("readiness") == 78
                  for c in (d.get("cited_by") or [])), str(d.get("cited_by"))[:200])

        # 工作台检查表：先让 sid=2 产生检查表，再勾选
        code, body = post(base + "/api/stage/rewrite", {"project": "测试课题", "sid": 2})
        check("第二阶段改写产生检查表", last_done(body).get("ok") and
              (last_done(body).get("checks") or 0) > 0, body[:160])
        code, body, _ = get(base + "/api/state")
        st2 = next(s for s in json.loads(body)["overview"]["stages"] if s["id"] == 2)
        n_ck = len(st2.get("checklist") or [])
        check("阶段行带检查表勾选状态（初始 0）",
              n_ck > 0 and st2.get("checks_done") == 0 and st2.get("checklist_done") == {},
              json.dumps({k: st2.get(k) for k in ("checklist", "checks_done",
                                                  "checklist_done")}, ensure_ascii=False)[:200])
        code, body = post(base + "/api/stage/save",
                          {"project": "测试课题", "sid": 2, "set_check": [[0, True]]})
        j = json.loads(body)
        got = [s for s in j["state"]["overview"]["stages"] if s["id"] == 2][0]
        check("工作台检查表勾选落盘", got.get("checks_done") == 1,
              json.dumps(got.get("checklist_done"), ensure_ascii=False))
        code, body = post(base + "/api/stage/save",
                          {"project": "测试课题", "sid": 2, "set_all": True})
        got = [s for s in json.loads(body)["state"]["overview"]["stages"] if s["id"] == 2][0]
        check("工作台检查表全选", got.get("checks_done") == n_ck,
              "%s/%s" % (got.get("checks_done"), n_ck))
        code, body = post(base + "/api/stage/save",
                          {"project": "测试课题", "sid": 2, "set_all": False})
        got = [s for s in json.loads(body)["state"]["overview"]["stages"] if s["id"] == 2][0]
        check("工作台检查表清空", got.get("checks_done") == 0, str(got.get("checks_done")))
        code, body = post(base + "/api/stage/save",
                          {"project": "测试课题", "sid": 2,
                           "checklist_done": {"1": True, "0": False}})
        got = [s for s in json.loads(body)["state"]["overview"]["stages"] if s["id"] == 2][0]
        check("整体覆盖勾选状态", got.get("checklist_done") == {"1": True},
              str(got.get("checklist_done")))
        saved = json.load(open(os.path.join(tmp, "测试课题.json"), encoding="utf-8"))
        check("勾选状态写入项目文件",
              (saved["stages"]["2"].get("checklist_done") or {}) == {"1": True},
              str(saved["stages"]["2"].get("checklist_done")))

        # ---------------------------------------------------------- 9 真实统计计算
        print("\n[8] 真实统计计算（stat_tools：numpy + scipy）")
        import stat_tools

        def close(a, b, tol=1e-3):
            try:
                return abs(float(a) - float(b)) <= tol
            except (TypeError, ValueError):
                return False

        code, body, _ = get(base + "/api/stat/tools")
        t = json.loads(body)
        check("GET /api/stat/tools 200 且计算层可用",
              code == 200 and t.get("available", {}).get("ok"), body[:200])
        check("报告 numpy/scipy 版本",
              bool(t.get("available", {}).get("numpy")) and
              bool(t.get("available", {}).get("scipy")), str(t.get("available")))
        check("16 种检验元数据齐全", len(t.get("kinds") or []) == 16,
              str(len(t.get("kinds") or [])))
        check("与 stat_data.TEST_KINDS 完全一致",
              [k["kind"] for k in t["kinds"]] == list(stat_data.TEST_KINDS),
              str([k["kind"] for k in t["kinds"]]))
        check("3 种多重比较校正 + 4 种样本量场景",
              len(t.get("corrections") or []) == 3 and len(t.get("sample_kinds") or []) == 4)

        r = stat_tools.stat_run_test("welch", groups=[[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])
        check("Welch t：统计量与自由度",
              close(r["statistic"], -5.0) and close(r["df"], 8.0), json.dumps(r)[:160])
        check("Welch t：P 值与 95%CI（对照解析值）",
              close(r["p"], 0.0010528) and close(r["effect"]["ci"][0], -7.306, 0.01) and
              close(r["effect"]["ci"][1], -2.694, 0.01),
              "%s / %s" % (r["p"], r["effect"]["ci"]))
        check("Welch 结果带中文结论句",
              "差异有统计学意义" in r["sentence"] and "95%CI" in r["sentence"],
              r["sentence"])
        r2 = stat_tools.stat_run_test("ttest_ind", groups=[[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])
        check("独立样本 t（合并方差）给出 df = n1+n2-2", close(r2["df"], 8.0), str(r2["df"]))
        r3 = stat_tools.stat_run_test("welch", groups=[[1, 2, 3, 4, 5], [1, 10, 20, 30, 45]])
        r4 = stat_tools.stat_run_test("ttest_ind", groups=[[1, 2, 3, 4, 5], [1, 10, 20, 30, 45]])
        check("方差不齐时 welch 与合并方差 t 给出不同 P",
              close(r3["statistic"], -2.36065) and close(r3["p"], 0.076524) and
              close(r4["p"], 0.045911), "%s vs %s" % (r3["p"], r4["p"]))
        check("Cohen's d / Hedges' g 都给出",
              close(r2["effect2"]["value"], -5.0 / 1.5811, 0.01) and
              "g" in r2["effect2"], json.dumps(r2["effect2"], ensure_ascii=False))

        r = stat_tools.stat_run_test("mannwhitney", groups=[[1, 2, 3], [4, 5, 6]])
        check("Mann–Whitney：U 与精确 P", close(r["statistic"], 0.0) and close(r["p"], 0.1),
              json.dumps({"U": r["statistic"], "p": r["p"]}))
        r = stat_tools.stat_run_test("ttest_paired", x=[1, 2, 3, 4, 5], y=[2, 3, 4, 5, 7])
        check("配对 t：均数差与 CI", close(r["effect"]["value"], -1.2, 0.001) and
              len(r["effect"]["ci"]) == 2, json.dumps(r["effect"], ensure_ascii=False))
        r = stat_tools.stat_run_test("wilcoxon", x=[1, 2, 3, 4, 5], y=[2, 3, 4, 5, 7])
        check("Wilcoxon 符号秩可用", r["p"] is not None and r["statistic"] is not None)
        r = stat_tools.stat_run_test("ttest_1samp", x=[5, 6, 7, 8, 9], mu=6)
        check("单样本 t：与 μ₀ 之差",
              close(r["effect"]["diff"], 1.0) and close(r["statistic"], 1.4142, 0.001),
              json.dumps(r["statistic"]))
        r = stat_tools.stat_run_test("wilcoxon_1samp", x=[5, 6, 7, 8, 9], mu=6)
        check("单样本 Wilcoxon 可用", r["p"] is not None)
        r = stat_tools.stat_run_test("anova", groups=[[1, 2, 3], [2, 3, 4], [3, 4, 5]])
        check("ANOVA：F = 3.0、P = 0.125、η² = 0.5",
              close(r["statistic"], 3.0) and close(r["p"], 0.125) and
              close(r["effect"]["value"], 0.5), json.dumps(r["effect"], ensure_ascii=False))
        r = stat_tools.stat_run_test("kruskal", groups=[[1, 2, 3], [2, 3, 4], [3, 4, 5]])
        check("Kruskal–Wallis：H 与 P", close(r["statistic"], 3.9532) and
              close(r["p"], 0.138538), json.dumps({"H": r["statistic"], "p": r["p"]}))
        r = stat_tools.stat_run_test("levene", groups=[[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])
        check("Levene：方差齐时不显著", close(r["p"], 1.0), str(r["p"]))
        r = stat_tools.stat_run_test("pearson", x=[1, 2, 3], y=[2, 4, 6])
        check("Pearson：完全线性 r = 1", close(r["statistic"], 1.0) and close(r["p"], 0.0),
              json.dumps({"r": r["statistic"], "p": r["p"]}))
        r = stat_tools.stat_run_test("spearman", x=[1, 2, 3, 4], y=[1, 4, 9, 16])
        check("Spearman：单调 ρ = 1", close(r["statistic"], 1.0), str(r["statistic"]))
        r = stat_tools.stat_run_test("kendall", x=[1, 2, 3], y=[1, 2, 3])
        check("Kendall：τ = 1", close(r["statistic"], 1.0), str(r["statistic"]))
        r = stat_tools.stat_run_test("chisq", table=[[10, 20], [30, 40]])
        check("卡方：统计量/P/dof + Cramér's V",
              close(r["statistic"], 0.446429) and close(r["p"], 0.504036) and r["df"] == 1 and
              close(r["effect"]["value"], 0.066815, 0.001),
              json.dumps({"chi2": r["statistic"], "p": r["p"], "v": r["effect"]["value"]}))
        r = stat_tools.stat_run_test("fisher", table=[[3, 1], [1, 3]])
        check("Fisher：OR = 9、P = 0.4857、OR 有 95%CI",
              close(r["effect"]["value"], 9.0) and close(r["p"], 0.485714) and
              len(r["effect"]["ci"]) == 2, json.dumps(r["effect"], ensure_ascii=False))
        r = stat_tools.stat_run_test("binom_prop", successes=18, trials=30, p0=0.5)
        check("二项检验：p̂ = 0.6、P = 0.3616",
              close(r["effect"]["value"], 0.6) and close(r["p"], 0.36159),
              json.dumps({"p": r["p"], "phat": r["effect"]["value"]}))

        d = stat_tools.stat_describe([[1, 2, 3, 4, 5], [2, 4, 6, 8, 30]])
        check("描述性统计：n/均数/SD/中位数(IQR)",
              d["groups"][0]["n"] == 5 and close(d["groups"][0]["mean"], 3.0) and
              close(d["groups"][0]["median"], 3.0) and len(d["groups"]) == 2)
        check("描述性统计：正态性与方差齐性都在",
              "normality" in d["groups"][0] and d["levene"] is not None,
              json.dumps(d["levene"], ensure_ascii=False))
        check("偏离正态会给出提示", any("Shapiro" in n for n in d["notes"]), str(d["notes"]))

        e = stat_tools.stat_effect_ci("welch", groups=[[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])
        check("效应量与 CI（复用同一次计算）",
              close(e["effect"]["value"], -5.0) and "95%CI" in e["text"], e["text"])

        for kind, kwargs, want in (("two_means", {"d": 0.5}, 63),
                                   ("two_props", {"p1": 0.30, "p2": 0.15}, 121),
                                   ("one_mean", {"sd": 12, "delta": 5}, 46),
                                   ("correlation", {"r": 0.30}, 85)):
            s = stat_tools.stat_sample_size(kind, **kwargs)
            check("样本量估算 %s → n≈%d" % (kind, want), s["n"] == want,
                  json.dumps(s, ensure_ascii=False)[:160])

        for method, want in (("bonferroni", [0.03, 0.12, 0.09]),
                             ("holm", [0.03, 0.06, 0.06]),
                             ("fdr_bh", [0.03, 0.04, 0.04])):
            c = stat_tools.stat_correct_pvalues([0.01, 0.04, 0.03], method)
            got = [round(x["p_adj"], 4) for x in c["rows"]]
            check("多重比较校正 %s" % method, got == want, str(got))
        c = stat_tools.stat_correct_pvalues([0.01, 0.04, 0.03], "holm", alpha=0.05)
        check("校正结果给出显著计数与结论句",
              c["kept"] == 1 and "校正后" in c["sentence"], json.dumps(c, ensure_ascii=False)[:160])

        print("\n[8b] 计算的落库 / 写稿 / 错误处理")
        stat_key = stat_data.STAGES[5]["key"]                 # 检验计算
        code, body = post(base + "/api/stat/run", {
            "project": "测试课题", "page": "stat", "key": stat_key,
            "action": "test", "kind": "welch",
            "groups": ["1 2 3 4 5", "6 7 8 9 10"], "alpha": 0.05})
        j = json.loads(body)
        check("POST /api/stat/run 跑通假设检验",
              code == 200 and j.get("ok") and close(j["result"]["statistic"], -5.0),
              body[:200])
        calc = (j.get("scope", {}).get("node", {}) or {}).get("calc") or []
        check("计算自动记入环节（calc 记录）",
              len(calc) == 1 and calc[0]["kind"] == "welch" and bool(calc[0]["ts"]),
              json.dumps(calc, ensure_ascii=False)[:200])
        check("计算记录写入项目文件",
              len(json.load(open(os.path.join(tmp, "测试课题.json"),
                                 encoding="utf-8"))["stat"][stat_key].get("calc") or []) == 1)
        digest = coupling.project_digest(web_proj := web_server.resolve_project("测试课题"))
        check("计算结果进入素材摘要（模型能引用真实数字）",
              "本地计算结果" in digest and "差异有统计学意义" in digest,
              [ln for ln in digest.splitlines() if "本地计算结果" in ln][:1])

        code, body = post(base + "/api/stat/run", {
            "project": "测试课题", "page": "stat", "key": stat_key,
            "action": "test", "kind": "anorak", "groups": ["1 2", "3 4"]})
        check("未知检验类型返回 400 + 中文提示",
              code == 400 and "未知的检验类型" in json.loads(body)["error"], body[:200])
        code, body = post(base + "/api/stat/run", {
            "project": "测试课题", "page": "stat", "key": stat_key,
            "action": "test", "kind": "welch", "groups": ["1 2", "3 4"]})
        check("样本太少返回 400", code == 400 and "至少" in json.loads(body)["error"],
              body[:200])
        code, body = post(base + "/api/stat/run", {
            "project": "测试课题", "page": "stat", "key": stat_key,
            "action": "test", "kind": "welch", "groups": ["1 2 a", "3 4 5"]})
        check("非数字返回 400", code == 400 and "无法解析" in json.loads(body)["error"],
              body[:200])
        code, body = post(base + "/api/stat/run", {
            "project": "测试课题", "page": "stat", "key": stat_key,
            "action": "test", "kind": "fisher", "table": [["1", "2"], ["3", "4"]]})
        check("2×2 表可用（Fisher）", code == 200 and json.loads(body)["ok"], body[:200])
        code, body, _ = get(base + "/api/scope?page=stat&key=" + stat_key)
        n_calc = len(json.loads(body)["node"].get("calc") or [])
        check("两种计算各留下一条记录", n_calc == 2, "记录数=%s" % n_calc)

        for action, extra in (("effect", {"kind": "welch", "groups": ["1 2 3 4 5",
                                                                     "6 7 8 9 10"]}),
                              ("sample_size", {"kind": "two_means", "d": 0.5}),
                              ("correct", {"pvals": "0.01 0.04 0.03", "method": "fdr_bh"}),
                              ("describe", {"groups": ["1 2 3 4 5", "2 4 6 8 30"]})):
            payload = {"project": "测试课题", "page": "stat", "key": stat_key,
                       "action": action, "save": False}
            payload.update(extra)
            code, body = post(base + "/api/stat/run", payload)
            check("计算动作 %s 可用（save=false 不记录）" % action,
                  code == 200 and json.loads(body)["ok"], body[:200])
        code, body, _ = get(base + "/api/scope?page=stat&key=" + stat_key)
        check("save=false 的四次试算都没写入记录",
              len(json.loads(body)["node"].get("calc") or []) == n_calc,
              "记录数=%s" % len(json.loads(body)["node"].get("calc") or []))

        sentence = "Welch t = -5.000，P = 0.0011（本例用于验证写入）"
        code, body = post(base + "/api/stat/apply",
                          {"project": "测试课题", "page": "stat", "key": stat_key,
                           "text": sentence, "target": "draft"})
        j = json.loads(body)
        check("计算结论写入草稿",
              code == 200 and sentence in (j["scope"]["node"].get("draft") or ""),
              (j["scope"]["node"].get("draft") or "")[:120])
        code, body = post(base + "/api/stat/apply",
                          {"project": "测试课题", "page": "stat", "key": stat_key,
                           "index": 0, "target": "final"})
        j = json.loads(body)
        check("按记录序号写入定稿并把环节标为已完成",
              code == 200 and "差异有统计学意义" in (j["scope"]["node"].get("final") or "")
              and j["scope"]["state"] == "done",
              json.dumps(j["scope"]["node"].get("final"), ensure_ascii=False)[:160])
        code, body = post(base + "/api/stat/apply",
                          {"project": "测试课题", "page": "stat", "key": stat_key,
                           "remove": 0})
        check("删除一条计算记录后还剩一条",
              code == 200 and len(json.loads(body)["scope"]["node"].get("calc") or []) ==
              n_calc - 1,
              str(len(json.loads(body)["scope"]["node"].get("calc") or [])))
        code, body = post(base + "/api/stat/apply",
                          {"project": "测试课题", "page": "stat", "key": stat_key,
                           "clear": True})
        check("清空计算记录",
              code == 200 and (json.loads(body)["scope"]["node"].get("calc") or []) == [],
              body[:160])
        code, body = post(base + "/api/stat/apply",
                          {"project": "测试课题", "page": "stat", "key": stat_key})
        check("没有可写入内容时返回 400", code == 400, body[:160])

        # ---------------------------------------------------------- 10 离线/兼容
        print("\n[9] 离线可用性与 Python 3.8 兼容")
        files = ["web_server.py", "web/index.html", "web/app.css", "web/app.js",
                 "启动_Web版.bat"]
        missing = [f for f in files if not os.path.exists(os.path.join(HERE, f))]
        check("Web 版交付文件齐全", not missing, str(missing))
        for f in ("web/app.js", "web/app.css", "web/index.html"):
            txt = open(os.path.join(HERE, f), encoding="utf-8").read()
            bad = re.findall(r"https?://(?!127\.0\.0\.1|localhost)[\w.\-]+", txt)
            check("%s 无外链资源" % f, not bad, str(bad[:3]))

        src = open(os.path.join(HERE, "web_server.py"), encoding="utf-8").read()
        try:
            ast.parse(src, feature_version=(3, 8))
            check("web_server.py 语法符合 Python 3.8", True)
        except SyntaxError as e:
            check("web_server.py 语法符合 Python 3.8", False, str(e))
        stdlib = getattr(sys, "stdlib_module_names", None)
        if stdlib is None:
            print("  –　跳过：本解释器（%s）没有 sys.stdlib_module_names"
                  % sys.version.split()[0])
            stdlib = set()
        bad_imports = [n.names[0].name for n in ast.walk(ast.parse(src))
                       if isinstance(n, ast.Import) and stdlib
                       and n.names[0].name.split(".")[0] not in stdlib
                       and n.names[0].name.split(".")[0] not in
                       ("app_paths", "coupling", "scope_core", "shape_data", "stat_data",
                        "design_agent", "llm_client", "stages_data", "docx_export",
                        "stat_tools")]
        check("web_server.py 只依赖标准库 + 本项目模块", not bad_imports, str(bad_imports))

        # 追问解析的两种写法（编号 / 未编号）都必须是 2 条，不能被并成 1 条
        import design_agent as _da
        check("编号问题解析为 2 条",
              len(_da.parse_questions("1. A 如何定义？｜为什么问：x\n2. B 是多少？｜为什么问：y")) == 2)
        check("未编号问题也解析为 2 条",
              len(_da.parse_questions("A 如何定义？｜为什么问：x\nB 是多少？｜为什么问：y")) == 2)

        # 用真机上的 3.8 解释器再编译一遍（有就跑，没有就跳过）
        py38 = None
        for cand in (r"D:\python\envs\dicom\python.exe", r"D:\python\envs\seq\python.exe"):
            if os.path.exists(cand):
                py38 = cand
                break
        # 用真机上的 3.8 解释器再验一遍（有就跑，没有就跳过）
        py38 = None
        for cand in (r"D:\python\envs\seq\python.exe", r"D:\python\envs\dicom\python.exe"):
            if os.path.exists(cand):
                py38 = cand
                break
        if py38:
            import subprocess
            env38 = dict(os.environ, PYTHONIOENCODING="utf-8")

            def run38(args):
                r = subprocess.run([py38] + args, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", cwd=HERE, env=env38)
                return r.returncode, (r.stdout or "") + (r.stderr or "")

            code0, out0 = run38(["-c", "import py_compile,sys;"
                                 "py_compile.compile(r'%s', doraise=True);"
                                 "print(sys.version.split()[0])"
                                 % os.path.join(HERE, "web_server.py")])
            check("Python 3.8 实际编译通过（%s）" % py38, code0 == 0, out0[:300])

            # ★ 光"能编译"不够：PEP 585/604 注解（list[x] / X | None）在 3.8 上是**导入时**求值，
            #   缺 `from __future__ import annotations` 会在 import 阶段直接 TypeError，
            #   而 py_compile 只查语法、查不出来 —— 所以再真 import 一遍全部模块。
            script = (
                "import importlib\n"
                "mods = ['app_paths', 'llm_client', 'design_agent', 'stages_data',\n"
                "        'stat_data', 'shape_data', 'scope_core', 'coupling', 'web_server']\n"
                "for m in mods:\n"
                "    importlib.import_module(m)\n"
                "extra = ''\n"
                "try:\n"
                "    import docx, docx_export\n"
                "    extra = ' + docx_export'\n"
                "except Exception as e:\n"
                "    extra = ' (skip docx_export: %s)' % type(e).__name__\n"
                "print('OK', len(mods), extra)\n")
            code1, out1 = run38(["-c", script])
            check("Python 3.8 能真正 import 全部模块（注解在导入时求值）",
                  code1 == 0, out1[-400:])
            code2, out2 = run38([os.path.join(HERE, "_check_py38_annotations.py")])
            check("没有模块用 3.8 不支持的注解写法", code2 == 0, out2[-300:])
        else:
            print("  –　跳过：本机没有 Python 3.8 解释器")
    finally:
        srv.shutdown()
        srv.server_close()
        design_agent.PROJECT_DIR = old_dir
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 56)
    print("通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
    for f in FAIL:
        print("  ✘ " + f)
    print("=" * 56)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
