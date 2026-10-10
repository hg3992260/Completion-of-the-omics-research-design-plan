# -*- coding: utf-8 -*-
"""高对比拟物化三维皮肤库（skeuo_kit）。

设计目标（用户要求）：**更高对比度** + **更拟物化的三维风格**，深浅两套，深色优先。

它做两件事：

1. **换掉调色板**：把 ``ui_kit.PAL`` 里那套偏"柔和弥散"的配色替换成高对比版本
   （更深的底、更亮的字、更硬的边、更强的受光/背光色阶）。因为 ``ui_kit.C()`` 与
   ``Card`` / ``CheckBox3D`` / ``ProgressBar`` / ``FlowStepper`` / ``CreditBar`` /
   ``BusyIndicator`` / ``ThinkingButton`` 都是按 key 取色并自绘，所以只换调色板就能让
   这些既有构件整体变得更"立体 + 高对比"，不需要动它们的绘制代码。

2. **给 PyCt6 控件套三维皮肤**：按钮/输入框/下拉/滑条/文本域/滚动条。
   全部用 **运行时包装**（monkey-patch ``_change_theme``）实现，不修改 PyCt6 源码。
   关键点：亮面/暗面颜色不是写死的，而是**从控件自己的底色推出来**的
   （``raised()`` / ``inset()`` / ``facet()``），所以强调色按钮、中性按钮、危险按钮、
   禁用态都能自动得到正确的立体感，不会出现"只有某一种按钮好看"的情况。

用法::

    import ui_kit, skeuo_kit
    skeuo_kit.install(ui_kit)            # 换调色板 + 套所有控件皮肤
    # 之后照常 set_appearance_mode("dark"/"light")，皮肤会自动跟着重画

注意：装了本库之后 **不要再调用** ``ui_kit.install_button_skin()``
（那是旧版弱渐变皮肤，会被本库覆盖；本库是其超集）。
"""

from __future__ import annotations

import os
import re
import tempfile

from PySide6 import QtCore, QtGui
from PySide6.QtCore import QRectF, Qt

from PyCt6 import (CButton, CComboBox, CFrame, CLabel, CLineEdit, CSlider,
                   CTextEdit, ModeManager)

