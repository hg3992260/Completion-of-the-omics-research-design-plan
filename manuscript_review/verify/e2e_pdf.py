# -*- coding: utf-8 -*-
"""验证 PDF → DOCX 转换分支，并跑通「PDF 导入 → 审阅 → 落盘」全链路。"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample, out_dir
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from manuscript_review import mr_docx, mr_engine, mr_pdf, mr_word

HERE = os.path.dirname(os.path.abspath(__file__))
# 样例 PDF **不入库**（体积大且可由 DOCX 现场导出），所以这里按需生成：
# 优先用 examples/ 下已有的；没有就用 Word COM 从样例 DOCX 导出一份到 out_dir()。
PDF = os.path.join(EXAMPLES, "sample_manuscript.pdf")
OUT = os.path.join(out_dir(), "pdf_审阅修订版.docx")


def ensure_pdf() -> str:
    """确保有一份可用于测试的 PDF；返回其路径（失败返回原路径，由调用方报错）。"""
    if os.path.exists(PDF):
        return PDF
    target = os.path.join(out_dir(), "sample_manuscript.pdf")
    if os.path.exists(target):
        return target
    try:
        import win32com.client as win32                       # 需要 Word + pywin32
        word = win32.gencache.EnsureDispatch("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(sample_manuscript(), ReadOnly=True)
            doc.SaveAs2(target, FileFormat=17)                # 17 = wdFormatPDF
            doc.Close(False)
        finally:
            word.Quit()
        print(f"[准备] 已用 Word 导出样例 PDF → {os.path.basename(target)}")
        return target
    except Exception as e:                                     # noqa: BLE001
        print(f"[跳过] 无法生成样例 PDF（{type(e).__name__}: {e}）")
        print("       请先把一份 PDF 放到 manuscript_review/examples/sample_manuscript.pdf")
        return PDF


PDF = ensure_pdf()

print("依赖:", json.dumps(mr_pdf.available(), ensure_ascii=False))
print()

# --- 直接测转换
r = mr_pdf.to_docx(PDF, out_path=os.path.join(out_dir(), "pdf_转换稿.docx"))
print("转换:", json.dumps({k: v for k, v in r.to_dict().items()
                          if k not in ("warnings",)}, ensure_ascii=False))
for w in r.warnings:
    print("   ⚠", w)
assert r.ok, r.error

# --- 转换稿的结构识别
ms = mr_docx.load(r.docx_path)
print()
print(f"转换稿：{len(ms.paragraphs)} 段 / {ms.word_count} 字 / 标题「{ms.title[:40]}」")
for o in ms.outline():
    print(f"   {o['name']:8s} 段{o['start']:4d} · {o['paragraphs']:3d} 段 · {o['chars']:5d} 字")
for w in ms.warnings:
    print("   ⚠", w)

# --- 用转换稿跑完整流程（信号 → 落盘）
print()
eng = mr_engine.RevEngine()
proj = mr_engine.ReviewProject()
ok, msg, proj = eng.ingest(PDF, proj)
print("[ingest ]", ok, msg)
ok, msg, proj = eng.run_signals(proj)
print("[signals]", ok, msg)
m = eng._manuscript(proj)
plan = mr_word.build_plan(m, proj.defects, mode="dual")
print("[plan   ]", mr_word.summarize_plan(plan))
res = mr_word.apply_plan(proj.docx_path, OUT, plan)
print("[apply  ]", res.ok, (res.error or "")[:200])
print("           verify:", json.dumps(res.verify, ensure_ascii=False))
ok, msg, proj = eng.build_report(proj)
print("[report ]", ok, os.path.basename(proj.report_path))
print()
print("输出:", OUT, os.path.getsize(OUT) if os.path.exists(OUT) else "MISSING", "bytes")
