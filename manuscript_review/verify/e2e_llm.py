# -*- coding: utf-8 -*-
"""跑一次真实的 LLM 语义审阅，验证 JSON 解析、req_id 匹配与缺陷质量。"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from llm_client import LLMClient, load_config
from manuscript_review import mr_docx, mr_engine, mr_reviewer, mr_signals

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sample_manuscript()

cfg = load_config()
client = LLMClient(cfg)
print("model:", client.model, "base:", client.base_url)

ms = mr_docx.load(SRC)
hits = mr_signals.check(ms)
det = mr_signals.defects(hits)
skip = {h.signal for h in hits if h.verdict in ("missing", "weak")}
print("确定性缺陷:", len(det), "| 跳过信号:", len(skip))

t0 = time.time()


def on_prog(call):
    print(f"  [{call.layer} {call.batch_index}] ok={call.ok} "
          f"defects={len(call.defects)} cached={call.cached} "
          f"{call.elapsed:.1f}s {call.error[:120]}", flush=True)


# 只跑一层（shape 层最能检验语义判断），避免整轮耗时过长
defects, calls = mr_reviewer.review(client, ms, layers=["shape"], use_cache=True,
                                    skip_signals=skip, on_progress=on_prog)
print()
print(f"LLM 缺陷 {len(defects)} 条 / {len(calls)} 批 / {time.time()-t0:.0f}s")
merged = mr_reviewer.merge_defects(det, defects)
merged = mr_reviewer.sort_defects(merged)
print("合并后:", json.dumps(mr_reviewer.summarize(merged), ensure_ascii=False))
print()
for d in merged:
    if d.get("source") != "llm":
        continue
    print(f"[{d['severity']}] {d['layer']} 段{d['para_idx']} · {d['title']}")
    print(f"   规范: {d['ref']} | {d['spec']}")
    print(f"   缺陷: {d['why'][:150]}")
    print(f"   证据: {(d.get('evidence') or '')[:100]}")
    print(f"   建议: {d['suggestion'][:150]}")
    print()

bad = [c for c in calls if not c.ok]
if bad:
    print("失败批次:", [(c.layer, c.batch_index, c.error[:200]) for c in bad])
