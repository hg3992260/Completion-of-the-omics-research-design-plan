# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包脚本 —— macOS 版（必须在 macOS 上运行，PyInstaller 不支持跨平台）。

产出：
    dist/PCLRadiomics.app/                         图形界面（拖进 Applications 即可）
    dist/PCLRadiomics.app/Contents/MacOS/PCLRadiomics   同一个二进制的命令行入口
    dist/pclradiomics                              纯命令行版（不含 Qt，约 50MB，MCP 注册用这个最省事）

用法（macOS）：
    python -m PyInstaller --noconfirm --clean pclradiomics_macos.spec
    PCL_ARCH=universal2 python -m PyInstaller ... pclradiomics_macos.spec   # 通用二进制（若依赖有 universal2 轮子）
    PCL_VERSION=1.1.1 python -m PyInstaller ... pclradiomics_macos.spec

macOS 与 Windows 的差异都在代码里处理好了：
    · 字体      ui_kit 在 darwin 上用 PingFang SC / Menlo
    · 数据目录  app_paths 在 macOS 用 ~/Library/Application Support/PCLRadiomics（.app 包内只读，不能写）
    · 标准流    win_stdio 只在 Windows 生效；macOS 的 .app 内二进制本身就有 stdout，stdio MCP 直接可用
"""

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.getcwd())
APP_NAME = "PCLRadiomics"
APP_NAME_CN = "组学研究设计工作台"
VERSION = os.environ.get("PCL_VERSION", "1.1.1")
ARCH = os.environ.get("PCL_ARCH", "")            # 留空=本机架构；universal2 / x86_64 / arm64

ASSETS = ["theme_tech.json", "logo_icon.ico", "logo_badge.png", "logo_banner.png",
          "logo_mark.png", "LOGO.jpg", "logo.icns"]
datas = [(f, ".") for f in ASSETS if os.path.exists(os.path.join(ROOT, f))]
datas += collect_data_files("certifi")     # HTTPS 根证书
datas += collect_data_files("PyCt6")       # 自带主题 JSON，缺了界面会静默退出
datas += collect_data_files("mcp")
datas += collect_data_files("docx")   # python-docx 的默认模板 templates/default.docx 必须一起打包，否则导出 Word 会失败

# —— 内嵌 opencode 内核（Windows 走 pclradiomics.spec，macOS 为可选）——
# v2.0.0 的内核嵌入以 Windows 为完整目标；macOS 这里只收集**内核客户端代码**，
# 使 `kernel` 子命令不会 ImportError，并在找不到二进制时由 kernel selftest 明确报错。
# 若在 macOS 上跑过 get_opencode_kernel.py（会下 darwin 版，约 43 MB 压缩），
# 则一并打进产物，macOS 也能获得完整内核能力。
KERNEL_EXE_MAC = os.path.join(ROOT, "opencode", "opencode")
if os.path.exists(KERNEL_EXE_MAC):
    datas.append((KERNEL_EXE_MAC, "opencode"))

MODULES = ["app_paths", "stages_data", "llm_client", "design_agent",
           "mcp_server", "api_server", "cli", "win_stdio",
           "docx_export", "manuscript_review",
           "kernel_client", "kernel_config", "kernel_cli"]
HIDDEN = list(MODULES)
for pkg in ("mcp", "anyio", "httpx", "httpcore", "starlette", "uvicorn",
            "sse_starlette", "pydantic", "pydantic_core", "sniffio", "certifi", "h11"):
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


def strip_mkl(binaries):
    """剔除被间接拉进来的 Intel MKL（约 350MB，本程序运行期用不到）。"""
    return [b for b in binaries if not os.path.basename(b[0]).lower().startswith("mkl_")]


ICON = "logo.icns" if os.path.exists(os.path.join(ROOT, "logo.icns")) else None

# ---------------------------------------------------------------- 图形版（.app）
gui_hidden = HIDDEN + ["ui_kit", "design_studio", "omics_pipeline"]
try:
    gui_hidden += collect_submodules("PyCt6")
except Exception:
    gui_hidden.append("PyCt6")

a_gui = Analysis(["cli.py"], pathex=[ROOT], binaries=[], datas=datas,
                 hiddenimports=gui_hidden, hookspath=[], runtime_hooks=[],
                 excludes=["tkinter", "matplotlib", "IPython", "notebook",
                           "numpy", "PIL", "Pillow", "scipy", "pandas",
                           "mkl", "mkl_rt", "numpy_distutils"],
                 noarchive=False, target_arch=ARCH or None)
a_gui.binaries = strip_mkl(a_gui.binaries)
pyz_gui = PYZ(a_gui.pure, a_gui.zipped_data)
exe_gui = EXE(pyz_gui, a_gui.scripts, [], exclude_binaries=True,
              name=APP_NAME, debug=False, strip=False, upx=False,
              console=False, icon=ICON, target_arch=ARCH or None)
coll_gui = COLLECT(exe_gui, a_gui.binaries, a_gui.zipfiles, a_gui.datas,
                   strip=False, upx=False, name=APP_NAME)

app = BUNDLE(
    coll_gui,
    name=f"{APP_NAME}.app",
    icon=ICON,
    bundle_identifier="io.github.hg3992260.pclradiomics",
    version=VERSION,
    info_plist={
        "CFBundleName": "PCL-Radiomics",
        "CFBundleDisplayName": APP_NAME_CN,
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,      # 跟随系统深浅色
        "LSApplicationCategoryType": "public.app-category.education",
        "NSHumanReadableCopyright": "designed by christ.paul90@gmail.com, all rights reserved",
    },
)

# ---------------------------------------------------------------- 命令行版（MCP / API）
cli_hidden = HIDDEN + ["ui_kit"]
a_cli = Analysis(["cli.py"], pathex=[ROOT], binaries=[], datas=datas,
                 hiddenimports=cli_hidden, hookspath=[], runtime_hooks=[],
                 excludes=["PySide6", "shiboken6", "PyQt5", "PyQt6", "tkinter",
                           "matplotlib", "IPython", "notebook", "numpy", "PIL",
                           "Pillow", "scipy", "pandas", "mkl", "mkl_rt",
                           "numpy_distutils"],
                 noarchive=False, target_arch=ARCH or None)
a_cli.binaries = strip_mkl(a_cli.binaries)
pyz_cli = PYZ(a_cli.pure, a_cli.zipped_data)
exe_cli = EXE(pyz_cli, a_cli.scripts, [], exclude_binaries=True,
              name="pclradiomics", debug=False, strip=False, upx=False,
              console=True, icon=ICON, target_arch=ARCH or None)
coll_cli = COLLECT(exe_cli, a_cli.binaries, a_cli.zipfiles, a_cli.datas,
                   strip=False, upx=False, name="pclradiomics-cli")
