# -*- coding: utf-8 -*-
"""扫一遍：哪些模块用了 PEP 585/604 注解（list[x] / X | None）却没有 `from __future__ import annotations`。

Python 3.8 上这种注解会在**导入时**求值并直接抛 TypeError（'type' object is not subscriptable），
而 py_compile 只查语法、查不出来 —— 所以在 3.8 上必须真 import 一次。

    python _check_py38_annotations.py
"""

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r"(?:->\s*|:\s*)(?:list|dict|tuple|set|frozenset|type)\[|[A-Za-z_\]\)]\s*\|\s*None")
FILES = ["web_server.py", "design_agent.py", "coupling.py", "scope_core.py",
         "stages_data.py", "shape_data.py", "stat_data.py", "llm_client.py",
         "app_paths.py", "docx_export.py", "api_server.py", "mcp_server.py", "cli.py"]


def main() -> int:
    bad = []
    for name in FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        src = io.open(path, encoding="utf-8").read()
        future = "from __future__ import annotations" in src
        hits = []
        for i, line in enumerate(src.splitlines(), 1):
            s = line.split("#")[0]
            if PAT.search(s):
                hits.append((i, line.strip()[:80]))
        flag = "OK " if (future or not hits) else "!! "
        print("%s%-18s future=%-5s 注解命中=%d" % (flag, name, future, len(hits)))
        if hits and not future:
            bad.append(name)
            for i, line in hits[:5]:
                print("      L%-4d %s" % (i, line))
    print("")
    if bad:
        print("需要加 `from __future__ import annotations`（或改成 typing 写法）：" + "、".join(bad))
    else:
        print("全部模块都能在 Python 3.8 上正常导入")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
