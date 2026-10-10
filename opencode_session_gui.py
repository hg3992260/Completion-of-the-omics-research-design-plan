# -*- coding: utf-8 -*-
"""opencode 会话窗口（PyCt6 + skeuo_kit 高对比拟物三维皮肤）。

**这是什么**：本仓库此前没有"opencode 自己的界面"——内核是以外部终端里跑 `opencode attach`
的 TUI 形式存在的（kernel_driver.py:11 明确写着"交互镜像仍在 opencode 自带 TUI（不重写会话 UI）"）。
这个窗口就是那件一直没做的事：把 opencode 的会话 UI 做成本机 PySide6 窗口，并套上新的皮肤。

结构（对齐 opencode 桌面版的直觉布局）：

    ┌───────────┬────────────────────────────────────┬────────────┐
    │ 会话侧栏   │ 会话头部（标题/模型/状态/操作）        │ 上下文面板  │
    │ 项目+会话  ├────────────────────────────────────┤ 用量+工具   │
    │ 模型选择   │ 对话流（气泡 / 思考 / 工具卡 / 问答）  │ 权限        │
    │ 内核状态   ├────────────────────────────────────┤            │
    │           │ 输入区（多行 + 发送 + 提示）          │            │
    └───────────┴────────────────────────────────────┴────────────┘

**两种运行模式**：

* ``--demo``：完全离线，灌一段假会话（截图/评审用）。默认。
* ``--live``：真连内嵌内核 —— 用 kernel_driver.KernelDriver 驱动
  （``run_turn_async`` 的规范化事件 → 逐块渲染），会话/模型来自 kernel_client。
  ``opencode.exe`` 缺失时不会崩：状态栏变红并说明，界面仍可浏览。

用法::

    D:\\python\\envs\\mar\\python.exe opencode_session_gui.py            # 离线演示
    D:\\python\\envs\\mar\\python.exe opencode_session_gui.py --live     # 连内核
    D:\\python\\envs\\mar\\python.exe opencode_session_gui.py --shot     # 离线出图（深/浅各一张）
"""

from __future__ import annotations

import os
import sys
import threading
import time

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QSizePolicy,
                               QVBoxLayout, QWidget)

from PyCt6 import (CButton, CComboBox, CFrame, CLabel, CLineEdit, CTextEdit,
                   ModeManager, set_appearance_mode, set_color_theme)

import ui_kit
import skeuo_kit
from ui_kit import (C, PAL, UI_FONT, MONO_FONT, CreditBar, ProgressBar,
                    WorkScroll, draw_backdrop, mk_label, text_height)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_shots")
FONT = UI_FONT


def _resource(name: str) -> str:
    """只读资源：exe 同级（用户可替换主题/图标）→ 打包内置 → 源码目录。

    走 app_paths，保证"源码运行"与"PyInstaller 冻结后"取到的是同一套规则。
    """
    try:
        from app_paths import resource_path
        p = resource_path(name)
        if os.path.exists(p):
            return p
    except Exception:                                                # noqa: BLE001
        pass
    return os.path.join(HERE, name)


def _out_dir() -> str:
    """出图目录：冻结后落 exe 同级 _shots（绿色便携），源码运行落仓库 _shots。"""
    try:
        from app_paths import data_path
        return data_path("_shots")
    except Exception:                                                # noqa: BLE001
        return os.path.join(HERE, "_shots")


# ===========================================================================
# 基础构件（全部自绘，才能把"上亮下暗 + 投影 + 内嵌"做到位）
# ===========================================================================
class Block(QWidget):
    """所有对话块的基类：统一提供主题广播与高度自适应。"""

    def __init__(self, master, height: int = 40):
        super().__init__(master)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(height)

    def _change_theme(self):
        self.update()


