# 把 opencode 内核嵌入 PCL-Radiomics：实现方案

> **宿主**：`I:\Completion-of-the-omics-research-design-plan-main\Completion-of-the-omics-research-design-plan-main`（Python 3.11 / PySide6+PyCt6 / 版本 1.3.0）
> **内核**：`I:\Completion-of-the-omics-research-design-plan-main\opencode-dev\opencode-dev`（TypeScript / Bun / Effect，版本 1.18.35）
>
> 本文所有 `路径:行号` 锚点均已对照当前工作树核实。方案本身未改动任何文件。

---

## 0. 结论先行

1. **Python 进程内直接嵌入 opencode 内核是不可能的** —— 它是 Bun/TypeScript 程序，运行时不同。唯一可行的"内核级联动"是：**由宿主托管一个 opencode 子进程，通过官方 HTTP 契约通信**（见 §2）。这仍然满足"内核联动"的全部实质：同一个 session 引擎、同一套 skill 解析、同一份 API key 存储格式、同一个权限引擎。
2. **"嵌入"其实是方向相反的两件事，必须拆开**（§2.1）：
   - **方向 A**：内核调用宿主的领域能力 —— 走 **MCP**，内核是客户端。**这就是「GUI 程序是 opencode 的 MCP 服务」**（已核实：opencode 只做 MCP 客户端，从不做服务端）。
   - **方向 B**：宿主驱动内核（建会话/发消息/看事件/配 skill/配 key）—— 走 **HTTP + SSE**，宿主是客户端。
3. **接入通道选 HTTP sidecar**（`opencode serve`），而不是 ACP —— 因为只有 HTTP 面同时覆盖 session / skill / provider / credential / permission / question 全套管理能力（见 §5 对照表）。
4. **"与 opencode 一致"的正确做法是复用同一套文件格式与语义，而不是硬编码一套平行配置**：直接读写 opencode 的 `opencode.json`、`auth.json`、`SKILL.md`，宿主只做界面，不做第二套真值。
5. **`console=True` 会与 windowed 主 exe 冲突**（Win11 上控制台窗口藏不掉，README 已实测），因此**产出独立变体 `PCLRadiomicsConsole.exe`**，主 exe 保持 windowed（见 §4.2）。
6. **内核的模型必须走 opencode 原生 provider** —— 宿主的 LLM 层完全没有 function/tool calling（`llm_client.py:259` 无 `tools` 参数、`api_server.py:160-166` 无 `tool_calls`），把内核接到宿主上游会让它一个工具都调不了，能力归零（见 §7）。
7. **内核 UI 不必自绘**：用 opencode 自带 Web UI（系统浏览器）+ console 变体里的 TUI 即可，避免重建会话界面与一串自检脚本风险（见 §8.3）。

---

## 1. 现状核实（两侧关键事实）

### 1.1 宿主侧：可插拔程度比预期高

| 事实 | 锚点 |
|---|---|
| 统一 CLI 分派表，加子命令只需一个函数 + 一行注册 | `cli.py:261-263`、`:276-281` |
| `_hide_own_console()` **已经**处理"console 子系统 + GUI 模式藏窗口" | `cli.py:96-118` |
| spec 已有 `PCL_CONSOLE` 开关切换 `console=` | `pclradiomics.spec:29`、`:117`、`:122` |
| spec 说明文字明确记录了 console vs windowed 的设计张力 | `pclradiomics.spec:13-16`、`:28` |
| `win_stdio` 按需接管标准流（管道 → 父控制台 → devnull） | `win_stdio.py:44-61`、`:63+` |
| 可写路径统一由 `app_paths` 解析，冻结后行为一致 | `app_paths.py:39-84` |
| 已有用户级私有配置目录 + `secret.json`(0600) 纪律 | `app_paths.py:87-107`、`llm_client.py:152-172` |
| MCP 用 FastMCP，`@mcp.tool()` 装饰器注册，schema 由类型注解+docstring 派生 | `mcp_server.py:45-50`、`:85`、`:583` |
| MCP 已有 21 个工具，`--list-tools` 可零成本枚举验证 | `mcp_server.py:612-617` |
| 已有 OpenAI 兼容推理服务，可反向作为内核上游 | `api_server.py:101-149` |
| LLM 配置已实现"非密钥进配置文件 / 密钥进 0600 文件"的分离 | `llm_client.py:119-172` |
| 流式回调契约稳定：`on_delta(piece, kind)`，`kind ∈ {content, reasoning, note}` | `llm_client.py:259`、`:371-377` |
| GUI 已有 5 视图栈、可复用的设置对话框模板、Qt-free 后端先例 | `design_studio.py:2538-2544`、`:2151-2234`、`manuscript_review/mr_engine.py:203-207` |
| GUI 已注册 `_busy()` 单槽守卫，假定"一次性调用" | `design_studio.py:3455-3456`、`:4216-4217` |
| **取消机制是弱项**：无停止按钮，只在关窗时 `terminate()` | `design_studio.py:3709-3721` |
| 无中央 feature flag；三套 server 各持独立 `STATE` | `mcp_server.py:316`、`api_server.py:46`、`web_server.py:94` |

### 1.2 opencode 侧：可直接使用的嵌入面

| 能力 | 事实 | 锚点 |
|---|---|---|
| 独立二进制 | `Bun.build({compile})` → `dist/opencode-windows-x64/bin/opencode.exe`；发布为 `opencode-windows-x64.zip`，另有 `-baseline`（非 AVX2）变体 | `packages/opencode/script/build.ts:163-202`、`.github/workflows/publish.yml:277-290` |
| HTTP 服务 | `opencode serve`，`OPENCODE_SERVER_PASSWORD` 保护 | `packages/opencode/src/cli/cmd/serve.ts:6-23` |
| 健康检查 | `GET /api/health` → `{healthy:true}`；`GET /global/health` → `{healthy,version}` | `packages/protocol/src/groups/health.ts:4-6`、`httpapi/groups/global.ts:66-69` |
| ACP | `opencode acp`：stdio 上 ndjson，内建 HTTP server 再桥接 | `packages/opencode/src/cli/cmd/acp.ts:9-73` |
| 一次性运行 | `opencode run "msg" --format json --session <id> --agent <a> --model <p/m> --attach <url> --auto` | `packages/opencode/src/cli/cmd/run.ts:127-261` |
| 会话管理 API | create / list / get / active / prompt / compact / wait / interrupt / history / events(SSE) / context / switchAgent / switchModel / revert.* | `packages/protocol/src/groups/session.ts:109-360` |
| 权限闭环 API | request.list / saved.list / saved.remove / create / list / get / reply | `packages/protocol/src/groups/permission.ts:23-136` |
| 问题闭环 API | request.list / list / reply / reject | `packages/protocol/src/groups/question.ts:20-81` |
| **API key / 凭据** | `integration.connect.key` / `connect.oauth` / attempt.* + `credential.update` / `credential.remove` | `packages/protocol/src/groups/integration.ts:12-114`、`groups/credential.ts:8-24` |
| 凭据文件格式 | `<data>/auth.json`：`{providerID: {type:"api",key} \| {type:"oauth",...} \| {type:"wellknown",...}}`，写入 `0600`；环境变量 `OPENCODE_AUTH_CONTENT` 可整体注入 | `packages/opencode/src/auth/index.ts:10-95` |
| **skill 只读** | `/api/skill` 只有 list；**写必须落到 `SKILL.md` 文件** | `packages/protocol/src/groups/skill.ts:9` |
| **agent 只读** | `/api/agent` 只有 list；写走 `opencode agent create`（可完全非交互）或 Markdown 文件 | `packages/protocol/src/groups/agent.ts:8`、`packages/opencode/src/cli/cmd/agent.ts:33-232` |
| provider / model | `/api/provider`、`/api/provider/:id`、`/api/model`；CLI `providers list\|login\|logout` | `groups/provider.ts:10-25`、`groups/model.ts:10`、`packages/opencode/src/cli/cmd/providers.ts:249-501` |
| 配置隔离环境变量 | `OPENCODE_CONFIG_DIR` / `OPENCODE_CONFIG` / `OPENCODE_CONFIG_CONTENT` / `XDG_DATA_HOME` / `XDG_STATE_HOME` / `OPENCODE_DB` / `OPENCODE_CLIENT` / `OPENCODE_DISABLE_AUTOUPDATE` / `OPENCODE_PURE` / `OPENCODE_PERMISSION` / `OPENCODE_AUTH_CONTENT` | `packages/core/src/flag/flag.ts:14-69`、`packages/core/src/global.ts:40-57`、`packages/opencode/src/config/config.ts:415-489` |
| 配置合并顺序 | global → 项目 `opencode.json(c)` → `.opencode/` 目录 → `OPENCODE_CONFIG_CONTENT`（最后、最高优先） | `packages/opencode/src/config/config.ts:413-489`、`packages/core/src/config.ts:186-203` |
| **本仓库自带的嵌入先例** | Electron 用 `utilityProcess` fork sidecar，sidecar `import("virtual:opencode-server")` 调 `Server.listen(...)`，Basic 认证 + 轮询 `/api/health` + 60s 启动超时 | `packages/desktop/src/main/server.ts:57-184`、`src/main/sidecar.ts:51-71` |
| 该先例用的环境变量 | `OPENCODE_CLIENT=desktop`、`XDG_STATE_HOME=<userDataPath>` | `packages/desktop/src/main/server.ts:44-55`、`sidecar.ts:83-89` |
| **客户端身份影响工具门控** | `question` 工具仅当 `client ∈ {app,cli,desktop}` 时注册；`plan_exit` 仅当 `client === "cli"` | `packages/opencode/src/tool/registry.ts:207`、`:248` |
| opencode **不提供** MCP 服务端 | `opencode mcp` 是 MCP **客户端**管理器（add/list/auth/logout/debug），没有 serve | `packages/opencode/src/cli/cmd/mcp.ts:96-104` |

