# -*- coding: utf-8 -*-
"""组学研究标准流程 · 交互式 Pipeline 界面

极简蓝色科技风格，基于 PySide6 + PyCt6（CApplication / CMainWindow / CButton ...）。

左侧：十阶段流程管线（自绘节点 + 连接线，可点击 / 悬停 / 键盘导航）
中间：阶段详情（目标 / 必做动作 / 必报参数，动作可勾选）
右侧：规范出处 / 本案例状态 / 常见缺陷
顶部：搜索过滤、深浅色切换、导出检查表、进度条

运行：  python omics_pipeline.py
自检：  python omics_pipeline.py --shot      （离屏渲染截图到 _shots/）
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import date

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QRectF, QSize, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QSizePolicy,
                               QSpacerItem, QVBoxLayout, QWidget)

from PyCt6 import (CMainWindow, CFrame, CLabel, CButton, CLineEdit,
                   set_appearance_mode, set_color_theme, ModeManager)

from stages_data import STAGES
from ui_kit import (PAL, C, UI_FONT, MONO_FONT, mk_label, clear_layout,
                    text_height, ProgressBar, status_key, CreditBar,
                    WorkScroll, screen_size)

HERE = os.path.dirname(os.path.abspath(__file__))
from app_paths import resource_path, data_path

THEME_PATH = resource_path("theme_tech.json")
ICON_PATH = resource_path("logo_mark.png" if sys.platform == "darwin"
                              else "logo_icon.ico")   # macOS 用 PNG，Windows 用多尺寸 ICO
BADGE_PATH = resource_path("logo_badge.png")
STATE_PATH = data_path("progress_state.json")


# --------------------------------------------------------------------------- 流程管线画布
class PipelinePanel(QWidget):
    stageSelected = Signal(int)

    NODE_H = 46
    GAP = 12
    PAD_X = 10
    PAD_Y = 10

    def __init__(self, master, stages):
        super().__init__(master)
        self.stages = stages
        self.current = 0
        self.done = {}                     # stage index -> bool（由外部注入）
        self.hover = -1
        self.filter = ""
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        h = self.PAD_Y * 2 + len(stages) * self.NODE_H + (len(stages) - 1) * self.GAP
        self.setMinimumHeight(h)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(h)

    # -- 外部接口 -----------------------------------------------------------
    def set_filter(self, text: str):
        self.filter = (text or "").strip().lower()
        self.update()

    def set_current(self, index: int):
        self.current = max(0, min(len(self.stages) - 1, index))
        self.update()

    def set_done_map(self, done: dict):
        self.done = done
        self.update()

    def _change_theme(self):
        self.update()

    def _matches(self, stage) -> bool:
        if not self.filter:
            return True
        blob = " ".join([stage["title"], stage["spec"], stage["goal"],
                         " ".join(stage["actions"]), " ".join(stage["reports"])]).lower()
        return self.filter in blob

    def _rect(self, i) -> QRectF:
        return QRectF(self.PAD_X, self.PAD_Y + i * (self.NODE_H + self.GAP),
                      self.width() - self.PAD_X * 2, self.NODE_H)

    # -- 事件 ---------------------------------------------------------------
    def mouseMoveEvent(self, event):
        idx = self._index_at(event.position())
        if idx != self.hover:
            self.hover = idx
            self.setCursor(Qt.CursorShape.PointingHandCursor if idx >= 0
                           else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, event):
        self.hover = -1
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        idx = self._index_at(event.position())
        if idx >= 0:
            self.set_current(idx)
            self.stageSelected.emit(idx)

    def _index_at(self, pos) -> int:
        for i in range(len(self.stages)):
            if self._rect(i).contains(pos):
                return i
        return -1

    # -- 绘制 ---------------------------------------------------------------
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)

        f_title = QtGui.QFont(UI_FONT, 10)
        f_title.setBold(True)
        f_spec = QtGui.QFont(UI_FONT, 8)
        f_num = QtGui.QFont(MONO_FONT, 10)
        f_num.setBold(True)
        f_tag = QtGui.QFont(UI_FONT, 8)

        for i, stage in enumerate(self.stages):
            r = self._rect(i)
            matched = self._matches(stage)
            p.setOpacity(1.0 if matched else 0.28)

            # 连接线（先画，压在节点下）
            if i < len(self.stages) - 1:
                x = r.left() + 22
                y1, y2 = r.bottom(), r.bottom() + self.GAP
                passed = i < self.current or (i <= self.current and self.done.get(i, False))
                pen = QtGui.QPen(QtGui.QColor(C("accent") if passed else C("grid")))
                pen.setWidthF(1.6)
                p.setPen(pen)
                p.drawLine(QtCore.QPointF(x, y1), QtCore.QPointF(x, y2 - 1))
                p.setBrush(QtGui.QColor(C("accent") if passed else C("grid")))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(x - 4, y2 - 5),
                                               QtCore.QPointF(x + 4, y2 - 5),
                                               QtCore.QPointF(x, y2)]))

            # 节点底
            active = (i == self.current)
            hovered = (i == self.hover)
            bg = C("node_active") if active else (C("node_hover") if hovered else C("node"))
            if active:
                glow = QtGui.QColor(C("accent"))
                glow.setAlpha(46)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(glow)
                p.drawRoundedRect(r.adjusted(-3, -3, 3, 3), 13, 13)
            p.setBrush(QtGui.QColor(bg))
            border = QtGui.QColor(C("accent") if active else
                                  (C("accent_dim") if hovered else C("border")))
            pen = QtGui.QPen(border)
            pen.setWidthF(2.0 if active else 1.0)
            p.setPen(pen)
            p.drawRoundedRect(r, 10, 10)

            # 序号圆点
            cx, cy = r.left() + 22, r.center().y()
            done = self.done.get(i, False)
            if done:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QtGui.QColor(C("ok")))
                p.drawEllipse(QtCore.QPointF(cx, cy), 11, 11)
                p.setPen(QtGui.QPen(QtGui.QColor(C("surface2"))))
                p.setFont(f_num)
                p.drawText(QRectF(cx - 11, cy - 10, 22, 20), Qt.AlignCenter, "✓")
            else:
                col = QtGui.QColor(C("accent") if active else C("muted"))
                pen = QtGui.QPen(col)
                pen.setWidthF(1.6)
                p.setPen(pen)
                p.setBrush(QtGui.QColor(C("surface")) if not active else QtGui.QColor(C("node_active")))
                p.drawEllipse(QtCore.QPointF(cx, cy), 11, 11)
                p.setPen(QtGui.QPen(col))
                p.setFont(f_num)
                p.drawText(QRectF(cx - 11, cy - 10, 22, 20), Qt.AlignCenter,
                           f"{stage['id']:02d}")

            # 标题与规范
            tx = cx + 20
            ty = r.center().y()
            p.setPen(QtGui.QPen(QtGui.QColor(C("text") if matched else C("muted"))))
            p.setFont(f_title)
            p.drawText(QRectF(tx, ty - 19, r.width() - (tx - r.left()) - 64, 21),
                       Qt.AlignLeft | Qt.AlignVCenter, stage["title"])
            p.setPen(QtGui.QPen(QtGui.QColor(C("muted"))))
            p.setFont(f_spec)
            p.drawText(QRectF(tx, ty + 1, r.width() - (tx - r.left()) - 64, 19),
                       Qt.AlignLeft | Qt.AlignVCenter, stage["spec"])

            # 右侧状态标签
            tag = stage["case"][0]
            tcol = QtGui.QColor(C(status_key(tag)))
            tag_bg = QtGui.QColor(tcol)
            tag_bg.setAlpha(38)
            tw, th = 40, 19
            tr = QRectF(r.right() - tw - 10, r.center().y() - th / 2, tw, th)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(tag_bg)
            p.drawRoundedRect(tr, 9, 9)
            p.setPen(QtGui.QPen(tcol))
            p.setFont(f_tag)
            p.drawText(tr, Qt.AlignCenter, tag)

        p.setOpacity(1.0)


# --------------------------------------------------------------------------- 左侧栏
class PipelineColumn(CFrame):
    def __init__(self, master, stages, on_select):
        super().__init__(master, border_width=1, corner_radius=12,
                         background_color=PAL["surface"])
        self.setFixedWidth(372)
        self._lay = self.layout()
        self._lay.setContentsMargins(14, 14, 14, 14)
        self._lay.setSpacing(10)
        head = mk_label(self, "流程管线 · 十阶段", size=12, bold=True,
                        color=PAL["accent"], width_px=320)
        self.addWidget(head)
        # 管线画布放进滚动容器：窗口变矮时滚动，不会压住下方提示
        self.canvas_scroll = WorkScroll(self)
        self.canvas = PipelinePanel(self.canvas_scroll, stages)
        self.canvas.stageSelected.connect(on_select)
        self.canvas_scroll.setWidget(self.canvas)
        self.canvas_scroll.setMinimumHeight(180)
        self.addWidget(self.canvas_scroll)
        hint = mk_label(self, "点击节点查看详情 · ↑↓ 切换 · 空格标记完成",
                        size=8, color=PAL["muted"], width_px=320)
        self.addWidget(hint)
        spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Minimum,
                             QSizePolicy.Policy.MinimumExpanding)
        self.addItem(spacer)


# --------------------------------------------------------------------------- 中间详情
class DetailColumn(CFrame):
    def __init__(self, master, on_toggle_action, on_toggle_stage):
        super().__init__(master, border_width=1, corner_radius=12,
                         background_color=PAL["surface"])
        self._on_toggle_action = on_toggle_action
        self._on_toggle_stage = on_toggle_stage
        outer = self.layout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        # 详情内容放进滚动容器：窗口变矮时滚动，绝不与相邻控件重叠
        self.scroll = WorkScroll(self)
        inner = CFrame(self.scroll, border_width=0, corner_radius=0,
                       background_color="none")
        self._lay = inner.layout()
        self._lay.setContentsMargins(22, 18, 22, 18)
        self._lay.setSpacing(9)
        self.scroll.setWidget(inner)
        outer.addWidget(self.scroll)
        self.stage = None
        self.checks = []

    def show_stage(self, stage, checked, width_px=540):
        clear_layout(self._lay)
        self.stage = stage
        self.checks = []

        top = QWidget(self)
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(10)
        num = mk_label(top, f"{stage['id']:02d}", size=20, bold=True,
                       color=PAL["accent"], width_px=60)
        num.setFixedWidth(60)
        num.label().setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_lay.addWidget(num)
        box = QWidget(top)
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(0, 0, 0, 0)
        box_lay.setSpacing(2)
        t = mk_label(box, stage["title"], size=15, bold=True, width_px=width_px - 130)
        s = mk_label(box, "规范出处  " + stage["spec"], size=9,
                     color=PAL["muted"], width_px=width_px - 130)
        box_lay.addWidget(t)
        box_lay.addWidget(s)
        top_lay.addWidget(box, 1)
        self.addWidget(top)

        goal_head = mk_label(self, "阶段目标", size=11, bold=True, width_px=width_px)
        self.addWidget(goal_head)
        goal = mk_label(self, stage["goal"], size=10, width_px=width_px)
        self.addWidget(goal)

        act_head = mk_label(self, "必做动作（勾选即计入进度）", size=11, bold=True,
                            color=PAL["accent"], width_px=width_px)
        self.addWidget(act_head)
        for i, action in enumerate(stage["actions"]):
            row = QWidget(self)
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(8)
            cb = QCheckBox(row)
            cb.blockSignals(True)
            cb.setChecked(bool(checked[i]))
            cb.blockSignals(False)
            self._style_checkbox(cb)
            cb.stateChanged.connect(
                lambda _state, idx=i: self._on_toggle_action(idx))
            lbl = mk_label(row, action, size=10, width_px=width_px - 40,
                           color=PAL["text"])
            lay.addWidget(cb)
            lay.addWidget(lbl, 1)
            row.setFixedHeight(lbl.height())
            self.checks.append(cb)
            self.addWidget(row)

        rep_head = mk_label(self, "必报参数", size=11, bold=True, width_px=width_px)
        self.addWidget(rep_head)
        for item in stage["reports"]:
            lbl = mk_label(self, "·  " + item, size=10, width_px=width_px,
                           color=PAL["text"])
            self.addWidget(lbl)

        spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Minimum,
                             QSizePolicy.Policy.MinimumExpanding)
        self.addItem(spacer)

        done_all = all(checked)
        btn = CButton(master=self, text="取消本阶段勾选" if done_all else "全部标记完成",
                      width=150, height=30, font_family=UI_FONT, font_size=9,
                      command=self._on_toggle_stage,
                      background_color=PAL["btn"] if done_all
                      else PAL["accent"],
                      text_color=PAL["text"] if done_all
                      else PAL["on_accent"],
                      hover_color=PAL["btn_hover"] if done_all
                      else PAL["accent_hover"],
                      border_color=PAL["border"])
        self.addWidget(btn)

    @staticmethod
    def _style_checkbox(cb: QCheckBox):
        cb.setStyleSheet(
            "QCheckBox { spacing: 8px; }"
            "QCheckBox::indicator { width: 15px; height: 15px; border-radius: 4px;"
            f" border: 1px solid {C('border')}; background: {C('surface2')}; }}"
            "QCheckBox::indicator:hover { border: 1px solid " + C("accent") + "; }"
            "QCheckBox::indicator:checked { background: " + C("accent") + ";"
            " border: 1px solid " + C("accent") + "; }"
        )


# --------------------------------------------------------------------------- 右侧栏
class SideColumn(CFrame):
    def __init__(self, master, on_export):
        super().__init__(master, border_width=1, corner_radius=12,
                         background_color=PAL["surface2"])
        self.setFixedWidth(384)
        self._lay = self.layout()
        self._lay.setContentsMargins(18, 16, 18, 16)
        self._lay.setSpacing(8)
        self._on_export = on_export

    def show_stage(self, stage, width_px=330):
        clear_layout(self._lay)

        def heading(txt, key="muted"):
            lbl = mk_label(self, txt, size=10, bold=True, width_px=width_px,
                           color=PAL["muted"])
            self.addWidget(lbl)
            return lbl

        heading("本案例状态")
        status, note = stage["case"]
        pill_row = QWidget(self)
        row_lay = QHBoxLayout(pill_row)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(8)
        col = C(status_key(status))
        pill = mk_label(pill_row, status, size=10, bold=True, color="#FFFFFF",
                        width_px=54, bg=col, radius=8, align="center")
        pill.setFixedSize(56, 26)
        pill.label().setStyleSheet(
            f"QLabel {{ background-color: {col}; color: #FFFFFF;"
            " border-radius: 8px; }")
        row_lay.addWidget(pill)
        row_lay.addStretch(1)
        self.addWidget(pill_row)
        note_lbl = mk_label(self, note, size=10, width_px=width_px)
        self.addWidget(note_lbl)

        heading("常见缺陷")
        for pit in stage["pitfalls"]:
            lbl = mk_label(self, "·  " + pit, size=10, width_px=width_px,
                           color=PAL["text"])
            self.addWidget(lbl)

        heading("对应规范条目")
        for ref in stage["refs"]:
            lbl = mk_label(self, "–  " + ref, size=9, width_px=width_px,
                           color=PAL["muted_dim"])
            self.addWidget(lbl)

        spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Minimum,
                             QSizePolicy.Policy.MinimumExpanding)
        self.addItem(spacer)
        btn = CButton(master=self, text="导出检查表 (.md)", width=190, height=32,
                      font_family=UI_FONT, font_size=9, command=self._on_export,
                      background_color=PAL["btn"],
                      text_color=PAL["text"],
                      hover_color=PAL["btn_hover"],
                      border_color=PAL["border"])
        self.addWidget(btn)


# --------------------------------------------------------------------------- 主窗口
class MainWindow(CMainWindow):
    def __init__(self):
        sw, sh, sx, sy = screen_size(1440, 920, 1120, 700)
        super().__init__(width=sw, height=sh, x=sx, y=sy,
                         title="组学研究标准流程 · Pipeline",
                         icon=ICON_PATH, background_color=PAL["bg"])
        self.setMinimumSize(1100, 680)
        self.stages = STAGES
        self.current = 0
        self.state = self._load_state()
        self.filter_text = ""

        root = QVBoxLayout()
        root.setContentsMargins(18, 16, 18, 10)
        root.setSpacing(12)

        root.addWidget(self._build_header())

        body = CFrame(self, layout_type="horizontal", border_width=0, corner_radius=0,
                      background_color="none")
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        blay = body.layout()
        blay.setContentsMargins(0, 0, 0, 0)
        blay.setSpacing(14)

        self.pipeline_col = PipelineColumn(body, self.stages, self.select_stage)
        self.detail_col = DetailColumn(body, self.toggle_action, self.toggle_stage)
        self.side_col = SideColumn(body, self.export_markdown)
        blay.addWidget(self.pipeline_col)
        blay.addWidget(self.detail_col, 1)
        blay.addWidget(self.side_col)
        root.addWidget(body, 1)

        root.addWidget(self._build_footer())
        root.addWidget(CreditBar(self))
        self.setLayout(root)

        self._apply_responsive()

        self.refresh()

    # -- 顶部 ---------------------------------------------------------------
    def _build_header(self) -> CFrame:
        header = CFrame(self, layout_type="horizontal", border_width=1, corner_radius=12,
                        background_color=PAL["surface"])
        self.header = header
        header.setFixedHeight(96)
        lay = header.layout()
        lay.setContentsMargins(20, 14, 18, 14)
        lay.setSpacing(10)

        titles = QWidget(header)
        titles.setMinimumWidth(300)
        titles.setMaximumWidth(620)
        titles.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tlay = QHBoxLayout(titles)
        tlay.setContentsMargins(0, 0, 0, 0)
        tlay.setSpacing(10)
        badge = CLabel(titles, width=28, height=28, icon=BADGE_PATH,
                       border_width=0, tooltip="PCL-Radiomics")
        badge.setFixedSize(30, 30)
        badge.label().setFixedSize(28, 28)
        badge.label().setScaledContents(True)
        tlay.addWidget(badge, 0, Qt.AlignVCenter)
        col = QWidget(titles)
        cl = QVBoxLayout(col)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(2)
        cl.addWidget(mk_label(col, "组学研究标准流程 · 端到端 Pipeline", size=14, bold=True,
                              width_px=570, wrap=True))
        cl.addWidget(mk_label(col,
                              "CLEAR · METRICS · TRIPOD+AI · PROBAST+AI · CLAIM · IBSI · MIAPE · MSI",
                              size=8, color=PAL["muted"], width_px=570, wrap=True))
        tlay.addWidget(col, 1)
        lay.addWidget(titles)

        spacer = QSpacerItem(10, 10, QSizePolicy.Policy.MinimumExpanding,
                             QSizePolicy.Policy.Minimum)
        lay.addItem(spacer)

        self.search = CLineEdit(master=header, width=210, height=30, font_family=UI_FONT,
                                font_size=9, placeholder_text="搜索阶段 / 参数…")
        self.search.line_edit().textChanged.connect(self.on_search)
        lay.addWidget(self.search)

        self.progress_label = mk_label(header, "进度 0%", size=9, align="right", width_px=90,
                                       color=PAL["muted"])
        self.progress_label.setFixedWidth(92)
        lay.addWidget(self.progress_label)

        self.bar_wrap = bar_wrap = QWidget(header)
        wlay = QVBoxLayout(bar_wrap)
        wlay.setContentsMargins(0, 0, 0, 0)
        bar_wrap.setFixedSize(180, 30)
        self.progress = ProgressBar(bar_wrap, width=180, height=8)
        wlay.addWidget(self.progress, 0, Qt.AlignVCenter)
        lay.addWidget(bar_wrap)

        self.mode_btn = CButton(master=header, text="深色模式", width=96, height=30,
                                font_family=UI_FONT, font_size=9, command=self.toggle_mode,
                                background_color=PAL["btn"],
                                text_color=PAL["text"],
                                hover_color=PAL["btn_hover"],
                                border_color=PAL["border"])
        lay.addWidget(self.mode_btn)

        self.reset_btn = CButton(master=header, text="重置", width=72, height=30,
                                 font_family=UI_FONT, font_size=9, command=self.reset_state,
                                 background_color=PAL["btn"],
                                 text_color=PAL["text"],
                                 hover_color=PAL["btn_hover"],
                                 border_color=PAL["border"])
        lay.addWidget(self.reset_btn)
        return header

    # -- 底部 ---------------------------------------------------------------
    def _build_footer(self) -> CFrame:
        footer = CFrame(self, layout_type="horizontal", border_width=0, corner_radius=0,
                        background_color="none")
        footer.setFixedHeight(38)
        lay = footer.layout()
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(10)
        self.status = mk_label(footer, "", size=9, width_px=900,
                               color=PAL["muted"])
        lay.addWidget(self.status, 1)
        self.tip = mk_label(footer, "↑↓ 切换阶段 · 空格 全部完成 · Ctrl+E 导出",
                            size=9, align="right", width_px=460,
                            color=PAL["muted"])
        lay.addWidget(self.tip)
        return footer

    # -- 状态 ---------------------------------------------------------------
    def _load_state(self) -> dict:
        data = {}
        if os.path.exists(STATE_PATH):
            try:
                data = json.load(open(STATE_PATH, encoding="utf-8"))
            except Exception:
                data = {}
        out = {}
        for st in self.stages:
            saved = data.get(str(st["id"]), [])
            out[st["id"]] = [bool(saved[i]) if i < len(saved) else False
                             for i in range(len(st["actions"]))]
        return out

    def _save_state(self):
        try:
            json.dump({str(k): v for k, v in self.state.items()},
                      open(STATE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception:
            pass

    def _done_map(self) -> dict:
        return {i: all(self.state[st["id"]]) for i, st in enumerate(self.stages)}

    def total_actions(self) -> int:
        return sum(len(st["actions"]) for st in self.stages)

    def checked_actions(self) -> int:
        return sum(sum(1 for v in self.state[st["id"]] if v) for st in self.stages)

    # -- 交互 ---------------------------------------------------------------
    def select_stage(self, index: int):
        self.current = max(0, min(len(self.stages) - 1, index))
        self.pipeline_col.canvas.set_current(self.current)
        self.refresh()

    def _apply_responsive(self):
        """按窗口宽度收缩左右两栏，窄窗口下中栏不被挤压。"""
        w = self.width()
        narrow = w < 1340
        if hasattr(self, "pipeline_col"):
            self.pipeline_col.setFixedWidth(296 if narrow else 372)
        if hasattr(self, "side_col"):
            self.side_col.setFixedWidth(324 if narrow else 384)
        if hasattr(self, "header"):
            self.header.setFixedHeight(112 if narrow else 96)
        for wdg in (getattr(self, "progress", None), getattr(self, "progress_label", None),
                    getattr(self, "bar_wrap", None)):
            if wdg is not None:
                wdg.setVisible(not narrow)
        for name, wd in (("search", 150 if narrow else 210),
                         ("mode_btn", 58 if narrow else 96),
                         ("reset_btn", 54 if narrow else 72)):
            wdg = getattr(self, name, None)
            if wdg is not None:
                wdg.setFixedWidth(wd)
        self._narrow = narrow

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive()

    def current_stage(self):
        return self.stages[self.current]

    def toggle_action(self, action_index: int, checked=None):
        st = self.current_stage()
        vals = self.state[st["id"]]
        if checked is None:
            vals[action_index] = not vals[action_index]
        else:
            vals[action_index] = bool(checked)
        self._save_state()
        self.refresh()

    def toggle_stage(self):
        st = self.current_stage()
        vals = self.state[st["id"]]
        target = not all(vals)
        self.state[st["id"]] = [target] * len(vals)
        self._save_state()
        self.refresh()

    def on_search(self, text: str):
        self.filter_text = text
        self.pipeline_col.canvas.set_filter(text)
        self._update_status()

    def toggle_mode(self):
        mode = "light" if ModeManager.mode != "light" else "dark"
        set_appearance_mode(mode)
        self.mode_btn.button().setText("深色模式" if mode == "light" else "浅色模式")
        self._apply_mode()

    def _apply_mode(self):
        self.setWindowBackground(PAL["bg"])
        if hasattr(self, "_change_theme"):
            self._change_theme()
        for w in self.findChildren(QWidget):
            fn = getattr(w, "_change_theme", None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass
        self.refresh()

    def reset_state(self):
        for st in self.stages:
            self.state[st["id"]] = [False] * len(st["actions"])
        self._save_state()
        self.refresh()

    # -- 刷新 ---------------------------------------------------------------
    def refresh(self):
        self.pipeline_col.canvas.set_done_map(self._done_map())
        self.pipeline_col.canvas.set_current(self.current)
        st = self.current_stage()
        self.detail_col.show_stage(st, self.state[st["id"]])
        self.side_col.show_stage(st)
        self._update_status()

    def _update_status(self):
        total = self.total_actions()
        done = self.checked_actions()
        ratio = done / total if total else 0
        self.progress.set_value(ratio)
        self.progress_label.label().setText(f"进度 {done}/{total}")
        ok = sum(1 for s in self.stages if s["case"][0] == "达标")
        part = sum(1 for s in self.stages if s["case"][0] == "部分")
        bad = sum(1 for s in self.stages if s["case"][0] == "缺失")
        extra = ("　·　筛选生效" if self.filter_text.strip() else "")
        self.status.label().setText(
            f"当前：{self.current_stage()['id']:02d} {self.current_stage()['title']}"
            f"　·　本案例自评：达标 {ok} · 部分 {part} · 缺失 {bad}"
            f"　·　已勾选 {done}/{total} 项必做动作{extra}")

    # -- 导出 ---------------------------------------------------------------
    def export_markdown(self):
        lines = ["# 组学研究标准流程 · 检查表", "",
                 f"生成时间：{date.today().isoformat()}",
                 f"完成度：{self.checked_actions()}/{self.total_actions()} 项必做动作", ""]
        for st in self.stages:
            vals = self.state[st["id"]]
            flag = "✅" if all(vals) else ("◐" if any(vals) else "○")
            lines.append(f"## {flag} {st['id']:02d} {st['title']}　（{st['spec']}）")
            lines.append(f"- 阶段目标：{st['goal']}")
            lines.append(f"- 本案例状态：**{st['case'][0]}** —— {st['case'][1]}")
            lines.append("- 必做动作：")
            for a, v in zip(st["actions"], vals):
                lines.append(f"  - [{'x' if v else ' '}] {a}")
            lines.append("- 必报参数：" + "；".join(st["reports"]))
            lines.append("- 常见缺陷：" + "；".join(st["pitfalls"]))
            lines.append("- 对应规范条目：")
            for r in st["refs"]:
                lines.append(f"  - {r}")
            lines.append("")
        lines += ["---", "",
                  "规范依据：CLEAR（Insights Imaging 2023, doi:10.1186/s13244-023-01415-8）、"
                  "METRICS（Insights Imaging 2024, doi:10.1186/s13244-023-01572-w）、"
                  "TRIPOD+AI（BMJ 2024;385:e078378）、PROBAST+AI（BMJ 2025, doi:10.1136/bmj-2024-082505）、"
                  "CLAIM 2024（doi:10.1148/ryai.240300）、RQS（Nat Rev Clin Oncol 2017;14:749）、"
                  "IBSI（Radiology 2020;295:328）、MIAPE（Nat Biotechnol 2007）、"
                  "MSI（Metabolomics 2007）。"]
        path = os.path.join(HERE, f"标准流程检查表_{date.today().isoformat()}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        self.tip.label().setText(f"已导出 → {os.path.basename(path)}")
        return path

    # -- 键盘 ---------------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Right):
            self.select_stage(self.current + 1)
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Left):
            self.select_stage(self.current - 1)
        elif key == Qt.Key.Key_Space:
            self.toggle_stage()
        elif key == Qt.Key.Key_E and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.export_markdown()
        else:
            super().keyPressEvent(event)


# --------------------------------------------------------------------------- 入口
def main(argv):
    app = QApplication(argv)
    set_color_theme(THEME_PATH)
    set_appearance_mode("light")     # 默认浅色，深色为亮橙科技配色
    win = MainWindow()

    if "--shot" in argv:
        out_dir = os.path.join(HERE, "_shots")
        os.makedirs(out_dir, exist_ok=True)
        win.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        def snap(name):
            win.search.line_edit().clear()      # 排除实时输入对截图的干扰
            QtWidgets.QApplication.processEvents()
            win.grab().save(os.path.join(out_dir, name))

        steps = [
            (500, lambda: snap("01_light_default.png")),
            (900, lambda: win.select_stage(3)),
            (1300, lambda: snap("02_light_stage04.png")),
            (1700, lambda: win.toggle_action(0)),
            (2000, lambda: win.toggle_action(2)),
            (2300, lambda: snap("03_light_checked.png")),
            (2700, lambda: win.toggle_mode()),
            (3100, lambda: snap("04_dark_default.png")),
            (3500, lambda: win.select_stage(9)),
            (3900, lambda: snap("05_dark_stage10.png")),
            (4300, lambda: win.select_stage(8)),
            (4700, lambda: snap("06_dark_stage09.png")),
            (5100, lambda: win.export_markdown()),
            (5500, app.quit),
        ]
        for delay, fn in steps:
            QtCore.QTimer.singleShot(delay, fn)

    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
