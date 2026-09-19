# -*- coding: utf-8 -*-
"""联调本机推理服务：/health、/v1/models、/v1/chat/completions（非流式 + 流式）。"""
import json
import os
import time
import urllib.request

BASE = "http://127.0.0.1:8788"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_api_test.txt")
lines = []


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return r.status, json.loads(r.read().decode())


def post(path, payload, stream=False):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        if not stream:
            return r.status, json.loads(r.read().decode())
        pieces, t0 = [], time.time()
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    d = json.loads(chunk)
                except Exception:
                    continue
                for ch in d.get("choices", []):
                    c = (ch.get("delta") or {}).get("content")
                    if c:
                        pieces.append(c)
        return r.status, {"text": "".join(pieces), "elapsed": time.time() - t0,
                          "chunks": len(pieces)}


try:
    st, body = get("/health")
    lines.append(f"GET /health → {st} {body['status']} 模型={body['model']} "
                 f"上游={body['base_url']} 密钥={body['api_key']} 需口令={body['auth_required']}")

    st, body = get("/v1/models")
    lines.append(f"GET /v1/models → {st} " + ", ".join(m["id"] for m in body["data"]))

    st, body = post("/v1/chat/completions", {
        "model": "deepseek-v4-pro",
        "messages": [{"role": "user", "content": "只回答两个字：收到"}],
        "max_tokens": 300})
    lines.append(f"POST 非流式 → {st} 回复={body['choices'][0]['message']['content'].strip()[:30]!r} "
                 f"tokens={body['usage'].get('total_tokens')}")

    st, body = post("/v1/chat/completions", {
        "model": "deepseek-v4-pro",
        "messages": [{"role": "user", "content": "用一句话说明影像组学最需要报告什么参数"}],
        "max_tokens": 400, "stream": True}, stream=True)
    lines.append(f"POST 流式 → {st} 收到 {body['chunks']} 片 / {body['elapsed']:.1f}s "
                 f"拼接={body['text'].strip()[:60]!r}")

    st, body = get("/health")
    lines.append(f"再次 /health → 调用次数={body['calls']} 流式={body['stream_calls']} "
                 f"累计 tokens={body['tokens']} 错误={body['errors']}")
    lines.append("结论：独立推理服务可用（OpenAI 兼容，含 SSE 流式）")
except Exception as e:                                             # noqa: BLE001
    import traceback
    lines.append("失败：" + traceback.format_exc()[-700:])

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("done")
