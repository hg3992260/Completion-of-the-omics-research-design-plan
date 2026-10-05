# -*- coding: utf-8 -*-
"""审阅报告：把三层缺陷整理成可提交、可审计的文档。

产出三种形态（都在导出目录里）
--------------------------
    <手稿名>_审阅报告.md      主报告，Markdown，含三层分节与逐条缺陷
    <手稿名>_审阅报告.html    同内容 HTML（可直接浏览器打印成 PDF）
    <手稿名>_缺陷清单.csv     缺陷表，便于在 Excel 里排期与分派

报告结构刻意与 Word 批注一一对应：报告里第 N 条 = Word 里第 N 条批注，
两者用同一个 req_id 与段号，作者可以对着报告在 Word 里逐条核对。
"""

from __future__ import annotations

import csv
import html
import os
import time

from manuscript_review.mr_review_layers import (CHAPTER_TITLES, LAYERS, LAYER_ORDER,
                                                REQUIREMENTS, SEVERITY_RANK, stats)
from manuscript_review.mr_reviewer import sort_defects

SEV_MARK = {"关键": "■", "主要": "▲", "一般": "●"}


def _safe(name: str) -> str:
    import re
    s = re.sub(r'[\\/:*?"<>|\s]+', "_", (name or "").strip())
    return (s.strip("._") or "未命名手稿")[:80]


def _sev_sort(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda d: (SEVERITY_RANK.get(d.get("severity"), 9),
                                       d.get("para_idx") or 10 ** 6))


