# -*- coding: utf-8 -*-
"""皮肤试样台：离屏渲染一张"控件样本表"，用来肉眼校对高对比拟物三维的效果。

    D:\\python\\envs\\mar\\python.exe _skeuo_lab.py            # 深浅各出一张
    D:\\python\\envs\\mar\\python.exe _skeuo_lab.py --mode dark

产物：_shots/skeuo_lab_dark.png / _shots/skeuo_lab_light.png
"""

from __future__ import annotations

import os
import sys

# 注意：不能用 QT_QPA_PLATFORM=offscreen —— 本机 PySide6 没有 lib/fonts，
# 离屏渲染拿不到系统字体，文字会缺失或错位，判断不了对比度。用真实平台。
from PySide6 import QtCore, QtGui, QtWidgets                        # noqa: E402
from PySide6.QtCore import QRectF, Qt                               # noqa: E402
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout  # noqa: E402

from PyCt6 import (CButton, CComboBox, CFrame, CLabel, CLineEdit,  # noqa: E402
                   CSlider, CTextEdit, set_appearance_mode, set_color_theme)

import ui_kit                                                       # noqa: E402
import skeuo_kit                                                    # noqa: E402
from ui_kit import (C, PAL, UI_FONT, Card, CheckBox3D, ProgressBar,  # noqa: E402
                    draw_backdrop, mk_label)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_shots")

#: 需要"像素级体检"的样本：(name, widget, kind)；kind=text 测对比度，surface 测立体深度
PROBES: list[tuple[str, QtWidgets.QWidget, str]] = []


def probe_inset(name: str) -> int:
    """自绘块内部还留了投影/边距，采样必须避开它们，否则量到的是页面底衬。"""
    if name == "card":
        return 14
    if name.startswith("block_"):
        return 9
    if name.startswith(("bubble_", "tool_")):
        return 6
    if name == "slider":
        return 4
    return 3


def intended_text(w: QtWidgets.QWidget) -> QtGui.QColor | None:
    """取"皮肤实际下发的字色"——对比度必须拿它算，而不是拿区里最亮的像素算。"""
    fn = getattr(w, "probe_text", None)
    if callable(fn):
        return fn()
    try:
        return skeuo_kit._widget_text(w)                              # noqa: SLF001
    except Exception:                                                 # noqa: BLE001
        return None


def rel_lum(c: QtGui.QColor) -> float:
    def ch(v: float) -> float:
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())


