# -*- coding: utf-8 -*-
"""手稿缺陷审阅 —— 命令行界面（无 GUI，便于批处理与服务器上跑）。

用法
----
    # 一键全流程：导入 → 三层审阅 → 报告 → Word 批注+修订
    python -m manuscript_review.cli 手稿.pdf

    # 只跑确定性核验（不联网、不花钱）
    python -m manuscript_review.cli 手稿.docx --skip-llm

    # 只审写作层、最多 3 批（快速试跑）
    python -m manuscript_review.cli 手稿.pdf --layers shape --max-batches 3

    # 只出批注，不改正文
    python -m manuscript_review.cli 手稿.docx --mode comment_only

    # 看三层条目统计 / 看外部依赖就绪情况
    python -m manuscript_review.cli --layers-info
    python -m manuscript_review.cli --toolchain

退出码：0 成功；1 失败；2 参数错误。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                  # noqa: BLE001
    pass


def _print_layers() -> int:
    from manuscript_review.mr_review_layers import LAYERS, LAYER_ORDER, stats
    st = stats()
    print(f"{'层':<10}{'条目':>6}{'关键':>6}{'主要':>6}{'一般':>6}{'可核验':>8}  规范依据")
    print("-" * 92)
    for k in LAYER_ORDER:
        s = st[k]
        print(f"{LAYERS[k]['name']:<10}{s['total']:>6}{s['关键']:>6}{s['主要']:>6}"
              f"{s['一般']:>6}{s['with_signal']:>8}  {LAYERS[k]['sub']}")
    print("-" * 92)
    print(f"{'合计':<10}{st['total']:>6}")
    return 0


def _print_selfcheck() -> int:
    """逐个子模块自检 —— 用来确认「打包版里这个功能到底有没有被打进去」。

    为什么需要：打包时若漏了本地模块（PyInstaller 对 hardcoded hiddenimports
    不会递归分析其函数内的延迟导入），运行时会报 ModuleNotFoundError；
    但失败被后台线程接住后只写进界面流水，看起来就像「点了没反应」。
    这里在**不依赖界面**的情况下把每个子模块真实导入一次。
    """
    mods = ["mr_review_layers", "mr_docx", "mr_pdf", "mr_signals", "mr_reviewer",
            "mr_office", "mr_word", "mr_report", "mr_engine", "mr_thread", "cli"]
    print("手稿审阅 · 模块自检")
    print(f"  运行方式 : {'打包版（frozen）' if getattr(sys, 'frozen', False) else '源码'}")
    print(f"  解释器   : {sys.executable}")
    print(f"  模块目录 : {os.path.dirname(os.path.abspath(__file__))}")
    print()
    bad = []
    for m in mods:
        try:
            __import__(f"manuscript_review.{m}")
            print(f"  ✓ manuscript_review.{m}")
        except Exception as e:                                     # noqa: BLE001
            bad.append(f"{m}: {type(e).__name__}: {e}")
            print(f"  ✗ manuscript_review.{m}  —— {type(e).__name__}: {e}")
    print()
    if bad:
        print(f"结果：{len(bad)}/{len(mods)} 个子模块导入失败。")
        if getattr(sys, "frozen", False):
            print("这是**打包版**：说明编译时这些模块没被收进包。"
                  "请用配套 spec 重新编译（spec 里把本地模块显式放进 hiddenimports，"
                  "并对本地包调用 collect_submodules）。")
        else:
            print("这是源码运行：请检查仓库中对应 .py 文件是否存在。")
        return 1
    print(f"结果：{len(mods)}/{len(mods)} 个子模块全部可导入。")
    return 0


def _print_toolchain() -> int:
    from manuscript_review import mr_office, mr_pdf, mr_word
    oc = mr_office.available()
    pdf = mr_pdf.available()
    print("OfficeCLI（Word 批注 + Track Changes）")
    print(f"  可用 : {oc['available']}")
    print(f"  路径 : {oc['path'] or '—'}")
    print(f"  版本 : {oc['version'] or '—'}")
    if oc.get("error"):
        print(f"  问题 : {oc['error']}")
    print("PDF → DOCX")
    print(f"  PyMuPDF : {pdf['pymupdf']} {pdf.get('version', '')}")
    print("修订颜色规范")
    print(f"  新增 {mr_word.C_NEW} · 删除 {mr_word.C_DEL} · "
          f"修改 {mr_word.C_MOD} · 移动 {mr_word.C_MOVE}")
    return 0 if oc["available"] and pdf["pymupdf"] else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="manuscript_review",
        description="手稿缺陷审阅：按引导式组学/统计/撰写三层架构对照手稿缺陷，"
                    "并落回 Word（原生批注 + 四色 Track Changes 修订）")
    ap.add_argument("manuscript", nargs="?", help="手稿路径（.pdf / .docx）")
    ap.add_argument("--layers", default="omics,stat,shape",
                    help="要审的层，逗号分隔（omics/stat/shape），默认三层全审")
    ap.add_argument("--skip-llm", action="store_true",
                    help="只跑确定性核验（不联网、不花钱）")
    ap.add_argument("--max-batches", type=int, default=0,
                    help="每层最多跑多少批 LLM（0=不限；调试用）")
    ap.add_argument("--mode", default="dual", choices=["dual", "comment_only"],
                    help="dual=批注+修订（默认）；comment_only=只出批注不改正文")
    ap.add_argument("--max-insert", type=int, default=25,
                    help="最多补写多少段（默认 25）")
    ap.add_argument("--no-cache", action="store_true", help="不使用 LLM 结果缓存")
    ap.add_argument("--autonomy", default="revise",
                    choices=["revise", "comment", "report"],
                    help="自主落盘程度：revise=批注+补写缺失项（默认）；"
                         "comment=只挂批注不改正文；report=只出报告")
    ap.add_argument("--incremental", action="store_true",
                    help="增量模式：只把本次新报出的发现写到已有修订稿（默认每次完整重写）")
    ap.add_argument("--out", default="", help="修订稿输出路径（默认写到导出目录）")
    ap.add_argument("--merge-into", default="",
                    help="审稿批注版手稿路径：把发现作为**线程回复**挂在审稿意见下面，"
                         "保留审稿人原有批注不动")
    ap.add_argument("--reply-mode", default="reply", choices=["reply", "standalone"],
                    help="reply=匹配得上的发现做成线程回复（默认）；standalone=只做独立批注")
    ap.add_argument("--per-parent", type=int, default=4,
                    help="一条审稿意见最多收几条回复（默认 4）")
    ap.add_argument("--annotated-info", action="store_true",
                    help="只看某份手稿的审稿批注情况后退出")
    ap.add_argument("--name", default="", help="项目名（默认取文件名）")
    ap.add_argument("--layers-info", action="store_true", help="只看三层条目统计")
    ap.add_argument("--toolchain", action="store_true", help="只看外部依赖就绪情况")
    ap.add_argument("--selfcheck", action="store_true",
                    help="逐个子模块自检（打包版排查「功能没打进 exe」用）")
    ap.add_argument("--json", action="store_true", help="结果以 JSON 输出（便于管道）")
    args = ap.parse_args(argv)

    if args.selfcheck:
        return _print_selfcheck()
    if args.layers_info:
        return _print_layers()
    if args.toolchain:
        return _print_toolchain()
    if args.annotated_info:
        if not args.manuscript:
            print("[错误] 需要给出手稿路径", file=sys.stderr)
            return 2
        from manuscript_review import mr_thread
        info = mr_thread.probe(args.manuscript)
        print(json.dumps(info, ensure_ascii=False, indent=1))
        return 0
    if not args.manuscript:
        ap.print_help()
        return 2
    if not os.path.exists(args.manuscript):
        print(f"[错误] 文件不存在：{args.manuscript}", file=sys.stderr)
        return 1

    from manuscript_review.mr_engine import RevEngine, ReviewProject

    def step(name: str, msg: str):
        if not args.json:
            print(f"[{name:8s}] {msg}", flush=True)

    client = None
    if not args.skip_llm:
        try:
            from llm_client import LLMClient, load_config
            cfg = load_config()
            if not cfg.get("api_key"):
                print("[警告] 未配置 LLM 密钥，自动退化为只跑确定性核验。",
                      file=sys.stderr)
                args.skip_llm = True
            else:
                client = LLMClient(cfg)
                if not args.json:
                    print(f"[配置    ] 模型 {client.model} → {client.base_url}")
        except Exception as e:                                     # noqa: BLE001
            print(f"[警告] 无法初始化 LLM（{e}），退化为只跑确定性核验。", file=sys.stderr)
            args.skip_llm = True

    # ---- 一键全流程：审阅跑完**自动**把发现写进 Word（自主落盘）
    eng = RevEngine(client)
    layers = [x.strip() for x in (args.layers or "").split(",") if x.strip()]
    ok, msg, proj = eng.run_all(
        args.manuscript, layers=layers, use_cache=not args.no_cache,
        max_batches=args.max_batches, skip_llm=args.skip_llm,
        autonomy=args.autonomy, merge_into=args.merge_into,
        reply_mode=args.reply_mode, per_parent=args.per_parent,
        fresh=not args.incremental, on_step=step)

    if args.json:
        p = proj
        print(json.dumps({
            "ok": bool((p.applied or {}).get("ok")) or args.autonomy == "report",
            "project": p.name, "project_path": p.path(),
            "converted": p.converted, "docx_path": p.docx_path,
            "signal_summary": p.signal_summary, "summary": p.summary,
            "out_docx": p.out_docx, "report_path": p.report_path,
            "applied": p.applied, "applied_keys": len(p.applied_keys or []),
            "warnings": p.warnings,
        }, ensure_ascii=False, indent=1))
        return 0 if p.out_docx or args.autonomy == "report" else 1

    _print_summary(proj)
    return 0 if (proj.out_docx or args.autonomy == "report") else 1


def _print_summary(proj) -> None:
    s = proj.summary or {}
    print()
    print("=" * 70)
    print(f"审阅完成 · {proj.name}")
    print("=" * 70)
    print(f"  缺陷合计 : {s.get('total', 0)} 条"
          f"（关键 {s.get('关键', 0)} · 主要 {s.get('主要', 0)}"
          f" · 一般 {s.get('一般', 0)}）")
    sig = proj.signal_summary or {}
    print(f"  确定性核验: {sig.get('total', 0)} 项 —— 缺失 {sig.get('missing', 0)}"
          f" · 不完整 {sig.get('weak', 0)} · 已报告 {sig.get('reported', 0)}")
    ap = proj.applied or {}
    total_notes = (ap.get("comments_added") or 0) + (ap.get("replies_added") or 0)
    print(f"  Word 落盘 : 批注共 {total_notes} 条"
          f"（独立 {ap.get('comments_added', 0)}"
          f" + 线程回复 {ap.get('replies_added', 0)}）"
          f" · 正文修订 {ap.get('revisions_added', 0)} 处")
    mp = ap.get("merge_plan") or {}
    if mp:
        print(f"  并入批注版: {mp.get('replies_count', 0)} 条回复挂到 "
              f"{len(mp.get('parents_used') or [])} 条审稿意见下"
              f" · {mp.get('standalone', 0)} 条作独立批注")
    th = ap.get("threading") or {}
    if th:
        print(f"  线程校验  : {'通过' if th.get('ok') else '未通过'}"
              f"（根 {th.get('roots')} · 回复 {th.get('replies')} · "
              f"嵌套正常 {th.get('nested_ok')}）")
        for p in th.get("problems") or []:
            print(f"      ⚠ {p}")
    print()
    print(f"  修订稿 : {proj.out_docx or '（未生成 / autonomy=report）'}")
    print(f"  审阅报告: {proj.report_path or '（未生成）'}")
    print(f"  已入稿  : {len(proj.applied_keys or [])} 条发现"
          f"（{proj.applied_at or '—'}）")
    if proj.warnings:
        print()
        print("  提示：")
        for w in proj.warnings:
            print(f"    - {w}")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.exit(main())
