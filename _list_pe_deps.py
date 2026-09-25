# -*- coding: utf-8 -*-
"""列出若干 PE 文件的**全部**导入 DLL（用来定位冻结后缺哪个运行库）。

PyInstaller 只收集它"看得懂"的依赖；conda 版 Python 把 OpenSSL / libxml2 放在
`Library\\bin`，经常漏收，症状是冻结后 `ImportError: DLL load failed while importing _ssl`
或 `lxml` 起不来。这个脚本用来把真正的依赖列出来，好写进 spec。

    python _list_pe_deps.py dist-web\\PCLRadiomicsWeb\\_internal\\_ssl.pyd
    python _list_pe_deps.py D:\\python\\envs\\seq\\Library\\bin\\libxml2.dll -r
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from _check_win_target import pe_imports        # noqa: E402

SKIP = ("api-ms-win-", "ext-ms-win-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-r", "--real", action="store_true", help="只看非 API set 的真实 DLL")
    args = ap.parse_args()
    for path in args.files:
        if not os.path.exists(path):
            print("%s  → 不存在" % path)
            continue
        names = pe_imports(path)
        real = [n for n in names if not n.lower().startswith(SKIP)]
        print("%s\n  共 %d 个导入，其中非 API set %d 个：" % (path, len(names), len(real)))
        for n in (real if args.real else names):
            print("      " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
