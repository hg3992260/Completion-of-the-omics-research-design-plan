# -*- coding: utf-8 -*-
"""P3 自检：随包 agent/skill 是否被 opencode 内核识别。"""
from __future__ import annotations
import json, os, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kernel_client as kc          # noqa: E402
import kernel_config as kcfg        # noqa: E402


def main() -> int:
    kcfg.install_builtin_assets()
    client = kc.KernelClient(directory=HERE)
    adopted = client.adopt_state() is not None
    client.ensure_running(timeout=120)
    print("kernel", client.state.url)

    ok = True
    for path, label in (("/api/agent", "agent"), ("/api/skill", "skill")):
        try:
            got = client.request("GET", path, timeout=30)
            data = got.get("data") if isinstance(got, dict) else got
            names = []
            for d in (data or []):
                if isinstance(d, dict):
                    names.append(d.get("name") or d.get("id"))
            hit = "omics-design" in names
            print(f"{path}: {len(names)}  items; omics-design={'YES' if hit else 'NO'}")
            if not hit:
                print("   sample:", names[:12])
                ok = False
        except Exception as e:                                         # noqa: BLE001
            print(path, "ERR", type(e).__name__, e)
            ok = False

    if not adopted:
        client.stop()
    print("结论：" + ("通过" if ok else "未通过"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