# ===========================================================================
# 1. 高对比调色板
# ===========================================================================
# 每项都是 (浅色, 深色)。键位是原 PAL 的**超集**：前 44 个键与原 ui_kit.PAL 完全同名，
# 保证既有代码 / 自绘构件零改动即可生效；后面是本库新增的三维与部件专用色。
PAL_HC: dict[str, tuple[str, str]] = {
    # ---- 基底：浅色把底压深（让白卡片跳出来），深色压到近黑（让面板跳出来）----
    # 深色一栏整体比浅色"抬一档"：近黑底上的大面积渐变在亮度上天然被压缩，
    # 立体感只能靠"面更亮 + 倒角更狠"来补，所以深色面不用纯黑。
    "bg":          ("#D9E4F1", "#07080B"),
    "surface":     ("#FFFFFF", "#1D2129"),
    "surface2":    ("#F1F6FB", "#0E1015"),
    "node":        ("#FFFFFF", "#22262E"),
    "node_hover":  ("#E7F0FA", "#2C323D"),
    "node_active": ("#D6E9FA", "#43301A"),
    "border":      ("#A7BFD7", "#454D59"),      # 边更硬 → 轮廓更清楚
    "grid":        ("#B4C8DA", "#2E343D"),

    # ---- 主色：浅色更深（白字更稳），深色更亮更饱和 ----
    "accent":       ("#0A6BB4", "#FF8A2A"),
    "accent_dim":   ("#5F9CC7", "#7C4413"),
    "accent_hover": ("#085C9C", "#FFA452"),
    "on_accent":    ("#FFFFFF", "#1A0D02"),

    # ---- 文字：拉大层级差（深色一栏比基线更亮，补偿"面被抬亮"带来的对比损失）----
    "text":      ("#0A1626", "#F3F5F9"),
    "muted":     ("#4C6076", "#BCC3CD"),
    "muted_dim": ("#3E5060", "#A3ABB8"),

    # ---- 状态色：更饱和、更亮 ----
    "ok":    ("#067A58", "#35D69C"),
    "warn":  ("#8F5B14", "#FBBF24"),
    "bad":   ("#A8351C", "#FC7285"),
    "danger":    ("#B23A20", "#FC7285"),
    "danger_bg": ("#FBE9E4", "#2C1417"),

    "track": ("#C3D4E5", "#12151A"),
    "user":  ("#0A6BB4", "#FFA452"),
    "agent": ("#067A58", "#35D69C"),
    "btn":       ("#F7FAFD", "#272C35"),
    "btn_hover": ("#E8F1F9", "#333944"),

    # ---- 三维色阶：受光面 / 背光面、上缘高光 / 下缘暗边、凹槽、凸件 ----
    "surf_hi":  ("#FFFFFF", "#333A46"),
    "surf_lo":  ("#E1EAF4", "#0A0B0E"),
    "bevel_hi": ("#FFFFFF", "#545E6E"),          # 上缘高光更亮（但不过亮：过亮会被 "低对比文字带" 检查误判成文字行）
    "bevel_lo": ("#8FA8C0", "#000000"),          # 下缘暗边更黑
    "shadow":   ("#6F8CA8", "#000000"),

    "groove_hi": ("#93AAC0", "#050608"),         # 凹槽：上缘暗
    "groove_lo": ("#FFFFFF", "#454D59"),         # 凹槽：下缘亮
    "knob_hi":   ("#FFFFFF", "#4A525F"),
    "knob_lo":   ("#CFDEEE", "#0C0E11"),

    "accent_hi": ("#3E9BDA", "#FFB067"),
    "accent_lo": ("#064E82", "#CE5F0C"),
    "ok_hi":     ("#2BB183", "#5CE6AE"),
    "ok_lo":     ("#045B41", "#12A06D"),
    "warn_hi":   ("#C98A2E", "#FFD166"),
    "warn_lo":   ("#6B440E", "#D69B14"),
    "bad_hi":    ("#CC5A3C", "#FF9AA6"),
    "bad_lo":    ("#8A2A14", "#C6475A"),

    # 页面底衬：中心亮 / 边缘暗的径向渐变（纵深更大 → 更像"打着光的实体"）
    # 注意：边缘**不要压到纯黑**。纯黑会让卡片边缘 vs 底衬的亮度差跨过 50 的"显著像素"
    # 阈值，被 _check_theme 的"低对比文字带"启发式误判成文字行（实测 y=98/108 两行）。
    "back_hi": ("#FDFEFF", "#262C38"),
    "back_lo": ("#C2D4E6", "#0A0C11"),

    # =====================================================================
    # 以下为本库新增（会话窗口等新界面用；既有构件不引用也不受影响）
    # =====================================================================
    "panel_hi":  ("#FFFFFF", "#262B34"),         # 大面板受光面
    "panel_lo":  ("#E6EEF7", "#0C0E12"),         # 大面板背光面
    "edge_hi":   ("#FFFFFF", "#4A5361"),         # 通用上缘高光
    "edge_lo":   ("#93AAC0", "#000000"),         # 通用下缘暗边
    "divider":   ("#B9CCDE", "#31363F"),
    "gloss":     ("#FFFFFF", "#FFFFFF"),         # 玻璃高光（叠加时靠 alpha 控制）
    "focus":     ("#0A6BB4", "#FF8A2A"),         # 焦点环

    # 气泡 / 卡片
    "bubble_user_hi":   ("#E9F3FD", "#452F14"),
    "bubble_user_lo":   ("#D3E7FA", "#26190A"),
    "bubble_user_edge": ("#8CB7DA", "#7A5522"),
    "bubble_ai_hi":     ("#FFFFFF", "#262B33"),
    "bubble_ai_lo":     ("#EDF3FA", "#101318"),
    "bubble_ai_edge":   ("#B4C9DC", "#3E4551"),

    # 工具调用卡片
    "tool_hi":   ("#FBFDFF", "#2A3038"),
    "tool_lo":   ("#E7EFF8", "#101317"),
    "tool_edge": ("#A9C0D6", "#454D59"),
    "tool_bar":  ("#0A6BB4", "#FF8A2A"),

    # 代码 / 终端
    "code_bg":   ("#F4F8FC", "#0B0D11"),
    "code_edge": ("#B4C9DC", "#2B313A"),
    "code_text": ("#123A5A", "#D8E2EE"),

    # 选中 / 徽标
    "sel_bg":   ("#CFE5F8", "#4A3418"),
    "badge_bg": ("#E3EDF7", "#2C323B"),

    # 滚动条
    "scroll_hi":    ("#FFFFFF", "#4A525E"),
    "scroll_lo":    ("#C6D6E6", "#20242B"),
    "scroll_hover": ("#FFFFFF", "#5A6472"),

    "title_text": ("#08121F", "#FFFFFF"),
}


# ===========================================================================
# 2. 颜色数学
# ===========================================================================
def dark_mode() -> bool:
    """当前是否深色（与 ui_kit.C() 的判定口径保持一致）。"""
    mode = ModeManager.mode
    if mode == "dark":
        return True
    if mode == "light":
        return False
    return QtGui.QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


