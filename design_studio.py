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
                          parse_questions, parse_checklist, q_text, SYSTEM_PROMPT)
from llm_client import LLMClient, load_config, save_config, mask
from stages_data import STAGES
from ui_kit import (PAL, C, UI_FONT, MONO_FONT, mk_label, clear_layout,
                    ProgressBar, TranscriptView, stream_format, status_key,
                    WorkScroll, fit_height, text_height, BusyIndicator, CreditBar,
                    ThinkingButton, screen_size)

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
STATUS_LABEL = {"todo": "未开始", "asked": "已追问", "drafted": "待采纳", "done": "已收录"}


# --------------------------------------------------------------------------- 后台线程
class LLMThread(QtCore.QThread):
    delta = Signal(str, str)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, client: LLMClient, messages: list, stream: bool = True, parent=None,
                 max_tokens: int | None = None):
        super().__init__(parent)
        self.client, self.messages, self.stream = client, messages, stream
        self.max_tokens = max_tokens

    def run(self):
        try:
            out = self.client.chat(self.messages, stream=self.stream,
                                   on_delta=(lambda p, k: self.delta.emit(p, k))
                                   if self.stream else None,
                                   max_tokens=self.max_tokens)
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
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        f_t = QtGui.QFont(UI_FONT, 10)
        f_t.setBold(True)
        f_s = QtGui.QFont(UI_FONT, 8)
        f_n = QtGui.QFont(MONO_FONT, 9)
        f_n.setBold(True)
        for i, st in enumerate(self.stages):
            r = self._rect(i)
            state = self.states.get(st["id"], "todo")
            active = (i == self.current)
            hovered = (i == self.hover)
            # 连接线
            if i < len(self.stages) - 1:
                x = r.left() + 20
                done = state == "done"
                pen = QtGui.QPen(QtGui.QColor(C("ok") if done else C("grid")))
                pen.setWidthF(1.6)
                p.setPen(pen)
                p.drawLine(QtCore.QPointF(x, r.bottom()), QtCore.QPointF(x, r.bottom() + self.GAP))
            bg = C("node_active") if active else (C("node_hover") if hovered else C("node"))
            if active:
                glow = QtGui.QColor(C("accent"))
                glow.setAlpha(40)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(glow)
                p.drawRoundedRect(r.adjusted(-2, -2, 2, 2), 12, 12)
            p.setBrush(QtGui.QColor(bg))
            pen = QtGui.QPen(QtGui.QColor(C("accent") if active else
                                          (C("accent_dim") if hovered else C("border"))))
            pen.setWidthF(1.8 if active else 1.0)
            p.setPen(pen)
            p.drawRoundedRect(r, 10, 10)
            # 序号点
            cx, cy = r.left() + 20, r.center().y()
            dot = {"done": C("ok"), "drafted": C("accent"), "asked": C("warn")}.get(state, None)
            if dot:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QtGui.QColor(dot))
                p.drawEllipse(QtCore.QPointF(cx, cy), 10, 10)
                p.setPen(QtGui.QPen(QtGui.QColor(C("surface2"))))
                p.setFont(f_n)
                p.drawText(QRectF(cx - 10, cy - 9, 20, 18), Qt.AlignCenter,
                           "✓" if state == "done" else f"{st['id']:02d}")
            else:
                col = QtGui.QColor(C("accent") if active else C("muted"))
                pen = QtGui.QPen(col)
                pen.setWidthF(1.5)
                p.setPen(pen)
                p.setBrush(QtGui.QColor(C("surface")))
                p.drawEllipse(QtCore.QPointF(cx, cy), 10, 10)
                p.setFont(f_n)
                p.drawText(QRectF(cx - 10, cy - 9, 20, 18), Qt.AlignCenter, f"{st['id']:02d}")
            # 文本
            tx = cx + 18
            p.setPen(QtGui.QPen(QtGui.QColor(C("text"))))
            p.setFont(f_t)
            p.drawText(QRectF(tx, cy - 20, r.width() - (tx - r.left()) - 8, 20),
                       Qt.AlignLeft | Qt.AlignVCenter, st["title"])
            p.setPen(QtGui.QPen(QtGui.QColor(C(status_key(state)))))
            p.setFont(f_s)
            p.drawText(QRectF(tx, cy + 1, r.width() - (tx - r.left()) - 8, 18),
                       Qt.AlignLeft | Qt.AlignVCenter,
                       f"{STATUS_LABEL.get(state, state)} · {st['spec']}")


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

        root = QVBoxLayout()
        root.setContentsMargins(18, 16, 18, 10)
        root.setSpacing(12)
        root.addWidget(self._build_header())

        body = QWidget(self)
        blay = QHBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        blay.setSpacing(14)
        self.left_col = self._build_left()
        blay.addWidget(self.left_col)
        blay.addWidget(self._build_center(), 1)
        blay.addWidget(self._build_right())

        # 工作台 / 总览 两个视图共存于同一窗口，按钮切换
        self.body_stack = QtWidgets.QStackedWidget(self)
        self.body_stack.addWidget(body)              # 0 工作台
        self.body_stack.addWidget(self._build_overview())   # 1 总览
        root.addWidget(self.body_stack, 1)

        root.addWidget(self._build_footer())
        root.addWidget(CreditBar(self))
        self.setLayout(root)

        self._apply_responsive()
        self._style_tab(self.tab_work, True)
        self._style_tab(self.tab_over, False)
        self._view = "work"
        self._welcome()
        self._refresh_all()
        if demo:
            self._load_demo()
        else:
            self.show_raw_input()
        self._fetch_models()

    # ---------------------------------------------------------------- 总览视图
    def _build_overview(self) -> CFrame:
        """只读表格：十阶段 × 状态 / 规范出处 / 结果 / 检查表 / 更新时间，红黄绿标记。"""
        page = CFrame(self, border_width=1, corner_radius=12,
                      background_color=PAL["surface"])
        lay = page.layout()
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        head = QWidget(page)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(12)
        hl.addWidget(mk_label(head, "管线视图 · 评分与检查表", size=15, bold=True,
                              color=PAL["accent"], width_px=260, wrap=False))
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

        self.ov_cols = ["#", "阶段", "状态", "规范出处", "结果 / 待办", "检查表", "更新"]
        self.ov_table = QtWidgets.QTableWidget(0, len(self.ov_cols), page)
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
        lay.addWidget(self.ov_table, 1)
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

    @staticmethod
    def _style_tab(btn, active: bool):
        btn._background_color = PAL["accent"] if active else PAL["btn"]
        btn._text_color = PAL["on_accent"] if active else PAL["text"]
        btn._hover_color = PAL["accent_hover"] if active else PAL["btn_hover"]
        btn._change_theme()

    def show_overview(self):
        self.refresh_overview()
        self.body_stack.setCurrentIndex(1)
        self._style_tab(self.tab_work, False)
        self._style_tab(self.tab_over, True)
        self._view = "overview"

    def show_workspace(self):
        self.body_stack.setCurrentIndex(0)
        self._style_tab(self.tab_work, True)
        self._style_tab(self.tab_over, False)
        self._view = "work"

    def refresh_overview(self):
        """按十阶段结果重建表格（只读）。"""
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

    # ---------------------------------------------------------------- 头部
    def _build_header(self) -> CFrame:
        h = CFrame(self, layout_type="horizontal", border_width=1, corner_radius=12,
                   background_color=PAL["surface"])
        self.header = h
        h.setFixedHeight(96)
        lay = h.layout()
        lay.setContentsMargins(20, 14, 18, 14)
        lay.setSpacing(10)

        titles = QWidget(h)
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
        cl.addWidget(mk_label(col, "贴入初步设想 → 十阶段逐段追问与改写 → 输出可执行研究设计",
                              size=8, color=PAL["muted"], width_px=560, wrap=True))
        tl.addWidget(col, 1)
        lay.addWidget(titles)

        # 视图切换：工作台 / 总览
        tabs = QWidget(h)
        tl2 = QHBoxLayout(tabs)
        tl2.setContentsMargins(0, 0, 0, 0)
        tl2.setSpacing(6)
        self.tab_work = CButton(master=tabs, text="工作台", width=76, height=30,
                                font_family=UI_FONT, font_size=9,
                                command=self.show_workspace)
        self.tab_over = CButton(master=tabs, text="总览", width=76, height=30,
                                font_family=UI_FONT, font_size=9,
                                command=self.show_overview)
        tl2.addWidget(self.tab_work)
        tl2.addWidget(self.tab_over)
        lay.addWidget(tabs)

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
    def _build_left(self) -> CFrame:
        col = CFrame(self, border_width=1, corner_radius=12,
                     background_color=PAL["surface"])
        col.setFixedWidth(320)
        lay = col.layout()
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
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
        self.btn_go = ThinkingButton(col, width=200, height=36, text="开始本阶段")
        self.btn_go.clicked.connect(self.primary_action)
        lay.addWidget(self.btn_go)
        return col

    # ---------------------------------------------------------------- 中栏
    def _build_center(self) -> CFrame:
        col = CFrame(self, border_width=1, corner_radius=12,
                     background_color=PAL["surface"])
        self.center_col = col
        lay = col.layout()
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        head = QWidget(col)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        self.center_title = mk_label(head, "工作区", size=12, bold=True,
                                     color=PAL["accent"],
                                     width_px=520, wrap=False)
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
    def _build_right(self) -> CFrame:
        col = CFrame(self, border_width=1, corner_radius=12,
                     background_color=PAL["surface2"])
        col.setFixedWidth(420)
        self.right_col = col
        lay = col.layout()
        lay.setContentsMargins(16, 10, 16, 12)      # 上边距收紧，给文档框让高度
        lay.setSpacing(7)
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
        self.status = mk_label(f, "", size=9, width_px=900,
                               color=PAL["muted"])
        lay.addWidget(self.status, 1)
        self.progress = ProgressBar(f, width=160, height=8)
        wrap = QWidget(f)
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wrap.setFixedSize(160, 28)
        wl.addWidget(self.progress, 0, Qt.AlignVCenter)
        lay.addWidget(wrap)
        self.tip = mk_label(f, "Space 继续 · Ctrl+S 保存 · Ctrl+E 导出 · ⇧E 出 Word",
                            size=9, align="right", width_px=260,
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
        if hasattr(self, "body_stack") and self.body_stack.currentIndex() == 1:
            self.refresh_overview()
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
        self.status.label().setText(
            f"项目 {self.project.name}　·　"
            f"阶段 {self.current_index() + 1}/10 {STAGES[self.current_index()]['title']}"
            + (f"　·　{extra}" if extra else ""))

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
            self.new_project(confirm=False)

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
        for w in self.findChildren(QWidget):
            fn = getattr(w, "_change_theme", None)
            if callable(fn):
                try:
                    fn()
                except Exception:                                  # noqa: BLE001
                    pass
        if hasattr(self, "body_stack") and self.body_stack.currentIndex() == 1:
            self.refresh_overview()
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
    def _run(self, messages: list, on_done, max_tokens: int | None = None):
        if self._busy():
            return
        holder = {"text": ""}

        def on_delta(piece: str, kind: str):
            holder["text"] += piece
            if kind == "content":
                self.transcript.stream(piece)

        self.thread = LLMThread(self.client, messages, stream=True, parent=self,
                                max_tokens=max_tokens)
        self.thread.delta.connect(on_delta)
        self.thread.failed.connect(self._on_failed)

        def finished(out: dict):
            self.thread = None                     # 先释放，避免后续链条被 busy 挡掉
            self.transcript.end_stream()
            out["content"] = out.get("content") or holder["text"]
            if not holder["text"].strip() and out["content"].strip():
                self.transcript.add_text_block(out["content"])   # 重试后的整段补显
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
        self.left_col.setFixedWidth(292 if narrow else 320)
        if hasattr(self, "side_col"):
            self.side_col.setFixedWidth(322 if narrow else 420)
        if hasattr(self, "header"):
            self.header.setFixedHeight(112 if narrow else 96)
        for name, wd in (("search", 150 if narrow else 210),
                         ("project_box", 150 if narrow else 190),
                         ("model_box", 158 if narrow else 190),
                         ("new_btn", 54 if narrow else 64),
                         ("manage_btn", 54 if narrow else 64),
                         ("settings_btn", 54 if narrow else 64),
                         ("mode_btn", 54 if narrow else 64)):
            wdg = getattr(self, name, None)
            if wdg is not None:
                wdg.setFixedWidth(wd)
        if narrow != getattr(self, "_narrow", None):
            self._narrow = narrow
            self._refresh_doc()                 # 元信息文案随宽度切换，避免换行被截
        else:
            self._narrow = narrow

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive()

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
