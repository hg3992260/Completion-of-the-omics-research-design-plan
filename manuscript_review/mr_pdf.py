# -*- coding: utf-8 -*-
"""PDF → DOCX 转换。

为什么需要它
-----------
审阅结果必须落回 Word（批注 + Track Changes），而期刊投稿稿大多是 PDF。
所以流程是：**PDF → DOCX → 审阅 → 带批注/修订的 DOCX**。

转换策略（按保真度取舍）
--------------------
1. 优先取 PDF 内嵌的**结构化文本**（PyMuPDF ``get_text("dict")``），
   按字号判断标题层级、按行间距判断段落边界；
2. 双栏排版按 x 坐标切列，避免左右栏文字交错；
3. 页眉页脚、页码、行号（投稿稿常见）自动剔除；
4. 由连字符断行的英文单词（``hyphen-\nation``）自动接回；
5. 扫描件（无文字层）明确报错，提示先做 OCR —— 不静默产出空文档。

转换必然有损（公式、复杂表格、图表位置），因此：
    · 转换结果会记录 warnings，界面与报告都会提示"请核对转换稿"；
    · 审阅锚点写在转换稿上，作者最终修订的是**转换稿**而非原 PDF，
      这是这套流程的固有限制，文档里必须写明。
"""

from __future__ import annotations

import os
import re
import statistics
from dataclasses import dataclass, field

# 行号 / 页码噪声
PAGE_NUM_RE = re.compile(r"^\s*(?:page\s*)?\d{1,4}\s*(?:/\s*\d{1,4})?\s*$", re.I)
LINE_NUM_RE = re.compile(r"^\s*\d{1,4}\s*$")
# 投稿稿常见的行号前缀：「12  This study ...」
LINENO_PREFIX_RE = re.compile(r"^\s*\d{1,4}\s{2,}(?=\S)")


@dataclass
class ConvertResult:
    ok: bool = False
    docx_path: str = ""
    pdf_path: str = ""
    pages: int = 0
    text_chars: int = 0
    headings: int = 0
    paragraphs: int = 0
    columns: int = 1
    warnings: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {"ok": self.ok, "docx_path": self.docx_path, "pdf_path": self.pdf_path,
                "pages": self.pages, "text_chars": self.text_chars,
                "headings": self.headings, "paragraphs": self.paragraphs,
                "columns": self.columns, "warnings": list(self.warnings),
                "error": self.error}


def available() -> dict:
    """返回 PDF 转换所需依赖的就绪情况。"""
    info = {"pymupdf": False, "version": "", "pdf2docx": False}
    try:
        import fitz
        info["pymupdf"] = True
        info["version"] = getattr(fitz, "__doc__", "") and \
            getattr(fitz, "VersionBind", "") or ""
    except Exception:                                              # noqa: BLE001
        pass
    try:
        import pdf2docx                                          # noqa: F401
        info["pdf2docx"] = True
    except Exception:                                              # noqa: BLE001
        pass
    return info


# --------------------------------------------------------------------------- 文本抽取
def _lines_from_page(page) -> list[dict]:
    """把一页拆成行，**直接采用 PyMuPDF 自带的行分组**。

    这里有一个踩过的坑：早先版本自己按 ``round(y0/3)`` 把 span 分桶再重排，
    结果同一视觉行里"加粗字"（y0 略高）与"常规字"被分到不同桶，
    按 x 排序后字符交错 —— 抽出来的标题会变成「强组细预测」这种乱码。
    PyMuPDF 的 blocks→lines 分组本来就是对的，不要重做。
    """
    out = []
    try:
        d = page.get_text("dict")
    except Exception:                                              # noqa: BLE001
        return out
    for block in d.get("blocks", []):
        if block.get("type") != 0:                                  # 0 = 文本块
            continue
        for line in block.get("lines", []):
            spans = [s for s in line.get("spans", []) if (s.get("text") or "").strip()]
            if not spans:
                continue
            spans.sort(key=lambda s: (s.get("bbox") or (0, 0, 0, 0))[0])
            text = "".join(s.get("text") or "" for s in spans)
            bb = line.get("bbox") or spans[0].get("bbox")
            if not bb:
                continue
            sizes = [float(s.get("size") or 0) for s in spans]
            fonts = [s.get("font") or "" for s in spans]
            out.append({
                "text": text,
                "bbox": (bb[0], bb[1], bb[2], bb[3]),
                "y0": bb[1], "y1": bb[3],
                "x0": bb[0], "x1": bb[2],
                "size": max(sizes) if sizes else 0.0,
                "bold": any(("bold" in f.lower()) or ("black" in f.lower())
                            for f in fonts),
            })
    return out


