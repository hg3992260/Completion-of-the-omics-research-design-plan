# -*- coding: utf-8 -*-
"""统计计算层 —— 把「统计」页里声明的工具变成真的能算的东西。

对应桌面版/文档里承诺的那套工具（见 `stat_data.TOOLS["统计计算"]`）：

    stat_describe          描述性统计 + 正态性（Shapiro）+ 方差齐性（Levene）
    stat_run_test          16 种假设检验（见 KINDS）
    stat_effect_ci         效应量与置信区间（均数差 / Cohen's d·Hedges' g / OR·RD / r）
    stat_sample_size       样本量估算（两均数 / 两比例 / 单均数 / 相关，正态近似）
    stat_correct_pvalues   多重比较校正（bonferroni | holm | fdr_bh）

设计口径
--------
* **纯计算**：只用 numpy + scipy，不读项目、不调模型、不依赖 Qt；
  没有 scipy 时 `available()` 返回原因，界面据此降级提示，而不是崩掉。
* **只做统计，不做判断**：每个结果都回传中文"可直接粘贴"的结论句与前提提示，
  但"该用哪个检验、结论能不能站住"仍由研究者和模型决定（与项目的其余部分一致）。
* 所有函数出错都抛 `StatError`（消息为中文，可直接显示给用户）。
* Python 3.8 兼容（Win7 目标机上要能跑）。
"""

from __future__ import annotations

import math

KINDS = {
    # kind: (中文名, 输入形态, 前提提示, scipy 对应)
    "ttest_ind": ("独立样本 t 检验（合并方差）", "two", "两组独立、近似正态、方差齐（否则用 welch）",
                  "scipy.stats.ttest_ind(equal_var=True)"),
    "welch": ("Welch t 检验（方差不齐）", "two", "两组独立、近似正态；不要求方差齐",
              "scipy.stats.ttest_ind(equal_var=False)"),
    "mannwhitney": ("Mann–Whitney U（秩和）", "two", "两组独立；非正态或有序数据",
                    "scipy.stats.mannwhitneyu"),
    "ttest_paired": ("配对 t 检验", "paired", "配对/前后测量；差值近似正态",
                     "scipy.stats.ttest_rel"),
    "wilcoxon": ("Wilcoxon 符号秩", "paired", "配对数据；差值非正态（分布对称）",
                 "scipy.stats.wilcoxon"),
    "ttest_1samp": ("单样本 t 检验", "one", "与已知参考值 μ₀ 比较；近似正态",
                    "scipy.stats.ttest_1samp"),
    "wilcoxon_1samp": ("单样本 Wilcoxon 符号秩", "one", "与 μ₀ 比较；非正态",
                       "scipy.stats.wilcoxon(x - μ₀)"),
    "anova": ("单因素方差分析", "many", "≥3 组独立、正态、方差齐",
              "scipy.stats.f_oneway"),
    "kruskal": ("Kruskal–Wallis 检验", "many", "≥3 组独立；非正态（事后需 Dunn 检验）",
                "scipy.stats.kruskal"),
    "levene": ("Levene 方差齐性检验", "many", "≥2 组；用于判断能否用合并方差 t / ANOVA",
               "scipy.stats.levene(center='median')"),
    "pearson": ("Pearson 相关", "paired", "两连续变量、线性关系、近似双变量正态",
                "scipy.stats.pearsonr"),
    "spearman": ("Spearman 秩相关", "paired", "单调关系；非正态或有序",
                 "scipy.stats.spearmanr"),
    "kendall": ("Kendall τ 相关", "paired", "单调关系；小样本或有大量并列值",
                "scipy.stats.kendalltau"),
    "chisq": ("卡方独立性检验", "table", "两分类变量；期望频数≥5（否则用 fisher）",
              "scipy.stats.chi2_contingency"),
    "fisher": ("Fisher 精确检验", "table2", "2×2 列联表；小样本或期望频数<5",
               "scipy.stats.fisher_exact"),
    "binom_prop": ("二项检验（单组比例）", "binom", "与已知比例 p₀ 比较",
                   "scipy.stats.binomtest"),
}

