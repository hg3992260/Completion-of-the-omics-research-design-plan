# opencode 嵌入交接文档（可复用 Playbook）

> 目标：把 **opencode 当作驱动 agent** 嵌进任意宿主程序，并**让该宿主成为 opencode 的 MCP 工具服务**；
> 下一次可直接照此流程复用。
>
> 本文基于 PCLRadiomics（Python/3.11 + PySide6，宿主）嵌入 opencode **v1.18.35** 的实测实现整理，
> 标注 ✅ = 已实测验证，⚠️ = 已验证但需注意，未标 = 按源码/契约实现。
> 对应文件均在本仓库：`kernel_client.py / kernel_driver.py / kernel_boot.py / kernel_config.py / kernel_assets/`。

---

## 1. 适用场景

- 你有一个**有领域能力**的程序（算法/工具/数据），想让它被一个**真正的 agent** 自主编排调用。
- 你不想自己实现 agent loop，而是直接用 opencode（原生 function calling、18 内置工具、skills、subagents）。
- 结论形态：**opencode = 大脑；你的程序 = MCP 工具提供方 + 可选的会话宿主/控制面。**

---

## 2. 架构：四个角色、两个方向

| # | 关系 | 方向 | 协议 | 谁主动 |
|---|---|---|---|---|
| **A** | 内核调用宿主领域能力（**宿主是 opencode 的 MCP 服务**） | 内核 → 宿主 | **MCP** | 内核（客户端） |
| **B** | 宿主驱动内核（建会话/发消息/收事件/问答回灌） | 宿主 → 内核 | **HTTP（legacy V1）** | 宿主（客户端） |
| C | 外部 agent 调用宿主 | 外部 → 宿主 | MCP | 外部（与 A 同一套工具面） |
| D | 宿主托管内核进程 | — | 子进程 | 宿主 |

> **最重要的事实**：opencode **只做 MCP 客户端，永不提供 MCP 服务端**
> （`opencode mcp` 只有 add/list/auth/logout/debug，没有 serve）。
> 所以「宿主是 opencode 的 MCP 服务」= 方向 A，这是唯一正确的方向。

数据流：
```
宿主 GUI 动作 ──方向B(HTTP)──► opencode 会话/引擎
      ▲                              │ 调工具
      │ question/permission 回灌      ▼
      └──────────────────────── 宿主的 MCP 工具（方向A）──► 写宿主的领域数据
        opencode 终端(TUI) 复用同一会话（宿主可用 TUI 控制 API 让它切会话）
```

---

## 3. 通道选型（踩坑后的硬结论）

| 用途 | ✅ 采用 | ❌ 不要用 | 原因（实测） |
|---|---|---|---|
| 起内核 | `opencode serve --hostname 127.0.0.1`（随机端口） | — | 冷启动到 health ≈ 0.9–1.5s |
| **投递一轮任务** | **legacy V1：`POST /session/:id/message`** | V2 `POST /api/session/:id/prompt` | V2 的模型解析只认 `opencode/*` 自有模型；用用户 `auth.json` 里的 provider（如 deepseek）会 `ModelUnavailableError` |
| 取会话/消息 | legacy `/session`、`/session/:id/message` | — | V1 `SessionPrompt` 在**服务端**执行，直接用 auth.json 的 provider |
| 完成判定 | 阻塞式 `prompt` 的**返回值**（`parts` 含 step-finish） | `POST /api/session/:id/wait` | 该端点在本构建返回 **503 "not available yet"** |
| 问答/权限回灌 | legacy `/question`、`/permission`（轮询发现待决 → `.../reply`） | 依赖 `/event` SSE 推送 | legacy `/event` 实测只到 `server.connected`，不推 message/question |
| 事件归一化 | `prompt` 返回的 `parts` + 轮询 `/session/:id/message` | — | 返回值 `parts` **不含 tool 类型**（工具在服务端执行）；要看工具调用需轮询消息 |
| TUI 界面 | `opencode attach <url> ...`（**直接 spawn**，不经 powershell） | 裸跑 `opencode` | 裸跑会自建第二个 server，争用同一 sqlite |
| TUI 切会话（复用窗口） | `POST /tui/select-session {sessionID}` ✅ | 每次重开终端窗口 | 实测 TUI pid 不变、进程数不变 |
| TUI 提示 | `POST /tui/show-toast {message,variant}` ✅ | — | 实测 TUI 顶部出现提示 |
| 改会话标题 | `PATCH /session/:id {title}` ✅ | — | 改名时同步 opencode 会话标题 |

