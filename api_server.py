# -*- coding: utf-8 -*-
"""组学研究设计工作台 —— 独立推理服务（OpenAI 兼容 API）。

把本程序背后的 LLM（默认 DeepSeek）以 OpenAI 兼容协议暴露出去，任何支持
"自定义 base_url" 的客户端（OpenAI SDK、LangChain、Cursor、Cherry Studio…）
都能直接接：

    GET  /health                 健康检查（模型、上游、是否已配置密钥）
    GET  /v1/models             模型列表（透传上游）
    POST /v1/chat/completions   对话补全，支持 stream=true（SSE 直通）

运行：
    D:\\python\\envs\\mar\\python.exe api_server.py                 # 默认 127.0.0.1:8788
    D:\\python\\envs\\mar\\python.exe api_server.py --port 9000 --model deepseek-flash

客户端示例：
    from openai import OpenAI
    cli = OpenAI(base_url="http://127.0.0.1:8788/v1", api_key="not-needed")
    cli.chat.completions.create(model="deepseek-v4-pro", messages=[...])

安全：默认只绑 127.0.0.1（不对外网开放，避免把带密钥的代理暴露出去）。
需要局域网共享时显式 --host 0.0.0.0 --token <自定口令>，客户端用
Authorization: Bearer <口令> 访问。
"""

from __future__ import annotations

import argparse
import json
import os

from app_paths import APP_VERSION  # noqa: E402
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from llm_client import LLMClient, load_config, mask, ssl_context

STATE = {"client": None, "token": "", "started": time.time(), "calls": 0,
         "stream_calls": 0, "errors": 0, "tokens": 0}


def client() -> LLMClient:
    if STATE["client"] is None:
        STATE["client"] = LLMClient(load_config())
    return STATE["client"]


