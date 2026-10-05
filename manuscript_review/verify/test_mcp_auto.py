# -*- coding: utf-8 -*-
"""MCP 自主落盘验证：并入线程 + 三档 autonomy。"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import mcp_server as M

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sample_manuscript()
ANN = annotated_sample()

print("=" * 70)
print("① MCP 一次调用：审阅 + 并入审稿批注版（线程回复）")
print("=" * 70)
r = json.loads(M.manuscript_review(SRC, skip_llm=True, autonomy="revise",
                                   merge_into=ANN))
print("  steps      :", [s["step"] for s in r["steps"]])
print("  独立批注   :", r["comments_added"])
print("  线程回复   :", r["replies_added"])
print("  正文修订   :", r["revisions_added"])
mp = r.get("merge_plan") or {}
print("  匹配计划   :", mp.get("replies_count"), "条回复 → 父批注",
      mp.get("parents_used"), "| 独立", mp.get("standalone"))
print("  线程校验   :", json.dumps(r.get("threading"), ensure_ascii=False))
print("  out_docx   :", r["out_docx"])

print()
print("=" * 70)
print("② MCP 三档 autonomy")
print("=" * 70)
for a in ("report", "comment", "revise"):
    r = json.loads(M.manuscript_review(SRC, skip_llm=True, autonomy=a))
    out = "有" if r["out_docx"] else "无"
    print(f"  {a:8s} 批注 {r['comments_added']} + 回复 {r['replies_added']}"
          f" + 修订 {r['revisions_added']} | out={out}")

print()
print("=" * 70)
print("③ MCP 增量模式（incremental=True）：第二次应无新增")
print("=" * 70)
r = json.loads(M.manuscript_review(SRC, skip_llm=True, autonomy="revise",
                                   incremental=True))
steps = {s["step"]: s["msg"] for s in r["steps"]}
print("  apply 步骤:", steps.get("apply", "")[:110])
print("  已入稿指纹:", r["applied_keys"])