---

## 4. 组件清单（宿主侧）

| 文件 | 职责 | 关键 API |
|---|---|---|
| `kernel_client.py` | 传输层：进程托管（方向D）、HTTP、legacy 会话/问答/权限、TUI spawn、进程列举 | `ensure_running/adopt_state/stop`、`create_session`、`prompt_legacy`、`post_noreply`、`legacy_questions/reply`、`legacy_permissions/reply`、`update_session_title`、`tui_select_session`、`tui_show_toast`、`spawn_tui`、`list_processes`、`kernel_env`、`opencode_exe` |
| `kernel_driver.py` | 会话驱动层：事件归一化、`run_turn`、问答/权限回灌、会话消息轮询（工具可见） | `KernelDriver.run_turn/run_turn_async`、`normalize_event`、`parts_to_events`、`pending_questions/answer_question`、`_fetch_messages/_iter_parts/_emit_part` |
| `kernel_boot.py` | GUI↔内核总控：启动即拉起内核+注册 MCP+绑会话+开 TUI；单窗口复用/清理；改名联动 | `KernelBoot.start/stop`、`driver()`、`run_task()`、`ensure_project_session`、`switch_project`、`rename_project`、`_ensure_tui/_spawn_tui/_reap_extra_attach` |
| `kernel_config.py` | 隔离 home 的配置/凭据/skill/agent/项目↔会话映射/随包资产安装 | `paths/read_config/merge_config`、`read_auth/write_auth/import_host_llm_key`、`install_skill/install_builtin_assets`、`bind/get/rename_project_session` |
| `kernel_assets/` | 随包 agent/skill 模板（安装到隔离 home） | `agent/*.md`、`skill/<name>/SKILL.md` |

---

## 5. 移植到新程序的步骤（Checklist）

### 5.1 取得 opencode 二进制
- ✅ 推荐：下载 release `opencode-windows-x64.zip`（与版本号对应），放 `<app_home>/opencode/opencode.exe`。
- 体积参考：**172 MB**；冷启动到 health **≈0.9s**。
- 若要从源码构建：`bun install --ignore-scripts`、设 `OPENCODE_CHANNEL/OPENCODE_VERSION`、`--skip-embed-web-ui`（详见 `build_opencode_kernel.bat`）。

### 5.2 隔离 home + 环境变量（务必在**启动内核前**设好）
```
XDG_DATA_HOME   = <KERNEL_HOME>/data        # auth.json / sqlite / log 落点
XDG_CONFIG_HOME = <KERNEL_HOME>/config      # opencode.json / agent / skill
XDG_STATE_HOME  = <KERNEL_HOME>/state
XDG_CACHE_HOME  = <KERNEL_HOME>/cache
OPENCODE_CONFIG_DIR = <KERNEL_HOME>/config/opencode   # 更精确的 config 覆盖
OPENCODE_CLIENT = desktop      # 关键：让 question 工具注册（registry.ts）
OPENCODE_DISABLE_AUTOUPDATE = 1
# 不设 OPENCODE_TEST_HOME → 保留用户 ~/.claude/skills 等（读取不算污染）
```
> ⚠️ 这些变量在 opencode 模块加载时求值，**运行中改无效** → 切换隔离/共享要重启内核。
> ⚠️ 隔离 home 与用户真实 `~/.local/share/opencode` 完全分离，绝不污染。

### 5.3 起内核（方向 D）+ 健康检查 + 孤儿清理
- `spawn`：`opencode serve --hostname 127.0.0.1`（端口 0 = 随机），从 stdout 抓 `listening on http://host:port`。
- 健康检查：`GET /global/health` → `{healthy, version}`。
- 状态文件记 `{pid, port, password}`（0600）；启动时 `adopt_state()` 接管存活实例（否则每次都会多起一个内核）。
- 密码只走环境变量 `OPENCODE_SERVER_PASSWORD`（**不进命令行**，避免进程列表泄露）。
- 停止：`terminate` → 超时 `taskkill /T /F`（Windows）。