> ⚠️ **平台约束**：Bun 编译产物要求 Windows 10+。宿主的 Win7 变体（Python 3.8 + 无 Qt）**必须保持无内核**。

---

## 2. 目标架构

### 2.1 先把架构关系理清：四个角色、两个方向、两种协议

"把 opencode 嵌入宿主"这句话里其实藏着**两件方向相反的事**，必须拆开，否则会设计错：

| # | 关系 | 方向 | 协议 | 谁主动 | 技术含义 |
|---|---|---|---|---|---|
| **A** | 内核调用宿主的领域能力 | 内核 → 宿主 | **MCP** | 内核（客户端） | 宿主是**内核的 MCP 服务** |
| **B** | 宿主驱动内核（建会话/发消息/看事件/配 skill/配 key） | 宿主 → 内核 | **HTTP + SSE**（`/api/*`） | 宿主（客户端） | 宿主是**内核的宿主进程与控制面** |
| **C** | 外部 agent 调用宿主的领域能力 | 外部 → 宿主 | **MCP** | 外部 agent | 宿主仍是对外 MCP 服务（现状不变） |
| **D** | 宿主托管内核进程 | — | 进程管理 | 宿主 | "嵌入"的技术含义 |

**关键事实（已核实）**：**opencode 只是 MCP 客户端，永远不做 MCP 服务端。**
`opencode mcp` 的全部子命令是 `add` / `list` / `auth` / `logout` / `debug`（`packages/opencode/src/cli/cmd/mcp.ts:96-104`），没有任何 serve 形态。

所以「**GUI 程序是 opencode 的 MCP 服务**」这个判断是**正确**的，而且它正是上表的**方向 A**：宿主提供工具，内核作为 agent 来调用。这也与宿主 README 里"注册到 opencode 的 mcp 段"的既有设想一致。

### 2.2 架构图（修正版）

```
┌────────────── PCLRadiomics.exe（GUI 进程，常驻）──────────────┐
│                                                              │
│  ┌─ GUI 窗口 (PySide6 design_studio) ──────┐                 │
│  │  · 触发按钮：点"开始分析" → 建内核会话    │                 │
│  │  · 内核设置入口（配置面）                 │                 │
│  │  · 不新建会话 transcript 视图（见 §8.3）   │                 │
│  └──────────────────────────────────────────┘                 │
│                                                              │
│  ┌─ MCP 服务端 (FastMCP, streamable-http) ──┐                 │
│  │  127.0.0.1:<port>/mcp                    │                 │
│  │  21 个领域工具：design_* / manuscript_*   │                 │
│  │  / project_* / stat / export_*            │                 │
│  └──────────────────▲───────────────────────┘                 │
│                     │ 方向 A：MCP（内核来调）                  │
│  ┌─ kernel_client.py (Qt-free) ─────────────┐                 │
│  │  · 内核进程生命周期（懒启动/健康/停止/清理）│                 │
│  │  · HTTP + SSE 控制面                      │                 │
│  │  · 权限/提问回复通道                      │                 │
│  └──────────────────┬───────────────────────┘                 │
│  ┌─ kernel_config.py ───────────────────────┐                 │
│  │  隔离 home · opencode.json · auth.json    │                 │
│  │  · SKILL.md 管理 · 从系统 opencode 单向导入│                 │
│  └──────────────────────────────────────────┘                 │
└───────────────────────┬──────────────────────────────────────┘
                        │ 方向 D：subprocess
                        │ 方向 B：HTTP + SSE（127.0.0.1:<随机端口>, Basic）
                        ▼
        opencode.exe serve --hostname 127.0.0.1 --port <随机>
                        │
        ┌───────────────┴────────────────────────────┐
        │        opencode 内核（Bun，agent）          │
        │  session / runner · 18 内置工具             │
        │  permission engine · provider / LLM        │
        │  MCP client ───────────────────────────────┼──► 方向 A：
        └────────────────────────────────────────────┘   调宿主的
                                                          21 个领域工具
        ┌─ 内核 UI（见 §8.3）─────────────────────────┐
        │  首选：opencode 自带 Web UI（系统浏览器打开）  │
        │  辅选：console 变体里的 opencode TUI         │
        └────────────────────────────────────────────┘
```

**为什么这个架构值得做**：内核作为 agent 拿到 21 个组学领域工具后，可以做"多步自主任务"——例如自动读手稿 → 跑确定性信号 → 调 LLM 分层审阅 → 写回 Word，中间不需要人手点每一步。这是宿主现在做不到的（现有流程是 UI 上一步步点）。

### 2.3 方向 A 的配置形态（opencode 侧）

⚠️ **opencode 的配置键是 `mcp`，不是 `mcpServers`**（`mcpServers` 是 Claude Desktop 的键）。宿主 README 那句"opencode 的 `mcpServers` 段"是不准确的。

schema 见 `packages/core/src/v1/config/mcp.ts:6-63`，两种连接方式：

```jsonc
// <KERNEL_HOME>/config/opencode/opencode.json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "radiomics-workbench": {
      "type": "remote",                                    // ← 推荐：指向常驻 GUI 进程
      "url": "http://127.0.0.1:<宿主MCP端口>/mcp",
      "enabled": true,
      "timeout": 600000                                    // ← 必须调大，见下
    }
  }
}
```

| 连接方式 | 写法 | 评价 |
|---|---|---|
| **`type: "remote"`（推荐）** | 指向**已在运行**的 GUI 进程的 MCP HTTP 端点 | 不额外起进程；避开 stdio 在 windowed 构建下的接管问题（`win_stdio.py:44-61`）；生命周期最干净 |
| `type: "local"` | `command: ["<app_home>/PCLRadiomics.exe", "mcp"]` | 会**再起一个** PCLRadiomics.exe。GUI 已在跑，等于双实例；且 stdio 依赖 `win_stdio` 管道接管，在"打包进主 exe + console 子系统"的新组合下需重测 |

这带来一个**新增需求**：GUI 进程必须在跑界面的**同时**暴露 MCP HTTP 端点。现状是 `gui` / `mcp` 两种模式互斥（`cli.py:261-263`），需要把 FastMCP 的 streamable-http 挂到 GUI 进程的后台线程上。

⚠️ **`timeout` 必须显式调大**：MCP 默认 `5000` ms（`mcp.ts:21`、`:57`），而宿主的 `manuscript_review`、`design_finalize` 等工具要跑几分钟。**不改这个值，内核调用这些工具会直接超时失败。**

---

## 3. 通道选型（决策 D1）

