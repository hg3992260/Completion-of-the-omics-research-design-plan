# -*- coding: utf-8 -*-
"""统一入口：一个可执行文件承载 界面 / MCP 服务 / 推理 API 三种模式。

    pclradiomics.exe gui                    启动图形界面（工作台 + 管线视图）
    pclradiomics.exe mcp                    以 stdio 提供 MCP（供 DSH / Claude Desktop）
    pclradiomics.exe mcp --http             以 streamable-http 提供 MCP（--port 8765）
    pclradiomics.exe api                    以 OpenAI 兼容 API 提供服务（--port 8788）
    pclradiomics.exe stages                 打印十阶段标准流程（纯文本，便于脚本调用）
    pclradiomics.exe projects               列出项目与完成度
    pclradiomics.exe paths                  打印路径解析（排查冻结后的读写位置）
    pclradiomics.exe check                  自检：依赖、凭据、模型连通性

不传子命令时按 exe 名判断：含 "服务"/"serve" 则进服务模式，否则进界面。
"""

from __future__ import annotations

import os
import subprocess
import json
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _ensure_streams() -> str:
    """接管标准流：管道（MCP）→ 父控制台（终端里手敲）→ devnull（双击图形界面）。

    实现见 win_stdio.py；返回接管方式，便于 check 排查。
    """
    try:
        from win_stdio import setup_stdio
        return setup_stdio()
    except Exception:                                              # noqa: BLE001
        for name in ("stdout", "stderr"):
            if getattr(sys, name, None) is None:
                try:
                    setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
                except Exception:                                  # noqa: BLE001
                    pass
        return "fallback"


def _crash_log(exc: BaseException) -> str:
    """把崩溃写到 exe 同级 error.log（windowed 构建没有控制台可看）。"""
    import traceback
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        from app_paths import data_path
        path = data_path("error.log")
    except Exception:                                              # noqa: BLE001
        path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "error.log")
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n===== " + time.strftime("%Y-%m-%d %H:%M:%S") + " =====\n" + text)
    except Exception:                                              # noqa: BLE001
        pass
    return path


def _alert(msg: str) -> None:
    """无控制台时用系统弹窗提示（不依赖 Qt）。"""
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, "PCL-Radiomics 启动失败", 0x10)
        elif sys.platform == "darwin":                             # macOS 用系统弹窗
            subprocess.run(["osascript", "-e",
                            f'display dialog {json.dumps(msg)} with title '
                            f'"PCL-Radiomics 启动失败" buttons {{"好"}} default button 1'],
                           capture_output=True)
    except Exception:                                              # noqa: BLE001
        pass