### 5.4 方向 A：宿主暴露 MCP，并注册给内核
1. 宿主用 FastMCP（或任意 MCP 库）在**本进程内后台线程**起 **streamable-http** 端点：
   `http://127.0.0.1:<port>/mcp`（不要用 stdio —— windowed 构建下会与主进程抢标准流）。
2. 写内核配置 `<KERNEL_HOME>/config/opencode/opencode.json`：
   ```jsonc
   {
     "$schema": "https://opencode.ai/config.json",
     "model": "deepseek/deepseek-flash",
     "mcp": {
       "your-workbench": {                       // ⚠️ 键名是 `mcp`，不是 `mcpServers`
         "type": "remote",
         "url": "http://127.0.0.1:<port>/mcp",
         "enabled": true,
         "timeout": 600000                        // ⚠️ 默认 5000ms，长任务必超时
       }
     }
   }
   ```
3. 验证：`opencode mcp list` 显示 `✓ your-workbench connected`；内核日志 `init count` = 18 + 你的工具数。
   ✅ 实测：宿主 24 个工具 → opencode 自主调用 `your-workbench_xxx` 并拿到结果。

### 5.5 方向 B：投递任务（legacy V1）
```
POST /session                       {"title": "..."}                 → {id,...}          # 建会话
POST /session/:id/message           {"parts":[{"type":"text","text":"..."}],
                                     "model":{"providerID":"deepseek","modelID":"deepseek-flash"}}
                                    → 阻塞到本轮结束，返回 {info:{finish,...}, parts:[...]}
GET  /session/:id/message           → 全部消息（轮询可见 tool 调用）
PATCH /session/:id                  {"title":"新名"}
POST /session/:id/abort
```
- `model` 用 V1 形状 `{providerID, modelID}`；不传则可能落到 `opencode/*` 默认模型。
- 完成判定用该 POST 的返回（`info.finish`），不要用 `/wait`（503）。

### 5.6 问答 / 权限回灌（GUI 就地作答）
```
GET  /question                      → [Question.Request]  {id, sessionID, questions:[{question,header,options:[{label,description}],multiple?,custom?}]}
POST /question/:rid/reply           {"answers":[["继续"]]}   # 按问题顺序，每个答案是"已选 label 数组"
POST /question/:rid/reject
GET  /permission                    → [PermissionV1.Request] {id, sessionID, action, resources,...}
POST /permission/:rid/reply         {"reply":"once|always|reject", "message":"..."}
```
- 内核会**阻塞等待**回复；宿主必须实现回复（否则会话挂死）。用后台轮询 `/question`、`/permission` 发现待决 → 路由到 GUI 弹窗/输入。
- ✅ 实测：模型调用 `question` → GUI 就地答「继续」→ 阻塞的会话继续并回「已继续」。

### 5.7 TUI 交互面（保留 opencode 全部功能）
- 启动：`opencode attach <url> --dir <project_dir> [--session <sid>]`，**直接 spawn**（一个进程=一个终端，便于精确回收）。
- 只保留一个终端：切换时先树杀旧 TUI，再扫描**同源 exe 路径**的 opencode 进程，只留 `serve`+当前 `attach`（**不碰用户自己装的 opencode**）。
- **复用同一窗口切会话**：`POST /tui/select-session {sessionID}`（✅ TUI pid 不变）。
- 切换提示：`POST /tui/show-toast {message,variant}`（✅ TUI 顶部出现提示）。
- 可选：`POST /tui/execute-command {command}`（session.new/list/…）、`/tui/append-prompt`、`/tui/submit-prompt`。

### 5.8 项目↔会话绑定 / 改名 / 标题
- 绑定表存 `<KERNEL_HOME>/projects.json`：`{projectName: {sessionID, title, bound_at}}`。
- 切项目：命中绑定就复用，否则 `POST /session` 新建；随后 `select-session` 让 TUI 跟过去。
- **改名**：迁移绑定键（**沿用同一 sessionID**，不新建）+ `PATCH /session/:id {title}` 更新会话标题 + `select-session`/toast 跟随。

