# -*- coding: utf-8 -*-
"""调试：打印指定页的块分类明细。用法: python inspect_page.py 46 117 286"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
recs = [json.loads(l) for l in io.open(os.path.join(HERE, "blocks.jsonl"), encoding="utf-8")]
for pg in [int(a) for a in sys.argv[1:]]:
    print("=" * 30, "PDF page", pg)
    for r in recs:
        if r["pdf_page"] != pg:
            continue
        txt = r["text"][:92]
        print("  %-18s y=%6.1f up=%.2f tbl=%d it=%.2f | %s"
              % (r["kind"], r["y0"], r["upper"], int(r["in_table"]),
                 r["italic_ratio"], txt))
