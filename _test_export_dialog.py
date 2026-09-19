# -*- coding: utf-8 -*-
"""实测「导出 .md」的新交互：弹保存对话框 → 选路径 → 写文件；并测取消/补扩展名/写失败。

对话框用打桩方式模拟（自动化测试里没人点按钮）。
"""
import json
import os
import sys

sys.argv = ["x"]
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6 import QtCore

import design_agent as da
import design_studio as ds

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
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_export_tmp")
os.makedirs(TMP, exist_ok=True)


def stub(return_path):
    """把 QFileDialog.getSaveFileName 换成返回固定路径，并记录收到的默认路径。"""
    box = {}

    def fake(parent, caption, default, filters, *a, **kw):
        box["caption"] = caption
        box["default"] = default
        box["filters"] = filters
        return (return_path, filters.split(";;")[0] if return_path else "")

    QFileDialog.getSaveFileName = staticmethod(fake)
    return box


def run():
    # ---- 1) 正常选择路径
    target = os.path.join(TMP, "我的设计稿.md")
    box = stub(target)
    win.export_md()
    out.append("【1】选择路径后导出")
    out.append(f"  对话框标题：{box.get('caption')!r}")
    out.append(f"  默认路径：{box.get('default')}")
    out.append(f"  过滤器：{box.get('filters')!r}")
    out.append(f"  文件已写入：{os.path.exists(target)}　大小 "
               f"{os.path.getsize(target) if os.path.exists(target) else 0} 字节")
    out.append(f"  页脚提示：{win.tip.label().text()!r}")

    # ---- 2) 用户取消
    box = stub("")
    before = set(os.listdir(TMP))
    win.export_md()
    after = set(os.listdir(TMP))
    out.append("【2】用户取消")
    out.append(f"  是否新增文件：{bool(after - before)}")
    out.append(f"  页脚提示：{win.tip.label().text()!r}")

    # ---- 3) 不写扩展名
    noext = os.path.join(TMP, "没有扩展名")
    stub(noext)
    win.export_md()
    out.append("【3】未写扩展名")
    out.append(f"  自动补成 .md：{os.path.exists(noext + '.md')}")

    # ---- 4) 记住上次目录
    stub(os.path.join(TMP, "第二次.md"))
    win.export_md()
    prefs = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "ui_prefs.json"), encoding="utf-8"))
    out.append("【4】记住上次导出目录")
    out.append(f"  ui_prefs.json = {prefs}")
    out.append(f"  下次默认目录是它：{prefs.get('last_export_dir') == TMP}")

    # ---- 5) 写入失败（不存在的盘符）
    stub("Z:\\不存在的盘\\x.md")
    win.export_md()
    out.append("【5】写入失败")
    out.append(f"  页脚提示：{win.tip.label().text()[:70]!r}")

    open("_export_dialog_test.txt", "w", encoding="utf-8").write("\n".join(out))
    print("\n".join(out))
    app.quit()


QtCore.QTimer.singleShot(1000, run)
sys.exit(app.exec())
