# -*- coding: utf-8 -*-
"""P2 自检：GUI 桥接链路（KernelBoot.start → run_task → driver.run_turn → MCP 工具）。

不弹 TUI（PCL_KERNEL_TUI=0），验证 design_studio.opencode_run_task 实际依赖的
整条链路：起内核 → 注册宿主 MCP(方向A) → 建 legacy session → 投递任务 →
opencode 调用宿主领域工具 → 收集事件。
"""
from __future__ import annotations
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["PCL_KERNEL_TUI"] = "0"          # 不弹终端（CI/无头）
os.environ["PCL_KERNEL_AUTOSTART"] = "1"

import kernel_boot as kb                                                 # noqa: E402
import kernel_config as kcfg                                             # noqa: E402
import kernel_client as kc                                               # noqa: E402

OK = WARN = FAIL = 0


def rec(step, status, detail=""):
    global OK, WARN, FAIL
    OK += status == "OK"; WARN += status == "WARN"; FAIL += status == "FAIL"
    print(f"  [{status}] {step}" + (f" — {detail}" if detail else ""))


def main() -> int:
    # 先清掉可能的遗留实例：其 MCP 端点可能已失效，会让方向 A 失败
    c0 = kc.KernelClient(directory=HERE)
    if c0.adopt_state():
        try:
            c0.stop()
            print("stopped orphan kernel")
        except Exception:                                               # noqa: BLE001
            pass

    print("== 复用/启动内核（无 TUI）==")
    boot = kb.instance()
    out = boot.start("bridge-test")
    rec("KernelBoot.start", "OK" if out.get("ok") else "FAIL",
        f"url={out.get('url')} mcp={out.get('mcp')} sid={out.get('sessionID')}")
    if not out.get("ok"):
        print("start 失败：", out.get("error"))
        return 1

    drv = boot.driver()
    rec("KernelBoot.driver()", "OK" if drv is not None else "FAIL")

    print("== 投递任务（opencode 调宿主 MCP 工具）==")
    tool_hits = []
    t0 = time.time()

    def on_ev(ev: dict):
        if ev.get("kind") == "tool":
            tool_hits.append(ev.get("text") or "")

    try:
        events = boot.run_task(
            "bridge-test",
            "请调用 project_sections 工具，然后只回复 stat 分节的个数（一个数字）。",
            on_event=on_ev)
    except Exception as e:                                              # noqa: BLE001
        events = None
        rec("run_task", "FAIL", f"{type(e).__name__}: {e}")

    if events is not None:
        done = [e for e in events if e.get("kind") == "done"]
        text = "".join(e.get("text", "") for e in events
                       if e.get("kind") in ("text", "text_full"))
        rec("完成事件", "OK" if done else "WARN",
            f"{time.time() - t0:.1f}s finish={(done[-1]['data'].get('finish') if done else None)}")
        rec("工具事件", "OK" if tool_hits else "WARN", str(tool_hits[:3]))
        hit = any("project_sections" in t for t in tool_hits)
        rec("opencode 调用了宿主工具", "OK" if hit else "WARN",
            f"正文={text.strip()[:40]!r}")

    print("== 收尾 ==")
    boot.stop()
    rec("KernelBoot.stop()", "OK")
    print(f"\nOK={OK}  WARN={WARN}  FAIL={FAIL}")
    print("结论：" + ("通过" if FAIL == 0 else "未通过"))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
