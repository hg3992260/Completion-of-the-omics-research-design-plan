# -*- coding: utf-8 -*-
"""P1 自检：方向 B 驱动层（kernel_driver，legacy V1 通道）与问答回灌。

覆盖：
  [1] 定位并（接管/启动）内核
  [2] 凭据就绪（auth.json）
  [3] legacy 建 session（POST /session）
  [4] 纯文本一轮：阻塞投递 + parts 归一化，拿到正文
  [5] 事件分类：text_full / step
  [6] question 回灌：触发 question 工具 → 轮询发现 → 就地回答 → 轮次继续
  [7] 清理（仅停止本进程拉起的实例）

用法：
    D:\\python\\envs\\mar\\python.exe _test_driver.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import kernel_client as kc                                              # noqa: E402
import kernel_config as kcfg                                            # noqa: E402
import kernel_driver as kd                                              # noqa: E402

OK = WARN = FAIL = 0
R: list[tuple[str, str, str]] = []


def rec(step: str, status: str, detail: str = "") -> None:
    global OK, WARN, FAIL
    if status == "OK":
        OK += 1
    elif status == "WARN":
        WARN += 1
    else:
        FAIL += 1
    R.append((step, status, detail))
    print(f"  [{status}] {step}" + (f" — {detail}" if detail else ""))


def hr(t: str) -> None:
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--no-question", action="store_true")
    ap.add_argument("--timeout", type=float, default=600.0)
    args = ap.parse_args()

    hr("[1] 定位内核")
    exe = kc.opencode_exe()
    if not exe or not os.path.exists(exe):
        rec("opencode 可执行文件", "FAIL", "未找到；设 PCL_OPENCODE_EXE")
        return summary()
    rec("opencode 可执行文件", "OK",
        f"{os.path.basename(exe)} {os.path.getsize(exe)//1024//1024} MB")

    client = kc.KernelClient(exe=exe, directory=HERE)
    adopted = client.adopt_state() is not None
    try:
        st = client.ensure_running(timeout=120)
    except Exception as e:                                             # noqa: BLE001
        rec("内核启动", "FAIL", f"{type(e).__name__}: {e}")
        return summary()
    adopted = adopted or client.adopted
    rec("内核就绪", "OK", f"{st.url} version={st.version} pid={st.pid} "
                          f"{'（接管）' if adopted else '（本进程拉起）'}")

    hr("[2] 凭据")
    providers = sorted((kcfg.read_auth() or {}).keys())
    rec("auth.json", "OK" if providers else "FAIL", f"provider={providers}")
    model = (kcfg.read_config() or {}).get("model") or "deepseek/deepseek-flash"

    driver = kd.KernelDriver(client)

    hr("[3] legacy 建 session")
    try:
        got = client.create_session(title="driver-selftest")
        sid = got.get("id")
        if not isinstance(sid, str) or not sid:
            rec("create_session", "FAIL", str(got)[:200])
            return summary()
        rec("create_session", "OK", f"{sid}  model={model}")
    except Exception as e:                                             # noqa: BLE001
        rec("create_session", "FAIL", f"{type(e).__name__}: {e}")
        return summary()

    hr("[4] 纯文本一轮")
    t0 = time.time()
    try:
        events = driver.run_turn(sid, "只回答两个字：就绪", timeout=args.timeout, model=model)
    except Exception as e:                                             # noqa: BLE001
        events = []
        rec("run_turn", "FAIL", f"{type(e).__name__}: {e}")
    kinds: dict[str, int] = {}
    for ev in events:
        kinds[ev["kind"]] = kinds.get(ev["kind"], 0) + 1
        if ev["kind"] == "done":
            print("       done:", {k: ev["data"].get(k) for k in ("finish", "model", "provider")})
    dt = time.time() - t0
    text = kd.transcript_text(events)
    rec("事件种类", "OK" if events else "WARN", str(kinds))

    hr("[5] 归一化")
    if "就绪" in text:
        rec("正文含『就绪』", "OK", f"{dt:.1f}s  {text.strip()[:40]!r}")
    else:
        rec("正文含『就绪』", "WARN", f"{dt:.1f}s  正文={text.strip()[:120]!r}")
    rec("step 事件", "OK" if kinds.get("step") else "WARN", f"step={kinds.get('step', 0)}")

    hr("[6] question 回灌")
    if args.no_question:
        rec("question 回灌", "WARN", "按参数跳过")
    else:
        answered = {"ok": False}

        def on_ev(ev: dict) -> None:
            if ev["kind"] == "question":
                req = ev.get("data") or {}
                rid = req.get("id")
                qs = req.get("questions") or []
                first = (qs[0] if qs else {}).get("question")
                if isinstance(rid, str):
                    try:
                        driver.answer_question(rid, [["继续"]])
                        answered["ok"] = True
                        print(f"       ↳ 已回灌 {rid}（{first!r}）→ 继续")
                    except Exception as e:                             # noqa: BLE001
                        print(f"       ↳ 回灌失败：{type(e).__name__}: {e}")

        prompt = ("请调用 question 工具向我提一个问题：header=确认, question=是否继续?, "
                  "options=[{label:继续,description:继续},{label:停止,description:停止}]。"
                  "收到回答后，若为「继续」，只回复两个字：已继续。")
        try:
            evs2 = driver.run_turn(sid, prompt, on_event=on_ev,
                                   timeout=args.timeout, model=model)
        except Exception as e:                                         # noqa: BLE001
            evs2 = []
            rec("question run_turn", "FAIL", f"{type(e).__name__}: {e}")
        text2 = kd.transcript_text(evs2)
        if answered["ok"]:
            rec("question 触发 + 回灌", "OK",
                "已继续" in text2 and "正文=已继续" or f"正文={text2.strip()[:40]!r}")
        else:
            rec("question 触发 + 回灌", "WARN", "模型未调用 question 工具")
        try:
            rec("driver.pending_questions", "OK",
                f"pending={len(driver.pending_questions(sid))}")
        except Exception as e:                                         # noqa: BLE001
            rec("driver.pending_questions", "FAIL", f"{type(e).__name__}: {e}")

    hr("[7] 清理")
    if args.keep:
        rec("保留 session", "WARN", sid)
    if adopted:
        rec("内核生命周期", "OK", "接管实例，不停止")
    else:
        try:
            client.stop()
            rec("内核生命周期", "OK", "已停止本进程拉起的实例")
        except Exception as e:                                         # noqa: BLE001
            rec("内核生命周期", "WARN", f"停止失败：{e}")

    return summary()


def summary() -> int:
    print("\n" + "=" * 72)
    print(f"OK={OK}  WARN={WARN}  FAIL={FAIL}")
    for step, status, detail in R:
        if status != "OK":
            print(f"  [{status}] {step} — {detail}")
    print("结论：" + ("通过" if FAIL == 0 else "未通过"))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
