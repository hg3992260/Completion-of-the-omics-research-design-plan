# -*- coding: utf-8 -*-
"""精确复现：只改 id 类型，其他完全一致。

用法: python repro_id.py int|str
"""
from _bootstrap import ROOT, EXAMPLES, sample_manuscript, annotated_sample
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PySide6 import QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
import design_studio as ds
from design_studio import StageRail, WorkScroll, Card
from PyCt6 import set_appearance_mode, set_color_theme
from ui_kit import install_button_skin, CARD_PAD

set_color_theme(ds.THEME_PATH)
set_appearance_mode("light")
install_button_skin()

MODE = sys.argv[1] if len(sys.argv) > 1 else "str"
# 中文标题、3 条、全部 todo —— 唯一变量就是 id 是 int 还是 str
items = [
    {"id": (1 if MODE == "int" else "omics"), "title": "引导式组学", "spec": "TRIPOD+AI"},
    {"id": (2 if MODE == "int" else "stat"), "title": "统计", "spec": "9 阶段"},
    {"id": (3 if MODE == "int" else "shape"), "title": "撰写", "spec": "七章模型"},
]
print(f"模式={MODE}  id={[s['id'] for s in items]}", flush=True)
print(f"  首条 title={items[0]['title']!r}", flush=True)

host = QtWidgets.QWidget()
lay = QtWidgets.QVBoxLayout(host)
card = Card(host, margin=(14, 14, 14, 14), spacing=10)
card.setFixedWidth(320 + 2 * CARD_PAD)
sc = WorkScroll(card)
rail = StageRail(sc, items)
rail.set_states({s["id"]: "todo" for s in items}, 0)
sc.setWidget(rail)
card.layout().addWidget(sc, 1)
lay.addWidget(card)
host.resize(400, 900)
host.show()
print("shown", flush=True)
for i in range(5):
    app.processEvents()
print("processEvents OK", flush=True)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"repro_{MODE}.png")
host.grab().save(out)
print("grab OK -> 通过", flush=True)
