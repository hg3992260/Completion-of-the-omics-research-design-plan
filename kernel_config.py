# -*- coding: utf-8 -*-
"""内核配置层：直接读写 opencode 自己的配置格式，不做第二套真值。

设计原则（见 opencode-embedding-plan.md §5）：
    "与 opencode 一致" = 复用同一套文件与语义，宿主只做界面。
    凡 HTTP 有写接口的走 HTTP；没有的（skill / agent）落到 opencode 自己的文件；
    密钥一律 0600。

本模块只管文件，不管进程 —— 进程归 kernel_client.py。

落点（全部在隔离 home 下，已核实 opencode 的加载路径）：
    <kernel_home>/config/opencode/opencode.json   ← Global.Path.config（config.ts:272-274）
    <kernel_home>/data/opencode/auth.json         ← path.join(Global.Path.data, "auth.json")
                                                     （auth/index.ts:10，0600）
    <kernel_home>/config/opencode/{skill,skills}/<name>/SKILL.md
                                                  ← {skill,skills}/**/SKILL.md
                                                     （skill/index.ts:24）

⚠️ 目录层级易错：XDG_DATA_HOME 指向 <kernel_home>/data 时，opencode 自己再拼一层
   "opencode"，所以 auth.json 实际在 <kernel_home>/data/opencode/auth.json。
   本模块统一用 ensure_home_layout() 给出的路径，禁止调用方手拼。
"""

from __future__ import annotations

import json
import os
import re
import shutil
from typing import Any

from app_paths import config_dir, data_path
import kernel_client as kc

#: MCP 请求超时。opencode 默认只有 5000 ms（core/src/v1/config/mcp.ts:21），
#: 而宿主的 manuscript_review / design_finalize 要跑几分钟 —— 必须显式调大，
#: 否则内核调用这些工具会直接超时失败。
MCP_TIMEOUT_MS = 600_000

#: 宿主 MCP 服务在 opencode 配置里的名字（对应 UI 里显示的 server 名）
HOST_MCP_NAME = "radiomics-workbench"

_SCHEMA = "https://opencode.ai/config.json"


# --------------------------------------------------------------------------- 路径

def kernel_home() -> str:
    return kc.kernel_home()


def paths() -> dict[str, str]:
    """一次拿到全部关键路径（带目录创建）。"""
    p = kc.ensure_home_layout()
    p["config_file"] = os.path.join(p["config"], "opencode.json")
    p["auth_file"] = os.path.join(p["data"], "auth.json")
    p["skill_dir"] = os.path.join(p["config"], "skill")
    p["agent_dir"] = os.path.join(p["config"], "agent")
    for key in ("skill_dir", "agent_dir"):
        os.makedirs(p[key], exist_ok=True)
    return p


def system_paths() -> dict[str, str]:
    """用户真实 opencode 的路径（只读，用于"从系统导入"）。

    注意：xdg-basedir@5.1.0 无 Windows 特判，默认即 ~/.local/share 与 ~/.config。
    """
    home = os.path.expanduser("~")
    return {
        "data": os.path.join(home, ".local", "share", "opencode"),
        "config": os.path.join(home, ".config", "opencode"),
        "auth_file": os.path.join(home, ".local", "share", "opencode", "auth.json"),
    }


# ----------------------------------------------------------------------- 配置文件

