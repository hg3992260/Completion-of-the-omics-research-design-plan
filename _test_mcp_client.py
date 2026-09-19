# -*- coding: utf-8 -*-
"""用真实 MCP 客户端（streamable-http）连本机 mcp_server.py：initialize → tools/list → tools/call。"""
import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://127.0.0.1:8765/mcp"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_mcp_test.txt")
lines = []


async def main():
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            lines.append(f"握手成功：server={init.serverInfo.name} "
                         f"v{init.serverInfo.version} protocol={init.protocolVersion}")
            tools = await s.list_tools()
            lines.append(f"工具数={len(tools.tools)}：" + ", ".join(t.name for t in tools.tools))

            r1 = await s.call_tool("list_stages", {})
            d1 = json.loads(r1.content[0].text)
            lines.append(f"list_stages → {len(d1)} 阶段；首个={d1[0]['id']} {d1[0]['title']} "
                         f"（{d1[0]['spec']}，{len(d1[0]['actions'])} 个必做动作）")

            r2 = await s.call_tool("project_overview", {"project": "未命名课题"})
            d2 = json.loads(r2.content[0].text)
            if "error" in d2:
                lines.append(f"project_overview → {d2['error']}")
            else:
                lines.append(f"project_overview → 「{d2['project']}」汇总={d2['summary']} "
                             f"行数={len(d2['rows'])}")
                for row in d2["rows"][:3]:
                    lines.append(f"    {row['id']} {row['stage']} | {row['status']} | "
                                 f"{row['result'][:24]}")

            r3 = await s.call_tool("llm_chat", {"prompt": "只回答三个字母：OK", "max_tokens": 300})
            d3 = json.loads(r3.content[0].text)
            lines.append(f"llm_chat → 模型={d3['model']} {d3['elapsed']}s "
                         f"回复={d3['content'].strip()[:40]!r}")

            r4 = await s.call_tool("llm_models", {})
            d4 = json.loads(r4.content[0].text)
            lines.append(f"llm_models → 当前={d4['current']} 可用={d4['models']}")


try:
    asyncio.run(main())
    lines.append("结论：MCP 协议全链路（握手 / 工具发现 / 工具调用 / LLM 透传）可用")
except Exception as e:                                             # noqa: BLE001
    import traceback
    lines.append("失败：" + traceback.format_exc()[-700:])

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("done")