_CSS_RGB = re.compile(
    r"rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*(?:,\s*([0-9.]+)\s*)?\)",
    re.IGNORECASE)


def resolve(spec) -> QtGui.QColor:
    """把 (浅, 深) / 单色 / QColor 统一解析成当前模式下的一支 QColor。

    ⚠️ 必须自己解析 CSS 的 ``rgb()/rgba()``：PyCt6 的 theme JSON 里颜色就是这种写法，
    而 ``QColor("rgb(243, 245, 249)")`` 在 Qt 里是**无效色**（只认 #RRGGBB 与 SVG 色名），
    name() 会退化成 #000000 —— 那会让输入框的字无声无息变成黑色。
    """
    if isinstance(spec, QtGui.QColor):
        return QtGui.QColor(spec)
    if isinstance(spec, (tuple, list)):
        spec = spec[1] if dark_mode() else spec[0]
    s = str(spec).strip()
    m = _CSS_RGB.fullmatch(s)
    if m:
        r, g, b = (int(float(m.group(i))) for i in (1, 2, 3))
        a = int(float(m.group(4)) * 255) if m.group(4) is not None else 255
        return QtGui.QColor(r, g, b, a)
    return QtGui.QColor(s)


def lighten(c: QtGui.QColor, f: float) -> QtGui.QColor:
    """向白靠 f（保留色相）。"""
    f = max(0.0, min(1.0, f))
    return QtGui.QColor(int(c.red() + (255 - c.red()) * f),
                        int(c.green() + (255 - c.green()) * f),
                        int(c.blue() + (255 - c.blue()) * f))


def darken(c: QtGui.QColor, f: float) -> QtGui.QColor:
    """向黑靠 f。"""
    f = max(0.0, min(1.0, f))
    return QtGui.QColor(int(c.red() * (1 - f)), int(c.green() * (1 - f)),
                        int(c.blue() * (1 - f)))


def lum(c: QtGui.QColor) -> float:
    return 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()


def alpha(c: QtGui.QColor, a: int) -> QtGui.QColor:
    out = QtGui.QColor(c)
    out.setAlpha(max(0, min(255, a)))
    return out


def _strength() -> float:
    """立体强度：深色主题需要更大的明暗差才看得出来；浅色主题要收敛。

    （早期版本按"底色亮度"取值，结果浅色主题里的深蓝按钮被当成深色底，
    加白过猛 → 白字压在亮面上，对比度掉到 2.8:1。改为按**模式**取值。）
    """
    return 1.0 if dark_mode() else 0.60


def facet(base: QtGui.QColor, *, gloss: bool = False) -> tuple[QtGui.QColor, ...]:
    """从任意底色推出立体面：返回 (顶高光, 中面, 底暗, 边高光, 边暗边)。

    这是整套皮肤的核心：**不写死颜色**，所以强调色/中性/危险/禁用态都能自动成立。
    """
    s = _strength()
    top = lighten(base, (0.30 if gloss else 0.18) * s)
    mid = QtGui.QColor(base)
    bot = darken(base, (0.38 if gloss else 0.26) * s)
    edge_hi = lighten(base, 0.60 * s)
    edge_lo = darken(base, 0.55 * s)
    return top, mid, bot, edge_hi, edge_lo


def gloss_stops(base: QtGui.QColor) -> list[tuple[float, QtGui.QColor]]:
    """玻璃帽渐变：顶部一条**窄**镜面高光，中段保持底色，底部收暗。

    关键在"窄"：文字压在按钮中部，如果整块上半都提亮，白字就糊在亮面上
    （实测浅色主按钮会掉到 2.8:1）。把高光压到顶部 ~9% 高度，既有玻璃感，
    又保证文字所在区域≈底色，对比度不被牺牲。
    """
    s = _strength()
    return [(0.0, lighten(base, 0.46 * s)),
            (0.09, lighten(base, 0.13 * s)),
            (0.52, QtGui.QColor(base)),
            (1.0, darken(base, 0.34 * s))]


def vgrad(rect: QRectF, top: QtGui.QColor, bot: QtGui.QColor,
          mid: QtGui.QColor | None = None, split: float = 0.5) -> QtGui.QBrush:
    g = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
    if mid is None:
        g.setColorAt(0.0, top)
        g.setColorAt(1.0, bot)
    else:
        g.setColorAt(0.0, top)
        g.setColorAt(split, mid)
        g.setColorAt(1.0, bot)
    return QtGui.QBrush(g)


