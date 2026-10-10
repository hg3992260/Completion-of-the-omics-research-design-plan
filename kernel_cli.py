# -*- coding: utf-8 -*-
"""`PCLRadiomics.exe kernel ...` —— 内嵌 opencode 内核的控制台配置面。

设计依据（opencode-embedding-plan.md §5）：
    "与 opencode 一致" = 复用同一套文件与语义。
      · session  → 全走内核官方 HTTP API（无本地副本）
      · skill    → 写 opencode 自己的 SKILL.md（/api/skill 只有只读 list）
      · apikey   → 读写 opencode 自己的 auth.json（0600，schema 逐字段对齐）
      · model    → 以 `opencode models` 为准（/api/model 不含按凭据激活的 provider）
      · mcp      → 写 opencode.json 的 mcp 段（key 是 mcp，不是 mcpServers）

用法（冻结产物同样可用）：
    PCLRadiomics.exe kernel status
    PCLRadiomics.exe kernel auth set deepseek sk-xxx
    PCLRadiomics.exe kernel auth import-host
    PCLRadiomics.exe kernel skill add my-skill --file SKILL.md
    PCLRadiomics.exe kernel session list
    PCLRadiomics.exe kernel ui
    PCLRadiomics.exe kernel selftest
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import kernel_client as kc                                              # noqa: E402
import kernel_config as kcfg                                            # noqa: E402


# --------------------------------------------------------------------------- 工具

def _out(obj, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    elif isinstance(obj, (dict, list)):
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(obj)


def _kernel(verbose: bool = False) -> kc.KernelClient:
    return kc.KernelClient(exe=kc.opencode_exe(), verbose=verbose)


def _running_or_start(client: kc.KernelClient, timeout: float = 120.0):
    return client.ensure_running(timeout=timeout)


# --------------------------------------------------------------------- 子命令实现

def cmd_status(args) -> int:
    kstat = kc.status()
    cfg = kcfg.summary()
    info = {
        "binary": {"path": kstat.get("exe"),
                   "exists": bool(kstat.get("exe") and os.path.exists(kstat["exe"])),
                   "size_mb": round(os.path.getsize(kstat["exe"]) / 1024 / 1024, 1)
                   if kstat.get("exe") and os.path.exists(kstat["exe"]) else None},
        "kernel": {"running": kstat.get("running"),
                   "state": kstat.get("state"),
                   "health": kstat.get("health")},
        "config": {"home": cfg["home"], "config_file": cfg["config_file"],
                   "auth_file": cfg["auth_file"], "model": cfg["model"],
                   "mcp": cfg["mcp"], "mcp_timeouts": cfg["mcp_timeouts"]},
        "credentials": cfg["credentials"],
        "skills": cfg["skills"],
        "agents": cfg["agents"],
    }
    if args.json:
        _out(info, True)
        return 0
    b = info["binary"]
    print("== 内核二进制 ==")
    print(f"  路径      {b['path'] or '(未找到)'}")
    if b["size_mb"]:
        print(f"  体积      {b['size_mb']} MB")
    print("== 内核进程 ==")
    k = info["kernel"]
    print(f"  运行中    {'是' if k['running'] else '否'}")
    if k.get("state"):
        print(f"  端点      {k['state'].get('port')}  pid={k['state'].get('pid')}")
    if k.get("health"):
        print(f"  版本      {k['health'].get('version')}")
    print("== 隔离 home ==")
    print(f"  {info['config']['home']}")
    print(f"  配置文件  {info['config']['config_file']}")
    print(f"  凭据文件  {info['config']['auth_file']}")
    print(f"  模型      {info['config']['model'] or '(未设置)'}")
    print(f"  MCP       {info['config']['mcp'] or '(无)'}")
    print("== 凭据（脱敏）==")
    if info["credentials"]:
        for c in info["credentials"]:
            print(f"  {c['provider']:20s} {c['type']:10s} {c['key']}")
    else:
        print("  （无）")
    print("== 技能 ==")
    print(f"  {info['skills'] or '（无）'}")
    return 0


def cmd_start(args) -> int:
    client = _kernel(verbose=args.verbose)
    state = _running_or_start(client, timeout=args.timeout)
    _out({"ok": True, "port": state.port, "pid": state.pid, "version": state.version,
          "ready_seconds": round(client.ready_seconds or 0, 2)}, args.json)
    return 0


def cmd_stop(args) -> int:
    client = _kernel()
    _out({"ok": True, "message": client.stop()}, args.json)
    return 0


def cmd_logs(args) -> int:
    client = _kernel()
    lines = client.log_tail(args.lines)
    if args.json:
        _out({"lines": lines}, True)
    else:
        print("\n".join(lines) if lines else "（无日志）")
    return 0


def cmd_bootlog(args) -> int:
    """GUI 启动联动的持久日志（<kernel_home>/boot.log）。

    「双击后 opencode 没启动」这类问题只有这里能定位 —— 窗口化构建下
    stderr 可能不可用，界面上也未必有反应。
    """
    import kernel_boot as kb
    lines = kb.boot_log_tail(args.lines)
    if args.json:
        _out({"path": kb.boot_log_path(), "lines": lines}, True)
    else:
        print(f"日志文件 {kb.boot_log_path()}")
        print("\n".join(lines) if lines else "（还没有记录 —— 说明联动从未被触发过）")
    return 0


def cmd_ui(args) -> int:
    """在独立控制台窗口里拉起 opencode TUI，attach 到隔离实例（决策 D7）。"""
    client = _kernel(verbose=args.verbose)
    _running_or_start(client, timeout=args.timeout)
    proc = client.spawn_tui(project_dir=args.dir, session_id=args.session,
                            continue_last=args.continue_last,
                            via_powershell=not args.no_powershell)
    _out({"ok": True, "pid": proc.pid,
          "attach": client.state.url,
          "note": "TUI 在新窗口里；关闭该窗口不影响内核进程"}, args.json)
    return 0


# ------------------------------------------------------------------------ session

def cmd_session(args) -> int:
    client = _kernel()
    _running_or_start(client)
    if args.action == "list":
        rows = client.sessions()
        if args.json:
            _out(rows, True)
        else:
            if not rows:
                print("（无会话）")
            for s in rows if isinstance(rows, list) else []:
                if isinstance(s, dict):
                    print(f"  {s.get('id','?'):34s} {str(s.get('title',''))[:50]}")
        return 0
    if args.action == "new":
        got = client.new_session(title=args.title)
        sid = (got.get("data") or got).get("id") if isinstance(got, dict) else None
        _out({"ok": bool(sid), "id": sid}, args.json)
        return 0 if sid else 1
    if args.action == "prompt":
        if not args.session:
            print("需要 --session <id>", file=sys.stderr)
            return 2
        got = client.prompt(args.session, args.text or "你好")
        _out({"ok": True, "admitted": got}, args.json)
        return 0
    if args.action == "interrupt":
        if not args.session:
            print("需要 --session <id>", file=sys.stderr)
            return 2
        _out({"ok": True, "result": client.interrupt(args.session)}, args.json)
        return 0
    if args.action == "events":
        if not args.session:
            print("需要 --session <id>", file=sys.stderr)
            return 2
        # 先订阅再发 prompt，才能拿到事件（P0 教训）
        import threading
        collected: list[dict] = []

        def sub():
            try:
                for ev in client.events(session_id=args.session,
                                        timeout=args.timeout, max_events=args.max_events):
                    collected.append(ev)
            except Exception as e:                                     # noqa: BLE001
                collected.append({"_error": f"{type(e).__name__}: {e}"})

        t = threading.Thread(target=sub, daemon=True)
        t.start()
        import time as _t
        _t.sleep(1.0)
        client.prompt(args.session, args.text or "你好")
        t.join(timeout=args.timeout)
        _out(collected, True)
        return 0
    print(f"未知 session 动作：{args.action}", file=sys.stderr)
    return 2


# -------------------------------------------------------------------------- skill

def cmd_skill(args) -> int:
    if args.action == "list":
        rows = kcfg.list_skills()
        if args.json:
            _out(rows, True)
        else:
            if not rows:
                print("（隔离 home 内无技能）")
            for s in rows:
                print(f"  {s['name']:24s} {s['description'][:60]}")
            print(f"\n技能目录：{kcfg.skill_root()}")
            print("注：内核还会读用户级 ~/.claude/skills 与 ~/.agents/skills（未隔离）")
        return 0
    if args.action == "add":
        if not args.name:
            print("需要 --name", file=sys.stderr)
            return 2
        content = ""
        if args.file:
            with open(args.file, "r", encoding="utf-8") as fh:
                content = fh.read()
        elif args.content:
            content = args.content
        elif not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            print("需要 --file / --content，或从 stdin 读入正文", file=sys.stderr)
            return 2
        got = kcfg.install_skill(args.name, content, args.description or "")
        _out(got, args.json)
        return 0
    if args.action == "remove":
        ok = kcfg.remove_skill(args.name or "")
        _out({"ok": ok, "name": args.name}, args.json)
        return 0 if ok else 1
    if args.action == "path":
        _out({"root": kcfg.skill_root()}, args.json)
        return 0
    print(f"未知 skill 动作：{args.action}", file=sys.stderr)
    return 2


# --------------------------------------------------------------------------- auth

def cmd_auth(args) -> int:
    if args.action == "list":
        rows = kcfg.list_credentials()
        if args.json:
            _out(rows, True)
        else:
            if not rows:
                print("（隔离 home 内无凭据）")
            for c in rows:
                print(f"  {c['provider']:20s} {c['type']:10s} {c['key']}")
            print(f"\n凭据文件：{kcfg.paths()['auth_file']}")
        return 0
    if args.action == "set":
        if not args.provider or not args.key:
            print("需要 --provider 与 --key", file=sys.stderr)
            return 2
        path = kcfg.set_api_key(args.provider, args.key)
        _out({"ok": True, "provider": args.provider, "file": path}, args.json)
        return 0
    if args.action == "remove":
        ok = kcfg.remove_api_key(args.provider or "")
        _out({"ok": ok, "provider": args.provider}, args.json)
        return 0 if ok else 1
    if args.action == "import-host":
        got = kcfg.import_host_llm_key()
        _out(got, args.json)
        return 0 if got.get("ok") else 1
    if args.action == "import-system":
        got = kcfg.import_from_system(args.providers)
        _out(got, args.json)
        return 0 if got.get("ok") else 1
    print(f"未知 auth 动作：{args.action}", file=sys.stderr)
    return 2


# -------------------------------------------------------------------------- model

def cmd_model(args) -> int:
    if args.action == "list":
        # 以 CLI 为准：/api/model 不含按凭据激活的 provider（P0 实测）
        client = _kernel()
        try:
            ids = client.models_cli()
        except Exception:                                              # noqa: BLE001
            _running_or_start(client)
            ids = client.models_cli()
        if args.json:
            _out(ids, True)
        else:
            for i in ids:
                print("  " + i)
        return 0
    if args.action == "set":
        if not args.name:
            print("需要 --name provider/model", file=sys.stderr)
            return 2
        cfg = kcfg.set_model(args.name)
        _out({"ok": True, "model": cfg.get("model")}, args.json)
        return 0
    if args.action == "get":
        _out({"model": kcfg.read_config().get("model")}, args.json)
        return 0
    print(f"未知 model 动作：{args.action}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------- mcp

def cmd_mcp(args) -> int:
    if args.action == "host":
        # 起宿主自己的 MCP 端点，并把地址注册给内核（方向 A）
        import mcp_server
        r = mcp_server.serve_http_in_thread()
        if not r.get("ok"):
            _out({"ok": False, "error": r.get("error")}, args.json)
            return 1
        entry = kcfg.set_mcp_server(kcfg.HOST_MCP_NAME, url=r["url"],
                                   timeout_ms=kcfg.MCP_TIMEOUT_MS)
        _out({"ok": True, "url": r["url"], "tools": mcp_server.tool_count(),
              "config": entry, "note": "需重启内核生效"}, args.json)
        return 0
    if args.action == "remove-host":
        ok = kcfg.remove_mcp_server(kcfg.HOST_MCP_NAME)
        _out({"ok": ok, "name": kcfg.HOST_MCP_NAME}, args.json)
        return 0 if ok else 1
    if args.action == "list":
        client = _kernel()
        try:
            _running_or_start(client)
            out = client.mcp_list()
        except Exception as e:                                         # noqa: BLE001
            out = f"（内核未运行：{e}）"
        if args.json:
            _out({"servers": kcfg.read_config().get("mcp") or {}, "kernel_view": out}, True)
        else:
            print("== 配置里的 MCP server ==")
            print(json.dumps(kcfg.read_config().get("mcp") or {}, ensure_ascii=False, indent=2))
            print("\n== 内核视角（opencode mcp list）==")
            print(out)
        return 0
    if args.action == "status":
        import mcp_server
        _out({"in_process": mcp_server.http_status(),
              "tools": mcp_server.tool_count(),
              "config": kcfg.read_config().get("mcp") or {}}, args.json)
        return 0
    print(f"未知 mcp 动作：{args.action}", file=sys.stderr)
    return 2


# -------------------------------------------------------------------------- 其它

def cmd_config(args) -> int:
    if args.action == "show":
        _out(kcfg.read_config(), True)
        return 0
    if args.action == "path":
        _out(kcfg.paths(), args.json)
        return 0
    if args.action == "set-timeout":
        cfg = kcfg.read_config()
        mcp = dict(cfg.get("mcp") or {})
        for name in list(mcp):
            mcp[name]["timeout"] = args.ms
        cfg["mcp"] = mcp
        kcfg.write_config(cfg)
        _out({"ok": True, "timeout_ms": args.ms}, args.json)
        return 0
    print(f"未知 config 动作：{args.action}", file=sys.stderr)
    return 2


def cmd_boot(args) -> int:
    """一键拉起完整联动：内核 + 宿主 MCP 注册 + 项目 session + 可见终端 TUI。

    与「打开 GUI」时自动发生的动作完全一致，便于在控制台复现/排障。
    """
    import kernel_boot as kb
    boot = kb.instance()
    out = boot.start(args.project)
    if args.json:
        _out({**out, "status": boot.status()}, True)
    else:
        if out.get("ok"):
            print(f"内核     {out.get('url')}")
            print(f"方向 A   {out.get('mcp') or '(未注册)'}")
            print(f"session  {out.get('sessionID') or '(未绑定)'}")
            st = boot.status()
            print(f"TUI pid  {st.get('tui_pid') or '(未打开)'}")
            if not kb.tui_enabled():
                print("提示     已设 PCL_KERNEL_TUI=0，未打开终端界面")
        else:
            print(f"失败：{out.get('error')}")
    return 0 if out.get("ok") else 1


def cmd_project(args) -> int:
    """项目 ↔ opencode session 绑定（GUI 切项目时自动做的同一件事）。"""
    if args.action == "list":
        mapping = kcfg.read_projects_map()
        if args.json:
            _out(mapping, True)
        else:
            print(f"映射文件 {kcfg.projects_map_file()}")
            if not mapping:
                print("（空）")
            for name, entry in sorted(mapping.items()):
                sid = entry.get("sessionID") if isinstance(entry, dict) else entry
                print(f"  {name:32s} → {sid}")
        return 0

    if args.action == "unbind":
        ok = kcfg.unbind_project_session(args.name or "")
        _out({"ok": ok, "project": args.name}, args.json)
        return 0 if ok else 1

    # ensure / switch 都需要内核在跑
    import kernel_boot as kb
    boot = kb.instance()
    if not (boot._client and boot._client.state):
        # 只起内核，不弹 TUI（除非是 switch）
        import kernel_client as _kc
        boot._client = boot._client or _kc.KernelClient(exe=args.exe or _kc.opencode_exe())
        boot._client.ensure_running(timeout=args.timeout)
        boot._mcp_url = boot._ensure_host_mcp()

    relaunch = (args.action == "switch") and not args.no_tui
    got = boot.ensure_project_session(args.name or "未命名项目", relaunch_tui=relaunch)
    _out({"ok": True, **got, "relaunch_tui": relaunch}, args.json)
    return 0


def cmd_selftest(args) -> int:
    """不打网络、不依赖密钥的自检：路径 / 二进制 / 配置 / 技能 / MCP 端点。"""
    ok = True
    print("== 1. 路径与隔离 home ==")
    p = kcfg.paths()
    for k in ("home", "data", "config", "auth_file", "config_file", "skill_dir"):
        print(f"  {k:12s} {p[k]}")
    print("== 2. 内核二进制 ==")
    exe = kc.opencode_exe()
    if exe and os.path.exists(exe):
        print(f"  OK  {exe}  {round(os.path.getsize(exe)/1024/1024,1)} MB")
    else:
        print("  FAIL 未找到 opencode.exe（设置 PCL_OPENCODE_EXE 或放到 <app_home>/opencode/）")
        ok = False
    print("== 3. 配置文件 ==")
    cfg = kcfg.read_config()
    print(f"  {p['config_file']}  keys={sorted(cfg.keys())}")
    mcp = cfg.get("mcp") or {}
    if mcp:
        for name, spec in mcp.items():
            t = (spec or {}).get("timeout")
            flag = "OK" if (t or 0) >= 60_000 else "WARN timeout 太小（默认 5s 会让长任务失败）"
            print(f"    {name}: {spec.get('type')} timeout={t}  {flag}")
    else:
        print("    （未注册任何 MCP server —— 内核拿不到宿主的领域工具）")
    print("== 4. 技能 ==")
    print(f"  隔离 home 内 {len(kcfg.list_skills())} 个；目录 {kcfg.skill_root()}")
    print("== 5. 凭据（脱敏）==")
    creds = kcfg.list_credentials()
    print(f"  {len(creds)} 个：{[c['provider'] for c in creds] or '（无）'}")
    print("== 6. 宿主 MCP 端点（进程内）==")
    try:
        import mcp_server
        print(f"  工具数 {mcp_server.tool_count()}")
        st = mcp_server.http_status()
        print(f"  端点 {st.get('url') or '(未启动)'} serving={st.get('serving')}")
    except Exception as e:                                             # noqa: BLE001
        print(f"  FAIL 导入 mcp_server：{type(e).__name__}: {e}")
        ok = False
    print("\n结论：" + ("通过" if ok else "存在问题"))
    return 0 if ok else 1


# --------------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="kernel",
                                 description="内嵌 opencode 内核的控制台配置面")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("status", help="总览：二进制 / 进程 / 配置 / 凭据 / 技能")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_status)

    for name, fn, help_text in (("start", cmd_start, "启动内核"),
                                ("stop", cmd_stop, "停止内核")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--json", action="store_true")
        if name == "start":
            p.add_argument("--timeout", type=float, default=120.0)
            p.add_argument("--verbose", action="store_true")
        p.set_defaults(fn=fn)

    p = sub.add_parser("logs", help="内核日志尾部")
    p.add_argument("-n", "--lines", type=int, default=60)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_logs)

    p = sub.add_parser("bootlog", help="GUI 启动联动的持久日志（排查「opencode 没启动」）")
    p.add_argument("-n", "--lines", type=int, default=60)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_bootlog)

    p = sub.add_parser("ui", help="在独立控制台窗口里拉起 opencode TUI（attach 到隔离实例）")
    p.add_argument("--dir", default=None, help="TUI 的工作目录")
    p.add_argument("--session", default=None)
    p.add_argument("--continue", dest="continue_last", action="store_true")
    p.add_argument("--no-powershell", action="store_true", help="直接 spawn，不套 PowerShell")
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_ui)

    p = sub.add_parser("session", help="会话管理")
    p.add_argument("action", choices=["list", "new", "prompt", "interrupt", "events"])
    p.add_argument("--session", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--text", default=None)
    p.add_argument("--max-events", type=int, default=30)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_session)

    p = sub.add_parser("skill", help="技能管理（写 opencode 自己的 SKILL.md）")
    p.add_argument("action", choices=["list", "add", "remove", "path"])
    p.add_argument("--name", default=None)
    p.add_argument("--file", default=None)
    p.add_argument("--content", default=None)
    p.add_argument("--description", default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_skill)

    p = sub.add_parser("auth", help="API Key / 凭据管理（写 opencode 自己的 auth.json）")
    p.add_argument("action", choices=["list", "set", "remove", "import-host", "import-system"])
    p.add_argument("--provider", default=None)
    p.add_argument("--key", default=None)
    p.add_argument("--providers", nargs="*", default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_auth)

    p = sub.add_parser("model", help="模型（以 opencode models CLI 为准）")
    p.add_argument("action", choices=["list", "set", "get"])
    p.add_argument("--name", default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_model)

    p = sub.add_parser("mcp", help="MCP 服务（方向 A：把宿主 21 个工具暴露给内核）")
    p.add_argument("action", choices=["host", "remove-host", "list", "status"])
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_mcp)

    p = sub.add_parser("config", help="内核配置")
    p.add_argument("action", choices=["show", "path", "set-timeout"])
    p.add_argument("--ms", type=int, default=kcfg.MCP_TIMEOUT_MS)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_config)

    p = sub.add_parser("boot", help="一键拉起完整联动（内核 + 宿主 MCP + 项目 session + 终端 TUI）")
    p.add_argument("--project", default=None, help="要绑定的项目名")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_boot)

    p = sub.add_parser("project", help="项目 ↔ opencode session 绑定")
    p.add_argument("action", choices=["list", "ensure", "switch", "unbind"])
    p.add_argument("--name", default=None)
    p.add_argument("--exe", default=None)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--no-tui", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_project)

    p = sub.add_parser("selftest", help="离线自检（路径/二进制/配置/技能/MCP 端点）")
    p.set_defaults(fn=cmd_selftest)
    return ap


def main(argv: list | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(list(sys.argv[1:] if argv is None else argv))
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
