# -*- coding: utf-8 -*-
"""P0 验收：内嵌 opencode 内核的可行性 + 两个决定性数字。

跑法：
    python _test_kernel.py                 # 自动找构建产物
    python _test_kernel.py --exe <path>    # 指定 opencode.exe
    python _test_kernel.py --skip-llm      # 跳过需要真实凭据的对话步骤

覆盖：
    [0] 二进制定位与体积      —— 决定 D5「打进主 exe」后 onedir 会变成多大
    [1] 隔离 home 验证        —— 确认没写用户真实的 ~/.local/share/opencode
    [2] 冷启动               —— spawn → 打印端口 → health 通过（决定懒启动体验）
    [3] HTTP 控制面          —— 建会话 / 列会话
    [4] 模型目录             —— 列出内核可见的 provider/model
    [5] 凭据导入             —— 从宿主凭据链写隔离 auth.json（§6.3①）
    [6] 流式对话             —— opencode run --format json（契约明确，可断言）
    [7] SSE schema 探测      —— 为 P1 摸清 /api/session/:id/event 的事件形状
    [8] 优雅停止 + 孤儿检查

设计原则：需要真实凭据的步骤失败时标记 SKIP 并给出原因，不让整个 P0 失败 ——
体积与冷启动这两个数字才是 P0 的硬产出。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import kernel_client as kc                                              # noqa: E402

#: opencode 仓库与本项目同级（P0 期间用构建产物；P1 起改为随包分发）
SIBLING_BUILD = os.path.join(
    os.path.dirname(HERE), "opencode-dev", "opencode-dev",
    "packages", "opencode", "dist", "opencode-windows-x64", "bin", "opencode.exe",
)

RESULTS: list[tuple[str, str, str]] = []


def record(step: str, status: str, detail: str = "") -> None:
    RESULTS.append((step, status, detail))
    print(f"  [{status}] {step}" + (f" —— {detail}" if detail else ""))


def hr(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def find_exe(cli: str | None) -> str | None:
    for cand in (cli, os.environ.get("PCL_OPENCODE_EXE"), SIBLING_BUILD,
                 kc.opencode_exe()):
        if cand and os.path.exists(cand):
            return cand
    return None


# --------------------------------------------------------------------------- 步骤

def step0_binary(exe: str | None) -> str | None:
    hr("[0] 二进制定位与体积")
    if not exe:
        record("定位 opencode.exe", "FAIL",
               "未找到。构建：cd packages/opencode && bun run script/build.ts "
               "--single --skip-embed-web-ui")
        return None
    size_mb = os.path.getsize(exe) / 1024 / 1024
    record("定位 opencode.exe", "OK", exe)
    record("二进制体积", "OK", f"{size_mb:.1f} MB  ← D5 的关键数字")
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True,
                             timeout=60).stdout.strip()
        record("--version", "OK", out)
    except Exception as e:                                             # noqa: BLE001
        record("--version", "FAIL", f"{type(e).__name__}: {e}")
    return exe


def step1_isolation() -> dict:
    hr("[1] 隔离 home 验证")
    real_home = os.path.expanduser("~")
    real_data = os.path.join(real_home, ".local", "share", "opencode")
    before = os.path.getmtime(real_data) if os.path.exists(real_data) else None
    record("用户真实内核目录", "INFO",
           f"{real_data}（{'存在' if before else '不存在'}）")

    paths = kc.ensure_home_layout()
    record("隔离 home", "OK", paths["home"])
    for key in ("data", "config", "state", "cache"):
        record(f"  {key}", "OK", paths[key])

    return {"real_data": real_data, "before_mtime": before, "paths": paths}


def step1b_verify_isolation(ctx: dict) -> None:
    real_data = ctx["real_data"]
    after = os.path.getmtime(real_data) if os.path.exists(real_data) else None
    if ctx["before_mtime"] != after:
        record("隔离校验", "WARN",
               f"用户真实目录 mtime 变化了（{ctx['before_mtime']} → {after}）"
               " —— 需要排查是否有未覆盖的写入路径")
    else:
        record("隔离校验", "OK", "用户真实内核目录未被触碰")

    expected = ctx["paths"]["data"]
    if os.path.isdir(expected):
        record("隔离 data 已建", "OK", expected)
    else:
        record("隔离 data 已建", "WARN", f"未出现 {expected}")


def step2_coldstart(exe: str, timeout: float) -> kc.KernelClient | None:
    hr("[2] 冷启动（spawn → 端口 → health）")
    client = kc.KernelClient(exe=exe, verbose=True)
    try:
        t0 = time.time()
        state = client.ensure_running(timeout=timeout)
        total = time.time() - t0
        record("内核就绪", "OK", state.url)
        record("  到端口就绪", "OK", f"{client.listen_seconds:.2f}s"
               if client.listen_seconds is not None else "n/a")
        record("  到 health 通过", "OK",
               f"{client.ready_seconds:.2f}s  ← 懒启动的关键数字"
               if client.ready_seconds is not None else f"{total:.2f}s")
        record("  内核版本", "OK", state.version or "(未报告)")
        return client
    except Exception as e:                                             # noqa: BLE001
        record("内核就绪", "FAIL", f"{type(e).__name__}: {e}")
        for line in client.logs()[-15:]:
            print(f"      | {line}")
        return None


def step3_http(client: kc.KernelClient) -> str | None:
    hr("[3] HTTP 控制面")
    try:
        sessions = client.sessions()
        n = len(sessions) if isinstance(sessions, list) else "?"
        record("GET /api/session", "OK", f"{n} 个会话")
    except Exception as e:                                             # noqa: BLE001
        record("GET /api/session", "FAIL", f"{type(e).__name__}: {e}")

    try:
        created = client.new_session(title="P0 探针会话")
        sid = (created.get("data") or created).get("id") if isinstance(created, dict) else None
        record("POST /api/session", "OK" if sid else "WARN", f"id={sid}")
        return sid
    except Exception as e:                                             # noqa: BLE001
        record("POST /api/session", "FAIL", f"{type(e).__name__}: {e}")
        return None


def step4_models(client: kc.KernelClient, exe: str) -> list[str]:
    """模型目录。

    ⚠️ P0 实测发现：`GET /api/model` 只列出 opencode 自有 provider（38 个
    opencode/*），而 CLI `opencode models` 才能看到 deepseek/* 等按凭据激活的
    provider。因此控制台的模型选择器不能只依赖 /api/model。
    """
    hr("[4] 模型目录")
    http_ids: list[str] = []
    try:
        got = client.request("GET", "/api/model")
        data = got.get("data") if isinstance(got, dict) else got
        for item in (data or []):
            if isinstance(item, dict):
                pid = item.get("providerID") or item.get("provider")
                mid = item.get("modelID") or item.get("id") or item.get("model")
                http_ids.append(f"{pid}/{mid}" if pid and mid else str(mid or pid))
        record("GET /api/model", "OK", f"{len(http_ids)} 个（HTTP 视角）")
    except Exception as e:                                             # noqa: BLE001
        record("GET /api/model", "FAIL", f"{type(e).__name__}: {e}")

    cli_ids: list[str] = []
    try:
        st = client.state
        r = subprocess.run([exe, "models"], env=kc.kernel_env(st.password if st else None),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
        for line in (r.stdout or "").splitlines():
            line = line.strip()
            if "/" in line and " " not in line:
                cli_ids.append(line)
        record("opencode models", "OK", f"{len(cli_ids)} 个（CLI 视角，含按凭据激活的 provider）")
    except Exception as e:                                             # noqa: BLE001
        record("opencode models", "FAIL", f"{type(e).__name__}: {e}")

    merged = list(dict.fromkeys(cli_ids + http_ids))
    interesting = [m for m in merged if not m.startswith("opencode/")]
    print(f"      非 opencode 自有 provider：{interesting[:10] or '(无)'}")
    return merged


def step5_import_credential() -> tuple[bool, str, str]:
    """从宿主凭据链导入一个 api key 到隔离 auth.json（§6.3①）。

    返回 (是否有可用密钥, provider id, 宿主配置的模型名)。
    """
    hr("[5] 凭据导入（隔离 auth.json）")
    try:
        from llm_client import load_config, read_credential
    except Exception as e:                                             # noqa: BLE001
        record("载入 llm_client", "FAIL", f"{type(e).__name__}: {e}")
        return False, "", ""

    cfg = load_config()
    key = cfg.get("api_key") or ""
    source = cfg.get("key_source") or "none"
    host_model = cfg.get("model") or ""
    if not key:
        record("取得密钥", "SKIP", "宿主凭据链没有可用密钥")
        return False, "", host_model

    # 判定 provider id：宿主默认端点是 DeepSeek 官方
    base = (cfg.get("base_url") or "").lower()
    provider = "deepseek" if "deepseek" in base else "openai-compatible"
    record("宿主密钥", "OK",
           f"来源={source} provider={provider} 端点={cfg.get('base_url')} 模型={host_model}")

    auth_path = os.path.join(kc.kernel_home(), "data", "opencode", "auth.json")
    os.makedirs(os.path.dirname(auth_path), exist_ok=True)
    try:
        existing = {}
        if os.path.exists(auth_path):
            with open(auth_path, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
        existing[provider] = {"type": "api", "key": key}
        with open(auth_path, "w", encoding="utf-8") as fh:
            json.dump(existing, fh, ensure_ascii=False, indent=2)
        os.chmod(auth_path, 0o600)
        record("写入隔离 auth.json", "OK", auth_path)
        return True, provider, host_model
    except Exception as e:                                             # noqa: BLE001
        record("写入隔离 auth.json", "FAIL", f"{type(e).__name__}: {e}")
        return False, provider, host_model


def step6_stream(client: kc.KernelClient, model: str | None, enabled: bool,
                 session_id: str | None) -> None:
    hr("[6] 流式对话（opencode run --format json）")
    if not enabled:
        record("流式对话", "SKIP", "凭据不可用（见 [5]）")
        return
    prompt = "只回答两个字：就绪"
    try:
        t0 = time.time()
        events = client.run_once(prompt, session_id=session_id, model=model, timeout=300)
        elapsed = time.time() - t0
        text = _extract_text(events)
        record("run --format json", "OK",
               f"{len(events)} 个事件 / {elapsed:.1f}s")
        record("  模型输出", "OK" if text else "WARN", repr(text[:120]))
    except Exception as e:                                             # noqa: BLE001
        record("run --format json", "FAIL", f"{type(e).__name__}: {e}")


def _extract_text(events: list) -> str:
    """从 run --format json 的事件流里尽力抽出助手文本。"""
    chunks: list[str] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        for key in ("text", "content", "delta"):
            val = ev.get(key)
            if isinstance(val, str):
                chunks.append(val)
            elif isinstance(val, dict):
                for sub in ("text", "content"):
                    if isinstance(val.get(sub), str):
                        chunks.append(val[sub])
        part = ev.get("part")
        if isinstance(part, dict):
            for key in ("text", "content"):
                if isinstance(part.get(key), str):
                    chunks.append(part[key])
    return "".join(chunks).strip()


def step7_sse_probe(client: kc.KernelClient, session_id: str | None) -> None:
    """SSE 端点连通性探测。

    P0 只验证"能不能连上"，不验证事件形状 ——
    空闲会话没有事件，阻塞读会在 timeout 后抛 TimeoutError，这是客户端行为
    而非端点故障。完整的 subscribe-then-prompt + 事件 schema 发现放到 P1。
    """
    hr("[7] SSE 端点连通性（完整 schema 发现留待 P1）")
    if not session_id:
        record("SSE 探测", "SKIP", "没有会话 id")
        return
    try:
        for _ev in client.events(session_id=session_id, timeout=6, max_events=1):
            record("订阅 session 事件", "OK", "连上并收到事件")
            return
        record("订阅 session 事件", "OK", "连上（6s 内无事件，空闲会话属正常）")
    except Exception as e:                                             # noqa: BLE001
        name = type(e).__name__
        if "timed out" in str(e).lower() or name == "TimeoutError":
            record("订阅 session 事件", "OK",
                   "连上（空闲无事件导致读超时，属预期；P1 需改 subscribe-then-prompt）")
        else:
            record("订阅 session 事件", "FAIL", f"{name}: {e}")


def step8_stop(client: kc.KernelClient) -> None:
    hr("[8] 停止与孤儿检查")
    pid = client.state.pid if client.state else None
    try:
        msg = client.stop()
        record("优雅停止", "OK", msg)
    except Exception as e:                                             # noqa: BLE001
        record("优雅停止", "FAIL", f"{type(e).__name__}: {e}")
    if pid:
        alive = kc.KernelClient._pid_alive(pid)
        record("孤儿检查", "FAIL" if alive else "OK",
               f"pid={pid} {'仍在运行' if alive else '已退出'}")


# --------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=None, help="opencode 可执行文件路径")
    ap.add_argument("--timeout", type=float, default=120.0, help="冷启动超时（秒）")
    ap.add_argument("--skip-llm", action="store_true", help="跳过需要凭据的对话步骤")
    ap.add_argument("--model", default=None, help="覆盖对话所用模型（provider/model）")
    args = ap.parse_args()

    print("P0 验收：opencode 内核可行性与决定性数字")
    print(f"内核 home = {kc.kernel_home()}")

    exe = find_exe(args.exe)
    exe = step0_binary(exe)
    if not exe:
        _summary()
        return 1

    iso = step1_isolation()
    client = step2_coldstart(exe, args.timeout)
    if client:
        try:
            sid = step3_http(client)
            models = step4_models(client, exe)
            has_key, provider, host_model = step5_import_credential()

            model = args.model
            if not model:
                # 优先用宿主自己的模型名（同一端点、已验证可用）
                candidates = [f"{provider}/{host_model}"] if provider and host_model else []
                candidates += [m for m in models if provider and m.startswith(f"{provider}/")]
                candidates += [m for m in models if not m.startswith("opencode/")]
                candidates += models
                model = next((m for m in candidates if m), None)
            record("选用模型", "INFO", str(model))

            step6_stream(client, model, has_key and not args.skip_llm, sid)
            step7_sse_probe(client, sid)
        finally:
            step1b_verify_isolation(iso)
            step8_stop(client)
    else:
        step1b_verify_isolation(iso)

    _summary()
    hard_fail = [r for r in RESULTS if r[1] == "FAIL"]
    return 1 if hard_fail else 0


def _summary() -> None:
    hr("汇总")
    for step, status, detail in RESULTS:
        print(f"  {status:4s}  {step}")
    counts: dict[str, int] = {}
    for _, status, _ in RESULTS:
        counts[status] = counts.get(status, 0) + 1
    print("\n  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    sys.exit(main())