def raised(rect: QRectF, base: QtGui.QColor, *, gloss: bool = False) -> QtGui.QBrush:
    """凸起面（按钮 / 键帽 / 面板）。gloss=True 时做窄镜面高光的玻璃帽。"""
    if gloss:
        g = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
        for pos, c in gloss_stops(base):
            g.setColorAt(pos, c)
        return QtGui.QBrush(g)
    top, mid, bot, _, _ = facet(base, gloss=False)
    return vgrad(rect, top, bot, mid, 0.55)


def inset(rect: QRectF, base: QtGui.QColor) -> QtGui.QBrush:
    """内嵌面（输入井 / 凹槽 / 轨道）：上暗下亮，与凸起相反。

    深色主题要挖得更深：近黑底上 0.14 的提亮几乎看不出来。
    """
    deep = dark_mode()
    top = darken(base, 0.45 if deep else 0.30)
    bot = lighten(base, 0.22 if deep else 0.14)
    return vgrad(rect, top, bot, QtGui.QColor(base), 0.62)


def _css(c: QtGui.QColor) -> str:
    if c.alpha() < 255:
        return "rgba(%d,%d,%d,%d)" % (c.red(), c.green(), c.blue(), c.alpha())
    return "rgb(%d,%d,%d)" % (c.red(), c.green(), c.blue())


def grad_css(stops: list[tuple[float, QtGui.QColor]]) -> str:
    """竖向 qlineargradient 的 CSS 片段（stops 必须是预先算好的颜色对象）。"""
    body = ", ".join("stop:%g %s" % (p, _css(c)) for p, c in stops)
    return "qlineargradient(x1:0, y1:0, x2:0, y2:1, " + body + ")"


# ===========================================================================
# 3. Qt 样式表生成（统一用 % 模板，避免 f-string 花括号/跨行表达式的坑）
# ===========================================================================
_ARROW_CACHE: dict[str, str] = {}


