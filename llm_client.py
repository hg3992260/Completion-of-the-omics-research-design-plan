# -*- coding: utf-8 -*-
"""LLM 客户端（OpenAI 兼容协议，仅用标准库）。

配置解析优先级：
    1. 同目录 llm_config.json（界面里保存的配置）
    2. 环境变量（LLM_BASE_URL / LLM_API_KEY / LLM_MODEL，或 DEEPSEEK_API_KEY）
    3. agent 自身凭据 ~/.dsh/.credentials.yaml 的 refs 段（DEEPSEEK_API_KEY）

默认后端：DeepSeek 官方 https://api.deepseek.com · deepseek-v4-pro
"""

from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
from app_paths import data_path, secret_path

CONFIG_PATH = data_path("llm_config.json")   # 非敏感设置：便携，放 exe 同级
SECRET_PATH = secret_path()                   # 用户手填的密钥：只放本用户配置目录
CREDENTIALS = os.path.expanduser(r"~\.dsh\.credentials.yaml")

DEFAULTS = {
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-v4-pro",
    "api_key_env": "DEEPSEEK_API_KEY",
    "credential_name": "DEEPSEEK_API_KEY",
    "temperature": 0.4,
    # 推理模型的思考 token 也算进 max_tokens，预算给小了会「只想不说」返回空正文
    "max_tokens": 8000,
    "timeout": 240,
}


# --------------------------------------------------------------------------- 配置
def read_credential(name: str) -> str | None:
    """从 agent 的凭据文件里取密钥。"""
    try:
        txt = open(CREDENTIALS, encoding="utf-8").read()
    except Exception:
        return None
    m = re.search(rf"^\s*{re.escape(name)}\s*:\s*(\S+)\s*$", txt, re.M)
    return m.group(1) if m else None


_SSL_CTX = None


def ssl_context():
    """HTTPS 上下文：优先用 certifi 根证书（冻结后 Windows 证书库可能不可用）。"""
    global _SSL_CTX
    if _SSL_CTX is None:
        try:
            import certifi
            _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
        except Exception:                                          # noqa: BLE001
            try:
                _SSL_CTX = ssl.create_default_context()
            except Exception:                                      # noqa: BLE001
                _SSL_CTX = ssl._create_unverified_context()        # 最后兜底
    return _SSL_CTX


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            cfg.update(json.load(open(CONFIG_PATH, encoding="utf-8")))
        except Exception:
            pass
    # 用户手填的密钥存在用户配置目录（不放在程序目录，避免随文件夹分发而泄漏）
    if os.path.exists(SECRET_PATH):
        try:
            secret = json.load(open(SECRET_PATH, encoding="utf-8"))
            if secret.get("api_key"):
                cfg["api_key"] = secret["api_key"]
                cfg["key_source"] = "user"
        except Exception:
            pass
    cfg["base_url"] = os.environ.get("LLM_BASE_URL", cfg["base_url"]).rstrip("/")
    cfg["model"] = os.environ.get("LLM_MODEL", cfg["model"])
    cfg["temperature"] = float(os.environ.get("LLM_TEMPERATURE", cfg["temperature"]))
    # 密钥来源：界面里手填(saved) > 环境变量 > agent 凭据文件
    key, source = "", "none"
    if cfg.get("api_key"):
        key, source = cfg["api_key"], "saved"
    if not key:
        key = os.environ.get("LLM_API_KEY") or os.environ.get(cfg.get("api_key_env", "")) or ""
        source = "env" if key else "none"
    if not key:
        key = read_credential(cfg.get("credential_name", "DEEPSEEK_API_KEY")) or ""
        source = "credential" if key else "none"
    cfg["api_key"], cfg["key_source"] = key, source
    return cfg


