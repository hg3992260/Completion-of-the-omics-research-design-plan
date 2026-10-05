# -*- coding: utf-8 -*-
"""LLM 语义审阅层：确定性信号覆盖不到的规范条目，交给模型逐条判断。

分工原则
--------
· 确定性层（mr_signals）负责**能证据化**的硬缺陷：参数缺失、ICC 未做、
  注册号没写……结论可复现、可追责。
· 本层负责**语义判断**：摘要里缺哪个通用模型组件、Discussion 有没有真的
  "move on from the Results"、时态与确定性是否匹配、gap 是不是写成了问句……
  这些无法用正则判定，但模型很擅长。

为了不让模型自由发挥，每次调用都：
    1. 只给它**一层**、**一个批次**（≤ `BATCH` 条）的规范条目；
    2. 附带该层相关的**带段号手稿正文**（段号是回写锚点，必须让模型引用）；
    3. 强制 JSON 输出，并要求每条缺陷给出 `para`（段号）或 `quote`（原文片段）；
    4. 结果按内容哈希缓存，同一份手稿重跑不重复花钱。

输出缺陷结构与 mr_signals.defects() 完全同构，便于 mr_engine 合并去重。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field

from manuscript_review.mr_review_layers import (CHAPTER_TITLES, LAYERS, LAYER_ORDER,
                                                SEVERITY_RANK, by_layer)
from manuscript_review import mr_docx

BATCH = 10                 # 每次调用送审的规范条目数
MAX_TOKENS = 6000
CACHE_VERSION = "v1"

# LLM 输出允许的严重度取值
_SEV = ("关键", "主要", "一般")
_VERDICT = ("missing", "insufficient", "wrong", "ok")


SYSTEM_PROMPT = """你是一位同时具备三重身份的资深审稿人：影像组学/多组学方法学专家、生物统计学家、\
以及 SCI 论文写作教练。你的任务是**审查一份已成稿的手稿**，逐条对照给定的规范条目，指出手稿的缺陷。

严格执行以下要求：
1. 只输出 JSON 数组，不要输出任何解释文字、不要用 Markdown 代码块包裹。
2. 数组每个元素对应一条**确实存在**的缺陷；确实合格的条目不输出。
3. 每条缺陷必须给出**手稿中的证据**：`para` 是段号（手稿正文里方括号里的数字），
   `quote` 是能支撑你判断的原文片段（缺失类的可以留空字符串）。
4. 严禁编造。手稿里没有的内容绝对不能说"手稿指出……"；判断"未报告"必须有依据
   （例如：通读方法与结果，未见任何关于重采样的表述）。
5. 不要输出"建议加强方法学描述"这类空话。`suggestion` 必须是作者能直接抄进
   手稿的具体文字或具体参数名。
6. 严重度只能取三个值：
   关键 = 规范强制项，缺失即无法复现或被直接拒稿；
   主要 = 规范推荐项，缺失会被审稿人质疑；
   一般 = 写作语体与内容边界问题。
7. 中文输出，专业、简洁（每条 why ≤ 80 字，suggestion ≤ 120 字）。"""


USER_TMPL = """【本次审阅的层次】{layer_name}（{layer_sub}）
{layer_why}
{design_block}
【手稿相关章节正文】（行首 [数字] 为该段段号，回写批注时用作锚点）
---
{body}
---

【需要你逐条对照的规范条目】
{items}

【输出格式】严格输出如下 JSON 数组（无缺陷则输出 []）：
[
  {{
    "req_id": "上面某条规范条目的 req_id（必须原样照抄）",
    "verdict": "missing | insufficient | wrong",
    "severity": "关键 | 主要 | 一般",
    "title": "一句话缺陷名，≤20 字",
    "why": "为什么这是缺陷，指明违反的规范条目",
    "evidence": "手稿中支撑该判断的原文片段；判为缺失则留空",
    "para": 段落号数字（判为缺失且无对应段落时填 0）,
    "quote": "用于定位的原文片段（应与 evidence 一致或更短）",
    "suggestion": "作者可直接采纳的修改文字或需补充的具体参数"
  }}
]

