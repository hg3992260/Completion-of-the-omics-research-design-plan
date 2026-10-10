# -*- coding: utf-8 -*-
"""获取内嵌用的 opencode 内核二进制，落到 opencode/ 目录。

为什么需要它：
  二进制当前平台上是 **172.3 MB**（zip 59.3 MB），超过 GitHub 单文件 100 MB 硬上限，
  因此不可能入库。只能由构建时下载，再让 PyInstaller 打进产物。

为什么默认下载 release 而不用本地构建：
  release 是 CI 构建、已签名、可复现的规范产物；本地构建另有四个坑
  （非 git 仓库 / node-gyp / 依赖链接 / models.dev 联网），见
  opencode-embedding-plan.md §9.6 与 build_opencode_kernel.bat。

用法：
    python get_opencode_kernel.py                 # 按当前平台下载 1.18.35
    python get_opencode_kernel.py --version 1.18.35
    python get_opencode_kernel.py --baseline      # 非 AVX2 老 CPU 变体（仅 Windows）
    python get_opencode_kernel.py --check         # 只校验已存在的二进制，不下载
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEST_DIR = os.path.join(HERE, "opencode")
DEFAULT_VERSION = "1.18.35"
REPO = "anomalyco/opencode"          # 与仓库 package.json 的 repository 字段一致


def asset_name(baseline: bool = False) -> str | None:
    """按平台给出 release 资产名（与 .github/workflows/publish.yml 的打包名一致）。"""
    machine = platform.machine().lower()
    arm = machine in ("arm64", "aarch64")
    if sys.platform == "win32":
        base = "opencode-windows-arm64" if arm else "opencode-windows-x64"
        if baseline and not arm:
            base += "-baseline"
        return base + ".zip"
    if sys.platform == "darwin":
        return ("opencode-darwin-arm64" if arm else "opencode-darwin-x64") + ".zip"
    return None


def exe_name() -> str:
    return "opencode.exe" if sys.platform == "win32" else "opencode"


def target_path() -> str:
    return os.path.join(DEST_DIR, exe_name())


def verify(path: str) -> dict:
    """跑 --version 校验二进制真的可用。"""
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=120)
        return {"ok": out.returncode == 0, "version": (out.stdout or "").strip(),
                "returncode": out.returncode,
                "size_mb": round(os.path.getsize(path) / 1024 / 1024, 1)}
    except Exception as e:                                             # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def download(version: str, baseline: bool) -> dict:
    name = asset_name(baseline)
    if not name:
        return {"ok": False, "error": f"不支持的平台：{sys.platform}/{platform.machine()}"}

    url = f"https://github.com/{REPO}/releases/download/v{version}/{name}"
    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"下载 {url}")

    tmpdir = tempfile.mkdtemp(prefix="opencode-kernel-")
    zip_path = os.path.join(tmpdir, name)
    try:
        with urllib.request.urlopen(url, timeout=900) as res, open(zip_path, "wb") as fh:
            shutil.copyfileobj(res, fh, length=1024 * 1024)
        size_mb = round(os.path.getsize(zip_path) / 1024 / 1024, 1)
        print(f"  下载完成 {size_mb} MB，解压…")

        with zipfile.ZipFile(zip_path) as zf:
            members = zf.namelist()
            # zip 根目录即 bin/ 的内容 → 目标是 opencode.exe / opencode
            wanted = [m for m in members
                      if os.path.basename(m) in (exe_name(), "opencode", "opencode.exe")]
            if not wanted:
                return {"ok": False, "error": f"压缩包里没有可执行文件，成员={members[:10]}"}
            member = wanted[0]
            with zf.open(member) as src, open(target_path(), "wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
        if sys.platform != "win32":
            os.chmod(target_path(), 0o755)

        info = verify(target_path())
        info.update({"asset": name, "url": url, "zip_mb": size_mb,
                     "path": target_path()})
        return info
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="获取内嵌 opencode 内核二进制")
    ap.add_argument("--version", default=os.environ.get("PCL_OPENCODE_VERSION") or DEFAULT_VERSION)
    ap.add_argument("--baseline", action="store_true", help="非 AVX2 老 CPU 变体（仅 Windows）")
    ap.add_argument("--check", action="store_true", help="只校验，不下载")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--force", action="store_true", help="即使已存在也重新下载")
    args = ap.parse_args()

    path = target_path()
    if os.path.exists(path) and not args.force:
        info = verify(path)
        info.update({"skipped": True, "path": path,
                     "note": "已存在，未重新下载（要覆盖用 --force）"})
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print(f"已存在：{path}")
            print(f"  {info.get('size_mb')} MB  version={info.get('version')}  ok={info.get('ok')}")
        return 0 if info.get("ok") else 1

    if args.check:
        if not os.path.exists(path):
            print(json.dumps({"ok": False, "error": f"不存在：{path}"}, ensure_ascii=False))
            return 1
        info = verify(path)
        print(json.dumps(info, ensure_ascii=False, indent=2) if args.json
              else f"{path}\n  {info.get('size_mb')} MB  version={info.get('version')}  ok={info.get('ok')}")
        return 0 if info.get("ok") else 1

    info = download(args.version, args.baseline)
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        if info.get("ok"):
            print(f"\n[成功] {info['path']}")
            print(f"  release  v{args.version} ({info['asset']})")
            print(f"  体积     {info['size_mb']} MB（解压后）")
            print(f"  版本     {info['version']}")
            if sys.platform == "win32" and not args.baseline:
                print("  提示     老 CPU（无 AVX2）请改用 --baseline")
        else:
            print(f"[失败] {info.get('error')}")
    return 0 if info.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