CORRECTIONS = {
    "bonferroni": "Bonferroni（最保守，控制 FWER）",
    "holm": "Holm–Bonferroni（逐步，控制 FWER，比 Bonferroni 有功效）",
    "fdr_bh": "Benjamini–Hochberg（控制 FDR，探索性分析常用）",
}

_NP = None
_SP = None
_SCIPY = None
_ERR = ""


class StatError(Exception):
    """计算层的用户级错误（消息可直接展示）。"""


def _load():
    """惰性导入 numpy/scipy，并把不可用的原因记下来。"""
    global _NP, _SP, _SCIPY, _ERR
    if _NP is not None or _ERR:
        return _NP, _SP
    try:
        import numpy as np                                    # noqa: PLC0415
        import scipy                                          # noqa: PLC0415
        import scipy.stats as sp                              # noqa: PLC0415
        _NP, _SP, _SCIPY = np, sp, scipy
    except Exception as e:                                    # noqa: BLE001
        _ERR = "%s: %s" % (type(e).__name__, e)
    return _NP, _SP


def _version(mod) -> str:
    """取版本号：scipy 新版本去掉了 `scipy.__version__`，退到 version.version / importlib。"""
    for getter in (lambda: getattr(mod, "__version__", ""),
                   lambda: mod.version.version,
                   lambda: mod.version.short_version):
        try:
            v = getter()
            if v:
                return str(v)
        except Exception:                                      # noqa: BLE001
            continue
    try:
        import importlib.metadata as md                        # noqa: PLC0415
        return md.version(mod.__name__)
    except Exception:                                          # noqa: BLE001
        return "?"


def available() -> dict:
    """计算层是否可用（冻结产物若没打包 numpy/scipy，这里会给出原因）。"""
    np, _ = _load()
    if np is None:
        return {"ok": False, "reason": _ERR or "numpy/scipy 不可用", "numpy": "", "scipy": ""}
    return {"ok": True, "reason": "", "numpy": _version(np),
            "scipy": _version(_SCIPY) if _SCIPY is not None else "?"}


def kinds_payload() -> list:
    """给界面用的 kind 元数据（顺序固定，便于前端展示分组）。"""
    return [{"kind": k, "name": v[0], "shape": v[1], "hint": v[2], "scipy": v[3]}
            for k, v in KINDS.items()]


# --------------------------------------------------------------------------- 输入
def _numbers(raw) -> "object":
    """把界面传来的东西（字符串/列表/带分隔符的文本）转成一维浮点数组。"""
    np, _ = _load()
    if np is None:
        raise StatError("统计计算不可用：%s" % _ERR)
    if raw is None:
        raise StatError("没有数据")
    if isinstance(raw, str):
        items = raw.replace("，", ",").replace("；", ";").replace("\n", " ") \
                   .replace("\t", " ").replace(";", " ").replace(",", " ").split()
    elif isinstance(raw, (list, tuple)):
        items = []
        for x in raw:
            if isinstance(x, str):
                items += x.replace("，", ",").replace(";", " ").replace(",", " ").split()
            else:
                items.append(x)
    else:
        items = [raw]
    out = []
    for it in items:
        if it is None or (isinstance(it, str) and not it.strip()):
            continue
        try:
            v = float(it)
        except (TypeError, ValueError):
            raise StatError("无法解析为数字：%r" % (it,))
        if math.isnan(v) or math.isinf(v):
            raise StatError("数据里含 NaN/Inf：%r" % (it,))
        out.append(v)
    return np.asarray(out, dtype=float)


def _groups(raw) -> list:
    """两组/多组：接受 [[...],[...]]，或界面传来的多行文本（每行一组）。"""
    if isinstance(raw, str):
        blocks = [b for b in raw.split("\n") if b.strip()]
        return [_numbers(b) for b in blocks] if len(blocks) > 1 else [_numbers(raw)]
    if isinstance(raw, (list, tuple)):
        if raw and isinstance(raw[0], (list, tuple, str)):
            return [_numbers(x) for x in raw]
        return [_numbers(raw)]
    return [_numbers(raw)]


