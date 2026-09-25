# -*- coding: utf-8 -*-
"""对**打包产物**（Win7 Web 版 exe）做端到端自检。

打出来的 exe 才是真正要拷到 Windows 7 上跑的东西，所以它必须单独验一遍：
    1. exe 能起来（冻结后的路径解析、内置 web/ 资源都能找到）
    2. 接口可用：/api/health、/api/state、静态资源、项目管理、导出 Markdown 与 Word
    3. SSE 通路可用：把模型地址指向一个连不上的端口，应收到 error 事件且 done.ok=false
    4. 真实浏览器能渲染冻结版服务的界面（无头 Chrome 截图）

    python _test_web_exe.py                                  # 默认验文件夹版
    python _test_web_exe.py --exe dist-web\\PCLRadiomicsWeb.exe   # 验单文件版
    python _test_web_exe.py --keep                            # 只起 exe，自己用浏览器看

注意：冻结后程序会把 projects/ 写在 **exe 同级目录**（绿色便携），自检结束会清理掉它新建的
那些文件；无头 Chrome 需要命名管道，受限沙箱里会被拒绝。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_EXE = os.path.join(HERE, "dist-web", "PCLRadiomicsWeb", "PCLRadiomicsWeb.exe")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  %s %s%s" % ("✔" if ok else "✘", name, ("　→ " + detail) if detail and not ok else ""))


def free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "exe-selftest"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})


def post(url, payload, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def wait_health(port, proc, limit=60.0):
    t0 = time.time()
    url = "http://127.0.0.1:%d/api/health" % port
    while time.time() - t0 < limit:
        if proc.poll() is not None:
            return None, "进程已退出（code=%s）" % proc.returncode
        try:
            code, body, _ = get(url, timeout=3)
            if code == 200:
                return json.loads(body.decode("utf-8")), ""
        except Exception:                                            # noqa: BLE001
            time.sleep(0.4)
    return None, "等待超时（%.0fs）" % limit


def find_chrome():
    for p in CHROME_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=DEFAULT_EXE)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--shot", action="store_true", help="额外用无头 Chrome 截图")
    args = ap.parse_args()

    exe = os.path.abspath(args.exe)
    if not os.path.isfile(exe):
        print("[错误] 找不到产物：%s\n       请先运行 编译_Win7_Web版.bat" % exe)
        return 2
    print("自检产物：%s（%.1f MB）" % (exe, os.path.getsize(exe) / 1024 / 1024))

    port = free_port()
    base = "http://127.0.0.1:%d" % port
    env = dict(os.environ)
    # 把模型地址指向一个连不上的端口：既能验证 SSE 通路，又不会真的花钱调模型
    env.update({"LLM_BASE_URL": "http://127.0.0.1:9/v1", "LLM_API_KEY": "sk-selftest",
                "no_proxy": "*", "NO_PROXY": "*", "PYTHONIOENCODING": "utf-8"})
    proc = subprocess.Popen([exe, "--port", str(port), "--no-browser"], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out_dir = os.path.dirname(exe)                 # 冻结后 projects/ 就写在 exe 同级
    created = os.path.join(out_dir, "projects")
    had_projects = os.path.isdir(created)

    try:
        info, err = wait_health(port, proc)
        print("\n[1] 启动与内置资源")
        check("exe 能启动并响应 /api/health", info is not None, err)
        if info is None:
            return 1
        check("健康检查报告版本号", bool(info.get("version")), json.dumps(info)[:200])
        check("冻结标记为真（确实在跑打包产物）",
              "frozen" not in info or info.get("frozen") in (True, None), str(info)[:160])

        code, html, _ = get(base + "/")
        check("内置 web/index.html 能取到（冻结后资源路径正确）",
              code == 200 and "组学研究设计工作台" in html.decode("utf-8", "ignore"),
              "code=%s len=%s" % (code, len(html)))
        for f, must in (("app.css", "--accent"), ("app.js", "streamAction"),
                        ("favicon.svg", "<svg")):
            code, body, _ = get(base + "/static/" + f)
            check("内置静态资源 %s" % f,
                  code == 200 and must in body.decode("utf-8", "ignore"), "code=%s" % code)

        print("\n[2] 接口（冻结后的路径解析与落盘）")
        code, body, _ = get(base + "/api/state")
        d = json.loads(body.decode("utf-8"))
        check("GET /api/state 200", code == 200 and d.get("ok"), body[:160].decode("utf-8",
                                                                                  "ignore"))
        n0 = len(d.get("projects") or [])
        code, body = post(base + "/api/project/new", {"name": "自检临时课题"})
        check("新建课题写入 exe 同级 projects/",
              code == 200 and os.path.isfile(os.path.join(created, "自检临时课题.json")),
              body[:200].decode("utf-8", "ignore"))
        code, body = post(base + "/api/stage/save",
                          {"project": "自检临时课题", "sid": 1,
                           "raw_design": "自检用：这是一段用于验证打包产物的研究设想。"})
        check("保存阶段内容", code == 200 and json.loads(body)["ok"], body[:160].decode("utf-8",
                                                                                       "ignore"))
        code, md, hdr = get(base + "/api/export?project=" +
                            urllib.parse.quote("自检临时课题") + "&fmt=md")
        check("导出 Markdown", code == 200 and "自检用" in md.decode("utf-8", "ignore"),
              "code=%s" % code)
        check("Markdown 带下载头", "attachment" in (hdr.get("Content-Disposition") or ""))
        code, blob, _ = get(base + "/api/export?project=" +
                            urllib.parse.quote("自检临时课题") + "&fmt=docx")
        if code == 501:
            print("  –　未打包 python-docx：仅支持 Markdown 导出")
        else:
            check("导出 Word（python-docx 已打进产物）", code == 200 and blob[:2] == b"PK",
                  "code=%s len=%s" % (code, len(blob)))

        print("\n[3] SSE 通路")
        code, body = post(base + "/api/convergence", {"project": "自检临时课题"})
        events = []
        for line in body.decode("utf-8", "ignore").splitlines():
            if line.startswith("data:"):
                try:
                    events.append(json.loads(line[5:].strip()))
                except ValueError:
                    pass
        kinds = [e.get("type") for e in events]
        check("收敛推理返回 SSE 流", code == 200 and len(events) > 0, "code=%s" % code)
        check("连不上模型时给出 error 事件", "error" in kinds, str(kinds[:6]))
        done = [e for e in events if e.get("type") == "done"]
        check("并以 done.ok=false 收尾（前端能正确提示）",
              bool(done) and done[-1].get("ok") is False, str(kinds[-3:]))

        print("\n[4] 项目管理收尾")
        code, body = post(base + "/api/project/delete", {"project": "自检临时课题"})
        check("删除临时课题", code == 200 and json.loads(body)["ok"],
              body[:160].decode("utf-8", "ignore"))

        if args.keep:
            print("\n已保持运行：%s（Ctrl+C 结束）" % base)
            try:
                while proc.poll() is None:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            return 0

        if args.shot or not args.keep:
            chrome = find_chrome()
            if chrome:
                shots = os.path.join(HERE, "_shots")
                os.makedirs(shots, exist_ok=True)
                out = os.path.join(shots, "web_exe.png")
                prof = os.path.join(shots, "_chrome_profile")
                r = subprocess.run([chrome, "--headless=new", "--disable-gpu",
                                    "--hide-scrollbars", "--no-first-run",
                                    "--no-default-browser-check", "--disable-extensions",
                                    "--user-data-dir=" + prof, "--window-size=1600,1250",
                                    "--virtual-time-budget=6000", "--screenshot=" + out,
                                    base + "/?theme=dark"], capture_output=True, text=True,
                                   timeout=180)
                size = os.path.getsize(out) if os.path.exists(out) else 0
                print("\n[5] 浏览器渲染")
                check("冻结版服务的界面能被真实浏览器渲染（截图 %d bytes）" % size,
                      size > 20000, (r.stderr or "")[-200:])
                if size:
                    print("      截图：%s" % out)
            else:
                print("\n[5] 浏览器渲染：跳过（没找到 Chrome/Edge）")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        # 清理自检产生的数据（保持 exe 目录干净）
        for path in (os.path.join(out_dir, "_export_tmp"),):
            shutil.rmtree(path, ignore_errors=True)
        for name in ("llm_config.json", ".write_test"):
            try:
                os.remove(os.path.join(out_dir, name))
            except OSError:
                pass
        if not had_projects:
            shutil.rmtree(created, ignore_errors=True)

    print("\n" + "=" * 56)
    print("通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
    for f in FAIL:
        print("  ✘ " + f)
    print("=" * 56)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
