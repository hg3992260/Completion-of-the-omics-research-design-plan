# -*- coding: utf-8 -*-
"""组学研究设计工作台（主界面）

流程：贴入初步实验设计 → agent 速读 → 按十阶段标准流程逐阶段「先追问 → 你回答 → 再给改写稿」
→ 采纳后写入右侧设计文档 → 最后汇总成完整研究设计草案。

LLM 服务：DeepSeek（OpenAI 兼容），默认复用 agent 自身凭据，可在「设置」中切换任意兼容端点。

运行：  python design_studio.py
自检：  python design_studio.py --demo --shot   （离线假对话 + 截图，不调用网络）
"""

from __future__ import annotations

import json
import os
import re
import sys
import subprocess
import time

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QSizePolicy, QSpacerItem,
                               QVBoxLayout, QWidget)

from PyCt6 import (CMainWindow, CTopLevel, CFrame, CLabel, CButton, CLineEdit,
                   CTextEdit, CComboBox, set_appearance_mode, set_color_theme, ModeManager)

from design_agent import (Project, DesignAgent, parse_sections, pick,
                          parse_questions, parse_checklist, q_text, SYSTEM_PROMPT,
                          parse_convergence)
from llm_client import LLMClient, load_config, save_config, mask
from stages_data import STAGES
import shape_data as shape
import stat_data as stat
import scope_core
import coupling
from shape_data import SHAPE
from stat_data import STAGES as STAT_STAGES
from ui_kit import (PAL, C, UI_FONT, MONO_FONT, mk_label, clear_layout,
                    ProgressBar, TranscriptView, stream_format, status_key,
                    WorkScroll, fit_height, text_height, BusyIndicator, CreditBar,
                    ThinkingButton, screen_size,
                    Card, FlowStepper, draw_backdrop, CARD_PAD, install_button_skin,
                    pair_brush, CheckBox3D, RefitLabel)

HERE = os.path.dirname(os.path.abspath(__file__))
from app_paths import resource_path, data_path

THEME_PATH = resource_path("theme_tech.json")
ICON_PATH = resource_path("logo_mark.png" if sys.platform == "darwin"
                              else "logo_icon.ico")   # macOS 用 PNG，Windows 用多尺寸 ICO             # 窗口 / 任务栏图标
BADGE_PATH = resource_path("logo_badge.png")           # 标题旁的小角标
BANNER_PATH = resource_path("logo_banner.png")         # 启动画面
SHOW_SPLASH = True                                     # 需要时改 False 关闭启动画面

PHASE_LABEL = {"raw": "等待输入", "kickoff": "速读中", "ask": "追问中", "answer": "等待回答",
               "rewrite": "改写中", "draft": "等待采纳", "idle": "空闲", "final": "汇总中"}
STATUS_LABEL = {"todo": "未开始", "asked": "已追问", "drafted": "待采纳", "done": "已收录",
                "doing": "进行中"}


# --------------------------------------------------------------------------- 后台线程
class LLMThread(QtCore.QThread):
    delta = Signal(str, str)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, client: LLMClient, messages: list, stream: bool = True, parent=None,
                 max_tokens: int | None = None, reason: bool = False):
        super().__init__(parent)
        self.client, self.messages, self.stream = client, messages, stream
        self.max_tokens = max_tokens
        self.reason = reason

    def run(self):
        try:
            out = self.client.chat(self.messages, stream=self.stream,
                                   on_delta=(lambda p, k: self.delta.emit(p, k))
                                   if self.stream else None,
                                   max_tokens=self.max_tokens, reason=self.reason)
            self.finished_ok.emit(out)
        except Exception as e:                                     # noqa: BLE001
            self.failed.emit(str(e))


class ModelListThread(QtCore.QThread):
    done = Signal(list)

    def __init__(self, client: LLMClient, parent=None):
        super().__init__(parent)
        self.client = client

    def run(self):
        try:
            self.done.emit(self.client.list_models())
        except Exception:                                          # noqa: BLE001
            self.done.emit([])