def _paired_inputs(raw_a, raw_b) -> tuple:
    """配对数据：两组长度必须一致（注意与后面的检验分发函数 _paired 区分开）。"""
    a, b = _numbers(raw_a), _numbers(raw_b)
    if len(a) != len(b):
        raise StatError("配对数据两组长度必须相同（当前 %d vs %d）" % (len(a), len(b)))
    if len(a) < 3:
        raise StatError("配对数据太少（至少 3 对）")
    return a, b


def _need_min(x, n: int, what: str):
    if len(x) < n:
        raise StatError("%s至少需要 %d 个观测（当前 %d）" % (what, n, len(x)))


def _pct(x: float, digits: int = 4) -> str:
    """P 值显示：大于 0.001 保留小数，否则用科学计数法（论文里也这么写）。"""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    if x < 0.001:
        return "P < 0.001（实际 %.2e）" % x
    return "P = %.*f" % (digits, x)


# --------------------------------------------------------------------------- 描述
def stat_describe(groups, labels=None) -> dict:
    """描述性统计 + 正态性 + 方差齐性。"""
    np, sp = _load()
    if np is None:
        raise StatError("统计计算不可用：%s" % _ERR)
    gs = _groups(groups)
    gs = [g for g in gs if len(g)]
    if not gs:
        raise StatError("没有数据")
    labels = list(labels or []) + ["第 %d 组" % (i + 1) for i in range(len(gs))]
    rows = []
    for i, g in enumerate(gs):
        row = {"label": labels[i], "n": int(len(g)),
               "mean": float(np.mean(g)), "sd": float(np.std(g, ddof=1)) if len(g) > 1 else 0.0,
               "median": float(np.median(g)),
               "q1": float(np.percentile(g, 25)), "q3": float(np.percentile(g, 75)),
               "min": float(np.min(g)), "max": float(np.max(g))}
        row["normality"] = None
        if 3 <= len(g) <= 5000:
            try:
                w, p = sp.shapiro(g)
                row["normality"] = {"w": float(w), "p": float(p),
                                    "normal": bool(p >= 0.05)}
            except Exception:                                  # noqa: BLE001
                row["normality"] = None
        rows.append(row)
    levene = None
    if len(gs) >= 2 and all(len(g) >= 2 for g in gs):
        try:
            st, p = sp.levene(*gs, center="median")
            levene = {"stat": float(st), "p": float(p), "equal_var": bool(p >= 0.05)}
        except Exception:                                      # noqa: BLE001
            levene = None
    notes = []
    if levene and not levene["equal_var"]:
        notes.append("Levene 提示方差不齐（%s）→ 两组比较建议用 welch，≥3 组建议 Welch ANOVA 或"
                     "非参数检验。" % _pct(levene["p"]))
    for r in rows:
        if r["normality"] and not r["normality"]["normal"]:
            notes.append("%s：Shapiro–Wilk %s → 偏离正态，考虑非参数检验或报告中位数(IQR)。"
                         % (r["label"], _pct(r["normality"]["p"])))
    lines = ["　".join(["%s: n=%d" % (r["label"], r["n"]),
                        "均数±SD = %.3f±%.3f" % (r["mean"], r["sd"]),
                        "中位数(IQR) = %.3f (%.3f–%.3f)" % (r["median"], r["q1"], r["q3"])])
             for r in rows]
    return {"action": "describe", "groups": rows, "levene": levene, "notes": notes,
            "text": "\n".join(lines),
            "sentence": "各组分布如下：" + "；".join(
                "%s 均数±SD 为 %.3f±%.3f，中位数(IQR) 为 %.3f (%.3f–%.3f)"
                % (r["label"], r["mean"], r["sd"], r["median"], r["q1"], r["q3"])
                for r in rows) + "。" + ("".join(notes) if notes else "")}


