# -*- coding: utf-8 -*-
"""生成「审稿批注版」样例：在 sample_manuscript.docx 上加 3 条审稿意见。

用途：验证「并入审稿批注版 → 发现做成线程回复」这条链路。
批注由 OfficeCLI 写入，与真实审稿批注版同源（Word 能正确识别其线程关系）。

用法：
    python manuscript_review/examples/make_annotated.py
输出：
    manuscript_review/examples/annotated_sample.docx
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from manuscript_review import mr_office

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sample_manuscript.docx")
OUT = os.path.join(HERE, "annotated_sample.docx")

# 模拟审稿人在三段方法学内容上留意见（段号 = OfficeCLI 的 /body/p[N]）
REVIEW = [
    (13, "审稿人1",
     "扫描参数完全没有给出，机型、kVp、层厚、重建核都缺失，第三方无法复现影像组学特征。"
     "请补充完整的采集与重建参数。"),
    (15, "审稿人1",
     "分割只写了一位医师勾画加高年资复核，没有任何一致性量化。"
     "请补充 ICC 或 Dice 并说明重复勾画子集。"),
    (17, "审稿人2",
     "并列构建 11 个模型取最好者，这属于 best-of-N 择优，性能会乐观偏倚。请预先指定主模型。"),
]


def main() -> int:
    if not os.path.exists(SRC):
        print(f"[错误] 缺少 {SRC}，请先运行 make_sample.py", file=sys.stderr)
        return 1
    shutil.copyfile(SRC, OUT)
    mr_office.close(OUT)
    cmds = [{"command": "add", "parent": f"/body/p[{idx}]", "type": "comment",
             "props": {"author": author, "initials": author[:2], "text": text,
                       "runStart": 0, "range": True}}
            for idx, author, text in REVIEW]
    res = mr_office.batch(OUT, cmds)
    mr_office.close(OUT)
    if not res.ok:
        print(f"[失败] 写入审稿批注：{res.error}", file=sys.stderr)
        return 1
    print(f"已生成审稿批注版：{os.path.basename(OUT)}"
          f"（{res.succeeded}/{res.total} 条批注）")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                              # noqa: BLE001
        pass
    sys.exit(main())
