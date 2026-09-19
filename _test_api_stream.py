# -*- coding: utf-8 -*-
"""流式联调（修正版）：区分 content 与 reasoning_content，预算给足。"""
import json
import os
import time
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_api_stream.txt")
lines = []


def stream_call(model, prompt, max_tokens=2500):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": max_tokens, "stream": True}
    req = urllib.request.Request("http://127.0.0.1:8788/v1/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    content, reasoning, t0, n = [], [], time.time(), 0
    with urllib.request.urlopen(req, timeout=240) as r:
        for raw in r:
            s = raw.decode("utf-8", "ignore").strip()
            if not s.startswith("data:"):
                continue
            chunk = s[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                d = json.loads(chunk)
            except Exception:
                continue
            for ch in d.get("choices", []):
                delta = ch.get("delta") or {}
                if delta.get("content"):
                    content.append(delta["content"])
                if delta.get("reasoning_content"):
                    reasoning.append(delta["reasoning_content"])
                n += 1
    return {"chunks": n, "content": "".join(content), "reasoning_len": len("".join(reasoning)),
            "elapsed": time.time() - t0}


for model in ("deepseek-v4-pro", "deepseek-flash"):
    r = stream_call(model, "用两句话说明：影像组学论文必须报告的采集参数有哪些？")
    lines.append(f"{model}: 分片={r['chunks']} 用时={r['elapsed']:.1f}s "
                 f"正文={len(r['content'])}字 思考={r['reasoning_len']}字")
    lines.append(f"    正文开头：{r['content'].strip()[:90]!r}")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("done")