class SessionItem(Block):
    """侧栏的一条会话：选中 = 凸起 + 橙色主色条；未选中 = 平放；悬停 = 微亮。"""

    clicked = Signal(str)

    def __init__(self, master, title: str, subtitle: str, active: bool = False):
        super().__init__(master, 52)
        self.title, self.subtitle, self._active = title, subtitle, active
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(52)

    def set_active(self, on: bool):
        self._active = bool(on)
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit(self.title)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(6, 3, -6, -4)
        if self._active:
            base = skeuo_kit.resolve(PAL["node_active"])
            skeuo_kit.draw_contact_shadow(p, r, 10, depth=0.8)
            skeuo_kit.draw_raised(p, r, base, 10, gloss=True, gloss_alpha=30)
            # 左侧主色条
            p.setPen(Qt.PenStyle.NoPen)
            acc = skeuo_kit.resolve(PAL["accent"])
            p.setBrush(skeuo_kit.vgrad(r, skeuo_kit.lighten(acc, 0.3), skeuo_kit.darken(acc, 0.3)))
            p.drawRoundedRect(QRectF(r.left() + 1, r.top() + 1, 4, r.height() - 2), 2, 2)
        elif self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(skeuo_kit.resolve(PAL["node_hover"]))
            p.drawRoundedRect(r, 10, 10)
        f = QtGui.QFont(FONT, 9, QtGui.QFont.Weight.DemiBold)
        p.setFont(f)
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["title_text" if self._active else "text"])))
        p.drawText(QRectF(r.left() + 14, r.top() + 6, r.width() - 22, 18),
                   Qt.AlignLeft | Qt.AlignVCenter, self.title)
        p.setFont(QtGui.QFont(FONT, 8))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["muted" if self._active else "muted_dim"])))
        p.drawText(QRectF(r.left() + 14, r.top() + 24, r.width() - 22, 16),
                   Qt.AlignLeft | Qt.AlignVCenter, self.subtitle)


class Bubble(Block):
    """对话气泡。role: user / ai / system。"""
    reply = Signal(str)

    def __init__(self, master, role: str, text: str, meta: str = ""):
        self.role, self.text, self.meta = role, text, meta
        self._w = 640
        h = text_height(text, 10, self._w - 34) + (34 if meta else 20)
        super().__init__(master, h)
        self.setFixedHeight(max(38, h))

    def set_width_hint(self, w: int):
        self._w = max(240, w)
        h = text_height(self.text, 10, self._w - 34) + (34 if self.meta else 20)
        self.setFixedHeight(max(38, h))
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(8, 4, -8, -6)
        user = self.role == "user"
        hi = skeuo_kit.resolve(PAL["bubble_user_hi" if user else "bubble_ai_hi"])
        lo = skeuo_kit.resolve(PAL["bubble_user_lo" if user else "bubble_ai_lo"])
        edge = skeuo_kit.resolve(PAL["bubble_user_edge" if user else "bubble_ai_edge"])
        skeuo_kit.draw_contact_shadow(p, r, 12, depth=0.75)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(skeuo_kit.vgrad(r, hi, lo))
        p.drawRoundedRect(r, 12, 12)
        p.setPen(QtGui.QPen(skeuo_kit.alpha(hi, 160), 1.2))          # 上缘高光
        p.drawLine(QtCore.QPointF(r.left() + 12, r.top() + 0.8),
                   QtCore.QPointF(r.right() - 12, r.top() + 0.8))
        p.setPen(QtGui.QPen(edge, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        # 角色徽标
        tag = {"user": "你", "ai": "opencode", "system": "系统"}.get(self.role, self.role)
        tag_col = {"user": "user", "ai": "agent", "system": "muted"}.get(self.role, "muted")
        p.setFont(QtGui.QFont(FONT, 8, QtGui.QFont.Weight.Bold))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL[tag_col])))
        p.drawText(QRectF(r.left() + 14, r.top() + 4, 120, 16),
                   Qt.AlignLeft | Qt.AlignVCenter, tag)
        if self.meta:
            p.setFont(QtGui.QFont(FONT, 7))
            p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["muted_dim"])))
            p.drawText(QRectF(r.right() - 200, r.top() + 4, 186, 16),
                       Qt.AlignRight | Qt.AlignVCenter, self.meta)
        p.setFont(QtGui.QFont(FONT, 10))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["title_text" if user else "text"])))
        p.drawText(r.adjusted(14, 22 if self.meta or True else 10, -14, -8),
                   Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self.text)


class Reasoning(Block):
    """思考块：左侧一道凹槽导轨 + 暗字，与正文区分开。"""

    def __init__(self, master, text: str, seconds: float = 0.0):
        self.text = text
        self.seconds = seconds
        self._w = 640
        h = text_height(text, 9, self._w - 46) + 30
        super().__init__(master, h)
        self.setFixedHeight(max(34, h))

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(8, 3, -8, -4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(skeuo_kit.resolve(PAL["surface2"]))
        p.drawRoundedRect(r, 10, 10)
        rail = QRectF(r.left() + 1, r.top() + 3, 4, r.height() - 6)
        p.setBrush(skeuo_kit.inset(rail, skeuo_kit.resolve(PAL["track"])))
        p.drawRoundedRect(rail, 2, 2)
        p.setFont(QtGui.QFont(FONT, 7, QtGui.QFont.Weight.DemiBold))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["muted_dim"])))
        p.drawText(QRectF(r.left() + 14, r.top() + 4, r.width() - 26, 14),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   "思考中 %.1fs" % self.seconds if self.seconds else "思考")
        p.setFont(QtGui.QFont(FONT, 9))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["muted"])))
        p.drawText(r.adjusted(14, 20, -12, -6),
                   Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self.text)


