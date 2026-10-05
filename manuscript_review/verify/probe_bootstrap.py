# -*- coding: utf-8 -*-
"""验证「没有任何带 PySide6 的解释器」时的提示是否可读。

做法：把 design_studio.py 复制一份，把解释器候选清单清空并去掉 PATH 兜底，
再用 base 解释器（无 PySide6）执行，观察输出。
"""
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "design_studio.py")
TMP = os.path.join(ROOT, "_mr_probe", "_bootstrap_probe.py")

src = open(SRC, encoding="utf-8").read()

# 1) 清空候选清单（用括号配对扫描，避免正则被 os.path.join(...) 里的嵌套括号搞坏）
start = src.index("_PY_CANDIDATES = (")
i = src.index("(", start)
depth = 0
for k in range(i, len(src)):
    if src[k] == "(":
        depth += 1
    elif src[k] == ")":
        depth -= 1
        if depth == 0:
            end = k + 1
            break
else:
    raise RuntimeError("未能定位 _PY_CANDIDATES 的结尾")
src2 = src[:start] + "_PY_CANDIDATES = ()" + src[end:]

# 2) PATH 兜底也要屏蔽（否则会找到别的 python）
src2 = src2.replace(
    'for name in ("python3", "py"):',
    'for name in ():  # 探针：屏蔽 PATH 兜底')

# 3) 只保留到自举调用为止，后面需要 PySide6 的部分不执行
CALL = "\n_bootstrap_interpreter()"
cut = src2.index(CALL) + len(CALL)
head = src2[:cut]
head += "\nprint('（探针到此结束：未发生 execve）')\n"

with open(TMP, "w", encoding="utf-8") as fh:
    fh.write(head)

env = dict(os.environ)
env.pop("PCLRADIOMICS_RELAUNCHED", None)
base = r"C:\Users\chris\miniconda3\python.exe"
print("用 base 解释器执行探针:", base)
print("-" * 62)
r = subprocess.run([base, TMP], capture_output=True, text=True, encoding="utf-8",
                   errors="replace", env=env, timeout=90)
print("退出码:", r.returncode)
print("--- stdout ---")
print(r.stdout)
print("--- stderr ---")
print(r.stderr)
os.remove(TMP)