# --------------------------------------------------------------------------- Markdown
def build_markdown(project, manuscript=None) -> str:
    md = project.manuscript or {}
    outline = project.outline or []
    summ = project.summary or {}
    sig = project.signal_summary or {}
    layers = project.layers or list(LAYER_ORDER)
    defects = sort_defects(project.defects or [])
    L: list[str] = []

    L.append(f"# 手稿缺陷审阅报告 · {project.name}")
    L.append("")
    L.append(f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M')}")
    L.append(f"- 审阅对象：`{os.path.basename(project.source_path or '')}`")
    if project.converted:
        L.append(f"- 格式转换：PDF → DOCX（`{os.path.basename(project.docx_path or '')}`），"
                 f"**审阅与修订均作用于转换稿**")
    else:
        L.append(f"- 审阅正文：`{os.path.basename(project.docx_path or '')}`")
    L.append(f"- 手稿规模：{md.get('paragraphs', 0)} 段 · {md.get('word_count', 0)} 字")
    L.append(f"- 审阅层次：{'、'.join(LAYERS[k]['name'] for k in layers if k in LAYERS)}")
    L.append(f"- 缺陷合计：**{summ.get('total', len(defects))} 条**"
             f"（关键 {summ.get('关键', 0)} · 主要 {summ.get('主要', 0)}"
             f" · 一般 {summ.get('一般', 0)}）")
    out_docx = project.out_docx or (project.applied or {}).get("out_path") or ""
    if out_docx:
        L.append(f"- 修订稿：`{out_docx}`")
    if project.report_path:
        L.append(f"- 本报告：`{project.report_path}`")
    L.append("")

    # ---- 结论摘要
    L.append("## 一、审阅结论")
    L.append("")
    L.append(_verdict_paragraph(summ, sig, project))
    L.append("")

    # ---- 审阅口径
    L.append("## 二、三层审阅口径")
    L.append("")
    st = stats()
    L.append("| 层 | 规范依据 | 对照条目 | 关键 | 主要 | 一般 | 其中可确定性核验 |")
    L.append("|---|---|---|---|---|---|---|")
    for k in LAYER_ORDER:
        s = st[k]
        L.append(f"| {LAYERS[k]['name']} | {LAYERS[k]['sub']} | {s['total']} | "
                 f"{s['关键']} | {s['主要']} | {s['一般']} | {s['with_signal']} |")
    L.append(f"| **合计** | | **{st['total']}** | | | | |")
    L.append("")
    L.append("> 三层条目全部派生自工作台已有的权威数据（`stages_data` / `stat_data` / "
             "`shape_data`），与引导式组学、统计、撰写三套架构同源，不存在第二套标准。")
    L.append("")

    # ---- 确定性核验
    L.append("## 三、确定性核验（可证据化硬缺陷）")
    L.append("")
    L.append(f"共核验 {sig.get('total', 0)} 项：已报告 {sig.get('reported', 0)} · "
             f"信息不完整 {sig.get('weak', 0)} · 完全缺失 {sig.get('missing', 0)}。")
    L.append("")
    L.append("| 核验项 | 结论 | 命中证据 | 所在段 |")
    L.append("|---|---|---|---|")
    for h in sorted(project.signals or [],
                    key=lambda x: (0 if x.get("verdict") == "missing" else
                                   1 if x.get("verdict") == "weak" else 2,
                                   x.get("signal", ""))):
        from manuscript_review import mr_signals
        label = mr_signals.label_of(h.get("signal", ""))
        v = {"missing": "缺失", "weak": "不完整", "reported": "已报告"}.get(
            h.get("verdict"), h.get("verdict"))
        ev = (h.get("evidence") or "").replace("|", "\\|")[:60]
        L.append(f"| {label} | {v} | {ev} | {h.get('para_idx') or '-'} |")
    L.append("")

    # ---- 逐层缺陷
    L.append("## 四、缺陷逐条清单")
    L.append("")
    n = 0
    for k in [x for x in LAYER_ORDER if x in layers] + \
             [x for x in LAYERS if x not in layers]:
        rows = _sev_sort([d for d in defects if d.get("layer") == k])
        if not rows:
            continue
        L.append(f"### {LAYERS[k]['name']}层（{LAYERS[k]['sub']}）")
        L.append("")
        L.append(f"共 {len(rows)} 条缺陷。")
        L.append("")
        for d in rows:
            n += 1
            sev = d.get("severity") or "主要"
            mark = SEV_MARK.get(sev, "")
            ch = CHAPTER_TITLES.get(d.get("chapter") or "", d.get("chapter") or "")
            pos = f"第 {d.get('para_idx')} 段" + (f"（{ch}）" if ch else "")
            L.append(f"**{n}. {mark} {d.get('title', '')}**")
            L.append("")
            L.append(f"- 层次与规范：{d.get('ref', '')}"
                     + (f"｜{d.get('spec')}" if d.get("spec") else ""))
            L.append(f"- 严重度：{sev}")
            L.append(f"- 位置：{pos}")
            if d.get("why"):
                L.append(f"- 缺陷：{d['why']}")
            if d.get("evidence"):
                L.append(f"- 证据：{d['evidence']}")
            if d.get("suggestion"):
                L.append(f"- 建议：{d['suggestion']}")
            src = "确定性核验" if d.get("source") == "signal" else "语义审阅"
            L.append(f"- 来源：{src}｜条目 {d.get('req_id', '')}")
            L.append("")

    # ---- 已报告项（正向确认）
    reported = [h for h in (project.signals or []) if h.get("verdict") == "reported"]
    if reported:
        from manuscript_review import mr_signals
        L.append("## 五、已报告项（正向确认）")
        L.append("")
        L.append("以下条目在手稿中已找到明确表述，**不生成批注**，仅作确认与留痕：")
        L.append("")
        for h in reported:
            L.append(f"- {mr_signals.label_of(h.get('signal', ''))}"
                     f"（第 {h.get('para_idx') or '-'} 段）："
                     f"{(h.get('evidence') or '')[:80]}")
        L.append("")

    # ---- 落盘结果
    ap = project.applied or {}
    if ap:
        L.append("## 六、Word 落盘结果")
        L.append("")
        L.append(f"- 结果：{'成功' if ap.get('ok') else '失败'}")
        L.append(f"- 批注：{ap.get('comments_added', 0)} 条")
        L.append(f"- 正文修订：{ap.get('revisions_added', 0)} 处")
        if ap.get("error"):
            L.append(f"- 错误：{ap['error']}")
        sk = ap.get("skipped") or []
        if sk:
            L.append(f"- 仅出批注、未动正文：{len(sk)} 条（需作者重算或补充数据后定稿）")
        v = ap.get("verify") or {}
        if v:
            L.append(f"- 校验：{'通过' if v.get('ok') else '未通过'}"
                     f"（批注标记 {v.get('markers', {})}）")
            for pr in v.get("problems") or []:
                L.append(f"  - ⚠ {pr}")
        L.append("")
        L.append("**修订颜色规范**：绿色 `00B050` 下划线 = 新增 · "
                 "红色 `FF0000` 删除线 = 删除 · 蓝色 `0070C0` 下划线 = 修改 · "
                 "橙色 `ED7D31` = 移动/格式变更。")
        L.append("")

    # ---- 使用说明与限制
    L.append("## 七、使用说明与已知限制")
    L.append("")
    L.append("1. 打开修订稿后，在 Word「审阅」窗格逐条处理批注；"
             "若要全盘接受/拒绝修订，用「审阅 → 接受/拒绝」。")
    L.append("2. **批注只指出问题，最终取舍由作者负责** —— "
             "尤其是需要重算统计量、补做一致性分析的条目，程序不会替作者造数据。")
    L.append("3. 标为「缺失」的补正段落是**占位待补**文字（形如"
             "「请补充具体数值/来源后删除本标注」），不是可直接投稿的内容。")
    if project.converted:
        L.append("4. 本稿由 PDF 转换而来：公式、复杂表格、图注可能失真；"
                 "**修订落在转换稿上**，最终定稿请把修订内容合并回原始排版稿。")
    warns = list(project.warnings or [])
    if warns:
        L.append("")
        L.append("转换与解析过程中的提示：")
        L.append("")
        for w in warns:
            L.append(f"- {w}")
    L.append("")
    L.append("---")
    L.append("")
    L.append("_本报告由「手稿缺陷审阅工作台」自动生成；"
             "审阅条目与工作台的引导式组学/统计/撰写架构同源。_")
    return "\n".join(L)


def _verdict_paragraph(summ: dict, sig: dict, project) -> str:
    total = summ.get("total", 0)
    key = summ.get("关键", 0)
    main = summ.get("主要", 0)
    minor = summ.get("一般", 0)
    missing = sig.get("missing", 0)
    if total == 0:
        return "本次审阅未发现缺陷。请确认审阅层次与手稿章节是否匹配后再下结论。"
    parts = []
    if key:
        parts.append(f"{key} 条属**关键**缺陷（规范强制项，缺失即影响可复现性，"
                     f"建议投稿前必须处理）")
    if main:
        parts.append(f"{main} 条属**主要**缺陷（规范推荐项，会被审稿人质疑）")
    if minor:
        parts.append(f"{minor} 条属**一般**缺陷（写作语体与内容边界）")
    head = "；".join(parts) + "。"
    extra = ""
    if missing:
        extra = (f"其中 {missing} 项在确定性核验中判定为**完全缺失**，"
                 f"已在修订稿中以绿色插入段标出报告位点。")
    return head + extra


# --------------------------------------------------------------------------- 导出
def write_markdown(project, manuscript=None, out_dir: str = "") -> str:
    from manuscript_review.mr_engine import exports_root
    d = out_dir or exports_root()
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{_safe(project.name)}_审阅报告.md")
    text = build_markdown(project, manuscript)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    # 顺带产出 HTML 与 CSV
    try:
        _write_html(project, text, os.path.join(d, f"{_safe(project.name)}_审阅报告.html"))
    except Exception:                                              # noqa: BLE001
        pass
    try:
        write_csv(project, os.path.join(d, f"{_safe(project.name)}_缺陷清单.csv"))
    except Exception:                                              # noqa: BLE001
        pass
    return path


def write_csv(project, path: str) -> str:
    defects = sort_defects(project.defects or [])
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["序号", "严重度", "层次", "规范出处", "章节", "段号",
                    "缺陷", "为什么是缺陷", "证据", "建议修改",
                    "来源", "条目ID"])
        for i, d in enumerate(defects, 1):
            w.writerow([
                i, d.get("severity", ""),
                LAYERS.get(d.get("layer") or "", {}).get("name", d.get("layer", "")),
                f"{d.get('ref', '')} {d.get('spec', '')}".strip(),
                CHAPTER_TITLES.get(d.get("chapter") or "", d.get("chapter") or ""),
                d.get("para_idx") or "",
                d.get("title", ""), d.get("why", ""),
                (d.get("evidence") or "")[:300], d.get("suggestion", ""),
                "确定性核验" if d.get("source") == "signal" else "语义审阅",
                d.get("req_id", ""),
            ])
    return path


