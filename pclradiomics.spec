# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包脚本 —— **合并版：一个 exe 承载全部模式**。

    dist/PCLRadiomics/PCLRadiomics.exe          （onedir，推荐：启动快）
    PCLRadiomics.exe gui                        图形界面（自动隐藏控制台）
    PCLRadiomics.exe mcp                        MCP stdio（供 DSH / Claude Desktop）
    PCLRadiomics.exe mcp --transport streamable-http --port 8765
    PCLRadiomics.exe api --port 8788            OpenAI 兼容推理服务

单文件版（下载方便，但每次启动要解包，被 MCP 客户端反复拉起会慢 3–8 秒）：
    set PCL_ONEFILE=1 && python -m PyInstaller --noconfirm --clean pclradiomics.spec

为什么必须编成 console 子系统（而不是 windowed）：
    stdio 传输要求进程有真实的 stdout/stdin。windowed 构建里 sys.stdout 是 None，
    MCP 客户端一握手就失败。所以这里统一用 console，
    图形模式再调用 cli._hide_own_console() 把自己独占的控制台窗口藏起来。

想要不带界面、体积更小的服务端（约 54MB）：用 pclradiomics_service.spec。
"""

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.getcwd())
# 产物名可用 PCL_APP_NAME 覆盖 —— 双变体必需：
#   PCLRadiomics.exe（windowed 主程序）与 PCLRadiomicsConsole.exe（console 子系统）
#   若都叫 PCLRadiomics 会互相覆盖（见 opencode-embedding-plan.md §4.2 风险 13）。
APP_NAME = os.environ.get("PCL_APP_NAME") or "PCLRadiomics"
ONEFILE = os.environ.get("PCL_ONEFILE", "") not in ("", "0", "false", "False")
# 合并版默认 windowed：图形模式没有黑框；stdio MCP 由 win_stdio 接管父进程管道
CONSOLE = os.environ.get("PCL_CONSOLE", "") not in ("", "0", "false", "False")

# 只读资源：主题与图标（构建脚本还会拷一份到 exe 同级，便于用户替换）
ASSETS = ["theme_tech.json", "logo_icon.ico", "logo_badge.png", "logo_banner.png", "LOGO.jpg"]
datas = [(f, ".") for f in ASSETS if os.path.exists(os.path.join(ROOT, f))]
datas += collect_data_files("certifi")     # HTTPS 根证书（冻结后 Windows 证书库可能枚举失败）
datas += collect_data_files("PyCt6")       # PyCt6 自带主题 JSON，缺了界面会静默退出
datas += collect_data_files("mcp")
datas += collect_data_files("docx")   # python-docx 的默认模板 templates/default.docx 必须一起打包，否则导出 Word 会失败

# —— 内嵌 opencode 内核二进制（172 MB）——
# 为何不入库：GitHub 单文件硬上限 100 MB。故由构建期获取；本 spec 自带获取逻辑，
# 因此**不需要 workflow 做任何额外步骤**（这让构建在任何环境都自洽）。
# 放在 datas 的 "opencode" 目标下 → 冻结后落在 _internal/opencode/opencode.exe，
# 由 kernel_client.opencode_exe() 经 resource_path 找到（不放进 binaries：
# 那是预编译依赖目录，会被依赖分析/strip 处理，而这是个自带运行时的独立 exe）。
KERNEL_EXE = os.path.join(ROOT, "opencode", "opencode.exe")
SKIP_KERNEL = os.environ.get("PCL_SKIP_KERNEL", "") not in ("", "0", "false", "False")
FORCE_KERNEL_ONEFILE = os.environ.get("PCL_ONEFILE_WITH_KERNEL", "") not in ("", "0", "false", "False")
# onefile 默认**不**打包内核：onefile 每次启动都要把内容解包到 %TEMP%，再塞一个
# 172 MB 的内核会让启动严重恶化；而 MCP 客户端会反复拉起进程 → 反复解包。
# 要强制包含：PCL_ONEFILE_WITH_KERNEL=1（决策 D5 的连带结论，见 plan §4.3）。
if ONEFILE and not FORCE_KERNEL_ONEFILE:
    SKIP_KERNEL = True

if not os.path.exists(KERNEL_EXE) and not SKIP_KERNEL:
    import subprocess as _subprocess
    print("[spec] 未找到内嵌内核 opencode\\opencode.exe，尝试获取…")
    _rc = _subprocess.call([sys.executable, os.path.join(ROOT, "get_opencode_kernel.py")])
    if _rc != 0:
        raise SystemExit(
            "[打包中止] 未能获取内嵌内核 opencode\\opencode.exe。\n"
            "  · 有网时本 spec 会自动下载；离线请手工把 v1.18.35 的\n"
            "    opencode-windows-x64.zip 解压到 opencode/ 目录；\n"
            "  · 或先跑 build_opencode_kernel.bat --from-source 从源码构建；\n"
            "  · 若确实要打一个不含内核的版本，设 PCL_SKIP_KERNEL=1。"
        )

if os.path.exists(KERNEL_EXE):
    datas.append((KERNEL_EXE, "opencode"))
    print("[spec] 已纳入内嵌内核: {0:.1f} MB".format(os.path.getsize(KERNEL_EXE) / 1024 / 1024))
elif SKIP_KERNEL:
    print("[spec] 按配置跳过内嵌内核（PCL_SKIP_KERNEL=1 或 onefile 默认）")

HIDDEN = ["app_paths", "stages_data", "llm_client", "design_agent",
          "mcp_server", "api_server", "cli", "ui_kit", "design_studio", "omics_pipeline",
          "win_stdio", "docx_export", "manuscript_review",
          "kernel_client", "kernel_config", "kernel_cli"]
for pkg in ("mcp", "anyio", "httpx", "httpcore", "starlette", "uvicorn",
            "sse_starlette", "pydantic", "pydantic_core", "sniffio", "certifi",
            "h11", "PyCt6"):
    try:
        HIDDEN += collect_submodules(pkg)
    except Exception:
        HIDDEN.append(pkg)


def _collect_local(pkgs):
    """收集本地包的全部子模块。

    为什么必须显式收集：design_studio / cli 等是以 hiddenimports **硬编码**进来的，
    PyInstaller 对 hiddenimport 不再递归分析其内部导入；而它们内部的
    `from manuscript_review.mr_engine import ...` 又都写在**函数里**（延迟导入），
    所以整条链路会被静默丢弃 —— 打包后运行时报 ModuleNotFoundError，
    界面只显示“没有导入手稿”，完全看不出是缺模块。
    这里对本地包做一次显式 collect_submodules，新增子模块时不必再改本文件。
    """
    out = []
    for pkg in pkgs:
        try:
            out += collect_submodules(pkg)
        except Exception:
            out.append(pkg)
    return out


HIDDEN += _collect_local(("manuscript_review",))

# —— 打包前置校验：把「硬编码 hiddenimports 的本地模块」逐个真实导入一次。
#    任何一个导入失败都说明它自己或它依赖的本地模块没被收集，直接中止而不是产出坏包。
_probe_fail = []
for _m in ("design_studio", "omics_pipeline", "manuscript_review", "docx_export",
           "mcp_server", "api_server", "kernel_client", "kernel_config", "kernel_cli"):
    try:
        __import__(_m)
    except Exception as _e:                                        # noqa: BLE001
        _probe_fail.append(f"{_m}: {type(_e).__name__}: {_e}")
if _probe_fail:
    raise SystemExit("[打包中止] 以下模块无法导入，打包会产出缺模块的坏包：\n  "
                     + "\n  ".join(_probe_fail))

a = Analysis(
    ["cli.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=HIDDEN,
    hookspath=[],
    runtime_hooks=[],
    # 本程序运行期完全不用 numpy/PIL —— 它们是被间接拉进来的，
    # 其中 Intel MKL 运行库约 350MB，必须剔掉
    excludes=["tkinter", "matplotlib", "IPython", "notebook", "numpy", "PIL",
              "Pillow", "scipy", "pandas", "mkl", "mkl_rt", "numpy_distutils"],
    noarchive=False,
)


def strip_mkl(binaries):
    """兜底：即便某个 hook 又把 MKL 拉进来，也在这里剔除。

    保留 libssl/libcrypto（HTTPS 必需）与 opengl32sw.dll（无显卡机器的 Qt 软件渲染兜底）。
    """
    return [b for b in binaries if not os.path.basename(b[0]).lower().startswith("mkl_")]


a.binaries = strip_mkl(a.binaries)
pyz = PYZ(a.pure, a.zipped_data)

ICON = "logo_icon.ico" if os.path.exists(os.path.join(ROOT, "logo_icon.ico")) else None

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
              name=APP_NAME, debug=False, strip=False, upx=False,
              console=CONSOLE,
              runtime_tmpdir=None, icon=ICON)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
              name=APP_NAME, debug=False, strip=False, upx=False,
              console=CONSOLE, icon=ICON)
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
                   strip=False, upx=False, name=APP_NAME)
