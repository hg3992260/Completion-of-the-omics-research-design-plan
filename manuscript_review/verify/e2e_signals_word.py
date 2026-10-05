# -*- coding: utf-8 -*-
"""端到端验证：样例手稿 → 确定性核验 → Word 批注 + 四色修订 → 报告。"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample, out_dir
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from manuscript_review import mr_docx, mr_engine, mr_office, mr_report, mr_signals, mr_word

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sample_manuscript()
OUT = os.path.join(out_dir(), "sample_审阅修订版.docx")

print("=" * 70)
print("officecli:", json.dumps(mr_office.available(), ensure_ascii=False))
print("=" * 70)

eng = mr_engine.RevEngine()
proj = mr_engine.ReviewProject()

ok, msg, proj = eng.ingest(SRC, proj)
print("[ingest ]", ok, msg)
assert ok, msg

ok, msg, proj = eng.run_signals(proj)
print("[signals]", ok, msg)
print("           summary:", json.dumps(proj.signal_summary, ensure_ascii=False))

ms = eng._manuscript(proj)
plan = mr_word.build_plan(ms, mr_signals.__dict__ and proj.defects, mode="dual")
print("[plan   ]", mr_word.summarize_plan(plan))
print("           批注锚点:", [(c.para_idx, c.defect_key.split(':')[1][:22]) for c in plan.comments][:6], "…")
print("           修订:", [(r.kind, r.para_idx) for r in plan.revisions][:8], "…")

res = mr_word.apply_plan(SRC, OUT, plan)
print("[apply  ]", res.ok, res.error or "ok")
print("           批注", res.comments_added, "| 修订", res.revisions_added)
print("           校验:", json.dumps(res.verify, ensure_ascii=False))

ok, msg, proj = eng.build_report(proj)
print("[report ]", ok, msg)

print()
print("=== 输出文件 ===")
for p in (OUT, proj.report_path):
    print(f"  {p}  {os.path.getsize(p) if os.path.exists(p) else 'MISSING'} bytes")

# 结构复核
print()
print("=== 复核修订稿 XML ===")
import re
import zipfile
z = zipfile.ZipFile(OUT)
doc = z.read("word/document.xml").decode("utf-8")
print("  commentRangeStart", len(re.findall(r"<w:commentRangeStart\b", doc)))
print("  commentRangeEnd  ", len(re.findall(r"<w:commentRangeEnd\b", doc)))
print("  commentReference ", len(re.findall(r"<w:commentReference\b", doc)))
print("  w:ins            ", len(re.findall(r"<w:ins\b", doc)))
print("  w:del            ", len(re.findall(r"<w:del\b", doc)))
for c in ("00B050", "FF0000", "0070C0", "ED7D31"):
    print(f"  color {c}      ", len(re.findall(r'w:color w:val="' + c + r'"', doc)))
print("  comments.xml     ", len(re.findall(r"<w:comment\b", z.read("word/comments.xml").decode("utf-8")))
      if "word/comments.xml" in z.namelist() else "无")

print()
print("=== 批注内容抽样 ===")
for cm in mr_office.comments(OUT)[:2]:
    print("-" * 60)
    print(cm.get("text", "")[:500])
