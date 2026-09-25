# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包脚本 —— **Windows 7 可用的 Web 版**（本地服务 + 系统浏览器界面）。

它和 win7 的「仅 API 服务」版（pclradiomics_api_win7.spec）的区别：
    本 spec 打的是**完整界面**。界面不是 Qt，而是"本地起一个 HTTP 服务、用系统浏览器打开"，
    所以它对 Windows 7 没有 Qt 6 那层硬约束 —— 只要用 **Python 3.8** 构建即可。

产物（两种形态，二选一拷给用户）：
    dist-web\\PCLRadiomicsWeb\\PCLRadiomicsWeb.exe        文件夹版（推荐：启动快、无需解包）
    dist-web\\PCLRadiomicsWeb.exe                          单文件版（便于传输，启动稍慢）

用法（源码里也能直接跑，打包只是为了目标机不用装 Python）：
    PCLRadiomicsWeb.exe                        # 默认 127.0.0.1:8787，自动开浏览器
    PCLRadiomicsWeb.exe --port 8899 --no-browser
    PCLRadiomicsWeb.exe --host 0.0.0.0 --token 口令   # 局域网共享（慎用）

前置条件（Win7 目标机）：
    Windows 7 **SP1**（64 位） + KB2533623 + KB2999226（UCRT）
    + Visual C++ 2015-2019 运行库（x64）
    + 一个能跑现代界面的浏览器：Chrome 109 / Edge 109 / Firefox 115 ESR
      （三者都是 Win7 上最后一批支持现代 CSS + SSE 的浏览器；IE11 会显示降级提示）

构建前置条件（构建机）：
    Python **3.8**（务必是 3.8；3.9+ 打出来的东西 Win7 起不来）
    pip install pyinstaller==6.10 certifi python-docx
    （pyinstaller 6.11+ 要求 Python ≥3.9，所以 3.8 上请用 6.10 或 5.13）

构建后务必自检：
    python _check_win_target.py dist-web\\PCLRadiomicsWeb\\PCLRadiomicsWeb.exe
    python _test_web_exe.py                 # 起真 exe，验接口 / 静态资源 / SSE / 截图
"""

import glob
import os
import sys

from PyInstaller.utils.hooks import collect_data_files

ROOT = os.path.abspath(os.getcwd())
APP_NAME = "PCLRadiomicsWeb"
ICON = "logo_icon.ico" if os.path.exists(os.path.join(ROOT, "logo_icon.ico")) else None

datas = [("web", "web")]                 # 界面资源：index.html / app.css / app.js / favicon
try:
    datas += collect_data_files("certifi")      # HTTPS 根证书（连模型 API 用）
except Exception:
    pass


def _extra_dlls():
    """conda 风格的 Python 把 OpenSSL / libxml2 放在 `Library\\bin`，PyInstaller 默认收不到 ——
    少了它们，冻结后会依次报：
        ImportError: DLL load failed while importing _ssl       （连 HTTPS 都起不来）
        ImportError: DLL load failed while importing etree      （python-docx 导出 Word 失败）
    这里把 ssl / 压缩 / libxml2 一族真正依赖的 DLL 显式带上。
    （依赖是用 _list_pe_deps.py 逐个 PE 解析出来的，不是猜的。）"""
    out, seen = [], set()
    roots = [sys.prefix, sys.base_prefix,
             os.path.join(sys.prefix, "Library", "bin"),
             os.path.join(sys.prefix, "DLLs"),
             os.path.join(sys.base_prefix, "Library", "bin"),
             os.path.join(sys.base_prefix, "DLLs")]
    patterns = ("libssl*.dll", "libcrypto*.dll", "libffi*.dll",
                "libbz2*.dll", "liblzma*.dll", "zlib*.dll",
                "libxml2*.dll", "libxslt*.dll", "libexslt*.dll",
                "iconv*.dll", "charset*.dll")
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for pat in patterns:
            for p in glob.glob(os.path.join(root, pat)):
                key = os.path.basename(p).lower()
                if key not in seen:
                    seen.add(key)
                    out.append((p, "."))
    return out


binaries = _extra_dlls()
if binaries:
    print("  附带的运行库 DLL：%s" % "、".join(sorted(os.path.basename(b[0])
                                                    for b in binaries)))

HIDDEN = ["app_paths", "llm_client", "design_agent", "stages_data", "stat_data",
          "shape_data", "scope_core", "coupling", "docx_export", "web_server"]

a = Analysis(
    ["web_server.py"],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=HIDDEN,
    hookspath=[],
    runtime_hooks=[],
    # 排除整条 Qt / 桌面界面链路：既减小体积，也避免把 Win7 上跑不起来的东西带进去
    excludes=["tkinter", "matplotlib", "IPython", "notebook", "pandas", "PIL", "Pillow",
              "mkl", "mkl_rt", "PySide6", "shiboken6", "PyCt6",
              "design_studio", "omics_pipeline", "ui_kit", "win_stdio",
              "mcp", "mcp_server", "api_server", "cli"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# 形态一：文件夹版（推荐）
exe_dir = EXE(pyz, a.scripts, [], exclude_binaries=True,
              name=APP_NAME, debug=False, strip=False, upx=False,
              console=True,                       # 保留控制台：能看到地址与报错
              icon=ICON)
coll = COLLECT(exe_dir, a.binaries, a.zipfiles, a.datas,
               strip=False, upx=False, name=APP_NAME)

# 形态二：单文件版（便于传输）
exe_one = EXE(pyz, a.scripts, a.binaries, a.datas, [],
              name=APP_NAME, debug=False, strip=False, upx=False,
              console=True, icon=ICON, exclude_binaries=False)

print("")
print("=" * 68)
print("  已构建 %s（Web 版：本地服务 + 系统浏览器界面，无需 Qt）" % APP_NAME)
print("  构建用 Python：%s" % sys.version.split()[0]
      + ("   ← 非 3.8：产物在 Win7 上仍会因 api-ms-win-core-path 报错"
         if sys.version_info[:2] != (3, 8) else
         "   ← 正确（3.8 是最后一个支持 Win7 的版本）"))
print("  产物： PCLRadiomicsWeb\\PCLRadiomicsWeb.exe（文件夹版）")
print("         PCLRadiomicsWeb.exe（单文件版）")
print("  自检： python _check_win_target.py PCLRadiomicsWeb\\PCLRadiomicsWeb.exe")
print("         python _test_web_exe.py")
print("=" * 68)
