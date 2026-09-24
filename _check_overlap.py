# -*- coding: utf-8 -*-
"""遮挡检查器：在多个窗口尺寸下，对四个视图做几何判定（不靠肉眼看缩略图）。

检查三类问题：
  1) 兄弟控件矩形相交（真正的遮挡）；
  2) 子控件溢出父容器（会被父容器裁切）；
  3) 自动换行标签高度不足（文字被压/被截）。

滚动区域内部的"超出视口"是设计使然，会被跳过。
用法：  python _check_overlap.py            多尺寸 × 四视图
产出：  _overlap_report.txt（并打印摘要；有违规时退出码 1）
"""
import os
import sys

sys.argv = ["x", "--demo"]
from PySide6.QtWidgets import QApplication, QAbstractScrollArea
from PySide6 import QtCore, QtWidgets, QtGui

import design_studio as ds
from ui_kit import RefitLabel, text_height, UI_FONT

SIZES = [(1120, 700), (1280, 800), (1520, 960), (1920, 1080)]
VIEWS = [("工作台", "show_workspace"), ("Statistic", "show_stat"),
         ("SCI Shape", "show_sci_shape"), ("总览", "show_overview")]
MIN_AREA = 8.0          # 相交面积阈值（px²）

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=True)
win._no_flush = True
win.show()

report = []
violations = 0


def grect(w):
    tl = w.mapTo(win, QtCore.QPoint(0, 0))
    return QtCore.QRect(tl, w.size())


def in_scroll(w):
    p = w.parentWidget()
    while p is not None:
        if isinstance(p, QAbstractScrollArea):
            return True
        p = p.parentWidget()
    return False


def kids(w):
    return [c for c in w.children()
            if isinstance(c, QtWidgets.QWidget) and c.isVisible()
            and not isinstance(c, QAbstractScrollArea)]


def check_view(tag):
    global violations
    hits, overflow, clipped, narrow, near, n = [], [], [], [], [], 0
    stack = [win]
    while stack:
        parent = stack.pop()
        ch = kids(parent)
        n += len(ch)
        pr = grect(parent)
        # 1) 兄弟相交
        for i in range(len(ch)):
            for j in range(i + 1, len(ch)):
                a, b = grect(ch[i]), grect(ch[j])
                inter = a.intersected(b)
                if inter.isValid() and inter.width() * inter.height() > MIN_AREA:
                    hits.append((ch[i], ch[j], inter, pr))
        # 2) 溢出父容器（滚动区域内部除外）
        for c in ch:
            if in_scroll(c) or in_scroll(parent):
                continue
            cr = grect(c)
            over = QtCore.QRect(cr.x() - pr.x(), cr.y() - pr.y(), cr.width(), cr.height())
            if (over.left() < -2 or over.top() < -2 or over.right() > pr.width() + 2
                    or over.bottom() > pr.height() + 2):
                overflow.append((c, over, parent, pr))
        stack.extend(ch)
    # 3) 文字：换行标签查高度，不换行标签查横向是否放得下
    for lbl in win.findChildren(RefitLabel):
        if not lbl.isVisible():
            continue
        inner = lbl.label()
        text = (inner.text() or "").strip()
        if not text:
            continue
        if getattr(lbl, "_wrap_on", True):
            # 与应用 RefitLabel._refit 完全同一套估算规则（否则会误报临界换行）
            w = inner.width() if inner.width() > 40 else max(40, lbl.width() - 12)
            need = text_height(text, lbl._font_size, max(40, w - 4),
                               lbl._font_style == "bold")
            if need > inner.height() + 1:
                clipped.append((text[:44], inner.height(), need))
            elif need > inner.height() - 5:
                near.append((text[:44], inner.height(), need))
        else:
            f = QtGui.QFont(UI_FONT, lbl._font_size)
            f.setBold(lbl._font_style == "bold")
            adv = QtGui.QFontMetrics(f).horizontalAdvance(text)
            if adv > inner.width() + 1:
                narrow.append((text[:44], inner.width(), adv))
    # 报告
    if hits or overflow or clipped or narrow:
        violations += len(hits) + len(overflow) + len(clipped) + len(narrow)
        report.append(f"[{tag}] 控件 {n}｜相交 {len(hits)}｜溢出 {len(overflow)}｜"
                      f"换行截断 {len(clipped)}｜单行放不下 {len(narrow)}")
        for a, b, r, pr in hits[:10]:
            report.append(f"    相交: {type(a).__name__}<{txt(a)}> × {type(b).__name__}"
                          f"<{txt(b)}> 重叠{r.width()}×{r.height()} 于 {type(pr).__name__}"
                          f"{pr.width()}×{pr.height()}")
        for c, o, parent, pr in overflow[:10]:
            report.append(f"    溢出: {type(c).__name__}<{txt(c)}> rel={o.getRect()} "
                          f"父{type(parent).__name__}={pr.width()}×{pr.height()}")
        for t, got, need in clipped[:10]:
            report.append(f"    换行截断: 给定高={got} 需要高={need} | {t}")
        for t, got, need in narrow[:10]:
            report.append(f"    单行放不下: 宽={got} 需要={need} | {t}")
    else:
        report.append(f"[{tag}] 控件 {n}｜无相交、无溢出、无文字截断  ✓"
                      + (f"（临界换行 {len(near)} 处，已留余量）" if near else ""))
    return n


def txt(w):
    for getter in ("text", "toPlainText"):
        fn = getattr(w, getter, None)
        if callable(fn):
            try:
                s = str(fn()).replace("\n", " ")
                if s:
                    return s[:22]
            except Exception:                                   # noqa: BLE001
                pass
    lb = getattr(w, "label", None)
    if callable(lb):
        try:
            return lb().text()[:22]
        except Exception:                                       # noqa: BLE001
            pass
    return "-"


def run():
    global violations
    for (w, h) in SIZES:
        win.resize(w, h)
        for _ in range(3):
            win.layout().activate()
            QApplication.processEvents()
        for name, fn in VIEWS:
            getattr(win, fn)()
            for _ in range(3):
                win.layout().activate()
                QApplication.processEvents()
            check_view(f"{w}×{h} {name}")
        # 两个 scope 页的「引导完善」模式也要查（问题/回答框/定稿框/按钮都在这里）
        for name, page in (("Statistic", win.stat_page), ("SCI Shape", win.shape_page)):
            page.pick(1)
            page.set_mode("guide")
            for _ in range(3):
                win.layout().activate()
                QApplication.processEvents()
            check_view(f"{w}×{h} {name}·引导完善")
    out = "\n".join(report)
    open("_overlap_report.txt", "w", encoding="utf-8").write(out + "\n")
    print(out)
    print("\n违规总数:", violations)
    app.quit()
    sys.exit(1 if violations else 0)


QtCore.QTimer.singleShot(1200, run)
QtCore.QTimer.singleShot(60000, lambda: (print("看门狗超时", flush=True), app.quit()))
sys.exit(app.exec())
