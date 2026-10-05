# -*- coding: utf-8 -*-
"""验证自主落盘：跑一次 run_all 就自动把批注写进 Word（不需要人工点落盘）。"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from manuscript_review import mr_docx, mr_engine, mr_thread

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sample_manuscript()
ANN = annotated_sample()


def run(label, name, **kw):
    print("=" * 72)
    print(f"{label}")
    print("=" * 72)
    # 关键：先清掉同名项目 JSON。否则上一次的 applied_keys（去重指纹）
    # 会被读回来，导致「已入稿」判定命中、看起来像没写入。
    pj = mr_engine.ReviewProject(name=name).path()
    if os.path.exists(pj):
        os.remove(pj)
    eng = mr_engine.RevEngine(None)
    steps = []
    ok, msg, p = eng.run_all(SRC, skip_llm=True,
                             on_step=lambda s, m: steps.append((s, m[:70])), **kw)
    for s, m in steps:
        print(f"  [{s:8s}] {m}")
    ap = p.applied or {}
    th = ap.get("threading") or {}
    print(f"  → 项目: {p.name}")
    print(f"  → 落盘: 独立批注 {ap.get('comments_added', 0)}"
          f" + 线程回复 {ap.get('replies_added', 0)}"
          f" · 正文修订 {ap.get('revisions_added', 0)} 处")
    print(f"  → 已入稿指纹: {len(p.applied_keys)} 条 | 落盘时间 {p.applied_at or '—'}")
    print(f"  → 输出: {p.out_docx or '（未写 Word）'}")
    if th:
        print(f"  → 线程校验: ok={th.get('ok')} 嵌套正常={th.get('nested_ok')} "
              f"异常={th.get('nested_bad')}")
    if p.out_docx and os.path.exists(p.out_docx):
        ms = mr_docx.load(p.out_docx)
        print(f"  → 输出段落数: {len(ms.paragraphs)}")
    print()
    return p


# ① 默认（auto → revise）：批注 + 补写段
p1 = run("① autonomy=auto（默认，等同 revise）→ 批注 + Track Changes 补写",
         "auto_test", autonomy="auto")

# ② 只挂批注，不动正文
p2 = run("② autonomy=comment → 只挂批注，不增删正文",
         "comment_test", autonomy="comment")

# ③ 只出报告
p3 = run("③ autonomy=report → 只出报告，不碰 Word",
         "report_test", autonomy="report")

# ④ 并入审稿批注版（线程回复）
p4 = run("④ autonomy=revise + merge_into（线程回复并入审稿批注版）",
         "merge_test", autonomy="revise", merge_into=ANN)

# ⑤ 增量：同一份稿件再跑一次，应识别为「无新增发现」
print("=" * 72)
print("⑤ 增量落盘：对①的项目再跑一次 review_to_word")
print("=" * 72)
eng = mr_engine.RevEngine(None)
again = mr_engine.ReviewProject.load(p1.path())
ok, msg, again = eng.review_to_word(again)
print(f"  ok={ok} msg={msg}")
print(f"  applied_keys={len(again.applied_keys)}")
print(f"  输出文件未被重复写入: {not msg.startswith('已生成')}")
print()
print("=" * 72)
print("汇总")
print("=" * 72)
for lbl, p in (("auto", p1), ("comment", p2), ("report", p3), ("merge", p4)):
    ap = p.applied or {}
    print(f"  {lbl:8s} 批注 {ap.get('comments_added', 0):3d}"
          f" + 回复 {ap.get('replies_added', 0):3d}"
          f" + 修订 {ap.get('revisions_added', 0):3d}"
          f" | out={'有' if p.out_docx else '无'}")