def save_config(cfg: dict):
    """非敏感设置写便携配置；用户手填的密钥单独写用户配置目录（权限收紧到本人可读）。"""
    keep = {k: cfg[k] for k in ("base_url", "model", "temperature", "max_tokens", "timeout",
                                "api_key_env", "credential_name")
            if k in cfg}
    # 便携配置里永远不带密钥
    keep.pop("api_key", None)
    json.dump(keep, open(CONFIG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    if cfg.get("api_key") and cfg.get("key_source") in ("user", "saved"):
        json.dump({"api_key": cfg["api_key"]}, open(SECRET_PATH, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        try:
            os.chmod(SECRET_PATH, 0o600)          # 仅本人可读写（Windows 上忽略即可）
        except Exception:                                          # noqa: BLE001
            pass
    elif cfg.get("api_key") == "" and os.path.exists(SECRET_PATH):
        try:
            os.remove(SECRET_PATH)                # 用户清空了密钥 → 一并删掉
        except Exception:                                          # noqa: BLE001
            pass


def mask(key: str) -> str:
    if not key:
        return "（未配置）"
    return key[:6] + "…" + key[-4:] if len(key) > 12 else "已配置"


# --------------------------------------------------------------------------- 客户端
class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or load_config()

    # -- 元信息 -------------------------------------------------------------
    @property
    def model(self) -> str:
        return self.cfg.get("model", DEFAULTS["model"])

    @property
    def base_url(self) -> str:
        return self.cfg.get("base_url", DEFAULTS["base_url"])

    def describe(self) -> str:
        return f"{self.model} @ {self.base_url} · {mask(self.cfg.get('api_key', ''))}"

    def list_models(self) -> list[str]:
        self.last_error = ""
        for path in ("/models", "/v1/models"):
            try:
                data = self._request("GET", path, None)
                return [m.get("id") for m in data.get("data", []) if m.get("id")]
            except LLMError as e:
                self.last_error = str(e)          # 供自检显示（源模式/冻结模式都适用）
                continue
            except Exception as e:                # noqa: BLE001
                self.last_error = f"{type(e).__name__}: {e}"
                continue
        return []

    # -- 基础请求 -----------------------------------------------------------
    def _url(self, path: str) -> str:
        base = self.base_url
        if base.endswith("/v1") and path.startswith("/v1"):
            path = path[3:]
        return base + path

    def _headers(self) -> dict:
        key = self.cfg.get("api_key", "")
        if not key:
            raise LLMError("未配置 API Key：请在「设置」里填写，或确认 ~/.dsh/.credentials.yaml 可读")
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                "User-Agent": "omics-design-studio/1.0"}

    def _request(self, method: str, path: str, payload: dict | None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(self._url(path), data=data, headers=self._headers(),
                                     method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.get("timeout", 180),
                                        context=ssl_context()) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            raise LLMError(f"HTTP {e.code}：{detail}") from None
        except urllib.error.URLError as e:
            raise LLMError(f"网络错误：{e.reason}") from None
        except Exception as e:                                    # noqa: BLE001
            raise LLMError(f"请求失败：{e!r}") from None

    # -- 对话 ---------------------------------------------------------------
    def chat(self, messages: list[dict], stream: bool = False, on_delta=None,
             temperature: float | None = None, max_tokens: int | None = None,
             reason: bool = False) -> dict:
        """返回 {content, reasoning, usage, model, elapsed, finish_reason, retried}。

        reason=True 走**推理模式**：温度降到 0（让推理可复现）、把 token 预算抬到至少 12000
        （思考 token 也算在预算内），并保留 reasoning_content 供界面展示推理过程。
        推理模型有时会把整个 token 预算花在思考上，导致正文为空（finish_reason=length）。
        这里自动加倍预算重试一次，并提示直接给结论。
        """
        base_temp = self.cfg.get("temperature", 0.4) if temperature is None else temperature
        base_budget = self.cfg.get("max_tokens", 8000) if max_tokens is None else max_tokens
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0 if reason else base_temp,
            "max_tokens": max(int(base_budget), 12000) if reason else int(base_budget),
            "stream": bool(stream),
        }
        t0 = time.time()
        res = self._once(payload, stream, on_delta, t0)
        retried = False
        if not res["content"].strip() and res.get("finish_reason") in ("length", ""):
            retried = True
            payload["max_tokens"] = min(int(payload["max_tokens"]) * 2, 32000)
            payload["stream"] = False
            payload["messages"] = messages + [
                {"role": "user", "content": "上一轮你把预算全部用于思考而没有输出正文。"
                                            "请直接输出规定的小标题与正文，不要再做长篇推理。"}]
            res = self._once(payload, False, None, t0)
        res["retried"] = retried
        return res

    def _once(self, payload: dict, stream: bool, on_delta, t0: float) -> dict:
        if not stream:
            d = self._request("POST", "/chat/completions", payload)
            ch = (d.get("choices") or [{}])[0]
            msg = ch.get("message", {})
            return {"content": msg.get("content") or "",
                    "reasoning": msg.get("reasoning_content") or "",
                    "usage": d.get("usage") or {},
                    "model": d.get("model", self.model),
                    "finish_reason": ch.get("finish_reason", ""),
                    "elapsed": time.time() - t0}
        return self._chat_stream(payload, on_delta, t0)

    def _chat_stream(self, payload: dict, on_delta, t0: float) -> dict:
        req = urllib.request.Request(self._url("/chat/completions"),
                                     data=json.dumps(payload).encode(),
                                     headers=self._headers(), method="POST")
        content, reasoning, usage, model, finish = [], [], {}, self.model, ""
        try:
            resp = urllib.request.urlopen(req, timeout=self.cfg.get("timeout", 180),
                                      context=ssl_context())
        except urllib.error.HTTPError as e:
            raise LLMError(f"HTTP {e.code}：{e.read().decode('utf-8', 'ignore')[:300]}") from None
        except Exception as e:                                     # noqa: BLE001
            raise LLMError(f"网络错误：{e!r}") from None

        with resp:
            for raw in resp:
                line = raw.decode("utf-8", "ignore").strip()
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    d = json.loads(chunk)
                except Exception:
                    continue
                if d.get("model"):
                    model = d["model"]
                if d.get("usage"):
                    usage = d["usage"]
                for ch in d.get("choices", []):
                    delta = ch.get("delta") or {}
                    if ch.get("finish_reason"):
                        finish = ch["finish_reason"]
                    piece = delta.get("content")
                    if piece:
                        content.append(piece)
                        if on_delta:
                            on_delta(piece, "content")
                    rc = delta.get("reasoning_content")
                    if rc:
                        reasoning.append(rc)
                        if on_delta:
                            on_delta(rc, "reasoning")
        return {"content": "".join(content), "reasoning": "".join(reasoning),
                "usage": usage, "model": model, "finish_reason": finish,
                "elapsed": time.time() - t0}


if __name__ == "__main__":                                        # 命令行自检
    c = LLMClient()
    print("配置：", c.describe())
    print("可用模型：", ", ".join(c.list_models()) or "（无法列出）")
    out = c.chat([{"role": "user", "content": "只回答两个字：就绪"}], max_tokens=200)
    print("连通性：", repr(out["content"].strip()), f"{out['elapsed']:.1f}s", out["usage"])
