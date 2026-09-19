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
          "win_stdio"]
for pkg in ("mcp", "anyio", "httpx", "httpcore", "starlette", "uvicorn",
            "sse_starlette", "pydantic", "pydantic_core", "sniffio", "certifi",
            "h11", "PyCt6"):
    try:
        HIDDEN += collect_submodules(pkg)
    except Exception:
        HIDDEN.append(pkg)

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
