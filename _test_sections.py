# -*- coding: utf-8 -*-
"""P3 自检：新增的通用分节工具（project_sections/get_section/set_section）。"""
from __future__ import annotations
import json
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import design_agent                                                     # noqa: E402

design_agent.PROJECT_DIR = tempfile.mkdtemp(prefix="pcl_sec_")         # 不污染真实库
import mcp_server                                                      # noqa: E402


def main() -> int:
    design_agent.Project.new("section-test", "x")
    n = mcp_server.tool_count()
    print("tool_count =", n)

    sections = json.loads(mcp_server.project_sections())
    print("sections keys:", list(sections.keys()),
          "stat 首节:", sections["stat"][0] if sections.get("stat") else None)

    key = sections["stat"][0]["key"]
    r = mcp_server.project_set_section("section-test", "stat", key,
                                       json.dumps({"checks": {"probe": True}, "notes": "hi"}))
    print("set:", r)
    g = json.loads(mcp_server.project_get_section("section-test", "stat", key))
    print("get:", json.dumps(g, ensure_ascii=False))
    ok = g.get(key, {}).get("checks", {}).get("probe") is True

    bad = json.loads(mcp_server.project_set_section("section-test", "nope", key, "{}"))
    ok = ok and "error" in bad
    print("结论：" + ("通过" if ok else "未通过"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
