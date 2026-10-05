# -*- coding: utf-8 -*-
"""手稿结构解析：把 DOCX 拆成带稳定锚点的段落，并把段落映射到论文章节。

为什么不用 python-docx 直接读就完事
----------------------------------
审阅结果最终要**落回 Word**，所以解析出的每一段都必须带一个"能回写的地址"。
OfficeCLI 的地址形式是 ``/body/p[N]``（N 为 1-based 的段落序号）。
因此本模块的核心产出是：

    Paragraph(idx, text, chapter, para_id, style, is_heading)

其中 ``idx`` 就是 OfficeCLI 的段落序号，**只要不在它前面插入段落就恒定不变**。
正文改写用 find/replace（不改变段落数），新增补正段落则**逆序插入**，
所以全文只解析一次、地址一次算好，后续所有回写都安全。

章节映射
--------
中英文手稿的章节标题写法差异很大，这里用「编号 + 关键词」两路匹配：

    1. 形如 ``3 结果`` / ``2.1 研究对象`` / ``Results`` / ``MATERIALS AND METHODS``
       的编号或整行标题 → 判为标题段并归入对应章节；
    2. 其余段落继承上一个标题的章节（前导段落先暂存为 ``title`` 候选，
       遇到摘要或引言后回填）。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- 章节词典
# 顺序即优先级：先匹配到的优先（"材料与方法" 必须先于 "方法" 被识别）
CHAPTER_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("abstract", ("摘要", "abstract", "summary", "结构化摘要")),
    ("keywords", ("关键词", "关键字", "keywords", "key words")),
    ("data_availability", ("数据可用性", "数据获取", "data availability",
                           "availability of data", "数据与代码可用性")),
    ("ethics", ("伦理声明", "伦理审批", "伦理学", "ethics statement",
                "ethical approval", "伦理")),
    ("funding", ("基金", "资助", "funding", "financial support")),
    ("coi", ("利益冲突", "conflicts of interest", "conflict of interest",
             "competing interests", "声明")),
    ("acknowledgements", ("致谢", "acknowledgement", "acknowledgment")),
    ("references", ("参考文献", "references", "reference list")),
    ("supplementary", ("补充材料", "附录", "supplementary", "appendix")),
    ("conclusion", ("结论", "总结", "conclusion", "conclusions")),
    ("discussion", ("讨论", "discussion")),
    ("introduction", ("引言", "前言", "背景", "introduction", "background")),
    ("methods", ("材料与方法", "对象与方法", "资料与方法", "方法", "methods",
                 "materials and methods", "patients and methods",
                 "method", "methodology", "材料和方法")),
    ("results", ("结果", "results", "result")),
    ("title", ("题目", "标题", "title")),
]

# 章节归并：把 "材料与方法" 之类拆出的子标题统一到章
CHAPTER_ALIASES = {
    "关键词": "keywords", "数据可用性": "data_availability", "伦理": "ethics",
}

# 章节在文中的自然顺序（用于校验缺失/错序）
CHAPTER_ORDER = ["title", "abstract", "keywords", "introduction", "methods",
                 "results", "discussion", "conclusion", "ethics", "funding",
                 "coi", "acknowledgements", "data_availability", "references",
                 "supplementary", "other"]

# 判为标题的行内编号形式：1 / 1. / 1.2 / 一、 / （一） / 3 结果
NUM_RE = re.compile(r"^\s*(?:第?\s*[一二三四五六七八九十]+[、.．)）]|"
                    r"[（(]\s*[一二三四五六七八九十\d]+\s*[)）]|"
                    r"\d+(?:\.\d+)*[、.．)）]?)\s*")
HEADING_HINT_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*[、.．)）]?\s*)?"
    r"(?:材料与方法|对象与方法|资料与方法|材料和方法|方法|结果|讨论|结论|总结|"
    r"引言|前言|背景|摘要|关键词|参考文献|致谢|附录|补充材料|"
    r"abstract|summary|keywords?|introduction|background|methods?|methodology|"
    r"materials?\s+and\s+methods|patients?\s+and\s+methods|results?|discussion|"
    r"conclusions?|references?|acknowledge?ments?|appendix|supplementary|"
    r"data\s+availability|ethics|funding|conflicts?\s+of\s+interest|"
    r"competing\s+interests|title|题目|标题)\s*$",
    re.I)

# 摘要是最常见的第一处显式标题；它之前的短段落视为标题候选
_ABSTRACT_MARKERS = ("摘要", "abstract", "summary")


@dataclass
class Paragraph:
    idx: int                      # OfficeCLI /body/p[N] 的 N（1-based）
    text: str
    chapter: str = "other"
    style: str = ""
    para_id: str = ""             # w14:paraId（若存在，可作为更稳的锚点）
    is_heading: bool = False
    char_len: int = 0
    runs: int = 1

    @property
    def anchor(self) -> str:
        """回写地址：优先 paraId，其次序号。"""
        if self.para_id:
            return f"/body/p[@paraId={self.para_id}]"
        return f"/body/p[{self.idx}]"

    def to_dict(self) -> dict:
        return {"idx": self.idx, "text": self.text, "chapter": self.chapter,
                "style": self.style, "para_id": self.para_id,
                "is_heading": self.is_heading, "runs": self.runs,
                "char_len": len(self.text)}


@dataclass
class Manuscript:
    path: str = ""
    fmt: str = "docx"
    paragraphs: list[Paragraph] = field(default_factory=list)
    chapters: dict = field(default_factory=dict)   # chapter -> [idx, ...]
    title: str = ""
    word_count: int = 0
    warnings: list[str] = field(default_factory=list)
    sections_meta: list[dict] = field(default_factory=list)   # 表格等
    converted_from: str = ""      # PDF 转来的原始文件

    # -- 取用 ---------------------------------------------------------------
    def chapter_text(self, key: str, limit: int = 0) -> str:
        idxs = self.chapters.get(key) or []
        parts = [self.paragraphs[i - 1].text for i in idxs
                 if 1 <= i <= len(self.paragraphs)]
        s = "\n".join(p for p in parts if p.strip())
        return s[:limit] if limit else s

    def text(self) -> str:
        return "\n".join(p.text for p in self.paragraphs)

    def get(self, idx: int) -> Paragraph | None:
        if 1 <= idx <= len(self.paragraphs):
            return self.paragraphs[idx - 1]
        return None

    def find_paragraph(self, needle: str, chapter: str = "") -> Paragraph | None:
        """按文本片段定位段落（用于把缺陷挂到正确位置）。"""
        if not needle:
            return None
        n = _norm(needle)
        best, score = None, 0.0
        for p in self.paragraphs:
            if chapter and p.chapter != chapter:
                continue
            t = _norm(p.text)
            if not t:
                continue
            if n and n in t:
                s = len(n) / max(len(t), 1)
                if s > score:
                    best, score = p, s
        return best

    def available_chapters(self) -> list[str]:
        return [c for c in CHAPTER_ORDER if c in self.chapters and self.chapters[c]]

    def outline(self) -> list[dict]:
        """章节清单：key / 中文名 / 起始段 / 字数 —— 供界面与 MCP 展示。"""
        from manuscript_review.mr_review_layers import CHAPTER_TITLES
        out = []
        for key in self.available_chapters():
            idxs = self.chapters[key]
            chars = sum(len(self.paragraphs[i - 1].text) for i in idxs
                        if 1 <= i <= len(self.paragraphs))
            out.append({"key": key, "name": CHAPTER_TITLES.get(key, key),
                        "start": idxs[0], "paragraphs": len(idxs), "chars": chars})
        return out

    def to_dict(self, with_paragraphs: bool = True) -> dict:
        d = {"path": self.path, "fmt": self.fmt, "title": self.title,
             "word_count": self.word_count, "paragraphs": len(self.paragraphs),
             "converted_from": self.converted_from,
             "outline": self.outline(), "warnings": list(self.warnings)}
        if with_paragraphs:
            d["body"] = [p.to_dict() for p in self.paragraphs]
        return d


# --------------------------------------------------------------------------- 工具
def _norm(s: str) -> str:
    """归一化：去掉所有空白与全角空格，便于中文无空格文本的包含匹配。"""
    return re.sub(r"[\s\u3000]+", "", s or "").lower()


def _match_chapter(line: str) -> tuple[str, bool]:
    """判断一行是不是章节标题；返回 (chapter_key, is_heading)。"""
    s = (line or "").strip()
    if not s or len(s) > 60:
        return "", False
    # 整行完全等于某个章节词（可带编号）
    if HEADING_HINT_RE.match(s):
        bare = NUM_RE.sub("", s).strip()
        for key, words in CHAPTER_PATTERNS:
            for w in words:
                if bare.lower() == w.lower():
                    return key, True
    # 「1 材料与方法」这类：去掉编号后仍然以章节词开头且整行很短
    bare = NUM_RE.sub("", s).strip().rstrip("：:").strip()
    if bare and len(bare) <= 24:
        for key, words in CHAPTER_PATTERNS:
            for w in words:
                lw = w.lower()
                if bare.lower() == lw:
                    return key, True
                # 允许「材料与方法（一）」式后缀
                if bare.lower().startswith(lw) and len(bare) <= len(w) + 8:
                    return key, True
    return "", False


def _guess_title(paras: list[Paragraph]) -> str:
    """标题猜测：摘要之前最长的那个非空段落。"""
    cands = [p for p in paras
             if p.chapter in ("other",) and 4 <= len(p.text) <= 200
             and not p.is_heading]
    if not cands:
        return paras[0].text[:200] if paras else ""
    return max(cands, key=lambda p: len(p.text)).text[:200]


# --------------------------------------------------------------------------- 主入口
def load(path: str) -> Manuscript:
    """解析 .docx 手稿。PDF 请先经 mr_pdf.to_docx 转换。"""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        raise ValueError("这是 PDF，请先用 mr_pdf.to_docx() 转成 DOCX 再解析")
    if ext not in (".docx", ".doc"):
        raise ValueError(f"不支持的格式：{ext}（仅支持 .docx / .doc / .pdf）")

    ms = Manuscript(path=os.path.abspath(path))
    ms.paragraphs = _read_docx(ms)
    if not ms.paragraphs:
        ms.warnings.append("未解析到任何段落：文件可能是扫描件或空文档。")
        return ms

    _assign_chapters(ms)
    ms.title = _guess_title(ms.paragraphs)
    ms.word_count = sum(len(p.text) for p in ms.paragraphs)
    if not ms.chapters.get("abstract"):
        ms.warnings.append("未识别到「摘要」章节，请确认手稿是否标注了摘要标题。")
    if not ms.chapters.get("methods"):
        ms.warnings.append("未识别到「方法」章节，组学与统计层审阅效果会受影响。")
    return ms


def _read_docx(ms: Manuscript) -> list[Paragraph]:
    """读段落。用 python-docx（只读、稳定），并记录 w14:paraId 以便更稳的回写地址。"""
    try:
        import docx
    except ImportError as e:                                       # pragma: no cover
        raise RuntimeError("缺少 python-docx：pip install python-docx") from e

    from docx.oxml.ns import qn

    d = docx.Document(ms.path)
    out: list[Paragraph] = []
    n = 0
    for p in d.paragraphs:
        n += 1
        text = (p.text or "").strip()
        para_id = ""
        try:
            el = p._p
            pid = el.get(qn("w14:paraId"))
            if pid:
                para_id = str(pid)
        except Exception:                                          # noqa: BLE001
            para_id = ""
        style = ""
        try:
            style = p.style.name or ""
        except Exception:                                          # noqa: BLE001
            style = ""
        out.append(Paragraph(idx=n, text=text, para_id=para_id, style=style,
                             runs=len(p.runs), char_len=len(text)))
    # 表格内容也参与审阅（很多手稿把基线特征放进表格）
    for ti, tb in enumerate(d.tables, 1):
        rows = []
        for r in tb.rows[:6]:
            rows.append(" | ".join((c.text or "").strip() for c in r.cells))
        if rows:
            ms.sections_meta.append({"type": "table", "index": ti,
                                     "rows": len(tb.rows), "cols": len(tb.columns),
                                     "preview": rows})
    return out


def _assign_chapters(ms: Manuscript) -> None:
    """逐段判定章节归属：标题段开新章，其余继承当前章。"""
    paragraphs = ms.paragraphs
    cur = "other"
    seen_any_heading = False
    # 第一遍：显式标题
    for p in paragraphs:
        key, is_h = _match_chapter(p.text)
        if is_h:
            p.chapter = key
            p.is_heading = True
            cur = key
            seen_any_heading = True
        else:
            p.chapter = cur

    # 第一遍可能把「标题/作者/单位」也算进 other；摘要出现前的短段落回填为 title
    if not seen_any_heading:
        # 完全没有标题的手稿：退化为按位置粗略切分
        ms.warnings.append("手稿未使用可识别的章节标题，章节映射按位置粗略估计。")
        _assign_by_position(ms)
    else:
        first_body = None
        for p in paragraphs:
            if p.chapter in ("abstract", "introduction", "keywords", "methods"):
                first_body = p.idx
                break
        if first_body:
            for p in paragraphs:
                if p.idx >= first_body:
                    break
                if p.chapter == "other" and len(p.text) <= 300:
                    p.chapter = "title"
        # 关键词行：摘要之后、引言之前的短行，含「关键词 / Keywords」
        for p in paragraphs:
            low = p.text.lower()
            if low.startswith(("关键词", "关键字", "keywords", "key words")):
                p.chapter = "keywords"
                p.is_heading = False

    # 组装 chapters 索引
    ms.chapters = {}
    for p in paragraphs:
        ms.chapters.setdefault(p.chapter, []).append(p.idx)


def _assign_by_position(ms: Manuscript) -> None:
    """无标题退化：按「摘要在最前、参考文献在最后、中间按 1/3 切分」粗略估计。"""
    ps = ms.paragraphs
    total = len(ps)
    if total == 0:
        return
    for p in ps:
        p.chapter = "other"
    # 找摘要：最前面的、含"目的/方法/结果/结论"结构词的段落，或前 10% 的段落
    head = max(1, total // 10)
    for p in ps[:head]:
        if re.search(r"(目的|背景)[：:]", p.text) or re.search(
                r"(objectives?|aims?|background)[:：]", p.text, re.I):
            p.chapter = "abstract"
            for q in ps:
                if q.idx > p.idx:
                    q.chapter = "introduction"
            break
    else:
        for p in ps[:head]:
            p.chapter = "title"
        for p in ps[head:]:
            p.chapter = "introduction"
    # 尾部：参考文献
    for p in ps:
        if re.search(r"^(参考文献|references)\b", p.text, re.I):
            for q in ps:
                if q.idx >= p.idx:
                    q.chapter = "references"
    # 中部按关键词找方法/结果/讨论
    for p in ps:
        if p.chapter not in ("introduction",):
            continue
        t = p.text
        if re.match(r"^\s*(2|二)[\s、.．]", t) or "资料与方法" in t[:20] or \
                re.search(r"methods?", t[:20], re.I):
            for q in ps:
                if q.idx >= p.idx and q.chapter == "introduction":
                    q.chapter = "methods"
    for p in ps:
        if p.chapter != "methods":
            continue
        t = p.text
        if re.match(r"^\s*(3|三)[\s、.．]", t) or re.search(r"results?", t[:20], re.I):
            for q in ps:
                if q.idx >= p.idx and q.chapter == "methods":
                    q.chapter = "results"
    ms.chapters = {}
    for p in ms.paragraphs:
        ms.chapters.setdefault(p.chapter, []).append(p.idx)


# --------------------------------------------------------------------------- 全文摘要
def digest(ms: Manuscript, limit_per_chapter: int = 0) -> str:
    """把整份手稿整理成「段号 + 章节」标注的文本，喂给 LLM。

    段号必须带上：LLM 引用证据时要能指回具体段落，回写才能挂对位置。
    """
    from manuscript_review.mr_review_layers import CHAPTER_TITLES
    lines = []
    for p in ms.paragraphs:
        if not p.text:
            continue
        name = CHAPTER_TITLES.get(p.chapter, p.chapter)
        lines.append(f"[{p.idx}]（{name}）{p.text}")
    body = "\n".join(lines)
    if limit_per_chapter:
        body = body[:limit_per_chapter]
    return body


def chapter_digest(ms: Manuscript, keys: list[str], budget: int = 6000) -> str:
    """只取指定章节的段落（带段号），超出预算时保留首尾。"""
    from manuscript_review.mr_review_layers import CHAPTER_TITLES
    picked = []
    for key in keys:
        for idx in ms.chapters.get(key, []):
            p = ms.get(idx)
            if p is None or not p.text:
                continue
            picked.append(f"[{p.idx}]（{CHAPTER_TITLES.get(key, key)}）{p.text}")
    body = "\n".join(picked)
    if len(body) <= budget:
        return body
    half = budget // 2
    return body[:half] + "\n…（中间段落省略）…\n" + body[-half:]


if __name__ == "__main__":
    import sys
    m = load(sys.argv[1])
    print(f"段落 {len(m.paragraphs)} · 字数 {m.word_count} · 标题 {m.title[:40]}")
    for o in m.outline():
        print(f"  {o['name']:8s} 起于段 {o['start']:4d} · {o['paragraphs']:3d} 段 "
              f"· {o['chars']:5d} 字")
    for w in m.warnings:
        print("  ⚠", w)
