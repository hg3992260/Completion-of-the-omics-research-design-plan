# -*- coding: utf-8 -*-
"""实测「导出 .md」：文件是否真的产生、内容是否完整、落在哪里。"""
import os
import sys

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

import design_agent as da
import design_studio as ds
from app_paths import app_home, data_path

app = QApplication([])
ds.set_color_theme(ds.THEME_PATH)
ds.set_appearance_mode("light")
win = ds.StudioWindow(demo=False)
win.resize(1638, 830)
p = os.path.join(da.PROJECT_DIR, "未命名课题.json")
if os.path.exists(p):
    win.project = da.Project.load(p)
    win._refresh_all()
win.show()

out = []


def test():
    name = win.project.name
    target = data_path(f"研究设计_{name}.md")
    if os.path.exists(target):
        os.remove(target)
    win.export_md()
    QApplication.processEvents()
    ok = os.path.exists(target)
    out.append(f"点击「导出 .md」→ 文件{'已生成' if ok else '未生成'}")
    out.append(f"目标路径：{target}")
    out.append(f"数据目录（app_home）：{app_home()}")
    out.append(f"页脚提示文字：{win.tip.label().text()!r}")
    if ok:
        text = open(target, encoding="utf-8").read()
        out.append(f"文件大小：{len(text)} 字符 / {os.path.getsize(target)} 字节")
        out.append(f"前 3 行：{text.splitlines()[:3]}")
        # 内容完整性：阶段标题个数、是否含问答与检查表
        out.append(f"包含阶段小节：{text.count('### ')} 个")
        out.append(f"包含「追问与回答」：{'追问与回答' in text}")
        out.append(f"包含「检查表」：{'检查表' in text}")
        out.append(f"含原始输入：{'研究设想（原始输入）' in text}")
    # 再测一次「导出失败」时的表现：把目录设成只读不可行，改为测 MCP 工具
    from mcp_server import export_markdown
    try:
        r = export_markdown(p.replace(".json", ""))
        out.append(f"MCP 工具 export_markdown → {r[:120]}")
    except Exception as e:                                          # noqa: BLE001
        out.append(f"MCP 工具 export_markdown 异常：{type(e).__name__}: {e}")
    open("_export_test.txt", "w", encoding="utf-8").write("\n".join(out))
    print("\n".join(out))
    app.quit()


QtCore.QTimer.singleShot(1200, test)
sys.exit(app.exec())
