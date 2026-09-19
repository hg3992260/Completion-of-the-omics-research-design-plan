# -*- coding: utf-8 -*-
"""合并版 exe 自检：CLI / API / MCP-http / GUI(控制台是否隐藏)。"""
import ctypes
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(ROOT, "dist", "PCLRadiomics")
EXE = os.path.join(APP_DIR, "PCLRadiomics.exe")
OUT = os.path.join(ROOT, "_merged_test.txt")
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
lines = []
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def note(m):
    lines.append(m)
    try:
        print(m)
    except Exception:
        pass


def run(args, timeout=180):
    t0 = time.time()
    p = subprocess.run([EXE] + args, capture_output=True, cwd=APP_DIR, timeout=timeout, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "ignore"), time.time() - t0


def windows_of(pid):
    """列出该进程的顶层窗口及其可见性（含控制台窗口 ConsoleWindowClass）。"""
    found = []
    u32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _):
        wpid = ctypes.c_ulong()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid:
            cls = ctypes.create_unicode_buffer(256)
            u32.GetClassNameW(hwnd, cls, 256)
            title = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(hwnd, title, 256)
            found.append((cls.value, title.value, bool(u32.IsWindowVisible(hwnd))))
        return True

    u32.EnumWindows(WNDENUMPROC(cb), None)
    return found


try:
    note(f"exe: {EXE}  存在={os.path.exists(EXE)}")

    for args in (["paths"], ["stages"], ["projects"]):
        code, out, sec = run(args)
        head = next((l for l in out.splitlines() if l.strip()), "(空)")
        note(f"`{' '.join(args)}` → 退出码 {code}　{sec:.1f}s　{head.strip()[:60]}")

    code, out, sec = run(["check"])
    keep = [l.strip() for l in out.splitlines() if any(k in l for k in ("可用模型", "结论", "数据目录"))]
    note("`check` → " + " ｜ ".join(keep))

    # ---- OpenAI API 模式
    proc = subprocess.Popen([EXE, "api", "--port", "8801"], cwd=APP_DIR, env=ENV,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        h = None
        for _ in range(60):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8801/health", timeout=3) as r:
                    h = json.loads(r.read().decode())
                    break
            except Exception:
                continue
        if h:
            note(f"API 模式 → /health {h['status']}　模型={h['model']}")
            payload = json.dumps({"model": h["model"], "max_tokens": 500,
                                  "messages": [{"role": "user", "content": "只回答：MERGED-OK"}]}
                                 ).encode()
            req = urllib.request.Request("http://127.0.0.1:8801/v1/chat/completions",
                                         data=payload,
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=240) as r:
                    d = json.loads(r.read().decode())
                    note("API 模式 → 对话 "
                         f"{d['choices'][0]['message']['content'].strip()[:40]!r}")
            except Exception as e:                                 # noqa: BLE001
                note(f"API 模式 → 对话失败 {type(e).__name__}: {str(e)[:70]}")
        else:
            note("API 模式 → /health 无响应")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:                                          # noqa: BLE001
            proc.kill()

    # ---- MCP http 模式（同一个 exe）
    mp = subprocess.Popen([EXE, "mcp", "--transport", "streamable-http", "--port", "8768"],
                          cwd=APP_DIR, env=ENV,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import asyncio

        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async def call():
            for _ in range(40):
                try:
                    async with streamablehttp_client("http://127.0.0.1:8768/mcp") as (r, w, _):
                        async with ClientSession(r, w) as s:
                            init = await s.initialize()
                            tools = await s.list_tools()
                            res = await s.call_tool("list_stages", {})
                            d = json.loads(res.content[0].text)
                            return (f"MCP(http) → {init.serverInfo.name} "
                                    f"v{init.serverInfo.version}，{len(tools.tools)} 工具，"
                                    f"{len(d)} 阶段")
                except Exception:
                    await asyncio.sleep(0.5)
            return "MCP(http) → 连接失败"

        note(asyncio.run(call()))
    finally:
        mp.terminate()
        try:
            mp.wait(timeout=10)
        except Exception:                                          # noqa: BLE001
            mp.kill()

    # ---- GUI 模式：窗口起来了 + 控制台是否隐藏
    gp = subprocess.Popen([EXE, "gui"], cwd=APP_DIR, env=ENV,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          creationflags=subprocess.CREATE_NEW_CONSOLE)
    try:
        time.sleep=__import__("time").sleep
        time.sleep(18)
        wins = windows_of(gp.pid)
        gui = [w for w in wins if w[0] != "ConsoleWindowClass"]
        con = [w for w in wins if w[0] == "ConsoleWindowClass"]
        note(f"GUI 模式 → 进程存活={gp.poll() is None}")
        note(f"  应用窗口：{[(t, v) for c, t, v in gui]}")
        note(f"  控制台窗口：{[(t, v) for c, t, v in con] or '（无）'}"
             f"　→ 控制台可见性={[v for c, t, v in con] or ['无控制台']}")
    finally:
        gp.terminate()
        try:
            gp.wait(timeout=10)
        except Exception:                                          # noqa: BLE001
            gp.kill()

    note(f"目录：{sorted(os.listdir(APP_DIR))}")
except Exception:                                                  # noqa: BLE001
    import traceback
    note("异常：" + traceback.format_exc()[-600:])

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("done")