def read_config() -> dict:
    p = paths()
    if not os.path.exists(p["config_file"]):
        return {}
    try:
        with open(p["config_file"], "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:                                                  # noqa: BLE001
        return {}


def write_config(cfg: dict) -> str:
    p = paths()
    cfg = dict(cfg or {})
    cfg.setdefault("$schema", _SCHEMA)
    with open(p["config_file"], "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    return p["config_file"]


def merge_config(patch: dict) -> dict:
    """浅合并（顶层键覆盖；mcp/provider 这类字典按键合并）。"""
    cfg = read_config()
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            cfg[key] = {**cfg[key], **value}
        else:
            cfg[key] = value
    write_config(cfg)
    return cfg


def set_model(provider_model: str) -> dict:
    """写顶层 model，形如 "deepseek/deepseek-v4-pro"。"""
    return merge_config({"model": provider_model})


def set_mcp_server(name: str, url: str | None = None,
                   command: list[str] | None = None,
                   timeout_ms: int = MCP_TIMEOUT_MS,
                   environment: dict | None = None,
                   enabled: bool = True) -> dict:
    """在 opencode.json 里 upsert 一个 MCP server。

    ⚠️ 配置键是 `mcp`，不是 Claude Desktop 的 `mcpServers`
       （schema: core/src/v1/config/config.ts:113 + v1/config/mcp.ts:6-63）。
    """
    if url:
        entry: dict[str, Any] = {"type": "remote", "url": url, "enabled": enabled,
                                 "timeout": timeout_ms}
    elif command:
        entry = {"type": "local", "command": list(command), "enabled": enabled,
                 "timeout": timeout_ms}
        if environment:
            entry["environment"] = dict(environment)
    else:
        raise ValueError("url 或 command 必须给一个")

    cfg = read_config()
    mcp = dict(cfg.get("mcp") or {})
    mcp[name] = entry
    cfg["mcp"] = mcp
    write_config(cfg)
    return entry


def remove_mcp_server(name: str) -> bool:
    cfg = read_config()
    mcp = dict(cfg.get("mcp") or {})
    if name not in mcp:
        return False
    mcp.pop(name)
    cfg["mcp"] = mcp
    write_config(cfg)
    return True


# ------------------------------------------------------------------------- 凭据

def read_auth() -> dict:
    """读隔离 auth.json。尊重 OPENCODE_AUTH_CONTENT 覆盖（auth/index.ts:59-63）。"""
    injected = os.environ.get("OPENCODE_AUTH_CONTENT")
    if injected:
        try:
            return json.loads(injected)
        except Exception:                                              # noqa: BLE001
            pass
    p = paths()
    if not os.path.exists(p["auth_file"]):
        return {}
    try:
        with open(p["auth_file"], "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:                                                  # noqa: BLE001
        return {}


def write_auth(auth: dict) -> str:
    """写隔离 auth.json，0600。复刻 Auth.set 的尾斜杠归一化语义（auth/index.ts:73-89）。"""
    p = paths()
    normalized: dict[str, Any] = {}
    for key, value in (auth or {}).items():
        norm = key.rstrip("/")
        normalized[norm] = value
    with open(p["auth_file"], "w", encoding="utf-8") as fh:
        json.dump(normalized, fh, ensure_ascii=False, indent=2)
    try:
        os.chmod(p["auth_file"], 0o600)
    except Exception:                                                  # noqa: BLE001
        pass
    return p["auth_file"]


def set_api_key(provider: str, key: str, metadata: dict | None = None) -> str:
    """写一个 api 型凭据。schema 与 opencode 完全一致：
    {"<provider>": {"type": "api", "key": "...", "metadata"?: {...}}}
    """
    auth = read_auth()
    entry: dict[str, Any] = {"type": "api", "key": key}
    if metadata:
        entry["metadata"] = dict(metadata)
    auth[provider.rstrip("/")] = entry
    return write_auth(auth)


def remove_api_key(provider: str) -> bool:
    auth = read_auth()
    if provider.rstrip("/") not in auth:
        return False
    auth.pop(provider.rstrip("/"), None)
    write_auth(auth)
    return True


def list_credentials() -> list[dict]:
    """列出凭据的**脱敏**摘要（绝不返回 key 明文）。"""
    from llm_client import mask
    out = []
    for provider, info in (read_auth() or {}).items():
        if not isinstance(info, dict):
            continue
        out.append({
            "provider": provider,
            "type": info.get("type"),
            "key": mask(info.get("key") or "") if info.get("key") else "",
            "has_metadata": bool(info.get("metadata")),
        })
    return sorted(out, key=lambda x: x["provider"])


def import_from_system(providers: list[str] | None = None) -> dict:
    """从用户真实 opencode 的 auth.json **单向导入**到隔离 home。

    隔离模式（D3）下系统 opencode 的凭据不可见，这是补偿手段。
    只读导出、不建立持续共享，因此不破坏隔离性（plan §6.3①）。
    """
    src = system_paths()["auth_file"]
    if not os.path.exists(src):
        return {"ok": False, "reason": f"系统 auth.json 不存在：{src}", "imported": []}
    try:
        with open(src, "r", encoding="utf-8") as fh:
            system_auth = json.load(fh) or {}
    except Exception as e:                                             # noqa: BLE001
        return {"ok": False, "reason": f"读取失败：{e}", "imported": []}

    auth = read_auth()
    imported = []
    for provider, info in system_auth.items():
        if providers and provider not in providers:
            continue
        if not isinstance(info, dict):
            continue
        auth[provider.rstrip("/")] = info
        imported.append(provider)
    if imported:
        write_auth(auth)
    return {"ok": True, "imported": sorted(imported), "source": src}


def import_host_llm_key() -> dict:
    """把宿主自己的凭据链导入成一个 api 凭据。

    宿主已有 secret.json → LLM_API_KEY → <api_key_env> → ~/.dsh/.credentials.yaml
    的完整解析链（llm_client.load_config），直接复用，不必让用户再配一遍。
    """
    try:
        from llm_client import load_config
    except Exception as e:                                             # noqa: BLE001
        return {"ok": False, "reason": f"载入 llm_client 失败：{e}"}
    cfg = load_config()
    key = cfg.get("api_key")
    if not key:
        return {"ok": False, "reason": "宿主凭据链没有可用密钥"}
    base = (cfg.get("base_url") or "").lower()
    provider = "deepseek" if "deepseek" in base else "openai-compatible"
    set_api_key(provider, key)
    return {"ok": True, "provider": provider, "source": cfg.get("key_source"),
            "endpoint": cfg.get("base_url"), "model": cfg.get("model")}


# ------------------------------------------------------------------------- 技能

_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def skill_root() -> str:
    """opencode 会在 {skill,skills}/**/SKILL.md 下发现技能（skill/index.ts:24）。"""
    return paths()["skill_dir"]


def list_skills() -> list[dict]:
    """列出内核可见的技能（隔离 home 内的）。

    注意：内核还会读用户级 ~/.claude/skills 与 ~/.agents/skills
    （未设 OPENCODE_TEST_HOME，见 plan §6.3②），那些不在本函数范围内。
    """
    root = skill_root()
    out = []
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        md = os.path.join(root, name, "SKILL.md")
        if not os.path.isfile(md):
            continue
        meta = parse_skill_frontmatter(md)
        out.append({"name": meta.get("name") or name, "dir": name,
                    "description": meta.get("description", ""), "path": md})
    return out


def parse_skill_frontmatter(path: str) -> dict:
    """极简 YAML frontmatter 解析（只取 name / description，够用且无新依赖）。"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except Exception:                                                  # noqa: BLE001
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end]
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if key in ("name", "description"):
            out[key] = value.strip().strip('"').strip("'")
    return out


def install_skill(name: str, content: str, description: str = "") -> dict:
    """安装/覆盖一个技能。

    content 是 SKILL.md 的正文；frontmatter 由本函数生成，
    格式与 opencode 一致（name 必填、description 可选 —— skill/index.ts:53-59）。
    """
    if not _SKILL_NAME_RE.match(name or ""):
        raise ValueError(f"技能名不合法：{name!r}（只允许字母数字与 . _ -，且字母数字开头）")
    root = skill_root()
    target = os.path.join(root, name)
    os.makedirs(target, exist_ok=True)
    fm = [f"name: {name}"]
    if description:
        fm.append(f"description: {description}")
    body = (content or "").strip()
    text = "---\n" + "\n".join(fm) + "\n---\n\n" + body + "\n"
    md = os.path.join(target, "SKILL.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write(text)
    return {"ok": True, "name": name, "path": md}


def remove_skill(name: str) -> bool:
    target = os.path.join(skill_root(), name)
    if not os.path.isdir(target):
        return False
    shutil.rmtree(target, ignore_errors=True)
    return True


# ------------------------------------------------------------------------- Agent

def list_agents() -> list[dict]:
    """列出隔离 home 内的自定义 agent（{agent,agents}/*.md）。

    内置 agent（build/plan/general/explore…）来自 opencode 自身，不在文件里。
    """
    out = []
    for root in (paths()["agent_dir"], os.path.join(paths()["config"], "agents")):
        if not os.path.isdir(root):
            continue
        for fn in sorted(os.listdir(root)):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(root, fn)
            meta = parse_skill_frontmatter(path)
            out.append({"name": fn[:-3], "mode": meta.get("mode", "all"),
                        "description": meta.get("description", ""), "path": path})
    return out


# --------------------------------------------------------------------------- 总览

def summary() -> dict:
    """控制台/自检用的配置总览（脱敏）。"""
    p = paths()
    cfg = read_config()
    return {
        "home": p["home"],
        "config_file": p["config_file"],
        "auth_file": p["auth_file"],
        "exists": {
            "config": os.path.exists(p["config_file"]),
            "auth": os.path.exists(p["auth_file"]),
        },
        "model": cfg.get("model"),
        "mcp": sorted((cfg.get("mcp") or {}).keys()),
        "mcp_timeouts": {k: (v or {}).get("timeout") for k, v in (cfg.get("mcp") or {}).items()},
        "credentials": list_credentials(),
        "skills": [s["name"] for s in list_skills()],
        "agents": [a["name"] for a in list_agents()],
        "system": system_paths(),
    }


if __name__ == "__main__":
    print(json.dumps(summary(), ensure_ascii=False, indent=2))
