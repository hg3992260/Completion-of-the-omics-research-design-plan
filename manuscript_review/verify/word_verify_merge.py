# -*- coding: utf-8 -*-
"""Word COM 权威确认：合并稿里的回复是否真的线程嵌套在审稿意见下。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "merged_review.docx")
ANN = annotated_sample()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import win32com.client as win32

word = win32.gencache.EnsureDispatch("Word.Application")
word.Visible = False
try:
    for label, path in (("原审稿批注版", ANN), ("并入我们的发现后", OUT)):
        print("=" * 70)
        print(f"{label}：{os.path.basename(path)}")
        print("=" * 70)
        doc = word.Documents.Open(os.path.abspath(path), ReadOnly=True)
        try:
            cs = doc.Comments
            print(f"  Word 批注总数: {cs.Count}")
            threaded = 0
            for i in range(1, cs.Count + 1):
                c = cs.Item(i)
                try:
                    anc = c.Ancestor
                except Exception:                               # noqa: BLE001
                    anc = None
                if anc is not None:
                    threaded += 1
                    if threaded <= 6:
                        print(f"    ✓ #{i} 作者={c.Author!r}")
                        print(f"        父级 → 作者={anc.Author!r} "
                              f"文本={anc.Range.Text[:34]!r}")
            print(f"  → Word 认为有线程父级的批注数: {threaded}")
            # 按作者统计
            from collections import Counter
            cnt = Counter()
            for i in range(1, cs.Count + 1):
                cnt[cs.Item(i).Author] += 1
            print(f"  → 作者分布: {dict(cnt)}")
        finally:
            doc.Close(False)
        print()
finally:
    word.Quit()