_HTML_CSS = """
:root{--bg:#0d1117;--fg:#c9d1d9;--mut:#8b949e;--key:#f85149;--main:#d29922;
--minor:#8b949e;--line:#30363d;--card:#161b22;--acc:#58a6ff}
*{box-sizing:border-box}
body{margin:0;padding:32px 40px;background:var(--bg);color:var(--fg);
font:15px/1.75 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;max-width:1100px}
h1{font-size:26px;border-bottom:2px solid var(--acc);padding-bottom:12px}
h2{font-size:20px;margin-top:38px;color:var(--acc);border-left:4px solid var(--acc);
padding-left:10px}
h3{font-size:17px;margin-top:26px;color:#e6edf3}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13.5px}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:#1f2428;font-weight:600}
tr:nth-child(even) td{background:#12161b}
code,pre{background:#1f2428;border-radius:4px;padding:2px 6px;font-size:13px}
pre{padding:12px;overflow:auto}
blockquote{border-left:4px solid var(--line);margin:14px 0;padding:6px 14px;color:var(--mut)}
ul{padding-left:22px}
hr{border:none;border-top:1px solid var(--line);margin:30px 0}
em{color:var(--mut)}
"""


def _md_to_html(md: str) -> str:
    """极简 Markdown → HTML（只支持报告用到的语法，避免引入依赖）。"""
    out: list[str] = []
    in_ul = in_table = False

    def close():
        nonlocal in_ul, in_table
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_table:
            out.append("</tbody></table>")
            in_table = False

    def inline(s: str) -> str:
        import re as _re
        s = html.escape(s)
        # 表格里的 \| 是转义竖线，还原成普通竖线
        s = s.replace("\\|", "|")
        s = _re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = _re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = _re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        s = _re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        return s

    for raw in md.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            close()
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(set(c) <= set("-: ") and c for c in cells):
                continue
            if not in_table:
                close()
                out.append("<table><thead><tr>" +
                           "".join(f"<th>{inline(c)}</th>" for c in cells) +
                           "</tr></thead><tbody>")
                in_table = True
            else:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            close()
        if s.startswith("#"):
            lvl = len(s) - len(s.lstrip("#"))
            close()
            out.append(f"<h{min(lvl, 6)}>{inline(s.lstrip('# ').strip())}</h{min(lvl, 6)}>")
            continue
        if s.startswith(("- ", "* ")):
            if not in_ul:
                close()
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(s[2:])}</li>")
            continue
        if s in ("---", "***"):
            close()
            out.append("<hr>")
            continue
        if s.startswith(">"):
            close()
            out.append(f"<blockquote>{inline(s.lstrip('> '))}</blockquote>")
            continue
        close()
        out.append(f"<p>{inline(s)}</p>")
    close()
    return "\n".join(out)


def _write_html(project, md: str, path: str) -> str:
    body = _md_to_html(md)
    doc = (f"<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
           f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
           f"<title>手稿缺陷审阅报告 · {html.escape(project.name)}</title>"
           f"<style>{_HTML_CSS}</style></head><body>{body}</body></html>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return path


def requirement_coverage(defects: list[dict]) -> dict:
    """按层统计：规范条目总数 / 报出缺陷数 / 通过数。"""
    out = {}
    for k in LAYER_ORDER:
        total = len([r for r in REQUIREMENTS if r["layer"] == k])
        bad = {d.get("req_id") for d in defects if d.get("layer") == k}
        out[k] = {"name": LAYERS[k]["name"], "total": total,
                  "defects": len(bad), "passed": max(0, total - len(bad))}
    return out