def arrow_png() -> str:
    """生成一枚跟随调色板的下拉箭头 PNG。

    PyCt6 的下拉箭头是**图片资源**（``::drop-down { image: url(...) }``，28px 固定盒），
    没法用 QSS 改颜色 —— 深色主题下它那枚深灰箭头几乎看不见。这里按当前模式画一枚
    高对比 chevron 并用 url() 指过去，两个主题都能看清。
    """
    key = "dark" if dark_mode() else "light"
    cached = _ARROW_CACHE.get(key)
    if cached and os.path.exists(cached):
        return cached.replace("\\", "/")
    size = 28
    pm = QtGui.QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    col = resolve(PAL_HC["text"] if key == "dark" else PAL_HC["muted_dim"])
    pen = QtGui.QPen(col, 2.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawPolyline(QtGui.QPolygonF([QtCore.QPointF(9.0, 11.5),
                                    QtCore.QPointF(14.0, 17.0),
                                    QtCore.QPointF(19.0, 11.5)]))
    p.end()
    out = os.path.join(tempfile.gettempdir(), "skeuo_arrow_%s.png" % key)
    pm.save(out)
    _ARROW_CACHE[key] = out
    return out.replace("\\", "/")


def _widget_base(w) -> QtGui.QColor:
    """取控件被显式指定的底色（没指定/解析不出来就用主题中性面）。"""
    raw = getattr(w, "_background_color", None)
    if raw is None or (isinstance(raw, str) and raw.lower() in ("none", "transparent")):
        return resolve(PAL_HC["btn"])
    c = resolve(raw)
    return c if c.isValid() else resolve(PAL_HC["btn"])


def _widget_text(w, fallback: str = "text") -> QtGui.QColor:
    raw = getattr(w, "_text_color", None)
    if raw is None:
        return resolve(PAL_HC[fallback])
    c = resolve(raw)
    return c if c.isValid() else resolve(PAL_HC[fallback])


def _widget_radius(w, dflt: int = 9) -> int:
    r = getattr(w, "_corner_radius", None)
    try:
        return int(r) if r is not None else dflt
    except Exception:                                            # noqa: BLE001
        return dflt


BUTTON_TMPL = (
    "QPushButton {"
    " background: %(face)s;"
    " color: %(txt)s;"
    " border: 1px solid %(e_lo)s;"
    " border-top: 1px solid %(e_hi)s;"
    " border-radius: %(r)dpx;"
    " padding: 3px 12px; font-weight: 600; }"
    "QPushButton:hover {"
    " background: %(hover)s;"
    " border-top: 1px solid %(hover_edge)s; }"
    # 按下：整体压暗 + 上下边**对调**（上暗下亮）= 视觉上真的凹进去了
    "QPushButton:pressed {"
    " background: %(press)s;"
    " border: 1px solid %(press_edge)s;"
    " border-top: 1px solid %(press_edge)s;"
    " border-bottom: 1px solid %(press_lite)s;"
    " padding-top: 5px; padding-bottom: 1px; }"
    "QPushButton:disabled {"
    " background: %(dis)s;"
    " color: %(dis_txt)s;"
    " border: 1px solid %(dis_edge)s; }"
)


def button_qss(w) -> str:
    """按钮：玻璃帽渐变 + 上缘高光/下缘暗边 + 按下时反向（真正"被按进去"）。"""
    base = _widget_base(w)
    txt = _widget_text(w)
    r = _widget_radius(w, 8)
    top, mid, bot, e_hi, e_lo = facet(base, gloss=True)
    hover = lighten(base, 0.18 if dark_mode() else 0.12)
    press = darken(base, 0.34)
    return BUTTON_TMPL % {
        "face": grad_css(gloss_stops(base)),
        "txt": _css(txt),
        "e_lo": _css(e_lo),
        "e_hi": _css(e_hi),
        "r": r,
        "hover": grad_css(gloss_stops(hover)),
        "hover_edge": _css(lighten(hover, 0.70)),
        "press": grad_css([(0.0, press), (0.55, darken(press, 0.18)),
                           (1.0, lighten(press, 0.10))]),
        "press_edge": _css(darken(press, 0.50)),
        "press_lite": _css(lighten(press, 0.22)),
        "dis": grad_css([(0.0, lighten(base, 0.06)), (1.0, darken(base, 0.10))]),
        "dis_txt": _css(alpha(txt, 110)),
        "dis_edge": _css(alpha(e_lo, 120)),
    }


INPUT_TMPL = (
    "QLineEdit, QTextEdit, QPlainTextEdit {"
    " background: %(bg)s;"
    " color: %(txt)s;"
    " border: 1px solid %(edge)s;"
    " border-top: 1px solid %(e_hi)s;"
    " border-bottom: 1px solid %(e_lo)s;"
    " border-radius: %(r)dpx; padding: 3px 8px;"
    " selection-background-color: %(sel)s;"
    " selection-color: %(sel_txt)s; }"
    "QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {"
    " border: 2px solid %(focus)s;"
    " border-top: 2px solid %(focus_lo)s;"
    " padding: 2px 7px; }"
    "QLineEdit:disabled, QTextEdit:disabled { color: %(dis_txt)s; }"
)


def input_qss(w, *, radius: int = 8) -> str:
    """输入井：内嵌渐变 + 上缘暗线（内阴影）+ 下缘亮线 + 聚焦环。"""
    base = resolve(PAL_HC["surface2"])
    txt = _widget_text(w)
    focus = resolve(PAL_HC["focus"])
    return INPUT_TMPL % {
        "bg": grad_css([(0.0, darken(base, 0.22)), (1.0, lighten(base, 0.10))]),
        "txt": _css(txt),
        "edge": _css(resolve(PAL_HC["border"])),
        "e_hi": _css(resolve(PAL_HC["groove_hi"])),
        "e_lo": _css(resolve(PAL_HC["groove_lo"])),
        "r": radius,
        "sel": _css(resolve(PAL_HC["accent"])),
        "sel_txt": _css(resolve(PAL_HC["on_accent"])),
        "focus": _css(focus),
        "focus_lo": _css(darken(focus, 0.25)),
        "dis_txt": _css(alpha(txt, 110)),
    }


SCROLL_TMPL = (
    "QScrollBar:vertical { background: %(track)s; width: %(w)dpx;"
    " border: 1px solid %(track_edge)s; border-radius: %(half)dpx; margin: 2px; }"
    "QScrollBar::handle:vertical { background: %(handle)s;"
    " border: 1px solid %(edge)s; border-radius: %(half1)dpx; min-height: 34px; }"
    "QScrollBar::handle:vertical:hover { background: %(handle_h)s; }"
    "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
    "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
    "QScrollBar:horizontal { background: %(track)s; height: %(w)dpx;"
    " border: 1px solid %(track_edge)s; border-radius: %(half)dpx; margin: 2px; }"
    "QScrollBar::handle:horizontal { background: %(handle)s;"
    " border: 1px solid %(edge)s; border-radius: %(half1)dpx; min-width: 34px; }"
    "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
)


def scroll_qss(width: int = 12) -> str:
    """滚动条：凹槽 + 凸起滑块（带高光），高对比。"""
    track = resolve(PAL_HC["track"])
    hi = resolve(PAL_HC["scroll_hi"])
    lo = resolve(PAL_HC["scroll_lo"])
    hov = resolve(PAL_HC["scroll_hover"])
    return SCROLL_TMPL % {
        "track": _css(track),
        "track_edge": _css(darken(track, 0.30)),
        "w": width,
        "half": width // 2,
        "half1": max(2, width // 2 - 1),
        "handle": grad_css([(0.0, hi), (0.5, lo), (1.0, darken(lo, 0.22))]),
        "handle_h": grad_css([(0.0, lighten(hov, 0.25)), (1.0, hov)]),
        "edge": _css(resolve(PAL_HC["border"])),
    }


COMBO_TMPL = (
    "QComboBox { background: %(bg)s; color: %(txt)s;"
    " border: 1px solid %(edge)s;"
    " border-top: 1px solid %(e_hi)s;"
    " border-bottom: 1px solid %(e_lo)s;"
    " border-radius: %(r)dpx; padding: 2px 8px; }"
    "QComboBox QAbstractItemView { background: %(pop)s; color: %(txt)s;"
    " border: 1px solid %(edge)s; border-radius: 8px; padding: 4px; outline: 0;"
    " selection-background-color: %(sel_bg)s; selection-color: %(sel_txt)s; }"
    "QComboBox QAbstractItemView::item { padding: 5px 8px; border-radius: 6px; }"
    "QComboBox QAbstractItemView::item:hover { background: %(sel_bg)s; }"
    # PyCt6 没有 ::item:selected 规则（选中态会退化成平台默认），这里补上
    "QComboBox QAbstractItemView::item:selected {"
    " background: %(sel_bg)s; color: %(sel_txt)s; font-weight: 600; }"
    "QComboBox::drop-down { image: url(\"%(arrow)s\"); width: 28px; height: 28px; border: none; }"
)


def combo_qss(w) -> str:
    """下拉框：本体与输入井同构；弹出列表做成"浮起的实体面板"。"""
    base = resolve(PAL_HC["surface2"])
    return COMBO_TMPL % {
        "bg": grad_css([(0.0, darken(base, 0.22)), (1.0, lighten(base, 0.10))]),
        "txt": _css(_widget_text(w)),
        "edge": _css(resolve(PAL_HC["border"])),
        "e_hi": _css(resolve(PAL_HC["groove_hi"])),
        "e_lo": _css(resolve(PAL_HC["groove_lo"])),
        "r": _widget_radius(w, 8),
        "pop": grad_css([(0.0, resolve(PAL_HC["panel_hi"])), (1.0, resolve(PAL_HC["panel_lo"]))]),
        "sel_bg": _css(resolve(PAL_HC["sel_bg"])),
        "sel_txt": _css(resolve(PAL_HC["title_text"])),
        "arrow": arrow_png(),
    }


SLIDER_TMPL = (
    "QSlider::groove:horizontal { background: %(groove)s; height: %(gh)dpx;"
    " border-radius: %(ghalf)dpx; border: 1px solid %(groove_edge)s; }"
    "QSlider::sub-page:horizontal { background: %(fill)s;"
    " border-radius: %(ghalf)dpx; border: 1px solid %(fill_edge)s; }"
    # 手柄右侧的剩余槽（PyCt6 用 groove 色单独画了 add-page，这里一并对齐成凹陷）
    "QSlider::add-page:horizontal { background: %(groove)s;"
    " border-radius: %(ghalf)dpx; border: 1px solid %(groove_edge)s; }"
    "QSlider::handle:horizontal { background: %(knob)s;"
    " border: 1px solid %(knob_edge)s; width: %(kw)dpx;"
    " margin: -%(km)dpx 0; border-radius: %(khalf)dpx; }"
    "QSlider::handle:horizontal:hover { background: %(knob_h)s; }"
)


def slider_qss(w) -> str:
    """滑条：内嵌槽 + 玻璃帽进度 + 凸起圆钮（带高光）。"""
    kw = getattr(w, "button_width", 14) or 14
    groove = resolve(PAL_HC["track"])
    acc = resolve(PAL_HC["accent"])
    gh = 10
    return SLIDER_TMPL % {
        "groove": grad_css([(0.0, darken(groove, 0.25)), (1.0, lighten(groove, 0.12))]),
        "gh": gh,
        "ghalf": gh // 2,
        "groove_edge": _css(darken(groove, 0.38)),
        "fill": grad_css([(0.0, resolve(PAL_HC["accent_hi"])), (1.0, resolve(PAL_HC["accent_lo"]))]),
        "fill_edge": _css(darken(acc, 0.38)),
        "knob": grad_css([(0.0, resolve(PAL_HC["knob_hi"])), (0.5, lighten(acc, 0.35)),
                          (1.0, resolve(PAL_HC["knob_lo"]))]),
        "knob_edge": _css(darken(acc, 0.42)),
        "kw": kw,
        "km": (kw - gh) // 2 + 1,
        "khalf": kw // 2,
        "knob_h": grad_css([(0.0, QtGui.QColor("#FFFFFF")), (1.0, lighten(acc, 0.25))]),
    }


FRAME_TMPL = (
    "QFrame { background: %(bg)s;"
    " border: 1px solid %(edge)s;"
    " border-top: 1px solid %(e_hi)s;"
    " border-bottom: 1px solid %(e_lo)s;"
    " border-radius: %(r)dpx; }"
)


def frame_qss(w) -> str:
    """面板：竖向渐变 + 上缘高光/下缘暗边 + 硬描边。

    ``background_color="none"``（ui_kit 里纯容器大量使用）必须原样保持透明 ——
    否则 QColor("none") 是无效色，会渲染成黑块。
    """
    raw = getattr(w, "_background_color", None)
    if raw is None or (isinstance(raw, str) and raw.lower() in ("none", "transparent")):
        return ""
    base = resolve(raw)
    if not base.isValid():
        return ""
    top, mid, bot, e_hi, e_lo = facet(base, gloss=False)
    return FRAME_TMPL % {
        "bg": grad_css([(0.0, top), (0.55, mid), (1.0, bot)]),
        "edge": _css(resolve(PAL_HC["border"])),
        "e_hi": _css(e_hi),
        "e_lo": _css(e_lo),
        "r": _widget_radius(w, 12),
    }


# ===========================================================================
# 4. 自绘助手（给新界面里的自绘控件用；既有 ui_kit 构件靠换调色板即可）
# ===========================================================================
def draw_contact_shadow(p: QtGui.QPainter, rect: QRectF, radius: float,
                        *, depth: float = 1.0, offset: float = 2.0) -> None:
    """接地投影：多层递减，向下偏移（画在 rect 内部预留边距里）。"""
    p.setPen(Qt.PenStyle.NoPen)
    for dy, a in ((3.0, 34), (1.9, 26), (0.9, 18)):
        col = alpha(resolve(PAL_HC["shadow"]), int(a * depth))
        p.setBrush(col)
        p.drawRoundedRect(
            rect.adjusted(-1.0, dy * offset / 2 - 1.0, 1.0, dy * offset / 2 + 1.0),
            radius, radius)


def draw_raised(p: QtGui.QPainter, rect: QRectF, base: QtGui.QColor, radius: float,
                *, gloss: bool = False, gloss_alpha: int = 64) -> None:
    """凸起块：渐变面 + 上缘高光 + 下缘暗边 + 描边 + 玻璃高光条。"""
    _, _, _, e_hi, e_lo = facet(base, gloss=gloss)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(raised(rect, base, gloss=gloss))
    p.drawRoundedRect(rect, radius, radius)
    if gloss:
        band = QRectF(rect.left() + 1.5, rect.top() + 1.2,
                      max(0.0, rect.width() - 3), rect.height() * 0.42)
        p.setBrush(alpha(resolve(PAL_HC["gloss"]), gloss_alpha))
        p.drawRoundedRect(band, radius * 0.8, radius * 0.8)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QtGui.QPen(e_hi, 1.1))
    p.drawLine(QtCore.QPointF(rect.left() + radius * 0.7, rect.top() + 0.7),
               QtCore.QPointF(rect.right() - radius * 0.7, rect.top() + 0.7))
    p.setPen(QtGui.QPen(e_lo, 1.1))
    p.drawLine(QtCore.QPointF(rect.left() + radius * 0.7, rect.bottom() - 0.7),
               QtCore.QPointF(rect.right() - radius * 0.7, rect.bottom() - 0.7))
    p.setPen(QtGui.QPen(resolve(PAL_HC["border"]), 1.0))
    p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)