def contrast(a: QtGui.QColor, b: QtGui.QColor) -> float:
    hi, lo = sorted((rel_lum(a), rel_lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def region_colors(img: QtGui.QImage, rect: QtCore.QRect, inset: int = 3
                  ) -> tuple[QtGui.QColor, int, list[QtGui.QColor]]:
    """区内像素 → (中位亮度对应的真实颜色, 总像素, 全部颜色)。

    为什么不用"出现最多的颜色"：拟物化的面是**竖向渐变**，每一行的颜色都不同，
    众数色只会落在横向重复的描边行上（实测把 #454d59 的边框当成了底色）。
    中位亮度对渐变稳健，取与之最接近的真实像素色，得到的就是"这块面大体是什么颜色"。
    """
    xs = range(max(rect.left() + inset, 0), max(rect.left() + inset + 1, rect.right() - inset))
    ys = range(max(rect.top() + inset, 0), max(rect.top() + inset + 1, rect.bottom() - inset))
    lums: list[float] = []
    cols: list[QtGui.QColor] = []
    for y in ys:
        for x in xs:
            if 0 <= x < img.width() and 0 <= y < img.height():
                c = QtGui.QColor(img.pixel(x, y))
                cols.append(c)
                lums.append(rel_lum(c))
    if not lums:
        return QtGui.QColor("#000000"), 0, []
    lums_sorted = sorted(lums)
    med = lums_sorted[len(lums_sorted) // 2]
    idx = min(range(len(lums)), key=lambda i: abs(lums[i] - med))
    return cols[idx], len(cols), cols


def text_audit(img: QtGui.QImage, rect: QtCore.QRect, want: QtGui.QColor | None,
               ) -> tuple[str, str, float, float]:
    """文字体检 → (底色, 前景色, 对比度, 前景色像素占比)。

    前景优先用**皮肤实际下发的那支字色**（对比度才有意义）；同时统计该色在区内的占比，
    占比≈0 说明字根本没按预期画出来（占位符就是被这个抓出来的）。
    """
    bg, _, cols = region_colors(img, rect)
    if want is None:
        want = bg
    hit = 0
    for c in cols:
        if max(abs(c.red() - want.red()), abs(c.green() - want.green()),
               abs(c.blue() - want.blue())) <= 26:
            hit += 1
    share = hit / max(1, len(cols))
    return bg.name(), want.name(), contrast(want, bg), share


def bevel_depth(img: QtGui.QImage, rect: QtCore.QRect, inset: int = 8
                ) -> tuple[float, str, str]:
    """立体深度：上下各 20% 高度带的**中位亮度**之差（对渐变稳健）。

    深色主题里大面积的亮度差天然被压缩，所以这里量的是"面本身"的明暗跨度，
    边缘那条 1px 高光另有渲染稿目视确认。
    """
    def band(y_from: int, y_to: int) -> QtGui.QColor:
        xs = range(max(rect.left() + inset, 0), max(rect.left() + inset + 1, rect.right() - inset))
        lums: list[float] = []
        cols: list[QtGui.QColor] = []
        for y in range(y_from, y_to):
            for x in xs:
                if 0 <= x < img.width() and 0 <= y < img.height():
                    c = QtGui.QColor(img.pixel(x, y))
                    cols.append(c)
                    lums.append(rel_lum(c))
        if not lums:
            return QtGui.QColor("#000000")
        s = sorted(lums)
        med = s[len(s) // 2]
        return cols[min(range(len(lums)), key=lambda i: abs(lums[i] - med))]

    y0 = rect.top() + inset
    y1 = max(y0 + 1, rect.bottom() - inset)
    h = y1 - y0
    top = band(y0, y0 + max(1, int(h * 0.2)))
    bot = band(y1 - max(1, int(h * 0.2)), y1)
    return abs(rel_lum(top) - rel_lum(bot)), bot.name(), top.name()


# --------------------------------------------------------------------------- 自绘试样
class RaisedBlock(QtWidgets.QWidget):
    def __init__(self, master, kind: str = "raised"):
        super().__init__(master)
        self.kind = kind
        self.setMinimumSize(120, 44)

    def _change_theme(self):
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        if self.kind == "raised":
            base = skeuo_kit.resolve(PAL["btn"])
            skeuo_kit.draw_contact_shadow(p, r, 10, depth=0.9)
            skeuo_kit.draw_raised(p, r, base, 10)
        elif self.kind == "glass":
            base = skeuo_kit.resolve(PAL["accent"])
            skeuo_kit.draw_contact_shadow(p, r, 10, depth=1.1)
            skeuo_kit.draw_raised(p, r, base, 10, gloss=True, gloss_alpha=72)
        else:
            base = skeuo_kit.resolve(PAL["surface2"])
            skeuo_kit.draw_inset(p, r, base, 10)


class Bubble(QtWidgets.QWidget):
    """会话气泡试样（新会话窗口的核心构件）。"""

    def __init__(self, master, who: str, text: str):
        super().__init__(master)
        self.who, self.text = who, text
        self.setMinimumHeight(58)

    def _change_theme(self):
        self.update()

    def probe_text(self) -> QtGui.QColor:
        return skeuo_kit.resolve(PAL["title_text" if self.who == "user" else "text"])

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(6, 5, -6, -7)
        user = self.who == "user"
        hi = skeuo_kit.resolve(PAL["bubble_user_hi" if user else "bubble_ai_hi"])
        lo = skeuo_kit.resolve(PAL["bubble_user_lo" if user else "bubble_ai_lo"])
        edge = skeuo_kit.resolve(PAL["bubble_user_edge" if user else "bubble_ai_edge"])
        skeuo_kit.draw_contact_shadow(p, r, 12, depth=0.8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(skeuo_kit.vgrad(r, hi, lo))
        p.drawRoundedRect(r, 12, 12)
        p.setPen(QtGui.QPen(skeuo_kit.alpha(hi, 150), 1.2))
        p.drawLine(QtCore.QPointF(r.left() + 10, r.top() + 0.8),
                   QtCore.QPointF(r.right() - 10, r.top() + 0.8))
        p.setPen(QtGui.QPen(edge, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        f = QtGui.QFont(UI_FONT, 10)
        p.setFont(f)
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["title_text" if user else "text"])))
        p.drawText(r.adjusted(12, 8, -12, -8), Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
                   self.text)


class ToolCard(QtWidgets.QWidget):
    """工具调用卡片试样（左侧色条 = 状态）。"""

    def __init__(self, master, name: str, detail: str, tone: str = "ok"):
        super().__init__(master)
        self.name, self.detail, self.tone = name, detail, tone
        self.setMinimumHeight(46)

    def _change_theme(self):
        self.update()

    def probe_text(self) -> QtGui.QColor:
        return skeuo_kit.resolve(PAL["text"])

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(6, 5, -6, -7)
        hi = skeuo_kit.resolve(PAL["tool_hi"])
        lo = skeuo_kit.resolve(PAL["tool_lo"])
        edge = skeuo_kit.resolve(PAL["tool_edge"])
        skeuo_kit.draw_contact_shadow(p, r, 10, depth=0.7)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(skeuo_kit.vgrad(r, hi, lo))
        p.drawRoundedRect(r, 10, 10)
        bar = QtGui.QColor(C(self.tone))
        p.setBrush(skeuo_kit.vgrad(r, skeuo_kit.lighten(bar, 0.25), skeuo_kit.darken(bar, 0.3)))
        p.drawRoundedRect(QRectF(r.left() + 1, r.top() + 1, 4.5, r.height() - 2), 2.2, 2.2)
        p.setPen(QtGui.QPen(skeuo_kit.alpha(hi, 170), 1.1))
        p.drawLine(QtCore.QPointF(r.left() + 9, r.top() + 0.8),
                   QtCore.QPointF(r.right() - 9, r.top() + 0.8))
        p.setPen(QtGui.QPen(edge, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)
        p.setFont(QtGui.QFont(UI_FONT, 9, QtGui.QFont.Weight.DemiBold))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["text"])))
        p.drawText(QRectF(r.left() + 14, r.top() + 6, r.width() - 22, 18),
                   Qt.AlignLeft | Qt.AlignVCenter, self.name)
        p.setFont(QtGui.QFont(ui_kit.MONO_FONT, 8))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["muted"])))
        p.drawText(QRectF(r.left() + 14, r.top() + 23, r.width() - 22, 16),
                   Qt.AlignLeft | Qt.AlignVCenter, self.detail)


