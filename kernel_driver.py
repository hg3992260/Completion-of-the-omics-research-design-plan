# -*- coding: utf-8 -*-
"""方向 B 驱动层：宿主 → opencode 内核的会话驱动 + 问答回灌（Qt-free）。

与 kernel_client 的分工：
    kernel_client   进程生命周期 + 裸 HTTP/SSE（方向 B/D 的传输层）
    kernel_driver   会话语义层：投递任务、事件归一化、问答/权限回灌、结果收集

为什么走 **legacy V1 HTTP**（`/session/:id/message`），而不是 V2 `/api/session/:id/prompt`：
    · V2 的模型解析在本构建只认 opencode/* 自有模型（实测 deepseek 报
      ModelUnavailableError），无法用用户 auth.json 里的 provider；
    · legacy 端点走 V1 `SessionPrompt`，在**服务端**执行，直接用 auth.json 的
      provider（deepseek 实测 6s 出结果），并完整保留 18 内置工具 + 宿主的 21
      个 MCP 领域工具（实测方向 A 打通）；
    · question / permission 都发生在服务端，可经 `/question`、`/permission`
      回灌，从而支持「GUI 就地答题」（实测：模型调用 question 工具 → 待决列表
      → POST /question/:id/reply → 阻塞的会话继续）。

用户澄清的交互模型（opencode-embedding-plan.md §9.7 + 本轮确认）：
    · opencode 是唯一大脑；GUI 的智能动作改为向内核 session 投递任务
    · GUI 就地答题：轮询 `/question` 发现待决 → on_event("question") → 回灌
    · 交互镜像仍在 opencode 自带 TUI（不重写会话 UI）

阻塞式、线程安全，供 GUI 在后台线程调用。
"""

from __future__ import annotations

import os
import sys
import threading
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import kernel_client as kc                                              # noqa: E402


# ------------------------------------------------------------- V2 事件归一化
#  保留给 SSE 观察面（/api/event，{id,type,properties}）；主链路走 legacy 轮询。

def _props(ev) -> dict:
    if not isinstance(ev, dict):
        return {}
    p = ev.get("properties")
    if isinstance(p, dict):
        return p
    p = ev.get("data")
    return p if isinstance(p, dict) else {}


def normalize_event(ev, want_session: str | None = None) -> dict | None:
    """把一条 V2/兼容 SSE 事件归一化；want_session 非空时只保留该会话。"""
    if not isinstance(ev, dict):
        return None
    t = ev.get("type") or ""
    p = _props(ev)
    sid = p.get("sessionID") if isinstance(p.get("sessionID"), str) else None
    if want_session and sid and sid != want_session:
        return None
    base = {"kind": "raw", "type": t, "session_id": sid, "text": "", "data": p, "raw": ev}
    if t == "session.next.text.delta":
        base.update(kind="text", text=p.get("delta") or "")
    elif t == "session.next.reasoning.delta":
        base.update(kind="reasoning", text=p.get("delta") or "")
    elif t == "session.next.tool.called":
        base.update(kind="tool", text=p.get("tool") or "",
                    data={"tool": p.get("tool"), "input": p.get("input")})
    elif t == "session.next.step.ended":
        base.update(kind="step", text=p.get("finish") or "")
    elif t in ("question.v2.asked", "question.asked"):
        base.update(kind="question", data=p)
    elif t in ("permission.v2.asked", "permission.asked"):
        base.update(kind="permission", data=p)
    elif t == "server.connected":
        base.update(kind="connected")
    elif t == "server.heartbeat":
        base.update(kind="heartbeat")
    return base


# -------------------------------------------------------- V1 parts → 事件

