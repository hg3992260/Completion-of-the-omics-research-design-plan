# -*- coding: utf-8 -*-
"""共享 UI 工具：蓝色科技配色、按字体度量自适应的标签、进度条、流式文本视图。

被 omics_pipeline.py（管线视图）与 design_studio.py（设计工作台）共用。
"""

from __future__ import annotations

import time

import sys

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtWidgets import QSizePolicy, QWidget

from PyCt6 import CLabel, CButton, ModeManager

if sys.platform == "darwin":                     # macOS：中文用苹方，等宽用 Menlo
    UI_FONT = "PingFang SC"
    MONO_FONT = "Menlo"
elif sys.platform == "win32":
    UI_FONT = "Microsoft YaHei UI"
    MONO_FONT = "Consolas"
else:                                             # Linux 等
    UI_FONT = "Noto Sans CJK SC"
    MONO_FONT = "DejaVu Sans Mono"

# 浅色：极简蓝白；深色：亮橙色科技（黑灰底 + 橙为主色，青绿/琥珀作状态色）
PAL = {
    "bg":           ("#EDF3FA", "#0F1013"),
    "surface":      ("#FFFFFF", "#191A1F"),
    "surface2":     ("#F5F9FE", "#131418"),
    "node":         ("#F8FBFF", "#1B1C21"),
    "node_hover":   ("#EAF2FC", "#24252C"),
    "node_active":  ("#E2F0FC", "#2A2118"),
    "border":       ("#D6E4F2", "#2C2E36"),
    "grid":         ("#C9DAEC", "#33353D"),
    "accent":       ("#0E7FC1", "#FF7A1A"),
    "accent_dim":   ("#7FB6DA", "#8A4A16"),
    "accent_hover": ("#0A6BA6", "#FF9445"),
    "on_accent":    ("#FFFFFF", "#1A0F05"),
    "text":         ("#16233A", "#ECEDF0"),
    "muted":        ("#6A8095", "#989AA4"),
    "muted_dim":    ("#54687C", "#8E9099"),
    "ok":           ("#0F9D6B", "#3DDC97"),
    "warn":         ("#B7791F", "#FFC53D"),
    "bad":          ("#C2410C", "#FF6B5C"),
    "track":        ("#DCE7F3", "#232429"),
    "user":         ("#0E7FC1", "#FFA24D"),
    "agent":        ("#0F9D6B", "#3DDC97"),
    "btn":          ("#F0F6FC", "#24252C"),
    "btn_hover":    ("#E2EEFC", "#2E3038"),
    "danger":       ("#C2410C", "#FF6B5C"),
    "danger_bg":    ("#FDF1EF", "#2A1A18"),

    # ---- 拟物化三维用色阶（浅色 / 深色）----
    # 卡片受光面与背光面（竖向渐变的上下端）
    "surf_hi":      ("#FFFFFF", "#23252B"),
    "surf_lo":      ("#EEF4FB", "#16171C"),
    # 倒角：上缘高光、下缘暗边
    "bevel_hi":     ("#FFFFFF", "#3A3D46"),
    "bevel_lo":     ("#C2D4E8", "#0C0D10"),
    # 投影（画在控件自身矩形内，不会越界）
    "shadow":       ("#93AECB", "#000000"),
    # 凹槽/内嵌件：上缘暗、下缘亮
    "groove_hi":    ("#BCD0E4", "#0B0C0F"),
    "groove_lo":    ("#FFFFFF", "#33363E"),
    # 凸起件（键帽/旋钮）的受光与背光
    "knob_hi":      ("#FFFFFF", "#31343C"),
    "knob_lo":      ("#DEE9F5", "#1A1C21"),
    # 强调色的亮/暗两端（用于渐变）
    "accent_hi":    ("#37A0DD", "#FFA45C"),
    "accent_lo":    ("#0A6BA6", "#D95F14"),
    "ok_hi":        ("#2FBF88", "#54E6A5"),
    "ok_lo":        ("#0B7C54", "#24A874"),
    "warn_hi":      ("#D9903A", "#FFD166"),
    "warn_lo":      ("#9A6415", "#D69B14"),
    "bad_hi":       ("#E0603F", "#FF8478"),
    "bad_lo":       ("#A83A22", "#C6473A"),
    # 页面底衬（径向渐变的中心与边缘）
    "back_hi":      ("#F7FBFF", "#1A1C22"),
    "back_lo":      ("#DFE9F5", "#0B0C0F"),
}


def C(key: str) -> str:
    light, dark = PAL[key]
    if ModeManager.mode == "dark":
        return dark
    if ModeManager.mode == "light":
        return light
    if QtGui.QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return dark
    return light


def status_key(status: str) -> str:
    return {"达标": "ok", "部分": "warn", "缺失": "bad",
            "done": "ok", "drafted": "accent", "asked": "warn",
            "doing": "warn", "todo": "muted", "运行中": "accent"}.get(status, "muted")


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()