class ToolCard(Block):
    """工具调用卡：左侧状态色条 + 工具名（等宽）+ 参数/耗时 + 结果摘要。"""

    TONE = {"ok": "ok", "err": "bad", "run": "warn"}

    def __init__(self, master, name: str, detail: str, tone: str = "ok",
                 result: str = "", expanded: bool = False, compact: bool = False):
        self.name, self.detail, self.tone, self.result = name, detail, tone, result
        self.compact = compact
        h = 38 if compact else 46 + (text_height(result, 8, 560) + 8 if (result and expanded) else 0)
        super().__init__(master, h)
        self.setFixedHeight(h)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(8 if not self.compact else 4, 4, -8 if not self.compact else -4, -5)
        hi = skeuo_kit.resolve(PAL["tool_hi"])
        lo = skeuo_kit.resolve(PAL["tool_lo"])
        edge = skeuo_kit.resolve(PAL["tool_edge"])
        skeuo_kit.draw_contact_shadow(p, r, 10, depth=0.6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(skeuo_kit.vgrad(r, hi, lo))
        p.drawRoundedRect(r, 10, 10)
        bar = skeuo_kit.resolve(PAL[self.TONE.get(self.tone, "ok")])
        p.setBrush(skeuo_kit.vgrad(r, skeuo_kit.lighten(bar, 0.3), skeuo_kit.darken(bar, 0.3)))
        p.drawRoundedRect(QRectF(r.left() + 1, r.top() + 1, 4.5, r.height() - 2), 2.2, 2.2)
        p.setPen(QtGui.QPen(skeuo_kit.alpha(hi, 170), 1.1))
        p.drawLine(QtCore.QPointF(r.left() + 10, r.top() + 0.8),
                   QtCore.QPointF(r.right() - 10, r.top() + 0.8))
        p.setPen(QtGui.QPen(edge, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)
        # 状态灯
        lamp = QRectF(r.right() - 18, r.center().y() - 4.5, 9, 9)
        p.setPen(QtGui.QPen(skeuo_kit.darken(bar, 0.45), 1.0))
        p.setBrush(skeuo_kit.vgrad(lamp, skeuo_kit.lighten(bar, 0.5), bar))
        p.drawEllipse(lamp)
        if self.compact:
            # 窄栏：单行 name + 灰字 detail（detail 用省略号裁切，不溢出）
            f = QtGui.QFont(MONO_FONT, 8, QtGui.QFont.Weight.DemiBold)
            p.setFont(f)
            p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["text"])))
            name_w = QtGui.QFontMetrics(f).horizontalAdvance(self.name) + 6
            p.drawText(QRectF(r.left() + 13, r.top(), name_w, r.height()),
                       Qt.AlignLeft | Qt.AlignVCenter, self.name)
            f2 = QtGui.QFont(MONO_FONT, 7)
            p.setFont(f2)
            p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["muted"])))
            avail = r.width() - name_w - 34
            txt = QtGui.QFontMetrics(f2).elidedText(self.detail, Qt.TextElideMode.ElideRight,
                                                    int(max(20, avail)))
            p.drawText(QRectF(r.left() + 13 + name_w, r.top(), max(20, avail), r.height()),
                       Qt.AlignLeft | Qt.AlignVCenter, txt)
            return
        p.setFont(QtGui.QFont(MONO_FONT, 9, QtGui.QFont.Weight.DemiBold))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["text"])))
        p.drawText(QRectF(r.left() + 14, r.top() + 6, r.width() - 46, 18),
                   Qt.AlignLeft | Qt.AlignVCenter, self.name)
        p.setFont(QtGui.QFont(MONO_FONT, 8))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["muted"])))
        p.drawText(QRectF(r.left() + 14, r.top() + 24, r.width() - 30, 16),
                   Qt.AlignLeft | Qt.AlignVCenter, self.detail)
        if self.result:
            p.setFont(QtGui.QFont(MONO_FONT, 8))
            p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["muted_dim"])))
            p.drawText(r.adjusted(14, 42, -14, -6),
                       Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self.result)


