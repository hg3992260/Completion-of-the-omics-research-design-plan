# -*- coding: utf-8 -*-
"""验证两条尚未跑到的分支：① find/replace 修订 + 红蓝补色；② PDF → DOCX 转换。"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample
import os
import re
import sys
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from manuscript_review import mr_docx, mr_word

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sample_manuscript()
OUT = os.path.join(HERE, "probe_replace.docx")

ms = mr_docx.load(SRC)

# 人工构造两个"明确写错"的缺陷，专门触发 find/replace 分支
WRONG = "扫描参数未作统一规定，由各台设备按常规设置执行。"
EXTRA = "结论：增强CT影像组学模型可有效预测微血管侵犯，具有重要的临床应用价值。"
defects = [
    {"source": "llm", "layer": "omics", "req_id": "test:acq", "ref": "组学阶段 4",
     "spec": "CLEAR 16 · METRICS #6", "severity": "关键", "verdict": "wrong",
     "title": "扫描参数缺失", "why": "只写增强CT不给参数",
     "evidence": WRONG, "quote": WRONG,
     "suggestion": "管电压 120 kVp，自动管电流，层厚 1.0 mm，重建卷积核为标准软组织核。",
     "para_idx": 13, "chapter": "methods", "anchors": ["methods"], "signal": ""},
    {"source": "llm", "layer": "shape", "req_id": "test:conc", "ref": "写作章节 7",
     "spec": "Unit 5", "severity": "主要", "verdict": "wrong",
     "title": "结论过度断言", "why": "声称有效预测超出单中心回顾性证据强度",
     "evidence": EXTRA, "quote": EXTRA,
     "suggestion": "结论：基于增强CT门静脉期影像组学的模型**可能**有助于术前评估MVI，"
                   "其临床效用需多中心前瞻性验证。",
     "para_idx": 27, "chapter": "conclusion", "anchors": ["conclusion"], "signal": ""},
]

# 校验 find 片段唯一性
for d in defects:
    hits = sum(1 for p in ms.paragraphs if d["quote"] in p.text)
    print(f"quote 唯一性 ({d['req_id']}): 命中 {hits} 段")

plan = mr_word.build_plan(ms, defects, mode="dual")
print("plan:", mr_word.summarize_plan(plan))
print("替换:", [(r.kind, r.para_idx, r.find[:20]) for r in plan.revisions])

res = mr_word.apply_plan(SRC, OUT, plan)
print("apply:", res.ok, res.error or "ok")
print("verify:", res.verify)

print()
print("=== XML 复核（应出现红 del + 蓝 ins）===")
doc = zipfile.ZipFile(OUT).read("word/document.xml").decode("utf-8")
for tag in ("commentRangeStart", "commentRangeEnd", "commentReference", "w:ins", "w:del"):
    print(f"  {tag:20s}", len(re.findall(r"<" + tag + r"\b", doc)))
for c in ("00B050", "FF0000", "0070C0", "ED7D31"):
    print(f"  color {c}         ", len(re.findall(r'w:color w:val="' + c + r'"', doc)))

# 找出 del / ins 的实际结构，确认红蓝落在正确位置
for m in re.finditer(r"<w:(del|ins)\b[^>]*>(.{0,260}?)</w:\1>", doc, re.S):
    kind, inner = m.group(1), m.group(2)
    if "FF0000" in inner or "0070C0" in inner:
        print(f"  {kind}: {inner[:200]}")