# --------------------------------------------------------------------------- 步骤栏
class StageRail(QWidget):
    stageClicked = Signal(int)

    NODE_H = 50
    GAP = 10
    PAD = 10

    def __init__(self, master, stages):
        super().__init__(master)
        self.stages = stages
        self.states = {}
        self.current = 0
        self.hover = -1
        self.setMouseTracking(True)
        h = self.PAD * 2 + len(stages) * self.NODE_H + (len(stages) - 1) * self.GAP
        self.setFixedHeight(h)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _change_theme(self):
        self.update()

    def set_states(self, states: dict, current: int):
        self.states, self.current = states, current
        self.update()

    def _rect(self, i) -> QRectF:
        return QRectF(self.PAD, self.PAD + i * (self.NODE_H + self.GAP),
                      self.width() - self.PAD * 2, self.NODE_H)

    def _index_at(self, pos) -> int:
        for i in range(len(self.stages)):
            if self._rect(i).contains(pos):
                return i
        return -1

    def mouseMoveEvent(self, e):
        i = self._index_at(e.position())
        if i != self.hover:
            self.hover = i
            self.setCursor(Qt.CursorShape.PointingHandCursor if i >= 0
                           else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self.hover = -1
        self.update()

    def mousePressEvent(self, e):
        i = self._index_at(e.position())
        if i >= 0:
            self.stageClicked.emit(i)

    def paintEvent(self, event):
        """步骤条三维化：凹槽轨道 + 金属旋钮 + 进度填充，一眼看清流程先后与位置。"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        f_t = QtGui.QFont(UI_FONT, 10)
        f_t.setBold(True)
        f_s = QtGui.QFont(UI_FONT, 8)
        f_n = QtGui.QFont(MONO_FONT, 9)
        f_n.setBold(True)
        n = len(self.stages)
        # ---- 轨道凹槽：贯穿所有旋钮的一根槽，已完成的段落被强调色填充 ----
        track_x = self.PAD + 20
        y0 = self._rect(0).center().y()
        y1 = self._rect(n - 1).center().y()
        def groove(x, ya, yb, filled):
            p.setPen(QtGui.QPen(QtGui.QColor(C("groove_hi")), 5.0,
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QtCore.QPointF(x, ya), QtCore.QPointF(x, yb))
            p.setPen(QtGui.QPen(QtGui.QColor(C("groove_lo")), 3.0,
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QtCore.QPointF(x, ya), QtCore.QPointF(x, yb))
            if filled > 0:
                p.setPen(QtGui.QPen(QtGui.QColor(C("accent")), 3.0,
                                    Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(QtCore.QPointF(x, ya), QtCore.QPointF(x, ya + filled))
        groove(track_x, y0, y1, 0)
        # 已走过的段落（到当前旋钮中心）填强调色 → 流程推进可见
        cur_center = self._rect(self.current).center().y()
        if self.current > 0:
            groove(track_x, y0, cur_center, cur_center - y0)
        for i, st in enumerate(self.stages):
            r = self._rect(i)
            state = self.states.get(st["id"], "todo")
            active = (i == self.current)
            hovered = (i == self.hover)
            done = state in ("done", "drafted", "asked")
            cx, cy = r.left() + 20, r.center().y()
            # ---- 卡片面：抬起（投影在自身矩形内） ----
            p.setPen(Qt.PenStyle.NoPen)
            if active or hovered:
                col = QtGui.QColor(C("shadow"))
                col.setAlpha(58 if active else 30)
                p.setBrush(col)
                p.drawRoundedRect(r.adjusted(1, 3, -1, 5), 10, 10)
            brush = pair_brush("surf_hi", "surf_lo", r) if (active or hovered) else \
                    pair_brush("knob_hi", "knob_lo", r)
            p.setBrush(brush)
            p.drawRoundedRect(r, 10, 10)
            # 倒角：上亮下暗（抬起）／上暗下亮（未到 = 内嵌感）
            if active or hovered:
                p.setPen(QtGui.QPen(QtGui.QColor(C("bevel_hi")), 1.0))
                p.drawLine(QtCore.QPointF(r.left() + 8, r.top() + 1.0),
                           QtCore.QPointF(r.right() - 8, r.top() + 1.0))
                p.setPen(QtGui.QPen(QtGui.QColor(C("bevel_lo")), 1.0))
                p.drawLine(QtCore.QPointF(r.left() + 8, r.bottom() - 1.0),
                           QtCore.QPointF(r.right() - 8, r.bottom() - 1.0))
            else:
                p.setPen(QtGui.QPen(QtGui.QColor(C("groove_hi")), 1.0))
                p.drawLine(QtCore.QPointF(r.left() + 8, r.top() + 1.0),
                           QtCore.QPointF(r.right() - 8, r.top() + 1.0))
                p.setPen(QtGui.QPen(QtGui.QColor(C("groove_lo")), 1.0))
                p.drawLine(QtCore.QPointF(r.left() + 8, r.bottom() - 1.0),
                           QtCore.QPointF(r.right() - 8, r.bottom() - 1.0))
            pen = QtGui.QPen(QtGui.QColor(C("accent") if active else
                                          (C("accent_dim") if hovered else C("border"))))
            pen.setWidthF(1.6 if active else 1.0)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)
            # ---- 金属旋钮 ----
            kr = QRectF(cx - 11, cy - 11, 22, 22)
            p.setPen(Qt.PenStyle.NoPen)
            if active or done:
                sh = QtGui.QColor(C("shadow"))
                sh.setAlpha(60)
                p.setBrush(sh)
                p.drawEllipse(kr.adjusted(0.5, 2.0, -0.5, 2.5))
            if state == "done":
                face = pair_brush("ok_hi", "ok_lo", kr)
            elif active:
                face = pair_brush("accent_hi", "accent_lo", kr)
            elif state in ("drafted", "asked"):
                face = pair_brush("warn_hi", "warn_lo", kr)
            else:
                face = pair_brush("knob_hi", "knob_lo", kr)
            p.setBrush(face)
            p.drawEllipse(kr)
            # 旋钮上缘高光（金属感）
            hl = QtGui.QColor("#FFFFFF")
            hl.setAlpha(120 if ModeManager.mode != "dark" else 80)
            p.setBrush(hl)
            p.drawEllipse(QRectF(kr.left() + 3.5, kr.top() + 2.0, kr.width() - 7, 5.0))
            p.setPen(QtGui.QPen(QtGui.QColor(C("bevel_lo")), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(kr.adjusted(0.5, 0.5, -0.5, -0.5))
            printed = "✓" if state == "done" else f"{st['id']:02d}"
            p.setPen(QtGui.QPen(QtGui.QColor(
                "#FFFFFF" if (active or state == "done") else C("muted_dim"))))
            p.setFont(f_n)
            p.drawText(QRectF(cx - 11, cy - 9.5, 22, 19), Qt.AlignCenter, printed)
            # ---- 文本 ----
            tx = cx + 17
            p.setPen(QtGui.QPen(QtGui.QColor(C("text"))))
            p.setFont(f_t)
            p.drawText(QRectF(tx, cy - 20, r.width() - (tx - r.left()) - 8, 20),
                       Qt.AlignLeft | Qt.AlignVCenter, st["title"])
            p.setPen(QtGui.QPen(QtGui.QColor(C(status_key(state)))))
            p.setFont(f_s)
            p.drawText(QRectF(tx, cy + 1, r.width() - (tx - r.left()) - 8, 18),
                       Qt.AlignLeft | Qt.AlignVCenter,
                       f"{STATUS_LABEL.get(state, state)} · {st['spec']}")


# --------------------------------------------------------------------------- SCI Shape

class CheckRow(QWidget):
    """自检项一行：勾选框 + 可换行文本；点击整行也可切换。"""
    toggled = Signal(int, bool)

    def __init__(self, master, idx: int, text: str, checked: bool, width_px: int = 320):
        super().__init__(master)
        self.idx = idx
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(8)
        self.box = CheckBox3D(self, checked)
        self.box.setFixedWidth(18)
        self.box.toggled.connect(lambda on: self.toggled.emit(self.idx, on))
        lay.addWidget(self.box, 0, Qt.AlignTop)
        self.lbl = mk_label(self, text, size=9, width_px=width_px, wrap=True,
                            color=PAL["text"])
        lay.addWidget(self.lbl, 1)
        self._style()

    def _style(self):
        """三维勾选框：凹陷槽 + 选中时的渐变与对勾。"""
        self.box._change_theme()

    def set_checked(self, on: bool):
        self.box.blockSignals(True)
        self.box.setChecked(bool(on))
        self.box.blockSignals(False)

    def is_checked(self) -> bool:
        return self.box.isChecked()

    def mousePressEvent(self, event):
        self.box.setChecked(not self.box.isChecked())      # 触发 stateChanged → toggled
        event.accept()

    def _change_theme(self):
        self._style()


class ScopePage:
    """通用「scope 环节 + 本稿自评」三栏页：Statistic 与 SCI Shape 共用同一模板。

    子类只需实现 head_text / goal_text / render_detail / extra_text 四个内容钩子，
    布局、步骤条、自检勾选、完成度与持久化全部在这里统一处理。
    """

    def __init__(self, win, *, store_key: str, data: list, rail_title: str,
                 side_title: str, unit: str):
        self.win = win
        self.store_key = store_key
        self.data = data
        self.unit = unit
        self.cur = 0

        body = QWidget(win)
        self.body = body
        blay = QHBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        blay.setSpacing(14)

        # 左栏：环节步骤条（复用 StageRail）
        left = Card(win, margin=(14, 14, 14, 14), spacing=10)
        self.left = left
        left.setFixedWidth(320 + 2 * CARD_PAD)      # 外形尺寸与原先的板面一致
        ll = left.layout()
        ll.addWidget(mk_label(left, rail_title, size=12, bold=True,
                              color=PAL["accent"], width_px=280))
        self.scroll = WorkScroll(left)
        self.rail = StageRail(self.scroll, data)
        self.rail.stageClicked.connect(self.pick)
        self.scroll.setWidget(self.rail)
        self.scroll.setMinimumHeight(180)
        ll.addWidget(self.scroll, 1)
        self.left_status = mk_label(left, "", size=9, width_px=280, color=PAL["muted"])
        ll.addWidget(self.left_status)
        # 流程导航：上一环节 / 下一环节（显式体现先后）
        nav = QWidget(left)
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(8)
        self.btn_prev = CButton(master=nav, text="◀ 上一环节", width=124, height=30,
                                font_family=UI_FONT, font_size=9,
                                command=lambda: self.step_by(-1),
                                background_color=PAL["btn"], text_color=PAL["text"],
                                hover_color=PAL["btn_hover"], border_color=PAL["border"])
        self.btn_next = CButton(master=nav, text="下一环节 ▶", width=124, height=30,
                                font_family=UI_FONT, font_size=9,
                                command=lambda: self.step_by(1),
                                background_color=PAL["accent"], text_color=PAL["on_accent"],
                                hover_color=PAL["accent_hover"])
        self.btn_prev.setFixedWidth(124)          # PyCt6 会按内边距加宽，这里锁死防重叠
        self.btn_next.setFixedWidth(124)
        nl.addWidget(self.btn_prev)
        nl.addWidget(self.btn_next)
        ll.addWidget(nav)
        ll.addWidget(CButton(master=left, text="返回工作台", width=280, height=30,
                             font_family=UI_FONT, font_size=9, command=win.show_workspace,
                             background_color=PAL["btn"], text_color=PAL["text"],
                             hover_color=PAL["btn_hover"], border_color=PAL["border"]))
        blay.addWidget(left)

        # 中栏：所选环节的 scope 详情
        center = Card(win, margin=(18, 14, 18, 14), spacing=8)
        self.center = center
        cl = center.layout()
        head = QWidget(center)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        self.head = mk_label(head, "", size=15, bold=True, color=PAL["accent"],
                             width_px=330, wrap=False)
        hl.addWidget(self.head, 1)
        cl.addWidget(head)
        # 出处/单元信息独占一行：避免与标题在同一行互抢宽度而被挤没
        self.spec = mk_label(center, "", size=9, color=PAL["muted"], width_px=330,
                             wrap=False)
        cl.addWidget(self.spec)
        self.goal = mk_label(center, "", size=10, width_px=560, wrap=True,
                             color=PAL["text"], bg=PAL["surface2"], radius=8, min_h=44)
        cl.addWidget(self.goal)
        # 模式切换：结构内容 ⇄ 引导完善（引导式对话按内容补齐本环节）
        mode_row = QWidget(center)
        ml = QHBoxLayout(mode_row)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(8)
        self.btn_content = CButton(master=mode_row, text="结构内容", width=104, height=28,
                                   font_family=UI_FONT, font_size=9,
                                   command=lambda: self.set_mode("content"))
        self.btn_guide = CButton(master=mode_row, text="引导完善", width=104, height=28,
                                 font_family=UI_FONT, font_size=9,
                                 command=lambda: self.set_mode("guide"))
        self.btn_content.setFixedWidth(104)
        self.btn_guide.setFixedWidth(104)
        ml.addWidget(self.btn_content)
        ml.addWidget(self.btn_guide)
        ml.addStretch(1)
        self.guide_state = mk_label(mode_row, "", size=9, width_px=260, wrap=False,
                                    color=PAL["muted"])
        ml.addWidget(self.guide_state)
        cl.addWidget(mode_row)

        self.center_stack = QtWidgets.QStackedWidget(center)
        self.detail = WorkScroll(self.center_stack)
        self.detail_host = QWidget()
        self.detail_lay = QVBoxLayout(self.detail_host)
        self.detail_lay.setContentsMargins(2, 2, 6, 2)
        self.detail_lay.setSpacing(3)
        self.detail.setWidget(self.detail_host)
        self.center_stack.addWidget(self.detail)                 # 0 结构内容
        self.center_stack.addWidget(self._build_guide(self.center_stack))  # 1 引导完善
        cl.addWidget(self.center_stack, 1)
        self._mode = "content"
        blay.addWidget(center, 1)

        # 右栏：完成度与自检
        side = Card(win, margin=(16, 14, 16, 14), spacing=8)
        self.side = side
        side.setFixedWidth(384 + 2 * CARD_PAD)
        rl = side.layout()
        rl.addWidget(mk_label(side, side_title, size=12, bold=True,
                              color=PAL["accent"], width_px=340))
        self.prog = ProgressBar(side, width=344, height=8)
        rl.addWidget(self.prog)
        self.prog_lbl = mk_label(side, "", size=9, width_px=340, color=PAL["muted"])
        rl.addWidget(self.prog_lbl)
        self.guide_lbl = mk_label(side, "", size=9, width_px=340, color=PAL["muted"],
                                  bg=PAL["surface2"], radius=8, min_h=30)
        rl.addWidget(self.guide_lbl)
        self.extra_lbl = mk_label(side, "", size=9, width_px=340, color=PAL["muted"])
        rl.addWidget(self.extra_lbl)
        self.check_scroll = WorkScroll(side)
        self.check_host = QWidget()
        self.check_lay = QVBoxLayout(self.check_host)
        self.check_lay.setContentsMargins(0, 0, 4, 0)
        self.check_lay.setSpacing(2)
        self.check_scroll.setWidget(self.check_host)
        rl.addWidget(self.check_scroll, 1)
        row = QWidget(side)
        rwl = QHBoxLayout(row)
        rwl.setContentsMargins(0, 0, 0, 0)
        rwl.setSpacing(8)
        for text, on in (("全选", True), ("清空", False)):
            b = CButton(master=row, text=text, width=146, height=30,
                        font_family=UI_FONT, font_size=9,
                        command=(lambda o=on: self.bulk(o)),
                        background_color=PAL["btn"], text_color=PAL["text"],
                        hover_color=PAL["btn_hover"],
                        border_color=PAL["border"])
            b.setFixedWidth(146)
            rwl.addWidget(b)
        rl.addWidget(row)
        blay.addWidget(side)

    # ---------------------------------------------------------------- 数据与状态
    @property
    def store(self) -> dict:
        d = getattr(self.win.project, self.store_key, None)
        if d is None:
            d = {}
            setattr(self.win.project, self.store_key, d)
        return d

    def section(self) -> dict:
        return self.data[max(0, min(len(self.data) - 1, self.cur))]

    # ---------------------------------------------------------------- 交互
    def pick(self, idx: int):
        self.cur = idx
        self.refresh()

    def step_by(self, delta: int):
        """按流程顺序前后移动一个环节（显式体现先后）。"""
        self.pick(max(0, min(len(self.data) - 1, self.cur + delta)))

    def on_check(self, idx: int, on: bool):
        sec = self.section()
        scope_core.set_check(self.store, sec["key"], idx, on)
        self.win._flush_project()
        QtCore.QTimer.singleShot(0, self.refresh)   # 延后重建：信号来自将被销毁的行

    def bulk(self, on: bool):
        sec = self.section()
        scope_core.set_all(self.store, sec, on)
        self.win._flush_project()
        self.refresh()

    # ---------------------------------------------------------------- 渲染
    def _block_title(self, text: str, sub: str = ""):
        wrap = QWidget(self.detail_host)
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 10, 0, 2)
        wl.setSpacing(1)
        wl.addWidget(mk_label(wrap, text, size=11, bold=True, width_px=560,
                              wrap=False, color=PAL["accent"]))
        if sub:
            wl.addWidget(mk_label(wrap, sub, size=8, width_px=560, wrap=False,
                                  color=PAL["muted"]))
        return wrap

    def _line(self, text: str, color=None, bold: bool = False, size: int = 9):
        return mk_label(self.detail_host, text, size=size, bold=bold, width_px=560,
                        wrap=True, color=color or PAL["text"])

    def refresh(self):
        if not self.data:
            return
        self.cur = max(0, min(len(self.data) - 1, self.cur))
        sec = self.section()
        states = {s["id"]: scope_core.state(self.store, s) for s in self.data}
        self.rail.set_states(states, self.cur)

        done, doing, ticks = scope_core.overall(self.store, self.data)
        self.left_status.label().setText(
            f"已完成 {done}/{len(self.data)} {self.unit}　·　进行中 {doing}　·　"
            f"自检 {ticks}/{scope_core.total_checks(self.data)} 项")
        self.head.label().setText(self.head_text(sec))
        self.spec.label().setText(sec.get("spec", ""))
        self.goal.label().setText(self.goal_text(sec))
        # 流程导航按钮状态（首/末环节置灰）
        self.btn_prev.setEnabled(self.cur > 0)
        self.btn_next.setEnabled(self.cur < len(self.data) - 1)
        self.btn_next.button().setText(
            "下一环节 ▶" if self.cur < len(self.data) - 1 else "已到末环节")
        self.render_detail(sec)
        self._fill_checks(sec, states)
        self._style_mode_buttons()
        self.refresh_guide()
        self.refit_all()
        QtCore.QTimer.singleShot(0, self.refit_all)   # 布局稳定后再校一次

    def refit_all(self):
        """内容重建/窗口变化后，强制所有换行标签按实际宽度重算高度（防止文字被压）。"""
        for lbl in self.body.findChildren(RefitLabel):
            try:
                lbl.fit_now()
            except Exception:                                   # noqa: BLE001
                pass

    def _fill_checks(self, sec: dict, states: dict):
        lay, host = self.check_lay, self.check_host
        clear_layout(lay)
        got = scope_core.checked(self.store, sec["key"])
        for i, text in enumerate(sec["checks"]):
            row = CheckRow(host, i, text, bool(got.get(str(i))), width_px=298)
            row.toggled.connect(self.on_check)
            lay.addWidget(row)
        lay.addStretch(1)
        done, total = scope_core.progress(self.store, sec)
        self.prog.set_value(done / total if total else 0.0)
        # 进度条宽度跟随右栏实际内容宽度（避免在窄窗口下越出卡片）
        avail = max(180, self.side.width() - 2 * CARD_PAD - 32 - 6)
        if self.prog.width() != avail:
            self.prog.setFixedWidth(avail)
        st = states.get(sec["id"], "todo")
        self.prog_lbl.label().setText(
            f"本{self.unit}自检 {done}/{total} 项　·　状态："
            f"{scope_core.STATUS_LABEL.get(st, st)}")
        self.extra_lbl.label().setText(self.extra_text(sec))

    # ---------------------------------------------------------------- 引导式对话
    def _build_guide(self, parent) -> QWidget:
        """引导完善面板：对话流（流式）+ 追问回答 / 定稿工作区 + 操作按钮。"""
        page = QWidget(parent)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.guide_transcript = TranscriptView(page)
        self.guide_transcript.setMinimumHeight(110)
        lay.addWidget(self.guide_transcript, 1)

        self.guide_scroll = WorkScroll(page)
        self.guide_host = QWidget()
        self.guide_lay = QVBoxLayout(self.guide_host)
        self.guide_lay.setContentsMargins(2, 2, 6, 2)
        self.guide_lay.setSpacing(6)
        self.guide_scroll.setWidget(self.guide_host)
        self.guide_scroll.setMinimumHeight(190)
        lay.addWidget(self.guide_scroll, 2)

        row = QWidget(page)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        self.btn_guide_start = CButton(master=row, text="开始引导", width=112, height=32,
                                       font_family=UI_FONT, font_size=9,
                                       command=self.start_guide,
                                       background_color=PAL["accent"],
                                       text_color=PAL["on_accent"],
                                       hover_color=PAL["accent_hover"])
        self.btn_guide_submit = CButton(master=row, text="提交回答", width=112, height=32,
                                        font_family=UI_FONT, font_size=9,
                                        command=self.submit_guide_answers)
        self.btn_guide_regen = CButton(master=row, text="生成定稿", width=112, height=32,
                                       font_family=UI_FONT, font_size=9,
                                       command=self.run_guide_rewrite)
        self.btn_guide_accept = CButton(master=row, text="采纳并收录", width=124, height=32,
                                        font_family=UI_FONT, font_size=9,
                                        command=self.accept_guide_draft)
        for b in (self.btn_guide_start, self.btn_guide_submit, self.btn_guide_regen,
                  self.btn_guide_accept):
            b.setFixedWidth(112 if b is not self.btn_guide_accept else 124)
            rl.addWidget(b)
        rl.addStretch(1)
        lay.addWidget(row)
        self.guide_answer_rows = []
        self.guide_draft_box = None
        self._guide_busy = False
        return page

    def set_mode(self, mode: str):
        self._mode = mode
        if hasattr(self, "center_stack"):
            self.center_stack.setCurrentIndex(0 if mode == "content" else 1)
        self._style_mode_buttons()

    def _style_mode_buttons(self):
        on = getattr(self, "_mode", "content") == "guide"
        for btn, active in ((self.btn_content, not on), (self.btn_guide, on)):
            btn._background_color = PAL["accent"] if active else PAL["btn"]
            btn._text_color = PAL["on_accent"] if active else PAL["text"]
            btn._hover_color = PAL["accent_hover"] if active else PAL["btn_hover"]
            btn._change_theme()

    def node(self, sec: dict | None = None) -> dict:
        """取（并补齐）当前环节的引导状态。"""
        return scope_core.node(self.store, (sec or self.section())["key"])

    def start_guide(self):
        if self.win._busy():
            return
        sec = self.section()
        self.set_mode("guide")
        self._guide_busy = True
        self.refresh_guide()
        self.guide_transcript.add_rule()
        self.guide_transcript.add_header(f"{sec['title']}｜引导追问", "agent",
                                         time.strftime("%H:%M"))
        self.win._run(self.win.agent.scope_ask_messages(self.store_key, sec),
                      on_done=lambda out: self._after_guide_ask(sec, out),
                      view=self.guide_transcript)

    def _after_guide_ask(self, sec: dict, out: dict):
        node = self.node(sec)
        s = parse_sections(out["content"])
        node["assessment"] = pick(s, "现状评估")
        node["questions"] = parse_questions(pick(s, "必须澄清", "问题"))
        node["answers"] = ["" for _ in node["questions"]]
        node["status"] = "asked" if node["questions"] else "todo"
        node["model"] = out.get("model", "")
        node["updated"] = time.strftime("%H:%M")
        self._guide_busy = False
        self.win._flush_project()
        self.refresh()
        self.set_mode("guide")

    def submit_guide_answers(self):
        if self.win._busy() or not self.guide_answer_rows:
            return
        sec = self.section()
        node = self.node(sec)
        node["answers"] = [self.win._answer_text(e) for e in self.guide_answer_rows]
        self.guide_transcript.add_header("研究者回答", "user", time.strftime("%H:%M"))
        lines = [f"{i + 1}. {q_text(q)}\n　→ {a or '（未回答，按常规做法给建议值）'}"
                 for i, (q, a) in enumerate(zip(node["questions"], node["answers"]))]
        self.guide_transcript.add_text_block("\n".join(lines) + "\n")
        self.win._flush_project()
        self.run_guide_rewrite()

    def run_guide_rewrite(self):
        if self.win._busy():
            return
        sec = self.section()
        self._guide_busy = True
        self.refresh_guide()
        self.guide_transcript.add_header(f"{sec['title']}｜定稿", "agent",
                                         time.strftime("%H:%M"))
        self.win._run(self.win.agent.scope_rewrite_messages(self.store_key, sec),
                      on_done=lambda out: self._after_guide_rewrite(sec, out),
                      view=self.guide_transcript)

    def _after_guide_rewrite(self, sec: dict, out: dict):
        node = self.node(sec)
        s = parse_sections(out["content"])
        node["draft"] = pick(s, "定稿", "改写稿")
        node["risks"] = pick(s, "风险提示")
        node["next"] = pick(s, "下一步")
        node["checklist"] = pick(s, "检查表")
        node["status"] = "drafted" if node["draft"] else node["status"]
        node["updated"] = time.strftime("%H:%M")
        self._guide_busy = False
        self.win._flush_project()
        self.refresh()
        self.set_mode("guide")
        # 定稿是工作区最后一块，生成后自动滚到底，省得用户再找
        if node.get("draft"):
            def _to_draft():
                bar = self.guide_scroll.verticalScrollBar()
                bar.setValue(bar.maximum())
            QtCore.QTimer.singleShot(80, _to_draft)

    def accept_guide_draft(self):
        sec = self.section()
        if self.guide_draft_box is None:
            self.win._toast("当前没有待采纳的定稿，请先「开始引导 → 提交回答」")
            return
        node = self.node(sec)
        node["final"] = self.guide_draft_box.text_edit().toPlainText().strip()
        node["status"] = "done"
        node["updated"] = time.strftime("%H:%M")
        # 按模型的检查表判断自动勾选自检项（编号优先，其次文本匹配）
        ticked = 0
        for idx, ok in scope_core.parse_suggestions(node.get("checklist", ""),
                                                    sec.get("checks", [])):
            scope_core.set_check(self.store, sec["key"], idx, ok)
            ticked += 1 if ok else 0
        self.win._flush_project()
        self.refresh()
        self.set_mode("guide")
        self.win._sync_flow({"stat": 1, "shape": 2}.get(self.store_key, 0))
        self.win._toast(f"已收录「{sec['title']}」定稿（{len(node['final'])} 字，"
                        f"自检勾选 {ticked} 项）")

    def refresh_guide(self):
        """重建引导工作区：现状评估 / 追问回答 / 定稿与检查表建议。"""
        if not hasattr(self, "guide_lay"):
            return
        sec = self.section()
        node = scope_core.node(self.store, sec["key"])
        st = scope_core.guide_status(self.store, sec["key"])
        words = len((node.get("final") or node.get("draft") or "").strip())
        busy = "　·　正在生成…" if getattr(self, "_guide_busy", False) else ""
        self.guide_state.label().setText(
            f"{scope_core.GUIDE_STATUS.get(st, st)}{f'　·　{words} 字' if words else ''}{busy}")
        self.guide_lbl.label().setText(
            f"引导：{scope_core.GUIDE_STATUS.get(st, st)}"
            + (f"　·　定稿 {len(node['final'])} 字" if node.get("final") else "")
            + (f"　·　有定稿待采纳" if (not node.get("final") and node.get("draft")) else ""))
        lay, host = self.guide_lay, self.guide_host
        clear_layout(lay)
        self.guide_answer_rows = []
        self.guide_draft_box = None
        if node.get("assessment"):
            lay.addWidget(mk_label(host, "现状评估", size=11, bold=True,
                                   color=PAL["accent"], width_px=560, wrap=False))
            lay.addWidget(mk_label(host, node["assessment"], size=9, width_px=560,
                                   wrap=True, color=PAL["text"], bg=PAL["surface2"],
                                   radius=8, min_h=36))
        if node.get("questions"):
            lay.addWidget(mk_label(host, "追问（回答后可生成定稿）", size=11, bold=True,
                                   color=PAL["accent"], width_px=560, wrap=False))
            for i, q in enumerate(node["questions"]):
                title = q.get("q") if isinstance(q, dict) else str(q)
                why = (q.get("why") if isinstance(q, dict) else "") or ""
                lay.addWidget(mk_label(host, f"Q{i + 1}　{title}", size=10, bold=True,
                                       width_px=560, wrap=True, color=PAL["text"]))
                if why:
                    lay.addWidget(mk_label(host, "为什么问：" + why, size=8, width_px=560,
                                           wrap=True, color=PAL["muted"]))
                box = CTextEdit(master=host, width=520, height=54, font_family=UI_FONT,
                                font_size=9,
                                text=(node["answers"][i] if i < len(node["answers"]) else ""))
                lay.addWidget(box)
                self.guide_answer_rows.append(box)
        if node.get("draft"):
            lay.addWidget(mk_label(host, "定稿（可直接编辑后采纳）", size=11, bold=True,
                                   color=PAL["accent"], width_px=560, wrap=False))
            self.guide_draft_box = CTextEdit(master=host, width=520, height=190,
                                             font_family=UI_FONT, font_size=9,
                                             text=node["draft"])
            lay.addWidget(self.guide_draft_box)
            if node.get("risks"):
                lay.addWidget(mk_label(host, "风险提示：\n" + node["risks"], size=9,
                                       width_px=560, wrap=True, color=PAL["bad"],
                                       bg=PAL["surface2"], radius=8, min_h=34))
            tips = scope_core.parse_suggestions(node.get("checklist", ""),
                                                sec.get("checks", []))
            if tips:
                ok = [str(i + 1) for i, v in tips if v]
                no = [str(i + 1) for i, v in tips if not v]
                lay.addWidget(mk_label(
                    host, "模型判定：已满足 " + ("、".join(ok) or "—")
                    + "；待补 " + ("、".join(no) or "—")
                    + "（采纳时会自动勾选已满足项）", size=9, width_px=560, wrap=True,
                    color=PAL["muted"]))
        if node.get("final"):
            lay.addWidget(mk_label(host, "已收录定稿", size=11, bold=True,
                                   color=PAL["ok"], width_px=560, wrap=False))
            lay.addWidget(mk_label(host, node["final"], size=9, width_px=560, wrap=True,
                                   color=PAL["text"], bg=PAL["surface2"], radius=8,
                                   min_h=40))
        if not lay.count():
            lay.addWidget(mk_label(
                host, "这个环节还没有内容。点「开始引导」：模型会带着本环节的规范要求"
                      "和本项目已有的相关定稿，先给出「现状评估」，再提出必须澄清的问题；"
                      "你回答后它会产出可直接采纳的定稿，并按检查表给出勾选建议。",
                size=9, width_px=560, wrap=True, color=PAL["muted"]))
        # 按钮可用性
        busy = self.win._busy()
        self.btn_guide_start.setEnabled(not busy)
        self.btn_guide_submit.setEnabled(bool(node.get("questions")) and not busy)
        self.btn_guide_regen.setEnabled(bool(node.get("questions")) and not busy)
        self.btn_guide_accept.setEnabled(bool(node.get("draft")) and not busy)

    def inferred_for_section(self, sec: dict) -> dict | None:
        """从模型的收敛推理结果里取出与本环节对应的一章。

        匹配依据是**模型自己输出的章节名**（拿本环节标题里的英文词去对），
        代码里不存在"哪一章对应哪个环节"的固定表。
        """
        conv = getattr(self.win.project, "convergence", None) or {}
        chapters = conv.get("chapters") or []
        if not chapters:
            return None
        m = re.search(r"([A-Za-z][A-Za-z \-]{2,})", sec.get("title", "") or "")
        eng = (m.group(1).strip().lower() if m else "")
        if not eng:
            return None
        return next((ch for ch in chapters
                     if eng in (ch.get("title") or "").lower()), None)

    # ---------------------------------------------------------------- 子类钩子
    def head_text(self, sec: dict) -> str:
        return sec["title"]

    def goal_text(self, sec: dict) -> str:
        return sec.get("goal", "")

    def render_detail(self, sec: dict):
        raise NotImplementedError

    def extra_text(self, sec: dict) -> str:
        return ""


class StatScopePage(ScopePage):
    """Statistic 页：科学问题统计计算与归纳的 9 阶段（含常用检验速查表）。"""

    def __init__(self, win):
        super().__init__(win, store_key="stat", data=STAT_STAGES,
                         rail_title="统计九阶段", side_title="完成度与自检",
                         unit="阶段")

    def head_text(self, sec):
        return f"{sec['icon']} {self.cur + 1:02d} · {sec['title']}"

    def goal_text(self, sec):
        return "本阶段要做什么：" + sec["desc"]

    def render_detail(self, sec):
        lay = self.detail_lay
        clear_layout(lay)
        cat = stat.CATS.get(sec["cat"], {"n": sec["cat"], "c": C("accent")})
        lay.addWidget(mk_label(self.detail_host, f"{cat['n']} · 阶段 {sec['id']}/9",
                               size=8, width_px=560, wrap=True, color="#FFFFFF",
                               bg=cat["c"], radius=9, min_h=26))
        # 目标 / 核心动作
        lay.addWidget(self._block_title(sec.get("goal_title", "目标")))
        for t in sec["goal"]:
            lay.addWidget(self._line("·　" + t))
        # 示例化表述
        if sec.get("example"):
            lay.addWidget(self._block_title(sec.get("example_title", "示例化表述")))
            for ln in str(sec["example"]).split("\n"):
                lay.addWidget(mk_label(self.detail_host, ln, size=9, width_px=560,
                                       wrap=True, color=PAL["muted"],
                                       bg=PAL["surface2"], radius=8, min_h=32))
        # 公式
        if sec.get("formula"):
            lay.addWidget(self._block_title("公式与参数"))
            for f in sec["formula"]:
                lay.addWidget(mk_label(self.detail_host, f, size=9, width_px=560,
                                       wrap=True, color=PAL["text"], bg=PAL["surface2"],
                                       radius=8, min_h=30))
        # 常见陷阱
        lay.addWidget(self._block_title("常见陷阱", "✓ 做对的样子见右栏自检"))
        for t in sec["pitfalls"]:
            lay.addWidget(self._line("✕　" + t, color=PAL["bad"]))
        # 输出
        if sec.get("output"):
            lay.addWidget(self._block_title(sec.get("output_title", "输出")))
            for t in sec["output"]:
                lay.addWidget(self._line("→　" + t, color=PAL["ok"]))
        # 速查表（只挂在「检验计算」阶段）
        if sec["id"] == 6:
            lay.addWidget(self._block_title("常用检验速查表",
                                            "场景 → 方法 · 前提 · scipy · R"))
            for row in stat.CHEATSHEET:
                lay.addWidget(mk_label(self.detail_host, f"{row[0]} → {row[1]}",
                                       size=9, bold=True, width_px=560, wrap=True,
                                       color=PAL["accent"]))
                lay.addWidget(mk_label(
                    self.detail_host,
                    f"　　前提：{row[2]}　｜　scipy：{row[3]}　｜　R：{row[4]}",
                    size=8, width_px=560, wrap=True, color=PAL["muted"]))
            lay.addWidget(mk_label(
                self.detail_host,
                "stat_run_test 支持 16 种 kind：" + "、".join(stat.TEST_KINDS),
                size=8, width_px=560, wrap=True, color=PAL["muted"]))
        if sec.get("note"):
            lay.addWidget(self._block_title("说明"))
            lay.addWidget(mk_label(self.detail_host, sec["note"], size=9, width_px=560,
                                   wrap=True, color=PAL["muted"], bg=PAL["surface2"],
                                   radius=8, min_h=34))
        lay.addSpacing(10)

    def extra_text(self, sec):
        lines = []
        tools = sec.get("tools") or []
        lines.append("对应工具：" + ("、".join(tools) if tools else
                                 "本阶段无计算工具（由数据准备脚本承担，决策需留痕）"))
        lines.append("与其他页面的关系由模型在引导对话中自行判断：它会通读项目全部素材，"
                     "决定哪些与本阶段相关（代码不设固定映射）。")
        lines.append("架构来源：9 阶段状态机 + 12 个工具（7 控制 / 5 计算），计算层纯 numpy+scipy。")
        return "\n".join(lines)


class ShapeScopePage(ScopePage):
    """SCI Shape 页：七章通用结构与本稿自评（原实现迁移到通用模板）。"""

    def __init__(self, win):
        super().__init__(win, store_key="shape", data=SHAPE,
                         rail_title="SCI 七章环节", side_title="完成度与自检",
                         unit="章")

    def head_text(self, sec):
        return f"{self.cur + 1:02d} · {sec['title']}"

    def goal_text(self, sec):
        return "功能定位：" + sec["goal"]

    def render_detail(self, sec):
        lay = self.detail_lay
        clear_layout(lay)
        lay.addWidget(self._block_title(
            f"通用模型（{len(sec['model'])} 个组件）", "按原书顺序，见 " + sec["spec"]))
        for i, m in enumerate(sec["model"], 1):
            lay.addWidget(mk_label(self.detail_host, f"{i:02d}　{m['en']}", size=9,
                                   bold=True, width_px=560, wrap=True, color=PAL["text"]))
            zh = re.sub(r"^[①-⑳]\s*", "", m["zh"])
            lay.addWidget(mk_label(self.detail_host, "　　　" + zh, size=9, width_px=560,
                                   wrap=True, color=PAL["muted"]))
        lay.addWidget(self._block_title("内容边界", "✓ 必须写进去　✕ 不得写进去"))
        for t in sec["must"]:
            lay.addWidget(self._line("✓　" + t, color=PAL["ok"]))
        for t in sec["must_not"]:
            lay.addWidget(self._line("✕　" + t, color=PAL["bad"]))
        if sec["language"]:
            lay.addWidget(self._block_title("语言与时态", "括号内为书内页码"))
            for r in sec["language"]:
                lay.addWidget(self._line(f"·　{r['rule']}（{r['page']}）"))
        if sec["phrases"]:
            lay.addWidget(self._block_title("词块组", "英文原短语 + 书内页码"))
            for g in sec["phrases"]:
                lay.addWidget(mk_label(self.detail_host,
                                       f"{g['group']}　（书 {g['page']}）", size=9,
                                       bold=True, width_px=560, wrap=True,
                                       color=PAL["accent"]))
                lay.addWidget(mk_label(self.detail_host, "　　" + "；".join(g["items"]),
                                       size=9, width_px=560, wrap=True,
                                       color=PAL["muted"]))
        if sec.get("note"):
            lay.addWidget(self._block_title("说明"))
            lay.addWidget(mk_label(self.detail_host, sec["note"], size=9, width_px=560,
                                   wrap=True, color=PAL["muted"], bg=PAL["surface2"],
                                   radius=8, min_h=34))
        lay.addSpacing(10)

    def extra_text(self, sec):
        """右栏补充：显示**模型推理**给出的本章来源/缺口（没有推理结果就提示去总览跑）。"""
        ch = self.inferred_for_section(sec)
        if not ch:
            return ("本章与其他页面素材的关系由模型推理判断：在总览点「开始推理」，"
                    "模型会说明本章的来源、已有、缺失与就绪度。")
        rd = ch.get("readiness")
        lines = []
        if ch.get("sources"):
            lines.append("模型判断来源：" + ch["sources"])
        if ch.get("missing") and ch["missing"].strip() not in ("无", "—", "-"):
            lines.append("尚缺：" + ch["missing"])
        if isinstance(rd, int):
            lines.append(f"就绪度 {rd}%")
        if ch.get("reason"):
            lines.append("理由：" + ch["reason"])
        return "\n".join(lines) or "（模型未给出本章结论）"


# --------------------------------------------------------------------------- 设置弹窗
class SettingsDialog(CTopLevel):
    saved = Signal(dict)

    def __init__(self, master, cfg: dict):
        super().__init__(width=560, height=470, title="LLM 服务设置",
                         background_color=PAL["bg"])
        self.cfg = dict(cfg)
        root = QVBoxLayout()
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(10)

        root.addWidget(mk_label(self, "LLM 服务设置", size=14, bold=True,
                                color=PAL["accent"], width_px=500))
        root.addWidget(mk_label(self,
                                "默认复用 agent 自身凭据（~/.dsh/.credentials.yaml 的 DEEPSEEK_API_KEY）。"
                                "任何 OpenAI 兼容端点都可以填在这里。",
                                size=9, color=PAL["muted"],
                                width_px=500))
        self.base = self._row(root, "Base URL", cfg.get("base_url", ""))
        self.key = self._row(root, "API Key", cfg.get("api_key", ""), password=True)
        self.model = self._row(root, "模型", cfg.get("model", ""))
        self.temp = self._row(root, "Temperature", str(cfg.get("temperature", 0.4)))
        self.result = mk_label(self, "", size=9, width_px=500,
                               color=PAL["muted"])
        root.addWidget(self.result)

        row = QWidget(self)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        rl.addWidget(CButton(master=row, text="测试连接", width=110, height=32,
                             font_family=UI_FONT, font_size=9, command=self.test))
        rl.addWidget(CButton(master=row, text="保存", width=90, height=32,
                             font_family=UI_FONT, font_size=9, command=self.commit))
        rl.addStretch(1)
        root.addWidget(row)
        root.addStretch(1)
        self.setLayout(root)

    def _row(self, root, label, value, password=False):
        wrap = QWidget(self)
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(mk_label(wrap, label, size=10, width_px=90))
        edit = CLineEdit(master=wrap, width=380, height=30, font_family=UI_FONT, font_size=9,
                         text=value or "", placeholder_text=label)
        if password:
            edit.line_edit().setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        lay.addWidget(edit)
        root.addWidget(wrap)
        return edit

    def values(self) -> dict:
        cfg = dict(self.cfg)
        cfg["base_url"] = self.base.line_edit().text().strip()
        key = self.key.line_edit().text().strip()
        if key:
            cfg["api_key"] = key
        cfg["model"] = self.model.line_edit().text().strip()
        try:
            cfg["temperature"] = float(self.temp.line_edit().text().strip())
        except ValueError:
            pass
        return cfg

    def test(self):
        self.result.label().setText("正在测试…")
        QApplication.processEvents()
        try:
            cli = LLMClient(self.values())
            models = cli.list_models()
            out = cli.chat([{"role": "user", "content": "只回答：OK"}], max_tokens=200)
            self.result.label().setText(
                f"连接成功 · {out['elapsed']:.1f}s · 可用模型 {len(models)} 个"
                f"（{', '.join(models[:4])}）")
        except Exception as e:                                     # noqa: BLE001
            self.result.label().setText(f"失败：{e}")

    def commit(self):
        cfg = self.values()
        save_config(cfg)
        self.saved.emit(cfg)
        self.close()


# --------------------------------------------------------------------------- 通用小弹窗
class PromptDialog(CTopLevel):
    """命名 / 新建用：单行输入 + 可选多行文本。"""
    submitted = Signal(dict)

    def __init__(self, master, title, label, value="", with_text=False,
                 text_label="", text_value="", placeholder="", danger=False):
        super().__init__(width=620, height=520 if with_text else 300, title=title,
                         background_color=PAL["bg"])
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        root = QVBoxLayout()
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(10)
        root.addWidget(mk_label(self, title, size=14, bold=True,
                                color=PAL["accent"], width_px=560))
        root.addWidget(mk_label(self, label, size=10, width_px=560))
        self.edit = CLineEdit(master=self, width=560, height=32, font_family=UI_FONT,
                              font_size=10, text=value, placeholder_text=placeholder)
        root.addWidget(self.edit)
        self.text = None
        if with_text:
            root.addWidget(mk_label(self, text_label, size=10, width_px=560))
            self.text = CTextEdit(master=self, width=560, height=260, font_family=UI_FONT,
                                  font_size=10, text=text_value,
                                  placeholder_text="把初步实验设计贴在这里，也可以先建空项目稍后再填……")
            root.addWidget(self.text, 1)
        self.hint = mk_label(self, "", size=9, width_px=560, color=PAL["danger"])
        root.addWidget(self.hint)
        root.addStretch(1)
        row = QWidget(self)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        rl.addStretch(1)
        rl.addWidget(CButton(master=row, text="取消", width=90, height=32, font_family=UI_FONT,
                             font_size=9, command=self.close,
                             background_color=PAL["btn"],
                             text_color=PAL["text"],
                             hover_color=PAL["btn_hover"],
                             border_color=PAL["border"]))
        ok = CButton(master=row, text="确定", width=100, height=32, font_family=UI_FONT,
                     font_size=9, command=self._ok,
                     background_color=PAL["danger"] if danger
                     else PAL["accent"],
                     text_color=PAL["on_accent"] if not danger
                     else ("rgb(255,255,255)", "rgb(255,255,255)"))
        rl.addWidget(ok)
        root.addWidget(row)
        self.setLayout(root)

    def _ok(self):
        name = self.edit.line_edit().text().strip()
        if not name:
            self.hint.label().setText("名称不能为空")
            return
        payload = {"name": name}
        if self.text is not None:
            payload["text"] = self.text.text_edit().toPlainText().strip()
        self.submitted.emit(payload)
        self.close()


class ConfirmDialog(CTopLevel):
    confirmed = Signal()

    def __init__(self, master, title, message, ok_text="确认删除"):
        super().__init__(width=560, height=250, title=title, background_color=PAL["bg"])
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        root = QVBoxLayout()
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(10)
        root.addWidget(mk_label(self, title, size=14, bold=True,
                                color=PAL["danger"], width_px=500))
        root.addWidget(mk_label(self, message, size=10, width_px=500))
        root.addStretch(1)
        row = QWidget(self)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addStretch(1)
        rl.addWidget(CButton(master=row, text="取消", width=90, height=32, font_family=UI_FONT,
                             font_size=9, command=self.close,
                             background_color=PAL["btn"],
                             text_color=PAL["text"],
                             hover_color=PAL["btn_hover"],
                             border_color=PAL["border"]))
        rl.addWidget(CButton(master=row, text=ok_text, width=120, height=32, font_family=UI_FONT,
                             font_size=9, command=self._ok,
                             background_color=PAL["danger"],
                             text_color="#FFFFFF"))
        root.addWidget(row)
        self.setLayout(root)

    def _ok(self):
        self.confirmed.emit()
        self.close()


# --------------------------------------------------------------------------- 项目管理
class ProjectManagerDialog(CTopLevel):
    """项目列表：打开 / 重命名 / 复制 / 删除 / 新建 / 定位文件。"""
    openRequested = Signal(str)          # path
    createRequested = Signal()
    renamed = Signal(str, str)           # path, new_name
    duplicated = Signal(str, str)        # path, new_name
    deleteRequested = Signal(str)        # path

    def __init__(self, master, current_path=""):
        super().__init__(width=900, height=620, title="项目管理", background_color=PAL["bg"])
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.current_path = current_path
        self.rows: list[dict] = []

        root = QVBoxLayout()
        root.setContentsMargins(22, 18, 22, 16)
        root.setSpacing(10)
        head = QWidget(self)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        hl.addWidget(mk_label(head, "项目管理", size=14, bold=True,
                              color=PAL["accent"], width_px=120))
        hl.addWidget(mk_label(head, "文件存于 projects/ · 双击打开 · 支持重命名 / 副本 / 删除",
                              size=9, width_px=460, wrap=False,
                              color=PAL["muted"]))
        hl.addStretch(1)
        self.search = CLineEdit(master=head, width=220, height=30, font_family=UI_FONT,
                                font_size=9, placeholder_text="搜索项目名…")
        self.search.line_edit().textChanged.connect(lambda _t: self.reload())
        hl.addWidget(self.search)
        root.addWidget(head)

        self.list = QtWidgets.QListWidget(self)
        self.list.setStyleSheet(
            f"QListWidget {{ background:{C('surface2')}; color:{C('text')};"
            f" border:1px solid {C('border')}; border-radius:10px; font-family:'{UI_FONT}';"
            " font-size:10pt; outline:none; }"
            f"QListWidget::item {{ padding:10px 12px; border-bottom:1px solid {C('border')}; }}"
            f"QListWidget::item:selected {{ background:{C('node_active')}; color:{C('accent')}; }}")
        self.list.itemDoubleClicked.connect(lambda _i: self._open())
        self.list.currentRowChanged.connect(lambda _r: self._sync_buttons())
        root.addWidget(self.list, 1)

        self.meta = mk_label(self, "", size=9, width_px=840,
                             color=PAL["muted"])
        root.addWidget(self.meta)

        row = QWidget(self)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        self.b_open = self._btn(rl, "打开", 84, self._open, primary=True)
        self.b_rename = self._btn(rl, "重命名", 96, self._rename)
        self.b_copy = self._btn(rl, "创建副本", 104, self._duplicate)
        self.b_folder = self._btn(rl, "打开文件夹", 110, self._open_folder)
        self.b_del = self._btn(rl, "删除", 84, self._delete, danger=True)
        rl.addStretch(1)
        self._btn(rl, "新建项目", 110, lambda: self.createRequested.emit(), primary=True)
        root.addWidget(row)
        self.setLayout(root)
        self.reload()

    def _btn(self, layout, text, width, cmd, primary=False, danger=False):
        bg = PAL["btn"]
        fg = PAL["text"]
        hover = PAL["btn_hover"]
        if primary:
            bg, fg, hover = PAL["accent"], \
                            PAL["on_accent"], \
                            PAL["accent_hover"]
        if danger:
            bg, fg = PAL["danger_bg"], PAL["danger"]
        btn = CButton(master=self, text=text, width=width, height=34, font_family=UI_FONT,
                      font_size=9, command=cmd, background_color=bg, text_color=fg,
                      hover_color=hover, border_color=PAL["border"])
        layout.addWidget(btn)
        return btn

    # -- 列表 ---------------------------------------------------------------
    def reload(self, select_path: str = ""):
        keep = select_path or self._selected_path() or self.current_path
        kw = self.search.line_edit().text().strip().lower()
        self.rows = [m for m in Project.list_all() if not kw or kw in m["name"].lower()]
        self.list.clear()
        for m in self.rows:
            mark = "● " if os.path.abspath(m["path"]) == os.path.abspath(self.current_path) else "   "
            item = QtWidgets.QListWidgetItem(
                f"{mark}{m['name']}\n     {m['done']}/10 阶段 · 更新 {m['updated']} · "
                f"{m['size_kb']} KB" + (f" · {m['model']}" if m["model"] else ""))
            item.setData(Qt.ItemDataRole.UserRole, m["path"])
            self.list.addItem(item)
        if self.rows:
            want = next((i for i, m in enumerate(self.rows)
                         if os.path.abspath(m["path"]) == os.path.abspath(keep)), 0)
            self.list.setCurrentRow(want)
        self.meta.label().setText(
            f"共 {len(self.rows)} 个项目 · 目录：{Project.dir()}")
        self._sync_buttons()

    def _selected_path(self) -> str:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    def _selected_name(self) -> str:
        r = self.list.currentRow()
        return self.rows[r]["name"] if 0 <= r < len(self.rows) else ""

    def _sync_buttons(self):
        has = bool(self._selected_path())
        for b in (self.b_open, self.b_rename, self.b_copy, self.b_folder, self.b_del):
            b.button().setEnabled(has)

    # -- 动作 ---------------------------------------------------------------
    def _open(self):
        p = self._selected_path()
        if p:
            self.openRequested.emit(p)
            self.close()

    def _open_folder(self):
        p = self._selected_path()
        if p:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(p)])

    def _rename(self):
        p, old = self._selected_path(), self._selected_name()
        if not p:
            return
        dlg = PromptDialog(self, "重命名项目", "新的项目名称（文件名会同步变更）：", old)
        dlg.submitted.connect(lambda d: (self.renamed.emit(p, d["name"]), self.reload()))
        dlg.show()

    def _duplicate(self):
        p, old = self._selected_path(), self._selected_name()
        if not p:
            return
        dlg = PromptDialog(self, "创建副本", "副本名称：", f"{old} 副本")
        dlg.submitted.connect(lambda d: (self.duplicated.emit(p, d["name"]), self.reload()))
        dlg.show()

    def _delete(self):
        p, old = self._selected_path(), self._selected_name()
        if not p:
            return
        dlg = ConfirmDialog(self, "删除项目",
                            f"确定删除「{old}」吗？项目文件将被移除，且无法撤销。\n"
                            f"（位置：{os.path.basename(p)}）")
        dlg.confirmed.connect(lambda: (self.deleteRequested.emit(p), self.reload()))
        dlg.show()


def make_flex(widget, min_w: int = 160, min_h: int = 60, vertical: str = "expanding"):
    """让 PyCt6 的输入类控件撑满容器。

    PyCt6 的 CTextEdit / CLineEdit 构造时把尺寸策略设成 Fixed/Fixed，
    放进布局后不会随容器伸缩，窗口变宽就会留下空白。
    """
    v = {"expanding": QSizePolicy.Policy.Expanding,
         "fixed": QSizePolicy.Policy.Fixed,
         "minimum": QSizePolicy.Policy.Minimum}[vertical]
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, v)
    widget.setMinimumSize(min_w, min_h)
    return widget

# --------------------------------------------------------------------------- 主窗口
class StudioWindow(CMainWindow):
    def __init__(self, demo: bool = False):
        sw, sh, sx, sy = screen_size(1520, 960, 1180, 720)
        super().__init__(width=sw, height=sh, x=sx, y=sy, title="组学研究设计工作台",
                         icon=ICON_PATH, background_color=PAL["bg"])
        self.setMinimumSize(1120, 700)
        self.cfg = load_config()
        self.client = LLMClient(self.cfg)
        self.demo = demo
        self.project = Project(name="未命名课题", model=self.client.model)
        self.agent = DesignAgent(self.client, self.project)
        self.phase = "raw"
        self.thread = None
        self.answer_rows = []
        self.pending_draft = ""
        self.final_mode = False
        install_button_skin()          # 保证任何构造路径下按钮都有立体皮肤

        root = QVBoxLayout()
        root.setContentsMargins(18, 16, 18, 10)
        root.setSpacing(10)
        root.addWidget(self._build_header())
        root.addWidget(self._build_flow())

        body = QWidget(self)
        blay = QHBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        blay.setSpacing(14)
        self.left_col = self._build_left()
        blay.addWidget(self.left_col)
        blay.addWidget(self._build_center(), 1)
        blay.addWidget(self._build_right())

        # 工作台 / Statistic / SCI Shape / 总览 四个视图共存于同一窗口，按钮切换
        self.body_stack = QtWidgets.QStackedWidget(self)
        self.body_stack.addWidget(body)                        # 0 工作台
        self.body_stack.addWidget(self._build_stat_page())      # 1 Statistic
        self.body_stack.addWidget(self._build_shape_page())     # 2 SCI Shape
        self.body_stack.addWidget(self._build_overview())       # 3 总览
        root.addWidget(self.body_stack, 1)

        root.addWidget(self._build_footer())
        root.addWidget(CreditBar(self))
        self.setLayout(root)

        self._apply_responsive()
        self._apply_root_bg()
        self._sync_flow(0)
        self._view = "work"
        self._welcome()
        self._refresh_all()
        if demo:
            self._load_demo()
        else:
            self.show_raw_input()
        self._fetch_models()

    # ---------------------------------------------------------------- Statistic / SCI Shape
    def _build_stat_page(self) -> QWidget:
        self.stat_page = StatScopePage(self)
        return self.stat_page.body

    def _build_shape_page(self) -> QWidget:
        self.shape_page = ShapeScopePage(self)
        return self.shape_page.body

    def show_stat(self):
        self.stat_page.refresh()
        self.body_stack.setCurrentIndex(1)
        self._sync_flow(1)
        self._view = "stat"

    def show_sci_shape(self):
        self.shape_page.refresh()
        self.body_stack.setCurrentIndex(2)
        self._sync_flow(2)
        self._view = "shape"

    def _build_flow(self) -> Card:
        """流程条：把四个视图按先后顺序做成三维键帽（设计 → 统计 → 结构 → 总览）。"""
        card = Card(self, margin=(16, 7, 16, 7), spacing=0)
        self.flow_card = card
        self.flow = FlowStepper(card, [
            {"title": "设计工作台", "sub": "十阶段追问与改写"},
            {"title": "统计 Statistic", "sub": "九阶段计算与归纳"},
            {"title": "SCI 结构 Shape", "sub": "七章 scope 自评"},
            {"title": "总览 Overview", "sub": "评分与检查表"},
        ], height=42)
        self.flow.stepClicked.connect(self.goto_step)
        card.layout().addWidget(self.flow)
        return card

    def goto_step(self, idx: int):
        """点击流程条上的步骤 → 跳到对应视图。"""
        steps = (self.show_workspace, self.show_stat, self.show_sci_shape,
                 self.show_overview)
        steps[max(0, min(len(steps) - 1, idx))]()

    def _sync_flow(self, idx: int):
        """同步流程条：当前步骤抬起，之前的步骤打勾，并把各视图进度挂成角标。"""
        if not hasattr(self, "flow"):
            return
        self.flow.set_current(idx)
        try:
            self.flow.set_badge(0, f"阶段 {self.current_index() + 1}/10")
            done, doing, ticks = scope_core.overall(self.project.stat, STAT_STAGES)
            self.flow.set_badge(1, f"自评 {ticks}/{scope_core.total_checks(STAT_STAGES)}")
            done2, doing2, ticks2 = scope_core.overall(self.project.shape, SHAPE)
            self.flow.set_badge(2, f"自评 {ticks2}/{scope_core.total_checks(SHAPE)}")
            counts = {"ok": 0, "warn": 0, "bad": 0}
            for st in STAGES:
                s = self.project.stage(st["id"]).get("status", "todo")
                counts["ok" if s == "done" else ("warn" if s in ("drafted", "asked")
                                                 else "bad")] += 1
            self.flow.set_badge(3, f"定稿 {counts['ok']}/10")
            # 总览角标：模型给出过就绪度就用它，否则退回事实计数
            chapters = (getattr(self.project, "convergence", None) or {}).get("chapters") or []
            ready = [c.get("readiness") for c in chapters
                     if isinstance(c.get("readiness"), int)]
            if ready:
                self.flow.set_badge(3, f"就绪 {sum(ready) // len(ready)}%")
        except Exception:                                       # noqa: BLE001
            pass

    # ---------------------------------------------------------------- 总览视图
    def _build_overview(self) -> Card:
        """总览 = 收敛视图（三路输入 → 七章）+ 十阶段评分与检查表明细。"""
        page = Card(self, margin=(20, 16, 20, 16), spacing=10, deep=True)
        lay = page.layout()

        head = QWidget(page)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(12)
        hl.addWidget(mk_label(head, "总览 · 收敛视图与评分", size=15, bold=True,
                              color=PAL["accent"], width_px=300, wrap=False))
        self.ov_summary = mk_label(head, "", size=10, width_px=520, wrap=False,
                                   color=PAL["muted"])
        hl.addWidget(self.ov_summary, 1)
        self.ov_progress = ProgressBar(head, width=180, height=8)
        wrap = QWidget(head)
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wrap.setFixedSize(180, 28)
        wl.addWidget(self.ov_progress, 0, Qt.AlignVCenter)
        hl.addWidget(wrap)
        hl.addWidget(CButton(master=head, text="返回工作台", width=110, height=30,
                             font_family=UI_FONT, font_size=9, command=self.show_workspace,
                             background_color=PAL["btn"], text_color=PAL["text"],
                             hover_color=PAL["btn_hover"], border_color=PAL["border"]))
        lay.addWidget(head)

        # 收敛视图整体可滚动（下面还有十阶段明细表，页面高度会超出窗口）
        self.ov_scroll = WorkScroll(page)
        self.ov_host = QWidget()
        self.ov_lay = QVBoxLayout(self.ov_host)
        self.ov_lay.setContentsMargins(0, 0, 6, 0)
        self.ov_lay.setSpacing(8)

        # ① 收敛推理（reason 模式）：章节归属、完整度与缺口全部由模型推断
        crow = QWidget(self.ov_host)
        crl = QHBoxLayout(crow)
        crl.setContentsMargins(0, 0, 0, 0)
        crl.setSpacing(10)
        crl.addWidget(mk_label(crow, "收敛推理（reason 模式）", size=12, bold=True,
                               color=PAL["accent"], width_px=200, wrap=False))
        self.conv_state = mk_label(crow, "", size=9, width_px=520, wrap=False,
                                   color=PAL["muted"])
        crl.addWidget(self.conv_state, 1)
        self.btn_conv = CButton(master=crow, text="开始推理", width=104, height=30,
                                font_family=UI_FONT, font_size=9,
                                command=self.run_convergence,
                                background_color=PAL["accent"],
                                text_color=PAL["on_accent"],
                                hover_color=PAL["accent_hover"])
        self.btn_conv_re = CButton(master=crow, text="重新推理", width=104, height=30,
                                   font_family=UI_FONT, font_size=9,
                                   command=self.run_convergence,
                                   background_color=PAL["btn"],
                                   text_color=PAL["text"],
                                   hover_color=PAL["btn_hover"],
                                   border_color=PAL["border"])
        self.btn_conv.setFixedWidth(104)
        self.btn_conv_re.setFixedWidth(104)
        crl.addWidget(self.btn_conv)
        crl.addWidget(self.btn_conv_re)
        self.ov_lay.addWidget(crow)

        self.conv_transcript = TranscriptView(self.ov_host)
        self.conv_transcript.setMinimumHeight(120)
        self.ov_lay.addWidget(self.conv_transcript)

        self.conv_summary = mk_label(self.ov_host, "", size=10, width_px=980, wrap=True,
                                     color=PAL["text"], bg=PAL["surface2"], radius=8,
                                     min_h=36)
        self.ov_lay.addWidget(self.conv_summary)
        self.conv_host = QWidget(self.ov_host)
        self.conv_lay = QVBoxLayout(self.conv_host)
        self.conv_lay.setContentsMargins(0, 0, 0, 0)
        self.conv_lay.setSpacing(6)
        self.ov_lay.addWidget(self.conv_host)

        # ② 三条工作线完成度（纯事实统计）
        lanes = QWidget(self.ov_host)
        ll = QHBoxLayout(lanes)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)
        self.ov_lane_bars, self.ov_lane_lbls = {}, {}
        for key, name, desc in coupling.LANES:
            box = Card(lanes, margin=(12, 9, 12, 9), spacing=3)
            bl = box.layout()
            bl.addWidget(mk_label(box, name, size=10, bold=True, width_px=280,
                                  wrap=False, color=PAL["accent"]))
            bl.addWidget(mk_label(box, desc, size=8, width_px=280, wrap=True,
                                  color=PAL["muted"]))
            row = QWidget(box)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            bar = ProgressBar(row, width=150, height=8)
            rl.addWidget(bar)
            lbl = mk_label(row, "", size=9, width_px=120, wrap=False, color=PAL["muted"])
            rl.addWidget(lbl, 1)
            bl.addWidget(row)
            self.ov_lane_bars[key] = bar
            self.ov_lane_lbls[key] = lbl
            ll.addWidget(box, 1)
        self.ov_lay.addWidget(lanes)

        # ⑤ 十阶段评分与检查表明细（原表格）
        self.ov_lay.addWidget(mk_label(self.ov_host, "十阶段评分与检查表明细（设计工作台）",
                                       size=11, bold=True, color=PAL["accent"],
                                       width_px=300, wrap=False))
        self.ov_cols = ["#", "阶段", "状态", "规范出处", "结果 / 待办", "检查表", "更新"]
        self.ov_table = QtWidgets.QTableWidget(0, len(self.ov_cols), self.ov_host)
        self.ov_table.setHorizontalHeaderLabels(self.ov_cols)
        self.ov_table.verticalHeader().setVisible(False)
        self.ov_table.setShowGrid(False)
        self.ov_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ov_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.ov_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)        # 纯只读
        self.ov_table.verticalHeader().setDefaultSectionSize(40)
        self.ov_table.horizontalHeader().setFixedHeight(40)
        for i, w in enumerate((54, 206, 100, 258, 0, 82, 82)):
            if w:
                self.ov_table.setColumnWidth(i, w)
        self.ov_table.horizontalHeader().setSectionResizeMode(
            4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.ov_lay.addWidget(self.ov_table)
        self.ov_lay.addStretch(1)
        self.ov_scroll.setWidget(self.ov_host)
        lay.addWidget(self.ov_scroll, 1)
        return page

    def _style_table(self):
        self.ov_table.setStyleSheet(
            f"QTableWidget {{ background: {C('surface2')}; color: {C('text')};"
            f" border: 1px solid {C('border')}; border-radius: 10px;"
            f" font-family: '{UI_FONT}'; font-size: 10pt; }}"
            f"QTableWidget::item {{ padding: 4px 6px;"
            f" border-bottom: 1px solid {C('border')}; }}"
            f"QHeaderView::section {{ background: {C('accent')};"
            f" color: {C('on_accent')}; padding: 8px 6px; border: none;"
            f" font-family: '{UI_FONT}'; font-size: 10pt; font-weight: bold; }}"
            f"QTableCornerButton::section {{ background: {C('accent')}; border: none; }}")

    def show_overview(self):
        self.refresh_overview()
        self.body_stack.setCurrentIndex(3)
        self._sync_flow(3)
        self._view = "overview"

    def show_workspace(self):
        self.body_stack.setCurrentIndex(0)
        self._sync_flow(0)
        self._view = "work"

    def refresh_overview(self):
        """重建总览：收敛视图（三路 → 七章）+ 十阶段评分明细（只读）。"""
        self._style_table()
        tone = {"done": "ok", "drafted": "warn", "asked": "warn", "todo": "bad"}
        label = {"done": "已完成", "drafted": "待采纳", "asked": "已追问", "todo": "未开始"}
        counts = {"ok": 0, "warn": 0, "bad": 0}
        rows = []

        for st in STAGES:
            sid = st["id"]
            state = self.project.stage(sid).get("status", "todo")
            key = tone.get(state, "bad")
            counts[key] += 1
            final = (self.project.stage(sid).get("final") or "").strip()
            draft = (self.project.stage(sid).get("draft") or "").strip()
            checks = self.project.stage(sid).get("checklist") or []
            updated = self.project.stage(sid).get("updated") or "—"
            if final:
                one = final.replace("\n", " ")
                result = f"定稿：{one[:52]}…" if len(one) > 52 else f"定稿：{one}"
            elif draft:
                result = "已有改写稿，等待采纳"
            elif state == "asked":
                result = "已完成追问，等待回答"
            else:
                result = "尚未开始本阶段"
            rows.append((f"{sid:02d}", st["title"], label.get(state, state), st["spec"],
                         result, str(len(checks)) if checks else "—", updated, key))

        self.ov_table.setRowCount(len(rows))
        for r, (num, title, status, spec, result, checks, updated, key) in enumerate(rows):
            for c, text in enumerate([num, title, status, spec, result, checks, updated]):
                item = QtWidgets.QTableWidgetItem(text)
                f = QtGui.QFont(UI_FONT, 10)
                if c in (0, 2, 5, 6):
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                color = C("text")
                if c == 0:
                    color, _b = C(key), f.setBold(True)
                elif c == 1:
                    f.setBold(True)
                elif c == 2:
                    color, _b = C(key), f.setBold(True)
                    text = "● " + status
                    item.setText(text)
                elif c in (3, 5, 6):
                    color = C("muted")
                item.setForeground(QtGui.QColor(color))
                item.setFont(f)
                self.ov_table.setItem(r, c, item)

        done = sum(1 for s in STAGES if self.project.stage(s["id"]).get("status") == "done")
        self.ov_summary.label().setText(
            f"● 绿 {counts['ok']} 已完成　"
            f"● 黄 {counts['warn']} 进行中　"
            f"● 红 {counts['bad']} 未开始　·　"
            f"共 {done}/10 阶段定稿")
        self.ov_progress.set_value(done / len(STAGES))
        # 明细表按内容定高（外层滚动容器负责翻页）
        self.ov_table.setFixedHeight(40 * len(rows) + 44)
        self.refresh_convergence()

    def run_convergence(self):
        """让模型在 reason 模式下推断：每条素材收敛到哪一章、各章还缺什么。"""
        if self._busy():
            return
        self.conv_transcript.add_rule()
        self.conv_transcript.add_header("收敛推理（reason 模式）", "agent",
                                        time.strftime("%H:%M"))
        self.conv_state.label().setText("正在推理…（推理过程会以弱化色实时显示）")
        self._run(self.agent.convergence_messages(), on_done=self._after_convergence,
                  view=self.conv_transcript, reason=True)

    def _after_convergence(self, out: dict):
        data = parse_convergence(out["content"])
        data["updated"] = time.strftime("%Y-%m-%d %H:%M")
        data["model"] = out.get("model", "")
        data["elapsed"] = round(float(out.get("elapsed") or 0), 1)
        data["reasoning"] = (out.get("reasoning") or "")[:8000]
        self.project.convergence = data
        self._flush_project()
        self.refresh_convergence()
        self._sync_flow(3)
        self._toast(f"收敛推理完成：{len(data['chapters'])} 章 · "
                    f"{len(data['actions'])} 条下一步动作")

    def refresh_convergence(self):
        """渲染模型给出的收敛结论；未推理时给出一条引导。"""
        conv = getattr(self.project, "convergence", None) or {}
        chapters = conv.get("chapters") or []
        reasoning = conv.get("reasoning") or ""
        self.conv_state.label().setText(
            (f"已更新 · {conv.get('updated', '')} · {conv.get('model', '')}"
             f" · {conv.get('elapsed', '')}s · {len(chapters)} 章")
            if chapters else
            "尚未推理 · 点「开始推理」由模型自行判断各章来源与缺口")
        for lane in coupling.lane_progress(self.project):
            bar = self.ov_lane_bars.get(lane["key"])
            lbl = self.ov_lane_lbls.get(lane["key"])
            if bar is None:
                continue
            bar.set_value(lane["done"] / max(1, lane["total"]))
            lbl.label().setText(f"{lane['done']}/{lane['total']} {lane['unit']}")
        self.btn_conv.setEnabled(not self._busy())
        self.btn_conv_re.setEnabled(not self._busy() and bool(chapters))
        # 总览摘要
        if chapters or conv.get("overall"):
            txt = conv.get("overall") or ""
            if conv.get("basis"):
                txt += ("\n判定依据：" + conv["basis"]) if txt else conv["basis"]
            self.conv_summary.label().setText(txt or "（模型未给出总览）")
            self.conv_summary.setVisible(True)
        else:
            self.conv_summary.setVisible(False)
        lay, host = self.conv_lay, self.conv_host
        clear_layout(lay)
        if not chapters:
            if reasoning:
                lay.addWidget(mk_label(host, "上次推理过程（未解析出章节）", size=10,
                                       bold=True, color=PAL["accent"], width_px=960,
                                       wrap=False))
                lay.addWidget(mk_label(host, reasoning[:1200], size=9, width_px=960,
                                       wrap=True, color=PAL["muted"],
                                       bg=PAL["surface2"], radius=8, min_h=40))
            return
        for ch in chapters:
            box = Card(host, margin=(12, 9, 12, 9), spacing=3)
            bl = box.layout()
            head = QWidget(box)
            hl = QHBoxLayout(head)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(10)
            hl.addWidget(mk_label(head, ch.get("title", ""), size=11, bold=True,
                                  width_px=260, wrap=False, color=PAL["accent"]))
            rd = ch.get("readiness")
            if isinstance(rd, int):
                tone = "ok" if rd >= 80 else ("warn" if rd >= 40 else "bad")
                pill = mk_label(head, f"就绪度 {rd}%", size=9, width_px=110, wrap=False,
                                color="#FFFFFF", bg=PAL[tone], radius=9, min_h=26)
                pill.setFixedWidth(110)
                hl.addWidget(pill)
            hl.addStretch(1)
            bl.addWidget(head)
            for label, key, color in (("来源", "sources", PAL["muted"]),
                                      ("已有", "have", PAL["text"]),
                                      ("缺失", "missing", PAL["bad"]),
                                      ("理由", "reason", PAL["muted"])):
                val = (ch.get(key) or "").strip()
                if not val:
                    continue
                bl.addWidget(mk_label(box, f"{label}：{val}", size=9, width_px=940,
                                      wrap=True, color=color))
            lay.addWidget(box)
        if conv.get("actions"):
            lay.addWidget(mk_label(host, "下一批动作（模型按优先级排序）", size=11,
                                   bold=True, color=PAL["accent"], width_px=400,
                                   wrap=False))
            for i, a in enumerate(conv["actions"], 1):
                lay.addWidget(mk_label(host, f"{i}. {a}", size=9, width_px=960,
                                       wrap=True, color=PAL["text"]))

    # ---------------------------------------------------------------- 头部
    def _build_header(self) -> Card:
        h = Card(self, horizontal=True, margin=(20, 14, 18, 14), spacing=10)
        self.header = h
        h.setFixedHeight(108 + 2 * CARD_PAD)    # 外形比原先的 96 略高，容下两行副标题
        lay = h.layout()

        titles = QWidget(h)
        self.titles = titles
        titles.setMinimumWidth(300)                 # 窄窗口时允许收缩，不再压住右侧控件
        titles.setMaximumWidth(620)
        titles.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tl = QHBoxLayout(titles)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(10)
        # 注意：PyCt6 的 CLabel 传 icon_size 会触发其内部 bug（引用了不存在的属性），
        # 这里只传 icon，图标按 logo_badge.png 的原始 28×28 显示。
        badge = CLabel(titles, width=28, height=28, icon=BADGE_PATH,
                       border_width=0, tooltip="PCL-Radiomics")
        badge.setFixedSize(30, 30)
        badge.label().setFixedSize(28, 28)
        badge.label().setScaledContents(True)
        tl.addWidget(badge, 0, Qt.AlignVCenter)
        col = QWidget(titles)
        cl = QVBoxLayout(col)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(2)
        cl.addWidget(mk_label(col, "组学研究设计工作台", size=15, bold=True,
                              width_px=560, wrap=True))
        self.subtitle = mk_label(col, "贴入初步设想 → 十阶段逐段追问与改写 → 输出可执行研究设计",
                                 size=8, color=PAL["muted"], width_px=560, wrap=True)
        cl.addWidget(self.subtitle)
        tl.addWidget(col, 1)
        lay.addWidget(titles)

        # 流程导航已由上方「流程条」承担，页头只保留标题与项目/模型/设置
        lay.addWidget(titles)

        lay.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.MinimumExpanding,
                                QSizePolicy.Policy.Minimum))

        self._lbl_project = mk_label(h, "项目", size=9, align="right", width_px=36)
        self._lbl_project.setFixedWidth(38)
        lay.addWidget(self._lbl_project)
        self.project_box = CComboBox(master=h, width=190, height=30, font_family=UI_FONT,
                                     font_size=9, values=self._project_names(),
                                     current_value=self.project.name)
        self.project_box.combo_box().currentTextChanged.connect(self._on_project_pick)
        lay.addWidget(self.project_box)
        self.new_btn = CButton(master=h, text="新建", width=64, height=30, font_family=UI_FONT,
                               font_size=9, command=lambda: self.new_project(True),
                               background_color=PAL["btn"],
                               text_color=PAL["text"],
                               hover_color=PAL["btn_hover"],
                               border_color=PAL["border"])
        lay.addWidget(self.new_btn)
        # 一级界面直接改名 / 删除当前项目（不必再进「管理」弹窗）
        self.rename_btn = CButton(master=h, text="改名", width=64, height=30,
                                  font_family=UI_FONT, font_size=9,
                                  command=self.rename_current_project,
                                  background_color=PAL["btn"],
                                  text_color=PAL["text"],
                                  hover_color=PAL["btn_hover"],
                                  border_color=PAL["border"],
                                  tooltip="给当前项目改名（项目文件一并改名）")
        lay.addWidget(self.rename_btn)
        self.delete_btn = CButton(master=h, text="删除", width=64, height=30,
                                  font_family=UI_FONT, font_size=9,
                                  command=self.delete_current_project,
                                  background_color=PAL["btn"],
                                  text_color=PAL["danger"],
                                  hover_color=PAL["danger_bg"],
                                  border_color=PAL["border"],
                                  tooltip="删除当前项目（二次确认；删除后自动新建空项目）")
        lay.addWidget(self.delete_btn)
        self.manage_btn = CButton(master=h, text="管理", width=64, height=30,
                                  font_family=UI_FONT, font_size=9, command=self.manage_projects,
                                  background_color=PAL["accent"],
                                  text_color=PAL["on_accent"],
                                  hover_color=PAL["accent_hover"])
        lay.addWidget(self.manage_btn)

        self._lbl_model = mk_label(h, "模型", size=9, align="right", width_px=36)
        self._lbl_model.setFixedWidth(38)
        lay.addWidget(self._lbl_model)
        self.model_box = CComboBox(master=h, width=190, height=30, font_family=UI_FONT,
                                   font_size=9, values=[self.client.model],
                                   current_value=self.client.model)
        self.model_box.combo_box().currentTextChanged.connect(self._on_model_pick)
        lay.addWidget(self.model_box)

        self.settings_btn = CButton(master=h, text="设置", width=64, height=30,
                                    font_family=UI_FONT, font_size=9, command=self.open_settings,
                                    background_color=PAL["btn"],
                                    text_color=PAL["text"],
                                    hover_color=PAL["btn_hover"],
                                    border_color=PAL["border"])
        lay.addWidget(self.settings_btn)
        self.mode_btn = CButton(master=h, text="深色", width=64, height=30, font_family=UI_FONT,
                                font_size=9, command=self.toggle_mode,
                                background_color=PAL["btn"],
                                text_color=PAL["text"],
                                hover_color=PAL["btn_hover"],
                                border_color=PAL["border"])
        lay.addWidget(self.mode_btn)
        return h

    # ---------------------------------------------------------------- 左栏
    def _build_left(self) -> Card:
        col = Card(self, margin=(14, 14, 14, 14), spacing=10)
        col.setFixedWidth(320 + 2 * CARD_PAD)
        lay = col.layout()
        lay.addWidget(mk_label(col, "十阶段流程", size=12, bold=True,
                               color=PAL["accent"], width_px=280))
        # 步骤条放进滚动容器：窗口变矮时滚动而不是压到下面的按钮上
        self.rail_scroll = WorkScroll(col)
        self.rail = StageRail(self.rail_scroll, STAGES)
        self.rail.stageClicked.connect(self.on_stage_clicked)
        self.rail_scroll.setWidget(self.rail)
        self.rail_scroll.setMinimumHeight(180)
        lay.addWidget(self.rail_scroll, 1)
        self.left_status = mk_label(col, "", size=9, width_px=280,
                                    color=PAL["muted"])
        lay.addWidget(self.left_status)
        # 阶段导航：显式体现先后（上一阶段 / 下一阶段）
        nav = QWidget(col)
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(8)
        nl.addWidget(CButton(master=nav, text="◀ 上一阶段", width=124, height=30,
                             font_family=UI_FONT, font_size=9,
                             command=lambda: self.set_current(self.current_index() - 1),
                             background_color=PAL["btn"], text_color=PAL["text"],
                             hover_color=PAL["btn_hover"], border_color=PAL["border"]))
        nl.addWidget(CButton(master=nav, text="下一阶段 ▶", width=124, height=30,
                             font_family=UI_FONT, font_size=9,
                             command=lambda: self.set_current(self.current_index() + 1),
                             background_color=PAL["btn"], text_color=PAL["text"],
                             hover_color=PAL["btn_hover"], border_color=PAL["border"]))
        for wdg in (nl.itemAt(0).widget(), nl.itemAt(1).widget()):
            wdg.setFixedWidth(124)                # 锁死宽度，窄窗口下也不会相互重叠
        lay.addWidget(nav)
        self.btn_go = ThinkingButton(col, width=200, height=36, text="开始本阶段")
        self.btn_go.clicked.connect(self.primary_action)
        lay.addWidget(self.btn_go)
        return col

    # ---------------------------------------------------------------- 中栏
    def _build_center(self) -> Card:
        col = Card(self, margin=(14, 14, 14, 14), spacing=10)
        self.center_col = col
        lay = col.layout()

        head = QWidget(col)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        self.center_title = mk_label(head, "工作区", size=12, bold=True,
                                     color=PAL["accent"],
                                     width_px=520, wrap=True)
        hl.addWidget(self.center_title, 1)      # 占满剩余宽度，长标题不再被裁切
        self.phase_pill = mk_label(head, "等待输入", size=9, align="center", width_px=110)
        self.phase_pill.setFixedSize(110, 24)
        self.phase_pill.label().setStyleSheet(
            f"QLabel {{ background:{C('surface2')}; color:{C('muted')};"
            f" border:1px solid {C('border')}; border-radius:8px; }}")
        hl.addWidget(self.phase_pill)
        lay.addWidget(head)

        self.transcript = TranscriptView(col)
        self.transcript.setMinimumHeight(160)
        lay.addWidget(self.transcript, 1)

        self.work_scroll = WorkScroll(col)
        self.work = CFrame(self.work_scroll, border_width=0, corner_radius=0,
                           background_color="none")
        self.work.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.work_lay = self.work.layout()
        self.work_lay.setContentsMargins(0, 0, 6, 0)
        self.work_lay.setSpacing(8)
        self.work_scroll.setWidget(self.work)
        self.work_scroll.setFixedHeight(260)
        lay.addWidget(self.work_scroll, 0)
        return col

    def _work_width(self) -> int:
        """工作区可用像素宽度，用于按字体度量预估换行后的行数。"""
        w = self.center_col.width() or 720
        return max(320, w - 56)

    # ---------------------------------------------------------------- 右栏
    def _build_right(self) -> Card:
        col = Card(self, margin=(16, 10, 16, 12), spacing=7)   # 上边距收紧，给文档框让高度
        col.setFixedWidth(420 + 2 * CARD_PAD)
        self.right_col = col
        lay = col.layout()
        head = QWidget(col)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(mk_label(head, "研究设计文档", size=11, bold=True,
                              width_px=200, wrap=False))
        hl.addStretch(1)
        self.doc_meta = mk_label(head, "", size=9, align="right", width_px=160,
                                 color=PAL["muted"])
        hl.addWidget(self.doc_meta)
        lay.addWidget(head)

        self.doc_view = CTextEdit(master=col, width=380, height=560, font_family=UI_FONT,
                                  font_size=9)
        # CTextEdit 构造时既设了很大的最小尺寸、又是 Fixed 策略：
        # 必须放开最小尺寸并改为可伸缩，文档框才能撑满右栏（此前只有 266×202）
        make_flex(self.doc_view, min_w=200, min_h=180)
        self.doc_view.text_edit().setReadOnly(True)
        lay.addWidget(self.doc_view, 1)

        row = QWidget(col)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(CButton(master=row, text="导出 .md", width=104, height=32,
                             font_family=UI_FONT, font_size=9, command=self.export_md))
        rl.addWidget(CButton(master=row, text="导出 Word", width=104, height=32,
                             font_family=UI_FONT, font_size=9, command=self.export_docx,
                             tooltip="导出为 .docx：标题层级 + 检查表表格，适合伦理申请/论文附件"))
        rl.addStretch(1)
        lay.addWidget(row)
        row2 = QWidget(col)
        rl2 = QHBoxLayout(row2)
        rl2.setContentsMargins(0, 0, 0, 0)
        rl2.setSpacing(8)
        rl2.addWidget(CButton(master=row2, text="生成完整草案", width=130, height=32,
                              font_family=UI_FONT, font_size=9, command=self.finalize,
                              background_color=PAL["btn"],
                              text_color=PAL["text"],
                              hover_color=PAL["btn_hover"],
                              border_color=PAL["border"]))
        rl2.addStretch(1)
        lay.addWidget(row2)
        lay.addWidget(CButton(master=col, text="打开管线视图（评分与检查表）", width=280, height=32,
                              font_family=UI_FONT, font_size=9, command=self.show_overview,
                              background_color=PAL["btn"],
                              text_color=PAL["text"],
                              hover_color=PAL["btn_hover"],
                              border_color=PAL["border"]))
        return col

    # ---------------------------------------------------------------- 底部
    def _build_footer(self) -> CFrame:
        f = CFrame(self, layout_type="horizontal", border_width=0, corner_radius=0,
                   background_color="none")
        f.setFixedHeight(38)
        lay = f.layout()
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(12)
        # 左下角：响应动画（等待模型时橙色律动 + 计时；空闲时低调灰点）
        self.busy = BusyIndicator(f, width=300, height=30)
        lay.addWidget(self.busy, 0, Qt.AlignVCenter)
        self.status = mk_label(f, "", size=9, width_px=900, wrap=False,
                               color=PAL["muted"])
        lay.addWidget(self.status, 1)
        self.progress = ProgressBar(f, width=160, height=8)
        wrap = QWidget(f)
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wrap.setFixedSize(160, 28)
        wl.addWidget(self.progress, 0, Qt.AlignVCenter)
        lay.addWidget(wrap)
        # 提示文字固定单行：不给它换行机会，就永远不会超出 38px 的状态栏
        self.tip = mk_label(f, "Space 继续 · Ctrl+S 保存 · Ctrl+E 导出 · ⇧E 出 Word",
                            size=9, align="right", width_px=260, wrap=False,
                            color=PAL["muted"])
        self.tip.setFixedWidth(280)
        lay.addWidget(self.tip)
        return f

    # ---------------------------------------------------------------- 欢迎与文档
    def _welcome(self):
        self.transcript.add_header("工作台 · 使用说明", "accent", time.strftime("%H:%M"))
        self.transcript.add_text_block(
            "把你这门课题的初步设想贴进下方输入框（越具体越好：数据类型、例数、中心、终点、"
            "打算怎么建模）。我会先做一次速读，然后按十阶段标准流程（CLEAR / METRICS / "
            "TRIPOD+AI / IBSI）逐段推进：\n"
            "　1) 先就当前阶段提出必须澄清的问题；\n"
            "　2) 你逐条回答（可只答部分、也可写“不确定”）；\n"
            "　3) 我据此产出该阶段的改写稿与检查表；\n"
            "　4) 你采纳后写入右侧设计文档，自动进入下一阶段。\n"
            "随时可以点左侧任意阶段跳转，或在下面直接追问。\n")

    def _refresh_doc(self):
        self.doc_view.text_edit().setPlainText(self.project.render_doc())
        counts = self.project.status_counts()
        self.doc_meta.label().setText(
            f"已收录 {counts['done']}/10" if getattr(self, "_narrow", False)
            else f"已收录 {counts['done']}/10 · 待采纳 {counts['drafted']}")

    def _refresh_rail(self):
        states = {s["id"]: self.project.stage(s["id"]).get("status", "todo") for s in STAGES}
        self.rail.set_states(states, self.current_index())
        done = sum(1 for v in states.values() if v == "done")
        self.left_status.label().setText(f"已完成 {done}/10 阶段 · 点击任意阶段可跳转")
        self.progress.set_value(done / 10)

    def _refresh_all(self):
        self._refresh_rail()
        self._refresh_doc()
        self._set_phase_pill()
        self._update_status()
        if hasattr(self, "busy") and not self.busy.is_busy():
            self.busy.set_idle(self._idle_hint())
        if hasattr(self, "btn_go") and not self.btn_go.is_busy():
            self.btn_go.set_idle_text(self._primary_label())
        if hasattr(self, "body_stack"):
            idx = self.body_stack.currentIndex()
            if idx == 3:
                self.refresh_overview()
            elif idx == 2:
                self.shape_page.refresh()
            elif idx == 1:
                self.stat_page.refresh()
        if hasattr(self, "project_box"):
            self._sync_project_box()

    def _set_phase_pill(self):
        txt = PHASE_LABEL.get(self.phase, self.phase)
        col = C(status_key("运行中" if self._busy() else "todo"))
        self.phase_pill.label().setText(txt)
        self.phase_pill.label().setStyleSheet(
            f"QLabel {{ background:{C('surface2')}; color:{col};"
            f" border:1px solid {C('border')}; border-radius:8px; }}")

    def _update_status(self, extra: str = ""):
        if getattr(self, "_narrow", False):        # 窄窗口：只留项目与阶段序号
            txt = (f"项目 {self.project.name}　·　"
                   f"阶段 {self.current_index() + 1}/10")
        else:
            txt = (f"项目 {self.project.name}　·　"
                   f"阶段 {self.current_index() + 1}/10 "
                   f"{STAGES[self.current_index()]['title']}")
        self.status.label().setText(txt + (f"　·　{extra}" if extra else ""))

    def current_index(self) -> int:
        return getattr(self, "_cur", 0)

    def set_current(self, idx: int):
        self._cur = max(0, min(len(STAGES) - 1, idx))
        self._refresh_rail()
        self._update_status()

    def _busy(self) -> bool:
        return self.thread is not None and self.thread.isRunning()

    # ---------------------------------------------------------------- 项目
    def _project_names(self) -> list[str]:
        names = [f[:-5] for f in Project.list_projects()]
        if self.project.name not in names:
            names = [self.project.name] + names
        return names or ["未命名课题"]

    def _sync_project_box(self):
        names = self._project_names()
        box = self.project_box.combo_box()
        box.blockSignals(True)
        box.clear()
        box.addItems(names)
        box.setCurrentText(self.project.name)
        box.blockSignals(False)

    def _on_project_pick(self, name: str):
        if not name or name == self.project.name:
            return
        target = next((m for m in Project.list_all() if m["name"] == name), None)
        if not target:
            self._sync_project_box()
            return
        self.open_project(target["path"])

    def _flush_project(self) -> str:
        """把内存中的改动落盘（含尚未提交的原始设计输入）。"""
        if getattr(self, "_no_flush", False):
            return self.project.path_
        if self.phase == "raw" and getattr(self, "raw_box", None) is not None:
            text = self.raw_box.text_edit().toPlainText().strip()
            if text and text != self.project.raw_design:
                self.project.raw_design = text
        blank = (not self.project.exists_on_disk()
                 and not self.project.raw_design.strip()
                 and not any((self.project.shape.get(s["key"]) or {}).get("checks")
                             for s in SHAPE)
                 and not any((self.project.stat.get(s["key"]) or {}).get("checks")
                             for s in STAT_STAGES)
                 and all(self.project.stage(st["id"]).get("status", "todo") == "todo"
                         for st in STAGES))
        if blank:
            return ""                      # 空项目不建文件，避免产生一堆空副本
        return self.project.save()

    def open_project(self, path: str, announce: bool = True):
        if not path or not os.path.exists(path):
            self._toast("项目文件不存在")
            return
        if os.path.abspath(path) == os.path.abspath(self.project.path):
            return
        self._flush_project()
        self._switch_project(Project.load(path), announce=announce)

    def _switch_project(self, project: Project, announce: bool = True):
        self.project = project
        self.agent = DesignAgent(self.client, project)
        self.pending_draft = ""
        self.transcript.clear()
        self._welcome()
        st_done = project.status_counts()["done"]
        if announce:
            self.transcript.add_header(f"已打开项目「{project.name}」", "accent",
                                       f"{st_done}/10 阶段已收录")
        # 恢复上次未完成的阶段与输入态
        nxt_id = next((s["id"] for s in STAGES
                       if project.stage(s["id"]).get("status") != "done"), STAGES[0]["id"])
        nxt = max(0, nxt_id - 1)
        self.set_current(nxt)
        st = project.stage(STAGES[nxt]["id"])
        if st.get("status") == "drafted" and st.get("draft"):
            self.phase = "draft"
            self.show_draft(st["draft"])
        elif st.get("status") == "asked" and st.get("questions"):
            self.phase = "answer"
            self.show_answers(st["questions"])
        elif project.raw_design.strip():
            self.phase = "idle"
            self.transcript.add_text_block("研究设想：\n" + project.raw_design.strip() + "\n")
            self.show_free_input()
        else:
            self.phase = "raw"
            self.show_raw_input()
        self._refresh_all()
        self._toast(f"当前项目：{project.name}")

    def manage_projects(self):
        dlg = ProjectManagerDialog(self, self.project.path if self.project.exists_on_disk() else "")
        dlg.openRequested.connect(self.open_project)
        dlg.createRequested.connect(self.new_project)
        dlg.renamed.connect(self.rename_project_file)
        dlg.duplicated.connect(self.duplicate_project_file)
        dlg.deleteRequested.connect(self.delete_project_file)
        self._pm_dlg = dlg                      # 保留引用，避免被回收
        dlg.show()

    def rename_project_file(self, path: str, new_name: str):
        if os.path.abspath(path) == os.path.abspath(self.project.path):
            self.project.rename(new_name)
            self._refresh_all()
            self._toast(f"已重命名为「{self.project.name}」")
            return
        proj = Project.load(path)
        proj.rename(new_name)
        self._toast(f"已重命名：{proj.name}")

    def duplicate_project_file(self, path: str, new_name: str):
        proj = Project.load(path)
        copy = proj.duplicate(new_name)
        self._toast(f"已创建副本「{copy.name}」")
        if hasattr(self, "project_box"):
            self._sync_project_box()

    def delete_project_file(self, path: str):
        was_current = os.path.abspath(path) == os.path.abspath(self.project.path)
        proj = Project.load(path)
        ok = proj.delete()
        self._toast(f"已删除「{proj.name}」" if ok else "删除失败（文件可能被占用）")
        if was_current:
            self._blank_project()          # 换成空白项目，且不立刻落盘

    def rename_current_project(self):
        """一级界面：给当前项目改名（同步移动项目文件，重名自动加 (2)）。"""
        dlg = PromptDialog(self, "重命名项目", "新名称：", self.project.name,
                           placeholder="例如：课题_胰腺囊性病变")
        dlg.submitted.connect(lambda d: self._rename_current(d["name"]))
        self._prompt_dlg = dlg                      # 保留引用，避免被回收
        dlg.show()

    def _rename_current(self, new_name: str):
        new_name = (new_name or "").strip()
        if not new_name or new_name == self.project.name:
            return
        old = self.project.name
        self.project.rename(new_name)               # 内部处理文件移动与重名后缀
        self._refresh_all()
        self._sync_project_box()
        self._toast(f"「{old}」已改名为「{self.project.name}」")

    def delete_current_project(self):
        """一级界面：删除当前项目（二次确认）。"""
        saved = self.project.exists_on_disk()
        msg = (f"确定删除当前项目「{self.project.name}」吗？\n"
               + ("项目文件会一并删除，且不可恢复。" if saved
                  else "该项目尚未保存到磁盘，将直接清空当前工作区。"))
        dlg = ConfirmDialog(self, "删除项目", msg, ok_text="确认删除")
        dlg.confirmed.connect(self._delete_current)
        self._confirm_dlg = dlg                     # 保留引用，避免被回收
        dlg.show()

    def _delete_current(self):
        name = self.project.name
        if self.project.exists_on_disk():
            self.delete_project_file(self.project.path)     # 删除文件并换成空白项目
        else:
            self._blank_project()
            self._toast(f"已清空「{name}」")

    def _blank_project(self):
        """换成空白项目，但**不落盘**——空项目在写入内容前不产生文件（沿用原有约定）。"""
        fresh = Project(name=f"课题_{time.strftime('%m%d_%H%M')}", model=self.client.model)
        self._switch_project(fresh, announce=False)
        self.phase = "raw"

    def new_project(self, confirm: bool = True):
        if confirm:
            dlg = PromptDialog(self, "新建项目", "项目名称：",
                               f"课题_{time.strftime('%m%d_%H%M')}",
                               with_text=True, text_label="初步实验设计（可稍后再填）：",
                               placeholder="例如：课题_胰腺囊性病变")
            dlg.submitted.connect(lambda d: self._create_project(d["name"], d.get("text", "")))
            self._prompt_dlg = dlg               # 保留引用
            dlg.show()
            return
        self._create_project(f"课题_{time.strftime('%m%d_%H%M')}", "")

    def _create_project(self, name: str, raw: str = ""):
        try:
            self._flush_project()
        except Exception:                                          # noqa: BLE001
            pass
        project = Project.new(name, raw=raw, model=self.client.model)
        self._switch_project(project, announce=False)
        self.phase = "raw" if not raw.strip() else "idle"
        if raw.strip():
            self.transcript.add_text_block("研究设想：\n" + raw.strip() + "\n")
            self.show_free_input()
            self.set_current(0)
            self.run_ask(0)
        else:
            self.show_raw_input()
        self._refresh_all()
        self._toast(f"已新建项目「{project.name}」（{os.path.basename(project.path)}）")

    def save_project(self):
        p = self._flush_project()
        self.tip.label().setText(f"已保存 → {os.path.basename(p)}")

    def closeEvent(self, event):
        try:
            self._flush_project()
        except Exception:                                          # noqa: BLE001
            pass
        # 关闭时若仍有后台请求在跑，先等它结束，否则 Qt 会因线程未回收而中止进程
        for th in (getattr(self, "thread", None), getattr(self, "_ml", None)):
            if th is not None and th.isRunning():
                th.requestInterruption()
                if not th.wait(6000):
                    th.terminate()
                    th.wait(1000)
        super().closeEvent(event)

    def open_settings(self):
        dlg = SettingsDialog(self, self.cfg)
        dlg.saved.connect(self._apply_settings)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.show()

    def _apply_settings(self, cfg: dict):
        self.cfg = cfg
        self.client = LLMClient(cfg)
        self.agent = DesignAgent(self.client, self.project)
        self.model_box.combo_box().blockSignals(True)
        self.model_box.combo_box().clear()
        self.model_box.combo_box().addItem(cfg["model"])
        self.model_box.combo_box().setCurrentText(cfg["model"])
        self.model_box.combo_box().blockSignals(False)
        self._update_status("设置已更新")

    def _fetch_models(self):
        self._ml = ModelListThread(self.client, self)
        self._ml.done.connect(self._on_models)
        self._ml.start()

    def _on_models(self, models: list):
        if not models:
            return
        cur = self.client.model
        self.model_box.combo_box().blockSignals(True)
        self.model_box.combo_box().clear()
        self.model_box.combo_box().addItems(models)
        self.model_box.combo_box().setCurrentText(cur if cur in models else models[0])
        self.model_box.combo_box().blockSignals(False)

    def _on_model_pick(self, name: str):
        if not name or name == self.client.model:
            return
        self.cfg["model"] = name
        save_config(self.cfg)
        self.client = LLMClient(self.cfg)
        self.agent = DesignAgent(self.client, self.project)
        self._update_status(f"已切换模型 {name}")

    # ---------------------------------------------------------------- 模式切换
    def toggle_mode(self):
        mode = "light" if ModeManager.mode != "light" else "dark"
        set_appearance_mode(mode)
        self.mode_btn.button().setText("深色" if mode == "light" else "浅色")
        self.setWindowBackground(PAL["bg"])
        self._apply_root_bg()                      # 只给顶层上底色，子控件透明
        self.update()                              # 底衬渐变随主题重绘
        for w in self.findChildren(QWidget):
            fn = getattr(w, "_change_theme", None)
            if callable(fn):
                try:
                    fn()
                except Exception:                                  # noqa: BLE001
                    pass
        if hasattr(self, "body_stack"):
            idx = self.body_stack.currentIndex()
            if idx == 3:
                self.refresh_overview()
            elif idx == 2:
                self.shape_page.refresh()
            elif idx == 1:
                self.stat_page.refresh()
        if hasattr(self, "phase_pill"):
            self._set_phase_pill()      # 阶段胶囊为自定义样式，切主题后需重新套用
    def _clear_work(self):
        clear_layout(self.work_lay)
        self.answer_rows = []
        if hasattr(self, "work_scroll"):
            self.work_scroll.setFixedHeight(220)

    def show_raw_input(self):
        self._clear_work()
        self._draft_stage = None
        self.raw_box = CTextEdit(master=self.work, width=800, height=150, font_family=UI_FONT,
                                 font_size=10,
                                 placeholder_text="例如：回顾性收集 2015–2023 年两家医院经手术病理证实的"
                                                  "胰腺囊性病变患者，术前行增强 CT，计划提取影像组学特征"
                                                  "预测恶性潜能，并用囊液蛋白组解释模型……")
        self.raw_box.setMinimumSize(240, 120)
        make_flex(self.raw_box, min_w=240, min_h=120)      # 撑满中栏宽度
        self.work_lay.addWidget(self.raw_box)
        row = QWidget(self.work)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        _n = getattr(self, "_narrow", False)
        rl.addWidget(CButton(master=row, text="开始分析",
                             width=140, height=34,
                             font_family=UI_FONT, font_size=10, command=self.start_analysis))
        rl.addWidget(CButton(master=row, text="载入示例", width=100, height=34,
                             font_family=UI_FONT, font_size=9, command=self.load_sample,
                             background_color=PAL["btn"],
                             text_color=PAL["text"],
                             hover_color=PAL["btn_hover"],
                             border_color=PAL["border"]))
        rl.addStretch(1)
        self.work_lay.addWidget(row)
        self.center_title.label().setText("① 输入初步实验设计")
        fit_height(self.work_scroll, 150 + 52, lo=210, hi=300)

    def show_answers(self, questions: list):
        self._clear_work()
        self._draft_stage = None
        self.center_title.label().setText("② 回答追问（问题已完整显示，可只答部分）")
        W = self._work_width()
        total = 0

        for i, q in enumerate(questions):
            block = QWidget(self.work)
            bl = QVBoxLayout(block)
            bl.setContentsMargins(0, 8 if i else 0, 0, 0)
            bl.setSpacing(4)

            # 问题本体：编号 + 完整问题（自动换行）
            head = QWidget(block)
            hl = QHBoxLayout(head)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(8)
            tag = mk_label(head, f"Q{i + 1}", size=10, bold=True, width_px=32,
                           color=PAL["accent"])
            tag.setFixedWidth(32)
            hl.addWidget(tag)
            qlabel = mk_label(head, q["q"], size=11, width_px=W - 40, wrap=True)
            hl.addWidget(qlabel, 1)
            bl.addWidget(head)
            total += qlabel.height() + 4

            # 为什么问
            if q.get("why"):
                wlabel = mk_label(block, "为什么问：" + q["why"], size=9,
                                  width_px=W - 40, wrap=True,
                                  color=PAL["muted"])
                bl.addWidget(wlabel)
                total += wlabel.height() + 2

            # 回答输入：多行、自动换行，能看到自己写的全部内容（固定高度，避免被拉伸）
            box = CTextEdit(master=block, width=W - 40, height=60, font_family=UI_FONT,
                            font_size=10, text="",
                            placeholder_text="在此作答；不确定可写“不确定，按常规做法给建议值”")
            box.setFixedHeight(62)
            make_flex(box, min_w=200, min_h=52, vertical="fixed")   # 宽度撑满，高度固定
            box.text_edit().setFixedHeight(52)      # 内层也固定，避免被布局拉伸
            # 只在点击时取焦点，否则 QScrollArea 会自动把最后一个输入框滚进视野
            box.text_edit().setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            bl.addWidget(box)
            total += 68
            self.answer_rows.append(box)
            self.work_lay.addWidget(block)          # 每个问题一个块，必须逐个加入布局

        total += 60

        row = QWidget(self.work)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 6, 0, 0)
        rl.setSpacing(10)
        _n = getattr(self, "_narrow", False)
        rl.addWidget(CButton(master=row, text="提交回答",
                             width=120, height=34,
                             font_family=UI_FONT, font_size=10, command=self.submit_answers))
        rl.addWidget(CButton(master=row, text="跳过本阶段",
                             width=110, height=34,
                             font_family=UI_FONT, font_size=9, command=self.skip_stage,
                             background_color=PAL["btn"],
                             text_color=PAL["text"],
                             hover_color=PAL["btn_hover"],
                             border_color=PAL["border"]))
        rl.addStretch(1)
        self.work_lay.addWidget(row)
        total += 44
        # 尽量让全部问题一屏可见：可用高度 = 中栏高度 − 标题 − 对话区最小高度
        avail = max(240, (self.center_col.height() or 780) - 250)
        fit_height(self.work_scroll, total + 20, lo=200, hi=min(600, avail))
        # 焦点若停在回答框上，QScrollArea 会自动把它滚进视野 → 这里把焦点移走并复位滚动条
        for w in self.answer_rows:
            w.text_edit().clearFocus()
        self.transcript.setFocus()
        for delay in (0, 120, 350):
            QtCore.QTimer.singleShot(delay, self._scroll_work_top)

    def _scroll_work_top(self):
        try:
            self.work_scroll.verticalScrollBar().setValue(0)
        except Exception:                                          # noqa: BLE001
            pass

    def show_draft(self, draft: str):
        self._clear_work()
        self.center_title.label().setText("③ 审阅改写稿（可编辑后采纳）")
        self.draft_box = CTextEdit(master=self.work, width=800, height=150, font_family=UI_FONT,
                                   font_size=10, text=draft)
        self.draft_box.setMinimumSize(240, 120)
        make_flex(self.draft_box, min_w=240, min_h=120)    # 撑满中栏宽度
        self.work_lay.addWidget(self.draft_box)
        row = QWidget(self.work)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        _n = getattr(self, "_narrow", False)
        rl.addWidget(CButton(master=row, text="采纳并收录",
                             width=120, height=34,
                             font_family=UI_FONT, font_size=10, command=self.accept_draft))
        rl.addWidget(CButton(master=row, text="重新生成", width=96, height=34,
                             font_family=UI_FONT, font_size=9, command=self.regenerate,
                             background_color=PAL["btn"],
                             text_color=PAL["text"],
                             hover_color=PAL["btn_hover"],
                             border_color=PAL["border"]))
        rl.addWidget(CButton(master=row, text="跳过本阶段",
                             width=110, height=34,
                             font_family=UI_FONT, font_size=9, command=self.skip_stage,
                             background_color=PAL["btn"],
                             text_color=PAL["text"],
                             hover_color=PAL["btn_hover"],
                             border_color=PAL["border"]))
        rl.addStretch(1)
        self.work_lay.addWidget(row)
        fit_height(self.work_scroll, 200 + 52, lo=240, hi=380)

    def show_free_input(self):
        self._clear_work()
        self.center_title.label().setText("随时追问 agent")
        row = QWidget(self.work)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        self._draft_stage = None
        self.free_edit = CLineEdit(master=row, width=700, height=32, font_family=UI_FONT,
                                   font_size=9, placeholder_text="针对当前阶段追问，例如："
                                                                 "外部验证需要多少例才够？")
        rl.addWidget(self.free_edit, 1)
        rl.addWidget(CButton(master=row, text="发送", width=80, height=32, font_family=UI_FONT,
                             font_size=9, command=self.send_free))
        self.work_lay.addWidget(row)
        fit_height(self.work_scroll, 88, lo=100, hi=140)

    # ---------------------------------------------------------------- 主流程
    def primary_action(self):
        if self.phase == "raw":
            self.start_analysis()
        elif self.phase in ("answer",):
            self.submit_answers()
        elif self.phase == "draft":
            self.accept_draft()
        elif self.phase in ("idle", "todo"):
            self.run_ask(self.current_index())

    def load_sample(self):
        self.raw_box.text_edit().setPlainText(
            "回顾性收集 2015 年 1 月至 2023 年 6 月在我院行手术切除、术后病理证实的胰腺囊性病变"
            "（PCL）患者，术前行上腹部增强 CT。计划在门静脉期图像上手工勾画囊性病灶、胰腺与"
            "非病灶区域，用 PyRadiomics 提取影像组学特征，比较 LASSO、随机森林等模型预测"
            "恶性潜能（高级别异型增生 / 浸润癌）的效能，并在另一家医院做外部验证；"
            "同时前瞻性留取囊液做蛋白组与脂质组，解释模型背后的生物学机制。"
            "预计纳入约 300 例，外部验证约 60 例。")

    def start_analysis(self):
        raw = self.raw_box.text_edit().toPlainText().strip()
        if len(raw) < 20:
            self._toast("请先贴入初步实验设计描述（至少 20 字）")
            return
        self.project.raw_design = raw
        self.save_project()
        self.phase = "kickoff"
        self._set_phase_pill()
        self.transcript.add_rule()
        self.transcript.add_header("速读", "agent", f"{time.strftime('%H:%M')} · {self.client.model}")
        self._run(self.agent.kickoff_messages(), on_done=self._after_kickoff)

    def _after_kickoff(self, out: dict):
        sec = parse_sections(out["content"])
        focus = pick(sec, "首要关注点")
        self.phase = "idle"
        self._refresh_all()
        self.show_free_input()
        if focus:
            self.transcript.add_html(f"<div style='margin-top:6px;'><b>首要关注点</b></div>")
            self.transcript.add_text_block(focus + "\n")
        self.set_current(0)
        self.run_ask(0)

    def run_ask(self, idx: int):
        if self._busy():
            return
        self.set_current(idx)
        st = self.project.stage(STAGES[idx]["id"])
        self.phase = "ask"
        self._set_phase_pill()
        self.transcript.add_rule()
        self.transcript.add_header(f"阶段 {STAGES[idx]['id']:02d} · {STAGES[idx]['title']}｜追问",
                                   "agent", f"{time.strftime('%H:%M')}")
        self._run(self.agent.ask_messages(STAGES[idx]["id"]),
                  on_done=lambda out: self._after_ask(idx, out))

    def _after_ask(self, idx: int, out: dict):
        st = self.project.stage(STAGES[idx]["id"])
        sec = parse_sections(out["content"])
        st["assessment"] = pick(sec, "现状评估")
        st["questions"] = parse_questions(pick(sec, "必须澄清", "问题"))
        st["answers"] = ["" for _ in st["questions"]]
        st["status"] = "asked"
        st["model"] = out.get("model", "")
        st["updated"] = time.strftime("%H:%M")
        self.phase = "answer"
        self._refresh_all()
        self.show_answers(st["questions"])
        self.save_project()

    @staticmethod
    def _answer_text(widget) -> str:
        """回答输入框可能是多行 CTextEdit 或单行 CLineEdit。"""
        if hasattr(widget, "text_edit"):
            return widget.text_edit().toPlainText().strip()
        if hasattr(widget, "line_edit"):
            return widget.line_edit().text().strip()
        return ""

    @staticmethod
    def _set_answer(widget, text: str):
        if hasattr(widget, "text_edit"):
            widget.text_edit().setPlainText(text)
        elif hasattr(widget, "line_edit"):
            widget.line_edit().setText(text)

    def submit_answers(self):
        if not self.answer_rows:
            return
        st = self.project.stage(STAGES[self.current_index()]["id"])
        st["answers"] = [self._answer_text(e) for e in self.answer_rows]
        self.transcript.add_header("研究者回答", "user", time.strftime("%H:%M"))
        lines = [f"{i + 1}. {q_text(q)}\n　→ {a or '（未回答，按常规做法给建议值）'}"
                 for i, (q, a) in enumerate(zip(st["questions"], st["answers"]))]
        self.transcript.add_text_block("\n".join(lines) + "\n")
        self.save_project()
        self.run_rewrite()

    def run_rewrite(self):
        idx = self.current_index()
        self.phase = "rewrite"
        self._set_phase_pill()
        self.transcript.add_header(f"阶段 {STAGES[idx]['id']:02d} · 改写稿", "agent",
                                   time.strftime("%H:%M"))
        self._run(self.agent.rewrite_messages(STAGES[idx]["id"]),
                  on_done=lambda out: self._after_rewrite(idx, out))

    def _after_rewrite(self, idx: int, out: dict):
        st = self.project.stage(STAGES[idx]["id"])
        sec = parse_sections(out["content"])
        draft = pick(sec, "改写稿")
        st["draft"] = draft
        st["risks"] = pick(sec, "风险提示")
        st["checklist"] = parse_checklist(pick(sec, "检查表"))
        st["next"] = pick(sec, "下一步")
        st["status"] = "drafted"
        st["updated"] = time.strftime("%H:%M")
        self.pending_draft = draft
        self._draft_stage = idx
        self.phase = "draft"
        self._refresh_all()
        self.show_draft(draft)
        self.save_project()

    def accept_draft(self):
        idx = self.current_index()
        box = getattr(self, "draft_box", None)
        if box is None or getattr(self, "_draft_stage", None) != idx:
            # 工作区里的稿子不属于当前阶段（例如上一阶段的稿子还留在框里）→ 拒绝收录
            self._toast("当前阶段没有待采纳的改写稿，请先「重新生成」")
            return
        text = box.text_edit().toPlainText().strip()
        st = self.project.stage(STAGES[idx]["id"])
        st["final"] = text
        st["status"] = "done"
        self.save_project()
        self._refresh_all()
        self.transcript.add_header(f"✓ 已收录阶段 {STAGES[idx]['id']:02d} 改写稿", "ok",
                                   time.strftime("%H:%M"))
        nxt = idx + 1
        if nxt < len(STAGES):
            self.run_ask(nxt)
        else:
            self.transcript.add_header("十个阶段已全部推进完毕", "accent")
            self.transcript.add_text_block(
                "可以点右侧「生成完整草案」，把各阶段定稿整合成一份研究设计草案与待补数据清单；"
                "也可以随时回到任一阶段重新打磨。\n")
            self.phase = "idle"
            self.show_free_input()
            self._refresh_all()
            self.save_project()

    def skip_stage(self):
        idx = self.current_index()
        st = self.project.stage(STAGES[idx]["id"])
        if st.get("status") == "todo":
            st["status"] = "todo"
        self.phase = "idle"
        self.transcript.add_text_block(f"（已跳过阶段 {STAGES[idx]['id']:02d}）\n")
        if idx + 1 < len(STAGES):
            self.run_ask(idx + 1)
        else:
            self.show_free_input()
            self._refresh_all()

    def regenerate(self):
        if self.phase == "draft":
            self.run_rewrite()
        else:
            self.run_ask(self.current_index())

    def on_stage_clicked(self, idx: int):
        if self._busy():
            self._toast("正在生成中，稍候…")
            return
        self.set_current(idx)
        st = self.project.stage(STAGES[idx]["id"])
        if st.get("status") == "drafted" and st.get("draft"):
            self.phase = "draft"
            self.show_draft(st["draft"])
        elif st.get("status") == "asked" and st.get("questions"):
            self.phase = "answer"
            self.show_answers(st["questions"])
        elif st.get("status") == "done":
            self.phase = "idle"
            self.show_free_input()
            self.transcript.add_header(f"阶段 {STAGES[idx]['id']:02d} 已收录", "ok")
            self.transcript.add_text_block((st.get("final") or "") + "\n")
        else:
            self.run_ask(idx)

    def send_free(self):
        q = self.free_edit.line_edit().text().strip()
        if not q or self._busy():
            return
        self.free_edit.line_edit().clear()
        idx = self.current_index()
        self.transcript.add_header("我的追问", "user", time.strftime("%H:%M"))
        self.transcript.add_text_block(q + "\n")
        self.transcript.add_header("agent", "agent", "")
        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"【研究者的初步设计描述】\n{self.project.raw_design}\n\n"
                f"【已完成阶段定稿】\n{self.project.done_summary()}\n\n"
                f"【当前阶段】{STAGES[idx]['id']:02d} {STAGES[idx]['title']}（{STAGES[idx]['spec']}）\n\n"
                f"研究者的追问：{q}\n\n请直接回答，200 字以内，给出可执行建议与规范依据。"},
        ]
        self._run(msgs, on_done=lambda out: None)

    def finalize(self):
        if self._busy():
            return
        self.phase = "final"
        self._set_phase_pill()
        self.transcript.add_rule()
        self.transcript.add_header("汇总 · 完整设计草案", "agent", time.strftime("%H:%M"))
        self._run(self.agent.finalize_messages(), on_done=self._after_final, max_tokens=14000)

    def _after_final(self, out: dict):
        sec = parse_sections(out["content"])
        self.project.final_doc = pick(sec, "设计草案") or out["content"]
        extra = []
        if pick(sec, "待补数据"):
            extra.append("【待补数据清单】\n" + pick(sec, "待补数据"))
        if pick(sec, "投稿前自查"):
            extra.append("【投稿前自查】\n" + pick(sec, "投稿前自查"))
        if extra:
            self.transcript.add_text_block("\n" + "\n\n".join(extra) + "\n")
        self.phase = "idle"
        self.show_free_input()
        self.save_project()
        self._refresh_all()
        self._toast("已生成完整草案，可在右侧导出")

    # ---------------------------------------------------------------- 线程
    def _run(self, messages: list, on_done, max_tokens: int | None = None, view=None,
             reason: bool = False):
        """跑一次 LLM 调用；view 指定流式输出落到哪个对话视图（默认工作台）。

        reason=True 走推理模式：模型输出正文的同时会把推理过程单独流式推送
        （kind == "reasoning"），这里用弱化色显示，便于看清结论是怎么推出来的。
        """
        if self._busy():
            return
        tv = view or self.transcript
        holder = {"text": "", "reason": ""}

        def on_delta(piece: str, kind: str):
            if kind == "reasoning":
                holder["reason"] += piece
                tv.stream(piece, "muted")          # 推理过程用弱化色
                return
            holder["text"] += piece
            if kind == "content":
                tv.stream(piece)

        self.thread = LLMThread(self.client, messages, stream=True, parent=self,
                                max_tokens=max_tokens, reason=reason)
        self.thread.delta.connect(on_delta)
        self.thread.failed.connect(self._on_failed)

        def finished(out: dict):
            self.thread = None                     # 先释放，避免后续链条被 busy 挡掉
            tv.end_stream()
            out["content"] = out.get("content") or holder["text"]
            out["reasoning"] = out.get("reasoning") or holder["reason"]
            if not holder["text"].strip() and out["content"].strip():
                tv.add_text_block(out["content"])   # 重试后的整段补显
            usage = out.get("usage") or {}
            self._set_busy_ui(False)
            self._update_status(
                f"{out['elapsed']:.1f}s · tokens {usage.get('total_tokens', '—')}"
                f"（推理 {usage.get('completion_tokens_details', {}).get('reasoning_tokens', '—')}）"
                + ("· 已自动重试" if out.get("retried") else ""))
            QtCore.QTimer.singleShot(0, lambda: on_done(out))   # 脱离信号回调栈再续流程

        self.thread.finished_ok.connect(finished)
        self._set_busy_ui(True)
        self.thread.start()

    def _on_failed(self, msg: str):
        self.thread = None
        self.transcript.end_stream()
        self._set_busy_ui(False)
        self.transcript.add_header("调用失败", "bad")
        self.transcript.add_text_block(f"{msg}\n"
                                       "可点右上「设置」检查 Base URL / API Key，或换一个模型重试。\n")
        self._update_status("调用失败")

    def _set_busy_ui(self, busy: bool):
        # 主按钮在思考时变为动画（旋转弧线 + 省略号 + 流光条）
        if busy:
            self.btn_go.start("正在思考")
        else:
            self.btn_go.stop(self._primary_label())
        self.btn_go.setEnabled(not busy)
        self._set_phase_pill()
        if hasattr(self, "busy"):
            if busy:
                self.busy.start(PHASE_LABEL.get(self.phase, "正在生成"))
            else:
                self.busy.stop(self._idle_hint())
        if not busy:
            QApplication.processEvents()

    def _apply_responsive(self):
        """按窗口宽度收缩左右两栏，保证中栏与按钮行不被挤压。"""
        w = self.width()
        if not hasattr(self, "left_col"):
            return
        narrow = w < 1420
        pad2 = 2 * CARD_PAD                       # 卡片投影预留量（外形尺寸补偿）
        self.left_col.setFixedWidth((292 if narrow else 320) + pad2)
        if hasattr(self, "side_col"):
            self.side_col.setFixedWidth((322 if narrow else 420) + pad2)
        for page in (getattr(self, "stat_page", None), getattr(self, "shape_page", None)):
            if page is not None:
                page.left.setFixedWidth((292 if narrow else 320) + pad2)
                page.side.setFixedWidth((340 if narrow else 384) + pad2)
                page.refit_all()                   # 宽度变了 → 立即重算换行高度
        if hasattr(self, "header"):
            self.header.setFixedHeight((124 if narrow else 108) + pad2)
            self.header.layout().setSpacing(6 if narrow else 10)
        # 窄窗口：隐去「项目 / 模型」这两个说明标签，腾出空间给新建/重命名/删除/管理
        for nm in ("_lbl_project", "_lbl_model"):
            wdg = getattr(self, nm, None)
            if wdg is not None:
                wdg.setVisible(not narrow)
        if hasattr(self, "titles"):
            self.titles.setMinimumWidth(300)        # 保证标题块不被压扁（否则文字互相重叠）
        if hasattr(self, "subtitle"):
            self.subtitle.label().setText(
                "十阶段逐段追问与改写" if narrow
                else "贴入初步设想 → 十阶段逐段追问与改写 → 输出可执行研究设计")
            self.subtitle.fit_now()
        for name, wd in (("search", 150 if narrow else 210),
                         ("project_box", 132 if narrow else 190),
                         ("model_box", 140 if narrow else 190),
                         ("new_btn", 48 if narrow else 64),
                         ("rename_btn", 48 if narrow else 64),
                         ("delete_btn", 48 if narrow else 64),
                         ("manage_btn", 48 if narrow else 64),
                         ("settings_btn", 48 if narrow else 64),
                         ("mode_btn", 48 if narrow else 64)):
            wdg = getattr(self, name, None)
            if wdg is not None:
                wdg.setFixedWidth(wd)
        # 页脚提示按可用宽度切换长短，避免单行文字放不下（单行标签不会换行）
        if hasattr(self, "tip"):
            if w < 1420:
                self.tip.setFixedWidth(196)
                self.tip.label().setText("Space 继续 · Ctrl+S 保存")
            elif w < 1700:
                self.tip.setFixedWidth(246)
                self.tip.label().setText("Space 继续 · Ctrl+S 保存 · Ctrl+E 导出")
            else:
                self.tip.setFixedWidth(300)
                self.tip.label().setText("Space 继续 · Ctrl+S 保存 · Ctrl+E 导出 · ⇧E 出 Word")
        if narrow != getattr(self, "_narrow", None):
            self._narrow = narrow
            self._refresh_doc()                 # 元信息文案随宽度切换，避免换行被截
        else:
            self._narrow = narrow

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive()

    def _change_theme(self):
        """CMainWindow 会在主题/调色板变化时重写全局 `QWidget{…}`，
        这里立刻收回作用域，否则子容器又会被涂上底色方块。"""
        super()._change_theme()
        self._apply_root_bg()

    def _apply_root_bg(self):
        """把窗口底色限定在顶层自身。

        PyCt6 的 setWindowBackground 会写 `QWidget { background-color: … }`，
        该规则会命中**所有**子控件，于是标题块、行容器等会在三维卡片上留下一个个
        浅色方块。这里改成只命中顶层（#studioRoot），子控件一律透明。
        """
        self.setObjectName("studioRoot")
        self.setStyleSheet(f"QWidget#studioRoot {{ background-color: {C('bg')}; }}")
        # 纯容器一律不画样式表底色：PyCt6 的全局规则会给它们带上 WA_StyledBackground，
        # 于是在三维卡片上留下一块块浅色方块（标题块、按钮行等）。
        for w in self.findChildren(QtWidgets.QWidget):
            if type(w) is QtWidgets.QWidget:
                w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def paintEvent(self, event):
        """页面底衬：中心亮、边缘暗的径向渐变，给整个界面一层纵深。"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        draw_backdrop(p, QRectF(self.rect()))

    def _idle_hint(self) -> str:
        """空闲时左下角显示的小字提示。"""
        if self._busy():
            return "正在生成"
        if self.phase == "answer":
            return "等待你的回答"
        if self.phase == "draft":
            return "等待采纳改写稿"
        if self.phase == "raw":
            return "等待输入实验设计"
        return "就绪 · 可随时追问"

    def _primary_label(self) -> str:
        """主按钮在空闲态显示的动作名（跟随当前阶段）。"""
        return {"raw": "开始分析", "answer": "提交回答",
                "draft": "采纳并收录"}.get(self.phase, "开始本阶段")

    # ---------------------------------------------------------------- 导出/其它
    def _load_prefs(self) -> dict:
        """界面偏好（记住上次导出目录），存 data_path/ui_prefs.json。"""
        if not hasattr(self, "_prefs"):
            try:
                with open(data_path("ui_prefs.json"), encoding="utf-8") as fh:
                    self._prefs = json.load(fh)
            except Exception:                                      # noqa: BLE001
                self._prefs = {}
        return self._prefs

    def _save_prefs(self) -> None:
        try:
            with open(data_path("ui_prefs.json"), "w", encoding="utf-8") as fh:
                json.dump(getattr(self, "_prefs", {}), fh, ensure_ascii=False, indent=1)
        except Exception:                                          # noqa: BLE001
            pass

    def export_md(self):
        """导出 Markdown：弹保存对话框让用户选路径（默认落在文档目录、记住上次位置）。"""
        from app_paths import export_dir
        name = f"研究设计_{self.project.name}.md"
        prefs = self._load_prefs()
        start_dir = prefs.get("last_export_dir") or export_dir()
        if not os.path.isdir(start_dir):
            start_dir = export_dir()
        default = os.path.join(start_dir, name)

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出研究设计文档（Markdown）", default,
            "Markdown 文档 (*.md);;所有文件 (*)")
        if not path:                                               # 用户取消
            self._toast("已取消导出")
            return
        if not path.lower().endswith(".md"):
            path += ".md"                                          # 没写扩展名就补上

        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.project.render_doc())
        except Exception as e:                                     # noqa: BLE001
            self._toast(f"导出失败：{e}")
            self.status.label().setText(f"导出失败：{e}")
            return

        prefs["last_export_dir"] = os.path.dirname(path)
        self._save_prefs()
        self._toast(f"已导出 → {path}")
        self.status.label().setText(f"已导出 Markdown：{path}")

    def export_docx(self):
        """导出 Word（.docx）：标题层级 + 检查表表格，弹对话框让用户选路径。"""
        from app_paths import export_dir
        name = f"研究设计_{self.project.name}.docx"
        prefs = self._load_prefs()
        start_dir = prefs.get("last_export_dir") or export_dir()
        if not os.path.isdir(start_dir):
            start_dir = export_dir()
        default = os.path.join(start_dir, name)

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出研究设计文档（Word）", default, "Word 文档 (*.docx);;所有文件 (*)")
        if not path:
            self._toast("已取消导出")
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"

        try:
            import docx_export
            path = docx_export.build(self.project, path)
        except Exception as e:                                     # noqa: BLE001
            self._toast(f"导出 Word 失败：{e}")
            self.status.label().setText(f"导出 Word 失败：{e}")
            return

        prefs["last_export_dir"] = os.path.dirname(path)
        self._save_prefs()
        self._toast(f"已导出 Word → {path}")
        self.status.label().setText(f"已导出 Word：{path}")

    def open_pipeline(self):
        try:
            subprocess.Popen([sys.executable, os.path.join(HERE, "omics_pipeline.py")])
            self._toast("已打开管线视图（评分与检查表）")
        except Exception as e:                                     # noqa: BLE001
            self._toast(f"打开失败：{e}")

    def _toast(self, text: str):
        self.tip.label().setText(text)

    # ---------------------------------------------------------------- 键盘
    def keyPressEvent(self, event):
        k = event.key()
        mod = event.modifiers()
        focus = getattr(self, "free_edit", None)
        typing = focus is not None and focus.hasFocus()
        if k == Qt.Key.Key_Space and not typing:
            self.primary_action()
        elif k == Qt.Key.Key_Down:
            self.set_current(self.current_index() + 1)
        elif k == Qt.Key.Key_Up:
            self.set_current(self.current_index() - 1)
        elif k == Qt.Key.Key_S and mod & Qt.KeyboardModifier.ControlModifier:
            self.save_project()
        elif k == Qt.Key.Key_E and mod & Qt.KeyboardModifier.ControlModifier:
            if mod & Qt.KeyboardModifier.ShiftModifier:
                self.export_docx()                 # Ctrl+Shift+E → Word
            else:
                self.export_md()                   # Ctrl+E → Markdown
        else:
            super().keyPressEvent(event)

    # ---------------------------------------------------------------- 演示数据
    def _load_demo(self):
        self._no_flush = True          # 演示/截图用，不写入 projects/
        self.project = Project(name="demo_胰腺囊性病变", model=self.client.model)
        self.project.raw_design = (
            "回顾性收集 2015–2023 年我院手术病理证实的胰腺囊性病变患者，术前门静脉期增强 CT，"
            "勾画病灶 / 胰腺 / 非病灶三个 ROI，PyRadiomics 提取特征，比较 LASSO 与随机森林预测"
            "恶性潜能的效能，并在外院做外部验证；前瞻队列留取囊液做蛋白组与脂质组。")
        self.agent = DesignAgent(self.client, self.project)
        st = self.project.stage(1)
        st.update({"status": "done", "final":
                   "研究类型：诊断准确性研究（预测恶性潜能），非预后研究。数据来源为 2015-01 至 "
                   "2023-06 本院手术病理证实 PCL 患者，伦理批号待补；计划注册于 ChiCTR。"
                   "目标人群：术前 2 周内完成门静脉期增强 CT、且接受手术切除的 PCL 成人患者；"
                   "排除术前接受新辅助治疗或影像质量不合格者。预期用途：辅助决定是否手术。"})
        st2 = self.project.stage(2)
        st2.update({"status": "asked",
                    "questions": [
                        {"q": "三个中心的伦理与知情同意状态分别是什么？回顾性影像数据是否豁免知情同意、前瞻性囊液采集是否单独签署？",
                         "why": "多中心数据的合法性决定能否合并建模，也决定 CLEAR 8 里同意方式怎么写"},
                        {"q": "回顾队列、外部验证队列与前瞻队列之间是否存在患者级重叠？用什么标识符核查？",
                         "why": "重叠会使外部验证效能虚高，属于 CLEAR 14 必须声明的内容"},
                        {"q": "外院数据的伦理与数据共享协议是否允许把影像与病理结果用于本研究的建模与发表？",
                         "why": "决定外院数据能否作为独立外部验证集进入分析"}],
                    "answers": ["本院豁免知情同意，外院已获伦理批准", "已核查，无患者级重叠"]})
        st3 = self.project.stage(3)
        st3.update({"status": "drafted", "draft":
                    "样本量：按 Riley 预测模型公式估算，预期 AUC 0.85、拟纳入 15 个候选变量时，"
                    "训练集需 ≥ 240 例且恶性事件 ≥ 90 例；外部验证 ≥ 100 例、事件 ≥ 40 例。"
                    "当前训练集 262 例（恶性 101 例）满足要求，外部 50 例偏少，建议扩至 ≥ 100 例。",
                    "risks": "外部验证事件数不足会使 AUC 置信区间过宽，难以支撑泛化性结论。",
                    "checklist": ["写明样本量估算方法与参数 ｜ 依据：TRIPOD+AI 10",
                                  "报告各分析的事件数 ｜ 依据：TRIPOD+AI 21"]})
        self.transcript.clear()
        self._welcome()
        self.transcript.add_header("速读", "agent", time.strftime("%H:%M"))
        self.transcript.add_text_block(
            "【设计速读】这是一项以术前增强 CT 影像组学预测胰腺囊性病变恶性潜能的诊断准确性研究，"
            "数据为单中心回顾队列 + 外院外部验证，另设前瞻队列做囊液蛋白组与脂质组解释。\n"
            "【首要关注点】① 采集与重建参数未说明 ｜ 阶段 04；② 外部验证例数与事件数 ｜ 阶段 03；"
            "③ 组学分组是否独立于模型输出 ｜ 阶段 09。\n")
        self.set_current(2)
        self.phase = "draft"
        self.show_draft(st3["draft"])
        self._refresh_all()