def _detect_columns(lines: list[dict], page_width: float) -> int:
    """判断是否真的是双栏排版。

    判定必须保守：把单栏稿误判成双栏会**打乱段落顺序**（按左栏全部、再右栏全部重排），
    代价远大于漏判双栏。所以这里同时要求三个条件：

      1. 左栏行数与右栏行数都占到 25% 以上（真的两栏都有大量文字）；
      2. 左栏起点（第 5 百分位 x0）靠近页左边距（< 页宽 28%）；
      3. 右栏起点显著右移（> 页宽 40%），即两栏的左边界是分离的。

    只要有一条不满足就返回 1（单栏），宁可漏判也不错排。
    """
    if page_width <= 0 or len(lines) < 16:
        return 1
    lefts = sorted(l["x0"] for l in lines if l.get("x0") is not None)
    if len(lefts) < 16:
        return 1
    mid = page_width / 2
    left = [x for x in lefts if x < mid]
    right = [x for x in lefts if x >= mid]
    if len(left) < len(lefts) * 0.25 or len(right) < len(lefts) * 0.25:
        return 1
    l_start = left[max(0, int(len(left) * 0.05))]
    r_start = right[max(0, int(len(right) * 0.05))]
    if l_start > page_width * 0.28:
        return 1
    if r_start < page_width * 0.40:
        return 1
    # 中缝确实空着：中缝 ±5% 页宽内几乎没有行起点
    band = page_width * 0.05
    if sum(1 for x in lefts if abs(x - mid) < band) > len(lefts) * 0.04:
        return 1
    return 2


def _order_lines(lines: list[dict], page_width: float, columns: int) -> list[dict]:
    """按栏 → 纵坐标排序，并给每行标上栏号。"""
    for ln in lines:
        ln["col"] = 0 if columns == 1 else (
            0 if (ln["x0"] + ln["x1"]) / 2 < page_width / 2 else 1)
    lines.sort(key=lambda l: (l["col"], round(l["y0"], 1), l["x0"]))
    return lines


def _clean_line(t: str) -> str:
    t = t.replace("\u00ad", "")                 # soft hyphen
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _is_noise(t: str, y: float, page_h: float) -> bool:
    """页眉页脚 / 页码 / 行号噪声。"""
    s = t.strip()
    if not s:
        return True
    if PAGE_NUM_RE.match(s) or LINE_NUM_RE.match(s):
        return True
    # 页眉页脚带：上下各 6%
    if page_h > 0 and (y < page_h * 0.06 or y > page_h * 0.94):
        if len(s) < 120 and not re.search(r"[。．.；;：:]$", s):
            # 只有很短且不含正文句读时才丢，避免误删正文首行
            if len(s) < 60:
                return True
    return False


def extract_lines(pdf_path: str, max_pages: int = 0) -> tuple[list[dict], int, list[str]]:
    """抽取全文行。返回 (lines, 页数, warnings)。"""
    warns: list[str] = []
    try:
        import fitz
    except ImportError as e:                                       # pragma: no cover
        raise RuntimeError("缺少 PyMuPDF：pip install pymupdf") from e

    doc = fitz.open(pdf_path)
    try:
        pages = doc.page_count
        if max_pages:
            pages = min(pages, max_pages)
        all_lines: list[dict] = []
        col_votes = []
        sizes: list[float] = []
        empty_pages = 0
        for pno in range(pages):
            page = doc.load_page(pno)
            rect = page.rect
            page_lines = _lines_from_page(page)
            if not page_lines:
                empty_pages += 1
                continue
            cols = _detect_columns(page_lines, rect.width)
            col_votes.append(cols)
            for ln in page_lines:
                sizes.append(ln["size"])
            for ln in _order_lines(page_lines, rect.width, cols):
                t = _clean_line(ln["text"])
                if _is_noise(t, ln["y0"], rect.height):
                    continue
                t = LINENO_PREFIX_RE.sub("", t)
                if not t.strip():
                    continue
                ln["text"] = t
                ln["page"] = pno + 1
                all_lines.append(ln)
        if empty_pages == pages:
            warns.append("PDF 无文字层（可能是扫描件）：请先做 OCR 再导入。")
        if col_votes:
            two = sum(1 for c in col_votes if c == 2)
            if two > len(col_votes) / 2:
                warns.append(f"检测到双栏排版（{two}/{len(col_votes)} 页），"
                             f"已按栏切分；请核对转换稿的段落顺序。")
        return all_lines, pages, warns
    finally:
        doc.close()


