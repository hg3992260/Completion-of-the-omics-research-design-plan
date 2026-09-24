# -*- coding: utf-8 -*-
"""B 层：Glasman-Deal《Science Research Writing》(2nd ed.) 块级解析器（确定性，无 LLM）。

输出「SCI 章节 scope」子集：Title/Abstract/Introduction/Methods/Results/Discussion/
Conclusion 七章的 模型框 + 结构内容指导 + 语言指导 + 词块表；
排除练习(EXERCISE)、答案(KEY)、样例论文引文、索引、附录、前言。

判据（全部来自实测的字体/字号/矢量线特征，不依赖 LLM）：
  - 页眉/页码 : EurostileRegular 8pt      → 剥离，并提供书内页码
  - 标题       : MyriadPro-Black/Bold      → 20=单元 12=节 10.5=小节
  - 指导语     : Calibri / Calibri-Bold 10.5pt
  - 样例引文   : Calibri-Italic 主导（italic_ratio>=0.6）或 9.5pt 缩进块
  - 模型框     : 水平矢量线(height<3,width>100)划出的条带 + 条带内**大写率>0.6**
  - 词块表     : 同样在矢量线框内，但内容为**小写词条**（大写率低）→ 与模型组件区分
  - 表格       : page.find_tables()
  - 章节归属   : 取自 PDF 目录(get_toc)的 Unit 页码范围（比页眉可靠）

输出（docs/parse/）：blocks.jsonl / sci_scope_blocks.jsonl / outline.json / parse_report.txt
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE
DOCS = os.path.dirname(HERE)
SRC = os.path.join(
    DOCS,
    "Science Research Writing_ For Native And Non-native Speakers Of English, "
    "Second Edition - PDF Room.pdf")

PAGE_OFFSET = 29
BACKMATTER_PDF = 360

UNIT_TO_SECTION = {
    1: ("introduction", "引言"),
    2: ("methods", "方法"),
    3: ("results", "结果"),
    4: ("discussion", "讨论"),
    5: ("conclusion", "结论"),
    6: ("abstract", "摘要"),
    7: ("title", "标题"),
    8: ("checklist", "检查清单与技巧"),
}
SCI_SECTIONS = ("title", "abstract", "introduction", "methods", "results",
                "discussion", "conclusion")
SCOPE_KINDS = {"heading", "guidance", "model_box_title", "model_component",
               "word_list", "phrase_group", "phrase_table", "table", "list_item"}


def span_role(font: str) -> str:
    if font.startswith("Eurostile"):
        return "runhead"
    if font.startswith("MyriadPro"):
        return "heading"
    if font.startswith("Calibri"):
        return "italic" if "Italic" in font else "body"
    if font.startswith("Times"):
        return "serif"
    if font.startswith(("Wingdings", "Symbol")):
        return "symbol"
    return "other"


def is_bold(font: str, flags: int) -> bool:
    return ("Bold" in font) or bool(flags & 16)


def upper_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def build_section_ranges(doc):
    """从 PDF 目录取 Unit 起始页 → 页区间 → 章节。"""
    starts = {}
    for _lvl, title, page in doc.get_toc():
        m = re.match(r"^Unit\s+(\d+)\s*:", title.strip())
        if m:
            starts[int(m.group(1))] = page
    ranges = []
    units = sorted(starts)
    for i, u in enumerate(units):
        end = starts[units[i + 1]] - 1 if i + 1 < len(units) else BACKMATTER_PDF - 1
        ranges.append((starts[u], end, u))
    return ranges


def section_of(pdf_page, ranges):
    for a, b, u in ranges:
        if a <= pdf_page <= b:
            return UNIT_TO_SECTION[u][0], u
    return None, None


def header_info(page):
    """返回 (书内页码或 None, 是否罗马数字页)。"""
    folio, roman = None, False
    for blk in page.get_text("dict")["blocks"]:
        for line in blk.get("lines", []):
            for s in line["spans"]:
                if s["font"].startswith("Eurostile") and s["bbox"][1] < 75:
                    t = s["text"].strip()
                    if not t:
                        continue
                    m = re.search(r"\b(\d{1,3})\b", t)
                    if m:
                        folio = int(m.group(1))
                    elif re.search(r"\b[ivxlc]{2,}\b", t, re.I):
                        roman = True
    return folio, roman


def horizontal_rules(page):
    ys = []
    for dr in page.get_drawings():
        r = dr["rect"]
        if r.height < 3 and r.width > 100:
            ys.append(round(r.y0, 1))
    out = []
    for y in sorted(ys):
        if not out or abs(y - out[-1]) > 2:
            out.append(y)
    return out


def collect_lines(page):
    rows = []
    for blk in page.get_text("dict")["blocks"]:
        for line in blk.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = "".join(s["text"] for s in spans)
            role_c = Counter()
            for s in spans:
                role_c[span_role(s["font"])] += len(s["text"].strip())
            role = role_c.most_common(1)[0][0]
            ital = sum(len(s["text"]) for s in spans if "Italic" in s["font"])
            bold = " ".join(s["text"].strip() for s in spans
                            if is_bold(s["font"], s["flags"]) and s["text"].strip())
            rows.append({
                "text": text.strip(),
                "bold": re.sub(r"\s+", " ", bold).strip(),
                "italic_ratio": round(ital / max(1, len(text)), 2),
                "role": role,
                "size": round(max(s["size"] for s in spans), 1),
                "x0": round(min(s["bbox"][0] for s in spans), 1),
                "x1": round(max(s["bbox"][2] for s in spans), 1),
                "y0": round(min(s["bbox"][1] for s in spans), 1),
                "y1": round(max(s["bbox"][3] for s in spans), 1),
            })
    rows.sort(key=lambda r: (r["y0"], r["x0"]))
    return rows


def group_blocks(rows, rules, table_rects):
    blocks, cur, prev = [], None, None

    def band_of(y):
        for i in range(len(rules) - 1):
            if rules[i] <= y <= rules[i + 1]:
                return i
        return None

    for r in rows:
        b = band_of(r["y0"])
        new = (cur is None
               or r["role"] != cur["role"]
               or b != cur["rule_band"]
               or (prev is not None
                   and (r["y0"] - prev["y1"]) > max(4.0, 0.9 * (prev["y1"] - prev["y0"]))))
        if new:
            if cur:
                blocks.append(cur)
            cur = {"role": r["role"], "size": r["size"], "x0": r["x0"], "x1": r["x1"],
                   "y0": r["y0"], "y1": r["y1"], "lines": [], "bold": [],
                   "italic_ratio": r["italic_ratio"], "rule_band": b}
        cur["lines"].append(r["text"])
        cur["y1"] = max(cur["y1"], r["y1"])
        cur["x1"] = max(cur["x1"], r["x1"])
        cur["italic_ratio"] = max(cur["italic_ratio"], r["italic_ratio"])
        if r["bold"]:
            cur["bold"].append(r["bold"])
        prev = r
    if cur:
        blocks.append(cur)

    for blk in blocks:
        blk["text"] = re.sub(r"\s+", " ", " ".join(blk["lines"])).strip()
        blk["n_lines"] = len(blk["lines"])
        blk["in_table"] = any(fitz.Rect(t).intersects(
            fitz.Rect(blk["x0"], blk["y0"], blk["x1"], blk["y1"])) for t in table_rects)
        blk["upper"] = round(upper_ratio(blk["text"]), 2)
        del blk["lines"]
    return blocks


MODEL_TITLE = re.compile(r"(GENERIC|A|THE)\b[^.]{0,40}\b(MODEL|SECTION)\b", re.I)
BOX_TITLE_CAPS = re.compile(r"^[A-Z0-9][A-Z0-9 /,&()'\-]{8,}$")


def is_box_title(text: str, upper: float, n_lines: int) -> bool:
    """框标题：短、全大写为主、含 MODEL/SECTION。避免正文句子（如 'structural model'）误命中。"""
    return (len(text) <= 70 and n_lines <= 2 and upper >= 0.7
            and bool(MODEL_TITLE.search(text)))


def is_prose(text: str) -> bool:
    """句子式正文（正文段落常被折进模型框所在表格，需排除）：以句末标点结尾且词数>15。"""
    t = text.strip()
    return bool(re.search(r"[.?!]\s*$", t)) and len(t.split()) > 15


def classify(blk, section, subsection, pdf_page, page_has_model_box, box_bands):
    t = blk["text"]
    if blk["role"] == "heading":
        if re.search(r"\b(EXERCISE|EXERCISES|Key|Language task)\b", t, re.I):
            return "exercise_key"
        return "unit_heading" if blk["size"] >= 16 else "heading"
    if pdf_page >= BACKMATTER_PDF or section is None:
        return "backmatter" if pdf_page >= BACKMATTER_PDF else "frontmatter"
    # 样例论文材料一律位于 EXERCISE / Key / Demonstration 小节内 → 整段排除出 scope
    if subsection and re.search(r"\b(EXERCISE|EXERCISES|Key|TASK|demonstration)\b",
                                subsection, re.I):
        return "exercise_key"
    if re.match(r"^(EXERCISE|KEY|TASK|EXERCISES)\b", t, re.I):
        return "exercise_key"
    band = blk["rule_band"]
    # 矢量线框优先于 find_tables：模型框与词块表都在框内，靠"框归属 + 内容"区分
    if band is not None:
        if is_box_title(t, blk["upper"], blk["n_lines"]):
            return "model_box_title"
        if band in box_bands:
            return "model_component"
        if re.fullmatch(r"\d{1,2}", t):
            return "model_component"
        # 词块组标题（如 INVITATION TO VIEW RESULTS、MAP TO LITERATURE/KNOWLEDGE）
        if blk["upper"] >= 0.7 and len(t) <= 60 and blk["n_lines"] <= 2:
            return "phrase_group"
        # 框内但实为句子式正文（被框线括进来的指导语/图注）
        if is_prose(t):
            return "example" if blk["italic_ratio"] >= 0.6 else "guidance"
        return "word_list"
    if blk["in_table"]:
        return ("phrase_table"
                if subsection and re.search(r"useful words|language for|language$",
                                            subsection, re.I)
                else "table")
    if blk["italic_ratio"] >= 0.6:
        # 样例论文引文（小一号字）vs 原书自带斜体例句（正文字号）
        return "quote" if blk["size"] <= 9.6 else "example"
    if re.match(r"^(EXERCISE|KEY|TASK|EXERCISES)\b", t, re.I):
        return "exercise_key"
    if blk["size"] <= 9.6 and blk["x0"] > 60:
        return "quote"
    if re.match(r"^[·•\-\u2013]\s", t) or blk["x0"] > 80:
        return "list_item"
    return "guidance"


def main():
    if not os.path.exists(SRC):
        sys.exit(f"source pdf not found: {SRC}")
    doc = fitz.open(SRC)
    ranges = build_section_ranges(doc)
    all_blocks, outline = [], {}
    stats, per_section = Counter(), defaultdict(Counter)
    cur_subsection = None

    for i in range(doc.page_count):
        page = doc[i]
        pdf_page = i + 1
        section, unit = section_of(pdf_page, ranges)
        folio, roman = header_info(page)
        book_page = folio if folio else (pdf_page - PAGE_OFFSET if pdf_page > 29 else None)

        rules = horizontal_rules(page)
        try:
            tables = [t.bbox for t in page.find_tables().tables]
        except Exception:
            tables = []
        rows = [r for r in collect_lines(page) if r["role"] != "runhead"]
        blocks = group_blocks(rows, rules, tables)

        # 页面级：模型框归属（严格判据的标题横带 + 其上下连续有内容的横带）
        band_text, band_meta = defaultdict(str), {}
        for b in blocks:
            if b["rule_band"] is None:
                continue
            bi = b["rule_band"]
            band_text[bi] += " " + b["text"]
            m = band_meta.setdefault(bi, {"upper": b["upper"], "n_lines": 0})
            m["upper"] = max(m["upper"], b["upper"])
            m["n_lines"] += b["n_lines"]
        box_bands, title_bands = set(), []
        for bi, bt in sorted(band_text.items()):
            meta = band_meta[bi]
            if is_box_title(bt.strip(), meta["upper"], meta["n_lines"]):
                title_bands.append(bi)
        for tb in title_bands:
            box_bands.add(tb)
            i = tb + 1
            while band_text.get(i, "").strip() and not is_prose(band_text[i]):
                box_bands.add(i)
                i += 1
            i = tb - 1
            while band_text.get(i, "").strip() and not is_prose(band_text[i]):
                box_bands.add(i)
                i -= 1
        page_has_model_box = bool(title_bands)

        outline[str(pdf_page)] = {"book_page": book_page, "section": section,
                                  "unit": unit, "roman": roman,
                                  "subsection": cur_subsection}
        for bi, blk in enumerate(blocks):
            if blk["role"] == "heading":
                m = re.match(r"^([\d.]+)\s*(.*)", blk["text"])
                if m and len(m.group(1)) >= 3:
                    cur_subsection = f"{m.group(1)} {m.group(2)}".strip()
                    outline[str(pdf_page)]["subsection"] = cur_subsection
            kind = classify(blk, section, cur_subsection, pdf_page,
                            page_has_model_box, box_bands)
            if kind == "unit_heading":
                cur_subsection = None
            rec = {"id": f"p{pdf_page:03d}-b{bi:02d}", "pdf_page": pdf_page,
                   "book_page": book_page, "section": section, "unit": unit,
                   "subsection": cur_subsection, "kind": kind, "role": blk["role"],
                   "size": blk["size"], "x0": blk["x0"], "y0": blk["y0"],
                   "upper": blk["upper"],
                   "italic_ratio": blk["italic_ratio"], "n_lines": blk["n_lines"],
                   "in_table": blk["in_table"], "bold": blk["bold"], "text": blk["text"]}
            all_blocks.append(rec)
            stats[kind] += 1
            if section:
                per_section[section][kind] += 1

    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, "blocks.jsonl"), "w", encoding="utf-8") as f:
        for r in all_blocks:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    scope = [r for r in all_blocks
             if r["section"] in SCI_SECTIONS and r["kind"] in SCOPE_KINDS]
    with io.open(os.path.join(OUT, "sci_scope_blocks.jsonl"), "w", encoding="utf-8") as f:
        for r in scope:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with io.open(os.path.join(OUT, "outline.json"), "w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=1)

    rep = [f"pages: {doc.page_count}   blocks: {len(all_blocks)}   "
           f"sci_scope_blocks: {len(scope)}",
           f"section ranges (pdf): {ranges}", "", "== kind 分布 =="]
    for k, n in stats.most_common():
        rep.append(f"  {k:18s} {n}")
    rep.append("\n== 各 SCI 章节（scope 块数 / 全部块数）==")
    for s in SCI_SECTIONS:
        c = per_section[s]
        rep.append(f"  {s:14s} scope={sum(v for k, v in c.items() if k in SCOPE_KINDS):4d}"
                   f"   all={sum(c.values()):4d}   {dict(c)}")
    rep.append("\n== 抽样自检（应与人工判断一致）==")
    for pg in (46, 88, 117, 155, 184, 208, 257, 286, 304, 199, 107, 173):
        sel = [r for r in all_blocks if r["pdf_page"] == pg]
        kc = Counter(r["kind"] for r in sel)
        rep.append(f"  p{pg:3d} 书{str(sel[0]['book_page']) if sel else '-':>3s} "
                   f"section={str(sel[0]['section']) if sel else '-':12s} {dict(kc)}")
    rep.append("\n== 模型框（model_box_title / model_component）==")
    for r in scope:
        if r["kind"] in ("model_box_title", "model_component"):
            rep.append(f"  p{r['pdf_page']}/书{r['book_page']} {r['section']:12s} "
                       f"{r['kind']:16s} {r['text'][:78]}")
    txt = "\n".join(rep)
    with io.open(os.path.join(OUT, "parse_report.txt"), "w", encoding="utf-8") as f:
        f.write(txt)

    # 人类可读 scope 索引
    idx = ["# SCI 章节 Scope 索引（B 层块级解析产出）", "",
           "来源：Glasman-Deal, *Science Research Writing* (2nd ed.)，块级确定性解析。",
           "`书页 = PDF 页 − 29`。kind 含义：`model_box_title/model_component` 通用模型框；",
           "`guidance` 原书指导语；`example` 原书自带例句；`word_list/phrase_group/phrase_table` 词块库；",
           "`heading` 小节标题；`quote` 样例论文引文（多数已随 EXERCISE/Key 排除）；`exercise_key` 练习与答案（不在 scope）。", "",
           "## 已知精度与局限（B 层）", "",
           "- 7 个通用模型框（含 Discussion 单元复用的 Introduction 模型）**全部命中**，页码经人工核对（书 p17/88/155/192/208/257/286）。",
           "- `word_list` 中仍混有少量图注或样例标题（估计 <10%）：它们与词块表一样排在被框线包围的单元格里，字体特征无区别。",
           "- Unit 6 的 18 篇摘要范例位于 6.2（非 EXERCISE/Key 小节），仍留在 scope 内——它们是 Unit 6 scope 的语料组成，但**属他人论文，引用时须注明**。",
           "- 块按「矢量线横带 + 字体角色」切分，一个块可能含多个模型子项（如 Results 的 11 条落在 4 个横带内）。需要逐条拆分请在 C 层（句级）处理。",
           "- 页眉/页码已剥离；前言用罗马数字编页，不含在 scope 内。", ""]
    for s in SCI_SECTIONS:
        sel = [r for r in scope if r["section"] == s]
        c = Counter(r["kind"] for r in sel)
        pages = sorted({r["book_page"] for r in sel if r["book_page"]})
        idx.append(f"## {s}  （scope 块 {len(sel)}｜书页 {pages[0]}–{pages[-1]}）")
        idx.append("")
        idx.append("| kind | 数量 |")
        idx.append("|---|---|")
        for k, n in c.most_common():
            idx.append(f"| {k} | {n} |")
        boxes = [r for r in sel if r["kind"] == "model_box_title"]
        if boxes:
            idx.append("")
            idx.append("**模型框**：" + "；".join(
                f"书 p{r['book_page']}（PDF p{r['pdf_page']}）{r['text']}" for r in boxes))
        subs = Counter(r["subsection"] for r in sel if r["subsection"])
        if subs:
            idx.append("")
            idx.append("**覆盖小节（块数）**：" + "；".join(
                f"{k} ({v})" for k, v in subs.most_common()))
        idx.append("")
    with io.open(os.path.join(OUT, "sci_scope_index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx))
    print(txt)


if __name__ == "__main__":
    main()
