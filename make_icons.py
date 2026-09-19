# -*- coding: utf-8 -*-
"""从 LOGO.jpg 生成程序图标资源（换了新 logo 后重跑本脚本即可）。

产物：
    logo_mark.png    方版徽标（橙底 + 居中徽章，无文字）—— 512×512
    logo_badge.png   界面标题旁的小角标 —— 28×28
    logo_banner.png  全幅 logo（徽章 + PCL-Radiomics 文字）—— 启动画面用
    logo_icon.ico    多尺寸 Windows 图标（16/24/32/48/64/128/256）

用法：python make_icons.py [源图路径]
"""
import sys

from PIL import Image
import numpy as np

SRC = sys.argv[1] if len(sys.argv) > 1 else "LOGO.jpg"
im = Image.open(SRC).convert("RGB")

# 背景色：取四角均值，作为方版画布的填充色
a = np.asarray(im).astype(int)
BG = tuple(int(v) for v in np.array([a[5, 5], a[5, -5], a[-5, 5], a[-5, -5]]).mean(axis=0))

# 自动找出徽章区域：内容与背景差异 > 阈值，且排除底部文字行
mask = np.abs(a - np.array(BG)).sum(axis=2) > 90
rows = mask.sum(axis=1)
blank = [y for y in range(int(im.height * 0.5), im.height) if rows[y] == 0]
cut = min(blank) if blank else int(im.height * 0.7)      # 徽章与文字之间的空白带
top = mask[:cut, :]
ys, xs = np.nonzero(top)
pad = int(max(xs.max() - xs.min(), ys.max() - ys.min()) * 0.05)
emblem = im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad),
                  min(im.width, xs.max() + pad), min(im.height, ys.max() + pad)))

side = max(emblem.size)
margin = int(side * 0.06)
canvas = Image.new("RGB", (side + margin * 2, side + margin * 2), BG)
canvas.paste(emblem, ((canvas.width - emblem.width) // 2,
                      (canvas.height - emblem.height) // 2))
canvas.resize((512, 512), Image.LANCZOS).save("logo_mark.png")
canvas.resize((28, 28), Image.LANCZOS).save("logo_badge.png")

banner = im.crop((max(0, xs.min() - 20), max(0, ys.min() - 20),
                  min(im.width, xs.max() + 20), im.height))
banner.save("logo_banner.png")

# macOS 图标（CI 在 macos 机器上打包 .app 时需要）
canvas.resize((512, 512), Image.LANCZOS).save(
    "logo.icns", sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512)])

canvas.resize((512, 512), Image.LANCZOS).save(
    "logo_icon.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

print(f"源图 {SRC} {im.size} · 背景 {BG}")
print(f"徽章区 x {xs.min()}..{xs.max()} y {ys.min()}..{ys.max()} · 文字分界 y={cut}")
print("已生成 logo_mark.png / logo_badge.png / logo_banner.png / logo_icon.ico / logo.icns")