class AskCard(Block):
    """内核的提问/权限请求：拟物化的"需要你决定"卡片。

    按钮在 __init__ 里建一次、resizeEvent 里排位 —— **不能在 paintEvent 里建控件**，
    否则每次重绘都会多出一排按钮。
    """

    answered = Signal(str)

    def __init__(self, master, question: str, options: list[str],
                 kind: str = "question"):
        self.question, self.options, self.kind = question, options, kind
        self._w = 620
        self._qh = max(20, text_height(question, 10, self._w - 34))
        h = 34 + self._qh + 46
        super().__init__(master, h)
        self.setFixedHeight(max(96, h))
        self._btns: list[CButton] = []
        for i, opt in enumerate(options):
            btn = CButton(master=self, text=opt, width=76 + 7 * len(opt), height=26,
                          font_family=FONT, font_size=9,
                          background_color=PAL["accent"] if i == 0 else PAL["btn"],
                          text_color=PAL["on_accent"] if i == 0 else PAL["text"],
                          command=lambda o=opt: self.answered.emit(o))
            self._btns.append(btn)

    def resizeEvent(self, e):
        r = QRectF(self.rect()).adjusted(8, 4, -8, -6)
        x = int(r.left() + 14)
        y = int(r.top() + 30 + self._qh + 8)
        for b in self._btns:
            b.move(x, y)
            x += b.width() + 14
        super().resizeEvent(e)

    def _change_theme(self):
        for b in getattr(self, "_btns", []):
            try:
                b._change_theme()
            except Exception:                                        # noqa: BLE001
                pass
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(8, 4, -8, -6)
        base = skeuo_kit.resolve(PAL["node"])
        skeuo_kit.draw_contact_shadow(p, r, 12, depth=1.0)
        skeuo_kit.draw_raised(p, r, base, 12)
        # 顶部一条 3px 的"待处理"色带
        p.setPen(Qt.PenStyle.NoPen)
        warn = skeuo_kit.resolve(PAL["warn"])
        p.setBrush(skeuo_kit.vgrad(r, skeuo_kit.lighten(warn, 0.35), warn))
        p.drawRoundedRect(QRectF(r.left() + 1, r.top() + 1, r.width() - 2, 3.4), 1.7, 1.7)
        p.setFont(QtGui.QFont(FONT, 8, QtGui.QFont.Weight.Bold))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["warn"])))
        p.drawText(QRectF(r.left() + 14, r.top() + 8, r.width() - 28, 16),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   "需要你决定 · %s" % ("权限" if self.kind == "permission" else "提问"))
        p.setFont(QtGui.QFont(FONT, 10))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["title_text"])))
        p.drawText(QRectF(r.left() + 14, r.top() + 28, r.width() - 28, self._qh),
                   Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self.question)


class Composer(QWidget):
    """输入区：多行输入（凹槽）+ 发送按钮 + 快捷键提示。"""

    send = Signal(str)

    def __init__(self, master):
        super().__init__(master)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(112)
        self.edit = CTextEdit(master=self, width=560, height=64, font_family=FONT,
                              font_size=10, placeholder_text="给 opencode 下达指令…（Ctrl+Enter 发送）")
        self.btn = CButton(master=self, text="发送 ⏎", width=104, height=32, font_family=FONT,
                           font_size=10, background_color=PAL["accent"],
                           text_color=PAL["on_accent"], command=self._fire)
        self.hint = CLabel(master=self, text="Enter 换行 · Ctrl+Enter 发送 · / 呼出命令",
                           font_family=FONT, font_size=8, text_color=PAL["muted_dim"])

    def _fire(self):
        text = self.edit.text_edit().toPlainText().strip()
        if text:
            self.send.emit(text)
            self.edit.text_edit().clear()

    def _change_theme(self):
        self.update()

    def resizeEvent(self, e):
        w, h = self.width(), self.height()
        self.edit.setGeometry(0, 0, w - 116, 72)
        self.btn.setGeometry(w - 108, 34, 104, 32)
        self.hint.setGeometry(4, 78, w - 124, 18)
        super().resizeEvent(e)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        # 凹槽只包住"输入 + 发送"，提示语落在凹槽外面的底衬上
        r = QRectF(self.rect()).adjusted(4, 2, -4, -32)
        skeuo_kit.draw_inset(p, r, skeuo_kit.resolve(PAL["surface2"]), 12)


