# -*- coding: utf-8 -*-
"""实验设计完善 agent：把粗略的研究设想按十阶段标准流程逐步打磨。

每个阶段两轮：
    第一轮 追问 —— 产出【现状评估】【必须澄清的问题】【本阶段小结】
    第二轮 改写 —— 拿到研究者回答后产出【改写稿】【检查表】【风险提示】【下一步】

输出用【小标题】分节而不是 JSON，既可流式展示，也便于稳健解析。
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field

from stages_data import STAGES

HERE = os.path.dirname(os.path.abspath(__file__))
from app_paths import data_path

PROJECT_DIR = data_path("projects")          # 项目存档目录（冻结后在 exe 同级）

SYSTEM_PROMPT = """你是一位资深临床研究方法学教练，专长影像组学与多组学转化研究，熟悉 CLEAR、METRICS、\
TRIPOD+AI、PROBAST+AI、CLAIM、RQS、IBSI、MIAPE、MSI 等国际规范。你的任务是陪研究者把一个粗略的\
实验设想，按十个标准阶段逐步打磨到可执行、可发表、可复现的程度。

写作要求：
1. 中文，专业、具体、可执行，不要客套话，不要复述研究者原话。
2. 严格按用户指定的小标题输出；每节标题单独一行，格式为【标题】；不要用 Markdown 代码块包裹整体。
3. 提问必须针对这项研究的具体缺陷，不要写"样本量要足够""要考虑混杂"这类放之四海皆准的空话。
4. 改写稿保留研究者原有意图，直接给出可粘贴进研究方案的语句，含具体参数、时间窗、判定标准。
5. 涉及规范时写明条目编号（如 CLEAR 16、TRIPOD+AI 10、METRICS #6、IBSI）。

严禁（违反即视为无效输出）：
A. 输出任何关于你如何写作的说明、自我评价、字数统计、对提示词的复述或与读者的商量语句，例如
   "这一段约400字""可以吗""写得合适""需要一句话""建议文字："。小标题下一行必须直接是正文。
B. 复述或重抄任务要求里的话（如"可直接粘贴进研究方案""300-500字""需要针对具体缺陷"）。
C. 输出思考过程、内心独白、备选方案的比较。只给最终结论。
D. 在正文末尾追加对自己输出的点评（如"可能太多""这4条具体""格式正确""应该可以"）。

