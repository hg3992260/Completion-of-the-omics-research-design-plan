# -*- coding: utf-8 -*-
"""冻结版 stdio 自检：以 MCP 客户端身份拉起 PCLRadiomics服务.exe mcp，走完整协议。

需要放宽权限：Windows 下 asyncio 用命名管道做子进程 stdio，受限沙箱会报 WinError 5。
"""
import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.abspath(__file__))
SRV = os.path.join(ROOT, "dist", "PCLRadiomics", "PCLRadiomics.exe")
SRV_DIR = os.path.dirname(SRV)
OUT = os.path.join(ROOT, "_frozen_stdio.txt")
lines = []


async def main():
    params = StdioServerParameters(command=SRV, args=["mcp"], cwd=SRV_DIR)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            lines.append(f"stdio 握手成功：server={init.serverInfo.name} "
                         f"v{init.serverInfo.version} protocol={init.protocolVersion}")
            tools = await s.list_tools()
            lines.append(f"工具数={len(tools.tools)}：" + ", ".join(t.name for t in tools.tools))

            r = await s.call_tool("list_stages", {})
            d = json.loads(r.content[0].text)
            lines.append(f"list_stages → {len(d)} 阶段（{d[0]['title']} / {d[0]['spec']}）")

            r = await s.call_tool("list_projects", {})
            d = json.loads(r.content[0].text)
            lines.append(f"list_projects → {len(d)} 个项目：{[m['name'] for m in d]}")

            r = await s.call_tool("project_overview", {"project": "未命名课题"})
            d = json.loads(r.content[0].text)
            lines.append("project_overview → " + (d.get("error") or
                         f"「{d['project']}」{d['summary']}"))

            r = await s.call_tool("llm_chat", {"prompt": "只回答：FROZEN-STDIO-OK",
                                               "max_tokens": 400})
            d = json.loads(r.content[0].text)
            lines.append(f"llm_chat → {d['model']} {d['elapsed']}s "
                         f"{d['content'].strip()[:32]!r}")
            lines.append("结论：冻结后的 exe 完整保留了 MCP 服务模式（stdio）")


try:
    asyncio.run(main())
except Exception:                                                  # noqa: BLE001
    import traceback
    lines.append("失败：\n" + traceback.format_exc()[-800:])

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("done")
