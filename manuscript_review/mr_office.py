# -*- coding: utf-8 -*-
"""OfficeCLI 调用封装。

为什么用 OfficeCLI 而不是自己改 XML
---------------------------------
Word 的原生批注（含回复线程）与 Track Changes 涉及 document.xml / comments.xml /
commentsExtended.xml / people.xml 四个部件与一堆 w14/w15 命名空间细节。
OfficeCLI 已经把这些做成受支持的操作，并且有 `batch`（原子执行 + 失败回滚），
比自己拼 XML 安全得多。本模块只做三件事：

    1. **绝不经过 shell**：批量操作写成 UTF-8 JSON 文件，用 ``--input`` 传入。
       这样彻底绕开 Windows 命令行代码页把中文变成乱码的问题（实测踩过）。
    2. **统一超时与错误解析**：OfficeCLI 失败时返回 JSON 或纯文本，两种都处理。
    3. **原子性**：一次审阅的全部写操作放进**一个 batch**，
       任一条失败则整批回滚，不会产出"改了一半"的稿件。

路径与可用性
-----------
OfficeCLI 是随 Node 全局安装的 CLI（``officecli``）。这里按
环境变量 → PATH → 常见安装位置 的顺序探测，探测不到时明确报错，
让界面能告诉用户"请先安装 officecli"而不是静默失败。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

# Windows 上避免弹出控制台黑框
if os.name == "nt":                                                # pragma: no cover
    _STARTUP = subprocess.STARTUPINFO()
    _STARTUP.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _CREATE_NO_WINDOW = 0x08000000
else:
    _STARTUP = None
    _CREATE_NO_WINDOW = 0

# 用户明确指定优先
ENV_KEY = "OFFICECLI_PATH"
DEFAULT_TIMEOUT = 180


@dataclass
class CmdResult:
    ok: bool = False
    code: int = -1
    stdout: str = ""
    stderr: str = ""
    data: dict = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict:
        return {"ok": self.ok, "code": self.code, "error": self.error,
                "stdout": self.stdout[-2000:], "stderr": self.stderr[-2000:]}


@dataclass
class BatchResult:
    ok: bool = False
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    rolled_back: bool = False
    results: list = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {"ok": self.ok, "total": self.total, "succeeded": self.succeeded,
                "failed": self.failed, "rolled_back": self.rolled_back,
                "error": self.error,
                "results": [{"index": r.get("index"), "success": r.get("success"),
                             "output": str(r.get("output") or "")[:400],
                             "error": str(r.get("error") or "")[:400]}
                            for r in self.results]}


# --------------------------------------------------------------------------- 探测
_CANDIDATES = (
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "OfficeCLI", "officecli.exe"),
    os.path.join(os.environ.get("APPDATA", ""), "npm", "officecli.cmd"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "npm-global", "officecli.cmd"),
    "/usr/local/bin/officecli",
    "/opt/homebrew/bin/officecli",
)

_EXE_CACHE: str | None = None


def exe() -> str:
    """探测 officecli 可执行文件。找不到返回空串。"""
    global _EXE_CACHE
    if _EXE_CACHE is not None:
        return _EXE_CACHE
    p = os.environ.get(ENV_KEY, "").strip()
    if p and os.path.exists(p):
        _EXE_CACHE = p
        return p
    for name in ("officecli", "officecli.cmd", "officecli.exe"):
        w = shutil.which(name)
        if w:
            _EXE_CACHE = w
            return w
    for c in _CANDIDATES:
        if c and os.path.exists(c):
            _EXE_CACHE = c
            return c
    _EXE_CACHE = ""
    return ""


def available() -> dict:
    """就绪情况：给界面显示用。"""
    e = exe()
    info = {"available": bool(e), "path": e, "version": "", "error": ""}
    if not e:
        info["error"] = ("未找到 officecli。请先安装：npm i -g officecli，"
                         f"或设置环境变量 {ENV_KEY} 指向可执行文件。")
        return info
    r = _run([e, "--version"], timeout=30)
    info["version"] = (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else ""
    return info


def _run(args: list[str], timeout: int = DEFAULT_TIMEOUT,
         cwd: str = "") -> CmdResult:
    """执行一次 officecli。**始终用参数列表**，不拼 shell 字符串。"""
    r = CmdResult()
    try:
        kw = {"capture_output": True, "timeout": timeout}
        if cwd:
            kw["cwd"] = cwd
        if os.name == "nt":                                        # pragma: no cover
            kw["startupinfo"] = _STARTUP
            kw["creationflags"] = _CREATE_NO_WINDOW
        p = subprocess.run(args, **kw)
        r.code = p.returncode
        r.stdout = _dec(p.stdout)
        r.stderr = _dec(p.stderr)
        r.ok = p.returncode == 0
        if not r.ok:
            r.error = _first_error(r.stdout, r.stderr) or f"officecli 退出码 {r.code}"
        return r
    except subprocess.TimeoutExpired:
        r.error = f"officecli 超时（>{timeout}s）"
        return r
    except FileNotFoundError:
        r.error = "找不到 officecli 可执行文件"
        return r
    except Exception as e:                                         # noqa: BLE001
        r.error = f"{type(e).__name__}: {e}"
        return r


def _dec(b) -> str:
    """officecli 输出在 Windows 上是 GBK，Linux 上是 UTF-8；两者都要能吃。"""
    if b is None:
        return ""
    if isinstance(b, str):
        return b
    for enc in ("utf-8-sig", "utf-8", "gbk", "cp936", "latin-1"):
        try:
            return b.decode(enc)
        except Exception:                                          # noqa: BLE001
            continue
    return b.decode("utf-8", "replace")


def _first_error(stdout: str, stderr: str) -> str:
    for blob in (stdout, stderr):
        for line in (blob or "").splitlines():
            if "ERROR" in line.upper():
                return line.strip()[:500]
    return (stderr or stdout or "").strip().splitlines()[-1][:500] if (stderr or stdout) else ""


# --------------------------------------------------------------------------- 高层操作
def close(path: str) -> CmdResult:
    """刷新并释放常驻进程（非 officecli 程序读文件前必须调用）。"""
    e = exe()
    if not e:
        return CmdResult(error="未找到 officecli")
    return _run([e, "close", path], timeout=60)


def save(path: str) -> CmdResult:
    e = exe()
    if not e:
        return CmdResult(error="未找到 officecli")
    return _run([e, "save", path], timeout=120)


def validate(path: str) -> CmdResult:
    """OpenXML schema 校验（Track Changes 的 pPr 警告属预期，见技能文档）。"""
    e = exe()
    if not e:
        return CmdResult(error="未找到 officecli")
    return _run([e, "validate", path], timeout=120)


def query(path: str, selector: str, timeout: int = DEFAULT_TIMEOUT) -> CmdResult:
    """查询元素，自动解析 --json 输出。"""
    e = exe()
    if not e:
        return CmdResult(error="未找到 officecli")
    r = _run([e, "query", path, selector, "--json"], timeout=timeout)
    r.data = _load_json(r.stdout)
    return r


def get(path: str, dom_path: str, timeout: int = DEFAULT_TIMEOUT) -> CmdResult:
    e = exe()
    if not e:
        return CmdResult(error="未找到 officecli")
    r = _run([e, "get", path, dom_path, "--json"], timeout=timeout)
    r.data = _load_json(r.stdout)
    return r


def raw(path: str, part: str = "/document", timeout: int = DEFAULT_TIMEOUT) -> CmdResult:
    """读文档部件的原始 XML。part 要带前导斜杠（officecli 的约定：/document）。"""
    e = exe()
    if not e:
        return CmdResult(error="未找到 officecli")
    if part and not part.startswith("/"):
        part = "/" + part
    r = _run([e, "raw", path, part], timeout=timeout)
    if not r.ok and "Unknown part" in (r.stderr or "") and part != "document":
        r2 = _run([e, "raw", path, "document"], timeout=timeout)
        if r2.ok:
            return r2
    return r


def _load_json(s: str) -> dict:
    """officecli --json 输出前可能有日志行，这里从第一个 { 开始解析。"""
    s = (s or "").strip()
    if not s:
        return {}
    i = s.find("{")
    if i < 0:
        return {}
    try:
        return json.loads(s[i:])
    except Exception:                                              # noqa: BLE001
        # 配平扫描
        depth, in_str, esc = 0, False, False
        for j in range(i, len(s)):
            c = s[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(s[i:j + 1])
                    except Exception:                              # noqa: BLE001
                        return {}
        return {}


def batch(path: str, commands: list[dict], timeout: int = DEFAULT_TIMEOUT,
          atomic: bool = True) -> BatchResult:
    """原子批量执行。

    commands 为 OfficeCLI 的原生 batch 语法：``{"command": "add", "parent": ...,
    "type": ..., "props": {...}}``。写入临时 UTF-8 文件后用 ``--input`` 传入。
    """
    res = BatchResult()
    e = exe()
    if not e:
        res.error = "未找到 officecli"
        return res
    if not commands:
        res.ok = True
        return res
    res.total = len(commands)
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="mr_batch_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(commands, fh, ensure_ascii=False, indent=1)
        r = _run([e, "batch", path, "--input", tmp, "--json"], timeout=timeout)
        d = r.data if r.data else _load_json(r.stdout)
        if not d:
            # 纯文本输出（如整批早期失败）
            res.error = r.error or _first_error(r.stdout, r.stderr) or "officecli batch 无输出"
            res.rolled_back = True
            return res
        data = d.get("data") or {}
        res.results = data.get("results") or []
        summ = data.get("summary") or {}
        res.succeeded = int(summ.get("succeeded") or 0)
        res.failed = int(summ.get("failed") or 0)
        res.total = int(summ.get("total") or res.total)
        res.rolled_back = bool(summ.get("atomicRolledBack"))
        res.ok = bool(d.get("success")) and res.failed == 0
        if not res.ok:
            errs = [f"[{x.get('index')}] {x.get('error')}"
                    for x in res.results if not x.get("success")]
            res.error = ("批量操作失败" + ("（整批已回滚，稿件未被修改）"
                                          if res.rolled_back else "")) + "：" + \
                        "；".join(errs[:5])
        return res
    finally:
        try:
            os.remove(tmp)
        except Exception:                                          # noqa: BLE001
            pass


# --------------------------------------------------------------------------- 结构查询助手
def comments(path: str) -> list[dict]:
    r = query(path, "comment")
    return ((r.data or {}).get("data") or {}).get("results") or []


def paragraphs(path: str) -> list[dict]:
    r = query(path, "paragraph")
    return ((r.data or {}).get("data") or {}).get("results") or []


def revisions(path: str) -> list[dict]:
    r = query(path, "revision")
    return ((r.data or {}).get("data") or {}).get("results") or []


def runs_in(path: str, dom_path: str) -> list[dict]:
    """取某段的 run 列表（含修订信息），用于确定 find/replace 的安全边界。"""
    r = get(path, dom_path)
    res = ((r.data or {}).get("data") or {}).get("results") or []
    if not res:
        return []
    return (res[0].get("children") or [])


def dom_path_of(path: str, para_idx: int) -> str:
    """把 Python 侧的段号转成 OfficeCLI 的 DOM 路径。"""
    return f"/body/p[{para_idx}]"


def para_id_of(path: str, para_idx: int) -> str:
    """读某段的 w14:paraId（存在则优先用它做锚点，比序号更稳）。"""
    r = get(path, f"/body/p[{para_idx}]")
    res = ((r.data or {}).get("data") or {}).get("results") or []
    if not res:
        return ""
    return str(((res[0].get("format") or {}).get("paraId")) or "")


def para_count(path: str) -> int:
    return len(paragraphs(path))


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                              # noqa: BLE001
        pass
    print(json.dumps(available(), ensure_ascii=False, indent=1))
    if len(sys.argv) > 1:
        print("段落数：", para_count(sys.argv[1]))
        print("批注数：", len(comments(sys.argv[1])))
