# -*- coding: utf-8 -*-
"""演示同步：向正在运行的 PCLRadiomics 内核（隔离 home 可指定）的当前项目 session
投递一条任务 —— 与 GUI 的 opencode_run_task 完全同一路径（同一 session）。
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kernel_client as kc                                              # noqa: E402


def main() -> int:
    home = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "dist", "PCLRadiomics", "opencode")
    inst = json.load(open(os.path.join(home, "kernel_instance.json"), encoding="utf-8"))
    proj = json.load(open(os.path.join(home, "projects.json"), encoding="utf-8"))
    sid = next(iter(proj.values()))["sessionID"]
    st = kc.KernelState(inst["pid"], inst["port"], inst["password"],
                        version=inst.get("version", ""), home=home)
    client = kc.KernelClient(state=st, directory=home)
    print("session =", sid, "url =", st.url, flush=True)
    out = client.prompt_legacy(
        sid,
        "请调用 project_sections 工具，然后只回复 stat 分节的个数（一个数字）。",
        model="deepseek/deepseek-flash", timeout=180)
    text = "".join(p.get("text", "") for p in (out.get("parts") or [])
                   if isinstance(p, dict) and p.get("type") == "text")
    tools = [p.get("tool") for p in (out.get("parts") or [])
             if isinstance(p, dict) and p.get("type") == "tool"]
    print("answer =", repr(text), "tools =", tools, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
