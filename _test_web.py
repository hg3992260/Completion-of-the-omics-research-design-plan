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


class FakeClient(object):
    """假 LLM：不联网，但按真实协议分片回调，用来验证 SSE 通路与解析。"""

    def __init__(self):
        self.model = "fake-reason-model"
        self.base_url = "http://fake.local"
        self.cfg = {"api_key": "sk-fake", "key_source": "test",
                    "temperature": 0.4, "max_tokens": 8000}
        self.calls = []
        self.messages = []

    def chat(self, messages, stream=False, on_delta=None, temperature=None,
             max_tokens=None, reason=False):
        self.calls.append({"stream": stream, "reason": reason, "messages": len(messages)})
        self.messages = messages
        reasoning = "先通读全部素材，再按内容主题判断归属……" * 3
        if on_delta:
            for i in range(0, len(reasoning), 9):
                on_delta(reasoning[i:i + 9], "reasoning")
            for i in range(0, len(DEMO), 13):
                on_delta(DEMO[i:i + 13], "content")
        return {"content": DEMO, "reasoning": reasoning, "usage": {"total_tokens": 1234},
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

        for f, must in (("app.css", "--accent"), ("app.js", "runConvergence"),
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

        # ---------------------------------------------------------- 6 离线/兼容
        print("\n[5] 离线可用性与 Python 3.8 兼容")
        files = ["web_server.py", "web/index.html", "web/app.css", "web/app.js",
                 "启动_Web版.bat"]
        missing = [f for f in files if not os.path.exists(os.path.join(HERE, f))]
        check("Phase 0 交付文件齐全", not missing, str(missing))
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
                        "design_agent", "llm_client", "stages_data")]
        check("web_server.py 只依赖标准库 + 本项目模块", not bad_imports, str(bad_imports))

        # 用真机上的 3.8 解释器再编译一遍（有就跑，没有就跳过）
        py38 = None
        for cand in (r"D:\python\envs\dicom\python.exe", r"D:\python\envs\seq\python.exe"):
            if os.path.exists(cand):
                py38 = cand
                break
        if py38:
            import subprocess
            r = subprocess.run([py38, "-c",
                                "import py_compile,sys;"
                                "py_compile.compile(r'%s', doraise=True);"
                                "print(sys.version.split()[0])"
                                % os.path.join(HERE, "web_server.py")],
                               capture_output=True, text=True)
            check("Python 3.8 实际编译通过（%s）" % py38,
                  r.returncode == 0, (r.stdout + r.stderr)[:300])
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
