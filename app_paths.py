# -*- coding: utf-8 -*-
"""统一的路径解析：源码运行与 PyInstaller 冻结后行为一致。

- 源码运行：一切都相对项目目录（与原来一致）
- 冻结后：
    * 只读资源（主题 / 图标）优先取 exe 同级目录，其次取打包内置目录(_MEIPASS)
    * 可写数据（projects/、配置、导出文件）一律放 exe 同级目录，做到"绿色便携"；
      若该目录不可写（例如装在 Program Files），自动退到 %LOCALAPPDATA%\\PCLRadiomics

这样同一个 exe 既能在开发机上跑，也能拷到别的机器上直接用，不需要改代码。
"""

from __future__ import annotations

import os
import sys

APP_NAME = "PCLRadiomics"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _exe_dir() -> str:
    return os.path.dirname(os.path.abspath(sys.executable))


def _bundle_dir() -> str:
    return getattr(sys, "_MEIPASS", "") or ""


def _source_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def app_home() -> str:
    """可写数据目录。

    macOS 的 .app 是"签名后只读"的包，绝不能往包里写；
    所以冻结态在 macOS 上固定用 ~/Library/Application Support/PCLRadiomics。
    """
    if not is_frozen():
        return _source_dir()
    if sys.platform == "darwin" or ".app/Contents/" in _exe_dir().replace("\\", "/"):
        d = os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_NAME)
        os.makedirs(d, exist_ok=True)
        return d
    cand = _exe_dir()
    try:
        probe = os.path.join(cand, ".write_test")
        with open(probe, "w") as fh:
            fh.write("1")
        os.remove(probe)
        return cand
    except Exception:                                              # noqa: BLE001
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        d = os.path.join(base, APP_NAME)
        os.makedirs(d, exist_ok=True)
        return d


def resource_path(name: str) -> str:
    """只读资源：exe 同级 → 打包内置 → 源码目录。"""
    for base in (_exe_dir() if is_frozen() else "", _bundle_dir(), _source_dir()):
        if not base:
            continue
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return os.path.join(app_home(), name)


def data_path(*parts: str) -> str:
    """可写数据文件/目录（会自动建父目录）。"""
    p = os.path.join(app_home(), *parts)
    parent = p if os.path.splitext(p)[1] == "" else os.path.dirname(p)
    try:
        os.makedirs(parent, exist_ok=True)
    except Exception:                                              # noqa: BLE001
        pass
    return p


def export_dir() -> str:
    """导出文件的落盘目录：优先用户可见的位置（文档/桌面/家目录）。

    原来直接写 app_home()，在 macOS 上是 ~/Library/Application Support/...（隐藏目录），
    Windows 装在 Program Files 时还可能是只读。这里按顺序找一个"能写且用户找得到"的目录。
    """
    home = os.path.expanduser("~")
    for cand in (os.path.join(home, "Documents", APP_NAME),
                 os.path.join(home, "桌面", APP_NAME),          # 中文 Windows 的桌面
                 os.path.join(home, "Desktop", APP_NAME),
                 os.path.join(home, APP_NAME),
                 app_home()):
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".write_probe")
            with open(probe, "w") as fh:
                fh.write("1")
            os.remove(probe)
            return cand
        except Exception:                                          # noqa: BLE001
            continue
    return app_home()


def describe() -> dict:
    return {"frozen": is_frozen(), "executable": sys.executable if is_frozen() else "",
            "app_home": app_home(), "export_dir": export_dir(),
            "bundle": _bundle_dir(), "source": _source_dir()}


if __name__ == "__main__":
    for k, v in describe().items():
        print(f"{k:12s} {v}")
