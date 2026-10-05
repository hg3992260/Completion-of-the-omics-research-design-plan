# -*- coding: utf-8 -*-
"""验证：① 导入自动登记为课题附件 ② 课题背景带入审阅 ③ 切换课题时的提示。"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from design_agent import Project
from manuscript_review import mr_engine, mr_reviewer

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sample_manuscript()

# ---- 造一个有内容的课题，验证背景快照
name = "关联验证课题"
pj = Project.unique_path(name)
if os.path.exists(pj):
    os.remove(pj)
design = Project.new(name, raw="回顾性收集 2015-2023 年单中心 PCL 患者，"
                               "术前门静脉期增强 CT，PyRadiomics 提取特征，"
                               "LASSO 建模，并在外院做外部验证；"
                               "前瞻队列留取囊液做蛋白组与脂质组。")
st = design.stage(1)
st["status"] = "done"
st["final"] = ("研究类型：诊断准确性研究。目标人群：术前 2 周内完成增强 CT 且接受手术者。"
               "预期用途：辅助决定是否手术。计划注册于 ChiCTR。")
st3 = design.stage(3)
st3["status"] = "done"
st3["final"] = ("样本量：按 Riley 公式估算，训练集需 ≥240 例且恶性事件 ≥90 例；"
                "外部验证 ≥100 例、事件 ≥40 例。")
design.save()
print("① 已造课题:", design.name, "| 路径:", os.path.basename(design.path))
print("   课题下已有手稿附件:", len(design.manuscripts))

print()
print("=" * 72)
print("② 导入手稿（design 传入 → 应自动登记 + 快照背景）")
print("=" * 72)
eng = mr_engine.RevEngine(None)
proj = mr_engine.ReviewProject()
ok, msg, proj = eng.ingest(SRC, proj, design=design)
print("  ingest:", ok, msg)
print("  design_name  :", proj.design_name)
print("  design_path  :", os.path.basename(proj.design_path))
print("  design_digest:", len(proj.design_digest), "字")
print("  --- 背景快照内容 ---")
for line in proj.design_digest.splitlines():
    print("   ", line[:96])
print()
print("  课题 JSON 里是否登记了这份手稿:")
design2 = Project.load(design.path)
print("   manuscripts 条数:", len(design2.manuscripts))
for m in design2.manuscripts:
    print("    ", json.dumps({k: (os.path.basename(v) if k in
                                 ("source", "docx", "out_docx", "report",
                                  "project_path") and v else v)
                              for k, v in m.items()}, ensure_ascii=False))

print()
print("=" * 72)
print("③ 课题背景是否真的进了 LLM 提示词")
print("=" * 72)
from manuscript_review.mr_reviewer import USER_TMPL, _design_block
dblock = _design_block(proj.design_digest)
print("  _design_block 非空:", bool(dblock.strip()))
print("  区块前 2 行:")
for line in dblock.strip().splitlines()[:2]:
    print("   ", line[:96])
prompt = USER_TMPL.format(layer_name="引导式组学", layer_sub="十阶段",
                          layer_why="测试", design_block=dblock,
                          body="[1]（摘要）测试正文", items="- req_id=x")
print("  渲染后提示词含「本手稿所属课题的背景」:", "本手稿所属课题的背景" in prompt)
print("  含课题里的「外部验证」:", "外部验证" in prompt)
print("  含课题里的样本量结论:", "240 例" in prompt)

print()
print("=" * 72)
print("④ 再跑一次完整流程：附件记录应被更新（不是新增重复条目）")
print("=" * 72)
ok, msg, proj = eng.run_signals(proj)
ok, msg, proj = eng.review_to_word(proj, autonomy="comment")
eng._register_attachment(proj, design)
design3 = Project.load(design.path)
print("  课题下 manuscripts 条数:", len(design3.manuscripts), "（应仍为 1）")
m = design3.latest_manuscript()
print("  记录缺陷数:", m.get("defects"), "| 关键:", m.get("key_defects"))
print("  记录产出:", os.path.basename(m.get("out_docx") or ""))

print()
print("=" * 72)
print("⑤ 换个课题再看（模拟切换设计项目 → 关联应显示不匹配）")
print("=" * 72)
other = Project.new("另一个课题", raw="与手稿无关的课题")
print("  审阅项目记录的课题:", proj.design_name)
print("  当前工作台课题    :", other.name)
print("  是否匹配:", proj.design_name == other.name)

# 清理
for p in (design.path, other.path):
    try:
        os.remove(p)
    except Exception:
        pass
rm = proj.path()
if os.path.exists(rm):
    os.remove(rm)
print()
print("（已清理测试用的课题与审阅项目）")
