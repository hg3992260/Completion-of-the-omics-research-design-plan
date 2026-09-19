# -*- coding: utf-8 -*-
"""stdio 传输自检：以 DSH/Claude Desktop 完全相同的方式拉起 mcp_server.py 并调用。

注意：asyncio 在 Windows 上用命名管道做子进程 stdio，受沙箱限制会报 WinError 5，
需在放宽的文件/进程权限下运行。
"""
import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PY = r"D:\python\envs\mar\python.exe"
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_mcp_stdio.txt")
lines = []


async def main():
    params = StdioServerParameters(command=PY, args=[SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            lines.append(f"stdio 握手成功：server={init.serverInfo.name} "
                         f"v{init.serverInfo.version} protocol={init.protocolVersion}")
            tools = await s.list_tools()
            lines.append(f"工具数={len(tools.tools)}：" + ", ".join(t.name for t in tools.tools))
            r = await s.call_tool("list_stages", {})
            d = json.loads(r.content[0].text)
            lines.append(f"list_stages → {len(d)} 阶段（首个 {d[0]['title']} / {d[0]['spec']}）")
            r2 = await s.call_tool("llm_chat", {"prompt": "只回答：STDIO-OK", "max_tokens": 300})
            d2 = json.loads(r2.content[0].text)
            lines.append(f"llm_chat → {d2['model']} {d2['elapsed']}s "
                         f"{d2['content'].strip()[:30]!r}")
            lines.append("结论：stdio 传输可用（DSH/Claude Desktop 可直接注册）")


try:
    asyncio.run(main())
except Exception:                                                  # noqa: BLE001
    import traceback
    lines.append("失败：\n" + traceback.format_exc()[-900:])

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("done")