def parts_to_events(session_id: str, out: dict) -> list:
    """把 SessionV1.WithParts 的 parts 归一化成事件列表。

    V1 part 类型：step-start / step-finish / text / reasoning / tool / file / ...。
    """
    events: list = []
    info = out.get("info") or {}
    for p in (out.get("parts") or []):
        if not isinstance(p, dict):
            continue
        t = p.get("type")
        ev = {"kind": "raw", "type": t or "", "session_id": session_id,
              "text": "", "data": p, "raw": p}
        if t == "text":
            ev.update(kind="text_full", text=p.get("text") or "")
        elif t == "reasoning":
            ev.update(kind="reasoning", text=p.get("text") or "")
        elif t == "tool":
            ev.update(kind="tool", text=p.get("tool") or "",
                      data={"tool": p.get("tool"), "state": p.get("state"),
                            "callID": p.get("callID")})
        elif t == "step-start":
            ev.update(kind="step_start")
        elif t == "step-finish":
            ev.update(kind="step", text=p.get("reason") or "",
                      data={"reason": p.get("reason"), "cost": p.get("cost"),
                            "tokens": p.get("tokens")})
        else:
            continue
        events.append(ev)
    return events


def assistant_text(out: dict) -> str:
    """取 SessionV1.WithParts 的正文。"""
    return "".join(p.get("text", "") for p in (out.get("parts") or [])
                   if isinstance(p, dict) and p.get("type") == "text")


def transcript_text(events: list) -> str:
    out = []
    for ev in events:
        k = ev.get("kind")
        if k == "text":
            out.append(ev.get("text") or "")
        elif k == "text_full":
            out.append(ev.get("text") or "")
        elif k == "tool":
            out.append(f"\n[tool] {ev.get('text')}\n")
    return "".join(out)


# ---------------------------------------------------------------------- 驱动

