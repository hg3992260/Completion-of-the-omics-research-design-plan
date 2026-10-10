# -*- coding: utf-8 -*-
"""P3 验收（方向 A）：内核能否发现并调用宿主的 21 个 MCP 领域工具。

架构（plan §2.1 方向 A）：
    宿主 GUI 进程  ──MCP(streamable-http)──►  内嵌 opencode 内核
    内核是 MCP 客户端，宿主是 MCP 服务端。

本测试把这条链路完整跑通：
    [1] 宿主进程内起 MCP HTTP 端点（21 个工具）
    [2] 把该端点写进内核配置的 mcp 段（type:"remote" + 调大 timeout）
    [3] 导入凭据 + 指定模型
    [4] 冷启动内核（配置在启动时读取）
    [5] `opencode mcp list` 确认宿主 server 已连接
    [6] 内核日志的 init count 应 >= 18 + 21
    [7] 真实发一句会触发宿主工具的提示，确认出现工具调用

用法：
    python _test_direction_a.py
    python _test_direction_a.py --model deepseek/deepseek-flash
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import kernel_client as kc                                              # noqa: E402
import kernel_config as kcfg                                            # noqa: E402
import mcp_server                                                       # noqa: E402

RESULTS: list[tuple[str, str, str]] = []


def record(step: str, status: str, detail: str = "") -> None:
    RESULTS.append((step, status, detail))
    print(f"  [{status}] {step}" + (f" —— {detail}" if detail else ""))


def hr(t: str) -> None:
    print("\n" + "=" * 72)
    print(t)
    print("=" * 72)


#: 宿主工具被内核命名后的样子：sanitize(server) + "_" + sanitize(tool)
EXPECTED_HOST_TOOL = "radiomics_workbench_list_stages"


def step1_host_endpoint() -> str | None:
    hr("[1] 宿主进程内起 MCP HTTP 端点")
    n = mcp_server.tool_count()
    record("已注册工具数", "OK" if n == 21 else "WARN", f"{n} 个")
    r = mcp_server.serve_http_in_thread()
    if not r.get("ok"):
        record("起 MCP 端点", "FAIL", str(r.get("error")))
        return None
    record("起 MCP 端点", "OK", f"{r['url']}（{'复用' if r.get('already') else '新建'}）")
    return r["url"]


def step2_config(url: str) -> None:
    hr("[2] 把宿主 MCP 写进内核配置")
    entry = kcfg.set_mcp_server(kcfg.HOST_MCP_NAME, url=url,
                               timeout_ms=kcfg.MCP_TIMEOUT_MS)
    record("mcp 段写入", "OK", json.dumps(entry, ensure_ascii=False))
    cfg = kcfg.read_config()
    if "mcp" not in cfg:
        record("配置校验", "FAIL", "opencode.json 里没有 mcp 段")
    elif kcfg.HOST_MCP_NAME not in cfg["mcp"]:
        record("配置校验", "FAIL", f"缺少 {kcfg.HOST_MCP_NAME}")
    else:
        record("配置校验", "OK", f"key=mcp（不是 mcpServers），timeout={entry['timeout']}ms")


def step3_credentials(model: str | None) -> str | None:
    hr("[3] 凭据与模型")
    r = kcfg.import_host_llm_key()
    if not r.get("ok"):
        record("导入宿主密钥", "FAIL", str(r.get("reason")))
        return None
    record("导入宿主密钥", "OK",
           f"provider={r['provider']} 来源={r['source']} 端点={r['endpoint']}")
    chosen = model or f"{r['provider']}/{r.get('model') or 'deepseek-flash'}"
    kcfg.set_model(chosen)
    record("写顶层 model", "OK", chosen)
    return chosen


def step4_kernel(exe: str, timeout: float) -> kc.KernelClient | None:
    hr("[4] 冷启动内核（配置在启动时读取）")
    # 配置改动必须重启内核才生效
    stale = kc.KernelClient(exe=exe)
    try:
        stale.cleanup_stale()
    except Exception:                                                  # noqa: BLE001
        pass
    client = kc.KernelClient(exe=exe, verbose=False)
    try:
        state = client.ensure_running(timeout=timeout)
        record("内核就绪", "OK", f"{state.url} ready={client.ready_seconds:.2f}s")
        return client
    except Exception as e:                                             # noqa: BLE001
        record("内核就绪", "FAIL", f"{type(e).__name__}: {e}")
        return None


def step5_mcp_connected(client: kc.KernelClient) -> bool:
    hr("[5] opencode mcp list（宿主 server 是否连上）")
    try:
        out = client.mcp_list()
    except Exception as e:                                             # noqa: BLE001
        record("opencode mcp list", "FAIL", f"{type(e).__name__}: {e}")
        return False
    print("      " + "\n      ".join(out.splitlines()[:20]))
    low = out.lower()
    hit = kcfg.HOST_MCP_NAME.split("-")[0] in low or kcfg.HOST_MCP_NAME in low
    connected = ("connected" in low) or ("✓" in out) or ("ready" in low)
    record("宿主 server 出现", "OK" if hit else "FAIL",
           kcfg.HOST_MCP_NAME)
    record("状态为已连接", "OK" if (hit and connected) else "WARN",
           "见上方原始输出")
    return bool(hit)


def step6_tool_count(client: kc.KernelClient) -> bool:
    hr("[6] 内核日志的 init count（仅内置工具）")
    tail = client.log_tail(200)
    counts = []
    for line in tail:
        if "message=init count=" in line:
            try:
                counts.append(int(line.split("count=")[1].split()[0]))
            except Exception:                                          # noqa: BLE001
                pass
    if not counts:
        record("init count", "WARN", "日志里没找到（可能还没跑过一轮）")
        return False
    last = counts[-1]
    # ⚠️ 实测结论：init count 只统计**内置**工具（18 个），MCP 工具不计入。
    #    因此这里不能断言 39。MCP 工具是否可用，真正的证据是
    #    step5 的 connected 与 step7 的 tool_use 事件 / 宿主侧 CallToolRequest。
    record("init count（内置）", "OK" if last >= 18 else "WARN",
           f"{last} —— 注意：MCP 工具不计入此数，与宿主 21 个工具无关")
    return True


def step7_real_tool_call(client: kc.KernelClient, model: str) -> bool:
    hr("[7] 真实调用宿主工具")
    prompt = (f"请调用工具 {EXPECTED_HOST_TOOL}（不要自己编内容），"
              f"然后只回答第 1 阶段的标题是什么。")
    try:
        t0 = time.time()
        events = client.run_once(prompt, model=model, timeout=420)
        elapsed = time.time() - t0
    except Exception as e:                                             # noqa: BLE001
        record("run", "FAIL", f"{type(e).__name__}: {e}")
        return False

    types: dict[str, int] = {}
    tool_names: list[str] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        t = str(ev.get("type") or "?")
        types[t] = types.get(t, 0) + 1
        part = ev.get("part") if isinstance(ev.get("part"), dict) else {}
        blob = json.dumps(ev, ensure_ascii=False)
        for cand in (EXPECTED_HOST_TOOL, "list_stages", "radiomics_workbench"):
            if cand in blob and cand not in tool_names:
                tool_names.append(cand)

    record("run 事件", "OK", f"{len(events)} 个 / {elapsed:.1f}s / types={types}")
    if tool_names:
        record("命中宿主工具", "OK", ", ".join(tool_names))
    else:
        record("命中宿主工具", "WARN", f"事件里没看到 {EXPECTED_HOST_TOOL}")
    text = "".join(
        (ev.get("part") or {}).get("text", "")
        for ev in events
        if isinstance(ev, dict) and isinstance(ev.get("part"), dict)
        and ev["part"].get("type") == "text"
    ).strip()
    if text:
        record("模型答复", "OK", text[:160])
    return bool(tool_names)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()

    print("方向 A 验收：内核调用宿主的 21 个 MCP 领域工具")
    print(f"内核 home = {kc.kernel_home()}")

    exe = args.exe or kc.opencode_exe()
    if not exe or not os.path.exists(exe):
        record("定位 opencode.exe", "FAIL", "未找到")
        _summary()
        return 1
    record("定位 opencode.exe", "OK", exe)

    url = step1_host_endpoint()
    if not url:
        _summary()
        return 1
    step2_config(url)
    model = step3_credentials(args.model)
    if not model:
        _summary()
        return 1

    client = step4_kernel(exe, args.timeout)
    if client:
        try:
            step5_mcp_connected(client)
            step6_tool_count(client)
            step7_real_tool_call(client, model)
        finally:
            try:
                client.stop()
                record("停止内核", "OK", "已停止")
            except Exception as e:                                     # noqa: BLE001
                record("停止内核", "WARN", str(e))

    _summary()
    return 1 if any(r[1] == "FAIL" for r in RESULTS) else 0


def _summary() -> None:
    hr("汇总")
    for step, status, _ in RESULTS:
        print(f"  {status:4s}  {step}")
    counts: dict[str, int] = {}
    for _, s, _ in RESULTS:
        counts[s] = counts.get(s, 0) + 1
    print("\n  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    sys.exit(main())