判断口径：
· verdict=missing      —— 该规范条目要求的内容在手稿中**完全找不到**；
· verdict=insufficient —— 提到了但信息不足（例如只写"增强CT"不给扫描参数）；
· verdict=wrong        —— 写了但与规范相悖或与手稿其他部分矛盾（例如把结论写成因果）。"""


@dataclass
class ReviewCall:
    """一次 LLM 调用的记录，用于界面展示进度与审计。"""
    layer: str
    batch_index: int
    req_ids: list[str]
    ok: bool = False
    defects: list = field(default_factory=list)
    error: str = ""
    elapsed: float = 0.0
    cached: bool = False
    raw_chars: int = 0

    def to_dict(self) -> dict:
        return {"layer": self.layer, "batch": self.batch_index,
                "req_ids": list(self.req_ids), "ok": self.ok,
                "defects": len(self.defects), "error": self.error,
                "elapsed": round(self.elapsed, 1), "cached": self.cached}


# --------------------------------------------------------------------------- 缓存
def cache_dir() -> str:
    try:
        from app_paths import data_path
        d = data_path("manuscript_review", "llm_cache")
    except Exception:                                              # noqa: BLE001
        d = os.path.join(os.path.expanduser("~"), ".pclradiomics_mr_cache")
    os.makedirs(d, exist_ok=True)
    return d


def _cache_key(layer: str, req_ids: list[str], body: str, model: str) -> str:
    h = hashlib.sha256()
    h.update(CACHE_VERSION.encode())
    h.update(layer.encode())
    h.update(model.encode())
    h.update("\x00".join(req_ids).encode())
    h.update(hashlib.sha256(body.encode("utf-8")).hexdigest().encode())
    return h.hexdigest()[:24]


def _cache_get(key: str):
    p = os.path.join(cache_dir(), f"{key}.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:                                          # noqa: BLE001
            return None
    return None


def _cache_put(key: str, payload: dict) -> None:
    try:
        with open(os.path.join(cache_dir(), f"{key}.json"), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
    except Exception:                                              # noqa: BLE001
        pass


# --------------------------------------------------------------------------- 解析
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I)


def _strip_fence(s: str) -> str:
    s = (s or "").strip()
    s = _FENCE_RE.sub("", s)
    return s.strip()


def extract_json_array(text: str) -> list | None:
    """从模型输出里稳健地取出 JSON 数组。

    优先直接解析；失败则扫描第一个 `[` 到**配平**的 `]`（跳过字符串内的括号）。
    """
    s = _strip_fence(text)
    if not s:
        return None
    for cand in (s, s[s.find("["):] if "[" in s else ""):
        if not cand:
            continue
        try:
            d = json.loads(cand)
            if isinstance(d, list):
                return d
            if isinstance(d, dict) and isinstance(d.get("defects"), list):
                return d["defects"]
        except Exception:                                          # noqa: BLE001
            pass
    # 配平扫描
    start = s.find("[")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
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
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    d = json.loads(s[start:i + 1])
                    return d if isinstance(d, list) else None
                except Exception:                                  # noqa: BLE001
                    return None
    return None


def _coerce_defect(raw: dict, req: dict, manuscript, layer: str) -> dict | None:
    """把模型返回的一条原始记录规范化成统一缺陷结构；不合格则丢弃。"""
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    why = str(raw.get("why") or "").strip()
    if not title and not why:
        return None
    sev = str(raw.get("severity") or "").strip()
    if sev not in _SEV:
        sev = req.get("severity") or "主要"
    verdict = str(raw.get("verdict") or "").strip().lower()
    if verdict not in _VERDICT:
        verdict = "insufficient" if str(raw.get("evidence") or "").strip() else "missing"

    # 段落锚点：先用模型给的段号，再用 quote 回查，最后退到章节首段
    para = raw.get("para") or raw.get("para_idx") or 0
    try:
        para = int(para)
    except Exception:                                              # noqa: BLE001
        para = 0
    quote = str(raw.get("quote") or raw.get("evidence") or "").strip()
    if not (1 <= para <= len(manuscript.paragraphs)):
        para = 0
    anchors = list(req.get("anchors") or [])
    if not para and quote:
        p = _locate_by_quote(manuscript, quote, anchors)
        para = p.idx if p else 0
    if not para:
        # 模型既没给段号也没给可用引文：用标题/理由里的具体名词回查
        p = _locate_by_terms(manuscript, f"{title} {why} {req.get('text', '')}", anchors)
        para = p.idx if p else 0

    return {
        "source": "llm",
        "layer": layer,
        "req_id": req["req_id"],
        "ref": req["ref"],
        "spec": req.get("spec", ""),
        "severity": sev,
        "verdict": verdict,
        "title": title or req["text"][:24],
        "why": why,
        "evidence": str(raw.get("evidence") or "").strip()[:400],
        "suggestion": str(raw.get("suggestion") or "").strip()[:600],
        "para_idx": para,
        "chapter": "",
        "anchors": list(req.get("anchors") or []),
        "quote": quote[:120],
        "signal": req.get("signal") or "",
    }

def _locate_by_quote(manuscript, quote: str, anchors: list[str]):
    """按原文片段定位段落：先精确包含，再退化到最长公共子串式模糊匹配。"""
    q = re.sub(r"[\s\u3000]+", "", quote or "")
    if len(q) < 4:
        return None
    cands = [p for p in manuscript.paragraphs if p.text]
    if anchors:
        pref = [p for p in cands if p.chapter in anchors]
        cands = pref or cands
    for p in cands:
        if q[:30] in re.sub(r"[\s\u3000]+", "", p.text):
            return p
    # 模糊：取 quote 的前 8 个非空白字符作探针
    probe = q[:8]
    for p in cands:
        if probe and probe in re.sub(r"[\s\u3000]+", "", p.text):
            return p
    return None


# 定位时值得从标题/理由里抽取的"具体名词"，抽到就能在正文里回查
_TERM_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9\-_\.]{2,}|"                     # 英文术语/软件名/指标
    r"[\u4e00-\u9fff]{2,10}(?:检验|分析|曲线|区间|参数|标准|模型|特征|"
    r"矩阵|方案|声明|清单|注册号|批号|同意|重叠|验证|校正|插补|种子)")


def _locate_by_terms(manuscript, text: str, anchors: list[str]):
    """当模型没给可用引文时，用标题/理由里的具体名词回查手稿段落。

    这样 LLM 缺陷也能拿到段落锚点，Word 批注才能挂到正确位置。
    只在目标章节内找；找不到返回 None，绝不硬凑。
    """
    terms = _TERM_RE.findall(text or "")
    if not terms:
        return None
    cands = [p for p in manuscript.paragraphs if p.text]
    if anchors:
        pref = [p for p in cands if p.chapter in anchors]
        cands = pref or cands
    best, score = None, 0
    for p in cands:
        norm = re.sub(r"[\s\u3000]+", "", p.text)
        hits = sum(1 for t in set(terms) if t.lower() in norm.lower())
        if hits > score:
            best, score = p, hits
    return best if score > 0 else None


# --------------------------------------------------------------------------- 主体
def _format_items(reqs: list[dict]) -> str:
    lines = []
    for r in reqs:
        kind = {"reports": "必报参数", "pitfall": "常见缺陷", "check": "检查项",
                "must": "必须写到", "must_not": "不得出现", "action": "必做动作",
                "goal": "阶段目标"}.get(r["kind"], r["kind"])
        lines.append(f"- req_id={r['req_id']} [{r['severity']}·{kind}] "
                     f"（{r['ref']}｜{r['spec']}）{r['text']}")
    return "\n".join(lines)


def _body_for(manuscript, layer: str, budget: int = 9000) -> str:
    keys = LAYERS[layer]["sections"]
    return mr_docx.chapter_digest(manuscript, keys, budget=budget)


def _dedupe(reqs: list[dict]) -> list[dict]:
    """同一段文本在多层可能重复出现，这里按 (ref, text) 去重，保留先出现的。"""
    seen, out = set(), []
    for r in reqs:
        k = (r["ref"], r["text"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def batches(layer: str, size: int = BATCH) -> list[list[dict]]:
    reqs = _dedupe(by_layer(layer))
    return [reqs[i:i + size] for i in range(0, len(reqs), size)]


def _design_block(design_context: str) -> str:
    """课题背景区块：把「这个课题本来打算怎么做」交给模型。

    为什么需要：手稿缺陷分两类 —— 违反通用规范的（正则/清单能查），
    以及**与课题自身意图不一致**的（例如课题预设了外部验证与前瞻队列，
    手稿只报了单中心内部验证）。后者只有在拿到课题背景时才判得出来。
    """
    txt = (design_context or "").strip()
    if not txt:
        return ""
    return ("\n【本手稿所属课题的背景】（用于判断手稿与课题意图是否一致；"
            "课题里写明却未在手稿中兑现的，属于缺陷）\n"
            + txt + "\n")


def review(client, manuscript, layers: list[str] | None = None,
           use_cache: bool = True, skip_signals: set[str] | None = None,
           max_batches: int = 0, on_progress=None,
           on_delta=None, design_context: str = ""
           ) -> tuple[list[dict], list[ReviewCall]]:
    """跑 LLM 语义审阅。

    Args:
        client: llm_client.LLMClient
        manuscript: mr_docx.Manuscript
        layers: 要审的层（默认三层全审）
        use_cache: 命中缓存则不调用模型
        skip_signals: 这些信号的条目已在确定性层覆盖，跳过以免重复报同一件事
        max_batches: >0 时限制每个层的批次数（调试/快速试跑）
        on_progress: 回调 (ReviewCall) —— 每批结束调用一次，供界面刷新
        on_delta: 流式回调 (text_piece)
        design_context: 课题背景快照（研究设想 + 各阶段定稿摘要）。
            给了它才能审出「手稿与课题意图不一致」这类缺陷。

    Returns:
        (defects, calls)
    """
    layers = layers or list(LAYER_ORDER)
    skip_signals = {s for s in (skip_signals or set()) if s}
    model = getattr(client, "model", "") or ""
    dblock = _design_block(design_context)
    all_defects: list[dict] = []
    calls: list[ReviewCall] = []

    for layer in layers:
        if layer not in LAYERS:
            continue
        body = _body_for(manuscript, layer)
        if not body.strip():
            calls.append(ReviewCall(layer=layer, batch_index=-1, req_ids=[],
                                    ok=False, error="手稿缺少该层的相关章节，已跳过。"))
            if on_progress:
                on_progress(calls[-1])
            continue
        bl = batches(layer)
        if skip_signals:
            bl = [[r for r in b if not (r.get("signal") and r["signal"] in skip_signals)]
                  for b in bl]
            bl = [b for b in bl if b]
        if max_batches:
            bl = bl[:max_batches]

        for bi, reqs in enumerate(bl, 1):
            call = ReviewCall(layer=layer, batch_index=bi,
                              req_ids=[r["req_id"] for r in reqs])
            t0 = time.time()
            # 缓存键必须带上课题背景：换了课题，同一批条目的结论可能不同
            key = _cache_key(layer, call.req_ids,
                             body + "\x00" + dblock, model)
            cached = _cache_get(key) if use_cache else None
            if cached is not None:
                call.cached = True
                call.ok = True
                call.defects = cached.get("defects") or []
                call.elapsed = 0.0
            else:
                msgs = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_TMPL.format(
                        layer_name=LAYERS[layer]["name"],
                        layer_sub=LAYERS[layer]["sub"],
                        layer_why=LAYERS[layer]["why"],
                        design_block=dblock,
                        body=body, items=_format_items(reqs))},
                ]
                try:
                    out = client.chat(msgs, stream=on_delta is not None,
                                      on_delta=on_delta,
                                      temperature=0.1, max_tokens=MAX_TOKENS)
                    raw = out.get("content") or ""
                    call.raw_chars = len(raw)
                    arr = extract_json_array(raw)
                    if arr is None:
                        call.ok = False
                        call.error = ("模型未按 JSON 格式输出，本批结果已丢弃。"
                                      f"原始输出前 120 字：{raw[:120]}")
                    else:
                        reqmap = {r["req_id"]: r for r in reqs}
                        seen = set()
                        for item in arr:
                            rid = str((item or {}).get("req_id") or "").strip()
                            req = reqmap.get(rid)
                            if req is None:
                                # 模型写错 req_id 时，退化为按文本近似匹配
                                req = _match_req(item, reqs)
                            if req is None:
                                continue
                            d = _coerce_defect(item, req, manuscript, layer)
                            if d is None:
                                continue
                            k = (d["req_id"], d["title"])
                            if k in seen:
                                continue
                            seen.add(k)
                            call.defects.append(d)
                        call.ok = True
                except Exception as e:                             # noqa: BLE001
                    call.ok = False
                    call.error = f"{type(e).__name__}: {e}"
                call.elapsed = time.time() - t0
                if call.ok and use_cache:
                    _cache_put(key, {"defects": call.defects, "ts": int(time.time()),
                                     "model": model})
            all_defects.extend(call.defects)
            calls.append(call)
            if on_progress:
                on_progress(call)

    return all_defects, calls


def _match_req(item: dict, reqs: list[dict]) -> dict | None:
    """模型把 req_id 写错时，用 title/why 与规范条目文本做近似匹配。"""
    import difflib
    blob = f"{item.get('title') or ''}{item.get('why') or ''}"
    if not blob.strip():
        return None
    best, score = None, 0.0
    for r in reqs:
        s = difflib.SequenceMatcher(None, blob, r["text"]).ratio()
        if s > score:
            best, score = r, s
    return best if score >= 0.34 else None


# --------------------------------------------------------------------------- 汇总
def merge_defects(primary: list[dict], secondary: list[dict]) -> list[dict]:
    """合并确定性缺陷与 LLM 缺陷。

    去重口径：同一信号（signal 相同）或同一规范条目（req_id 相同）且段落相同，
    只保留确定性层的那条 —— 它带可核验证据，比模型的判断更可信。
    """
    out = list(primary)
    keys = {(d.get("signal") or d.get("req_id"), d.get("para_idx")) for d in primary}
    sigs = {d.get("signal") for d in primary if d.get("signal")}
    for d in secondary:
        sig = d.get("signal") or ""
        if sig and sig in sigs:
            continue
        k = (sig or d.get("req_id"), d.get("para_idx"))
        if k in keys:
            continue
        keys.add(k)
        out.append(d)
    return out


def sort_defects(defects: list[dict]) -> list[dict]:
    """按 严重度 → 有段落锚点优先 → 层 → 段号 排序。

    "有锚点优先"是刻意的：能指到具体段落的缺陷，作者打开 Word 就能跳过去改；
    定位不到的（手稿里根本没写这类内容，例如"未做样本量估算"）
    放在后面统一处理。若按段号直接排，段号 0 会全部挤到最前面，
    读者第一眼看到的全是最虚的条目。
    """
    order = {k: i for i, k in enumerate(LAYER_ORDER)}

    def keyf(d):
        para = d.get("para_idx") or 0
        return (SEVERITY_RANK.get(d.get("severity"), 9),
                0 if para else 1,
                order.get(d.get("layer"), 9),
                para if para else 10 ** 6,
                d.get("req_id") or "")
    return sorted(defects, key=keyf)


def summarize(defects: list[dict]) -> dict:
    out = {"total": len(defects), "关键": 0, "主要": 0, "一般": 0,
           "by_layer": {}, "by_source": {"signal": 0, "llm": 0}}
    for d in defects:
        sev = d.get("severity")
        if sev in out:
            out[sev] += 1
        lay = d.get("layer") or "?"
        out["by_layer"].setdefault(lay, {"total": 0, "关键": 0, "主要": 0, "一般": 0})
        out["by_layer"][lay]["total"] += 1
        if sev in ("关键", "主要", "一般"):
            out["by_layer"][lay][sev] += 1
        src = d.get("source") or "llm"
        out["by_source"][src] = out["by_source"].get(src, 0) + 1
    return out


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                              # noqa: BLE001
        pass
    print("可用层：", {k: len(_dedupe(by_layer(k))) for k in LAYER_ORDER})
    print("每层批次数：", {k: len(batches(k)) for k in LAYER_ORDER})
    print("JSON 解析自测：",
          extract_json_array('```json\n[{"req_id":"x","title":"t"}]\n```'))
    print("容错自测：", extract_json_array('好的，结果如下：[{"a":[1,2]}] 以上。'))
