# v2.0.0 —— 内嵌 opencode 内核

> 相对 v1.3.0 的主版本跃迁：本程序不再只是一个「调用 LLM 的界面」，
> 而是一个**内嵌 agent 内核、并作为该内核工具提供方**的宿主。
> 完整设计见 [`opencode-embedding-plan.md`](opencode-embedding-plan.md)。

---

## 一句话

程序里嵌了一个 **opencode**（TypeScript/Bun 写的编码 agent）作为内核；
内核通过 **MCP** 调用本程序的 21 个组学领域工具，本程序通过 **HTTP + SSE** 驱动内核的会话。
于是模型可以自主串起多步任务（读手稿 → 跑确定性信号 → 调 LLM 分层审阅 → 写回 Word），
中间不再需要人手点每一步。

---

## 架构关系：四个角色、两个方向

"嵌入"其实是方向相反的两件事，v2.0.0 把它们都实现了：

| # | 关系 | 方向 | 协议 | 谁主动 |
|---|---|---|---|---|
| **A** | 内核调用本程序的领域能力 | **内核 → 宿主** | **MCP** | 内核（客户端） |
| **B** | 本程序驱动内核（建会话/发消息/看事件/配 skill/配 key） | **宿主 → 内核** | **HTTP + SSE** | 宿主（客户端） |
| C | 外部 agent 调用本程序 | 外部 → 宿主 | MCP | 外部 agent（**维持 v1.x 现状不变**） |
| D | 本程序托管内核进程 | — | 进程管理 | 宿主 |

**关键事实**：opencode 只做 MCP **客户端**，从不做服务端。
所以「GUI 程序是 opencode 的 MCP 服务」这个定位是准确的 —— 它就是方向 A。

```
┌──────────── PCLRadiomics.exe（GUI 进程，常驻）────────────┐
│  GUI 窗口（触发按钮 + 内核设置入口）                        │
│  MCP 服务端  FastMCP / streamable-http（21 个领域工具）      │
│         ▲                                                  │
│         │ 方向 A：MCP                                       │
│  kernel_client.py ──HTTP+SSE──┐                            │
│  kernel_config.py（隔离 home） │                            │
└────────────────────────────────┼───────────────────────────┘
                                 │ 方向 B / 方向 D
                                 ▼
              opencode.exe serve（agent 内核，隔离 home）
                  · session / runner · 18 个内置工具
                  · permission / provider / LLM
                  · MCP client ──► 调本程序的 21 个领域工具
              内核 UI：opencode TUI（独立控制台窗口，attach 到本实例）
```

---

## 新增能力

### 1. 内核可以调用本程序的 21 个领域工具（方向 A）

内核配置里注册本程序的 MCP 端点后，`design_ask` / `design_rewrite` / `design_finalize` /
`manuscript_review` / `stat_run_test` / `project_*` / `export_*` 等全部对内核可见可调。

已实测：内核自主调用 `list_stages`，并正确答出本程序 `stages_data` 里的真实内容
（"第 1 阶段的标题是：研究问题与设计"）。

### 2. 控制台配置面（`kernel` 子命令组）

**session / skill / API Key** 都能在控制台配置，且**写的是 opencode 自己的文件**
—— 不存在第二套真值：

```bat
PCLRadiomics.exe kernel selftest                 :: 离线自检（推荐先跑这个）
PCLRadiomics.exe kernel status                   :: 二进制/进程/配置/凭据/技能总览

PCLRadiomics.exe kernel auth set deepseek sk-xxx :: 配 API Key（写 auth.json，0600）
PCLRadiomics.exe kernel auth import-host         :: 复用宿主已有凭据链的密钥
PCLRadiomics.exe kernel auth import-system       :: 从系统 opencode 单向导入
PCLRadiomics.exe kernel auth list                :: 列出（脱敏）

PCLRadiomics.exe kernel skill list                :: 列出
PCLRadiomics.exe kernel skill add my-skill --file SKILL.md
PCLRadiomics.exe kernel skill remove my-skill

PCLRadiomics.exe kernel session list              :: 会话列表
PCLRadiomics.exe kernel session new --title 试验
PCLRadiomics.exe kernel session prompt --session <id> --text "帮我看看这份手稿"
PCLRadiomics.exe kernel session interrupt --session <id>

PCLRadiomics.exe kernel model list                :: 模型（以 opencode models 为准）
PCLRadiomics.exe kernel model set deepseek/deepseek-v4-pro
PCLRadiomics.exe kernel mcp host                  :: 起宿主 MCP 端点并注册给内核
PCLRadiomics.exe kernel mcp list                  :: 配置视角 + 内核视角
PCLRadiomics.exe kernel ui                        :: 在独立控制台窗口里开内核 TUI
PCLRadiomics.exe kernel logs -n 100
```

