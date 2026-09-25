# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包脚本 —— **Windows 7 可用的「仅 API 服务」版**。

为什么要单独一个 spec：
    图形界面依赖 PySide6 / Qt 6，而 Qt 6 与 Python 3.9+ **都不支持 Windows 7**，
    因此 Win7 上无法提供 GUI。但 OpenAI 兼容推理服务（api_server.py）只依赖
    标准库 + certifi + 可选 openai，**完全不需要 Qt**，所以可以用
    **Python 3.8**（最后一个支持 Win7 的解释器）打出一个能在 Win7 上跑的服务端。

    dist/PCLRadiomicsAPI/PCLRadiomicsAPI.exe --port 8788
    dist/PCLRadiomicsAPI/PCLRadiomicsAPI.exe --host 0.0.0.0 --token <口令> --port 8788

前置条件（Win7 目标机）：
    Windows 7 **SP1**（64 位） + KB2533623 + KB2999226（UCRT）
    + Visual C++ 2015-2019 运行库（x64）。

构建前置条件（构建机）：
    Python **3.8**（务必是 3.8；3.9+ 打出来的东西 Win7 起不来）
    pip install pyinstaller==6.10 certifi
    （pyinstaller 6.11+ 要求 Python ≥3.9，所以 3.8 上请用 6.10 或 5.13）

构建后务必自检：
    python _check_win_target.py dist\\PCLRadiomicsAPI\\PCLRadiomicsAPI.exe
    —— 应报告「未发现 Win8+/Win10+ 专有 API set」。
"""

import os
import sys

from PyInstaller.utils.hooks import collect_data_files

ROOT = os.path.abspath(os.getcwd())
APP_NAME = "PCLRadiomicsAPI"

# 只用得到主题/图标之外的东西：这里连图标都不是必需，但保留便于识别
ICON = "logo_icon.ico" if os.path.exists(os.path.join(ROOT, "logo_icon.ico")) else None

datas = []
try:
    datas += collect_data_files("certifi")      # HTTPS 根证书
except Exception:
    pass

HIDDEN = ["app_paths", "llm_client", "api_server"]

a = Analysis(
    ["api_server.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=HIDDEN,
    hookspath=[],
    runtime_hooks=[],
    # 关键：整条 Qt / 界面链路都排除掉，既减小体积也避免引入 Win10+ 依赖
    excludes=["tkinter", "matplotlib", "IPython", "notebook", "numpy", "PIL",
              "Pillow", "scipy", "pandas", "mkl", "mkl_rt",
              "PySide6", "shiboken6", "PyCt6",
              "design_studio", "omics_pipeline", "ui_kit", "win_stdio",
              "mcp", "mcp_server", "docx", "docx_export"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name=APP_NAME, debug=False, strip=False, upx=False,
          console=True,                      # 服务端保留控制台，便于看日志/报错
          icon=ICON)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
               strip=False, upx=False, name=APP_NAME)

# 构建期提示：让使用者在控制台直接看到目标系统要求
print("")
print("=" * 68)
print(f"  已构建 {APP_NAME}（无需 Qt，可面向 Windows 7）")
print(f"  构建用 Python：{sys.version.split()[0]}"
      + ("   ← 非 3.8：产物在 Win7 上仍会因 api-ms-win-core-path 报错"
         if sys.version_info[:2] != (3, 8) else "   ← 正确（3.8 是最后一个支持 Win7 的版本）"))
print("  自检：python _check_win_target.py dist\\%s\\%s.exe" % (APP_NAME, APP_NAME))
print("=" * 68)