# --------------------------------------------------------------------------- 检验
def _two_group(kind: str, a, b, alpha: float) -> dict:
    np, sp = _load()
    _need_min(a, 3, "第一组")
    _need_min(b, 3, "第二组")
    n1, n2 = len(a), len(b)
    m1, m2 = float(np.mean(a)), float(np.mean(b))
    s1, s2 = float(np.std(a, ddof=1)), float(np.std(b, ddof=1))
    diff = m1 - m2
    if kind in ("ttest_ind", "welch"):
        equal = kind == "ttest_ind"
        st, p = sp.ttest_ind(a, b, equal_var=equal)
        if equal:
            df = n1 + n2 - 2
            sp2 = (((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / df) if df > 0 else 0.0
            se = math.sqrt(sp2 * (1.0 / n1 + 1.0 / n2)) if sp2 > 0 else 0.0
        else:
            v1, v2 = s1 ** 2 / n1, s2 ** 2 / n2
            se = math.sqrt(v1 + v2)
            df = ((v1 + v2) ** 2 / (v1 ** 2 / (n1 - 1) + v2 ** 2 / (n2 - 1))
                  if (v1 + v2) > 0 else 0.0)
        tcrit = float(sp.t.ppf(1 - alpha / 2, df)) if df > 0 else 0.0
        ci = [diff - tcrit * se, diff + tcrit * se] if se > 0 else [diff, diff]
        pooled = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2)) \
            if (n1 + n2 - 2) > 0 else 0.0
        d = (diff / pooled) if pooled > 0 else 0.0
        j = 1 - 3 / (4 * (n1 + n2) - 9) if (n1 + n2) > 3 else 1.0
        g = d * j
        se_d = math.sqrt((n1 + n2) / (n1 * n2) + d ** 2 / (2 * (n1 + n2))) if d or True else 0.0
        return {"statistic": float(st), "df": float(df), "p": float(p),
                "effect": {"name": "均数差 (mean difference)", "value": diff,
                           "ci": ci, "ci_level": 1 - alpha},
                "effect2": {"name": "Cohen's d / Hedges' g", "value": d, "g": g,
                            "ci": [d - 1.96 * se_d, d + 1.96 * se_d]},
                "extra": {"se": se, "mean1": m1, "mean2": m2, "sd1": s1, "sd2": s2}}
    if kind == "mannwhitney":
        st, p = sp.mannwhitneyu(a, b, alternative="two-sided")
        return {"statistic": float(st), "df": None, "p": float(p),
                "effect": {"name": "秩和统计量 U", "value": float(st), "ci": None},
                "extra": {"n1": n1, "n2": n2, "median1": float(np.median(a)),
                          "median2": float(np.median(b))}}
    raise StatError("未知的检验类型：%s" % kind)


def _paired(kind: str, a, b, alpha: float) -> dict:
    np, sp = _load()
    diff = a - b
    if kind == "ttest_paired":
        st, p = sp.ttest_rel(a, b)
        n = len(diff)
        md = float(np.mean(diff))
        sd = float(np.std(diff, ddof=1))
        se = sd / math.sqrt(n) if n else 0.0
        tcrit = float(sp.t.ppf(1 - alpha / 2, n - 1)) if n > 1 else 0.0
        d = md / sd if sd > 0 else 0.0
        return {"statistic": float(st), "df": float(n - 1), "p": float(p),
                "effect": {"name": "配对差值均数", "value": md,
                           "ci": [md - tcrit * se, md + tcrit * se], "ci_level": 1 - alpha},
                "effect2": {"name": "Cohen's d（配对）", "value": d},
                "extra": {"n": n, "mean_diff": md, "sd_diff": sd}}
    if kind == "wilcoxon":
        st, p = sp.wilcoxon(a, b)
        return {"statistic": float(st), "df": None, "p": float(p),
                "effect": {"name": "配对差值中位数", "value": float(np.median(diff)),
                           "ci": None},
                "extra": {"n": int(len(diff))}}
    if kind in ("pearson", "spearman", "kendall"):
        if kind == "pearson":
            st, p = sp.pearsonr(a, b)
            name = "Pearson r"
        elif kind == "spearman":
            st, p = sp.spearmanr(a, b)
            name = "Spearman ρ"
        else:
            st, p = sp.kendalltau(a, b)
            name = "Kendall τ"
        ci = None
        if kind == "pearson" and len(a) > 3:
            z = math.atanh(max(-0.999999, min(0.999999, float(st))))
            se = 1.0 / math.sqrt(len(a) - 3)
            zc = 1.96
            ci = [math.tanh(z - zc * se), math.tanh(z + zc * se)]
        return {"statistic": float(st), "df": None, "p": float(p),
                "effect": {"name": name, "value": float(st), "ci": ci},
                "extra": {"n": int(len(a))}}
    raise StatError("未知的检验类型：%s" % kind)


