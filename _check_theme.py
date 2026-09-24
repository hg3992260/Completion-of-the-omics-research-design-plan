# -*- coding: utf-8 -*-
"""主题一致性检查：浅色构建 → 切深色（再切回），逐控件核对颜色是否跟着主题更新。

检查三类问题：
  1) 颜色被冻结：样式的实际色与「当前模式应有的色」不一致（多见于把 C() 结果当常量传进去）；
  2) 前景 = 背景：文字色与其背景色相同（就是"白字白底"无法显示）；
  3) 深色下仍是浅色底：背景色等于某个 PAL 键的浅色值而其深色值不同。

用法： python _check_theme.py     产出 _theme_report.txt，有违规时退出码 1
"""
import io
import re
import sys

sys.argv = ["x", "--demo"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtGui

import design_studio as ds
from ui_kit import PAL, C

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=True)
win._no_flush = True
win.resize(1520, 960)
win.show()

HEX = re.compile(r"#([0-9a-fA-F]{6})")
RGB = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")


def norm(v):
    """把 #RRGGBB / rgb(r,g,b) / rgba(...) 统一成小写 #rrggbb；其他原样返回。"""
    if not v:
        return None
    v = v.strip()
    m = HEX.search(v)
    if m:
        return "#" + m.group(1).lower()
    m = RGB.search(v)
    if m:
        return "#%02x%02x%02x" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return v.lower()


def resolve(val, dark: bool):
    if val is None:
        return None
    if isinstance(val, (tuple, list)):
        return val[1] if dark else val[0]
    return val


LIGHT_VALUES = {}
DARK_VALUES = {}
for k, v in PAL.items():
    if isinstance(v, (tuple, list)) and len(v) == 2:
        LIGHT_VALUES.setdefault(norm(v[0]), set()).add(k)
        DARK_VALUES.setdefault(norm(v[1]), set()).add(k)


def scan(tag: str):
    dark = C("bg") == PAL["bg"][1]
    ok_values = DARK_VALUES if dark else LIGHT_VALUES      # 当前模式下合法的调色板取值
    bad_frozen, bad_same, bad_light = [], [], []
    for lbl in win.findChildren(ds.CLabel):
        inner = lbl.label()
        text = (inner.text() or "").strip()
        if not text:
            continue
        css = inner.styleSheet() or ""
        # 注意：`color:` 会匹配到 `background-color:` 内部，必须用否定后顾
        mc = re.search(r"(?<![-\w])color:\s*([^;]+);", css)
        mb = re.search(r"background-color:\s*([^;]+);", css)
        got_c = norm(mc.group(1)) if mc else None
        got_b = norm(mb.group(1)) if mb else None
        exp_c = norm(resolve(getattr(lbl, "_text_color", None), dark))
        exp_b = norm(resolve(getattr(lbl, "_background_color", None), dark))
        # 冻结判定：实际色既不是该控件应有的色，也不是当前模式调色板里的任何色
        if exp_c and got_c and got_c != exp_c and got_c not in ok_values:
            bad_frozen.append(f"色不符 {text[:26]!r} 实际={got_c} 应为={exp_c}")
        if exp_b and got_b and got_b != exp_b and got_b not in ok_values:
            bad_frozen.append(f"底色不符 {text[:26]!r} 实际={got_b} 应为={exp_b}")
        if got_c and got_b and got_c == got_b:
            bad_same.append(f"前景=背景 {got_c} | {text[:30]!r}")
        if dark and got_b and got_b in LIGHT_VALUES:
            keys = "/".join(sorted(LIGHT_VALUES[got_b]))
            if norm(resolve(PAL[list(LIGHT_VALUES[got_b])[0]], True)) != got_b:
                bad_light.append(f"深色下仍是浅色底 {got_b}（{keys}）| {text[:26]!r}")
    lines = [f"[{tag}] 冻结色 {len(bad_frozen)}｜前景=背景 {len(bad_same)}｜"
             f"浅色底残留 {len(bad_light)}"]
    for t in (bad_frozen, bad_same, bad_light):
        lines += ["    " + x for x in t[:12]]
    return lines, len(bad_frozen) + len(bad_same) + len(bad_light)


def lum(c):
    return 0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()


