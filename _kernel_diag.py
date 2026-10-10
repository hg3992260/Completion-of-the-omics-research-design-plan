# -*- coding: utf-8 -*-
"""P0 诊断：为什么 run 没有正文、模型目录里有什么。只读探测，用完即弃。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import kernel_client as kc                                              # noqa: E402


def main() -> int:
    exe = kc.opencode_exe()
    print(f"exe = {exe}")

    # 1) 启动内核
    client = kc.KernelClient(exe=exe, verbose=False)
    state = client.ensure_running(timeout=120)
    print(f"kernel up: {state.url}  ready={client.ready_seconds:.2f}s")

    # 2) 完整模型目录
    got = client.request("GET", "/api/model")
    data = got.get("data") if isinstance(got, dict) else got
    ids = []
    for item in (data or []):
        if isinstance(item, dict):
            pid = item.get("providerID") or item.get("provider")
            mid = item.get("modelID") or item.get("id") or item.get("model")
            ids.append(f"{pid}/{mid}" if pid and mid else str(mid or pid))
    print(f"\n=== /api/model 共 {len(ids)} 个 ===")
    for i in sorted(ids):
        print("   ", i)

    print("\n=== 含 deepseek 的条目 ===")
    print("   ", [i for i in ids if "deepseek" in i.lower()] or "(无)")

    print("\n=== provider 列表 ===")
    try:
        prov = client.request("GET", "/api/provider")
        pdata = prov.get("data") if isinstance(prov, dict) else prov
        if isinstance(pdata, list):
            for p in pdata:
                if isinstance(p, dict):
                    print("   ", p.get("id") or p.get("providerID"), "|",
                          (p.get("name") or "")[:40])
        else:
            print("   ", json.dumps(prov, ensure_ascii=False)[:600])
    except Exception as e:                                             # noqa: BLE001
        print(f"    FAIL {type(e).__name__}: {e}")

    # 3) 用 CLI 列模型（catalog 视角）
    print("\n=== opencode models（前 30 行） ===")
    r = subprocess.run([exe, "models"], env=kc.kernel_env(state.password),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    print("\n".join((r.stdout or "").splitlines()[:30]))
    if r.stderr:
        print("stderr:", r.stderr[:400])

    # 4) 直接跑一次，打印原始事件（用 CLI 暴露的真实 model id）
    for model in ("deepseek/deepseek-flash", "deepseek/deepseek-v4-pro"):
        print(f"\n=== run --model {model} ===")
        cmd = [exe, "run", "--format", "json", "--attach", state.url,
               "--model", model, "只回答两个字：就绪"]
        try:
            r = subprocess.run(cmd, env=kc.kernel_env(state.password),
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=300)
            print(f"exit={r.returncode}")
            print("stdout:")
            for line in (r.stdout or "").splitlines()[:30]:
                print("   ", line[:500])
            if r.stderr:
                print("stderr:", r.stderr[:800])
        except Exception as e:                                         # noqa: BLE001
            print(f"   FAIL {type(e).__name__}: {e}")

    # 5) 内核自己的日志（generic 错误要看这里）
    print("\n=== 内核日志尾部 ===")
    logdir = os.path.join(kc.kernel_home(), "data", "opencode", "log")
    if os.path.isdir(logdir):
        files = sorted(
            (os.path.join(logdir, f) for f in os.listdir(logdir)),
            key=lambda p: os.path.getmtime(p), reverse=True)
        for path in files[:1]:
            print(f"--- {os.path.basename(path)} ---")
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
                for line in lines[-60:]:
                    print("   ", line.rstrip()[:400])
            except Exception as e:                                     # noqa: BLE001
                print(f"    读取失败 {type(e).__name__}: {e}")
    else:
        print(f"   日志目录不存在：{logdir}")

    client.stop()
    print("\nkernel stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