def _one_group(kind: str, x, mu: float, alpha: float) -> dict:
    np, sp = _load()
    _need_min(x, 3, "样本")
    n = len(x)
    if kind == "ttest_1samp":
        st, p = sp.ttest_1samp(x, mu)
        m, sd = float(np.mean(x)), float(np.std(x, ddof=1))
        se = sd / math.sqrt(n)
        tcrit = float(sp.t.ppf(1 - alpha / 2, n - 1))
        return {"statistic": float(st), "df": float(n - 1), "p": float(p),
                "effect": {"name": "均数（与 μ₀ 之差）", "value": m,
                           "ci": [m - tcrit * se, m + tcrit * se], "ci_level": 1 - alpha,
                           "diff": m - mu, "mu0": mu},
                "effect2": {"name": "Cohen's d（单样本）",
                            "value": (m - mu) / sd if sd > 0 else 0.0},
                "extra": {"n": n, "mean": m, "sd": sd}}
    if kind == "wilcoxon_1samp":
        st, p = sp.wilcoxon(x - mu)
        return {"statistic": float(st), "df": None, "p": float(p),
                "effect": {"name": "中位数（与 μ₀ 之差）", "value": float(np.median(x)),
                           "ci": None, "diff": float(np.median(x)) - mu, "mu0": mu},
                "extra": {"n": n}}
    raise StatError("未知的检验类型：%s" % kind)


def _many_group(kind: str, gs, alpha: float) -> dict:
    np, sp = _load()
    gs = [g for g in gs if len(g) >= 2]
    if len(gs) < 2:
        raise StatError("至少需要 2 组、每组 ≥2 个观测")
    if kind == "levene":
        st, p = sp.levene(*gs, center="median")
        return {"statistic": float(st), "df": None, "p": float(p),
                "effect": {"name": "方差齐性", "value": float(p), "ci": None},
                "extra": {"k": len(gs), "n": [int(len(g)) for g in gs]}}
    if kind == "anova":
        st, p = sp.f_oneway(*gs)
        allv = np.concatenate(gs)
        grand = float(np.mean(allv))
        ssb = sum(len(g) * (float(np.mean(g)) - grand) ** 2 for g in gs)
        ssw = sum(float(np.sum((g - np.mean(g)) ** 2)) for g in gs)
        df1, df2 = len(gs) - 1, len(allv) - len(gs)
        eta2 = ssb / (ssb + ssw) if (ssb + ssw) > 0 else 0.0
        return {"statistic": float(st), "df": [df1, df2], "p": float(p),
                "effect": {"name": "η²（效应量）", "value": eta2, "ci": None},
                "extra": {"k": len(gs), "n": [int(len(g)) for g in gs],
                          "means": [float(np.mean(g)) for g in gs]}}
    if kind == "kruskal":
        st, p = sp.kruskal(*gs)
        return {"statistic": float(st), "df": len(gs) - 1, "p": float(p),
                "effect": {"name": "H 统计量", "value": float(st), "ci": None},
                "extra": {"k": len(gs), "n": [int(len(g)) for g in gs]}}
    raise StatError("未知的检验类型：%s" % kind)


