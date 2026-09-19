# -*- coding: utf-8 -*-
"""无界面端到端联调：直接驱动 DesignAgent 跑完三个阶段，检查真实输出质量。
不打开任何窗口，避免与正在使用的界面互相干扰。

用法：python _e2e_agent.py [模型名]
"""

import os
import sys
import time

from design_agent import Project, DesignAgent, parse_sections, pick, q_text
from llm_client import LLMClient, load_config

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_e2e_agent.log")

RAW = ("回顾性收集 2015 年 1 月至 2023 年 6 月在我院行手术切除、术后病理证实的胰腺囊性病变"
       "（PCL）患者，术前行上腹部增强 CT。计划在门静脉期图像上手工勾画囊性病灶、胰腺与"
       "非病灶区域，用 PyRadiomics 提取影像组学特征，比较 LASSO、随机森林等模型预测"
       "恶性潜能（高级别异型增生 / 浸润癌）的效能，并在另一家医院做外部验证；"
       "同时前瞻性留取囊液做蛋白组与脂质组，解释模型背后的生物学机制。"
       "预计纳入约 300 例，外部验证约 60 例。")

ANSWERS = ["门静脉期增强 CT，层厚 1.25 mm，两家医院机型不同",
           "以手术病理为金标准，高级别异型增生或浸润癌判为恶性",
           "训练集 262 例（恶性 101 例）、外部 50 例、前瞻 34 例",
           "已按患者 ID 核查，两份队列无重叠"]

log = open(OUT, "w", encoding="utf-8")


def say(*parts):
    text = " ".join(str(p) for p in parts)
    log.write(text + "\n")
    log.flush()


def show(title, out):
    say(f"\n{'=' * 30} {title} {'=' * 30}")
    say(f"[模型 {out.get('model')} · {out['elapsed']:.1f}s · tokens "
        f"{out['usage'].get('total_tokens', '—')}]")
    say(out["content"].strip())


cfg = load_config()
if len(sys.argv) > 1:
    cfg["model"] = sys.argv[1]
client = LLMClient(cfg)
say(f"后端：{client.describe()}")
say(f"输入：{RAW[:60]}…")

proj = Project(name="_agent_e2e", raw_design=RAW, model=client.model)
agent = DesignAgent(client, proj)

t0 = time.time()
show("速读", agent.run(agent.kickoff_messages()))

for sid in (1, 2, 3):
    out = agent.run(agent.ask_messages(sid))
    show(f"阶段 {sid:02d} 追问（原文）", out)
    sec = parse_sections(out["content"])
    proj.stage(sid)["questions"] = __import__("design_agent").parse_questions(
        pick(sec, "必须澄清", "问题"))
    proj.stage(sid)["answers"] = [ANSWERS[i % len(ANSWERS)]
                                  for i in range(len(proj.stage(sid)["questions"]))]
    say("\n--- 清洗后的问题 ---")
    for i, q in enumerate(proj.stage(sid)["questions"]):
        say(f"  Q{i + 1}: {q_text(q)}")

    out2 = agent.run(agent.rewrite_messages(sid))
    sec2 = parse_sections(out2["content"])
    draft = pick(sec2, "改写稿")
    proj.stage(sid)["draft"] = proj.stage(sid)["final"] = draft
    proj.stage(sid)["status"] = "done"
    proj.stage(sid)["checklist"] = __import__("design_agent").parse_checklist(
        pick(sec2, "检查表"))
    say(f"\n{'=' * 30} 阶段 {sid:02d} 改写稿（清洗后） {'=' * 30}")
    say(draft)
    say(f"\n--- 检查表（{len(proj.stage(sid)['checklist'])} 条）---")
    for c in proj.stage(sid)["checklist"]:
        say("  · " + c)

path = proj.save()
say(f"\n总耗时 {time.time() - t0:.0f}s · 项目已存 {path}")
say(f"文档字数 {len(proj.render_doc())}")
log.close()
print("done ->", OUT)