class Section(QtWidgets.QWidget):
    """带标题的分区（同时充当页面底衬的可见证据）。"""

    def __init__(self, master, title: str):
        super().__init__(master)
        self.title = title
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 34, 16, 16)
        self.body.setSpacing(10)
        self.setMinimumHeight(90)

    def add(self, w):
        self.body.addWidget(w)
        return w

    def add_row(self, *widgets):
        host = QtWidgets.QWidget(self)
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        for w in widgets:
            row.addWidget(w)
        row.addStretch(1)
        self.body.addWidget(host)
        return host

    def _change_theme(self):
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        draw_backdrop(p, r)                                   # 页面底衬（径向渐变）
        p.setFont(QtGui.QFont(UI_FONT, 11, QtGui.QFont.Weight.Bold))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["title_text"])))
        p.drawText(QRectF(18, 10, r.width() - 36, 20), Qt.AlignLeft | Qt.AlignVCenter, self.title)


def build() -> QtWidgets.QWidget:
    PROBES.clear()
    root = QtWidgets.QWidget()
    root.setWindowTitle("skeuo lab")
    root.resize(940, 1120)
    col = QVBoxLayout(root)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(0)

    # 1) 按钮：主色 / 中性 / 危险 / 禁用
    s1 = Section(root, "① 按钮 — 玻璃帽 + 上亮下暗倒角；按下时上下边对调（真凹进去）")
    b_primary = CButton(master=s1, text="采纳并收录", width=132, height=34, font_family=UI_FONT,
                        font_size=10, background_color=PAL["accent"], text_color=PAL["on_accent"])
    b_neutral = CButton(master=s1, text="重新生成", width=112, height=34, font_family=UI_FONT,
                        font_size=10, background_color=PAL["btn"], text_color=PAL["text"])
    b_danger = CButton(master=s1, text="删除", width=88, height=34, font_family=UI_FONT,
                       font_size=10, background_color=PAL["danger"], text_color=PAL["on_accent"])
    b_dis = CButton(master=s1, text="已禁用", width=96, height=34, font_family=UI_FONT,
                    font_size=10, background_color=PAL["btn"], text_color=PAL["text"])
    b_dis.button().setEnabled(False)
    s1.add_row(b_primary, b_neutral, b_danger, b_dis)
    PROBES.extend([("btn_primary", b_primary, "text"), ("btn_neutral", b_neutral, "text"),
                   ("btn_danger", b_danger, "text"), ("btn_disabled", b_dis, "text")])
    col.addWidget(s1)

    # 2) 输入件：输入井 / 下拉 / 滑条
    s2 = Section(root, "② 输入件 — 内嵌井（上暗下亮）+ 上缘内阴影；聚焦换 2px 焦点环")
    e1 = CLineEdit(master=s2, width=250, height=32, font_family=UI_FONT, font_size=10,
                   placeholder_text="课题名称 / 搜索…")
    cb = CComboBox(master=s2, width=170, height=32, font_family=UI_FONT, font_size=10,
                   values=["deepseek-flash", "deepseek-reasoner", "gpt-5"], current_value="deepseek-flash")
    sl = CSlider(master=s2, width=220, value=62)
    s2.add_row(e1, cb, sl)
    PROBES.extend([("input_line", e1, "text"), ("combo", cb, "text"), ("slider", sl, "surface")])
    col.addWidget(s2)

    # 3) 文本域 + 滚动条
    s3 = Section(root, "③ 文本域 — 凹槽 + 凸起滑块滚动条")
    te = CTextEdit(master=s3, width=880, height=96, font_family=UI_FONT, font_size=10)
    te.text_edit().setPlainText("复核 2015-01 至 2023-06 本院病理证实 PCL 患者…\n"
                                "① 采集与重建参数未说明  ② 外部验证例数与事件数  ③ 组学分组是否独立于模型输出")
    s3.add(te)
    PROBES.append(("text_edit", te, "text"))
    col.addWidget(s3)

    # 4) 既有自绘构件（只换调色板就该整体变立体）
    s4 = Section(root, "④ 既有自绘构件 — Card / CheckBox3D / ProgressBar（换调色板即生效）")
    card = Card(s4, radius=14, horizontal=True)
    # 注意：ui_kit.Card 只暴露 layout()（PyCt6 的 CFrame 才有 addWidget）
    card.layout().addWidget(mk_label(card, "十阶段流程", size=11, bold=True, color="title_text"))
    card.layout().addWidget(CheckBox3D(card, checked=True))
    card.layout().addWidget(CheckBox3D(card, checked=False))
    pb = ProgressBar(card, width=170, height=10)
    pb.set_value(0.62)
    card.layout().addWidget(pb)
    s4.add(card)
    PROBES.append(("card", card, "surface"))
    col.addWidget(s4)

    # 5) 新界面构件试样：凸起/玻璃/内嵌 + 气泡 + 工具卡
    s5 = Section(root, "⑤ 新会话窗口构件 — 凸起块 / 玻璃块 / 内嵌井 / 气泡 / 工具卡")
    r_raised, r_glass, r_inset = (RaisedBlock(s5, "raised"), RaisedBlock(s5, "glass"),
                                  RaisedBlock(s5, "inset"))
    s5.add_row(r_raised, r_glass, r_inset)
    b_user = Bubble(s5, "user", "把回顾性队列的外部验证例数补到 ≥ 100 例，并把事件数单列。")
    b_ai = Bubble(s5, "ai", "已按 CLEAR 14 补写：外部验证 ≥ 100 例、事件 ≥ 40 例，"
                            "并注明组学分组独立于模型输出。")
    s5.add(b_user)
    s5.add(b_ai)
    t_ok = ToolCard(s5, "read  研究设计文档.md", "1.2 KB · 12 ms", "ok")
    t_warn = ToolCard(s5, "bash  python omics_pipeline.py --check", "exit 1 · 处理中…", "warn")
    s5.add(t_ok)
    s5.add(t_warn)
    PROBES.extend([("block_raised", r_raised, "surface"), ("block_glass", r_glass, "surface"),
                   ("block_inset", r_inset, "surface"), ("bubble_user", b_user, "text"),
                   ("bubble_ai", b_ai, "text"), ("tool_ok", t_ok, "text"),
                   ("tool_warn", t_warn, "text")])
    col.addWidget(s5)
    col.addStretch(1)
    return root