def _table(kind: str, table, alpha: float) -> dict:
    np, sp = _load()
    t = [[float(v) for v in row] for row in table]
    if kind == "fisher":
        if len(t) != 2 or any(len(r) != 2 for r in t):
            raise StatError("Fisher 精确检验需要 2×2 列联表")
        st, p = sp.fisher_exact(t)
        a, b = t[0]
        c, d = t[1]
        orr = ((a * d) / (b * c)) if (b * c) > 0 else float("inf")
        ci = None
        if a > 0 and b > 0 and c > 0 and d > 0:
            se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
            z = math.log(orr)
            ci = [math.exp(z - 1.96 * se), math.exp(z + 1.96 * se)]
        return {"statistic": float(st), "df": None, "p": float(p),
                "effect": {"name": "优势比 OR", "value": orr, "ci": ci},
                "extra": {"table": t}}
    if kind == "chisq":
        st, p, dof, exp = sp.chi2_contingency(t)
        n = sum(sum(r) for r in t)
        cramv = math.sqrt(float(st) / (n * (min(len(t), len(t[0])) - 1))) if n > 0 else 0.0
        warn = ""
        cells = [e for row in exp for e in row]
        if cells and min(cells) < 5:
            warn = "有理论频数 <5（最小 %.2f）→ 建议改用 Fisher 精确检验" % min(cells)
        return {"statistic": float(st), "df": int(dof), "p": float(p),
                "effect": {"name": "Cramér's V", "value": cramv, "ci": None},
                "extra": {"expected": [[float(e) for e in row] for row in exp], "warn": warn}}
    raise StatError("未知的检验类型：%s" % kind)


def _binom(kind: str, k: int, n: int, p0: float, alpha: float) -> dict:
    _, sp = _load()
    if n <= 0 or k < 0 or k > n:
        raise StatError("二项检验需要 0 ≤ 成功数 ≤ 总数（当前 %s / %s）" % (k, n))
    res = sp.binomtest(int(k), int(n), p0)
    p = float(res.pvalue)
    phat = k / n
    ci = None
    if n > 0:
        se = math.sqrt(phat * (1 - phat) / n)
        ci = [max(0.0, phat - 1.96 * se), min(1.0, phat + 1.96 * se)]
    return {"statistic": float(k), "df": None, "p": p,
            "effect": {"name": "比例 p̂", "value": phat, "ci": ci, "p0": p0},
            "extra": {"k": int(k), "n": int(n)}}


def stat_run_test(kind: str, groups=None, x=None, y=None, mu: float = 0.0,
                  table=None, successes=None, trials=None, p0: float = 0.5,
                  alpha: float = 0.05) -> dict:
    """跑一次检验，返回 {statistic, df, p, effect, extra, sentence, notes}。

    `kind` 见 KINDS；输入形态按 kind 取用：
        two    : groups=[组A, 组B]（或 groups=[[..],[..]]）
        paired : x=向量A, y=向量B（长度相同）
        one    : x=样本, mu=μ₀
        many   : groups=[组1, 组2, 组3...]
        table  : table=[[a,b],[c,d]]
        binom  : successes=k, trials=n, p0=p₀
    """
    kind = (kind or "").strip()
    if kind not in KINDS:
        raise StatError("未知的检验类型：%s（支持 %s）" % (kind, "、".join(KINDS)))
    shape = KINDS[kind][1]
    if shape == "two":
        gs = _groups(groups)
        if len(gs) < 2:
            raise StatError("需要两组数据")
        r = _two_group(kind, gs[0], gs[1], alpha)
    elif shape == "paired":
        if y is None and isinstance(groups, (list, tuple)) and len(groups) == 2:
            r = _paired(kind, _numbers(groups[0]), _numbers(groups[1]), alpha)
        else:
            a, b = _paired_inputs(x, y)
            r = _paired(kind, a, b, alpha)
    elif shape == "one":
        r = _one_group(kind, _numbers(x), float(mu), alpha)
    elif shape == "many":
        r = _many_group(kind, _groups(groups), alpha)
    elif shape == "table":
        r = _table(kind, table or [], alpha)
    elif shape == "table2":
        if len(table or []) != 2:
            raise StatError("需要 2×2 列联表")
        r = _table("fisher", table, alpha)
    elif shape == "binom":
        r = _binom(kind, int(successes or 0), int(trials or 0), float(p0), alpha)
    else:                                                      # pragma: no cover
        raise StatError("未实现的输入形态：%s" % shape)
    r["kind"] = kind
    r["name"] = KINDS[kind][0]
    r["alpha"] = alpha
    r["significant"] = bool(r.get("p") is not None and r["p"] < alpha)
    r["notes"] = [KINDS[kind][2]]
    r["sentence"] = _sentence(r)
    return r


def _fmt(v, digits: int = 3) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return "—"
    return ("%%.%df" % digits) % v


