# -*- coding: utf-8 -*-
"""构建目标检查：这个程序/这份 python 运行时到底能在哪些 Windows 上跑。

两个用途：
  1. 不带参数：报告当前工具链（Python / PySide6 / Qt 版本）推出的**最低系统要求**；
  2. 带一个 .exe/.dll 路径：解析其 PE 导入表，列出 Win8+/Win10+ 专有的 API set
     （例如 `api-ms-win-core-path-l1-1-0.dll` —— Win7 上缺失它会报
     「无法启动此程序，因为计算机中丢失 api-ms-win-core-path-l1-1-0.dll」）。

用法：
    python _check_win_target.py
    python _check_win_target.py dist\\PCLRadiomics\\PCLRadiomics.exe
    python _check_win_target.py D:\\python\\envs\\mar\\python311.dll
"""
from __future__ import annotations

import os
import struct
import sys

# Windows 8 起才有的 API set（Win7 上必然缺失）
WIN8_API_SETS = (
    "api-ms-win-core-path-l1-1-0.dll",
    "api-ms-win-core-winrt-l1-1-0.dll",
    "api-ms-win-core-file-l1-2-0.dll",
    "api-ms-win-core-synch-l1-2-0.dll",
    "api-ms-win-core-com-l1-1-1.dll",
    "api-ms-win-core-processthreads-l1-1-1.dll",
)
# 明确要求 Windows 10 的组件
WIN10_API_SETS = (
    "api-ms-win-core-windowserrorreporting-l1-1-1.dll",
    "api-ms-win-core-featurestaging-l1-1-0.dll",
)


def pe_imports(path: str) -> list[str]:
    """纯标准库读取 PE 导入表，返回被导入的 DLL 名称（大写去重）。"""
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"MZ":
        raise ValueError("不是 PE 文件")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        raise ValueError("PE 签名不正确")
    coff = e_lfanew + 4
    n_sections, = struct.unpack_from("<H", data, coff + 2)
    size_opt, = struct.unpack_from("<H", data, coff + 16)
    opt = coff + 20
    magic, = struct.unpack_from("<H", data, opt)
    pe32plus = magic == 0x20B
    # 数据目录表偏移：PE32+ 为 112，PE32 为 96；导入表是第 2 项（索引 1）
    dd = opt + (112 if pe32plus else 96)
    imp_rva, imp_size = struct.unpack_from("<II", data, dd + 8)
    if not imp_rva:
        return []
    # 节表 → RVA 转文件偏移
    sec = opt + size_opt
    sections = []
    for i in range(n_sections):
        off = sec + i * 40
        va, = struct.unpack_from("<I", data, off + 12)
        raw_size, raw_ptr = struct.unpack_from("<II", data, off + 16)
        sections.append((va, raw_size, raw_ptr))

    def rva2off(rva: int) -> int:
        for va, raw_size, raw_ptr in sections:
            if va <= rva < va + max(raw_size, 1):
                return raw_ptr + (rva - va)
        return rva                                   # 退路：按 1:1 映射

    names, seen = [], set()
    off = rva2off(imp_rva)
    while True:
        entry = data[off:off + 20]
        if len(entry) < 20:
            break
        name_rva, = struct.unpack_from("<I", entry, 12)
        if not name_rva:
            break
        n_off = rva2off(name_rva)
        end = data.find(b"\0", n_off)
        name = data[n_off:end].decode("ascii", "replace")
        key = name.upper()
        if key not in seen:
            seen.add(key)
            names.append(name)
        off += 20
    return names


def toolchain_report() -> int:
    print("== 构建工具链 ==")
    print(f"  Python : {sys.version.split()[0]}  ({sys.executable})")
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 9):
        print("  → Python ≥ 3.9 **不支持 Windows 7**（3.9 起要求 Win8.1+）")
    else:
        print(f"  → Python {major}.{minor} 支持 Windows 7")
    try:
        import PySide6
        from PySide6 import QtCore
        print(f"  PySide6: {PySide6.__version__}  |  Qt {QtCore.qVersion()}")
        print("  → Qt 6 **不支持 Windows 7**（Qt 5.15 是最后一个支持 Win7 的版本）")
        print("\n结论：这份构建的**图形界面**最低要求 = Windows 10（64 位）")
    except Exception:                                         # noqa: BLE001
        print("  PySide6: 未安装（无界面构建）")
        print("\n结论：无 Qt 依赖，可面向较低版本 Windows（仍受上面的 Python 版本限制）")
    print("\n若必须在 Windows 7 上用：")
    print("  · 图形界面：不可行（Python 3.9+ 与 Qt 6 双重不支持）")
    print("  · 仅 API 服务：用 Python 3.8 构建（最后一个支持 Win7 的版本），"
          "系统需 Win7 SP1 + KB2533623 + KB2999226(UCRT) + VC++2015-2019 运行库")
    print("  · 单独补一个 api-ms-win-core-path-l1-1-0.dll 也无效：Qt 6 仍然起不来")
    return 0


def check_file(path: str) -> int:
    print(f"== PE 导入检查：{path} ==")
    if not os.path.exists(path):
        print("  文件不存在")
        return 1
    try:
        names = pe_imports(path)
    except Exception as e:                                     # noqa: BLE001
        print(f"  解析失败：{e}")
        return 1
    print(f"  共导入 {len(names)} 个 DLL")
    hits8 = [n for n in names if n.lower() in WIN8_API_SETS]
    hits10 = [n for n in names if n.lower() in WIN10_API_SETS]
    other = [n for n in names if n.lower().startswith("api-ms-win-")
             and n.lower() not in WIN8_API_SETS + WIN10_API_SETS]
    if hits8:
        print("\n  ✗ 需要 Windows 8+ 的 API set：")
        for n in hits8:
            print(f"      {n}   ← Windows 7 上缺失，会报「计算机中丢失 …dll」")
    if hits10:
        print("\n  ✗ 需要 Windows 10+ 的 API set：")
        for n in hits10:
            print(f"      {n}")
    if other:
        print("\n  · 其它 API set（多为 Win7 自带或可随 UCRT 补丁提供）：")
        for n in other[:12]:
            print(f"      {n}")
    if not (hits8 or hits10):
        print("\n  ✓ 未发现 Win8+/Win10+ 专有 API set（仍可能是 Qt6/其它依赖限制）")
    return 1 if (hits8 or hits10) else 0


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        rc = 0
        for p in argv[1:]:
            rc |= check_file(p)
        return rc
    return toolchain_report()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