def text_height(text: str, size_pt: int, width_px: int, bold: bool = False) -> int:
    f = QtGui.QFont(UI_FONT, size_pt)
    f.setBold(bold)
    fm = QtGui.QFontMetrics(f)
    rect = fm.boundingRect(QtCore.QRect(0, 0, max(20, width_px), 6000),
                           Qt.TextWordWrap | Qt.AlignLeft, text)
    return max(rect.height(), fm.lineSpacing()) + 4


class RefitLabel(CLabel):
    """宽度变化时按**实际宽度**重算高度，避免换行文字被裁切或压到别的控件上。"""

    def __init__(self, master, *, wrap=True, basis_px=400, **kw):
        self._wrap_on = wrap
        self._basis = basis_px
        super().__init__(master, **kw)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._refit()

    def _refit(self):
        if not self._wrap_on:
            return
        inner = self.label()
        text = inner.text() or ""
        if not text:
            return
        # 用**内层文字区**的实际宽度估算（外层 CLabel 比文字区宽约 10px，
        # 用外层宽度会在临界换行处低估一行，导致文字被压/被截）
        if inner.width() > 40:
            w = inner.width()
        elif self.width() > 40:
            w = self.width() - 12
        else:
            w = self._basis
        need = text_height(text, self._font_size, max(40, w - 4),
                           self._font_style == "bold")
        if abs(inner.height() - need) > 1:
            inner.setFixedHeight(need)
            self.setFixedHeight(need + 10)

    def fit_now(self):
        """立即按当前实际宽度重算高度（用于批量重建内容后强制对齐）。"""
        self._refit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refit()


def mk_label(parent, text, size=10, bold=False, color=None, align="left",
             width_px=400, wrap=True, bg=None, radius=0, min_h=0):
    """CLabel 包装：初始高度按 width_px 估算，之后随实际宽度自动重算。"""
    lbl = RefitLabel(parent, wrap=wrap, basis_px=width_px, width=10, height=10,
                     text=text, font_family=UI_FONT,
                     font_size=size, font_style="bold" if bold else None,
                     text_color=color, background_color=bg, corner_radius=radius,
                     border_width=0)
    inner = lbl.label()
    inner.setWordWrap(wrap)
    inner.setTextInteractionFlags(Qt.TextSelectableByMouse)
    halign = {"left": Qt.AlignLeft, "center": Qt.AlignHCenter, "right": Qt.AlignRight}[align]
    inner.setAlignment(halign | Qt.AlignVCenter)
    if wrap:
        inner_h = text_height(text, size, width_px, bold)
    else:
        # 不换行的标签只占一行高（此前按换行估算，长文本会被算成多行而挤掉相邻控件）
        fm = QtGui.QFontMetrics(QtGui.QFont(UI_FONT, size, weight=75 if bold else 50))
        inner_h = fm.lineSpacing() + 6
    inner.setFixedHeight(inner_h)
    lbl.setFixedHeight(max(inner_h + 10, min_h))
    return lbl