def _sentence(r: dict) -> str:
    """把结果拼成一句可直接粘进论文/方案的结论。"""
    parts = []
    eff = r.get("effect") or {}
    if eff.get("value") is not None and eff.get("name"):
        s = "%s = %s" % (eff["name"], _fmt(eff["value"]))
        if eff.get("ci"):
            s += "（95%%CI %s–%s）" % (_fmt(eff["ci"][0]), _fmt(eff["ci"][1]))
        parts.append(s)
    st = "%s = %s" % ("统计量", _fmt(r.get("statistic")))
    if r.get("df") is not None:
        st += "，df = %s" % (r["df"] if isinstance(r["df"], list) else _fmt(r["df"], 1))
    parts.append(st)
    parts.append(_pct(r.get("p")))
    head = "%s 结果：" % r.get("name", r.get("kind", ""))
    tail = "，差异有统计学意义（α=%.2f）。" % r["alpha"] if r.get("significant") \
        else "，差异无统计学意义（α=%.2f）。" % r["alpha"]
    return head + "，".join(parts) + tail


# --------------------------------------------------------------------------- 效应量
def stat_effect_ci(kind: str, groups=None, x=None, y=None, table=None,
                   alpha: float = 0.05) -> dict:
    """效应量与 95%CI。kind 与 stat_run_test 同名（内部就是取同一次计算的效应量）。"""
    r = stat_run_test(kind, groups=groups, x=x, y=y, table=table, alpha=alpha)
    eff = r.get("effect") or {}
    eff2 = r.get("effect2") or {}
    return {"action": "effect", "kind": kind, "name": r.get("name"),
            "effect": eff, "effect2": eff2, "p": r.get("p"), "alpha": alpha,
            "sentence": r.get("sentence"),
            "text": "%s：%s = %s%s" % (r.get("name"), eff.get("name", ""),
                                       _fmt(eff.get("value")),
                                       ("（95%%CI %s–%s）" % (_fmt(eff["ci"][0]),
                                                              _fmt(eff["ci"][1])))
                                       if eff.get("ci") else "")}


