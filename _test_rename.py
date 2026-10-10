# -*- coding: utf-8 -*-
"""自检：课题改名时 session 绑定迁移（rename_project_session）。"""
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                       # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kernel_config as kcfg                                            # noqa: E402

tmp = os.path.join(tempfile.mkdtemp(prefix="pcl_rename_"), "projects.json")
kcfg.projects_map_file = lambda: tmp                # 隔离到临时文件

kcfg.bind_project_session("旧课题", "ses_test123", title="旧课题")
before = kcfg.get_project_session("旧课题")
entry = kcfg.rename_project_session("旧课题", "新课题")
m = kcfg.read_projects_map()

ok = (before == "ses_test123"
      and "新课题" in m and "旧课题" not in m
      and m["新课题"]["sessionID"] == "ses_test123"
      and m["新课题"]["title"] == "新课题")
print("before =", before)
print("migrated entry =", entry)
print("map =", m)
print("结论：" + ("通过" if ok else "未通过"))
sys.exit(0 if ok else 1)