class Sidebar(QWidget):
    """左栏：品牌 / 内核状态 / 项目 / 会话列表 / 模型。"""

    new_session = Signal()
    pick_session = Signal(str)
    model_changed = Signal(str)

    def __init__(self, master, sessions: list[tuple[str, str]], models: list[str],
                 current: str):
        super().__init__(master)
        self.setFixedWidth(272)
        self._cards: list[SessionItem] = []
        self.sessions = sessions
        self._build(models, current)

    def _build(self, models, current):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 12, 10, 10)
        lay.setSpacing(8)
        brand = CLabel(master=self, text="opencode", font_family=MONO_FONT, font_size=15,
                       font_style="bold", text_color=PAL["title_text"])
        sub = CLabel(master=self, text="嵌入本工作台的内核 · 会话界面", font_family=FONT,
                     font_size=8, text_color=PAL["muted"])
        lay.addWidget(brand)
        lay.addWidget(sub)
        self.status = StatusChip(self, "内核已连接 · 1.18.35", "ok")
        lay.addWidget(self.status)
        lay.addWidget(SectionTitle(self, "项目 / 会话"))
        for title, subtitle in self.sessions:
            item = SessionItem(self, title, subtitle, active=(title == self.sessions[0][0]))
            item.clicked.connect(self._on_pick)
            self._cards.append(item)
            lay.addWidget(item)
        btn = CButton(master=self, text="＋ 新会话", width=232, height=30, font_family=FONT,
                      font_size=9, background_color=PAL["btn"], text_color=PAL["text"],
                      command=self.new_session.emit)
        lay.addWidget(btn)
        lay.addStretch(1)
        lay.addWidget(SectionTitle(self, "模型"))
        combo = CComboBox(master=self, width=232, height=30, font_family=FONT, font_size=9,
                          values=models, current_value=current)
        combo.combo_box().currentTextChanged.connect(self.model_changed.emit)
        lay.addWidget(combo)
        self.footer = CLabel(master=self, text="内核 home：…\\opencode\\  ·  隔离运行",
                             font_family=FONT, font_size=7, text_color=PAL["muted_dim"])
        lay.addWidget(self.footer)

    def _on_pick(self, title: str):
        for c in self._cards:
            c.set_active(c.title == title)
        self.pick_session.emit(title)

    def _change_theme(self):
        self.update()


class StatusChip(QWidget):
    """状态胶囊：左侧圆点 + 文本（凸起小胶囊）。"""

    def __init__(self, master, text: str, tone: str = "ok"):
        super().__init__(master)
        self.text, self.tone = text, tone
        self.setFixedHeight(26)

    def set_status(self, text: str, tone: str = "ok"):
        self.text, self.tone = text, tone
        self.update()

    def _change_theme(self):
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        skeuo_kit.draw_raised(p, r, skeuo_kit.resolve(PAL["btn"]), 12)
        col = skeuo_kit.resolve(PAL[self.tone])
        dot = QRectF(r.left() + 9, r.center().y() - 4.5, 9, 9)
        p.setPen(QtGui.QPen(skeuo_kit.darken(col, 0.45), 1.0))
        p.setBrush(skeuo_kit.vgrad(dot, skeuo_kit.lighten(col, 0.55), col))
        p.drawEllipse(dot)
        p.setFont(QtGui.QFont(FONT, 8, QtGui.QFont.Weight.DemiBold))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["text"])))
        p.drawText(r.adjusted(24, 0, -10, 0), Qt.AlignLeft | Qt.AlignVCenter, self.text)


class SectionTitle(QWidget):
    """小节标题：左对齐小字 + 一条凹槽分隔线。"""

    def __init__(self, master, text: str):
        super().__init__(master)
        self.text = text
        self.setFixedHeight(24)

    def _change_theme(self):
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setFont(QtGui.QFont(FONT, 8, QtGui.QFont.Weight.Bold))
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["muted"])))
        p.drawText(self.rect().adjusted(2, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, self.text)
        fm = QtGui.QFontMetrics(QtGui.QFont(FONT, 8, QtGui.QFont.Weight.Bold))
        x = 8 + fm.horizontalAdvance(self.text)
        y = self.height() / 2
        p.setPen(QtGui.QPen(skeuo_kit.resolve(PAL["groove_hi"]), 1.0))
        p.drawLine(QtCore.QPointF(x, y), QtCore.QPointF(self.width() - 2, y))


class ContextPanel(QWidget):
    """右栏：上下文用量 + 最近工具 + 内核信息。"""

    def __init__(self, master, tools: list[tuple[str, str, str]]):
        super().__init__(master)
        self.setFixedWidth(236)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 12, 10, 10)
        lay.setSpacing(8)
        lay.addWidget(SectionTitle(self, "上下文用量"))
        self.bar = ProgressBar(self, width=200, height=10)
        self.bar.set_value(0.42)
        lay.addWidget(self.bar)
        self.usage = CLabel(master=self, text="84.2K / 200K tokens · 42%", font_family=FONT,
                            font_size=8, text_color=PAL["muted"])
        lay.addWidget(self.usage)
        lay.addWidget(SectionTitle(self, "本次会话工具"))
        for name, detail, tone in tools:
            lay.addWidget(ToolCard(self, name, detail, tone, compact=True))
        lay.addStretch(1)
        lay.addWidget(SectionTitle(self, "内核"))
        for k, v in (("实例", "隔离 home"), ("MCP", "pclradiomics（已连）"),
                     ("端口", "127.0.0.1:random"), ("模型", "deepseek-flash")):
            row = CLabel(master=self, text="%s：%s" % (k, v), font_family=MONO_FONT,
                         font_size=8, text_color=PAL["muted_dim"])
            lay.addWidget(row)

    def _change_theme(self):
        self.update()