class Handler(BaseHTTPRequestHandler):
    server_version = f"PCL-Radiomics-LLM/{APP_VERSION}"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------ 工具
    def log_message(self, fmt, *args):                    # 静音默认日志
        if os.environ.get("API_SERVER_VERBOSE"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        if not STATE["token"]:
            return True
        got = (self.headers.get("Authorization") or "").replace("Bearer ", "").strip()
        return got == STATE["token"]

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:                                          # noqa: BLE001
            return {}

    # ------------------------------------------------------------------ 路由
    def do_OPTIONS(self):                                          # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def do_GET(self):                                              # noqa: N802
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path in ("/health", "/"):
            c = client()
            return self._json(200, {
                "status": "ok", "service": "组学研究设计工作台 · 推理服务",
                "model": c.model, "base_url": c.base_url,
                "api_key": mask(c.cfg.get("api_key", "")),
                "auth_required": bool(STATE["token"]),
                "uptime_s": round(time.time() - STATE["started"], 1),
                "calls": STATE["calls"], "stream_calls": STATE["stream_calls"],
                "errors": STATE["errors"], "tokens": STATE["tokens"],
            })
        if path in ("/v1/models", "/models"):
            if not self._authorized():
                return self._json(401, {"error": {"message": "invalid token"}})
            try:
                ids = client().list_models()
                return self._json(200, {"object": "list", "data": [
                    {"id": m, "object": "model", "created": int(STATE["started"]),
                     "owned_by": "deepseek"} for m in ids]})
            except Exception as e:                                 # noqa: BLE001
                STATE["errors"] += 1
                return self._json(502, {"error": {"message": str(e)}})
        return self._json(404, {"error": {"message": f"unknown path {path}"}})

    def do_POST(self):                                             # noqa: N802
        path = self.path.split("?")[0].rstrip("/")
        if path not in ("/v1/chat/completions", "/chat/completions"):
            return self._json(404, {"error": {"message": f"unknown path {path}"}})
        if not self._authorized():
            return self._json(401, {"error": {"message": "invalid token"}})
        body = self._body()
        messages = body.get("messages") or []
        if not messages:
            return self._json(400, {"error": {"message": "messages is required"}})
        stream = bool(body.get("stream"))
        model = body.get("model") or client().model
        kwargs = {"temperature": body.get("temperature"),
                  "max_tokens": body.get("max_tokens") or body.get("max_completion_tokens")}
        STATE["calls"] += 1
        try:
            if stream:
                STATE["stream_calls"] += 1
                return self._stream(model, messages, kwargs)
            out = self._chat(model, messages, kwargs)
            STATE["tokens"] += (out.get("usage") or {}).get("total_tokens", 0) or 0
            return self._json(200, self._response(out, model))
        except Exception as e:                                     # noqa: BLE001
            STATE["errors"] += 1
            return self._json(502, {"error": {"message": str(e), "type": "upstream_error"}})

    # ------------------------------------------------------------------ 上游
    def _chat(self, model: str, messages: list, kwargs: dict) -> dict:
        c = client()
        if model != c.model:
            c = LLMClient({**c.cfg, "model": model})
        return c.chat(messages, stream=False,
                      temperature=kwargs.get("temperature"),
                      max_tokens=kwargs.get("max_tokens"))

    def _response(self, out: dict, model: str) -> dict:
        return {"id": f"chatcmpl-{int(time.time() * 1000)}", "object": "chat.completion",
                "created": int(time.time()), "model": out.get("model") or model,
                "choices": [{"index": 0, "finish_reason": out.get("finish_reason") or "stop",
                             "message": {"role": "assistant",
                                         "content": out.get("content") or ""}}],
                "usage": out.get("usage") or {}}

    def _stream(self, model: str, messages: list, kwargs: dict):
        """SSE 直通：把上游的 data: 行原样转发，客户端可逐字接收。"""
        c = client()
        if model != c.model:
            c = LLMClient({**c.cfg, "model": model})
        payload = {"model": model, "messages": messages, "stream": True,
                   "temperature": kwargs.get("temperature")
                   if kwargs.get("temperature") is not None else c.cfg.get("temperature", 0.4),
                   "max_tokens": kwargs.get("max_tokens") or c.cfg.get("max_tokens", 8000)}
        req = urllib.request.Request(c._url("/chat/completions"),
                                     data=json.dumps(payload).encode(),
                                     headers=c._headers(), method="POST")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        cid = f"chatcmpl-{int(time.time() * 1000)}"
        try:
            with urllib.request.urlopen(req, timeout=c.cfg.get("timeout", 240),
                                            context=ssl_context()) as resp:
                for raw in resp:
                    line = raw.decode("utf-8", "ignore").rstrip("\n")
                    if not line:
                        continue
                    if line.startswith("data:"):
                        chunk = line[5:].strip()
                        if chunk == "[DONE]":
                            break
                        try:
                            d = json.loads(chunk)
                        except Exception:                          # noqa: BLE001
                            continue
                        for ch in d.get("choices", []):
                            delta = ch.get("delta") or {}
                            # 与 DeepSeek 官方一致：reasoning_content 一并透传，
                            # 标准客户端只读 content，不会受影响
                            keep = {k: v for k, v in delta.items()
                                    if k in ("content", "role", "reasoning_content")}
                            piece = {"id": cid, "object": "chat.completion.chunk",
                                     "created": int(time.time()),
                                     "model": d.get("model") or model,
                                     "choices": [{"index": 0, "delta": keep,
                                                  "finish_reason": ch.get("finish_reason")}]}
                            self.wfile.write(
                                f"data: {json.dumps(piece, ensure_ascii=False)}\n\n".encode())
                            self.wfile.flush()
                        if d.get("usage"):
                            STATE["tokens"] += (d["usage"].get("total_tokens") or 0)
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except Exception as e:                                     # noqa: BLE001
            STATE["errors"] += 1
            err = {"error": {"message": str(e), "type": "upstream_error"}}
            try:
                self.wfile.write(f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
            except Exception:                                      # noqa: BLE001
                pass


def main() -> None:
    ap = argparse.ArgumentParser(description="组学研究设计工作台 · OpenAI 兼容推理服务")
    ap.add_argument("--host", default="127.0.0.1", help="默认仅本机可访问")
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--model", default="", help="默认模型（默认取 llm_config.json / agent 凭据）")
    ap.add_argument("--token", default="", help="可选的访问口令（局域网共享时建议设置）")
    args = ap.parse_args()

    cfg = load_config()
    if args.model:
        cfg["model"] = args.model
    STATE["client"] = LLMClient(cfg)
    STATE["token"] = args.token

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    c = STATE["client"]
    print(f"推理服务已启动： http://{args.host}:{args.port}/v1")
    print(f"  模型 {c.model} → 上游 {c.base_url} · 密钥 {mask(c.cfg.get('api_key',''))}")
    print(f"  健康检查 http://{args.host}:{args.port}/health"
          + ("　（已启用口令）" if args.token else "　（无口令，仅本机）"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
