# -*- coding: utf-8 -*-
"""手稿缺陷审阅与 Word 修订 —— 独立模块。

用途变更说明
------------
本模块把工作台原有的「引导式组学 / 统计 / 撰写」三套架构**换一个用法**：
不再是从零陪研究者写方案，而是**导入一份已成稿的手稿（PDF / Word），
逐条对照这三套架构找出缺陷，并把缺陷直接落到 Word 里**：

    · 每条缺陷 = 一条 Word 原生批注，挂在手稿对应段落上
      批注正文写清「违反哪一层哪一条规范 + 为什么是缺陷 + 建议怎么改」
    · 可直接采纳的修改 = Track Changes 修订，按四色规范着色
      绿 00B050 新增 / 红 FF0000 删除 / 蓝 0070C0 修改 / 橙 ED7D31 移动

模块分工
--------
    mr_review_layers.py   三层审阅条目（派生自 stages_data / stat_data / shape_data）
    mr_docx.py            DOCX 结构解析（段落 + 章节映射 + 稳定锚点）
    mr_pdf.py             PDF → DOCX 转换
    mr_signals.py         确定性信号核验（可证据化的硬缺陷）
    mr_reviewer.py        LLM 语义审阅（分层分批 + 缓存）
    mr_word.py            Word 落盘（OfficeCLI：批注 + 四色修订）
    mr_office.py          OfficeCLI 调用封装
    mr_store.py           项目存储
    mr_engine.py          审阅编排
    cli.py                命令行界面

界面
----
桌面界面**不在这里**：它是 design_studio.py 里的第 5 个原生视图
（``ManuscriptReviewPage``），与「设计工作台 / Statistic / SCI Shape / 总览」
共用同一套 PyCt6 + ui_kit 原生组件与浅色主题，启动方式就是原来的
``启动_设计工作台.bat``，然后点流程条第 5 步「手稿审阅」。
"""

from __future__ import annotations

import os as _os
import sys as _sys

# 三层审阅条目**必须**直接复用工作台已有的权威数据模块
# （stages_data / stat_data / shape_data）而不是复制一份，否则两套规范会分叉。
# 这些模块住在仓库根目录，所以包导入时先把它挂到 sys.path 上。
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

APP_NAME = "手稿缺陷审阅工作台"
APP_VERSION = "1.0.0"

__all__ = ["APP_NAME", "APP_VERSION"]