| 维度 | **HTTP sidecar**（推荐） | ACP stdio | `run` 一次性 |
|---|---|---|---|
| 能力覆盖 | 全套：session/skill/provider/credential/permission/question/pty | 仅 session 生命周期 + prompt + cancel + setMode/Model | 单轮 prompt |
| 配置管理 | ✅ HTTP + 文件双通道 | ❌ 需另走 CLI/文件 | ❌ |
| 权限交互 | ✅ HTTP 拉取 + reply | ✅ 协议内请求/响应 | ⚠️ 只能 `--auto` 放行 |
| 常驻 session | ✅ 天然 | ✅ | ❌ 每次新进程 |
| 事件流 | ✅ `/api/event` SSE + `/api/session/:id/event` | ✅ ndjson 流 | ⚠️ `--format json` 逐行 |
| 宿主实现成本 | 低（`urllib` + SSE 解析，宿主已有同款代码） | 中高（无 Python 官方 SDK，需自实现 ndjson JSON-RPC） | 低 |
| 端口/认证 | 需管理端口 + 密码 | 无 | 需管理端口 |
| 多客户端共享 | ✅ 可被 GUI / MCP / console 同时用 | ❌ 独占 stdio | ❌ |

**结论**：HTTP sidecar 作为唯一内核通道。ACP 留作后续"编辑器集成"选项，`run` 保留作为降级/脚本化入口。

---

## 4. console 的真实含义与构建策略（决策 D2）

### 4.1 现状

- `pclradiomics.spec:29` 已有 `CONSOLE = os.environ.get("PCL_CONSOLE", ...)`，`set PCL_CONSOLE=1` 即切成 `console=True`（`:117`/`:122`）。
- `cli.py:96-118` 的 `_hide_own_console()` 专为此设计：**仅当本进程独占控制台**（`GetConsoleProcessList` 返回 1）时才 `ShowWindow(hwnd, 0)`。
- README 记录实测结论：**Win11 上控制台由 Windows Terminal 托管（属于别的进程），`ShowWindow` 藏不掉，console 构建在 GUI 模式下会留下一个终端窗口**。这正是 v1.3.0 把默认切回 windowed、改用 `win_stdio` 按需接管的原因（`pclradiomics.spec:28`）。

### 4.2 决策已定：编译成 console 子系统

> ✅ **D2 = 「编译成 console 子系统」**（已确认）

落地方案：**产出独立变体 `PCLRadiomicsConsole.exe`，不取代现有 windowed 主 exe。**

| 产物 | 子系统 | 角色 |
|---|---|---|
| `PCLRadiomics.exe` | windowed（现状不变） | 双击即用的图形主程序 + MCP/API 服务 |
| `PCLRadiomicsConsole.exe` | **console=True** | 带真实控制台的交付形态：内核配置、会话管理、日志、诊断 |

理由：console 子系统在 Win11 上由 Windows Terminal 托管，`ShowWindow` 藏不掉（README 已实测，`cli.py:96-118` 的 `_hide_own_console()` 对 WT 托管窗口无效）。若把它做成**唯一**产物，双击 GUI 场景就会永远多一个终端窗口——这是确定会发生的回归，而不是风险。

构建方式：复用同一份 spec。`pclradiomics.spec:29` 的 `CONSOLE = os.environ.get("PCL_CONSOLE", ...)` 已经支持，只需新增一个批处理：

```bat
:: 编译_内核版.bat（console 变体）
set PCL_CONSOLE=1
set PCL_APP_NAME=PCLRadiomicsConsole
python -m PyInstaller --noconfirm --clean pclradiomics.spec
```

> ⚠️ 需要新增 `PCL_APP_NAME` 支持（当前 `APP_NAME` 在 `pclradiomics.spec:26` 是硬编码的），否则两个变体会产出同名 exe 并互相覆盖。
>
> **同时仍建议做"console 配置面"**（`cli.py kernel ...` 子命令组）：它是功能，任何构建都能用；而 console 子系统只是交付形态。两者互补，不冲突。

### 4.3 决策已定：打进主 exe —— 但有三个连带后果

> ✅ **D5 = `opencode.exe` 打进主 exe**（已确认）

