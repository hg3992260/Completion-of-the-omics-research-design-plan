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

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.getcwd())
APP_NAME = "PCLRadiomics"
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

HIDDEN = ["app_paths", "stages_data", "llm_client", "design_agent",
          "mcp_server", "api_server", "cli", "ui_kit", "design_studio", "omics_pipeline",
          "win_stdio", "docx_export", "manuscript_review"]
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
           "mcp_server", "api_server"):
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
