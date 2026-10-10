# -*- coding: utf-8 -*-
"""单测：macOS/Linux 的 ps 解析（_list_processes_posix）——注入伪造 ps 输出。"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kernel_client as kc                                              # noqa: E402

FAKE = (
    "  100 /usr/local/bin/opencode /usr/local/bin/opencode serve --hostname 127.0.0.1\n"
    "  200 /Applications/PCL.app/Contents/Resources/opencode/opencode "
    "/Applications/PCL.app/Contents/Resources/opencode/opencode attach "
    "http://127.0.0.1:4096 --dir /x --session ses_abc\n"
    "  300 /usr/bin/other /usr/bin/other --foo\n"
)


class _R:
    stdout = FAKE


def _fake_run(*a, **k):
    return _R()


orig = kc.subprocess.run
kc.subprocess.run = _fake_run
try:
    procs = kc._list_processes_posix("opencode")
finally:
    kc.subprocess.run = orig

print("parsed:", procs)
ok = (len(procs) == 2
      and procs[0]["pid"] == 100 and "serve" in procs[0]["cmd"]
      and procs[1]["pid"] == 200 and "attach" in procs[1]["cmd"])
print("结论：" + ("通过" if ok else "未通过"))
sys.exit(0 if ok else 1)