def pixel_contrast(widget, tag: str, min_delta: float = 90.0):
    """像素级验收：抓取卡片，逐行找"有文字"的行，检查其最大对比度是否足够。

    这是对用户症状（白字白底/看不见）的直接检验——不看样式表，只看渲染结果。
    """
    from collections import Counter
    img = widget.grab().toImage()
    W, H = img.width(), img.height()
    bad_bands, y = [], 0
    cur = None
    while y < H:
        cols = [QtGui.QColor(img.pixel(x, y)) for x in range(20, max(21, W - 20))]
        if not cols:
            break
        bg = QtGui.QColor(Counter(c.name() for c in cols).most_common(1)[0][0])
        deltas = [abs(lum(c) - lum(bg)) for c in cols]
        strong = [d for d in deltas if d > 50]        # 明显不同于本行底色的像素
        dense = len(strong) / max(1, len(deltas))
        # 文字是"稀疏但明显"的：像素数够、占比低（描边/阴影线是满行的，占比高）
        is_text = len(strong) >= 15 and dense < 0.55
        mx = max(deltas) if deltas else 0.0
        if is_text and mx < min_delta:               # 有文字但对比不足
            if cur is None:
                cur = [y, y, mx]
            cur[1] = y
            cur[2] = min(cur[2], mx)
        else:
            if cur is not None:
                bad_bands.append(tuple(cur))
                cur = None
        y += 1
    if cur is not None:
        bad_bands.append(tuple(cur))
    lines = [f"[像素验收 {tag}] 低对比文字带 {len(bad_bands)} 处"
             f"（阈值 Δ≥{min_delta:.0f}）"]
    for y0, y1, d in bad_bands[:8]:
        lines.append(f"    y={y0}-{y1} 最大对比 Δ={d:.0f}")
    return lines, len(bad_bands)


def run():
    report, total = [], 0
    for view_name, fn, pick in (("Statistic", win.show_stat, 1),
                                ("SCI Shape", win.show_sci_shape, 3),
                                ("总览", win.show_overview, None),
                                ("工作台", win.show_workspace, None)):
        fn()
        if pick is not None:
            (win.stat_page if view_name == "Statistic" else win.shape_page).pick(pick)
        for _ in range(3):
            win.layout().activate()
            QApplication.processEvents()
        lines, n = scan(f"浅色 {view_name}")
        report += lines
        total += n
    # 切深色（这是用户实际遇到问题的场景）
    win.toggle_mode()
    for view_name, fn, pick in (("Statistic", win.show_stat, 1),
                                ("SCI Shape", win.show_sci_shape, 3),
                                ("总览", win.show_overview, None),
                                ("工作台", win.show_workspace, None)):
        fn()
        if pick is not None:
            (win.stat_page if view_name == "Statistic" else win.shape_page).pick(pick)
        for _ in range(3):
            win.layout().activate()
            QApplication.processEvents()
        lines, n = scan(f"深色 {view_name}")
        report += lines
        total += n
    # 负向自检：在深色下故意写死一个浅色底，检查器必须检出（否则形同虚设）
    probe = next((lbl for lbl in win.findChildren(ds.CLabel)
                  if (lbl.label().text() or "").strip()), None)
    if probe is not None:
        keep = probe._background_color
        probe._background_color = "#F5F9FE"        # = PAL surface2 的浅色值
        probe._change_theme()
        QApplication.processEvents()
        _, n_probe = scan("负向自检")
        report.append(f"[负向自检] 注入浅色底后检出 {n_probe} 项 → "
                      f"{'检出成功 ✓' if n_probe else '未检出 ✗（检查器失效）'}")
        total += 0 if n_probe else 1               # 没检出才算失败
        probe._background_color = keep
        probe._change_theme()
        QApplication.processEvents()
    # 像素级验收：深色下两张页面的中栏与右栏（用户报的就是这两页）
    for name, page in (("Statistic", win.stat_page), ("SCI Shape", win.shape_page)):
        win.show_stat() if name == "Statistic" else win.show_sci_shape()
        page.pick(1)
        for _ in range(3):
            win.layout().activate()
            QApplication.processEvents()
        for part in ("center", "side"):
            lines, n = pixel_contrast(getattr(page, part), f"深色 {name}.{part}")
            report += lines
            total += n
    # 切回浅色，确认可逆
    win.toggle_mode()
    for _ in range(2):
        win.layout().activate()
        QApplication.processEvents()
    lines, n = scan("切回浅色 工作台")
    report += lines
    total += n
    out = "\n".join(report) + f"\n\n违规总数: {total}\n"
    io.open("_theme_report.txt", "w", encoding="utf-8").write(out)
    print(out)
    app.quit()
    sys.exit(1 if total else 0)


from PySide6 import QtCore                                          # noqa: E402
QtCore.QTimer.singleShot(1300, run)
QtCore.QTimer.singleShot(60000, lambda: (print("看门狗超时", flush=True), app.quit()))
sys.exit(app.exec())