def draw_inset(p: QtGui.QPainter, rect: QRectF, base: QtGui.QColor, radius: float) -> None:
    """内嵌块：反向渐变 + 上缘暗线（内阴影）+ 下缘亮线。"""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(inset(rect, base))
    p.drawRoundedRect(rect, radius, radius)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QtGui.QPen(resolve(PAL_HC["groove_hi"]), 1.2))
    p.drawLine(QtCore.QPointF(rect.left() + radius * 0.7, rect.top() + 0.8),
               QtCore.QPointF(rect.right() - radius * 0.7, rect.top() + 0.8))
    p.setPen(QtGui.QPen(resolve(PAL_HC["groove_lo"]), 1.2))
    p.drawLine(QtCore.QPointF(rect.left() + radius * 0.7, rect.bottom() - 0.8),
               QtCore.QPointF(rect.right() - radius * 0.7, rect.bottom() - 0.8))
    p.setPen(QtGui.QPen(resolve(PAL_HC["border"]), 1.0))
    p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)


# ===========================================================================
# 5. 安装
# ===========================================================================
def apply_palette(uk=None) -> None:
    """把高对比调色板灌进 ui_kit.PAL（就地更新，既有 C() 取色立即生效）。"""
    if uk is None:
        import ui_kit as uk                                     # noqa: PLC0415
    uk.PAL.update(PAL_HC)


