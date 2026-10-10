# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包脚本 —— **opencode GUI**（PyCt6 高对比拟物三维皮肤的会话窗口）。

产物（与 pclradiomics.spec 同一套约定）：
    dist/OpenCodeGUI/OpenCodeGUI.exe             onedir，推荐：启动快，默认含内嵌内核
    set PCL_ONEFILE=1  → dist-onefile/OpenCodeGUI.exe  单文件（默认**不含** 172MB 内核）

运行方式：
    OpenCodeGUI.exe              离线演示界面（不连内核，用于评审/截图）
    OpenCodeGUI.exe --live       连内嵌内核：起 opencode serve + 流式渲染会话
    OpenCodeGUI.exe --shot       出深/浅两张界面图到 exe 同级 _shots/

设计取舍（都是踩过的坑，改前先读）：
  · console=False：这是纯图形程序，内核是子进程，界面状态条 + 内核日志文件足够排错。
  · 必须 collect_data_files("PyCt6")：PyCt6 的主题 JSON 与下拉箭头 down_arrow.png 是
    数据文件，缺了控件构造会 KeyError，或箭头位置空白一片。
  · 内核二进制放进 datas 的 "opencode" 目标（不是 binaries）：冻结后落在
    _internal/opencode/opencode.exe，由 kernel_client.opencode_exe() 经 resource_path 找到；
    放进 binaries 会被依赖分析与 strip 当普通依赖处理，而它是自带运行时的独立 exe。
  · onefile 默认不含内核：每次启动都要解包到 %TEMP%，再塞 172 MB 会让启动严重恶化。
    强制包含：PCL_ONEFILE_WITH_KERNEL=1。
  · hiddenimports 必须列全 kernel_*：它们是写在函数里的**延迟导入**
    （SessionWindow.connect_kernel 内 import），PyInstaller 静态分析看不到，
    漏了就是"打包成功但连内核时报 ModuleNotFoundError"。
"""

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.getcwd())
APP_NAME = os.environ.get("PCL_APP_NAME") or "OpenCodeGUI"
ONEFILE = os.environ.get("PCL_ONEFILE", "") not in ("", "0", "false", "False")

# 只读资源：主题 + 图标（构建脚本还会拷一份到 exe 同级，便于用户替换主题）
ASSETS = ["theme_skeuo.json", "theme_tech.json", "logo_icon.ico",
          "logo_badge.png", "logo_banner.png", "logo_mark.png", "LOGO.jpg"]
datas = [(f, ".") for f in ASSETS if os.path.exists(os.path.join(ROOT, f))]
datas += collect_data_files("PyCt6")       # PyCt6 自带主题/箭头，缺了界面会静默退出

# —— 内嵌 opencode 内核（172 MB）——
KERNEL_EXE = os.path.join(ROOT, "opencode", "opencode.exe")
SKIP_KERNEL = os.environ.get("PCL_SKIP_KERNEL", "") not in ("", "0", "false", "False")
FORCE_KERNEL_ONEFILE = os.environ.get("PCL_ONEFILE_WITH_KERNEL", "") not in ("", "0", "false", "False")
if ONEFILE and not FORCE_KERNEL_ONEFILE:
    SKIP_KERNEL = True

if os.path.exists(KERNEL_EXE) and not SKIP_KERNEL:
    datas.append((KERNEL_EXE, "opencode"))
    print("[spec] 已纳入内嵌内核: {0:.1f} MB".format(os.path.getsize(KERNEL_EXE) / 1024 / 1024))
else:
    print("[spec] 未纳入内嵌内核（PCL_SKIP_KERNEL=1 或 onefile 默认）；"
          "--live 将回落到 PCL_OPENCODE_EXE / exe 同级 opencode/ / PATH")

HIDDEN = ["ui_kit", "skeuo_kit", "app_paths",
          "kernel_client", "kernel_driver",           # 延迟导入，必须显式列
          "PyCt6"]
for pkg in ("PyCt6",):
    try:
        HIDDEN += collect_submodules(pkg)
    except Exception:                                             # noqa: BLE001
        pass

# 打包前置校验：硬编码进来的本地模块先真实导入一次，缺依赖就中止而不是产出坏包
_probe_fail = []
for _m in ("ui_kit", "skeuo_kit", "app_paths", "kernel_client", "kernel_driver",
           "opencode_session_gui"):
    try:
        __import__(_m)
    except Exception as _e:                                       # noqa: BLE001
        _probe_fail.append("%s: %s: %s" % (_m, type(_e).__name__, _e))
if _probe_fail:
    raise SystemExit("[打包中止] 以下模块无法导入，打包会产出缺模块的坏包：\n  "
                     + "\n  ".join(_probe_fail))

a = Analysis(
    ["opencode_session_gui.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=HIDDEN,
    hookspath=[],
    runtime_hooks=[],
    # 界面本身完全不用这些；它们是被间接拉进来的（Intel MKL 运行库约 350MB）
    excludes=["tkinter", "matplotlib", "IPython", "notebook", "numpy", "PIL",
              "Pillow", "scipy", "pandas", "mkl", "mkl_rt", "numpy_distutils"],
    noarchive=False,
)
a.binaries = [b for b in a.binaries if not os.path.basename(b[0]).lower().startswith("mkl_")]

pyz = PYZ(a.pure, a.zipped_data)
ICON = "logo_icon.ico" if os.path.exists(os.path.join(ROOT, "logo_icon.ico")) else None

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
              name=APP_NAME, debug=False, strip=False, upx=False,
              console=False, runtime_tmpdir=None, icon=ICON)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
              name=APP_NAME, debug=False, strip=False, upx=False,
              console=False, icon=ICON)
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
                   strip=False, upx=False, name=APP_NAME)
