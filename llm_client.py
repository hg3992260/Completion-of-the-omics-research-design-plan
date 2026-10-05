# -*- coding: utf-8 -*-
"""LLM 客户端（OpenAI 兼容协议，仅用标准库）。

配置解析优先级：
    1. 同目录 llm_config.json（界面里保存的配置）
    2. 环境变量（LLM_BASE_URL / LLM_API_KEY / LLM_MODEL，或 DEEPSEEK_API_KEY）
    3. agent 自身凭据 ~/.dsh/.credentials.yaml 的 refs 段（DEEPSEEK_API_KEY）

默认后端：DeepSeek 官方 https://api.deepseek.com · deepseek-v4-pro
"""

from __future__ import annotations

import http.client
import json
import os
import re
import socket
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
    # 传输层瞬时故障的重试次数（不含首次尝试）。流式响应被中途掐断
    # （IncompleteRead / ConnectionReset）几乎都是服务端或中间网络抖动，
    # 重试一次通常就过；这一项就是为它准备的。
    "retries": 2,
}


# --------------------------------------------------------------------------- 传输层故障
# 这个元组里的异常都表示「请求本身没被拒绝，只是连接坏了」，重试有意义。
# 注意：http.client.IncompleteRead 只继承 HTTPException，**不是** OSError 子类，
# 必须单独列出，否则不会被当成可重试错误。
RETRYABLE = (
    http.client.IncompleteRead,          # 响应体读到一半连接断了（0 bytes read 也属此类）
    http.client.RemoteDisconnected,
    ConnectionResetError,
    ConnectionAbortedError,
    BrokenPipeError,
    socket.timeout,
    TimeoutError,
)


def _describe_net_error(e: BaseException) -> str:
    """把传输层异常翻译成能看懂、能据以处置的中文说明。"""
    if isinstance(e, http.client.IncompleteRead):
        got = len(e.partial or b"")
        if got == 0:
            return ("服务端已开始响应但一个字节都没送到就断开了"
                    "（IncompleteRead: 0 bytes read）")
        return (f"流式响应读到一半被掐断：已收到 {got} 字节，"
                f"还差 {e.expected} 字节（IncompleteRead）")
    if isinstance(e, http.client.RemoteDisconnected):
        return "服务端主动断开了连接且没返回任何响应（RemoteDisconnected）"
    if isinstance(e, (socket.timeout, TimeoutError)):
        return "等待响应超时（可在「设置」里调大 timeout，或改用非流式）"
    if isinstance(e, ConnectionResetError):
        return "连接被重置（对端或中间网络设备强制断开）"
    return f"{type(e).__name__}: {e}"