# --------------------------------------------------------------------------- 样本量
def stat_sample_size(kind: str = "two_means", alpha: float = 0.05, power: float = 0.80,
                     d: float = None, sd: float = None, delta: float = None,
                     p1: float = None, p2: float = None, r: float = None) -> dict:
    """样本量估算（正态近似）。

    kind:
        two_means      两组均数比较：给 d（标准化效应量）或 sd+delta
        two_props      两组比例比较：给 p1、p2
        one_mean       单组均数与 μ₀ 比较：给 sd、delta
        correlation    相关：给 r
    """
    _, sp = _load()
    if sp is None:
        raise StatError("统计计算不可用：%s" % _ERR)
    z_a = float(sp.norm.ppf(1 - alpha / 2))
    z_b = float(sp.norm.ppf(power))
    kind = (kind or "two_means").strip()
    if kind == "two_means":
        if d is None:
            if not sd or not delta:
                raise StatError("两组均数比较需要 d（标准化效应量），或同时给 sd 与 delta")
            d = delta / sd
        if d == 0:
            raise StatError("效应量为 0 时无法估算样本量")
        n = 2 * ((z_a + z_b) / abs(d)) ** 2
        note = "每组 n ≈ %d（合计 %d）；d = %.3f" % (math.ceil(n), math.ceil(n) * 2, d)
    elif kind == "two_props":
        if p1 is None or p2 is None:
            raise StatError("两组比例比较需要 p1 与 p2")
        if p1 == p2:
            raise StatError("两组比例相同，无法估算样本量")
        pbar = (p1 + p2) / 2
        num = (z_a * math.sqrt(2 * pbar * (1 - pbar)) +
               z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        n = num / (p1 - p2) ** 2
        note = "每组 n ≈ %d（合计 %d）；p1 = %.3f，p2 = %.3f" % (math.ceil(n), math.ceil(n) * 2,
                                                                p1, p2)
    elif kind == "one_mean":
        if not sd or not delta:
            raise StatError("单组均数比较需要 sd 与 delta（与 μ₀ 的差值）")
        n = ((z_a + z_b) * sd / abs(delta)) ** 2
        note = "n ≈ %d；Δ = %.3f，SD = %.3f" % (math.ceil(n), delta, sd)
    elif kind == "correlation":
        if not r or abs(r) >= 1:
            raise StatError("相关分析需要 −1 < r < 1")
        zr = math.atanh(r)
        n = ((z_a + z_b) / abs(zr)) ** 2 + 3
        note = "n ≈ %d；r = %.3f" % (math.ceil(n), r)
    else:
        raise StatError("未知的样本量场景：%s（two_means | two_props | one_mean | correlation）"
                        % kind)
    return {"action": "sample_size", "kind": kind, "n": int(math.ceil(n)),
            "n_per_group": int(math.ceil(n)) if kind.startswith("two") else None,
            "alpha": alpha, "power": power, "note": note,
            "text": note + "（正态近似；α=%.2f，power=%.2f）" % (alpha, power),
            "sentence": "按 α=%.2f、把握度 %.0f%% 估算，%s。" % (alpha, power * 100,
                                                                note.split("；")[0])}


# --------------------------------------------------------------------------- 校正
def stat_correct_pvalues(pvals, method: str = "fdr_bh", alpha: float = 0.05) -> dict:
    """多重比较校正：bonferroni | holm | fdr_bh。"""
    np, _ = _load()
    if np is None:
        raise StatError("统计计算不可用：%s" % _ERR)
    vals = [float(v) for v in _numbers(pvals)]
    if not vals:
        raise StatError("没有 P 值")
    for v in vals:
        if not (0 <= v <= 1):
            raise StatError("P 值必须在 0–1 之间：%s" % v)
    method = (method or "fdr_bh").strip()
    if method not in CORRECTIONS:
        raise StatError("未知的校正方法：%s（支持 %s）" % (method, "、".join(CORRECTIONS)))
    n = len(vals)
    order = sorted(range(n), key=lambda i: vals[i])
    adj = [0.0] * n
    if method == "bonferroni":
        for i, v in enumerate(vals):
            adj[i] = min(1.0, v * n)
    elif method == "holm":
        running = 0.0
        for rank, i in enumerate(order):
            val = min(1.0, vals[i] * (n - rank))
            running = max(running, val)
            adj[i] = running
    else:                                                     # fdr_bh
        running = 1.0
        for rank, i in reversed(list(enumerate(order))):
            val = min(1.0, vals[i] * n / (rank + 1))
            running = min(running, val)
            adj[i] = running
    rows = [{"p": vals[i], "p_adj": adj[i], "keep": bool(adj[i] < alpha)} for i in range(n)]
    lines = ["%d. P = %.4g → P_adj = %.4g（%s）" % (i + 1, rows[i]["p"], rows[i]["p_adj"],
                                                   "显著" if rows[i]["keep"] else "不显著")
             for i in range(n)]
    kept = sum(1 for r in rows if r["keep"])
    return {"action": "correct", "method": method, "method_name": CORRECTIONS[method],
            "n": n, "rows": rows, "kept": kept, "alpha": alpha, "text": "\n".join(lines),
            "sentence": "对 %d 个 P 值采用%s校正（α=%.2f）：校正后 %d 个仍显著。"
                        % (n, CORRECTIONS[method].split("（")[0], alpha, kept)}


# --------------------------------------------------------------------------- 自检
if __name__ == "__main__":
    print("可用性：", available())
    a = [1, 2, 3, 4, 5]
    b = [6, 7, 8, 9, 10]
    t = stat_run_test("welch", groups=[a, b])
    print("welch:", _fmt(t["statistic"]), _pct(t["p"]), "|", t["sentence"])
    print("描述：", stat_describe([a, b], ["A", "B"])["text"])
    print("校正：", stat_correct_pvalues([0.01, 0.04, 0.03], "holm")["text"])
    print("样本量：", stat_sample_size("two_means", d=0.5)["text"])
    print("配对：", stat_run_test("ttest_paired", x=a, y=b)["sentence"])
    print("相关：", stat_run_test("pearson", x=[1, 2, 3], y=[2, 4, 6])["sentence"])