### 5.9 凭据
- 内核凭据落 `<KERNEL_HOME>/data/opencode/auth.json`：`{providerID:{type:"api",key}}`，**0600**。
- 冻结产物隔离 home 默认**没有** auth.json（易踩：点了报 500）→ 提供首次自动导入或 `kernel auth import-host`。
- 宿主自己的 LLM 凭据链与 opencode 的 auth.json 是两套；opencode 只需要 auth.json（方向 A 的宿主工具内部若用宿主 LLM，则宿主那套也要就绪）。

### 5.10 打包（PyInstaller 示例）
- `datas` 收集：opencode 二进制 → 目标目录 `opencode`；随包 `kernel_assets/` → 目标 `kernel_assets`。
- `hiddenimports`：`kernel_client/kernel_config/kernel_cli/kernel_boot/kernel_driver`。
- 加「前置导入校验」：对硬编码的本地模块逐个 `__import__`，失败即中止构建（免得产出坏包）。
- onefile 会把内核解包到 `%TEMP%` 并**锁住**临时目录 → 主进程退出挂死；如需 onefile，先把内核复制到 exe 同级再从稳定位置启动，或只出 onedir。
- ✅ 实测：windowed onedir 产物 ≈367 MB，含 `_internal/opencode/opencode.exe` 与 `_internal/kernel_assets/`；冻结包 `kernel selftest` exit=0。

---

## 6. 端点速查（legacy V1）

| 目的 | 方法 + 路径 | 载荷/返回 |
|---|---|---|
| 健康 | GET `/global/health` | `{healthy,version}` |
| 建会话 | POST `/session` | `{title?,model?,agent?}` → Session.Info |
| 投递（阻塞） | POST `/session/:id/message` | `{parts:[{type:"text",text}],model?}` → `{info,parts}` |
| 发消息不回话 | POST `/session/:id/message` | 加 `"noReply": true` |
| 列消息 | GET `/session/:id/message` | 消息+parts |
| 改标题 | PATCH `/session/:id` | `{title}` |
| 中断 | POST `/session/:id/abort` | — |
| 待决问题 | GET `/question` | Question.Request[] |
| 答问题 | POST `/question/:rid/reply` | `{answers:[[label,...]]}` |
| 拒问题 | POST `/question/:rid/reject` | — |
| 待决权限 | GET `/permission` | PermissionV1.Request[] |
| 答权限 | POST `/permission/:rid/reply` | `{reply,message?}` |
| TUI 切会话 | POST `/tui/select-session` | `{sessionID}` → bool |
| TUI 提示 | POST `/tui/show-toast` | `{message,variant,title?}` → bool |
| TUI 命令 | POST `/tui/execute-command` | `{command}` → bool |
| MCP 清点 | CLI `opencode mcp list` | 文本 |

---

## 7. 自检脚本（随本仓库）

| 脚本 | 验证 |
|---|---|
| `_test_driver.py` | 驱动层 + 问答回灌（内核/凭据/建会话/纯文本/归一化/question 回灌） ✅ OK=10 |
| `_test_assets.py` | 内核是否识别随包 agent/skill ✅ 通过 |
| `_test_sections.py` | 通用分节工具（stat/shape）读写往返 ✅ 通过 |
| `_test_gui_bridge.py` | `KernelBoot.start→run_task→driver.run_turn`（无 TUI）✅ 通过 |
| `_test_gui_point.py` | offscreen 真实窗口的信号回流 ✅ 通过 |
| `_test_console.py` | 底部状态/日志面板的展开折叠 ✅ 通过 |
| `_test_rename.py` | 改名时的会话绑定迁移 ✅ 通过 |

---

## 8. 常见坑与解法