# --------------------------------------------------------------------------- 入口
def main(argv):
    app = QApplication(argv)
    set_color_theme(THEME_PATH)
    set_appearance_mode("light")     # 默认浅色，深色为亮橙科技配色
    app.setWindowIcon(QtGui.QIcon(ICON_PATH))     # 任务栏 / Alt-Tab 图标
    install_button_skin()            # 给按钮套立体皮肤（渐变面 + 上亮下暗倒角）

    splash = None
    if SHOW_SPLASH and not any(a in argv for a in ("--shot", "--e2e", "--demo")):
        pix = QtGui.QPixmap(BANNER_PATH)
        if not pix.isNull():
            splash = QtWidgets.QSplashScreen(
                pix.scaledToWidth(520, Qt.TransformationMode.SmoothTransformation))
            splash.showMessage("　组学研究设计工作台 · 正在启动…",
                               Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                               QtGui.QColor("#1A1A1A"))
            splash.show()
            app.processEvents()

    win = StudioWindow(demo="--demo" in argv)
    if splash is not None:
        QtCore.QTimer.singleShot(1100, splash.close)   # 启动画面短暂展示后自动关闭

    if "--shot" in argv:
        out = data_path("_shots")                       # 冻结后写到 exe 同级
        os.makedirs(out, exist_ok=True)
        win.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # 隔离出临时项目目录并造几条样本，避免动到真实 projects/
        import shutil
        import design_agent as _da
        real_dir = _da.PROJECT_DIR
        _da.PROJECT_DIR = os.path.join(HERE, "_pmtest")
        shutil.rmtree(_da.PROJECT_DIR, ignore_errors=True)
        os.makedirs(_da.PROJECT_DIR, exist_ok=True)
        for i, (nm, dn, st) in enumerate([("胰腺囊性病变_影像组学", 3, "done"),
                                          ("肝细胞癌_多组学预后", 1, "drafted"),
                                          ("卒中_ASPECTS_自动分割", 0, "todo")]):
            sp = Project.new(nm, raw="样本项目的初步设计描述……" * 3, model="deepseek-v4-pro")
            for k in range(1, dn + 1):
                sp.stage(k)["status"] = "done"
                sp.stage(k)["final"] = f"第 {k} 阶段定稿（样本）"
            if dn + 1 <= 10:
                sp.stage(dn + 1)["status"] = st
                sp.stage(dn + 1)["draft"] = "待采纳的改写稿（样本）"
            sp.save()

        def snap(name, widget=None):
            QApplication.processEvents()
            (widget or win).grab().save(os.path.join(out, name))
            if name.startswith("studio_03"):
                bar = win.work_scroll.verticalScrollBar()
                with open(os.path.join(out, "_snap_diag.txt"), "w", encoding="utf-8") as fh:
                    fh.write(f"问题数={len(win.answer_rows)}\n"
                             f"工作区高={win.work_scroll.height()} 内容高={win.work.height()} "
                             f"scroll={bar.value()}/{bar.maximum()}\n"
                             f"中心栏高={win.center_col.height()} 窗口={win.width()}x{win.height()}\n"
                             f"阶段={win.current_index()} phase={win.phase}\n")

        def cleanup():
            win._no_flush = True
            _da.PROJECT_DIR = real_dir            # 先复位，避免退出时的保存又写回临时目录
            shutil.rmtree(os.path.join(HERE, "_pmtest"), ignore_errors=True)

        steps = [
            (600, lambda: snap("studio_01_light_default.png")),
            (1000, lambda: win.set_current(0)),
            (1300, lambda: win.on_stage_clicked(0)),
            (1700, lambda: snap("studio_02_light_done_stage.png")),
            (2100, lambda: win.set_current(1)),
            (2400, lambda: win.on_stage_clicked(1)),
            (2800, lambda: snap("studio_03_light_answers.png")),
            (3100, lambda: win.toggle_mode()),
            (3500, lambda: snap("studio_04_dark_answers.png")),
            (3900, lambda: win.manage_projects()),
            (4500, lambda: snap("studio_05_dark_manager.png",
                                getattr(win, "_pm_dlg", None))),
            (4800, lambda: getattr(win, "_pm_dlg", None) and win._pm_dlg.close()),
            (5000, lambda: win.new_project(True)),
            (5500, lambda: snap("studio_06_dark_new_project.png",
                                getattr(win, "_prompt_dlg", None))),
            (5800, lambda: getattr(win, "_prompt_dlg", None) and win._prompt_dlg.close()),
            (6100, cleanup),
            (6500, app.quit),
        ]
        for d, fn in steps:
            QtCore.QTimer.singleShot(d, fn)

    if "--e2e" in argv:                       # 真实 LLM 端到端联调（跑完自动退出）
        log = open(os.path.join(HERE, "_e2e.log"), "w", encoding="utf-8")
        out = os.path.join(HERE, "_shots")
        os.makedirs(out, exist_ok=True)
        st = {"i": 0}
        answers = ["门静脉期增强 CT，层厚 1.25 mm，两家医院机型不同",
                   "以手术病理为金标准，高级别异型增生或浸润癌判为恶性",
                   "训练集 262 例、外部 50 例、前瞻 34 例", "已按患者 ID 核查，无重叠"]

        def poll():
            if win._busy():
                return
            i = st["i"]
            if i == 0:
                win.load_sample()
                win.start_analysis()
                st["i"] = 1
            elif i == 1:
                if not win.answer_rows:
                    log.write("!! 未拿到追问：\n" + win.transcript.toPlainText())
                    log.close()
                    app.quit()
                    return
                log.write("=== 追问阶段输出 ===\n" + win.transcript.toPlainText() + "\n")
                for k, e in enumerate(win.answer_rows):
                    win._set_answer(e, answers[k % len(answers)])
                win.submit_answers()
                st["i"] = 2
            elif i == 2:
                log.write("\n=== 改写稿 ===\n" + (win.pending_draft or "(空)") + "\n")
                win.grab().save(os.path.join(out, "e2e_after_rewrite.png"))
                win.accept_draft()
                st["i"] = 3
            elif i == 3:
                win.grab().save(os.path.join(out, "e2e_after_accept.png"))
                log.write("\n=== 项目文档 ===\n" + win.project.render_doc() + "\n")
                log.close()
                app.quit()

        timer = QtCore.QTimer()
        timer.timeout.connect(poll)
        timer.start(900)

    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