# ===========================================================================
# 主窗口
# ===========================================================================
class SessionWindow(QWidget):
    """opencode 会话窗口。_change_theme 会把新配色广播给所有自绘构件。"""

    def __init__(self, demo: bool = True):
        super().__init__()
        self.setWindowTitle("opencode · 会话")
        self.setMinimumSize(1120, 720)
        self.resize(1440, 900)
        self._demo = demo
        self._driver = None
        self._client = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 10)
        root.setSpacing(10)

        header = QtWidgets.QWidget(self)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(2, 0, 2, 0)
        hl.setSpacing(10)
        self.title = CLabel(master=header, text="demo_胰腺囊性病变 · 阶段 03 改写稿收敛",
                            font_family=FONT, font_size=12, font_style="bold",
                            text_color=PAL["title_text"])
        hl.addWidget(self.title)
        hl.addStretch(1)
        self.pill = StatusChip(header, "空闲", "ok")
        self.pill.setFixedWidth(120)
        hl.addWidget(self.pill)
        for text, tone in (("中断", "btn"), ("附着 TUI", "btn"), ("深色", "btn")):
            b = CButton(master=header, text=text, width=92, height=30, font_family=FONT,
                        font_size=9, background_color=PAL[tone], text_color=PAL["text"],
                        command=(self.toggle_mode if text == "深色" else
                                 (self._interrupt if text == "中断" else self._attach)))
            hl.addWidget(b)
        root.addWidget(header)

        body = QtWidgets.QHBoxLayout()
        body.setSpacing(12)
        self.side = Sidebar(self, DEMO_SESSIONS, DEMO_MODELS, "deepseek-flash")
        self.side.pick_session.connect(self._on_session)
        self.side.new_session.connect(lambda: self._append(Bubble(
            self.transcript_host(), "system", "已创建新会话（演示模式不连内核）。")))
        body.addWidget(self.side)

        center = QtWidgets.QVBoxLayout()
        center.setSpacing(8)
        self.scroll = WorkScroll(self)
        self.scroll.setWidgetResizable(True)
        self._host = QtWidgets.QWidget()
        self._host_lay = QVBoxLayout(self._host)
        self._host_lay.setContentsMargins(2, 2, 2, 2)
        self._host_lay.setSpacing(8)
        self._host_lay.addStretch(1)
        self.scroll.setWidget(self._host)
        center.addWidget(self.scroll, 1)
        self.composer = Composer(self)
        self.composer.send.connect(self._on_send)
        center.addWidget(self.composer)
        body.addLayout(center, 1)

        self.ctx = ContextPanel(self, DEMO_TOOLS)
        body.addWidget(self.ctx)
        root.addLayout(body, 1)

        self.credit = CreditBar(self)
        root.addWidget(self.credit)

        if demo:
            self.load_demo()

    # -- 装配 ---------------------------------------------------------------
    def transcript_host(self) -> QWidget:
        return self._host

    def _append(self, w: Block):
        w.setParent(self._host)
        self._host_lay.insertWidget(self._host_lay.count() - 1, w)
        return w

    def load_demo(self):
        self._append(Bubble(self._host, "system",
                            "内核已连接：opencode 1.18.35（隔离 home）· 本项目已注册为 MCP 服务 "
                            "pclradiomics，21 个领域工具可用。", "12:47:03"))
        self._append(Bubble(self._host, "user",
                            "把右侧设计文档里阶段 03「样本量与事件数」的改写稿再收敛一下："
                            "按 Riley 公式重算，并把外部验证的例数与事件数单列。", "12:47:20"))
        self._append(Reasoning(self._host,
                               "先确认口径：TRIPOD+AI 3-4 要求单列外部验证的例数与事件数；"
                               "Riley 公式需要预期 AUC、候选变量数与事件率三个输入……"
                               "文档里已有 AUC 0.85 / 15 个变量，事件率按既往 262 例中恶性 101 例推。",
                               6.4))
        self._append(ToolCard(self._host, "read  研究设计文档.md",
                              "1.2 KB · 12 ms · 阶段 03 段", "ok",
                              result="找到「训练集 262 例（恶性 101 例）」与「外部验证待定」两处。"))
        self._append(ToolCard(self._host, "bash  python omics_pipeline.py --check --stage 03",
                              "退出码 1 · 1.8 s", "err",
                              result="CLEAR 19-20 / METRICS #8-10 未通过：外部验证例数与事件数未单列。"))
        self._append(ToolCard(self._host, "edit  设计文档.md · 阶段 03",
                              "+312 −48 字符 · 已写回", "ok"))
        self._append(Bubble(self._host, "ai",
                            "已按 Riley 公式重算并单列：训练集 ≥ 240 例（事件 ≥ 90）、"
                            "外部验证 ≥ 100 例（事件 ≥ 40）。原稿「外部验证 ≥ 100 例」保留，"
                            "但把事件数独立成句，并注明组学分组独立于模型输出。"
                            "阶段 03 现满足 CLEAR 19-20 与 METRICS #8-10。", "12:48:41"))
        ask = AskCard(self._host, "外部验证队列的例数上限按哪个走？（影响统计功效与入组可行性）",
                      ["≥ 100 例", "≥ 150 例", "先按 100 例保守"], "question")
        ask.answered.connect(lambda o: self._append(
            Bubble(self._host, "system", "已回灌内核：%s" % o)))
        self._append(ask)
        perm = AskCard(self._host, "允许执行：python stat_tools.py --recalc --stage 03",
                       ["允许一次", "总是允许", "拒绝"], "permission")
        perm.answered.connect(lambda o: self._append(
            Bubble(self._host, "system", "权限回复：%s" % o)))
        self._append(perm)

    # -- 交互 ---------------------------------------------------------------
    def _on_session(self, title: str):
        self.title.label().setText(title)
        self._append(Bubble(self._host, "system", "已切换到会话：%s" % title))

    def _on_send(self, text: str):
        self._append(Bubble(self._host, "user", text,
                            time.strftime("%H:%M:%S")))
        if self._demo or self._driver is None:
            self._append(Bubble(self._host, "system",
                                "演示模式：未连接内核，指令未下发。（--live 模式会经 "
                                "kernel_driver.run_turn_async 发给内核）"))
            return
        self.pill.set_status("运行中", "accent")
        threading.Thread(target=self._run_turn, args=(text,), daemon=True).start()

    def _run_turn(self, text: str):
        """真连内核时：kernel_driver 的规范化事件 → 逐块渲染（回到 Qt 线程）。"""
        try:
            sid = getattr(self, "_session_id", None)
            self._driver.run_turn_async(
                sid, text,
                on_event=lambda ev: QtCore.QMetaObject.invokeMethod(
                    self, "_on_event", Qt.QueuedConnection,
                    QtCore.Q_ARG(object, ev)),
                on_done=lambda: QtCore.QMetaObject.invokeMethod(
                    self, "_on_done", Qt.QueuedConnection))
        except Exception as exc:                                     # noqa: BLE001
            self._append(Bubble(self._host, "system", "内核调用失败：%s" % exc))

    @QtCore.Slot(object)
    def _on_event(self, ev: dict):
        kind = ev.get("kind")
        if kind == "text":
            self._append(Bubble(self._host, "ai", ev.get("text", "")))
        elif kind in ("tool", "tool_ok", "tool_err"):
            self._append(ToolCard(self._host, str(ev.get("text", "tool")),
                                  str(ev.get("type", "")), 
                                  {"tool_ok": "ok", "tool_err": "err"}.get(kind, "run")))

    @QtCore.Slot()
    def _on_done(self):
        self.pill.set_status("空闲", "ok")

    def _interrupt(self):
        self._append(Bubble(self._host, "system", "已请求中断当前回合。"))
        if self._client and hasattr(self, "_session_id"):
            try:
                self._client.interrupt(self._session_id)
            except Exception:                                        # noqa: BLE001
                pass

    def _attach(self):
        self._append(Bubble(self._host, "system",
                            "附着 TUI：kernel_client.spawn_tui() 会在新终端里 "
                            "`opencode attach` 同一个隔离实例（不重写会话 UI 的旧路径仍然可用）。"))
        if self._client:
            try:
                self._client.spawn_tui(session_id=getattr(self, "_session_id", None))
            except Exception as exc:                                 # noqa: BLE001
                self._append(Bubble(self._host, "system", "附着失败：%s" % exc))

    def toggle_mode(self):
        mode = "light" if ModeManager.mode == "dark" else "dark"
        set_appearance_mode(mode)
        self.side._change_theme()
        self.ctx._change_theme()
        self._broadcast()

    def _broadcast(self):
        for w in self.findChildren(QWidget):
            fn = getattr(w, "_change_theme", None)
            if callable(fn) and w is not self:
                try:
                    fn()
                except Exception:                                    # noqa: BLE001
                    pass
        self.update()

    # -- 绘制 ---------------------------------------------------------------
    def _change_theme(self):
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        draw_backdrop(p, QRectF(self.rect()))

    # -- live 模式 ----------------------------------------------------------
    def connect_kernel(self, auto: bool = True):
        """尽力连上内嵌内核；失败只改状态，不打断界面。"""
        try:
            import kernel_client as kc
            import kernel_driver as kd
            exe = kc.opencode_exe()
            if not exe:
                self.side.status.set_status("未找到 opencode.exe", "bad")
                self._append(Bubble(self._host, "system",
                                    "未找到 opencode.exe：设 PCL_OPENCODE_EXE，或把二进制放到 "
                                    "<app_home>/opencode/opencode.exe。界面仍可浏览。"))
                return
            self._client = kc.KernelClient(exe=exe)
            if auto:
                self.side.status.set_status("启动内核…", "warn")
                st = self._client.ensure_running(timeout=180)
                sessions = self._client.sessions() or []
                self._session_id = sessions[0]["id"] if sessions else None
                if self._session_id is None:
                    got = self._client.new_session(title="opencode 会话窗口",
                                                   model="deepseek/deepseek-chat")
                    self._session_id = (got.get("data") or got).get("id")
                self._driver = kd.KernelDriver(self._client)
                self.side.status.set_status("内核已连接 · %s" % st.version, "ok")
                self._append(Bubble(self._host, "system",
                                    "已连上内核 %s（%s），会话 %s"
                                    % (st.version, st.url, self._session_id)))
        except Exception as exc:                                     # noqa: BLE001
            self.side.status.set_status("内核不可用", "bad")
            self._append(Bubble(self._host, "system", "连接内核失败：%s" % exc))