| 现象 | 根因 | 解法 |
|---|---|---|
| 宿主工具一个都调不到 | 把内核接到**不支持 function calling** 的宿主上游 | 内核必须走 opencode 原生 provider；宿主模型只可作为 `llm_chat` 一类 MCP 工具 |
| `ModelUnavailableError: provider/model` | 走了 V2 `/api/session`（只认 `opencode/*`） | 改用 legacy `/session/:id/message` |
| 会话永久卡住 | 内核在等 question/permission 回复，宿主没实现 | 轮询 `/question`、`/permission` 并回灌；加超时兜底 |
| 工具调用在返回值里看不到 | legacy `prompt` 返回的 parts 不含 tool | 轮询 `GET /session/:id/message` 取 tool parts |
| `session/wait` 报 503 | 该端点未就绪 | 用阻塞 `prompt` 的返回判完成 |
| MCP 长任务超时 | `mcp.timeout` 默认 5000ms | 写 `opencode.json` 时显式设大（如 600000） |
| 每敲一条命令多一个内核 | 只"报告复用"未"接管"存活实例 | `adopt_state()` 真正接管 |
| 切换后多出终端窗口 | powershell 起 attach，只杀父进程 | 直接 spawn + 树杀 + 按 exe 路径回收多余 attach |
| 冻结后点 opencode 功能报 500 | 隔离 home 无 auth.json | 首次自动 `auth import-host` 或显式导入 |
| onefile 退出挂死 | 内核锁住 `%TEMP%` 解包目录 | 复制内核到 exe 同级再启动，或只用 onedir |
| GBK 控制台打印崩溃 | 非 ASCII 字符（如 `↔`） | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` |

---

## 9. 环境变量速查

| 变量 | 作用 |
|---|---|
| `XDG_DATA_HOME/XDG_CONFIG_HOME/XDG_STATE_HOME/XDG_CACHE_HOME` | 隔离 home（启动前设） |
| `OPENCODE_CONFIG_DIR` | 精确覆盖 config 目录 |
| `OPENCODE_CLIENT=desktop` | 注册 question 工具 |
| `OPENCODE_SERVER_PASSWORD/OPENCODE_SERVER_USERNAME` | 内核 HTTP Basic 认证（附 TUI 共用） |
| `OPENCODE_DISABLE_AUTOUPDATE=1` | 嵌入式禁自更新 |
| `OPENCODE_CONFIG_CONTENT` | 最高优先级注入（可下发 provider/model 策略，不落盘） |
| `OPENCODE_TEST_HOME`（不设） | 保留用户级 skills |
| 宿主自定义：`PCL_DRIVER` | `host`（默认，走宿主自身流程）/ `opencode`（GUI 动作改由 opencode 驱动） |
| `PCL_KERNEL_AUTOSTART / PCL_KERNEL_TUI` | 是否随 GUI 起内核 / 是否弹 TUI |
| `PCL_SKIP_KERNEL` | 打包时是否排除内核二进制 |

---

## 10. 最小骨架（伪代码）

```python
# 1) 起内核 + 注册 MCP + 绑会话
client = KernelClient(exe=<opencode.exe>)
client.ensure_running()                                   # 隔离 env 已在 kernel_env() 里设好
url = mcp_server.serve_http_in_thread()["url"]            # 方向 A：宿主 MCP 端点
set_mcp_server("your-workbench", url=url, timeout_ms=600000)
sid = client.create_session(title="project")["id"]
client.spawn_tui(session_id=sid, via_powershell=False)    # 一个进程=一个终端

# 2) 投递 + 回灌（后台线程）
driver = KernelDriver(client)
driver.run_turn(sid, "读手稿→跑信号→审阅→写回 Word",
                on_event=lambda ev: {
                    "question": lambda: gui.ask(ev["data"]),      # GUI 就地答
                    "permission": lambda: client.reply_permission(ev["data"]["id"], "once"),
                    "tool": lambda: gui.log(f"[tool] {ev['text']}"),
                    "text": lambda: gui.append(ev["text"]),
                }[ev["kind"]]() if ev["kind"] in ("question","permission","tool","text") else None)

# 3) 切项目：复用同一 TUI 内部切会话并提示
client.tui_select_session(new_sid); client.tui_show_toast(f"已切换课题：{name}")
```

---

## 11. 已知限制 / 待办

- 只构建了 windowed onedir；console 子系统变体与 onefile-with-kernel 未单独构建。
- GUI 既有面板为 offscreen 验证 + 一次真机截图；未做人工逐按钮点验全量。
- 十阶段严格协议保真依赖 `kernel_assets/agent/omics-design.md` 的 prompt；如需更强约束可再收敛。
- V2 `/api/session` 在本构建对第三方 provider 不可用；若未来版本修好，可平滑切回 V2 面（事件/模型更规整）。
- `noReply` 消息进入会话历史：若做“GUI 操作全量注入 agent”需加白名单/去重，避免上下文膨胀。

---

*本文随实现同步维护；新增/修正端点或行为请更新对应小节与 `_test_*` 自检。*
