# -*- coding: utf-8 -*-
"""把 .bat 转成 CRLF（Windows 批处理对换行敏感；仓库里的新 .bat 统一 CRLF）。

    python _to_crlf.py 启动_Web版.bat [更多文件...]
"""

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def convert(path: str) -> str:
    with io.open(path, "rb") as fh:
        raw = fh.read()
    fixed = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if fixed != raw:
        with io.open(path, "wb") as fh:
            fh.write(fixed)
        return "已转换为 CRLF"
    return "本来就是 CRLF"


if __name__ == "__main__":
    targets = sys.argv[1:] or ["启动_Web版.bat"]
    for name in targets:
        p = name if os.path.isabs(name) else os.path.join(HERE, name)
        if not os.path.exists(p):
            print("跳过（不存在）：%s" % name)
            continue
        print("%-24s %s" % (name, convert(p)))
