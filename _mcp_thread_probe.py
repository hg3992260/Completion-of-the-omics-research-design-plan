# -*- coding: utf-8 -*-
"""探针：FastMCP 的 streamable-http 能否在 GUI 进程的后台线程里跑起来。

这一步决定方向 A 的实现方式（D10）：
    能           → 同一个进程内起后台线程（字面满足"GUI 进程同时暴露 MCP 端点"）
    不能（信号处理器限制）→ 退化为子进程 `PCLRadiomics.exe mcp --transport streamable-http`

只读探测：只起一个线程 + 一个 HTTP 请求，不改任何文件。
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    print("=== 导入 mcp_server（会构造 FastMCP 实例）===")
    try:
        import mcp_server
    except Exception as e:                                             # noqa: BLE001
        print(f"FAIL 导入失败: {type(e).__name__}: {e}")
        return 1
    print("  OK, mcp =", mcp_server.mcp.name)
    tools = getattr(mcp_server, "mcp", None)
    print("  后台线程？", threading.current_thread() is threading.main_thread())

    port = free_port()
    print(f"\n=== 在后台线程里 serve streamable-http :{port} ===")
    errors: list[BaseException] = []

    def run_server():
        try:
            mcp_server.mcp.settings.host = "127.0.0.1"
            mcp_server.mcp.settings.port = port
            mcp_server.mcp.run(transport="streamable-http")
        except BaseException as e:                                     # noqa: BLE001
            errors.append(e)

    t = threading.Thread(target=run_server, name="mcp-http-probe", daemon=True)
    t.start()

    # 轮询直到端口可连或线程死亡
    url = f"http://127.0.0.1:{port}/mcp"
    ok = False
    deadline = time.time() + 25
    while time.time() < deadline:
        if errors:
            break
        if not t.is_alive():
            break
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                ok = True
                break
        except OSError:
            time.sleep(0.3)

    print(f"  线程存活: {t.is_alive()}")
    print(f"  端口可连: {ok}")
    if errors:
        print(f"  异常: {type(errors[0]).__name__}: {errors[0]}")
        print("  → 结论：不能在后台线程跑，方向 A 改用子进程")
        return 2

    if not ok:
        print("  → 结论：线程活着但端口未就绪（超时）")
        return 3

    # 真的发一个 MCP initialize 请求，确认协议层可用
    print("\n=== 发一个 MCP initialize 请求 ===")
    body = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18",
                   "capabilities": {},
                   "clientInfo": {"name": "p0-probe", "version": "0"}},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8", "replace")
        print(f"  HTTP {res.status}")
        print(f"  响应前 300 字：{raw[:300]}")
        print("\n  → 结论：**可以在后台线程跑**，方向 A 可在 GUI 进程内实现（满足 D10）")
        return 0
    except Exception as e:                                             # noqa: BLE001
        print(f"  FAIL {type(e).__name__}: {e}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
