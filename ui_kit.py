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

from PyCt6 import CLabel, ModeManager

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
            "todo": "muted", "运行中": "accent"}.get(status, "muted")


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
        w = self.width() if self.width() > 40 else self._basis
        need = text_height(text, self._font_size, max(40, w - 12),
                           self._font_style == "bold")
        if abs(inner.height() - need) > 1:
            inner.setFixedHeight(need)
            self.setFixedHeight(need + 10)

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
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(C("track")))
        p.drawRoundedRect(r, self.height() / 2, self.height() / 2)
        if self._value > 0:
            w = max(self.height(), self.width() * self._value)
            p.setBrush(QtGui.QColor(C("accent")))
            p.drawRoundedRect(QRectF(0, 0, w, self.height()),
                              self.height() / 2, self.height() / 2)


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