如果研究者没有提供某项信息，就按该领域的常规做法直接给出建议值，并在该句末标注（待确认），不要反问自己。"""


# --------------------------------------------------------------------------- 解析
SECTION_RE = re.compile(r"【\s*([^】]{1,20})\s*】")


def parse_sections(text: str) -> dict:
    """把【标题】正文 形式的输出切成字典。"""
    out, matches = {}, list(SECTION_RE.finditer(text or ""))
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            out[name] = body
    return out


def pick(sections: dict, *keys) -> str:
    for k in keys:
        for name, body in sections.items():
            if k in name:
                return clean_section(body)
    return ""


# 模型偶尔会把自己的写作说明混进正文，这里按行剔除
META_PATTERNS = (
    "可直接粘贴", "300-500", "300～500", "字以内", "字左右", "约400字", "约 400 字",
    "可以吗", "写得合适", "需要一句话", "这很具体", "需注意",
    "建议文字", "以下是", "如下：", "说明：本节", "不要太长", "写得不错",
    "需针对", "需要针对", "不要空话", "违反即视为",
    # 模型对自己输出的点评（实测高频）
    "字数", "可以。", "应该可以", "可能太多", "格式正确", "条具体", "这4条", "这3条",
    "这2条", "太长", "重复了", "符合要求", "要不要", "我觉得", "似乎", "允许。",
    "用户没有", "用户是", "用户要求", "只需三节", "需避免",
)

DROP_LINE_RE = re.compile(r"^[^，。；]{0,20}(可以|行|对吗|合适)吗？?$|^（?[^（）]{0,12}(待补充|略)）?$")


def clean_section(body: str) -> str:
    """剔除模型混入正文的写作说明 / 提示词复述 / 自我点评。"""
    out = []
    for line in (body or "").splitlines():
        s = line.strip()
        if not s:
            if out and out[-1] != "":
                out.append("")
            continue
        bullet = s.startswith(("-", "·", "*", "•")) or bool(re.match(r"^\d+[.、)]", s))
        if not bullet and len(s) < 100 and any(p in s for p in META_PATTERNS):
            continue
        if not bullet and DROP_LINE_RE.match(s):
            continue
        out.append(line.rstrip())
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out).strip()


def parse_questions(block: str) -> list[dict]:
    """把追问段落拆成 [{q, why}]。"""
    items = []
    for raw in re.split(r"\n(?=\s*(?:\d+[.、)]|[-*·]))", block or ""):
        line = raw.strip().lstrip("-*·").strip()
        line = re.sub(r"^\d+[.、)]\s*", "", line)
        if not line:
            continue
        parts = re.split(r"[｜|]\s*为什么", line, maxsplit=1)
        q = parts[0].strip().rstrip("？?").strip()
        why = ""
        if len(parts) > 1:
            why = parts[1].lstrip("问：: ").strip()
        if q:
            items.append({"q": q + "？" if not q.endswith("？") else q, "why": why})
    return items


def parse_checklist(block: str) -> list[str]:
    out = []
    for raw in (block or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[-*]\s*\[\s*[ xX]?\s*\]\s*", "", line)
        line = re.sub(r"^[-*·]\s*", "", line)
        if line:
            out.append(line)
    return out


# --------------------------------------------------------------------------- 数据模型
def stage_by_id(sid: int) -> dict:
    return next(s for s in STAGES if s["id"] == sid)


def blank_stage_state() -> dict:
    return {"status": "todo", "assessment": "", "questions": [], "answers": [],
            "draft": "", "final": "", "risks": "", "checklist": [], "updated": ""}


def q_text(q) -> str:
    """问题可能是字符串或 {q, why} 字典。"""
    if isinstance(q, dict):
        why = q.get("why") or ""
        return q.get("q", "") + (f"（{why}）" if why else "")
    return str(q)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


@dataclass
class Project:
    name: str = "未命名课题"
    raw_design: str = ""
    model: str = ""
    created: str = field(default_factory=_now)
    updated: str = field(default_factory=_now)
    path_: str = ""
    stages: dict = field(default_factory=dict)
    shape: dict = field(default_factory=dict)
    stat: dict = field(default_factory=dict)
    convergence: dict = field(default_factory=dict)
    transcript: list = field(default_factory=list)
    final_doc: str = ""

    def __post_init__(self):
        for s in STAGES:
            self.stages.setdefault(str(s["id"]), blank_stage_state())

    # -- 路径与命名 ---------------------------------------------------------
    @staticmethod
    def dir() -> str:
        os.makedirs(PROJECT_DIR, exist_ok=True)
        return PROJECT_DIR

    @staticmethod
    def sanitize(name: str) -> str:
        s = re.sub(r'[\\/:*?"<>|\s]+', "_", (name or "").strip())
        s = s.strip("._") or "未命名课题"
        return s[:60]

    @staticmethod
    def unique_path(name: str, keep: str = "") -> str:
        base = Project.sanitize(name)
        cand = os.path.join(Project.dir(), base + ".json")
        i = 2
        while os.path.exists(cand) and os.path.abspath(cand) != os.path.abspath(keep or ""):
            cand = os.path.join(Project.dir(), f"{base} ({i}).json")
            i += 1
        return cand

    @property
    def path(self) -> str:
        return self.path_ or self.unique_path(self.name)

    def exists_on_disk(self) -> bool:
        return bool(self.path_) and os.path.exists(self.path_)

    # -- 构造与持久化 -------------------------------------------------------
    @classmethod
    def new(cls, name: str, raw: str = "", model: str = "") -> "Project":
        p = cls(name=(name or "").strip() or "未命名课题", raw_design=raw or "", model=model)
        p.path_ = cls.unique_path(p.name)
        p.save()
        return p

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        p = cls(name=d.get("name") or "未命名课题",
                raw_design=d.get("raw_design", "") or "",
                model=d.get("model", "") or "")
        p.created = d.get("created") or p.created
        p.updated = d.get("updated") or p.created
        p.transcript = d.get("transcript") or []
        p.final_doc = d.get("final_doc", "") or ""
        for k, v in (d.get("stages") or {}).items():
            st = blank_stage_state()
            st.update(v or {})
            p.stages[k] = st
        p.shape = d.get("shape") or {}
        p.stat = d.get("stat") or {}
        p.convergence = d.get("convergence") or {}
        return p

    @classmethod
    def load(cls, path: str) -> "Project":
        p = cls.from_dict(json.load(open(path, encoding="utf-8")))
        p.path_ = path
        return p

    @classmethod
    def load_file(cls, path: str) -> "Project":
        return cls.load(path)

    def to_dict(self) -> dict:
        return {"name": self.name, "raw_design": self.raw_design, "model": self.model,
                "created": self.created, "updated": self.updated, "stages": self.stages,
                "shape": self.shape,
                "stat": self.stat,
                "convergence": self.convergence,
                "transcript": self.transcript[-60:], "final_doc": self.final_doc}

    def save(self, path: str | None = None) -> str:
        if path:
            self.path_ = path
        if not self.path_:
            # 没有路径时确定一个并记住它，否则每次保存都会新建一份副本
            self.path_ = self.unique_path(self.name)
        self.updated = _now()
        json.dump(self.to_dict(), open(self.path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return self.path

    # -- 项目管理 -----------------------------------------------------------
    @staticmethod
    def _meta(path: str) -> dict | None:
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            return None
        done = sum(1 for v in (d.get("stages") or {}).values()
                   if (v or {}).get("status") == "done")
        return {"path": path,
                "name": d.get("name") or os.path.splitext(os.path.basename(path))[0],
                "created": d.get("created", "—"),
                "updated": d.get("updated") or d.get("created", "—"),
                "model": d.get("model", ""),
                "done": done,
                "raw_len": len(d.get("raw_design") or ""),
                "size_kb": round(os.path.getsize(path) / 1024, 1)}

    @classmethod
    def list_all(cls) -> list[dict]:
        out = []
        for f in os.listdir(cls.dir()):
            if not f.endswith(".json") or f.startswith("_"):
                continue
            m = cls._meta(os.path.join(cls.dir(), f))
            if m:
                out.append(m)
        out.sort(key=lambda m: m["updated"], reverse=True)
        return out

    @classmethod
    def list_projects(cls) -> list[str]:
        return [m["name"] for m in cls.list_all()]

    def rename(self, new_name: str) -> str:
        """改名并同步移动文件；返回新的文件路径。

        重名时文件会带 (2) 之类的后缀，**显示名同步采用该后缀**，
        否则下拉框里会出现两个同名项目、无法分辨。
        """
        new_name = (new_name or "").strip()
        if not new_name or new_name == self.name:
            return self.path
        old = self.path
        # 先按旧路径生成唯一新路径（keep=old 表示允许覆盖自己的旧文件）
        probe = self.unique_path(new_name, keep=old)
        base = os.path.splitext(os.path.basename(probe))[0]
        self.name = base
        self.save(probe)
        if os.path.abspath(old) != os.path.abspath(probe) and os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass
        return probe

    def duplicate(self, new_name: str = "") -> "Project":
        copy = Project.from_dict(self.to_dict())
        copy.name = (new_name or "").strip() or f"{self.name} 副本"
        copy.created = _now()
        copy.path_ = Project.unique_path(copy.name)
        copy.save()
        return copy

    def delete(self) -> bool:
        if self.exists_on_disk():
            try:
                os.remove(self.path_)
                return True
            except OSError:
                return False
        return False

    def stats(self) -> dict:
        c = self.status_counts()
        return {"done": c["done"], "asked": c["asked"], "drafted": c["drafted"],
                "todo": c["todo"], "raw_len": len(self.raw_design.strip()),
                "updated": self.updated, "created": self.created}

    # -- 状态 ---------------------------------------------------------------
    def stage(self, sid: int) -> dict:
        return self.stages[str(sid)]

    def done_summary(self, upto: int | None = None) -> str:
        """已定稿阶段的摘要，供后续阶段参考。"""
        rows = []
        for s in STAGES:
            if upto is not None and s["id"] >= upto:
                continue
            st = self.stage(s["id"])
            text = (st.get("final") or "").strip()
            if text:
                rows.append(f"· {s['id']:02d} {s['title']}：{text[:220]}")
        return "\n".join(rows) or "（尚无定稿阶段）"

    def status_counts(self) -> dict:
        c = {"todo": 0, "asked": 0, "drafted": 0, "done": 0}
        for s in STAGES:
            key = self.stage(s["id"]).get("status", "todo")
            c[key] = c.get(key, 0) + 1
        return c

    # -- 文档 ---------------------------------------------------------------
    def render_doc(self) -> str:
        lines = [f"# {self.name}", "",
                 f"（由「组学研究设计工作台」生成 · {self.created} · 模型 {self.model or '—'}）", "",
                 "## 研究设想（原始输入）", "", self.raw_design.strip() or "（未填写）", "",
                 "## 分阶段完善稿", ""]
        for s in STAGES:
            st = self.stage(s["id"])
            body = (st.get("final") or st.get("draft") or "").strip()
            mark = {"done": "✅", "drafted": "◐", "asked": "◔"}.get(st.get("status"), "○")
            lines.append(f"### {mark} {s['id']:02d} {s['title']}　`{s['spec']}`")
            lines.append(body if body else "（尚未完成本阶段）")
            if st.get("questions"):
                lines.append("")
                lines.append("**追问与回答**")
                for i, q in enumerate(st["questions"]):
                    ans = st["answers"][i] if i < len(st["answers"]) else ""
                    lines.append(f"- 问：{q_text(q)}")
                    lines.append(f"  答：{ans or '（未回答）'}")
            if st.get("checklist"):
                lines.append("")
                lines.append("**检查表**")
                lines += [f"- [ ] {c}" for c in st["checklist"]]
            if st.get("risks"):
                lines.append("")
                lines.append("**风险提示**")
                for r in re.split(r"\n(?=\s*[-*·]|\s*\d+[.、])", st["risks"].strip()):
                    r = re.sub(r"^\s*[-*·]\s*|\s*\d+[.、]\s*", "", r.strip())
                    if r:
                        lines.append(f"- {r}")
            lines.append("")
        if self.final_doc.strip():
            lines += ["## 汇总设计草案", "", self.final_doc.strip(), ""]
        return "\n".join(lines)


# --------------------------------------------------------------------------- Agent
class DesignAgent:
    """把 LLM 调用与提示词组装封装起来（不依赖 Qt，便于单独测试）。"""

    def __init__(self, client, project: Project):
        self.client = client
        self.project = project

    # -- 提示词 -------------------------------------------------------------
    def _stage_brief(self, sid: int) -> str:
        s = stage_by_id(sid)
        return (f"【当前阶段】第 {sid} 阶段：{s['title']}\n"
                f"规范出处：{s['spec']}\n"
                f"本阶段必做动作：" + "；".join(s["actions"]) + "\n"
                f"本阶段必报参数：" + "；".join(s["reports"]) + "\n"
                f"本阶段常见缺陷：" + "；".join(s["pitfalls"]) + "\n"
                f"参考条目：" + " / ".join(s["refs"]))

    def _base(self, sid: int) -> str:
        return (f"【研究者的初步设计描述】\n{self.project.raw_design.strip()}\n\n"
                f"【已完成阶段的定稿摘要】\n{self.project.done_summary(upto=sid)}\n\n"
                f"{self._stage_brief(sid)}")

    def kickoff_messages(self) -> list[dict]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"【研究者的初步设计描述】\n{self.project.raw_design.strip()}\n\n"
                "请输出三节，全部为最终结论，不要输出你的取舍过程：\n"
                "【设计速读】不超过 4 句：这项研究打算做什么、用什么数据、回答什么问题，"
                "并指出它属于诊断研究还是预后研究。\n"
                "【首要关注点】恰好 3 条，每条一行，格式严格为：关注点 ｜ 对应阶段。"
                "不要复述这个格式要求，不要出现第 4 条。\n"
                "【路线说明】一句话说明接下来将按十阶段标准流程逐个推进。"},
        ]

    def ask_messages(self, sid: int) -> list[dict]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                self._base(sid) + "\n\n请输出三节：\n"
                "【现状评估】2-4 句，指出该设计与本阶段标准要求的具体差距，"
                "必须引用研究者描述里的实际内容，不要泛泛而谈。\n"
                "【必须澄清的问题】2-4 条，每条格式：问题？｜为什么问：一句话。"
                "问题要能直接决定该阶段的参数取值。\n"
                "【本阶段小结】一句话说明回答这些问题后能补齐什么。"},
        ]

    def rewrite_messages(self, sid: int) -> list[dict]:
        st = self.project.stage(sid)
        qa = []
        for i, q in enumerate(st.get("questions", [])):
            a = st["answers"][i] if i < len(st.get("answers", [])) else ""
            qa.append(f"问：{q}\n答：{a or '（未回答，请按常规做法给出建议值并标注待确认）'}")
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                self._base(sid) + "\n\n【追问与回答】\n" + "\n".join(qa) + "\n\n"
                "请输出四节：\n"
                "【改写稿】小标题下一行直接开始写方案正文（不要写“建议文字”或复述本节要求），"
                "300-500 字，含具体参数、时间窗、判定标准与执行方式；保留研究者原有意图。\n"
                "【检查表】3-5 条，每条格式：- [ ] 条目 ｜ 依据：规范与条目号。\n"
                "【风险提示】1-3 条本阶段最容易翻车的点。\n"
                "【下一步】一句话指向下一阶段。"},
        ]

    def finalize_messages(self) -> list[dict]:
        done = []
        for s in STAGES:
            st = self.project.stage(s["id"])
            body = (st.get("final") or st.get("draft") or "").strip()
            if body:
                done.append(f"{s['id']:02d} {s['title']}：{body}")
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"【研究者的初步设计描述】\n{self.project.raw_design.strip()}\n\n"
                "【各阶段定稿】\n" + "\n\n".join(done) + "\n\n"
                "请把以上内容整合成一份完整、连贯、可直接用于伦理申报或课题标书的研究设计草案，"
                "输出三节：\n"
                "【设计草案】1500 字以内，分小标题组织（研究问题 / 数据与人群 / 影像与组学流程 / "
                "统计与建模 / 验证策略 / 预期产出）。\n"
                "【待补数据清单】研究者还需要提供或采集的信息，逐条列出。\n"
                "【投稿前自查】按 CLEAR / TRIPOD+AI / METRICS 要点列出 5-8 条自查项。"},
        ]

    # -- scope 页（Statistic / SCI Shape）的引导式对话 -----------------------
    SCOPE_ROLE = {
        "stat": "统计方法学教练：熟悉诊断/预后研究的统计分析方案（SAP）、功效分析、前提诊断与"
                "多重比较校正，也熟悉 CLEAR / METRICS / TRIPOD+AI 对统计报告的要求。",
        "shape": "SCI 论文写作教练：熟悉 Glasman-Deal《Science Research Writing》的七章通用模型、"
                 "时态与内容边界，按目标期刊惯例把控每一章的成稿。",
    }

    def _scope_brief(self, page: str, sec: dict) -> str:
        """把该环节的规范内容整段喂给模型 —— 引导必须"基于内容"。"""
        L = [f"【本环节】{sec.get('title', '')}（{sec.get('spec', '')}）"]
        if sec.get("desc"):
            L.append(f"环节定位：{sec['desc']}")
        if sec.get("goal"):
            L.append("本环节要点：\n" + "\n".join("  · " + str(x) for x in sec["goal"]))
        if sec.get("model"):
            L.append("通用模型组件（按顺序）：\n" + "\n".join(
                f"  {i}. {m.get('en', '')} — {m.get('zh', '')}"
                for i, m in enumerate(sec["model"], 1)))
        if sec.get("must"):
            L.append("必须写到：\n" + "\n".join("  ✓ " + str(x) for x in sec["must"]))
        if sec.get("must_not"):
            L.append("不得出现：\n" + "\n".join("  ✕ " + str(x) for x in sec["must_not"]))
        if sec.get("language"):
            L.append("语言与时态规则：\n" + "\n".join(
                f"  · {r['rule']}（{r.get('page', '')}）" for r in sec["language"]))
        if sec.get("example"):
            L.append("示例化表述：" + str(sec["example"]).replace("\n", " / "))
        if sec.get("formula"):
            L.append("公式与参数：" + " ；".join(str(x) for x in sec["formula"]))
        if sec.get("pitfalls"):
            L.append("常见陷阱：\n" + "\n".join("  ✕ " + str(x) for x in sec["pitfalls"]))
        if sec.get("output"):
            L.append("本环节应产出：" + "；".join(str(x) for x in sec["output"]))
        L.append("自检清单（回答与定稿都要对着它）：\n" + "\n".join(
            f"  {i}. {c}" for i, c in enumerate(sec.get("checks", []), 1)))
        if sec.get("note"):
            L.append("补充说明：" + str(sec["note"]))
        return "\n".join(L)

    def _scope_context(self, page: str, sec: dict) -> str:
        """把项目的**全部已有内容**交给模型，让它自己判断哪些与本环节相关
        （代码不再指定"这一环节该看哪几条"）。"""
        import coupling
        return (coupling.project_digest(self.project) +
                "\n\n上面是本项目的全部素材。请自行判断其中哪些与本环节相关，"
                "并在提问与定稿中只引用真正相关的内容；若某类素材缺失，"
                "请按常规做法给出建议值并标注需要研究者确认的地方。")

    def scope_ask_messages(self, page: str, sec: dict) -> list[dict]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n本次角色：" + self.SCOPE_ROLE[page]},
            {"role": "user", "content":
                self._scope_context(page, sec) + "\n\n" + self._scope_brief(page, sec) + "\n\n"
                "请针对**本环节**输出三节（全部为最终结论，不要输出你的思考过程）：\n"
                "【现状评估】2-4 句：对照本环节的要点与自检清单，指出本项目当前内容的具体缺口，"
                "必须引用上面已有的实际内容，不要泛泛而谈。\n"
                "【必须澄清的问题】2-4 条，每条格式：问题？｜为什么问：一句话。"
                "问题要能直接决定本环节的参数取值或措辞选择。\n"
                "【本环节小结】一句话说明回答这些问题后能补齐什么。"},
        ]

    def scope_rewrite_messages(self, page: str, sec: dict) -> list[dict]:
        store = (self.project.stat if page == "stat" else self.project.shape) or {}
        node = store.get(sec["key"]) or {}
        qa = []
        for i, q in enumerate(node.get("questions", [])):
            a = node["answers"][i] if i < len(node.get("answers", [])) else ""
            qa.append(f"问：{q}\n答：{a or '（未回答，请按常规做法给出建议值并标注待确认）'}")
        target = ("可直接放进统计分析方案（SAP）的段落：含具体检验、参数、判定标准与执行方式"
                  if page == "stat" else
                  "该章节的成稿文字：按上面通用模型组件的顺序组织，300-600 字，"
                  "时态与内容边界遵守上面列的规则")
        return [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n本次角色：" + self.SCOPE_ROLE[page]},
            {"role": "user", "content":
                self._scope_context(page, sec) + "\n\n" + self._scope_brief(page, sec) +
                "\n\n【追问与回答】\n" + "\n".join(qa) + "\n\n"
                "请输出四节：\n"
                f"【定稿】小标题下一行直接开始正文（不要写“建议文字”，不要复述要求）。{target}。\n"
                "【检查表】逐条判断上面的自检清单是否已被你的定稿满足，格式严格为："
                "`- [x] 编号` 或 `- [ ] 编号`，编号即自检清单序号，覆盖清单全部条目。\n"
                "【风险提示】1-3 条本环节最容易翻车的点。\n"
                "【下一步】一句话指向下一个环节。"},
        ]

    # -- 调用 ---------------------------------------------------------------
    def run(self, messages: list[dict], on_delta=None) -> dict:
        return self.client.chat(messages, stream=on_delta is not None, on_delta=on_delta)

    def record(self, role: str, text: str, sid: int | None = None, meta: str = ""):
        self.project.transcript.append({"role": role, "text": text, "stage": sid,
                                        "meta": meta, "ts": time.strftime("%H:%M:%S")})
        if len(self.project.transcript) > 60:
            self.project.transcript = self.project.transcript[-60:]


    # -- 收敛推理（总览页：由模型判断收敛关系，代码不做任何映射）--------------
    def convergence_messages(self) -> list[dict]:
        """把项目全部内容原样交给模型，由它自行推断「该收敛到哪一章、还缺什么」。
        代码里不存在章节与阶段/统计的对应表 —— 判断与理由都由模型给出。"""
        import coupling
        return [
            {"role": "system", "content":
                SYSTEM_PROMPT + "\n\n本次角色：投稿可行性评审。你要**自行推断**这些素材"
                "分别支撑论文的哪一章，并指出还缺什么；不存在任何预设的对应关系，"
                "你的判断依据必须写清楚。"},
            {"role": "user", "content":
                coupling.project_digest(self.project) + "\n\n"
                "请通读上面全部素材，自行判断它们的归属与完整度，并严格按下面的格式输出：\n"
                "【收敛总览】2-3 句：这份稿件现在收敛到什么程度、最大瓶颈是什么。\n"
                "【本章来源对照】一句话说清你依据什么判断归属（例如按内容主题、按变量与终点、"
                "按时间窗等），不要复述格式要求。\n"
                "【各章收敛】对 Title、Abstract、Introduction、Methods、Results、Discussion、"
                "Conclusion 依次输出一节，每节严格为：\n"
                "### 英文章节名\n"
                "来源：<支撑这一章的素材来自上面哪些条目，用分号分隔；没有就写 无>\n"
                "已有：<这一章现在能写出什么实质内容，100 字内>\n"
                "缺失：<还缺什么才能动笔，用分号分隔；没有就写 无>\n"
                "就绪度：<0 到 100 的整数>\n"
                "理由：<为什么这样判断，一句话>\n"
                "【下一批动作】3-5 条，按优先级排序，每条一行，直接写要做的事。"},
        ]


def parse_convergence(text: str) -> dict:
    """解析收敛推理结果 → {overall, basis, chapters:[{title, sources, have, missing,
    readiness, reason}], actions:[...]}。格式不完整时尽力而为，不抛异常。"""
    sec = parse_sections(text or "")
    out = {"overall": pick(sec, "收敛总览"),
           "basis": pick(sec, "本章来源对照", "来源对照"),
           "chapters": [], "actions": []}
    body = pick(sec, "各章收敛", "收敛")
    cur = None
    for raw in (body or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if cur:
                out["chapters"].append(cur)
            cur = {"title": line.lstrip("#").strip(), "sources": "", "have": "",
                   "missing": "", "readiness": None, "reason": ""}
            continue
        if cur is None:
            continue
        m = re.match(r"^(来源|已有|缺失|就绪度|理由)\s*[:：]\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "来源":
            cur["sources"] = val
        elif key == "已有":
            cur["have"] = val
        elif key == "缺失":
            cur["missing"] = val
        elif key == "理由":
            cur["reason"] = val
        else:
            num = re.search(r"\d{1,3}", val)
            cur["readiness"] = min(100, int(num.group(0))) if num else None
    if cur:
        out["chapters"].append(cur)
    for raw in (pick(sec, "下一批动作", "下一步动作", "下一步") or "").splitlines():
        line = re.sub(r"^\s*(?:[-*·]|\d+[.、)])\s*", "", raw).strip()
        if line:
            out["actions"].append(line)
    return out


if __name__ == "__main__":                                        # 离线自检
    p = Project(name="_selftest", raw_design="回顾性收集 200 例胰腺囊性病变 CT，做影像组学预测恶性。")
    demo = ("【现状评估】描述未提及扫描参数与期相……\n"
            "【必须澄清的问题】\n1. CT 是平扫还是增强？｜为什么问：期相决定纹理特征是否可比。\n"
            "2. 病理金标准如何定义？｜为什么问：结局定义决定标签质量。\n"
            "【本阶段小结】回答后可补齐数据来源与参考标准。")
    sec = parse_sections(demo)
    print("sections:", list(sec))
    print("questions:", parse_questions(pick(sec, "必须澄清")))
    print("checklist:", parse_checklist("- [ ] 写明期相 ｜ 依据：CLEAR 16\n· 报告重建核"))
    p.stage(1)["final"] = "已定稿内容"
    p.stage(1)["status"] = "done"
    print("counts:", p.status_counts())
    print("doc chars:", len(p.render_doc()))
