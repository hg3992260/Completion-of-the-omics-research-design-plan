# -*- coding: utf-8 -*-
"""验证新增的 MCP 手稿审阅工具（直接调用工具函数，等价于客户端调用）。"""
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


def show(title, payload, keys=None):
    print("=" * 66)
    print(title)
    print("=" * 66)
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            print(payload[:800])
            return
    if keys:
        payload = {k: payload.get(k) for k in keys}
    print(json.dumps(payload, ensure_ascii=False, indent=1)[:2600])
    print()


show("① manuscript_layers", M.manuscript_layers())
show("② manuscript_toolchain", M.manuscript_toolchain())

# 只跑确定性核验（skip_llm=True），避免重复花钱；LLM 分支另有专门测试
r = M.manuscript_review(SRC, layers="omics,stat,shape", skip_llm=True)
show("③ manuscript_review (skip_llm)", r,
     keys=["ok", "ingest", "signals", "project", "converted", "signal_summary",
           "summary", "warnings"])

d = M.manuscript_defects(layer="omics", severity="关键", limit=3)
show("④ manuscript_defects(omics, 关键, limit=3)", d,
     keys=["ok", "project", "returned", "defects"])

show("⑤ manuscript_apply", M.manuscript_apply(mode="comment_only"),
     keys=["ok", "msg", "out_docx"])

show("⑥ manuscript_report", M.manuscript_report())
show("⑦ manuscript_projects", M.manuscript_projects())