def _accessor(w):
    for name in ("button", "line_edit", "text_edit", "combo_box", "slider"):
        fn = getattr(w, name, None)
        if callable(fn):
            try:
                return fn()
            except Exception:                                   # noqa: BLE001
                return None
    return w if isinstance(w, QtCore.QObject) else None


def _sync_palette(target) -> None:
    """把字色/占位符色同步进 QPalette。

    QSS 的 ``color`` 不会写回 QPalette，而**占位符文字**（QPalette::PlaceholderText）
    与 QTextEdit 文档的默认字色都走 palette —— 不同步的话，深色主题下占位符几乎看不见
    （实测截图里"课题名称 / 搜索…"就是一片糊）。
    """
    pal = target.palette()
    pal.setColor(QtGui.QPalette.ColorRole.Text, resolve(PAL_HC["text"]))
    pal.setColor(QtGui.QPalette.ColorRole.PlaceholderText, resolve(PAL_HC["muted"]))
    pal.setColor(QtGui.QPalette.ColorRole.Base, resolve(PAL_HC["surface2"]))
    pal.setColor(QtGui.QPalette.ColorRole.Window, resolve(PAL_HC["surface2"]))
    target.setPalette(pal)


def _skin(cls, builder) -> None:
    """包装 cls._change_theme：先让 PyCt6 画自己的，再把我们的样式**追加在后**
    （同优先级下后写的胜出；PyCt6 每次 _change_theme 都是整段 setStyleSheet 覆盖，
    所以"先 orig 再追加"天然幂等，不会无限增长）。

    重入保护：PyCt6 的 setStyleSheet 会同步派发 PaletteChange → changeEvent → 再次
    调用 _change_theme。没有这个开关，内层调用会在外层之前追加一次，导致样式被追加两遍。
    """
    if getattr(cls, "_skeuo_skinned", False):
        return
    orig = cls._change_theme

    def patched(self):
        if getattr(self, "_skeuo_busy", False):
            return orig(self)                     # 重入：只画 PyCt6 自己的，追加交给外层
        self._skeuo_busy = True
        try:
            orig(self)
            target = _accessor(self)
            if target is None:
                return
            target.setStyleSheet((target.styleSheet() or "") + builder(self))
            _sync_palette(target)
        except Exception:                                       # noqa: BLE001
            pass
        finally:
            self._skeuo_busy = False

    cls._change_theme = patched
    cls._skeuo_skinned = True