| 后果 | 说明 | 处理 |
|---|---|---|
| **必须放弃 onefile** | onefile 每次启动要把全部内容解包到 `%TEMP%`；再塞进一个约 100 MB 级的 opencode.exe，会让启动从"CLI 2.5–4.4s / GUI ~10s"进一步恶化，且每次 MCP 客户端拉起都重解包 | **内核版只出 onedir**（`dist\PCLRadiomics\`）。`编译单文件版.bat` 不用于内核版 |
| **体积必然增长** | 现 onedir 148 MB；加上 opencode.exe 后需实测 | 由 **P0 实测**给出数字；若不可接受再回退到"首次使用时获取"（本决策可逆） |
| **spec 需收集二进制** | PyInstaller 默认不收集外部 `.exe` | 加入 `binaries`（会被 strip/依赖分析）**或** `datas`（原样拷贝）。对外部预编译二进制建议用 `datas` + 运行时按 `resource_path` 定位 |
| **Win7 变体不必处理** | 你已确认不需要兼容 Win7 变体 | 见 §11：D6 已定，§10 风险 2 与相关的排除工作一并取消 |

---

## 5. console 配置面：session / skill / apikey 的具体实现

> 目标：**与 opencode 完全一致**。做法是"同一套文件 + 同一套语义"，宿主只做界面。凡 HTTP 有写接口的走 HTTP；没有的（skill/agent）落到 opencode 自己的文件；密钥一律 0600。

| 配置域 | 读取 | 写入 | 一致性保证 |
|---|---|---|---|
| **session** | `GET /api/session`、`/api/session/:id`、`/api/session/:id/history`、`/api/session/:id/context` | `POST /api/session`（建）、`session.prompt`、`session.interrupt`、`session.compact`、`session.switchAgent/Model`、`session.revert.*`；删除走 `opencode session delete <id>` | 全程走内核官方 API，无本地副本 |
| **skill** | `GET /api/skill`（内核已解析后的清单） | **写 `<kernel-home>/.opencode/skill/<name>/SKILL.md`**；同时支持从用户 `~/.claude/skills`、`~/.agents/skills` 导入/镜像 | 复用 opencode 的 `SKILL.md` + YAML frontmatter（`name` 必填、`description` 可选）格式，见 `packages/opencode/src/skill/index.ts:23-25`、`:53-59`；内核重启或重载后 `GET /api/skill` 立即可见即为验收 |
| **apikey / provider 凭据** | `GET /api/provider`、`/api/provider/:id`、`/api/model`；已存凭据读 `<data>/auth.json`（尊重 `OPENCODE_AUTH_CONTENT` 覆盖） | 首选直接读写 `auth.json`：`{providerID: {type:"api", key, metadata?}}`，`chmod 0600`，并复刻 `Auth.set` 的尾斜杠归一化语义 | 与 `packages/opencode/src/auth/index.ts:73-89` 逐字段对齐；比 `providers login` 更可靠（后者是交互式流程） |
| **OAuth / 集成型凭据** | `/api/integration`、`/api/integration/:id`、`/api/integration/attempt/:id` | `integration.connect.key`、`integration.connect.oauth`、`attempt.complete/cancel`、`credential.update/remove` | 走 HTTP，内核自己落盘 |
| **agent** | `GET /api/agent` | `opencode agent create --path … --description … --mode … --permissions … --model …`（**可完全非交互**，成功时把文件路径打到 stdout），或直接写 `{agent,agents}/*.md` | 与 `packages/opencode/src/cli/cmd/agent.ts:33-232` 同源 |
| **model / 内核自身 LLM 走向** | `/api/model`、`GET /api/provider` | 写 `<kernel-home>/opencode.json` 的 `model` / `provider` 段 | 与 `packages/opencode/src/config/config.ts:272-274` 的 global config 加载路径一致 |
| **权限与提问（运行期）** | `GET /api/permission/request`、`GET /api/session/:id/permission`、`GET /api/question/request` | `POST /api/session/:id/permission/:rid/reply`（`once\|always\|reject` + 可选 message）、`question/:rid/reply\|reject` | 与内核引擎同一套 last-match-wins 规则，不做第二套判断 |

**关键约束**：内核会**阻塞等待**权限/提问回复。宿主如果不实现回复通道，会话会挂死。所以 `kernel_client.py` 必须常驻一个 SSE 订阅，把这两类请求路由到 GUI 弹窗 / MCP 工具 / console 交互，并带超时兜底。

---

## 6. 内核 home 与隔离（决策 D3）

opencode 的路径全部由 XDG + 专用环境变量决定（`packages/core/src/global.ts:9-45`）：

```
data   = $XDG_DATA_HOME/opencode      → auth.json、log、repos、sqlite
config = $XDG_CONFIG_HOME/opencode    → opencode.json、agent/、skill/
state  = $XDG_STATE_HOME/opencode
cache  = $XDG_CACHE_HOME/opencode
tmp    = $TMPDIR/opencode
```

### 6.1 ⚠️ 路径事实修正（已核实依赖源码）

`xdg-basedir@5.1.0` **不含任何 Windows 特判**，实现就是三条 `process.env.X || path.join(os.homedir(), ...)`：

```js
export const xdgData   = env.XDG_DATA_HOME   || path.join(homeDirectory, '.local', 'share');
export const xdgConfig = env.XDG_CONFIG_HOME || path.join(homeDirectory, '.config');
export const xdgState  = env.XDG_STATE_HOME  || path.join(homeDirectory, '.local', 'state');
export const xdgCache  = env.XDG_CACHE_HOME  || path.join(homeDirectory, '.cache');
```

因此在 Windows 上，opencode 的默认目录是 **`C:\Users\<用户>\.local\share\opencode`** 这一类，**不是** `%LOCALAPPDATA%\opencode`（早前版本的本方案文档此处写错，已修正）。

**好消息**：四个目录**全部**可被 `XDG_*` 环境变量覆盖，所以隔离模式成立。另外 `Global.Path.config` 还会被 `OPENCODE_CONFIG_DIR` 直接覆盖（`global.ts:40-57`：`config: Flag.OPENCODE_CONFIG_DIR ?? Path.config`），这是比 `XDG_CONFIG_HOME` 更精确的杠杆。

**约束**：`xdg-basedir` 在**模块加载时**求值（`const {env} = process;` 后立即计算）。所以这些变量**必须在 opencode 进程启动前设好**，运行中改不了——切换隔离/共享模式**必须重启内核**。

### 6.2 决策已定：隔离模式

> ✅ **D3 = 隔离（默认，便携、不污染系统 opencode）**（已确认）

```python
KERNEL_HOME = data_path("opencode")          # 对齐 app_paths 的绿色便携理念
env = {
  "XDG_DATA_HOME":   f"{KERNEL_HOME}/data",
  "XDG_CONFIG_HOME": f"{KERNEL_HOME}/config",     # 与 opencode 默认层级保持一致
  "XDG_STATE_HOME":  f"{KERNEL_HOME}/state",
  "XDG_CACHE_HOME":  f"{KERNEL_HOME}/cache",
  # "OPENCODE_CONFIG_DIR": f"{KERNEL_HOME}/config/opencode",  # 可选，更精确的 config 覆盖
}
```

效果：`auth.json`、会话 sqlite、日志、repos 全部落在 `app_home/opencode/` 下，随程序便携，且**绝不写入**用户真实的 `~/.local/share/opencode`。

### 6.3 隔离带来的三个后果（必须一并处理）

**① 用户已有的 opencode 凭据看不见了 → 需要显式"导入"动作。**

隔离后 `<KERNEL_HOME>/data/opencode/auth.json` 是空的，用户在系统 opencode 里配好的 key 不会被继承。这**不违背**"与 opencode 一致"（格式与语义仍然一致），但会造成"我明明配过 key 却要重配"的困惑。

建议在 console 里提供一个**单向导入**动作：`kernel auth import-from-system` —— 读 `~/.local/share/opencode/auth.json`（或 `OPENCODE_AUTH_CONTENT`），按同一 schema 合并进隔离 home。只读导出、不建立任何持续共享，因此不破坏隔离性。

**② `home` 要不要一起隔离？这是一个独立子决策。**

外部 skill 目录用的是 `Global.Path.home`，而 `home = process.env.OPENCODE_TEST_HOME ?? os.homedir()`（`global.ts:19`；调用点 `skill/index.ts:191`）：

| 选择 | 效果 | 评价 |
|---|---|---|
| **不设 `OPENCODE_TEST_HOME`（✅ 已定）** | 内核仍能读用户已有的 `~/.claude/skills/**/SKILL.md` 与 `~/.agents/skills/**/SKILL.md` | 隔离的既定理由是"便携、不污染"，而**读取不构成污染**；同时这正是 opencode 的原生行为，更符合"与 opencode 一致" |
| ~~设 `OPENCODE_TEST_HOME`（净室）~~ | ~~完全净室，看不到任何用户级 skill~~ | 已排除 |

副作用（两种选择都有）：`config/paths.ts:36-37` 的配置向上发现以 `Global.Path.home` 为 **start 和 stop**，所以内核会沿项目路径向上发现 `.opencode` 等配置目录直至 home。由于我们已经用 `OPENCODE_CONFIG_DIR` 把全局配置钉到内核 home，这一般是良性的，但需在 P0 实测确认不会误读用户其它项目的配置。

**③ 隔离 ⇒ 内核的 LLM 上游选择更依赖 D4。** 因为系统 opencode 的 key 不可见，D4 选 (b)「复用宿主 `api_server`」的收益变大了——宿主自己的凭据链（`secret.json` → `LLM_API_KEY` → `DEEPSEEK_API_KEY` → `~/.dsh/.credentials.yaml`）本来就是隔离体系内的一份真值，不需要再配第二遍。

### 6.4 固定注入的环境变量

```python
env = {
  "OPENCODE_SERVER_USERNAME": "opencode",
  "OPENCODE_SERVER_PASSWORD": <每实例随机>,          # 见 auth.ts:17-20
  "OPENCODE_CLIENT": "desktop",                       # 关键：让 question 工具注册（registry.ts:207）
  "OPENCODE_DISABLE_AUTOUPDATE": "1",                 # 嵌入式必须禁自更新
  "OPENCODE_DISABLE_MODELS_FETCH": "1",               # 可选：离线/内网
  # "OPENCODE_PURE": "1",                             # 可选：禁外部插件，减小风险面
  # "OPENCODE_DB": f"{KERNEL_HOME}/kernel.db",        # 可选：显式指定会话库
}
```

> 注意 `OPENCODE_CONFIG_CONTENT` 优先级最高（`packages/opencode/src/config/config.ts:482-489`），宿主要下发的策略（permission/provider）可以用它注入，**无需落盘**。

---

## 7. 内核的 LLM 走向（决策 D4）—— 已由硬约束确定

> 🔧 **结论：只能选 (a) opencode 原生 provider。**
> 本文档早前版本"建议默认 (b)"是**错误的**，此处更正。

### 7.1 为什么 (b) 结构性不可行

宿主的整个 LLM 层**完全不支持 function / tool calling**，它是纯文本对话管线：

| 证据 | 位置 |
|---|---|
| `chat()` 的签名里**没有** `tools` 参数 | `llm_client.py:259`：`chat(messages, stream=False, on_delta=None, temperature=None, max_tokens=None, reason=False)` |
| 全文件搜不到 `tools` / `tool_calls` / `function` 任何一处 | `llm_client.py`（grep 仅命中 `_request` / `chat` / `_stream_once`） |
| `api_server` 读 body 时只取 `messages` / `stream` / `model` / `temperature` / `max_tokens`，**从不读 `body["tools"]`** | `api_server.py:132-138` |
| 非流式上游调用只传 messages/temperature/max_tokens | `api_server.py:152-158` |
| 响应体只拼 `message: {role, content}`，**没有 `tool_calls` 字段** | `api_server.py:160-166` |
| 流式路径自建 payload，同样不含 tools | `api_server.py:168-174` |

**后果**：opencode 是 **agent**，它的核心能力就是原生工具调用。若把它接到宿主 `api_server`：

- 请求里的 `tools` 数组被静默丢弃 → 内核**一个工具都拿不到**（18 个内置工具 + 21 个 MCP 工具全部失效）
- 响应里没有 `tool_calls` → 内核**无法发起任何工具调用**
- 结果：内核退化成"只会聊天的文本框"，"内核级联动"彻底落空

这不是"多一跳"或"继承流式缺陷"的性能问题，而是**能力归零**的架构问题。所以 (b) 不可选。

### 7.2 最终方案：(a) opencode 原生 provider

| 项 | 做法 |
|---|---|
| 凭据落点 | 隔离 home 的 `<KERNEL_HOME>/data/opencode/auth.json`，`{providerID: {type:"api", key}}`，`0600` |
| 配置方式 | console 里配；或 `kernel auth import-from-system` 从系统 opencode 单向导入（§6.3①） |
| 模型选择 | opencode 原生：26 个 SDK、OAuth 流程、模型变体（reasoning effort 等）全部可用 |
| 收益 | **原生工具调用保真**——这是 agent 能干活的前提 |

### 7.3 那"复用宿主模型"还有没有意义？有，但走工具而不是走上游

宿主已经有 `llm_chat` 这个 MCP 工具（`mcp_server.py:583-596`）。内核若需要调用宿主背后的模型（例如为了复用 `~/.dsh/.credentials.yaml` 的 DeepSeek 凭据），**正确做法是把它当工具调用**，而不是把它当 provider 上游。

| 维度 | 作为 provider 上游（❌ 不可行） | 作为 MCP 工具（✅ 可行） |
|---|---|---|
| 工具调用 | 被丢弃，能力归零 | 不影响，内核自己的工具链完好 |
| 凭据复用 | 可以 | 可以（走宿主既有凭据链） |
| 语义 | 内核"变成"那个模型 | 内核"调用"那个模型 —— 语义正确 |

> ✅ **D4 = (a) opencode 原生 provider**；需要宿主模型时通过 `llm_chat` 工具调用。

---

## 8. 文件改动清单

### 新增

| 文件 | 职责 |
|---|---|
| `kernel_client.py` | 内核客户端（Qt-free）：进程生命周期、HTTP、SSE 订阅与事件归一化、权限/提问回调 |
| `kernel_config.py` | 内核 home 解析（**隔离**）、`opencode.json` 生成/合并（含 `mcp` 段与调大的 `timeout`）、`auth.json` 读写(0600)、`SKILL.md` 安装/列举/删除、从系统 opencode 单向导入凭据 |
| `kernel_cli.py` | `cli.py kernel` 子命令实现：`status/start/stop/logs/ui/session/skill/auth/model/config` |
| `_test_kernel.py` | 自检：对齐 `_test_merged.py` 风格，覆盖 home 隔离、auth.json 往返、skill 可见性、session 全链路、权限回复、MCP 工具可被内核发现 |
| `pclradiomics_console.spec` | console=True 变体（也可继续用 `PCL_CONSOLE=1` 复用主 spec） |
| `编译_内核版.bat` | 校验 `opencode.exe` + 构建含内核的产物（**onedir**，见 §4.3） |

### 改动

| 文件 | 改动 | 风险 |
|---|---|---|
| `cli.py:261-263` | `COMMANDS` 增加 `"kernel": cmd_kernel` | 极低 |
| `app_paths.py` | 新增 `kernel_home()`，沿用 `app_home()` 的冻结规则；确保 `opencode.exe` 可被定位（`resource_path` / exe 同级） | 低 |
| `mcp_server.py` | **（方向 A 的关键）** 把 FastMCP 的 streamable-http 端点抽成可在 GUI 进程内后台线程启动，使 GUI 与 MCP 同时可用；`timeout` 语义对齐内核侧配置 | **中高**（现状 `gui`/`mcp` 互斥，`cli.py:261-263`） |
| `api_server.py` / `web_server.py` | 可选：暴露 `GET /kernel/status` | 低 |
| `pclradiomics.spec` | 收集 `opencode.exe`；`HIDDEN` 增加 `kernel_*`；前置校验增加内核模块探测（仿 `:74-83`）；**`APP_NAME`(`:26`) 改为读 `PCL_APP_NAME`**（§4.2 双变体必需） | 中 |
| ~~`design_studio.py` 第 6 视图~~ | **已取消**（见 §8.3）：不再新建会话 transcript 视图，`design_studio.py` 只需加一个"内核设置"入口与触发按钮 | **低**（原为高风险，现已消解） |
| ~~`_check_overlap.py` / `_check_theme.py` / `_probe_views.py` 注册新视图~~ | **已取消**：无新视图即无需注册 | 无 |

### 8.3 内核 UI：PowerShell 窗口里的 opencode TUI（已定）

> ✅ **D7 = 内核 UI 用 opencode 的 TUI，跑在 PowerShell 窗口里。**

因为架构关系是「宿主 = MCP 工具提供方，内核 = agent 执行方」（§2.1），"内核 UI"本质是**观察/交互 agent 会话的终端界面**。选 TUI 相比自绘 PyQt 视图的优势：零新增 PyQt 代码、完整会话/工具调用/diff/权限交互、且与已定的 **console 子系统**一致。

#### 关键：必须 `attach` 到我们的隔离实例，而不是裸跑 `opencode`

裸跑 `opencode`（即 `$0 [project]` 命令 `start opencode tui`，`cli/cmd/tui.ts:72-74`）会**自己起一个 server**。那会同时出现两个 server 争用同一个隔离 sqlite。正确做法是用 **`opencode attach`**：

```
opencode attach <url> [--dir <path>] [-c | -s <sessionID>] [--mini]
```

`attach` 的能力（`cli/cmd/attach.ts:7-61`）：

| 选项 | 作用 |
|---|---|
| `<url>`（必填） | 要挂载的 server，如 `http://127.0.0.1:<port>` |
| `-p, --password` | Basic 认证密码，**默认取 `OPENCODE_SERVER_PASSWORD`** |
| `-u, --username` | 默认 `OPENCODE_SERVER_USERNAME` 或 `opencode` |
| `--dir` | 在哪个目录下运行（决定 workspace/项目上下文） |
| `-c / --continue`、`-s, --session`、`--fork` | 续接或分叉历史会话 |
| `--mini` | 极简交互界面 |