# --------------------------------------------------------------------------- 组装段落
def _build_paragraphs(lines: list[dict]) -> tuple[list[dict], list[str]]:
    """把行组装成段落：同段续行按「行宽接近、下一行非标题、无空行」判定。"""
    warns: list[str] = []
    if not lines:
        return [], ["未抽取到任何文本行。"]
    sizes = [l["size"] for l in lines if l["size"] > 0]
    body_size = statistics.median(sizes) if sizes else 10.0
    # 标题阈值：显著大于正文字号，或加粗且短
    head_size = body_size * 1.12

    paras: list[dict] = []
    cur: dict | None = None
    for i, ln in enumerate(lines):
        t = ln["text"]
        is_head = False
        if len(t) <= 60:
            if ln["size"] >= head_size and not re.search(r"[。．.；;，,]$", t):
                is_head = True
            if ln["bold"] and len(t) <= 40 and ln["size"] >= body_size * 0.98 \
                    and not re.search(r"[。．.；;]$", t):
                is_head = True
        prev = lines[i - 1] if i else None
        new_page = prev is not None and prev.get("page") != ln.get("page")
        # 上一段是标题 → 当前行必须另起一段，绝不能拼进标题里
        # （否则会出现「摘要肝细胞癌是全球常见的…」这种标题被吃掉的情况）
        prev_is_head = bool(cur and cur.get("heading"))
        if is_head or cur is None or prev_is_head:
            if cur:
                paras.append(cur)
            cur = {"text": t, "size": ln["size"], "heading": is_head,
                   "bold": ln["bold"], "page": ln["page"]}
            continue
        # 续行判定
        same_col = prev is None or prev.get("col") == ln.get("col")
        prev_ends = bool(re.search(r"[。．.！!？?；;：:]$", cur["text"].strip()))
        cur_short = len(cur["text"]) < 0.65 * _max_line_len(lines)
        if new_page or (prev_ends and not cur_short) or not same_col:
            paras.append(cur)
            cur = {"text": t, "size": ln["size"], "heading": False,
                   "bold": ln["bold"], "page": ln["page"]}
        else:
            cur["text"] = _join(cur["text"], t)
    if cur:
        paras.append(cur)

    # 清掉纯噪声段与过短碎片
    out = []
    for p in paras:
        t = _clean_line(p["text"])
        if not t:
            continue
        out.append({**p, "text": t})
    if not out:
        warns.append("段落组装后为空。")
    return out, warns


def _max_line_len(lines: list[dict]) -> int:
    return max((len(l["text"]) for l in lines), default=80) or 80


def _join(a: str, b: str) -> str:
    """接续两行：英文连字符断行接回，中文直接拼接。"""
    a = a.rstrip()
    b = b.lstrip()
    if re.search(r"[A-Za-z]-$", a) and re.match(r"^[a-z]", b):
        return a[:-1] + b
    if re.search(r"[\u4e00-\u9fff]$", a) and re.match(r"^[\u4e00-\u9fff]", b):
        return a + b
    if a.endswith("-"):
        return a[:-1] + b
    return a + " " + b


# --------------------------------------------------------------------------- 写 DOCX
def _write_docx(paras: list[dict], out_path: str, base_size: float,
                title: str = "") -> int:
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    d = docx.Document()
    # 中文字体：同时设置 ascii / eastAsia，否则中文会回退成默认字体
    try:
        from docx.oxml.ns import qn
        style = d.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(round(base_size, 1) if 6 <= base_size <= 20 else 10.5)
        style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    except Exception:                                              # noqa: BLE001
        pass

    n = 0
    for p in paras:
        para = d.add_paragraph()
        run = para.add_run(p["text"])
        if p.get("heading"):
            run.bold = True
            try:
                run.font.size = Pt(min(round(p.get("size") or base_size * 1.3, 1), 20))
            except Exception:                                      # noqa: BLE001
                pass
        if p.get("heading") and len(p["text"]) < 40:
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        n += 1
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    d.save(out_path)
    return n


# --------------------------------------------------------------------------- 主入口
def to_docx(pdf_path: str, out_path: str = "", max_pages: int = 0,
            title: str = "") -> ConvertResult:
    """PDF → DOCX。失败时 res.ok=False 且 res.error 说明原因（不抛异常）。"""
    res = ConvertResult(pdf_path=os.path.abspath(pdf_path))
    if not os.path.exists(pdf_path):
        res.error = f"文件不存在：{pdf_path}"
        return res
    if not out_path:
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        out_path = os.path.join(os.path.dirname(os.path.abspath(pdf_path)),
                                f"{base}_转换稿.docx")
    res.docx_path = os.path.abspath(out_path)
    try:
        lines, pages, warns = extract_lines(pdf_path, max_pages=max_pages)
        res.pages = pages
        res.warnings.extend(warns)
        if not lines:
            res.error = ("PDF 中没有可抽取的文字。"
                         "若是扫描件请先 OCR（例如用 deepseek-ocr 技能）后再导入。")
            return res
        res.text_chars = sum(len(l["text"]) for l in lines)
        paras, w2 = _build_paragraphs(lines)
        res.warnings.extend(w2)
        if not paras:
            res.error = "未能组装出段落，请检查 PDF 版面是否异常。"
            return res
        sizes = [l["size"] for l in lines if l["size"] > 0]
        base = statistics.median(sizes) if sizes else 10.5
        res.paragraphs = _write_docx(paras, res.docx_path, base, title=title)
        res.headings = sum(1 for p in paras if p.get("heading"))
        res.columns = 2 if any("双栏" in w for w in res.warnings) else 1
        res.ok = res.paragraphs > 0
        if not res.headings:
            res.warnings.append("未识别到明显标题层级，转换稿的章节映射可能依赖关键词匹配。")
        res.warnings.append("公式、复杂表格与图注在转换中可能失真，请在转换稿上核对后再修订。")
        return res
    except Exception as e:                                         # noqa: BLE001
        res.error = f"PDF 转换失败：{type(e).__name__}: {e}"
        return res


if __name__ == "__main__":
    import json
    import sys
    r = to_docx(sys.argv[1])
    print(json.dumps(r.to_dict(), ensure_ascii=False, indent=1))