REPORT: list[str] = []


def shot(mode: str) -> str:
    # QApplication 必须先于 install()：否则 app 级兜底样式（滚动条）会被跳过
    app = QApplication.instance() or QApplication(sys.argv)
    set_appearance_mode(mode)
    skeuo_kit.install(ui_kit)
    app.setStyleSheet(skeuo_kit.scroll_qss())
    w = build()
    w.show()
    app.processEvents()
    w.repaint()
    for _ in range(4):
        app.processEvents()
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"skeuo_lab_{mode}.png")
    w.grab().save(path)                                   # 视觉稿（跟随 DPR，更清晰）
    # 体检用 1:1 渲染：grab() 是 DPR 1.5 的位图，逻辑坐标映射过去会整体错位
    meas = QtGui.QImage(w.size(), QtGui.QImage.Format.Format_RGB32)
    meas.setDevicePixelRatio(1.0)
    meas.fill(QtGui.QColor(0, 0, 0))
    w.render(meas)
    REPORT.append(f"== {mode} ==")
    crop = bool(os.environ.get("SKEUO_CROP"))
    for name, widget, kind in PROBES:
        tl = widget.mapTo(w, QtCore.QPoint(0, 0))
        rect = QtCore.QRect(tl, widget.size())
        if crop and kind in ("text", "surface"):
            meas.copy(rect).scaled(rect.width() * 3, rect.height() * 3,
                                   Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.FastTransformation).save(
                os.path.join(OUT, f"skeuo_crop_{mode}_{name}.png"))
        if rect.width() < 8 or rect.height() < 8:
            REPORT.append(f"  {name:<14} (未布局，跳过)")
            continue
        if kind == "text":
            bg, fg, cr, share = text_audit(meas, rect, intended_text(widget))
            flag = "" if cr >= 7 else ("  <- low" if cr >= 4.5 else "  <- LOW <4.5")
            if share < 0.004:
                flag += "  (字色未按预期出现)"
            if "disabled" in name:
                flag = "  (disabled: exempt)"
            REPORT.append(f"  {name:<14} text  bg={bg} fg={fg}  {cr:5.2f}:1  "
                          f"fg像素{share * 100:4.1f}%{flag}")
        else:
            depth, lo, hi = bevel_depth(meas, rect, probe_inset(name))
            flag = "" if depth >= 0.12 else ("  <- shallow" if depth >= 0.06 else "  <- FLAT")
            REPORT.append(f"  {name:<14} 3d    {lo} -> {hi}  dL={depth:5.3f}{flag}")
    w.close()
    return path


def main() -> int:
    set_color_theme(os.path.join(HERE, "theme_skeuo.json"))
    modes = ["dark", "light"]
    if "--mode" in sys.argv:
        modes = [sys.argv[sys.argv.index("--mode") + 1]]
    for m in modes:
        print("saved:", shot(m))
    text = "\n".join(REPORT) + "\n"
    with open(os.path.join(OUT, "skeuo_contrast.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