### 3. 配置与 opencode 完全一致

| 配置域 | 落点 | 一致性依据 |
|---|---|---|
| session | 内核官方 HTTP API | 无本地副本 |
| skill | `<kernel_home>/config/opencode/skill/<name>/SKILL.md` | 与 opencode 同格式（`name` 必填 + 可选 `description`） |
| API Key | `<kernel_home>/data/opencode/auth.json`（0600） | schema 逐字段对齐 `{"provider":{"type":"api","key":...}}` |
| model | `opencode.json` 顶层 `model` | 与 opencode 同一加载路径 |
| MCP | `opencode.json` 的 **`mcp`** 段 | 注意不是 Claude Desktop 的 `mcpServers` |
| MCP 超时 | 显式设 **600000 ms** | opencode 默认只有 5000 ms，会让 `manuscript_review` 这类长任务直接超时失败 |

### 4. 隔离运行，不污染系统 opencode

内核的全部状态落在 `<程序目录>/opencode/`（源码运行时即仓库根）：
`data/`（auth.json、会话 sqlite、snapshot）、`config/`、`state/`、`cache/`。

已实测：用户真实的 `~/.local/share/opencode` **未被触碰**。

### 5. 双 Windows 变体

```bat
编译_内核版.bat                  :: 两个变体都编
编译_内核版.bat --windowed       :: PCLRadiomics.exe（windowed，双击无黑框）
编译_内核版.bat --console        :: PCLRadiomicsConsole.exe（console 子系统）
编译_内核版.bat --onefile        :: 单文件版（按设计不含内核）
```

`PCLRadiomicsConsole.exe` 是独立变体而非取代主程序 —— 因为 Win11 的控制台由
Windows Terminal 托管（属于别的进程），`ShowWindow` 藏不掉，若把它做成唯一产物，
双击 GUI 必然多一个终端窗口。

---

## 实测数据

| 指标 | 实测值 |
|---|---|
| 内核二进制体积 | **172.3 MB**（release zip 59.3 MB） |
| 冷启动 spawn → 端口可连 | **0.93 s** |
| 冷启动 spawn → health 通过 | **0.94 s** |
| 一次完整流式对话（含标题生成/快照/工具注册） | 33.4 s |
| 内核内置工具数 | 18 |
| 本程序暴露给内核的工具数 | 21 |
| 产物体积（onedir，含内核） | 约 **320 MB** |

自检脚本：`_test_kernel.py`（P0）、`_test_direction_a.py`（P3 方向 A 端到端）、
`_mcp_thread_probe.py`（后台线程起 FastMCP 的可行性）。

---

## 分发说明（重要）

**内核二进制 172.3 MB，超过 GitHub 单文件 100 MB 硬上限，因此不入库。**
构建时由 `pclradiomics.spec` 自动获取（有网自动下载 release；
离线可先跑 `build_opencode_kernel.bat --from-source` 从源码构建）。

- 想打一个**不含内核**的版本：设 `PCL_SKIP_KERNEL=1`（单文件版默认如此）。
- 老 CPU（无 AVX2）：`python get_opencode_kernel.py --baseline`。
- `.gitignore` 已排除 `opencode/` —— 该目录含真实 API Key 与会话数据，**绝不可入库**。

---

## 已知限制

1. **内核嵌入的完整目标是 Windows。** macOS 会收集内核客户端代码，
   若在 macOS 上跑过 `get_opencode_kernel.py`（下 darwin 版）则同样具备完整能力；
   否则 `kernel selftest` 会明确报告「找不到 opencode」。
2. **单文件版不含内核**（启动解包 172 MB 会让体验严重恶化）。
3. **内核 UI 用 opencode 自带的 TUI**，本程序不自绘会话流 ——
   避免重建会话列表/工具调用/权限弹窗/diff 查看，也避开一批自检脚本的覆盖风险。
4. `PCLRadiomicsConsole.exe` 需要显式构建（`--console`），默认构建只出 windowed 主程序。
5. 内核 TUI 关闭不影响内核进程；内核随主进程退出。

---

## 从 v1.3.0 升级

- **无破坏性变更**：原有 GUI / MCP / Web / API 四种模式与全部子命令行为不变；
  对外 MCP 服务仍是 21 个工具（方向 C 未改）。
- `APP_VERSION` 1.3.0 → 2.0.0（推理 API 的 `Server` 头、macOS 的 `CFBundleVersion` 都会跟着变）。
- 新增 `kernel` 子命令组；新增 `opencode/` 运行期目录（已在 `.gitignore` 中）。
- 首次使用建议顺序：`kernel selftest` → `kernel auth import-host` →
  `kernel mcp host` → `kernel ui`。