它会先调 `validateSession({url, sessionID, directory, headers})` 验证连通性，失败就报错退出（`attach.ts:117-128`）——**这对宿主很有用：可以在拉起窗口前先拿到明确的失败原因**。

#### 启动方式（两个必须注意的细节）

```python
subprocess.Popen(
    ["powershell.exe", "-NoExit", "-Command",
     f"& '{opencode_exe}' attach '{url}' --dir '{project_dir}'"],
    env={**kernel_env(), "OPENCODE_SERVER_PASSWORD": password},   # ← 见下
    creationflags=subprocess.CREATE_NEW_CONSOLE,                  # ← 见下
)
```

**① 密码走环境变量，不要走命令行。** `attach` 的 `-p` 描述明确写着"defaults to `OPENCODE_SERVER_PASSWORD`"。把密码写在命令行上会**暴露在进程列表里**（任务管理器、`Get-Process`、窗口标题都可能带出来）。用 `OPENCODE_SERVER_PASSWORD` 传入即可，且与内核 server 端（`auth.ts:17-20`）共用同一个变量名。

**② 必须继承内核的隔离环境。** `attach` 会读本地 `TuiConfig.get()`（`attach.ts:115`）。若 TUI 进程没有继承 `XDG_*` / `OPENCODE_CONFIG_DIR`，它读到的就是**用户真实 home 的配置**，与隔离实例不一致。因此 `kernel_client` 要暴露一个 `kernel_env()`，**server 进程与 TUI 进程共用同一份环境**。

**③ 需要新控制台。** TUI 要真实终端；用 `CREATE_NEW_CONSOLE` 让 opencode 拿到自己的 conhost/WT 窗口，而不是复用宿主（console 子系统）的窗口。

> 备选（更省事但少一层 shell）：直接 `Popen([opencode_exe, "attach", url, "--dir", dir], creationflags=CREATE_NEW_CONSOLE)`，得到 conhost 窗口。走 `powershell.exe` 的好处是能落在 Windows Terminal 里，字体/颜色/TUI 渲染更稳，但要多处理一层引号转义。**建议先试直接 spawn，不满足再套 PowerShell。**

> Python GUI 的职责因此收缩为四件：① 内核配置入口 ② 触发按钮（启动内核 / 打开 TUI）③ 领域工具提供方（MCP）④ 内核进程宿主。**不自绘任何会话流。**

> 注：opencode 自带的 **Web UI**（`opencode web`，`cli/cmd/web.ts:31-83`）仍是一个现成备选——若以后想要图形化的会话浏览，直接起服务 + 系统浏览器即可，无需写 PyQt。本决策只是不把它作为主路径。

---

## 9. 分阶段实施