class ProgressBar(QWidget):
    def __init__(self, master, width=170, height=8):
        super().__init__(master)
        self._value = 0.0
        self.setFixedSize(width, height)

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, v))
        self.update()

    def _change_theme(self):
        self.update()

    def paintEvent(self, event):
        """内嵌凹槽 + 渐变进度 + 上缘高光，做出"液体在槽里"的立体感。"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        h = self.height()
        r = QRectF(0, 0, self.width(), h)
        rad = h / 2
        # 凹槽底色（上暗下亮 = 内嵌）
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(C("groove_hi")))
        p.drawRoundedRect(r, rad, rad)
        p.setBrush(QtGui.QColor(C("track")))
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), rad, rad)
        if self._value > 0:
            w = max(h, self.width() * self._value)
            fr = QRectF(1, 1, w - 2, h - 2)
            grad = QtGui.QLinearGradient(fr.topLeft(), fr.bottomLeft())
            grad.setColorAt(0.0, QtGui.QColor(C("accent_hi")))
            grad.setColorAt(1.0, QtGui.QColor(C("accent_lo")))
            p.setBrush(QtGui.QBrush(grad))
            p.drawRoundedRect(fr, rad, rad)
            # 玻璃高光：上半透明亮条
            gloss = QRectF(fr.left() + 2, fr.top() + 1.2, max(0.0, fr.width() - 4), h * 0.30)
            hl = QtGui.QColor("#FFFFFF")
            hl.setAlpha(70 if ModeManager.mode != "dark" else 40)
            p.setBrush(hl)
            p.drawRoundedRect(gloss, gloss.height() / 2, gloss.height() / 2)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QtGui.QPen(QtGui.QColor(C("bevel_lo")), 1))
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), rad, rad)


# --------------------------------------------------------------------------- 三维构件

CARD_PAD = 9          # 投影预留边距：阴影只画在控件自身矩形内，绝不越界遮挡邻居


class CheckBox3D(QtWidgets.QWidget):
    """三维勾选框：未选为凹陷空槽，选中为凸起绿钮 + 白色对勾。"""

    toggled = Signal(bool)

    def __init__(self, master, checked: bool = False, size: int = 16):
        super().__init__(master)
        self._checked = bool(checked)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, on: bool):
        on = bool(on)
        if on != self._checked:
            self._checked = on
            self.update()
            self.toggled.emit(on)

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)
        event.accept()

    def _change_theme(self):
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self._checked:
            p.setPen(QtGui.QPen(QtGui.QColor(C("ok_lo")), 1.0))
            p.setBrush(pair_brush("ok_hi", "ok_lo", r))
            p.drawRoundedRect(r, 4, 4)
            hl = QtGui.QColor("#FFFFFF")
            hl.setAlpha(90)
            p.setPen(QtGui.QPen(hl, 1.0))
            p.drawLine(QtCore.QPointF(r.left() + 3, r.top() + 1.4),
                       QtCore.QPointF(r.right() - 3, r.top() + 1.4))
            pen = QtGui.QPen(QtGui.QColor("#FFFFFF"), 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            w, h = r.width(), r.height()
            path = QtGui.QPainterPath()
            path.moveTo(r.left() + w * 0.26, r.top() + h * 0.52)
            path.lineTo(r.left() + w * 0.44, r.top() + h * 0.71)
            path.lineTo(r.left() + w * 0.75, r.top() + h * 0.31)
            p.drawPath(path)
        else:
            # 凹陷：上暗下亮 + 内阴影线
            p.setPen(QtGui.QPen(QtGui.QColor(C("groove_hi")), 1.0))
            p.setBrush(pair_brush("surf_lo", "surf_hi", r))
            p.drawRoundedRect(r, 4, 4)
            sh = QtGui.QColor(C("groove_hi"))
            sh.setAlpha(120)
            p.setPen(QtGui.QPen(sh, 1.2))
            p.drawLine(QtCore.QPointF(r.left() + 2.5, r.top() + 1.6),
                       QtCore.QPointF(r.right() - 2.5, r.top() + 1.6))


def pair_brush(hi_key: str, lo_key: str, rect: QRectF) -> QtGui.QBrush:
    g = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0.0, QtGui.QColor(C(hi_key)))
    g.setColorAt(1.0, QtGui.QColor(C(lo_key)))
    return QtGui.QBrush(g)


def draw_backdrop(p: QtGui.QPainter, rect: QRectF):
    """页面底衬：中心亮、边缘暗的径向渐变（给整个界面一个"被照亮"的纵深）。"""
    g = QtGui.QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.72)
    g.setColorAt(0.0, QtGui.QColor(C("back_hi")))
    g.setColorAt(1.0, QtGui.QColor(C("back_lo")))
    p.fillRect(rect, QtGui.QBrush(g))


class Card(QtWidgets.QFrame):
    """拟物化三维卡片：柔和多层投影 + 竖向渐变面 + 上缘高光/下缘暗边 + 描边。

    投影画在控件自身矩形内预留的 CARD_PAD 边距里，**不会越出控件边界**，
    因此不可能遮挡相邻控件；内容边距已包含该预留量。
    """

    def __init__(self, master, *, radius: int = 14, pad: int = CARD_PAD,
                 margin=(16, 14, 16, 14), spacing: int = 10, deep: bool = False,
                 horizontal: bool = False, **kw):
        super().__init__(master)
        self._radius = radius
        self._pad = pad
        self._deep = deep                       # deep=True 投影更重（用于顶层容器）
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        lay = (QtWidgets.QHBoxLayout if horizontal else QtWidgets.QVBoxLayout)(self)
        lay.setContentsMargins(pad + margin[0], pad + margin[1],
                               pad + margin[2], pad + margin[3])
        lay.setSpacing(spacing)
        self._layout = lay

    def layout(self):
        return self._layout

    def set_content_margins(self, left: int, top: int, right: int, bottom: int):
        self._layout.setContentsMargins(self._pad + left, self._pad + top,
                                        self._pad + right, self._pad + bottom)

    def _change_theme(self):
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        body = QRectF(self.rect()).adjusted(self._pad, self._pad, -self._pad, -self._pad)
        if body.width() <= 2 or body.height() <= 2:
            return
        # 1) 投影：多层递减，向下偏移，营造"悬浮"厚度
        layers = ((3.0, 26), (1.8, 20), (0.9, 16)) if not self._deep else \
                 ((5.0, 40), (3.0, 30), (1.4, 22))
        p.setPen(Qt.PenStyle.NoPen)
        for dy, alpha in layers:
            col = QtGui.QColor(C("shadow"))
            col.setAlpha(alpha if ModeManager.mode != "dark" else alpha + 30)
            p.setBrush(col)
            p.drawRoundedRect(body.adjusted(-1.5, dy - 1.5, 1.5, dy + 1.5),
                              self._radius, self._radius)
        # 2) 面：竖向渐变
        p.setBrush(pair_brush("surf_hi", "surf_lo", body))
        p.drawRoundedRect(body, self._radius, self._radius)
        # 3) 上缘高光（沿圆角内缩的一条亮线）→ 受光倒角
        hi = QtGui.QColor(C("bevel_hi"))
        p.setPen(QtGui.QPen(hi, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        arc = self._radius * 0.6
        path = QtGui.QPainterPath()
        path.moveTo(body.left() + arc, body.top() + 0.8)
        path.lineTo(body.right() - arc, body.top() + 0.8)
        p.drawPath(path)
        # 4) 下缘暗边 → 背光倒角
        p.setPen(QtGui.QPen(QtGui.QColor(C("bevel_lo")), 1.2))
        path2 = QtGui.QPainterPath()
        path2.moveTo(body.left() + arc, body.bottom() - 0.8)
        path2.lineTo(body.right() - arc, body.bottom() - 0.8)
        p.drawPath(path2)
        # 5) 描边
        p.setPen(QtGui.QPen(QtGui.QColor(C("border")), 1.0))
        p.drawRoundedRect(body.adjusted(0.5, 0.5, -0.5, -0.5), self._radius, self._radius)


class FlowStepper(QtWidgets.QWidget):
    """三维流程步进条：把四个视图按**先后顺序**做成凹槽里的键帽。

    - 已完成的步骤：绿色 ✓，键帽下沉；当前步骤：抬起 + 强调色渐变 + 投影；
    - 步骤之间的连接段在完成后被强调色填充 → 一眼看出流程推进到哪；
    - 全部绘制在自身矩形内，不产生越界遮挡。
    """

    stepClicked = Signal(int)                   # 点击某一步 → 跳到该视图

    def __init__(self, master, steps, width=0, height=44):
        super().__init__(master)
        self.steps = list(steps)                # [{"title": "工作台", "sub": "设计"}, ...]
        self.cur = 0
        self.states = ["todo"] * len(self.steps)
        self.hover = -1
        self.setMouseTracking(True)
        if width and width > 0:
            self.setFixedSize(width, height)
        else:                                   # 自适应宽度（放在流程条容器里铺满）
            self.setMinimumWidth(120 * len(self.steps))
            self.setFixedHeight(height)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # -- 对外接口 --
    def set_current(self, idx: int):
        self.cur = max(0, min(len(self.steps) - 1, idx))
        for i in range(len(self.steps)):
            self.states[i] = "done" if i < self.cur else ("active" if i == self.cur else "todo")
        self.update()

    def set_badge(self, idx: int, text: str):
        """在步骤下方挂一个角标（如进度 n/10）。"""
        if 0 <= idx < len(self.steps):
            self.steps[idx]["badge"] = text
            self.update()

    def _rect(self, i: int) -> QRectF:
        n = len(self.steps)
        gap = 14.0
        w = (self.width() - gap * (n - 1)) / n
        return QRectF(i * (w + gap), 0, w, self.height())

    def _index_at(self, pos) -> int:
        for i in range(len(self.steps)):
            if self._rect(i).contains(pos):
                return i
        return -1

    def mouseMoveEvent(self, e):
        i = self._index_at(e.position())
        if i != self.hover:
            self.hover = i
            self.update()

    def leaveEvent(self, e):
        self.hover = -1
        self.update()

    def mousePressEvent(self, e):
        i = self._index_at(e.position())
        if i >= 0:
            self.stepClicked.emit(i)

    def _change_theme(self):
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        f_t = QtGui.QFont(UI_FONT, 9)
        f_t.setBold(True)
        f_n = QtGui.QFont(MONO_FONT, 8)
        f_n.setBold(True)
        f_b = QtGui.QFont(UI_FONT, 7)
        for i, st in enumerate(self.steps):
            r = self._rect(i)
            state = self.states[i]
            active = state == "active"
            done = state == "done"
            rad = 9.0
            # 键帽下方的投影（抬起感）
            p.setPen(Qt.PenStyle.NoPen)
            if active or self.hover == i:
                col = QtGui.QColor(C("shadow"))
                col.setAlpha(60 if active else 34)
                p.setBrush(col)
                p.drawRoundedRect(r.adjusted(0, 1.5, 0, 5.5), rad, rad)
            # 键帽面
            if active:
                brush = pair_brush("accent_hi", "accent_lo", r)
            elif done:
                brush = pair_brush("surf_hi", "surf_lo", r)
            else:
                brush = pair_brush("knob_lo", "knob_lo", r)
            p.setBrush(brush)
            p.drawRoundedRect(r, rad, rad)
            # 倒角：上亮下暗（按下/未到的步骤反过来 = 内嵌感）
            if done or active:
                p.setPen(QtGui.QPen(QtGui.QColor(C("bevel_hi")), 1.0))
                p.drawLine(QtCore.QPointF(r.left() + rad * 0.6, r.top() + 0.8),
                           QtCore.QPointF(r.right() - rad * 0.6, r.top() + 0.8))
                p.setPen(QtGui.QPen(QtGui.QColor(C("bevel_lo")), 1.0))
                p.drawLine(QtCore.QPointF(r.left() + rad * 0.6, r.bottom() - 0.8),
                           QtCore.QPointF(r.right() - rad * 0.6, r.bottom() - 0.8))
            else:
                p.setPen(QtGui.QPen(QtGui.QColor(C("groove_hi")), 1.0))
                p.drawLine(QtCore.QPointF(r.left() + rad * 0.6, r.top() + 0.8),
                           QtCore.QPointF(r.right() - rad * 0.6, r.top() + 0.8))
                p.setPen(QtGui.QPen(QtGui.QColor(C("groove_lo")), 1.0))
                p.drawLine(QtCore.QPointF(r.left() + rad * 0.6, r.bottom() - 0.8),
                           QtCore.QPointF(r.right() - rad * 0.6, r.bottom() - 0.8))
            p.setPen(QtGui.QPen(QtGui.QColor(C("border")), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), rad, rad)
            # 序号圆章（左） + 标题（右）
            cx, cy = r.left() + 15, r.center().y()
            p.setPen(Qt.PenStyle.NoPen)
            badge_col = QtGui.QColor(C("ok_hi") if done else
                                     (C("on_accent") if active else C("muted")))
            if done:
                p.setBrush(QtGui.QColor(C("ok_lo")))
                p.drawEllipse(QtCore.QPointF(cx, cy), 8.5, 8.5)
                p.setPen(QtGui.QPen(QtGui.QColor("#FFFFFF")))
                p.setFont(f_n)
                p.drawText(QRectF(cx - 8.5, cy - 8, 17, 16), Qt.AlignCenter, "✓")
            else:
                p.setBrush(QtGui.QColor(C("knob_hi") if active else C("surface")))
                p.drawEllipse(QtCore.QPointF(cx, cy), 8.5, 8.5)
                p.setPen(QtGui.QPen(QtGui.QColor(
                    C("on_accent") if active else C("muted_dim")), 1.0))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QtCore.QPointF(cx, cy), 8.5, 8.5)
                p.setPen(QtGui.QPen(badge_col))
                p.setFont(f_n)
                p.drawText(QRectF(cx - 8.5, cy - 8, 17, 16), Qt.AlignCenter, str(i + 1))
            tx = cx + 13
            avail = r.right() - tx - 8
            p.setPen(QtGui.QPen(QtGui.QColor(C("on_accent") if active else
                                             (C("text") if done else C("muted")))))
            p.setFont(f_t)
            p.drawText(QRectF(tx, cy - 15, avail, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, st.get("title", ""))
            p.setPen(QtGui.QPen(QtGui.QColor(C("on_accent") if active else C("muted_dim"))))
            p.setFont(f_b)
            p.drawText(QRectF(tx, cy + 0.5, avail, 13),
                       Qt.AlignLeft | Qt.AlignVCenter, st.get("badge") or st.get("sub", ""))
            # 连接段：完成后填充强调色，未完成留凹槽
            if i < len(self.steps) - 1:
                y = cy
                seg = QRectF(r.right() + 2, y - 1.5, 10, 3)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QtGui.QColor(C("groove_hi")))
                p.drawRoundedRect(seg, 1.5, 1.5)
                if done:
                    p.setBrush(QtGui.QColor(C("accent")))
                    p.drawRoundedRect(seg, 1.5, 1.5)
                # 箭头
                ax = seg.right() + 1
                tri = QtGui.QPolygonF([QtCore.QPointF(ax, y - 4),
                                       QtCore.QPointF(ax + 4, y),
                                       QtCore.QPointF(ax, y + 4)])
                p.setBrush(QtGui.QColor(C("accent") if done else C("grid")))
                p.drawPolygon(tri)


def install_button_skin():
    """给 PyCt6 的 CButton 套一层立体皮肤（渐变面 + 上亮下暗倒角）。

    采用运行时包装而非修改第三方包：只在其自身 stylesheet 之后追加阴影/渐变，
    失败时静默回退（不影响原样式）。
    """

    def qss(widget) -> str:
        base = getattr(widget, "_background_color", None)
        base = base[1] if (ModeManager.mode == "dark" and isinstance(base, tuple)) else \
               (base[0] if isinstance(base, tuple) else base)
        txt = getattr(widget, "_text_color", None)
        txt = txt[1] if (ModeManager.mode == "dark" and isinstance(txt, tuple)) else \
              (txt[0] if isinstance(txt, tuple) else txt)
        rad = getattr(widget, "_corner_radius", 8)
        hi = QtGui.QColor(C("bevel_hi")).name()
        lo = QtGui.QColor(C("bevel_lo")).name()
        return (
            f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f" stop:0 {base}, stop:0.52 {base}, stop:1 {lo});"
            f" color: {txt}; border: 1px solid {lo}; border-top: 1px solid {hi};"
            f" border-radius: {rad}px; padding: 3px 10px; }}"
            f"QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f" stop:0 {C('knob_hi')}, stop:1 {base}); }}"
            f"QPushButton:pressed {{ background: {lo}; border-top: 1px solid {lo};"
            f" border-bottom: 1px solid {hi}; padding-top: 4px; }}")

    if getattr(CButton, "_dsh_skinned", False):
        return
    orig = CButton._change_theme

    def patched(self):
        orig(self)
        try:
            self.button().setStyleSheet(qss(self) + self.button().styleSheet())
        except Exception:                                       # noqa: BLE001
            pass

    CButton._change_theme = patched
    CButton._dsh_skinned = True


class TranscriptView(QtWidgets.QTextEdit):
    """对话流水：内部保存块列表，切换深浅色时整段重绘（否则旧文字会保留旧配色）。"""

    def __init__(self, master):
        super().__init__(master)
        self.setReadOnly(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.document().setDocumentMargin(14)
        self._blocks = []
        self._stream = None
        self._change_theme()

    def _change_theme(self):
        self.setStyleSheet(
            f"QTextEdit {{ background: {C('surface2')}; color: {C('text')};"
            f" border: 1px solid {C('border')}; border-radius: 12px;"
            f" font-family: '{UI_FONT}'; font-size: 10.5pt; }}"
            f"QScrollBar:vertical {{ background: {C('track')}; width: 10px;"
            " border-radius: 5px; margin: 4px; }"
            f"QScrollBar::handle:vertical {{ background: {C('accent_dim')};"
            " border-radius: 5px; min-height: 30px; }"
            "QScrollBar::add-line, QScrollBar::sub-line { height: 0; }")
        self._render_all()

    # -- 块模型 -------------------------------------------------------------
    def _cursor_end(self):
        cur = self.textCursor()
        cur.movePosition(QtGui.QTextCursor.MoveOperation.End)
        return cur

    def _insert_header(self, text: str, tone: str, meta: str):
        cur = self._cursor_end()
        color = C(tone) if tone in PAL else C("text")
        cur.insertHtml(
            "<div style='margin-top:14px; margin-bottom:2px;'>"
            f"<span style='color:{color}; font-weight:700; font-size:11pt;'>{text}</span>"
            + (f"<span style='color:{C('muted')}; font-size:9pt;'>　{meta}</span>" if meta else "")
            + "</div>")
        self.setTextCursor(cur)

    def _insert_text(self, text: str, tone: str = "text", size: float = 10.5):
        cur = self._cursor_end()
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor(C(tone) if tone in PAL else C("text")))
        fmt.setFont(QtGui.QFont(UI_FONT, size))
        cur.insertText(text, fmt)
        self.setTextCursor(cur)

    def _render_all(self):
        self.clear()
        self._stream = None
        for b in self._blocks:
            if b["kind"] == "header":
                self._insert_header(b["text"], b.get("tone", "agent"), b.get("meta", ""))
            elif b["kind"] == "html":
                cur = self._cursor_end()
                cur.insertHtml(b["html"])
                self.setTextCursor(cur)
            else:
                self._insert_text(b["text"], b.get("tone", "text"))
        self.ensureCursorVisible()

    # -- 内容 ---------------------------------------------------------------
    def add_header(self, text: str, tone: str = "agent", meta: str = ""):
        self._blocks.append({"kind": "header", "text": text, "tone": tone, "meta": meta})
        self._insert_header(text, tone, meta)
        self.ensureCursorVisible()

    def add_html(self, html: str):
        self._blocks.append({"kind": "html", "html": html})
        cur = self._cursor_end()
        cur.insertHtml(html)
        self.setTextCursor(cur)
        self.ensureCursorVisible()

    def add_text_block(self, text: str, tone: str = "text", size: int = 10.5):
        self._blocks.append({"kind": "text", "text": text, "tone": tone, "size": size})
        self._insert_text(text, tone, size)
        self.ensureCursorVisible()

    def stream(self, piece: str, tone: str = "text"):
        if self._stream is None:
            self._stream = {"kind": "text", "text": "", "tone": tone}
            self._blocks.append(self._stream)
        self._stream["text"] += piece
        self._insert_text(piece, tone)
        self.ensureCursorVisible()

    def end_stream(self):
        self._stream = None

    def add_rule(self):
        self.add_html(f"<hr style='border:none; border-top:1px solid {C('border')};"
                      " margin-top:12px; margin-bottom:2px;'>")


def stream_format(tone: str = "text", size: float = 10.5) -> QtGui.QTextCharFormat:
    fmt = QtGui.QTextCharFormat()
    fmt.setForeground(QtGui.QColor(C(tone) if tone in PAL else C("text")))
    fmt.setFont(QtGui.QFont(UI_FONT, size))
    return fmt


class WorkScroll(QtWidgets.QScrollArea):
    """工作区容器：内容自适应高度，超高时出现细滚动条（配合自动换行的长文本）。"""

    def __init__(self, master):
        super().__init__(master)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        self._change_theme()

    def _change_theme(self):
        self.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
            f"QScrollBar:vertical {{ background: {C('track')}; width: 8px;"
            " border-radius: 4px; margin: 2px; }"
            f"QScrollBar::handle:vertical {{ background: {C('accent_dim')};"
            " border-radius: 4px; min-height: 24px; }"
            "QScrollBar::add-line, QScrollBar::sub-line { height: 0; }"
            "QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }")
        self.viewport().setStyleSheet("background: transparent;")


class CreditBar(QWidget):
    """底部署名条：designed by christ.paul90@gmail.com ,all rights reserved"""

    MAIL = "christ.paul90@gmail.com"
    TEXT = "designed by christ.paul90@gmail.com ,all rights reserved"

    def __init__(self, master, height=24):
        super().__init__(master)
        self.setFixedHeight(height)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 14, 2)
        lay.setSpacing(0)
        self._label = QtWidgets.QLabel(self)
        self._label.setOpenExternalLinks(True)          # 邮箱可点，直接调起邮件客户端
        self._label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self._label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._label.setFont(QtGui.QFont(UI_FONT, 9))
        lay.addStretch(1)
        lay.addWidget(self._label)
        self._change_theme()

    def _change_theme(self):
        col = C("muted")
        self._label.setText(
            f"<span style='color:{col};'>designed by "
            f"<a href='mailto:{self.MAIL}' style='color:{col}; text-decoration:none;'>"
            f"{self.MAIL}</a> ,all rights reserved</span>")
        self._label.setStyleSheet(f"background: transparent; color: {col};")


class BusyIndicator(QWidget):
    """左下角的显眼动画：等待模型响应时显示橙色胶囊 + 均衡器律动 + 流光 + 计时。

    空闲时显示为低调的灰点 + 文案，位置固定，不会造成布局跳动。
    """

    def __init__(self, master, width=286, height=30):
        super().__init__(master)
        self.setFixedSize(width, height)
        self._busy = False
        self._phase = 0.0
        self._t0 = 0.0
        self._label = "就绪"
        self._idle = "就绪"
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(60)                 # ≈16fps，够顺滑也不吃 CPU
        self._timer.timeout.connect(self._tick)

    # -- 状态 ---------------------------------------------------------------
    def start(self, label: str = "正在生成"):
        self._busy = True
        self._label = label
        self._t0 = time.time()
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def stop(self, idle: str = "就绪"):
        self._busy = False
        self._idle = idle
        self._timer.stop()
        self.update()

    def set_idle(self, text: str):
        self._idle = text
        if not self._busy:
            self.update()

    def is_busy(self) -> bool:
        return self._busy

    def _tick(self):
        self._phase += 0.26
        if self._phase > 6.28318:
            self._phase -= 6.28318
        self.update()

    def _change_theme(self):
        self.update()

    # -- 绘制 ---------------------------------------------------------------
    def paintEvent(self, event):
        import math
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()
        rect = QRectF(0.5, 0.5, w - 1, h - 1)

        if not self._busy:
            dot = QtGui.QColor(C("muted"))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dot)
            p.drawEllipse(QtCore.QPointF(12, h / 2), 3.5, 3.5)
            p.setPen(QtGui.QPen(QtGui.QColor(C("muted"))))
            f = QtGui.QFont(UI_FONT, 9)
            p.setFont(f)
            p.drawText(QRectF(24, 0, w - 28, h), Qt.AlignLeft | Qt.AlignVCenter, self._idle)
            return

        accent = QtGui.QColor(C("accent"))

        # 胶囊底 + 描边
        bg = QtGui.QColor(accent)
        bg.setAlpha(38)
        p.setPen(QtGui.QPen(accent, 1.2))
        p.setBrush(bg)
        p.drawRoundedRect(rect, h / 2, h / 2)

        # 流光：一条从左到右扫过的高光带
        sweep_w = 70.0
        span = w + sweep_w
        sx = (self._phase / 6.28318) * span - sweep_w
        grad = QtGui.QLinearGradient(sx, 0, sx + sweep_w, 0)
        c0 = QtGui.QColor(accent)
        c0.setAlpha(0)
        c1 = QtGui.QColor(accent)
        c1.setAlpha(58)
        grad.setColorAt(0.0, c0)
        grad.setColorAt(0.5, c1)
        grad.setColorAt(1.0, c0)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(rect, h / 2, h / 2)

        # 均衡器：4 根律动的竖条
        bx = 14.0
        for i in range(4):
            amp = math.sin(self._phase * 1.8 + i * 0.85)
            bar_h = 7 + (amp + 1) * 4.5            # 7 ~ 16px
            bar = QRectF(bx, h / 2 - bar_h / 2, 3.0, bar_h)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            p.drawRoundedRect(bar, 1.5, 1.5)
            bx += 6.0

        # 文案 + 计时
        elapsed = time.time() - self._t0
        p.setPen(QtGui.QPen(accent))
        f = QtGui.QFont(UI_FONT, 9)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(44, 0, w - 50, h), Qt.AlignLeft | Qt.AlignVCenter,
                   f"{self._label} · {elapsed:.0f}s")

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        if self._busy and not self._timer.isActive():
            self._timer.start()
        super().showEvent(event)


class ThinkingButton(QWidget):
    """主操作按钮：空闲时是普通主按钮，等待模型响应时变成"正在思考"动画。

    思考态 = 旋转弧线 + 呼吸式省略号 + 底部不定量流光条，比单纯把按钮置灰更直观。
    """

    clicked = Signal()

    def __init__(self, master, width=200, height=34, text="开始本阶段",
                 font_size=10, radius=8):
        super().__init__(master)
        self.setFixedSize(width, height)
        self._text = text
        self._radius = radius
        self._font_size = font_size
        self._busy = False
        self._phase = 0.0
        self._hover = False
        self._press = False
        self._enabled = True
        self._t0 = 0.0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._tick)

    # -- 状态 ---------------------------------------------------------------
    def set_idle_text(self, text: str):
        self._text = text
        if not self._busy:
            self.update()

    def setEnabled(self, enabled: bool):                        # noqa: N802
        self._enabled = bool(enabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled
                       else Qt.CursorShape.ArrowCursor)
        self.update()

    def start(self, label: str = "正在思考"):
        self._busy = True
        self._text = label
        self._t0 = time.time()
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def stop(self, text: str = "开始本阶段"):
        self._busy = False
        self._text = text
        self._timer.stop()
        self.update()

    def is_busy(self) -> bool:
        return self._busy

    def _tick(self):
        self._phase += 0.16
        if self._phase > 6.28318:
            self._phase -= 6.28318
        self.update()

    def _change_theme(self):
        self.update()

    # -- 交互 ---------------------------------------------------------------
    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self._press = False
        self.update()

    def mousePressEvent(self, event):
        if self._enabled and not self._busy:
            self._press = True
            self.update()

    def mouseReleaseEvent(self, event):
        was = self._press
        self._press = False
        self.update()
        if was and self._enabled and not self._busy and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()

    # -- 绘制 ---------------------------------------------------------------
    def paintEvent(self, event):
        import math
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()
        rect = QRectF(0.5, 0.5, w - 1, h - 1)
        accent = QtGui.QColor(C("accent"))

        if self._busy:
            # 思考态：浅底 + 描边
            bg = QtGui.QColor(accent)
            bg.setAlpha(34)
            p.setPen(QtGui.QPen(accent, 1.2))
            p.setBrush(bg)
            p.drawRoundedRect(rect, self._radius, self._radius)

            # 底部不定量流光条
            bar = QRectF(rect.left() + 6, rect.bottom() - 4.5, rect.width() - 12, 2.5)
            p.setPen(Qt.PenStyle.NoPen)
            track = QtGui.QColor(accent)
            track.setAlpha(40)
            p.setBrush(track)
            p.drawRoundedRect(bar, 1.2, 1.2)
            frac = (self._phase / 6.28318)
            seg = bar.width() * 0.34
            x = bar.left() + (bar.width() + seg) * frac - seg
            vis = QRectF(max(bar.left(), x), bar.top(),
                         min(bar.right(), x + seg) - max(bar.left(), x), bar.height())
            if vis.width() > 1:
                p.setBrush(accent)
                p.drawRoundedRect(vis, 1.2, 1.2)

            # 旋转弧线
            cx, cy, r = 20.0, h / 2 - 1, 7.5
            pen = QtGui.QPen(accent, 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            start = int((-self._phase * 57.2958) * 16)
            p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), start, 120 * 16)

            # 文案 + 呼吸省略号
            dots = "." * (1 + int((self._phase % 2.0) / 0.67))
            p.setPen(QtGui.QPen(accent))
            f = QtGui.QFont(UI_FONT, self._font_size)
            f.setBold(True)
            p.setFont(f)
            p.drawText(QRectF(cx + r + 10, 0, w - (cx + r + 14), h - 3),
                       Qt.AlignLeft | Qt.AlignVCenter, f"{self._text}{dots}")
            return

        # 空闲态：常规主按钮
        if not self._enabled:
            fill = QtGui.QColor(C("muted"))
            fill.setAlpha(70)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(rect, self._radius, self._radius)
            p.setPen(QtGui.QPen(QtGui.QColor(C("muted"))))
        else:
            base = QtGui.QColor(C("accent"))
            if self._press:
                base = base.darker(115)
            elif self._hover:
                base = QtGui.QColor(C("accent_hover"))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(base)
            p.drawRoundedRect(rect, self._radius, self._radius)
            p.setPen(QtGui.QPen(QtGui.QColor(C("on_accent"))))
        f = QtGui.QFont(UI_FONT, self._font_size)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self._text)


def fit_height(scroll: "WorkScroll", content_height: int, lo: int = 150, hi: int = 460) -> int:
    """按内容高度设置容器高度（带上下限），返回最终高度。"""
    h = max(lo, min(hi, int(content_height)))
    scroll.setFixedHeight(h)
    return h


def screen_size(prefer_w: int = 1520, prefer_h: int = 960,
                min_w: int = 1180, min_h: int = 720) -> tuple:
    """按当前显示器可用区域给出合适的窗口尺寸与位置，避免窗口超出屏幕导致底部被截。"""
    scr = QtWidgets.QApplication.primaryScreen()
    area = scr.availableGeometry() if scr else None
    if area is None:
        return prefer_w, prefer_h, None, None
    w = max(min_w, min(prefer_w, int(area.width() * 0.96)))
    h = max(min_h, min(prefer_h, int(area.height() * 0.94)))
    x = area.x() + (area.width() - w) // 2
    y = area.y() + (area.height() - h) // 2
    return w, h, x, y
