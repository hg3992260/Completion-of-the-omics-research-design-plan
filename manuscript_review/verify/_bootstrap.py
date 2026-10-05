# -*- coding: utf-8 -*-
"""验证脚本的公共引导：把仓库根挂到 sys.path，并提供样例文件路径。

为什么要它：这些脚本原本放在仓库根的 `_mr_probe/` 下，靠
``os.path.dirname(os.path.dirname(__file__))`` 推算仓库根。搬进
``manuscript_review/verify/`` 后层数变了，导入就会失败。
这里改成**向上逐级找标记文件**，无论脚本在哪个子目录、无论从哪里执行都成立。

每个验证脚本开头只需：

    from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample

（同目录导入：脚本直接运行时其所在目录就在 sys.path[0]。）
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_root(start: str = HERE, marker: str = "design_studio.py") -> str:
    """向上找含 marker 的目录，即仓库根。找不到就退到两级以上。"""
    cur = os.path.abspath(start)
    for _ in range(8):
        if os.path.exists(os.path.join(cur, marker)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.dirname(os.path.dirname(HERE))


ROOT = find_root()
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 样例目录：manuscript_review/examples
EXAMPLES = os.path.join(os.path.dirname(HERE), "examples")


def sample_manuscript() -> str:
    """合成样例手稿（29 段，含 16 处硬伤，无任何真实患者数据）。"""
    return os.path.join(EXAMPLES, "sample_manuscript.docx")


def annotated_sample() -> str:
    """审稿批注版样例：3 条审稿意见，用于验证线程回复并入。"""
    return os.path.join(EXAMPLES, "annotated_sample.docx")


def out_dir() -> str:
    """验证脚本的临时产物目录（与源码同级的 _verify_out/，已被 .gitignore 忽略）。"""
    d = os.path.join(ROOT, "_verify_out")
    os.makedirs(d, exist_ok=True)
    return d


def ensure_examples() -> bool:
    """确认样例存在；缺失时提示如何生成。"""
    miss = [p for p in (sample_manuscript(), annotated_sample())
            if not os.path.exists(p)]
    if miss:
        sys.stderr.write(
            "[提示] 缺少样例文件：\n"
            + "".join(f"  - {p}\n" for p in miss)
            + "  生成方式：\n"
              "    python manuscript_review/examples/make_sample.py\n"
              "    python manuscript_review/examples/make_annotated.py\n")
        return False
    return True


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                              # noqa: BLE001
        pass
    print("ROOT     :", ROOT)
    print("EXAMPLES :", EXAMPLES)
    print("sample   :", sample_manuscript(), os.path.exists(sample_manuscript()))
    print("annotated:", annotated_sample(), os.path.exists(annotated_sample()))
    print("out_dir  :", out_dir())