| 阶段 | 内容 | 验收（必须可执行） | 估时 |
|---|---|---|---|
| **P0 可行性验证** | 取得 `opencode.exe`（构建或下载 release），Python `urllib` 打通 `/global/health` → `session.create` → `session.prompt` → 读 `session.events` SSE 拿流式输出 | Python 侧完成一次带流式输出的完整对话；**实测**二进制体积与冷启动到 health 就绪的时间 | 0.5–1 天 |
| **P1 客户端与配置层** | `kernel_client.py` + `kernel_config.py`；**隔离 home**（§6.2）；`auth.json` 往返 + 从系统 opencode 单向导入；`SKILL.md` 管理；生成含 `mcp` 段与调大 `timeout` 的 `opencode.json` | `_test_kernel.py` 全绿；`cli.py kernel status` 输出内核版本/端口/会话数/凭据来源；确认未写入真实 `~/.local/share/opencode` | 1–2 天 |
| **P2 console 配置面 + console 变体** | `kernel_cli.py` 的 session/skill/auth/model/config/**ui** 子命令（`ui` = 拉起 PowerShell + `opencode attach`）；**`PCLRadiomicsConsole.exe` 变体**（spec 增加 `PCL_APP_NAME`，避免同名覆盖） | 在 console 变体里跑通：新增 API key → 列模型 → 建 session → `kernel ui` 打开 TUI 能看到同一批 session → 发消息看输出 → 删除 session；**主 exe 双击仍无终端窗口**；attach 后内核进程数不增加 | 1–2 天 |
| **P3 方向 A 打通（核心）** | **GUI 进程同时暴露 MCP HTTP 端点**（§10 风险 17）；内核 `opencode.json` 注册宿主的 MCP（`type:"remote"` + 调大 `timeout`）；验证内核能发现并调用 21 个领域工具；权限/提问回复通道 | 内核自主完成一次"多步任务"（例：读手稿 → 跑确定性信号 → 调 LLM 审阅 → 报告），全过程工具调用在 TUI 里可见；长任务工具不因 `timeout` 失败 | 2–3 天 |
| **P4 打包与分发** | spec/bat（**仅 onedir**）；体积与启动实测；孤儿进程清理；内核变体与 windowed 主 exe 并存校验 | 冻结产物跑通 P2 + P3 全部验收项；两个 exe 同时存在且互不覆盖 | 1–2 天 |

**总估时约 6–10 个工作日**（不含 P0 结论可能引发的返工）。

> **风险已显著下降**：D7 定为"不自绘内核 UI"后，原 §8 里唯一标"高风险"的 `design_studio.py` 第 6 视图改造（含 7 处 `idx == 4` 硬编码与 3 个自检脚本注册）整体取消；`TranscriptView` 吞吐风险（§10 风险 7）与自检脚本漏检风险（风险 10）一并消失。**新增的主要风险转移到"GUI 进程同时暴露 MCP 端点"这一前置改造**（风险 17）。

---

## 9.5 P0 实测结果（已完成）

> 状态：**P0 通过**。自检 `_test_kernel.py` → `OK=24 / WARN=0 / FAIL=0`（修掉一个测试自身的路径拼接 bug 后）。
> 取二进制方式：**直接下载 v1.18.35 release**（`opencode-windows-x64.zip`），未走本地构建 —— 原因见 §9.6。

### 两个决定性数字

| 指标 | 实测值 | 含义 |
|---|---|---|
| **二进制体积** | **172.3 MB**（zip 59.3 MB） | ⚠️ 见下方"体积后果" |
| **冷启动：spawn → 端口可连** | **0.93 s** | 远好于预期 |
| **冷启动：spawn → health 通过** | **0.94 s** | 懒启动体验完全可接受，GUI 首屏不必预热 |
| 一次完整流式对话（`run --format json`） | 33.4 s（含标题生成、快照、18 工具注册） | 与宿主现有单阶段 30–60 s 同量级 |

### 其它已验证事实

| 项 | 结果 |
|---|---|
| 隔离生效 | 用户真实 `~/.local/share/opencode`（`C:\Users\chris\.local\share\opencode`）**未被触碰**；内核全部状态落在 `<app_home>/opencode/{data,config,state,cache}` |
| 内核自身日志 | `<app_home>/opencode/data/opencode/log/opencode.log`，含版本、provider、工具数、snapshot 路径 |
| 内置工具注册数 | 日志 `init count=18` |
| shell 工具后端 | 自动选用 `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.EXE` |
| HTTP 控制面 | `GET /api/session`（返回 6 个历史会话，证明会话持久化）、`POST /api/session`、`GET /api/model` 均可用 |
| 凭据导入 | 写入 `<app_home>/opencode/data/opencode/auth.json` 后，**同一端点、同一模型名**即可用 |
| 会话持久化 | 跨多次进程启动保留（隔离 sqlite） |
| 优雅停止 | `terminate()` 即退出，无孤儿进程残留 |
| 对话正确性 | 提问"只回答两个字：就绪" → 返回 `就绪`；`step_finish reason=stop`，tokens 9927，cost $0.00125 |

### ⚠️ 两个必须改设计的实测发现

**① 172.3 MB 对 D5「打进主 exe」的后果**

现 onedir 产物 148 MB + 内核 172.3 MB ≈ **320 MB 目录**；onefile 会更糟（每次解包 172 MB）。且 PyInstaller **不压缩** onedir 内容。

| 方案 | 体积 | 备注 |
|---|---|---|
| 现状：内核随主 exe 走（D5 已定） | ~320 MB | 用户体验：解压即用，零等待 |
| 备选：首次使用时下载到 `<app_home>/opencode/` | 主 exe 维持 148 MB | 首次用到需 8.6 s 下载（实测本机 59.3 MB）+ 解压 |
| 备选：用 `-baseline` 变体（非 AVX2） | 同样 59.3 MB | 只为兼容老 CPU，不省体积 |

> **决策待你确认**：D5 已选"打进主 exe"，但当时未知是 172 MB。请确认是否维持，还是改为首次下载。

**② `/api/model` 不是完整模型目录 —— 控制台不能只依赖它**

| 来源 | 数量 | 语义 |
|---|---|---|
| `GET /api/model`（HTTP） | 38 个，**全是 `opencode/*`** | provider 目录视角，不代表可用 |
| `opencode models`（CLI） | 13 个，**含 `deepseek/deepseek-flash`、`deepseek/deepseek-v4-pro`** | 按凭据激活后的**可用**列表 |

→ 控制台的模型选择器应**以 CLI 为准**（或两者合并去重），否则会漏掉用户自己配的 provider。已写入风险 23。

**③ 模型 id 报错信息友好，可直接暴露给用户**

传错模型时内核返回可读错误而非崩溃：

```
ProviderModelNotFoundError: Model not found: deepseek/deepseek-chat.
Did you mean: deepseek-flash, deepseek-v4-pro?
```

控制台可以直接把这条消息透出，不需要自己维护 model id 校验表。

**④ 宿主的模型名与 opencode 目录天然对齐**

宿主 `llm_config.json` 用 `deepseek-flash` / `deepseek-v4-pro`，opencode 的 deepseek provider 里**恰好是同两个 id**（`packages/opencode` 的模型目录）。所以 D4 的凭据导入 + 模型名可以零映射直通。

### 9.6 本地构建的四个坑（已写入 `build_opencode_kernel.bat`）

P0 起初尝试从源码构建，遇到四个问题，改用 release 二进制绕过。若将来需要打补丁或自建，按此处理：

| # | 坑 | 现象 | 修法 |
|---|---|---|---|
| 1 | **该 checkout 不是 git 仓库** | `packages/script/src/index.ts:30` 的 `git branch --show-current` → `fatal: not a git repository`，exit 128，构建直接失败 | 设 `OPENCODE_CHANNEL=latest` + `OPENCODE_VERSION=1.18.35`（前者跳过 git 调用，后者跳过 npm registry 查询，保证离线可重复） |
| 2 | **`bun install` 在原生 postinstall 上失败** | `tree-sitter-powershell` 的 node-gyp 在 Bun 的 `.bun` 目录布局下拼不出 `node-addon-api` 中间路径 → `FileNotFoundError` + `gyp ERR!`，install exit 1 | `bun install --ignore-scripts`（内核运行期走 `web-tree-sitter` WASM，不需要该原生 addon；`fix-node-pty` 只影响 PTY） |
| 3 | **首次 install 中断会污染依赖链接** | 中断后再 install 出现 10 个包 `failed to link package ... (copyfile)` ENOENT，构建时报 `Could not resolve: @opentelemetry/resources` 等 | 中断后必须清理 `node_modules` 再重装 |
| 4 | **构建期需联网** | `script/generate.ts:10-13` 拉 `https://models.dev/api.json` | 有网直跑；离线用 `MODELS_DEV_API_JSON` 指向本地 api.json |
| — | 另：`--skip-embed-web-ui` | 不跳过会额外跑一整趟 `packages/app` 的 Vite 构建 | D7 已定用 TUI，故跳过（也是体积优化） |

> **建议**：默认交付走 **release 二进制**（CI 构建、已签名、可复现），`build_opencode_kernel.bat` 仅作为"需要打补丁/离线"时的备选。release 资产命名固定为 `opencode-windows-x64.zip`，与内置版本号 `1.18.35` 对应，便于脚本校验。

### 9.7 用户澄清后的最终运行时行为（已实现）

用户在看过初版后澄清了四条，其中两条把原先的"手动"改成了"必须自动"。已实现：

| # | 用户要求 | 实现 | 验收 |
|---|---|---|---|
| 1 | **GUI 程序是 opencode 内核的 MCP 服务** | `mcp_server.serve_http_in_thread()` 在 GUI 进程内起 streamable-http 端点，并写进内核 `opencode.json` 的 `mcp` 段 | 已端到端验证（§9.5 方向 A）；`opencode mcp list` 显示 connected |
| 2 | **打开 GUI 就同时启动 opencode，并显示为系统的 console / mac 的 bash** | `design_studio` 在 `win.show()` 后调用 `StudioWindow.kernel_boot_async()`；`kernel_boot.KernelBoot.start()` 起内核 + 注册 MCP + 建会话 + `kernel_client.spawn_tui()` 在**独立终端窗口** attach 同一实例<br>Windows：新 PowerShell/conhost 窗口（`CREATE_NEW_CONSOLE`）<br>macOS：`osascript` 让 Terminal.app 执行同一 attach 命令<br>Linux：回到当前终端 | 需在真机 GUI 上验（本次仅验证到 `spawn_tui` 的构造与 attach 命令正确） |
| 3 | **GUI 切项目 → opencode 新建/切换到对应 session** | 项目↔session 映射存 `<kernel_home>/projects.json`；`_switch_project()`（**所有项目切换的唯一汇聚点**）末尾调 `kernel_switch_project()`；`KernelBoot.ensure_project_session()` 复用已有 session，不存在才新建，并让 TUI 重新 attach | ✅ 已实测：首次 `created=true`、再次 `created=false` 且 sessionID 相同、不同项目各自独立 |
| 4 | **在 console 用 opencode 下全自动命令驱动 GUI 功能** | 由方向 A 保证（21 个领域工具对内核可见可调） | ✅ 已实测（§9.5） |

**开关**（避免干扰既有自动化）：

| 环境变量 | 默认 | 作用 |
|---|---|---|
| `PCL_KERNEL_AUTOSTART` | `1` | GUI 启动时是否拉起内核 |
| `PCL_KERNEL_TUI` | `1` | 是否自动弹出内核终端窗口 |
| `PCL_SKIP_KERNEL` | `0` | 打包时是否排除内核二进制 |

`--shot` / `--e2e` / `--demo` 三种自动化模式**自动跳过**内核联动（`should_skip_for_mode()`）。

**控制台对等命令**（与 GUI 启动时做的完全同一件事，便于复现与排障）：

```bat
PCLRadiomics.exe kernel boot --project "某课题"   :: 起内核+注册MCP+绑会话+开终端
PCLRadiomics.exe kernel project list              :: 项目↔session 映射
PCLRadiomics.exe kernel project ensure --name X   :: 确保 X 有 session（复用或新建）
PCLRadiomics.exe kernel project switch --name X   :: 同上并让终端跟过去
PCLRadiomics.exe kernel project unbind --name X
```

### 9.8 实测修掉的两个内核进程管理 bug

这两个都是"控制台用法"才会暴露、GUI 长驻进程掩盖了的问题：

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | **每敲一条 `cli.py kernel ...` 就多一个内核进程**（实测连跑三条留下 3 个，各占 300+ MB） | `ensure_running()` 里 `cleanup_stale()` 只"报告复用"，并不真正**接管**状态文件里的存活实例，于是每次都再 spawn 一个 | 新增 `adopt_state()`：状态文件里的实例存活且 health 通过就直接接管为 `self.state`；`ensure_running()` 先尝试接管 |
| 2 | **`kernel stop` 跨进程停不掉内核**（报"无运行中的内核"） | `stop()` 只看 `self._proc`（本进程句柄），新进程里它是 `None`；状态文件里的 pid 被忽略 | `stop()` 无句柄时退回 `adopt_state()` 并按强杀处理，同时删除状态文件 |

> 注：验证时发现机器上另有 `C:\Users\chris\AppData\Local\npm-global\...\opencode.exe`（用户自己 npm 全局安装的 opencode，pid 11996，10/9 启动）。它不是我们拉起的，**未做处理** —— 隔离设计（独立 home、独立端口、独立密码）本就保证两者互不干扰。

---


## 10. 风险清单

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| 1 | **体积膨胀** | **P0 实测：内核 172.3 MB**。onedir 现 148 MB → 合计约 **320 MB**；onefile 更糟（每次解包 172 MB） | 见 §9.5①：维持打包内置，或改为首次使用时下载到 `<app_home>/opencode/`。**待确认** |
| 2 | ~~Win7 必须豁免~~ | **已随 D6 取消**（不需要兼容 Win7 变体） | 无需处理 |
| 3 | **首屏被阻塞** | 内核冷启动 + SQLite 初始化若在 GUI 启动路径上，会拖慢开窗 | 内核**懒启动**（首次用到才起）；起进程异步 + 健康检查带超时；GUI 首屏绝不等待内核 |
| 4 | **孤儿进程** | 宿主崩溃/被强杀时内核残留，端口与 sqlite 锁泄漏 | 记录 `{pid, port}` 到 `app_home`；启动时清理陈旧实例；优雅 stop + 超时 kill（对齐 `desktop/src/main/server.ts:165-183` 的 stop/race 模式） |
| 5 | **端口冲突** | 固定端口会撞 | 用随机端口或扫描（复用 `web_server.pick_port` 的既有做法 `:1141-1152`） |
| 6 | **权限/提问挂死** | 内核阻塞等待回复，宿主没实现 → 会话永久卡住 | 常驻 SSE 订阅 + 三类回复通道 + 超时兜底策略 |
| 7 | **流式吞吐** | `TranscriptView.stream` 每个 delta 一次跨线程 signal + `insertText`，**无合批**（ui_kit.py:675-681）。内核工具事件更密集 | 新增带缓冲/合批的 sink；复用宿主已有的 160 字符合批先例（`web_server.py:557-566`） |
| 8 | **取消机制** | 宿主无停止按钮，`closeEvent` 里 `terminate()` 对流式中 HTTP 不安全 | 用内核的 `POST /api/session/:id/interrupt` 做真取消；不要依赖 `terminate()` |
| 9 | **无中央 feature flag** | 三套 server 各自独立 `STATE`，开关要分别接 | 沿用 spec 级开关先例（`PCL_WEB_WITH_SCIPY`）+ 配置文件键 |
| 10 | **自检脚本静默漏检** | 新视图不注册进 `VIEWS`/`PAGES` 就不被检查 | 把注册写进 P3 的验收标准 |
| 11 | ~~`api_server` 流式缺陷被继承~~ | **已随 D4 消解**：(b) 已排除，内核不经过 `api_server` | 无需处理 |
| 12 | **`mcp._mcp_server.version` 私有 API** | `mcp_server.py:52-55` 依赖私有属性，SDK 升级会崩 | 加 try/except 并纳入升级检查清单 |
| 13 | **两个变体同名覆盖** | `pclradiomics.spec:26` 的 `APP_NAME` 是硬编码 `"PCLRadiomics"`，直接加 `PCL_CONSOLE=1` 会产出同名 exe 并覆盖 windowed 版 | 为 spec 增加 `PCL_APP_NAME` 环境变量；`编译_内核版.bat` 显式设置；构建后校验两个产物同时存在 |
| 14 | **隔离不彻底导致误配** | `OPENCODE_TEST_HOME` 未设时，`config/paths.ts:36-37` 的配置向上发现以真实 home 为边界，可能读到用户其它项目的 `.opencode` | P0 实测确认；必要时用 `OPENCODE_DISABLE_PROJECT_CONFIG` 收紧 |
| 15 | **切换隔离/共享需重启内核** | `xdg-basedir` 在模块加载时求值，运行中改 XDG 无效 | 设置项变更后强制重启内核进程；UI 明确提示 |
| **16** | **MCP `timeout` 默认 5 秒** | 内核调用宿主长任务工具（`manuscript_review` 数分钟）会超时失败 | 生成 `opencode.json` 时显式写 `timeout`（如 600000），见 §2.3 |
| **17** | **GUI 与 MCP 模式互斥** | 方向 A 要求 GUI 进程同时暴露 MCP HTTP 端点，但 `cli.py:261-263` 现状是 `gui`/`mcp` 二选一 | 把 FastMCP streamable-http 移到 GUI 进程的后台线程；这是方向 A 的前置改造 |
| **18** | **MCP 配置键名易错** | opencode 用 `mcp`，不是 Claude Desktop 的 `mcpServers`（宿主 README 写错过） | 生成配置时用 `mcp`；纳入 `_test_kernel.py` 断言 |
| **19** | **TUI 裸跑会起第二个 server** | 裸跑 `opencode` 会自建 server，与我们的隔离实例争用同一个 sqlite | **必须用 `opencode attach <url>`**（§8.3）；`_test_kernel.py` 断言 attach 后进程数不增加 |
| **20** | **TUI 进程未继承隔离环境** | `attach` 会读本地 `TuiConfig.get()`（`attach.ts:115`）；环境不一致会让 TUI 显示用户真实 home 的配置 | `kernel_client.kernel_env()` 供 server 与 TUI **共用同一份环境** |
| **21** | **密码泄露到进程列表** | 用 `-p <password>` 会把密码暴露在任务管理器/`Get-Process`/窗口标题里 | 改用 `OPENCODE_SERVER_PASSWORD` 环境变量传入（`attach` 原生支持，见 §8.3①） |
| **22** | **新控制台依赖** | TUI 需要真实终端；在 console 子系统的宿主里若不新开控制台，TUI 会与宿主日志抢同一个窗口 | `subprocess.CREATE_NEW_CONSOLE`；返回值/失败要能反馈到 GUI |
| **23** | **`/api/model` 不是完整模型目录** | P0 实测：`GET /api/model` 只返回 38 个 `opencode/*`（provider 目录视角），而 `opencode models` CLI 返回 13 个**可用**模型并含 `deepseek/*`。只依赖前者会让控制台漏掉用户自己配的 provider | 模型选择器以 `opencode models` 为准，或两者合并去重（§9.5②） |
| **24** | **内核 home 目录层级易错** | `XDG_DATA_HOME` 指向 `<app_home>/opencode/data` 时，opencode 再拼一层 `opencode` → 实际 auth.json 在 `<app_home>/opencode/data/opencode/auth.json`。拼错会写到别处 | `kernel_client.ensure_home_layout()` 统一给出路径，禁止各处手拼（P0 的测试自身就踩过这个坑） |

---

## 11. 决策点状态

### 已确认

| # | 决策 | 结论 | 落点 |
|---|---|---|---|
| D2 | 「console=true」 | ✅ **编译成 console 子系统**，产出独立变体 `PCLRadiomicsConsole.exe`，主 exe 保持 windowed | §4.2 |
| D3 | 内核配置隔离/共享 | ✅ **隔离**（便携、不污染系统 opencode） | §6.2 |
| D4 | 内核的模型走哪条 | ✅ **(a) opencode 原生 provider** —— 由硬约束确定：宿主 LLM 层无 function/tool calling，(b) 会让内核能力归零 | §7 |
| D5 | `opencode.exe` 是否打进主 exe | ✅ **打进主 exe** —— 连带结论：内核版只出 onedir，放弃 onefile。⚠️ **P0 实测内核为 172.3 MB，见 D11** | §4.3、§9.5① |
| D6 | 是否需要兼容 Win7 变体 | ✅ **不需要** —— 相关排除工作取消 | §4.3、§10 风险 2 |
| D7 | 内核 UI 落点 | ✅ **opencode TUI，跑在 PowerShell 窗口里**，且必须 `opencode attach` 到隔离实例（不能裸跑，否则会起第二个 server 争用同一 sqlite） | §8.3 |
| D8 | `OPENCODE_TEST_HOME` 是否隔离 | ✅ **不隔离** —— 保留用户已有的 `~/.claude/skills`、`~/.agents/skills` | §6.3② |
| D10 | 接受"GUI 进程同时暴露 MCP 端点"这一改造 | ✅ **接受** —— 方向 A 的前置改造 | §10 风险 17 |

### 待确认

| # | 决策 | 选项 | 备注 |
|---|---|---|---|
| D9 | 方向 A 的连接方式 | `type:"remote"` 指向常驻 GUI 进程（D10 已接受，隐含此项）／ `type:"local"` 另起 `PCLRadiomics.exe mcp` | §2.3。**若接受 D10 则应同时选 remote**，请确认或纠正 |
| **D11** | **体积已实测 172.3 MB，是否维持 D5「打进主 exe」？** | **(a) 维持**：onedir ≈ 320 MB，解压即用零等待 ／ **(b) 改为首次使用时下载**：主 exe 维持 148 MB，首次用到前下载 8.6 s + 解压 ／ **(c) 混合**：安装包内置，但按需释放 | §9.5①。D5 决策时未知具体体积，现在有了数字，**建议你重新拍一次** |

---

## 12. 未验证项

### ✅ 已由 P0 解决

| 原未验证项 | P0 结论 |
|---|---|
| 二进制实际体积 | **172.3 MB**（zip 59.3 MB） |
| 冷启动到 health 就绪时间 | **0.94 s**（到端口 0.93 s） |
| 隔离是否真的生效 | ✅ 用户真实 `~/.local/share/opencode` 未被触碰，全部状态落在 `<app_home>/opencode/` |
| 凭据能否用宿主那套 | ✅ 写入隔离 `auth.json` 后，同一端点同一模型名即可用；会话可持久化跨进程 |
| provider/model 命名是否对得上 | ✅ 宿主 `deepseek-flash` / `deepseek-v4-pro` 与 opencode 的 deepseek provider 目录**完全同名**，零映射 |
| 本地能否自建二进制 | ⚠️ 可以但有四个坑（§9.6）；P0 改用 release 二进制 |

### 仍未验证（转入 P1/P2）

- `opencode providers login` 能否**完全非交互**地写入 API key → 方案继续默认走直接读写 `auth.json`。
- **SSE 事件 schema**：P0 只验证了端点连通性。空闲会话无事件、阻塞读会超时，因此 P1 需改为 **subscribe-then-prompt**（先订阅、再发 prompt、再收集）才能拿到真实事件形状。
- **`opencode attach` + TUI 的实际表现**（D7 主路径）：`CREATE_NEW_CONSOLE`、环境继承、密码走环境变量三项尚未实跑。
- **内核能否调用宿主的 MCP 工具**（方向 A）：P0 未涉及；需 P1/P3 让 GUI 进程暴露 MCP 端点后，实测 `init count` 是否从 18 增加。
- **`question` 工具的实际触发**（依赖 `OPENCODE_CLIENT=desktop`，已按 `registry.ts:207` 推断但未运行验证）。
- Python 侧无官方 ACP SDK；若将来走 ACP 需自实现 ndjson JSON-RPC。
- 宿主 `_test_mcp_stdio.py` / `_test_mcp_test` 的既有失败是**沙箱环境所致**（`WinError 5` 命名管道、无监听端口 502），不是代码缺陷；引入内核工具后需在真实 MCP 客户端下重跑。

### P0 产出的文件

| 文件 | 说明 |
|---|---|
| `kernel_client.py` | 内核客户端（Qt-free）：隔离 `kernel_env()`、进程生命周期、孤儿清理、HTTP、SSE、`run_once`、`spawn_tui`、`status()` |
| `_test_kernel.py` | P0 验收自检（8 步）：体积 / 隔离 / 冷启动 / HTTP / 模型目录 / 凭据导入 / 流式对话 / SSE 连通 / 停止与孤儿 |
| `_kernel_diag.py` | 诊断用（可删）：模型目录、provider 列表、`run` 原始事件、内核日志尾部 |
| `build_opencode_kernel.bat` | 从源码构建的备选路径，已把 §9.6 的四个坑写进脚本 |
| `opencode/opencode.exe` | 下载的 v1.18.35 release 二进制（172.3 MB）—— **P1 起改为随包分发** |