class KernelDriver:
    """面向会话的驱动。持有 KernelClient，不负责进程生命周期。"""

    QUIET = ("heartbeat", "connected", "raw")

    def __init__(self, client: kc.KernelClient):
        self.client = client
        self._lock = threading.RLock()
        self._seen_interactions: set = set()
        self._stop = threading.Event()
        self._poller: threading.Thread | None = None
        self._session_id: str | None = None
        self._on_event = None

    # ------------------------------------------------------- 常驻交互轮询

    def start_interaction_watch(self, session_id: str, on_event) -> None:
        """常驻后台：轮询 /question 与 /permission，发现新待决就回调 on_event。

        为什么轮询而非 SSE：实测 legacy `/event` 未推 message/question 事件
        （只到 server.connected），而 `GET /question`、`GET /permission` 稳定可靠。
        """
        self.stop_interaction_watch()
        with self._lock:
            self._stop = threading.Event()
            self._session_id = session_id
            self._on_event = on_event
            self._seen_interactions = set()
            self._poller = threading.Thread(target=self._poll_loop,
                                            name="kernel-driver-poll", daemon=True)
            self._poller.start()

    def _emit(self, ev: dict) -> None:
        cb = self._on_event
        if cb is None:
            return
        try:
            cb(ev)
        except Exception:                                              # noqa: BLE001
            pass

    def _poll_loop(self) -> None:
        sid = self._session_id
        while not self._stop.is_set():
            for kind, fetch in (("question", self.client.legacy_questions),
                                ("permission", self.client.legacy_permissions)):
                try:
                    items = fetch()
                except Exception:                                      # noqa: BLE001
                    items = []
                for it in items or []:
                    if not isinstance(it, dict):
                        continue
                    if it.get("sessionID") not in (None, sid):
                        continue
                    rid = it.get("id")
                    if not rid or rid in self._seen_interactions:
                        continue
                    self._seen_interactions.add(rid)
                    self._emit({"kind": kind, "type": kind, "session_id": sid,
                                "text": "", "data": it, "raw": it})
            self._stop.wait(1.0)

    def stop_interaction_watch(self) -> None:
        with self._lock:
            self._stop.set()
            th = self._poller
            self._poller = None
        if th and th.is_alive():
            th.join(timeout=5)

    # -------------------------------------------------------------- 投递

    def prompt(self, session_id: str, text: str, model=None, agent=None,
               timeout: float = 900.0) -> dict:
        """阻塞投递一轮，返回 SessionV1.WithParts。"""
        return self.client.prompt_legacy(session_id, text, model=model,
                                         agent=agent, timeout=timeout)

    def abort(self, session_id: str) -> dict:
        sid = urllib.parse.quote(session_id, safe="")
        return self.client.request("POST", f"/session/{sid}/abort", None, timeout=30)

    # --------------------------------------------------------- 问答/权限

    def pending_questions(self, session_id: str | None = None) -> list:
        try:
            items = self.client.legacy_questions()
        except Exception:                                              # noqa: BLE001
            return []
        if session_id:
            return [q for q in items if isinstance(q, dict)
                    and q.get("sessionID") == session_id]
        return items

    def answer_question(self, request_id: str, answers: list) -> dict:
        """answers: [[label,...], ...]，按问题顺序。"""
        return self.client.legacy_reply_question(request_id, answers)

    def reject_question(self, request_id: str) -> dict:
        return self.client.legacy_reject_question(request_id)

    def pending_permissions(self, session_id: str | None = None) -> list:
        try:
            items = self.client.legacy_permissions()
        except Exception:                                              # noqa: BLE001
            return []
        if session_id:
            return [p for p in items if isinstance(p, dict)
                    and p.get("sessionID") == session_id]
        return items

    def answer_permission(self, request_id: str, reply: str = "once",
                          message: str | None = None) -> dict:
        return self.client.legacy_reply_permission(request_id, reply, message)

    # ------------------------------------------------- 会话消息轮询（工具可见）

    def _fetch_messages(self, session_id: str) -> list:
        """GET /session/:id/message —— 含每条消息的 parts（text/tool/step…）。

        legacy `prompt_legacy` 的**返回值** parts 不含 tool 类型（工具在服务端执行，
        返回只剩 step-start/text/step-finish），故要展示工具调用必须轮询消息。
        """
        sid = urllib.parse.quote(session_id, safe="")
        got = self.client.request("GET", f"/session/{sid}/message", timeout=30)
        if isinstance(got, list):
            return got
        if isinstance(got, dict):
            for key in ("data", "items", "messages"):
                v = got.get(key)
                if isinstance(v, list):
                    return v
        return []

    @staticmethod
    def _iter_parts(messages: list):
        """只产出 assistant 消息的 parts —— 避免把用户自己的输入当正文回显。"""
        for m in messages or []:
            if not isinstance(m, dict):
                continue
            info = m.get("info") if isinstance(m.get("info"), dict) else {}
            if (info.get("role") or m.get("role")) == "user":
                continue
            for p in (m.get("parts") or []):
                if isinstance(p, dict):
                    yield p

    def _emit_part(self, session_id: str, p: dict, seen: set, on_ev) -> None:
        """把一个 V1 part 归一化并去重后回调（tool 按 status 变化多次上报）。"""
        t = p.get("type")
        pid = p.get("id") or p.get("callID") or ""
        if t == "tool":
            state = p.get("state")
            if not isinstance(state, dict):
                state = {}
            status = p.get("status") or state.get("status") or ""
            key = f"{pid}:tool:{status}"
            if key in seen:
                return
            seen.add(key)
            on_ev({"kind": "tool", "type": "tool", "session_id": session_id,
                   "text": p.get("tool") or "", "data": {"tool": p.get("tool"),
                   "status": status, "state": state, "callID": p.get("callID")}, "raw": p})
        elif t == "text":
            if f"{pid}:text" in seen:
                return
            seen.add(f"{pid}:text")
            on_ev({"kind": "text_full", "type": "text", "session_id": session_id,
                   "text": p.get("text") or "", "data": {}, "raw": p})
        elif t == "reasoning":
            if f"{pid}:reason" in seen:
                return
            seen.add(f"{pid}:reason")
            on_ev({"kind": "reasoning", "type": "reasoning", "session_id": session_id,
                   "text": p.get("text") or "", "data": {}, "raw": p})
        elif t == "step-start":
            if f"{pid}:ss" in seen:
                return
            seen.add(f"{pid}:ss")
            on_ev({"kind": "step_start", "type": t, "session_id": session_id,
                   "text": "", "data": p, "raw": p})
        elif t == "step-finish":
            if f"{pid}:sf" in seen:
                return
            seen.add(f"{pid}:sf")
            on_ev({"kind": "step", "type": t, "session_id": session_id,
                   "text": p.get("reason") or "", "data": p, "raw": p})

    # ------------------------------------------------------------ 一轮同步

    def run_turn(self, session_id: str, text: str, on_event=None,
                 timeout: float = 900.0, model=None, agent=None) -> list:
        """同步跑一轮（阻塞；调用方放后台线程）。

        流程：
          1. 起交互轮询线程（发现 question/permission → on_event）；
          2. 阻塞投递 `POST /session/:id/message`；
          3. 把返回 parts 归一化成事件 → on_event；
          4. 收尾 done。
        返回收集到的归一化事件列表（含末尾的 done）。
        """
        events: list = []

        def on_ev(ev: dict) -> None:
            events.append(ev)
            if on_event:
                try:
                    on_event(ev)
                except Exception:                                      # noqa: BLE001
                    pass

        stop = threading.Event()
        seen: set = set()
        seen_parts: set = set()

        # 会话消息轮询：把服务端执行的工具调用暴露为事件（prompt_legacy 返回值不含 tool）
        def poll_parts() -> None:
            while not stop.is_set():
                try:
                    msgs = self._fetch_messages(session_id)
                except Exception:                                      # noqa: BLE001
                    msgs = []
                for p in self._iter_parts(msgs):
                    self._emit_part(session_id, p, seen_parts, on_ev)
                stop.wait(1.0)

        # 交互轮询线程（独立于常驻 watch，绑定本轮生命周期）
        def poller() -> None:
            while not stop.is_set():
                for kind, fetch in (("question", lambda: self.pending_questions(session_id)),
                                    ("permission", lambda: self.pending_permissions(session_id))):
                    try:
                        items = fetch()
                    except Exception:                                  # noqa: BLE001
                        items = []
                    for it in items or []:
                        rid = it.get("id") if isinstance(it, dict) else None
                        if not rid or rid in seen:
                            continue
                        seen.add(rid)
                        on_ev({"kind": kind, "type": kind, "session_id": session_id,
                               "text": "", "data": it, "raw": it})
                stop.wait(1.0)

        pt = threading.Thread(target=poller, name="kernel-driver-turnpoll", daemon=True)
        pt.start()
        mt = threading.Thread(target=poll_parts, name="kernel-driver-parts", daemon=True)
        mt.start()
        out = None
        err = None
        try:
            out = self.client.prompt_legacy(session_id, text, model=model,
                                            agent=agent, timeout=timeout)
        except Exception as e:                                         # noqa: BLE001
            err = e
        finally:
            stop.set()
            pt.join(timeout=3)
            mt.join(timeout=3)

        if out:
            for p in (out.get("parts") or []):
                self._emit_part(session_id, p, seen_parts, on_ev)
        info = (out or {}).get("info") or {}
        on_ev({"kind": "done", "type": "turn", "session_id": session_id,
               "text": info.get("finish") or "",
               "data": {"finish": info.get("finish"),
                        "model": info.get("modelID"), "provider": info.get("providerID"),
                        "error": f"{type(err).__name__}: {err}" if err else None,
                        "text": assistant_text(out) if out else ""},
               "raw": out})
        return events

    def run_turn_async(self, session_id: str, text: str, on_event=None,
                       on_done=None, timeout: float = 900.0, model=None,
                       agent=None) -> threading.Thread:
        def worker() -> None:
            err = None
            try:
                events = self.run_turn(session_id, text, on_event=on_event,
                                       timeout=timeout, model=model, agent=agent)
            except Exception as e:                                     # noqa: BLE001
                events = []
                err = f"{type(e).__name__}: {e}"
            if on_done:
                try:
                    on_done(events, err)
                except Exception:                                      # noqa: BLE001
                    pass

        th = threading.Thread(target=worker, name="kernel-driver-turn", daemon=True)
        th.start()
        return th
