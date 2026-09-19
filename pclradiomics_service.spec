# -*- mode: python ; coding: utf-8 -*-
"""只打包服务版（快，约 1-2 分钟），用于迭代排查。产物：dist/PCLRadiomics-服务/"""

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.getcwd())
APP_NAME = "PCLRadiomics"

ASSETS = ["theme_tech.json", "logo_icon.ico", "logo_badge.png", "logo_banner.png", "LOGO.jpg"]
datas = [(f, ".") for f in ASSETS if os.path.exists(os.path.join(ROOT, f))]
datas += collect_data_files("certifi")
datas += collect_data_files("docx")   # python-docx 默认模板（导出 Word 需要）          # python-docx 的默认模板

HIDDEN = []
for pkg in ("mcp", "anyio", "httpx", "httpcore", "starlette", "uvicorn",
            "sse_starlette", "pydantic", "pydantic_core", "sniffio", "certifi", "h11",
            "app_paths", "stages_data", "llm_client", "design_agent", "mcp_server", "api_server"):
    try:
        HIDDEN += collect_submodules(pkg)
    except Exception:
        HIDDEN.append(pkg)

a = Analysis(["cli.py"], pathex=[ROOT], binaries=[], datas=datas, hiddenimports=HIDDEN,
             excludes=["PySide6", "shiboken6", "PyQt5", "PyQt6", "tkinter", "matplotlib",
                       "numpy", "PIL", "scipy", "pandas", "IPython", "notebook"],
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=f"{APP_NAME}服务",
          debug=False, strip=False, upx=False, console=True,
          icon="logo_icon.ico" if os.path.exists(os.path.join(ROOT, "logo_icon.ico")) else None)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False,
               name=f"{APP_NAME}-服务")
