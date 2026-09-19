# -*- coding: utf-8 -*-
"""onefile 版 exe 全模式自检：CLI / API / MCP-http / MCP-stdio，并测启动耗时。"""
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = r"I:\文件\CTCC\HL\omics_pipeline"
APP_DIR = os.path.join(ROOT, "dist_onefile")
EXE = os.path.join(APP_DIR, "PCLRadiomics.exe")
OUT = os.path.join(ROOT, "_onefile_test.txt")
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
lines = []
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def note(m):
    lines.append(m)
    try:
        print(m)
    except Exception:
        pass


def run(args, timeout=300):
    t0 = time.time()
    p = subprocess.run([EXE] + args, capture_output=True, cwd=APP_DIR, timeout=timeout, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "ignore"), time.time() - t0


try:
    note(f"onefile exe: {EXE}")
    note(f"体积: {os.path.getsize(EXE)/1048576:.1f} MB（单文件）")

    for args in (["paths"], ["stages"]):
        code, out, sec = run(args)
        head = next((l for l in out.splitlines() if l.strip()), "(空)")
        note(f"`{' '.join(args)}` → 退出码 {code}　耗时 {sec:.1f}s　{head.strip()[:52]}")

    code, out, sec = run(["check"])
    keep = [l.strip() for l in out.splitlines() if any(k in l for k in ("可用模型", "结论", "数据目录"))]
    note(f"`check` → 耗时 {sec:.1f}s　" + " ｜ ".join(keep))

    # ---- API 模式
    t0 = time.time()
    proc = subprocess.Popen([EXE, "api", "--port", "8803"], cwd=APP_DIR, env=ENV,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ready = None
    try:
        for _ in range(80):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8803/health", timeout=3) as r:
                    h = json.loads(r.read().decode())
                    ready = time.time() - t0
                    break
            except Exception:
                continue
        if not ready:
            note("API 模式 → /health 无响应")
        else:
            note(f"API 模式 → 启动到可服务 {ready:.1f}s　/health {h['status']} 模型={h['model']}")
            payload = json.dumps({"model": h["model"], "max_tokens": 500,
                                  "messages": [{"role": "user", "content": "只回答：ONEFILE-OK"}]}
                                 ).encode()
            req = urllib.request.Request("http://127.0.0.1:8803/v1/chat/completions", data=payload,
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    d = json.loads(r.read().decode())
                    note("API 模式 → 对话 "
                         f"{d['choices'][0]['message']['content'].strip()[:40]!r}")
            except Exception as e:                                 # noqa: BLE001
                note(f"API 模式 → 对话失败 {type(e).__name__}: {str(e)[:70]}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()

    # ---- MCP over HTTP
    mp = subprocess.Popen([EXE, "mcp", "--transport", "streamable-http", "--port", "8770"],
                          cwd=APP_DIR, env=ENV,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async def http_call():
            for _ in range(60):
                try:
                    async with streamablehttp_client("http://127.0.0.1:8770/mcp") as (r, w, _):
                        async with ClientSession(r, w) as s:
                            init = await s.initialize()
                            tools = await s.list_tools()
                            res = await s.call_tool("list_stages", {})
                            return (f"MCP(http) → {init.serverInfo.name} v{init.serverInfo.version}"
                                    f"，{len(tools.tools)} 工具，"
                                    f"{len(json.loads(res.content[0].text))} 阶段")
                except Exception:
                    await asyncio.sleep(0.5)
            return "MCP(http) → 连接失败"

        note(asyncio.run(http_call()))
    finally:
        mp.terminate()
        try:
            mp.wait(timeout=15)
        except Exception:
            mp.kill()

    # ---- MCP over stdio（关键：onefile 每次拉起都要解包，看还能不能用）
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def stdio_call():
        t0 = time.time()
        params = StdioServerParameters(command=EXE, args=["mcp"], cwd=APP_DIR)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as s:
                init = await s.initialize()
                t_ready = time.time() - t0
                tools = await s.list_tools()
                res = await s.call_tool("llm_chat",
                                        {"prompt": "只回答：ONEFILE-STDIO-OK", "max_tokens": 400})
                d = json.loads(res.content[0].text)
                return (f"MCP(stdio) → 握手耗时 {t_ready:.1f}s，{len(tools.tools)} 工具，"
                        f"llm_chat {d['elapsed']:.1f}s {d['content'].strip()[:28]!r}")

    try:
        note(asyncio.run(stdio_call()))
    except Exception:                                              # noqa: BLE001
        import traceback
        note("MCP(stdio) → 失败：" + traceback.format_exc()[-400:])
except Exception:                                                  # noqa: BLE001
    import traceback
    note("异常：" + traceback.format_exc()[-600:])

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("done")