def _is_retryable(e: BaseException) -> bool:
    if isinstance(e, RETRYABLE):
        return True
    if isinstance(e, urllib.error.URLError):
        # URLError 包了一层真实原因，需要拆开看
        return isinstance(getattr(e, "reason", None), RETRYABLE) or \
            isinstance(e, urllib.error.URLError)
    return isinstance(e, OSError)


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
                                "retries", "api_key_env", "credential_name")
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
        """非流式请求。同样对传输层瞬时故障重试（read() 也会抛 IncompleteRead）。"""
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(self._url(path), data=data, headers=self._headers(),
                                     method=method)
        attempts = max(1, int(self.cfg.get("retries", DEFAULTS["retries"])) + 1)
        last_err: BaseException | None = None
        for attempt in range(1, attempts + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.cfg.get("timeout", 180),
                                            context=ssl_context()) as r:
                    return json.loads(r.read().decode("utf-8", "ignore"))
            except urllib.error.HTTPError as e:
                # 服务端明确答复，重试无意义
                detail = e.read().decode("utf-8", "ignore")[:300]
                raise LLMError(f"HTTP {e.code}：{detail}") from None
            except BaseException as e:                            # noqa: BLE001
                if not _is_retryable(e):
                    if isinstance(e, urllib.error.URLError):
                        raise LLMError(f"网络错误：{e.reason}") from None
                    raise LLMError(f"请求失败：{e!r}") from None
                last_err = e
                if attempt >= attempts:
                    break
                time.sleep(min(2 ** (attempt - 1), 8))
        raise LLMError(f"请求失败（已重试 {attempts - 1} 次仍失败）："
                       f"{_describe_net_error(last_err)}") from None

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
        """流式请求。传输层瞬时故障（尤其 IncompleteRead）自动重试。

        踩过的坑：早先 try 只包住 urlopen，而响应体是在 `with resp:` 的 for 循环里读的，
        循环没有任何保护 —— 一旦服务端把连接掐在半路（实测
        `IncompleteRead(0 bytes read)`），异常就直接冒到上层，整批审阅白跑。
        现在整个「发请求 + 读流」都在重试保护内。
        """
        attempts = max(1, int(self.cfg.get("retries", DEFAULTS["retries"])) + 1)
        last_err: BaseException | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._stream_once(payload, on_delta, t0, attempt)
            except urllib.error.HTTPError as e:
                # 4xx/5xx 是服务端明确答复，重试没意义
                raise LLMError(f"HTTP {e.code}："
                               f"{e.read().decode('utf-8', 'ignore')[:300]}") from None
            except BaseException as e:                             # noqa: BLE001
                if not _is_retryable(e):
                    raise LLMError(f"请求失败：{_describe_net_error(e)}") from None
                last_err = e
                if attempt >= attempts:
                    break
                wait = min(2 ** (attempt - 1), 8)                  # 1s, 2s, 4s… 封顶 8s
                if on_delta:
                    on_delta(f"　[传输中断，{wait}s 后重试 "
                             f"{attempt}/{attempts - 1}] {_describe_net_error(e)}\n",
                             "note")
                time.sleep(wait)
        raise LLMError(f"请求失败（已重试 {attempts - 1} 次仍失败）："
                       f"{_describe_net_error(last_err)}") from None

    def _stream_once(self, payload: dict, on_delta, t0: float,
                     attempt: int = 1) -> dict:
        req = urllib.request.Request(self._url("/chat/completions"),
                                     data=json.dumps(payload).encode(),
                                     headers=self._headers(), method="POST")
        content, reasoning, usage, model, finish = [], [], {}, self.model, ""
        saw_done = False
        resp = urllib.request.urlopen(req, timeout=self.cfg.get("timeout", 180),
                                      context=ssl_context())

        with resp:
            for raw in resp:
                line = raw.decode("utf-8", "ignore").strip()
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    saw_done = True
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
        if not content and not reasoning and not finish:
            # 连接建立、也没报错，但一个有效 delta 都没收到 —— 同样算传输失败，可重试
            raise http.client.IncompleteRead(b"", 0)
        # 流既没给 [DONE] 也没有 finish_reason，说明响应被中途截断了。
        # 这种情况 urllib **不会抛异常**（实测：服务端声明 Content-Length 却少发一半、
        # 或 chunked 发一半就断，for 循环都只是安静结束），于是半截正文会被当成完整结果
        # 写进定稿 —— 比抛错更危险。这里显式当作可重试的传输故障。
        if not saw_done and not finish:
            raise http.client.IncompleteRead("".join(content).encode("utf-8"), 1)
        return {"content": "".join(content), "reasoning": "".join(reasoning),
                "usage": usage, "model": model, "finish_reason": finish,
                "attempts": attempt,
                "elapsed": time.time() - t0}


if __name__ == "__main__":                                        # 命令行自检
    c = LLMClient()
    print("配置：", c.describe())
    print("可用模型：", ", ".join(c.list_models()) or "（无法列出）")
    out = c.chat([{"role": "user", "content": "只回答两个字：就绪"}], max_tokens=200)
    print("连通性：", repr(out["content"].strip()), f"{out['elapsed']:.1f}s", out["usage"])