def _install_app_wide() -> None:
    """给全局 QApplication 挂一份兜底样式（滚动条等原生控件）。"""
    app = QtGui.QGuiApplication.instance()
    if app is not None:
        app.setStyleSheet(scroll_qss())


def install(uk=None, *, palette: bool = True, widgets: bool = True) -> None:
    """一步到位：换调色板 + 给 PyCt6 控件套三维皮肤。可重复调用（幂等）。"""
    if palette:
        apply_palette(uk)
    if widgets:
        _skin(CButton, button_qss)
        _skin(CLineEdit, input_qss)
        _skin(CTextEdit, lambda w: input_qss(w, radius=_widget_radius(w, 10)) + scroll_qss())
        _skin(CComboBox, combo_qss)
        _skin(CSlider, slider_qss)
        _skin(CFrame, frame_qss)
        _install_app_wide()


def install_if_enabled(uk=None, theme_path: str | None = None) -> bool:
    """按开关安装皮肤，供既有程序"一行接入"。

    * 环境变量 ``PCL_SKEUO=0`` 可整体关闭（回退到改动前的观感）。
    * ``theme_path`` 给出时同时把 PyCt6 主题换成高对比版（须含全部 8 段）。
      必须在**创建控件之前**调用才生效 —— PyCt6 在构造时就快照了主题。
    * 任何异常都不抛出：皮肤失败不应该让主程序起不来。
    """
    if os.environ.get("PCL_SKEUO", "1") == "0":
        return False
    try:
        if theme_path and os.path.exists(theme_path):
            from PyCt6 import set_color_theme                          # noqa: PLC0415
            set_color_theme(theme_path)
        install(uk)
        return True
    except Exception:                                                  # noqa: BLE001
        return False
