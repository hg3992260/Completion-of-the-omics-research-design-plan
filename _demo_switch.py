# -*- coding: utf-8 -*-
"""演示：用 KernelBoot 驱动**正在运行的冻结产物**做「切课题 / 改名」。

GUI 的 _switch_project / _rename_current 调用的就是这些方法；因无法用鼠标点击，
这里用同源代码直接调用，并让终端 TUI 重挂到目标 session。
用法： _demo_switch.py switch <课题名>
       _demo_switch.py rename <旧名> <新名>
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist", "PCLRadiomics")

import app_paths                                                        # noqa: E402
app_paths.app_home = lambda: DIST           # 让 kernel_home = DIST\opencode

sys.path.insert(0, HERE)
import kernel_client as kc                                              # noqa: E402
import kernel_boot as kb                                                # noqa: E402


def main() -> int:
    exe = os.path.join(DIST, "opencode", "opencode.exe")
    client = kc.KernelClient(exe=exe)
    if not client.adopt_state():
        print("未发现运行中的冻结内核")
        return 2
    boot = kb.KernelBoot(exe=exe)
    boot._client = client
    boot._kboot_ready = True
    boot._project = "未命名课题"

    cmd = sys.argv[1] if len(sys.argv) > 1 else "switch"
    if cmd == "switch":
        r = boot.switch_project(sys.argv[2])
    elif cmd == "rename":
        r = boot.rename_project(sys.argv[2], sys.argv[3])
    elif cmd == "select":
        got = client.create_session(title="切会话测试")
        sid = got.get("id")
        r = client.tui_select_session(sid)
        print("select result =", r, " new session =", sid)
    elif cmd == "toast":
        r = client.tui_show_toast(sys.argv[2] if len(sys.argv) > 2 else "已切换课题：演示")
        print("toast result =", r)
    else:
        print("unknown cmd")
        return 2
    print("result =", r)

    pm = os.path.join(DIST, "opencode", "projects.json")
    if os.path.exists(pm):
        print("projects.json =", open(pm, encoding="utf-8").read())
    sid = r.get("sessionID") if isinstance(r, dict) else None
    if sid:
        try:
            info = client.session_get(sid)
            d = info.get("data") if isinstance(info, dict) else info
            print("session title =", (d or {}).get("title"))
        except Exception as e:                                         # noqa: BLE001
            print("session_get err", type(e).__name__, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