def _utf8_console() -> None:
    """统一 UTF-8 输出：冻结后控制台代码页可能是 GBK，中文会乱码或抛 UnicodeEncodeError。

    只改文本层编码，不动 .buffer —— stdio MCP 的二进制管道不受影响。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                          # noqa: BLE001
            pass


def _hide_own_console() -> None:
    """单 exe 方案：为让 stdio MCP 有真实 stdout，exe 必须以 console 子系统编译；
    于是图形模式需要把控制台窗口藏起来。

    只在本进程独占这个控制台时才隐藏 —— 如果是用户在 cmd 里敲命令启动的
    （控制台有多个进程），就去动它，免得把人家终端藏了。
    """
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        u32 = ctypes.windll.user32
        hwnd = k32.GetConsoleWindow()
        if not hwnd:
            return
        buf = (ctypes.c_uint * 8)()
        owner = k32.GetConsoleProcessList(buf, 8)
        if owner != 1:
            return
        u32.ShowWindow(hwnd, 0)                      # SW_HIDE
    except Exception:                                          # noqa: BLE001
        pass


def _banner() -> None:
    sys.stderr.write("组学研究设计工作台 · PCL-Radiomics\n")


def cmd_gui(argv: list) -> int:
    import design_studio
    return design_studio.main(["design_studio"] + argv)


def cmd_mcp(argv: list) -> int:
    import mcp_server
    sys.argv = ["mcp_server"] + argv
    mcp_server.main()
    return 0


def cmd_api(argv: list) -> int:
    import api_server
    sys.argv = ["api_server"] + argv
    api_server.main()
    return 0


def cmd_stages(argv: list) -> int:
    from stages_data import STAGES
    for s in STAGES:
        print(f"{s['id']:02d} {s['title']}　[{s['spec']}]")
        print(f"    目标：{s['goal']}")
        print(f"    必做：{'；'.join(s['actions'])}")
        print(f"    必报：{'；'.join(s['reports'])}")
    return 0


def cmd_projects(argv: list) -> int:
    from design_agent import Project
    rows = Project.list_all()
    if not rows:
        print("（暂无项目）")
    for m in rows:
        print(f"{m['name']:28s} {m['done']}/10 阶段  更新 {m['updated']}  {m['size_kb']} KB")
    print(f"\n目录：{Project.dir()}")
    return 0


def cmd_paths(argv: list) -> int:
    from app_paths import describe
    d = describe()
    print(f"冻结运行     {d['frozen']}")
    if d["frozen"]:
        print(f"可执行文件   {d['executable']}")
        print(f"内置资源目录 {d['bundle']}")
    print(f"数据目录     {d['app_home']}")
    return 0


def cmd_check(argv: list) -> int:
    from app_paths import resource_path, data_path, app_home
    from llm_client import LLMClient, load_config, mask
    ok = True
    print("== 路径 ==")
    print(f"  数据目录   {app_home()}")
    for f in ("theme_tech.json", "logo_icon.ico", "logo_badge.png", "logo_banner.png"):
        p = resource_path(f)
        print(f"  {f:18s} {'OK' if os.path.exists(p) else '缺失'}  {p}")
        ok &= os.path.exists(p)
    print(f"  配置       {data_path('llm_config.json')}")
    try:
        from win_stdio import setup_stdio
        print(f"  stdio 接管 {setup_stdio()}")
    except Exception:                                              # noqa: BLE001
        pass
    print("== 依赖 ==")
    for mod in ("mcp", "PySide6"):
        try:
            __import__(mod)
            print(f"  {mod:10s} OK")
        except Exception as e:                                     # noqa: BLE001
            print(f"  {mod:10s} 缺（{e}）")
            if mod == "mcp":
                ok = False
    print("== 模型 ==")
    try:
        c = LLMClient(load_config())
        print(f"  端点 {c.base_url} · 模型 {c.model} · 密钥 {mask(c.cfg.get('api_key',''))}")
        models = c.list_models()
        print(f"  可用模型 {models}")
        if not models:
            print(f"  上游报错 {getattr(c, 'last_error', '') or '(无)'}")
            ok = False
    except Exception as e:                                         # noqa: BLE001
        print(f"  失败：{e}")
        ok = False
    print("\n结论：" + ("全部通过" if ok else "存在问题"))
    return 0 if ok else 1


def cmd_net(argv: list) -> int:
    """网络自检：直接打上游 /models，打印完整异常（冻结后排查 HTTPS 用）。"""
    import ssl
    import traceback
    import urllib.request
    from llm_client import LLMClient, load_config, mask, ssl_context
    c = LLMClient(load_config())
    print(f"Python {sys.version.split()[0]}  frozen={getattr(sys, 'frozen', False)}")
    print(f"OpenSSL {ssl.OPENSSL_VERSION}")
    try:
        ctx = ssl.create_default_context()
        print(f"默认 CA 数量 {len(ctx.get_ca_certs()) if hasattr(ctx, 'get_ca_certs') else '?'}")
    except Exception as e:                                         # noqa: BLE001
        print(f"建默认 SSL 上下文失败：{type(e).__name__}: {e}")
    print(f"上游 {c.base_url} 密钥 {mask(c.cfg.get('api_key',''))}")
    for path in ("/models", "/v1/models"):
        url = c._url(path)
        try:
            req = urllib.request.Request(url, headers=c._headers())
            with urllib.request.urlopen(req, timeout=30, context=ssl_context()) as r:
                print(f"  GET {url} → HTTP {r.status}，前 120 字节：{r.read()[:120]!r}")
            return 0
        except Exception as e:                                     # noqa: BLE001
            print(f"  GET {url} → 失败 {type(e).__name__}: {e}")
            if getattr(e, 'read', None):
                try:
                    print(f"    响应体：{e.read()[:200]!r}")
                except Exception:                                  # noqa: BLE001
                    pass
            traceback.print_exc()
    return 1


COMMANDS = {"gui": cmd_gui, "net": cmd_net, "mcp": cmd_mcp, "api": cmd_api, "serve": cmd_api,
            "stages": cmd_stages, "projects": cmd_projects, "paths": cmd_paths,
            "check": cmd_check}


def main(argv: list | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("-"):
        # 无子命令：按 exe 名判断（服务版 exe 默认进 MCP，界面版默认进 GUI）
        name = os.path.basename(sys.executable if getattr(sys, "frozen", False)
                                else sys.argv[0]).lower()
        if any(k in name for k in ("serve", "服务", "mcp", "api")):
            argv = ["mcp"] + argv
        else:
            argv = ["gui"] + argv
    cmd, rest = argv[0], argv[1:]
    fn = COMMANDS.get(cmd)
    if fn is None:
        sys.stderr.write(__doc__ + f"\n未知命令：{cmd}\n")
        return 2
    return fn(rest)


if __name__ == "__main__":
    import time
    _ensure_streams()
    _utf8_console()
    _banner()
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:                                     # noqa: BLE001
        where = _crash_log(e)
        _alert(f"{type(e).__name__}: {e}\n\n详细堆栈已写入：\n{where}")
        raise
