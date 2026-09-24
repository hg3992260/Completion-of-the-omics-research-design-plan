# -*- coding: utf-8 -*-
"""只从真正的语言小节里取词块组（排除文章结构示意图的标签）。"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
recs = [json.loads(l) for l in io.open(os.path.join(HERE, "sci_scope_blocks.jsonl"),
                                       encoding="utf-8")]
SEC = ("title", "abstract", "introduction", "methods", "results", "discussion", "conclusion")
LANG_SUB = re.compile(r"(Language for|Useful Words|Using modal verbs|modal sentences|"
                      r"Verb tense|Prepositions|articles|Certainty|Linking|Paragraphing|"
                      r"Passive/Active|Owning your contribution|Clarity)", re.I)
for sec in SEC:
    sel = [r for r in recs if r["section"] == sec]
    groups, cur = [], None
    for r in sel:
        sub = r["subsection"] or ""
        if not LANG_SUB.search(sub):
            continue
        if r["kind"] == "phrase_group":
            cur = {"name": r["text"], "page": r["book_page"], "items": []}
            groups.append(cur)
        elif cur is not None and r["kind"] in ("word_list", "phrase_table"):
            t = r["text"]
            if 6 < len(t) < 160 and not t.startswith(("Examples from", "Notes", "Note:")):
                cur["items"].append((r["book_page"], t))
    print("=" * 72)
    print(f"### {sec}  组数 {len(groups)}")
    for g in groups:
        print(f"  [{g['name']}] 书p{g['page']}  ({len(g['items'])} 条)")
        for pg, t in g["items"][:4]:
            print(f"      p{pg}: {t[:110]}")