# ===========================================================================
# 演示数据
# ===========================================================================
DEMO_SESSIONS = [
    ("demo_胰腺囊性病变 · 阶段 03 改写稿收敛", "当前会话 · 12:48"),
    ("demo_胰腺囊性病变 · 伦理与数据治理", "已归档 · 阶段 02"),
    ("卵巢癌 · 影像组学外部验证", "已归档 · 阶段 05"),
    ("体模手稿测试 · 图表一致性", "已归档 · 手稿审阅"),
]
DEMO_MODELS = ["deepseek-flash", "deepseek-reasoner", "gpt-5.1-codex", "claude-sonnet-4.5",
               "qwen3-coder-plus"]
DEMO_TOOLS = [
    ("read", "研究设计文档.md · 12 ms", "ok"),
    ("bash", "omics_pipeline.py --check · exit 1", "err"),
    ("edit", "阶段 03 · +312 −48", "ok"),
]


def shot(mode: str) -> str:
    set_appearance_mode(mode)
    app = QApplication.instance() or QApplication(sys.argv)
    skeuo_kit.install(ui_kit)
    app.setStyleSheet(skeuo_kit.scroll_qss())
    app.setWindowIcon(QtGui.QIcon(_resource("logo_icon.ico")))
    win = SessionWindow(demo=True)
    win.show()
    app.processEvents()
    win._broadcast()
    win.repaint()
    for _ in range(5):
        app.processEvents()
    out = _out_dir()
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "opencode_gui_%s.png" % mode)
    win.grab().save(path)
    win.close()
    return path


def main(argv: list[str]) -> int:
    set_color_theme(_resource("theme_skeuo.json"))
    if "--shot" in argv:
        for m in (["dark", "light"] if "--mode" not in argv
                  else [argv[argv.index("--mode") + 1]]):
            print("saved:", shot(m))
        return 0
    set_appearance_mode("dark")
    app = QApplication(argv)
    skeuo_kit.install(ui_kit)
    app.setStyleSheet(skeuo_kit.scroll_qss())
    app.setWindowIcon(QtGui.QIcon(_resource("logo_icon.ico")))
    live = "--live" in argv
    win = SessionWindow(demo=not live)
    win.show()
    if live:
        threading.Thread(target=win.connect_kernel, daemon=True).start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
