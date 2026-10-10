# opencode Agent 代码结构与功能分析简报

> **分析对象根目录（下称 `<ROOT>`）**
> `I:\Completion-of-the-omics-research-design-plan-main\opencode-dev\opencode-dev`
>
> ⚠️ **路径注意**：`opencode-dev` 目录嵌套了两层。外层 `I:\Completion-of-the-omics-research-design-plan-main\opencode-dev\` 下只有一个同名子目录，真正的仓库根是内层的 `...\opencode-dev\opencode-dev`。
>
> **文中所有 `路径:行号` 引用均以 `<ROOT>` 为前缀**（即省略了 `<ROOT>\`），行号为分析时的当前工作树位置。
>
> **方法与局限**：结论全部来自源码只读分析（read/grep/glob），**未执行构建、未运行测试**，因此描述的是"代码写了什么"而非"运行时会怎样"。文末第 13 节集中列出未能确认的条目。

---

## 目录

1. [基本定位与规模](#1-基本定位与规模)
2. [Agent 代码地图](#2-agent-代码地图)
3. [Agent 定义与配置](#3-agent-定义与配置)
4. [一轮对话的生命周期（V1 生产路径）](#4-一轮对话的生命周期v1-生产路径)
5. [系统提示与上下文组装（V1 vs V2）](#5-系统提示与上下文组装v1-vs-v2)
6. [工具系统](#6-工具系统)
7. [权限模型](#7-权限模型)
8. [子代理、后台任务与上下文压缩](#8-子代理后台任务与上下文压缩)
9. [LLM / Provider 层](#9-llm--provider-层)
10. [客户端与服务层](#10-客户端与服务层)
11. [V1 → V2 迁移状态](#11-v1--v2-迁移状态)
12. [设计亮点与风险](#12-设计亮点与风险)
13. [未确认项与已知缺口](#13-未确认项与已知缺口)

---

## 1. 基本定位与规模

| 项 | 值 | 锚点 |
|---|---|---|
| 仓库 | `github.com/anomalyco/opencode` | `package.json:120-123` |
| 默认分支 | `dev` | `AGENTS.md:4` |
| 版本 | `1.18.35` | `packages\opencode\package.json:3`、`packages\core\package.json:3` |
| 许可 | MIT | `package.json:124` |
| 根包名 | `opencode`（private，**无 `version` 字段**） | `package.json:3`、`:5` |
| 包管理 | Bun `1.3.14`，workspace + catalog 锁版本 | `package.json:7`、`:25-32`（workspaces）、`:33-96`（catalog） |
| 运行时栈 | Effect `4.0.0-beta.83`（`:66`）/ Drizzle `1.0.0-rc.2`（`:65`）/ AI SDK `6.0.168`（`:67`）/ zod `4.1.8`（`:80`）/ Hono `4.10.7`（`:69`） | `package.json:33-96` |
| 构建 | Bun workspaces、Turbo 2.10.2、SST 4.13.1（Cloudflare）、Nix devshell | `turbo.json`、`sst.config.ts`、`flake.nix` |
| Lint / 格式化 | oxlint `1.60.0` + Prettier（`semi:false`, `printWidth:120`） | `.oxlintrc.json`、`package.json:105`、`:125-127` |
| 类型检查 | `tsgo`（`@typescript/native-preview`），**不用 `tsc`** | `AGENTS.md:149` |
| 依赖补丁 | ~20 个 `patchedDependencies` 覆盖 | `package.json:148-168` |

### 代码量（不含 `node_modules` / `dist` / `.turbo`，仅源码类扩展名）

| 包 | 文件数 | 行数 |
|---|---:|---:|
| `packages\opencode` | 804 | 342,845 |
| `packages\console` | 501 | 211,500 |
| `packages\app` | 618 | 164,305 |
| `packages\core` | 491 | 65,129 |
| `packages\sdk` | 47 | 64,614 |
| `packages\ui` | 373 | 45,823 |
| `packages\stats` | 117 | 36,624 |
| `packages\tui` | 239 | 36,181 |
| `packages\codemode` | 41 | 34,712 |
| `packages\session-ui` | 118 | 24,372 |
| `packages\llm` | 151 | 21,805 |
| `packages\web` | 52 | 10,254 |
| `packages\desktop` | 143 | 8,560 |
| `packages\client` | 21 | 5,109 |
| `packages\schema` | 74 | 3,333 |
| 其余（`effect-*`、`http-*`、`plugin`、`server`、`protocol`、`storybook`、`enterprise`、`cli`、`function`、`sdk-next`、`slack`…） | — | 各 < 3,300 |

### 核心结构判断

> 这是一个 **CLI + 常驻 HTTP 守护进程 + 内嵌服务器** 三合一的 agent 运行时。Agent 逻辑不是单点，而是**同时存在 V1（AI SDK 驱动、生产在用）与 V2（Effect 原生、迁移中）两套并行实现**。这是理解整个仓库的第一关键。

---

## 2. Agent 代码地图

### 2.1 五个最重要的位置

| 位置 | 职责 | 关键锚点 |
|---|---|---|
| `packages\opencode\src\agent\` | Agent 定义与服务 | `agent\agent.ts`、`agent\subagent-permissions.ts`、`agent\prompt\*.txt` |
| `packages\opencode\src\session\` | **一轮对话引擎**（真正的 agent loop） | `session\prompt.ts`、`session\processor.ts`、`session\llm.ts`、`session\system.ts`、`session\compaction.ts`、`session\tools.ts`、`session\instruction.ts` |
| `packages\opencode\src\tool\` | 内置工具**活代码** + 装配/过滤 | `tool\registry.ts`、`tool\truncate.ts`、各工具实现 |
| `packages\opencode\src\{permission,skill,mcp,plugin,provider,background,question,acp}\` | 权限/技能/MCP/插件钩子/Provider/后台/人机问答/ACP 协议 | 见第 6–9 节 |
| `packages\core\src\`、`packages\llm\src\` | **V2 域层与 LLM 协议层** | `core\src\agent.ts`、`core\src\session\runner\`、`core\src\tool\`、`core\src\system-context\`、`llm\src\route\`、`llm\src\protocols\` |

### 2.2 支撑性基础设施（agent 依赖但非 agent 本体）

| 文件 | 职责 |
|---|---|
| `packages\core\src\state.ts:29-127` | 可重放 transform 存储（`State.create({initial, draft})`、作用域化 `transform`、信号量保护的 `reload`、`batch` 合并）——Agent/Catalog/Command/Integration/Plugin 的共同基座 |
| `packages\core\src\event.ts:126-150` | 类型化事件总线 + 持久化事件存储；`:205-367` 每聚合单调 `seq` 与分歧/owner 校验在同一 SQLite 事务内；`:406-417` PubSub 扇出 |
| `packages\core\src\location.ts:19-32` | 工作区（Location）原语 |
| `packages\core\src\location-services.ts:42-79` | 每个 Location 的服务图（33 个节点） |
| `packages\core\src\location-services.ts:84-112` | 按 `Location.Ref` 惰性实例化的 LayerMap，空闲 TTL 60 分钟 |
| `packages\core\src\snapshot.ts:98` | 内容寻址的撤销：影子 git 目录 `<Global.data>\snapshot\<projectID>\<hash>`；`:238-248` 关闭时为 `noopLayer` |
| `packages\core\src\background-job.ts:88-99`、`:202-358` | 进程内任务注册表（start/extend/wait/promote/cancel）；`:113-119` 明确注明**非持久** |
| `packages\core\src\tool-output-store.ts:13-17`、`:129-174`、`:176-211` | 工具输出兜底：2000 行 / 50 KiB，超限写入 `<Global.data>\tool-output\tool_<id>`，首尾预览 + 每小时清扫 / 7 天 TTL |

### 2.3 分层依赖规则（仓库强约束）

```
schema  →  protocol  →  server
                 ↑
              client（可依赖 schema+protocol，绝不依赖 core/server）
sdk-next = client + core + server
```

出处：`AGENTS.md:3`。Protocol 只拥有端点的**构造与中间件摆放**，Server 注入具体的中间件 key。

---

## 3. Agent 定义与配置

### 3.1 V1 内置 Agent

定义于 `packages\opencode\src\agent\agent.ts`。

`Info` schema（`agent.ts:35-56`）字段：`name`、`description`、`mode: subagent|primary|all`、`native`、`hidden`、`topP`、`temperature`、`color`、**`permission: PermissionV1.Ruleset`**、`model`、`variant`、`prompt`、`options`、`steps`。

| Agent | mode | 权限特征 | 锚点 |
|---|---|---|---|
| `build` | primary | 默认 agent；`question`/`plan_enter` 设为 allow | `agent.ts:141-155` |
| `plan` | primary | 计划模式，禁止所有编辑；仅放行 `.opencode/plans/*.md` 与 plans 目录 | `agent.ts:156-181` |
| `general` | subagent | 通用多步任务；禁止 `todowrite` | `agent.ts:182-195` |
| `explore` | subagent | **白名单模式**：`"*": deny` 后仅放行 `grep/glob/list/bash/webfetch/websearch/read` | `agent.ts:196-218` |
| `compaction` | primary, hidden | 全 `"*": deny`，专用 Prompt | `agent.ts:219-233` |
| `title` | primary, hidden | 全 deny，`temperature: 0.5` | `agent.ts:234-249` |
| `summary` | primary, hidden | 全 deny | `agent.ts:250-264` |

**默认权限基线**（`agent.ts:108-136`）：

```
"*": allow
doom_loop: ask
external_directory: { "*": ask, <截断目录>/<tmp>/<技能目录>/<引用目录>: allow }
question / plan_enter / plan_exit: deny
read: { "*": allow, "*.env": ask, "*.env.*": ask, "*.env.example": allow }
```

内置项与用户配置的合并顺序为 `defaults → 内置覆盖 → user`（`agent.ts:267-294`）；`disable: true` 可删除内置 agent。`truncate.GLOB` 的 `external_directory` allow 会被强制补齐，除非用户显式 deny（`agent.ts:296-310`）。

服务接口：`get` / `list` / `defaultInfo` / `defaultAgent` / `generate`（`agent.ts:64-80`），默认 agent 选择逻辑跳过 `subagent` 与 `hidden` 并优先 `build`（`agent.ts:328-344`）。`generate` 用 LLM 生成新 agent 配置（`agent.ts:368-436`），提示词在 `agent\generate.txt`。

### 3.2 用户扩展的两条路径

1. **配置文件**：`opencode.json` / `opencode.jsonc` 的 `agent` 字段。
2. **磁盘 Markdown**：扫描 `{agent,agents}/**/*.md`（`packages\opencode\src\config\agent.ts:11-32`）与 `{mode,modes}/*.md`（`:34-58`）。YAML frontmatter 写入 mode/model/tools/color 等，**正文即 system prompt**（`prompt: md.content.trim()`）。

仓库自带示例：
- `.opencode\agent\triage.md:1-9` —— frontmatter 演示 `mode/hidden/model/color/tools`
- `.opencode\agent\duplicate-pr.md`
- `.opencode\opencode.jsonc` —— 演示 `permissions`、`references`、`mcp`、`tools` 开关

### 3.3 关键设计

> **Agent 定义不含工具清单**，只有 `permission` 规则集 + `mode` + `hidden`。工具的可见性与可调用性**完全由权限规则推导**。

### 3.4 V2 的 Agent 模型

`packages\schema\src\agent.ts:10-38` 定义 `AgentV2.Info`：`id`、`model`、`request`、`system`、`description`、`mode`、`hidden`、`color`、`steps`、**`permissions: Permission.Ruleset`**。
`packages\core\src\agent.ts:8-15` 定义 `AgentV2`（branded ID，`defaultID = "build"`），服务名 `@opencode/v2/Agent`；默认选择逻辑 `:67-79`，接口 `get/default/resolve/select/all` `:35-41`。

---

## 4. 一轮对话的生命周期（V1 生产路径）

### 4.1 关键文件

| 文件 | 职责 | 关键锚点 |
|---|---|---|
| `packages\opencode\src\session\session.ts` | Session/消息/part 的 CRUD、**事件发布**、token 与成本核算、fork、分页。无 LLM 逻辑 | `:629-633`、`:635-643`、`:877-885`、`:338-405` |
| `packages\opencode\src\session\prompt.ts` | **轮次引擎**：`prompt()`、`createUserMessage()`、`runLoop()`、`loop()`、`shell()`、`command()`、`handleSubtask()`、标题生成。拥有系统提示装配与循环终止 | `:1052`、`:1081`、`:635`、`:1343` |
| `packages\opencode\src\session\processor.ts` | 每条 assistant 消息一个 LLM 流：消费 `LLMEvent` → 写 part、doom-loop 检查、重试、清理；返回 `"continue" \| "compact" \| "stop"` | `:29`、`:30`、`:98`、`:641`、`:713-730` |
| `packages\opencode\src\session\llm.ts` | `LLM.stream()`：provider/auth/plugin 准备、native-vs-AI-SDK 运行时门控、`streamText()`、归一为单一 `LLMEvent` 流 | `:9-31`、`:85-90`、`:226-269` |
| `packages\opencode\src\session\llm\request.ts` | `LLMRequestPrep.prepare`：最终 `system[]`、provider 消息、params、headers、工具过滤 | `:58-78`、`:114`、`:134`、`:210-216` |
| `packages\opencode\src\session\llm\ai-sdk.ts` | 适配器：AI SDK `fullStream` part → `@opencode-ai\llm` `LLMEvent` | — |
| `packages\opencode\src\session\system.ts` | `SystemPrompt.environment/skills/mcp` + `provider(model)` 模板选择 | `:28-51`、`:69-105` |
| `packages\opencode\src\session\tools.ts` | `SessionTools.resolve`：registry + MCP 资源工具 → 带 `Tool.Context` 的 AI SDK 工具 | `:41-134`、`:81-89` |
| `packages\opencode\src\session\instruction.ts` | AGENTS.md/CLAUDE.md/CONTEXT.md 发现 + 读文件时向上懒注入 | `:110-153`、`:179-221` |
| `packages\opencode\src\session\run-state.ts` | 每会话 `Runner` 状态机 + 后台任务取消 | `:35-107` |
| `packages\opencode\src\session\retry.ts` | 可重试性分类 + 退避 `Schedule`（最多 5 次） | `:183-207` |

### 4.2 生命周期（文字流程）

```
POST /session/:id/prompt
  │   入口：packages\opencode\src\server\routes\instance\httpapi\handlers\session.ts:295-309
  │        （promptAsync 分叉版 :311-329；shell :341-347；command :331-339；summarize :273-293）
  ▼
SessionPrompt.prompt()                                   prompt.ts:1052
  ├─ sessions.get + SessionRevert.cleanup                prompt.ts:1055-1056
  ├─ createUserMessage                                   prompt.ts:635
  │    └─ plugin "chat.message"、图片归一化、Schema 解码校验   prompt.ts:1022-1047
  ├─ tool→permission 物化                                 prompt.ts:1060-1067
  └─ loop({sessionID})                                   prompt.ts:1070 → 1343
       └─ SessionRunState.ensureRunning                  run-state.ts:88
            └─ runLoop  while(true)                      prompt.ts:1081
                 ├─ status.set busy                      prompt.ts:1089
                 ├─ MessageV2.filterCompactedEffect       prompt.ts:1092
                 ├─ MessageV2.latest                      prompt.ts:1096
                 ├─ 退出判定（无待办则 break）              prompt.ts:1111-1130
                 ├─ ensureTitle（forked）                  prompt.ts:1133-1139
                 ├─ subtask → handleSubtask               prompt.ts:1144-1147
                 │  compaction → compaction.process       prompt.ts:1149-1159
                 ├─ 溢出? → compaction.create(auto)        prompt.ts:1161-1168
                 ├─ SessionReminders.apply                prompt.ts:1180
                 ├─ 创建并持久化 assistant 消息             prompt.ts:1186-1201
                 ├─ processor.create                      prompt.ts:1213
                 ├─ SessionTools.resolve                  prompt.ts:1226-1250
                 ├─ 并行装配：sys.skills / environment /
                 │  instruction.system / sys.mcp /
                 │  MessageV2.toModelMessagesEffect       prompt.ts:1257-1263
                 ├─ system = env + instructions + mcp + skills  prompt.ts:1264-1271
                 └─ handle.process(...)                   prompt.ts:1272-1286
                      └─ processor.process               processor.ts:641-697
                           └─ llm.stream → Stream.tap(handleEvent) → runDrain
                 └─ 结果 continue | break
       └─ compaction.prune（forked）；lastAssistant        prompt.ts:1338-1339
```

### 4.3 Processor 的流事件状态机

`processor.ts` 处理的 `LLMEvent` 分支（`:280-553`）：

| 事件 | 处理 |
|---|---|
| `reasoning-start` / `reasoning-delta` / `reasoning-end` | `:280-314` |
| `tool-input-start` / `tool-input-delta` / `tool-input-end` | `:315-330` |
| `tool-call` | `:331-382` |
| `tool-result` | `:383-415` |
| `tool-error` | `:416-420` |
| `provider-error` | `:421-423` |
| `step-start` / `step-finish`（携带 snapshot hash） | `:424-434` / `:435-499` |
| `text-start` / `text-delta` / `text-end` | `:500-547` |
| `finish` | `:548-552` |

关键机制：
- **doom-loop 防护**：`DOOM_LOOP_THRESHOLD = 3`（`:29`），连续 3 次完全相同的 `(tool, input)` 触发 `doom_loop` 权限询问（`:353-380`）
- **重试**：`Effect.retry(SessionRetry.policy(...))`（`:674-688`），中断被排除在重试外（`:670-673`）并转成 `AbortedError`（`:662-669`）
- **中断清理**：`cleanup()`（`:553-612`）把被中断的工具标记 `status:"error"` + `metadata.interrupted = true`，循环后续忽略这些孤儿
- 结果类型 `Result = "compact" | "stop" | "continue"`（`:30`）

### 4.4 持久化是"事件优先"

`Session.updateMessage`（`session.ts:629-633`）与 `updatePart`（`:635-643`）**只发布事件**（`MessageUpdated` / `PartUpdated`），持久状态由 EventV2/projector 层落地。`updatePartDelta`（`:877-885`）发布 `message.part.delta` 且**完全不写库**。
读取走 keyset 分页：`MessageV2.page`（`message-v2.ts:438-480`），`Session.messages` 每页 50 并反转（`session.ts:828-851`）。

### 4.5 事件总线与 SSE

- `EventV2Bridge.publish`（`packages\opencode\src\event-v2-bridge.ts:19-33`）附加 `Location.Info` 后委托给 core `EventV2`；`:35-63` 另挂一个全局 listener 把事件重发到 Node `EventEmitter`（`packages\opencode\src\bus\global.ts:22`）供 SSE 扇出
- SSE handler：`packages\opencode\src\server\routes\instance\httpapi\handlers\event.ts:25-87` —— 先注册 listener、按 directory/workspace 过滤、首发 `server.connected`、10 秒心跳
- Part 联合类型（`packages\schema\src\v1\session.ts:357-370`）：`text | subtask | reasoning | file | tool | step-start | step-finish | snapshot | patch | agent | retry | compaction`；`ToolPart.state` 为 `pending | running | completed | error`（`:259-325`）

### 4.6 V2 的对应实现

`packages\core\src\session\runner\llm.ts`（`:43-91` 头部列出已完成/待办切片）、`runner\to-llm-message.ts`（`:70-171`）、`runner\publish-llm-event.ts`、`runner\model.ts`、`runner\max-steps.ts`。
执行入口：`packages\core\src\session\execution.ts:9-34`（`active`/`resume`/`wake`/`interrupt`），路由为 `SessionExecution.resume(sessionID) → SessionStore.get → LocationServiceMap.get(location) → SessionRunner.run`。
进程全局 `SessionRunCoordinator` 串行化同一 Session 的执行但允许不同 Session 并发（`core\src\session\run-coordinator.ts`）。

---

## 5. 系统提示与上下文组装（V1 vs V2）

### 5.1 V1：两阶段字符串拼接

**A 阶段 —— 每步并行收集上下文块**（`prompt.ts:1257-1271`，`Effect.all`）

| 块 | 内容 | 锚点 |
|---|---|---|
| `sys.environment(model)` | 模型名与 ID、`<env>`（工作目录、workspace root、是否 git 仓库、平台、日期）、`<available_references>` | `system.ts:69-105` |
| `instruction.system()` | 每个文件一个 `Instructions from: <path>` 块 | `instruction.ts:155-169` |
| `sys.mcp(agent, permission)` | `<mcp_instructions>`，按权限过滤 | `system.ts:121-137` |
| `sys.skills(agent)` | 冗长的 `<available_skills>` 清单（`skill` 被禁则整体省略） | `system.ts:107-119` |
| 结构化输出提示 | 用户请求 `json_schema` 时追加 | `prompt.ts:1271` |

**B 阶段 —— Provider 模板选择**（`llm\request.ts:58-78`）

```ts
const system = [[
  ...(input.agent.prompt ? [input.agent.prompt] : SystemPrompt.provider(input.model)),
  ...input.system,
  ...(input.user.system ? [input.user.system] : []),
].filter(Boolean).join("\n")]
```

**优先级：agent 自带 prompt > 模型专属模板 > 上下文块 > PromptInput.system。**

模板按 `model.api.id` 子串匹配（`system.ts:28-51`）：

| 匹配条件 | 模板 |
|---|---|
| 含 `muse` | `meta.txt`（替换 `{{MODEL_NAME}}`） |
| 含 `gpt-4` / `o1` / `o3` | `beast.txt` |
| 含 `gpt-6` | `gpt-astra.txt` |
| 含 `codex` | `codex.txt` |
| 其他含 `gpt` | `gpt.txt` |
| 含 `gemini-` | `gemini.txt` |
| 含 `claude` | `anthropic.txt` |
| 含 `trinity` | `trinity.txt` |
| 含 `kimi` / provider 为 moonshot | `kimi.txt` |
| 兜底 | `default.txt` |

模板差异主要是语气、冗长度与并行工具指引（如 `beast.txt` 强调"一直做到解决"；`gpt.txt` 偏好 Glob/Grep 与 `multi_tool_use.parallel`；`gpt-astra.txt` 明确解释 `<system-reminder>` 块）。
`plan.txt`、`plan-mode.txt`、`build-switch.txt` 由 `reminders.ts` 作为**合成用户文本**注入，不走 system。
插件钩子 `experimental.chat.system.transform` 可改写 `system`（`request.ts:69-78`）；OpenAI OAuth 场景下 system 被搬进 `options.instructions`（`request.ts:99`）。

**AGENTS.md 发现逻辑**（`instruction.ts:110-153`）

- 全局：`<global.config>\AGENTS.md` 与 `~\.claude\CLAUDE.md` 取首个存在者（`:60-63`、`:115-120`）
- 项目：`fs.findUp` 依次找 `AGENTS.md` → `CLAUDE.md` → `CONTEXT.md`，**首个命中即止**，因此祖先目录不会层层叠加（`:64-68`、`:122-133`）
- 配置项 `instructions[]`：绝对/相对 glob（`fs.globUp`）+ http(s) URL（5 秒超时）（`:95-103`、`:135-150`）
- **懒注入**：`read` 工具打开文件时调用 `instruction.resolve(messages, filepath, messageID)`（`:179-221`，调用点 `tool\read.ts:300`），从该文件**向上回溯**挂载就近指令文件，并用 `claims: Map<MessageID, Set<path>>` 保证每条消息只注入一次；每步结束时由 `Effect.ensuring`/finalizer 清理（`prompt.ts:691`、`:1331`）

### 5.2 V2：SystemContext 代数 + Context Epoch

V2 把系统提示从"字符串拼接"升级为**带类型的可比较状态**。

| 概念 | 定义 | 锚点 |
|---|---|---|
| `Source<A>` | `{ key, codec, load, baseline, update, removed? }` —— 独立观测的带类型值 | `core\src\system-context\index.ts:32-39` |
| `Key` | 强制命名空间格式 `^[a-z0-9][a-z0-9._-]*\/[a-z0-9][a-z0-9._/-]*$` | `system-context\index.ts:22-25` |
| `initialize` | 观测一次，产出 `Baseline System Context` + `Context Snapshot` | `system-context\index.ts:198-217` |
| `reconcile` | 观测一次，返回恰好一个动作：`Unchanged` / `Updated` / `ReplacementReady` / `ReplacementBlocked` | `system-context\index.ts:218-282` |
| `replace` | 压缩或基线替换后渲染新一代 | `system-context\index.ts:283-291` |
| `unavailable` | 陈旧可用（stale-while-revalidate）语义：保留旧值、不发更新、阻塞基线替换 | `system-context\index.ts:28-29`、`:36` |
| Registry | Location 级有序生产者集合，**重复 key 直接 die**；并发求值但按 key 排序合并以保证确定性 | `system-context\registry.ts:24-45` |
| 内置源 | `core/environment` 与 `core/date` | `system-context\builtins.ts:16-42` |

围绕它的一整套词汇（`CONTEXT.md:7-86`）：`System Context`、`Session History`、`Context Source`、`System Context Registry`、`Mid-Conversation System Message`、`Context Epoch`、`Baseline System Context`、`Context Snapshot`、`Unavailable Context`、`Safe Provider-Turn Boundary`、`Admitted Prompt`、`Prompt Promotion`、`Provider Turn`、`Session Drain`、`Model Tool Output`、`Managed Tool Output File` 等。

关键不变量（`CONTEXT.md:88-199` 精选）：
- 上下文变更**只在 Safe Provider-Turn Boundary 惰性采样并准入**，绝不因源变化而异步推送
- 多个源在同一边界准入的变更**合并为一条** `Mid-Conversation System Message`
- 已准入的 `Mid-Conversation System Message` 即使在随后 provider 尝试失败时也保持持久并原样重放
- 完成压缩会开启新 `Context Epoch`，生成全新基线；旧的中途系统消息留在审计历史但退出模型可见历史
- Session 迁移（Location move）会清空 epoch，目标 Location 必须重新初始化完整基线

---

## 6. 工具系统

### 6.1 内置工具清单（活代码所在：`packages\opencode\src\tool\`）

> 装配入口：`packages\opencode\src\tool\registry.ts:229-252`

| id | 定义锚点 | 用途 / 关键参数 | 显著行为 |
|---|---|---|---|
| `invalid` | `tool\invalid.ts:10` | 幻觉工具名占位，参数 `{tool, error}`（`:4-7`） | 永远注册（`registry.ts:232`）；描述字面为 "Do not use"；无权限询问 |
| `question` | `tool\question.ts:15` | 向用户提结构化问题，`{questions: Question.Prompt[]}`（`:6-8`） | 仅当 client ∈ {app,cli,desktop} 或 `OPENCODE_ENABLE_QUESTION_TOOL` 时注册（`registry.ts:207,233`）；agent 默认 `question: deny` 时被隐藏 |
| `bash` | `tool\shell.ts:338`（id 为兼容硬编码 `"bash"`，`tool\shell\id.ts:16`） | shell 执行，`{command, timeout?, workdir?}`（`tool\shell\prompt.ts:15-23`） | **tree-sitter（bash + PowerShell WASM）解析命令**（`shell.ts:311-336`）→ 逐目录 `external_directory` 询问（`:263-280`）+ 按 arity 前缀的 `bash` 询问（`:282-291`、`permission\arity.ts:1-9`）；默认超时 120s（`:347`）；`shell.env` 插件钩子合并环境（`:416-426`）；超限输出流式落盘（`:500-522`、`:438-580`） |
| `read` | `tool\read.ts:69` | 读文件/目录，`{filePath, offset?, limit?}`（`:28-36`） | 上限 2000 行 / 2000 字符每行 / 50 KB（`:13-17`）；目录列举；图片 PDF 转 data-URL attachment（`:306-325`）；二进制嗅探（`:182-227`）；`read` 权限用 worktree 相对模式（`:255-260`）；外部目录守卫（`:250-253`）；注入就近 AGENTS.md（`:300`、`:355-357`） |
| `glob` | `tool\glob.ts:17` | 文件发现，`{pattern, path?}`（`:10-15`） | ripgrep 后端，硬限 100 条并附截断说明（`:49-63`）；`glob` 权限（`:28-36`） |
| `grep` | `tool\grep.ts:20` | 内容检索，`{pattern, path?, include?}`（`:10-18`） | ripgrep，限 100 条，按文件分组（`:63-110`） |
| `edit` | `tool\edit.ts:59` | 字符串替换，`{filePath, oldString, newString, replaceAll?}`（`:47-56`） | **9 级模糊匹配级联**（精确 → 去行首尾空白 → 块锚点 Levenshtein → 空白/缩进/转义归一 → 边界裁剪 → 上下文感知 → 多出现）（`:694-729`）；拒绝不成比例匹配（`:731-737`）；按路径信号量（`:35-45`）；`edit` 权限携带 diff（`:145-153`）；追加 LSP 诊断 |
| `write` | `tool\write.ts:28` | 整文件写，`{content, filePath}`（`:20-25`） | 保留/同步 BOM（`:47-66`）；`edit` 权限携带 diff（`:54-62`）；报告目标文件 + ≤5 个其他文件的诊断（`:18`、`:79-90`） |
| `task` | `tool\task.ts:82`（id `"task"`，`:24`） | 派生/续接子代理，`{description, prompt, subagent_type, task_id?, command?, background?}`（`:43-62`） | 深度限制（`:104-117`）；子会话权限派生（`:139-155`）；后台模式受 `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS` 门控（`:98-102`）；registry 把允许的子代理类型清单拼进描述（`registry.ts:265-278,327`） |
| `webfetch` | `tool\webfetch.ts:25` | 抓取 URL，`{url, format: text\|markdown\|html, timeout?}`（`:13-22`） | 5 MB 上限、默认 30s / 最大 120s（`:9-11`）；HTML→markdown 用 turndown，text 用 htmlparser2（`:158-191`）；Cloudflare `cf-mitigated: challenge` 时换非浏览器 UA 重试（`:79-91`） |
| `todowrite` | `tool\todo.ts:15` | 替换会话 todo 列表，`{todos}`（`:6-8`） | `todowrite` 权限；未声明该权限的子代理默认被 deny（`agent\subagent-permissions.ts:19,24`） |
| `websearch` | `tool\websearch.ts:100` | 网络搜索，`{query, numResults?, livecrawl?, type?, contextMaxCharacters?}`（`:10-25`） | 仅当 `webSearchEnabled` 时注册（`registry.ts:58-65,293-295`）；provider（`exa`/`parallel`）由环境变量 → flag → sessionID 校验和决定（`:30-37`）；以原始 JSON-RPC/SSE over HTTP 调远程 MCP 端点（`tool\mcp-websearch.ts:69-96`） |
| `skill` | `tool\skill.ts:13` | 加载技能，`{name}`（`:8-10`） | `skill` 权限；返回 `<skill_content>` = 正文 + 基目录 + 用 ripgrep 采样的最多 10 个同级文件（`:34-61`） |
| `apply_patch` | `tool\apply_patch.ts:23` | 多文件补丁，`{patchText}`（`:18-20`） | 解析 add/update/delete/move hunk（`:72-191`）；一次携带全部文件 diff 的 `edit` 询问（`:206-215`）；**仅 `gpt-*`（排除 `oss`/`gpt-4`）时注册**（`registry.ts:297-300`） |
| `execute` | `tool\code-mode.ts:189`（常量 `"execute"`，`:12`） | 受限脚本编排 MCP 工具，`{code}`（`:16-20`） | 需 `OPENCODE_EXPERIMENTAL_CODE_MODE`（`registry.ts:118-119,246`）**且**存在非空可见 MCP 目录（`:305-308`）；开启后**取代** MCP 工具的直接暴露（`session\tools.ts:388`）；每个子 MCP 调用各自发起按 MCP 工具名的权限询问（`code-mode.ts:147`） |
| `lsp` | `tool\lsp.ts:38` | LSP 查询，`{operation ∈ 9 种, filePath, line, character, query?}`（`:11-35`） | 需 `OPENCODE_EXPERIMENTAL_LSP_TOOL`（`registry.ts:247`） |
| `plan_exit` | `tool\plan.ts:16` | 退出计划模式，`{}`（`:13`） | 需 `OPENCODE_EXPERIMENTAL_PLAN_MODE` 且 `client === "cli"`（`registry.ts:248`）；经 Question 批准后注入合成用户消息切到 `build` agent（`:46-69`） |

### 6.2 registry 之外注入的工具

| 类别 | 条件 | 锚点 |
|---|---|---|
| `list_mcp_resources` / `list_mcp_resource_templates` / `read_mcp_resource` | 某个已连接 MCP 客户端声明 `resources` 能力 | `session\tools.ts:136-139,140,222,305` |
| 全部 MCP 服务器工具 | 默认注入；Code Mode 开启时改为不注入 | `session\tools.ts:390-490` |
| 插件工具与配置目录工具 | `{tool,tools}/*.{js,ts}`（各配置目录）+ 已加载插件的 `p.tool` | `registry.ts:183-204` |

MCP 资源工具的权限模式为 `read` + `mcp:<server>:*` / `mcp:<server>:<uri>`（`session\tools.ts:180-185,263-268,343-348`）；二进制响应受 MIME 白名单与 10 MB 限制（`:32-39`、`:442-459`）。

### 6.3 工具抽象与校验

- `Tool.define(id, init)` → `Info{id, init}`（`tool\tool.ts:151-169`）；`Tool.init` 解析出 `Def`（`:171-181`）
- `Def` 形状（`:55-65`）：`{ id, description, parameters: Schema.Decoder<unknown>, jsonSchema?, execute(args, ctx), formatValidationError? }`
- `Tool.Context`（`:36-46`）：`sessionID / messageID / agent / abort / callID / extra / messages / metadata() / ask()`
- 返回形状（`:48-53`）：`{ title, metadata, output, attachments? }`
- **校验**：`wrap()` 把 `Schema.decodeUnknownEffect(parameters)` 提升为每次 init 只编译一次；失败映射为 `InvalidArgumentsError`，其 `message` getter 就是面向模型的"请重写输入"文案（`:24-34`、`:111-129`）
- **JSON Schema 生成**：`ToolJsonSchema.fromSchema`（Effect schema → draft-2020-12，`$ref` 内联、null 剥离、整数边界）（`tool\json-schema.ts:8-88`）
- 插件可通过 `tool.definition` 钩子覆盖描述与参数（`registry.ts:313-336`）

### 6.4 三层过滤

1. `registry.tools({providerID, modelID, agent, permission})` —— 按模型切换 `apply_patch` vs `edit`/`write`、门控 `websearch`、无目录时隐藏 `execute`（`registry.ts:291-308`）
2. `session\llm\request.ts:210-216` —— 丢弃被整体 deny（`pattern:"*"` + `action:"deny"`）或 `user.tools[k] === false` 的工具
3. `config.ts:567-578` —— 把遗留 `tools` 布尔映射翻译成权限条目（`patch`/`edit`/`write` → `edit`）

### 6.5 输出截断

`packages\opencode\src\tool\truncate.ts`：默认 `MAX_LINES=2000`、`MAX_BYTES=50KB`（`:14-15`），可被 `config.tool_output.max_lines/max_bytes` 覆盖（`:75-83`）。
`output()` 在双限内原样返回；超限则把完整文本写入 `<Global.data>\tool-output\tool_<id>` 并返回首部（或尾部）预览 + 提示语——**提示语会依据 agent 是否仍有 `task` 工具而不同**（有则建议委派 explore，无则建议用 Grep/Read）（`:85-141`）。保留 7 天、每小时清扫（`:12`、`:53-66`、`:143-148`）。
`Tool.wrap` 对每个内置工具自动套用，除非工具已自行设置 `metadata.truncated`（`tool\tool.ts:131-144`）；插件工具在 registry 里截断（`registry.ts:159-168`）。

### 6.6 V2 工具栈（并行实现）

- `Tool.make({description, input, output, structured?, execute, toModelOutput?})` 返回不透明冻结 `Definition`；运行时放在 `WeakMap`，暴露 `definition(name)`、`settle(call, ctx)`，可用 `Tool.withPermission` 覆盖权限（`core\src\tool\tool.ts:71-156`）
- `settle` 解码输入 → 执行 → 编码输出 →（可选）投影结构化输出；解码与编码失败都成为 `ToolFailure`（`:91-129`）
- 工具名必须匹配 `^[A-Za-z][A-Za-z0-9_-]{0,63}$`（`:134-137`）
- `ToolRegistry.materialize(permissions)` 移除被整体禁用的工具，返回 `definitions` 与 `settle`；`settle` 按注册身份**拒绝 stale/未知调用**，再经 `ToolOutputStore.bound` 兜底（`core\src\tool\registry.ts:50-140`）
- **现状**：`core\src\tool\builtins.ts:18-30` 只注册了 apply-patch / bash / edit / glob / grep / question / read / skill / todowrite / webfetch / websearch / write；TODO 明确列出 `task`、LSP、`repo_clone`、`repo_overview`、`plan_exit`、Code Mode **尚未迁移**
- 设计契约详见 `specs\v2\tools.md:1-186` 与 `packages\core\src\tool\AGENTS.md:1-59`

---

## 7. 权限模型

### 7.1 V1（生产）

**规则形态**：`{ permission, pattern, action: allow | deny | ask }`；请求 `{ id, sessionID, permission, patterns[], metadata, always[], tool? }`（`packages\schema\src\v1\permission.ts:19-36`）。

**求值**：`evaluate(permission, pattern, ...rulesets)` 对扁平化后的规则用 `findLast`，默认 `{ action: "ask", pattern: "*" }`（`packages\opencode\src\permission\index.ts:28-38`）——**最后匹配胜出，因此配置键顺序即优先级**。

**配置翻译**：`fromConfig` 把 `{key: "allow"}` 展开为 `pattern: "*"` 规则，把对象值展开为逐 pattern 规则并展开 `~/` 与 `$HOME`（`permission\index.ts:178-198`）；`merge` 就是扁平 concat（`:200-202`）。

**询问与回复**（`permission\index.ts:67-167`）：
- `ask()` 对每个 pattern 在 `ruleset ++ sessionApprovals` 上求值；命中 `deny` 立即失败并抛 `DeniedError`；任一 `ask` 则创建 `Deferred` 并发布 `permission.asked`
- `reply` 接受 `once | always | reject`：
  - `reject`：失败该 Deferred（带 message 时为 `CorrectedError`），并**批量拒绝同一会话所有其他待决请求**
  - `always`：把 `always[]` 的 pattern 作为会话级 `allow` 追加，随后**自动放行同会话中所有已被新规则完全覆盖**的待决请求
  - `once`：只放行当前请求

**工具侧接线**：`ctx.ask` 构造于 `session\tools.ts:81-89`，把 `agent.permission` 与 `session.permission` 合并。
`Permission.disabled()` 把 `edit|write|apply_patch` 归一为 `edit`、把三个 MCP 资源工具归一为 `read`，返回最终 `*`-deny 的工具集（`permission\index.ts:204-214`）；`visibleTools()` 对 MCP 工具做同样隐藏（`:216-219`）。

**内置询问来源**：
- `doom_loop` —— 处理器检测到连续相同调用（`session\processor.ts:353-380`）
- `external_directory` —— 任何实例外路径（`tool\external-directory.ts:15-45`），可用 `ctx.extra.bypassCwdCheck` 绕过

**子代理权限派生**（`packages\opencode\src\agent\subagent-permissions.ts:14-27`）：

```ts
// 只继承父会话的 external_directory 规则与 deny 规则
...parentSessionPermission.filter(r => r.permission === "external_directory" || r.action === "deny"),
// 子代理自身未声明则默认 deny
...(canTodo ? [] : [{ permission: "todowrite", pattern: "*", action: "deny" }]),
...(canTask ? [] : [{ permission: "task",     pattern: "*", action: "deny" }]),
```

`tool\task.ts:143-171` 再把 `cfg.experimental.primary_tools` 的 deny 并进来。

### 7.2 V2（并行）

| 机制 | 说明 | 锚点 |
|---|---|---|
| `Policy` | Location 级 `{action, resource, effect: allow\|deny}` 语句，`findLast` 求值 + 调用方给 fallback。**无 ask 状态**，也不被 V1 权限服务使用 | `core\src\policy.ts:8-45` |
| `PermissionV2` | 服务（`ask`/`assert`/`reply`/`get`/`forSession`/`list`）带 `evaluate`、`merge`、`BlockedError`、`DeclinedError` 与 `PermissionSaved` 持久化 | `core\src\permission.ts:76-101`、`:137-162`、`:250-283` |
| Schema | `PermissionV2.Request`、`Reply = once\|always\|reject`、`Rule{action,resource,effect}`、事件 `permission.v2.asked/replied` | `packages\schema\src\permission.ts:10-65` |
| 持久化 | `saved.ts` + `sql.ts` | `core\src\permission\` |

---

## 8. 子代理、后台任务与上下文压缩

### 8.1 子代理委派（唯一入口是 `task` 工具）

`packages\opencode\src\tool\task.ts`：

1. **深度守卫**：沿 `parentID` 链回溯，`depth >= cfg.subagent_depth ?? 1` 即报错（`:104-117`）
2. **权限询问** `task` / `subagent_type`，除非 `ctx.extra.bypassAgentCheck`（`:119-129`）
3. **子权限**：`deriveSubagentSessionPermission` + `experimental.primary_tools` deny（`:139-155`）
4. **子会话**：续接 `params.task_id`，或 `sessions.create({ parentID: ctx.sessionID, agent, permission })`（`:136-172`）
5. **执行**：`runTask` 调用 `ops.resolvePromptParts` + `ops.prompt({sessionID: child, ...})`——即子会话**递归跑完整的 `SessionPrompt.prompt → runLoop`**（`:200-225`）；`ops` 由 `prompt.ts:144-150` 注入
6. **前台/后台**：`background.start({ id: nextSession.id, type: "task", run })`（`:284-297`）；前台 await `background.wait` 并与 `waitForPromotion` **竞速**，因此任务可在飞行中升级为后台（`:328-358`）；后台完成结果以合成 `<task ...><task_result>` 用户消息注入父会话（`:227-265`、`:316-319`）

**并行的非工具路径**：斜杠命令产生的 `SubtaskPart` 走 `prompt.ts:1144-1147` → `handleSubtask`（`:255-449`），它合成 assistant/tool part 并以 `bypassAgentCheck: true` 调用同一个 task 工具。

### 8.2 后台任务

引擎在 `core\src\background-job.ts`（`:202-358`），V1 包装为实例作用域（`packages\opencode\src\background\job.ts:18-33`）。
状态机 `running | completed | error | cancelled`；`extend()` 在既有 job 后追加可运行尾巴（`task` 用来向运行中的子代理续发消息）；`promote()` 翻转 `metadata.background=true` 并触发 `onPromote`。
⚠️ **明确非持久**：进程重启即全部丢失（`core\src\background-job.ts:113-119`）。

### 8.3 上下文窗口与压缩

| 环节 | 机制 | 锚点 |
|---|---|---|
| 数学 | `usable = limit.input ? max(0, limit.input - reserved) : max(0, context - maxOutput)`；`reserved = min(20_000, maxOutputTokens)` 或 `compaction.reserved`；`total >= usable` 即溢出 | `session\overflow.ts:10-34` |
| 检测(a) | 每次 `step-finish` 调 `isOverflow` 置 `ctx.needsCompaction`，经 `Stream.takeUntil` 中断流，使 `process` 返回 `"compact"` | `processor.ts:491-496`、`:693` |
| 检测(b) | `ContextOverflowError` → `halt()` 置位；若 `compaction.auto === false` 则直接报错转 idle | `processor.ts:613-639` |
| 触发 | 追加一条带 `compaction` part 的**用户消息**（携带 `auto`/`overflow`） | `session\compaction.ts:559-582` |
| 切分 | `select` 选出待摘要 `head` 与待保留 `tail_start_id`；预算 `clamp(usable*0.25, 2000, 15000)` 或 `compaction.preserve_recent_tokens`；受 `compaction.tail_turns` 限制并可拆分超大轮次 | `compaction.ts:140-163`、`:223-269` |
| 摘要 | 就是一次普通 `SessionProcessor.process` 调用，参数 `summary: true`、`agent: "compaction"`、`tools: {}`、`system: []` | `compaction.ts:358-448` |
| 摘要再溢出 | 抛 `ContextOverflowError` 并返回 `"stop"` | `compaction.ts:450-459` |
| 自动续跑 | 成功后若 `auto`，插入合成用户消息（"Continue if you have next steps…"），除非插件禁用 | `compaction.ts:497-549` |
| 历史整形 | `filterCompacted` 重排为 `[compaction-user, summary, ...保留的 tail, continuation]` | `message-v2.ts:534-585` |
| 剪枝 | 循环结束后 `compaction.prune` 反向遍历，保护 `PRUNE_PROTECT = 40_000` token 的工具输出，清理更早的已完成输出（打 `state.time.compacted` 戳），仅当释放 ≥ `PRUNE_MINIMUM = 20_000` 才生效 | `compaction.ts:28-29`、`:273-317` |
| 剪枝呈现 | 重放时渲染为 `[Old tool result content cleared]` | `message-v2.ts:303-305`、`compaction.ts:76-78` |
| 重试 | `Schedule.fromStepWithMetadata`，上限 `RETRY_MAX_RETRIES = 5`；优先 `retry-after-ms` / `retry-after` 头，否则指数退避（2s ×2、25% 抖动、无头时 30s 上限）；状态经 `status.set({type:"retry", ...})` 外露 | `retry.ts:183-207`、`processor.ts:674-688` |

### 8.4 V2 的压缩（spec 为准）

`specs\v2\session.md:111-121`：每次 provider 轮次前估算完整可见请求并与"上下文窗口 − 绝对预留"比较，预留取"输出配额"与 `compaction.buffer` 的较大者。压缩保留完整 transcript 但把活动模型表示替换为一条隐藏 checkpoint（结构化滚动摘要 + token 受限的近期上下文序列化）；**provider 原生 assistant/reasoning/tool 消息绝不跨越边界**，以避免签名与加密推理失效。事件 `session.next.compaction.started.1` / `ended.1` 提供持久标识；溢出触发的压缩最多一次，第二次溢出即终态失败。

---

## 9. LLM / Provider 层

### 9.1 `packages\llm`（V2 协议层，21,805 行）

- **仅三个运行时依赖**：`effect`、`@opencode-ai/schema`、`aws4fetch`/`@smithy/*`（`packages\llm\package.json:45-51`）——**不依赖 AI SDK**
- ⚠️ **`packages\llm\DESIGN.md` 是未实现的改版提案**（提议新包 `@opencode-ai/ai` 与 clean break：`generate` = 完整运行、`generateTurn` = 单轮、隐藏 `Route`、`Provider.define`、`output` 取代 `generateObject`）（`DESIGN.md:1-15`、`:1052-1096`）。**现状契约以 `packages\llm\AGENTS.md:33-49` 为准**

**抽象阶梯**（依赖箭头单向向下，协议绝不 import provider，`AGENTS.md:118-159`）：

```
src\schema\*           规范 Schema 类（messages / events / options / errors / ids）
      ↓
src\llm.ts             request / turn 构造器            llm.ts:53-75、:110-186
      ↓
src\route\*            Route.make + LLMClient           route\client.ts:141-163
                       protocol / endpoint / auth / framing
                       transport\{http,websocket} / executor
      ↓
src\protocols\*        线上协议"口音"
      ↓
src\providers\*        部署门面
```

**支持的协议**（`src\protocols\index.ts:1-6`）：`openai-chat`、`openai-responses`、`anthropic-messages`、`gemini`、`bedrock-converse`（含 AWS event-stream framing）、`openai-compatible-chat`（复用 `OpenAIChat.protocol`，无规范 URL）。

`Protocol<Body,Frame,Event,State>` 拥有 `body.schema`、`body.from(request)`、`stream.event`、`stream.initial/step/terminal/onHalt`（`route\protocol.ts:36-63`）——这正是 DeepSeek/TogetherAI/Cerebras 能复用同一协议的原因（`route\protocol.ts:20-24`）。

**Route 四轴正交**：Protocol（什么 API）、Endpoint（在哪）、Auth（怎么鉴权）、Framing（怎么切字节流）（`route\client.ts:303-339`）。`streamPrepared` 执行 `transport.frames → stream.event 解码 → mapAccumEffect(stream.step)`，并把失败原因映射为类型化的 `InvalidProviderOutput`（`:279-295`）。

**请求流程**：

1. `LLM.request(input)` 规范化 `system`/`prompt`/`messages`/`tools`/`toolChoice`/`generation`/`http`（`llm.ts:53-75`）
2. `LLMClient.stream/generate`（`llm.ts:45-47`）→ `compile`：`resolveRequestOptions` 合并 route → model → request 默认值（`route\client.ts:167-180`）→ `applyCachePolicy`（`:345`）→ `route.body.from(request)` 并对 `body.schema` 校验（`:348-350`）→ `prepareTransport`（`:351`）
3. 协议状态机把帧折叠成 `LLMEvent`；`generate` 折叠为 `LLMResponse`，若未收到终态 finish 事件则失败（`:382-391`）
4. `RequestExecutor` 控制 HTTP 发送：429/503/504/529 最多 2 次重试、解析 `Retry-After`、500 ms 基 / 10 s 上限退避；对 headers、URL、body 中的 authorization/api-key/token/secret 做正则脱敏（`route\executor.ts:35-106`）

**缓存策略**：默认 `"auto"`（`undefined` 也解析为 `"auto"`），在工具定义、system、最新用户消息三处放置断点；`"none"` 关闭自动放置但手工 `CacheHint` 仍生效；对象形式则完全按调用方要求。且**整趟策略只对尊重内联缓存标记的协议执行**——即只有 `anthropic-messages` 与 `bedrock-converse`（`cache-policy.ts:18-42`；`AUTO` 见 `:18-22`，`resolve` 见 `:33-37`，`RESPECTS_INLINE_HINTS` 见 `:39-42`）。

**鉴权**：`Auth` 是带 `apply(AuthInput) → Headers` 的值；`Credential` 是惰性 `Redacted` 加载器，带 `orElse`/`bearer`/`header`（`route\auth.ts:25-52`）。来源可以是字面值、`Redacted` 或 `Effect Config`（`Auth.config(name)`，`:92`）。`AuthOptions.bearer` 的优先级为**显式 `auth` 覆盖 → `apiKey` → `Config` 环境变量**，缺键时产生类型化 `AuthenticationReason` 而非崩溃（`route\auth-options.ts:47-55`、`route\auth.ts:137-154`）。Bedrock SigV4 与缓存辅助在 `src\protocols\utils\bedrock-auth.ts` / `bedrock-cache.ts`（**未逐行阅读**）。

**Provider 门面**（`src\providers\index.ts:1-11`）：Anthropic、AmazonBedrock、Azure、Cloudflare（AIGateway + WorkersAI）、GitHubCopilot、Google、OpenAI、OpenAICompatible、OpenRouter、XAI。
OpenAI 声明三条 route（`OpenAIResponses.route`、`webSocketRoute`、`OpenAIChat.route`），`configure({apiKey, baseURL, queryParams, providerOptions})` 在选模型前绑定 auth 与 endpoint（`providers\openai.ts:10-63`）。
通用兼容 profile 追加 baseten、cerebras、deepinfra、deepseek、fireworks、groq、openrouter、togetherai、xai（`providers\openai-compatible-profile.ts:6-15`、`providers\openai-compatible.ts:54-65`）。

**工具调用归一化**：`Tool.make` 接受 Effect Schema 或原始 `jsonSchema`（MCP 场景），预计算 `_decode`/`_encode`/`_project` 与 `ToolDefinition`（`src\tool.ts:133-206`）；`toDefinitions` 以 record key 作为线上名（`:221-230`）。协议必须发出 `tool-input-delta` 再发最终带解析输入的 `tool-call`（`AGENTS.md:202`）。`ToolRuntime.dispatch(tools, call)` 只执行**恰好一个**调用（解码 → 执行 → 编码 → 投影），返回规范 `tool-error` + `tool-result` 事件，**刻意不做流式、调度、持久化或续跑**（`tool-runtime.ts:23-76`）。Provider 托管工具以 `providerExecuted: true` 标识，本地必须跳过（`AGENTS.md:248-254`）。测试为 cassette 驱动（`AGENTS.md:292-321`）。

### 9.2 core 侧 AI SDK 与 Provider 管线

| 文件 | 职责 | 锚点 |
|---|---|---|
| `core\src\aisdk.ts` | 把 `ModelV2.Info` 变成 `LanguageModelV3`：插件钩子 `sdk`（返回 AI SDK provider 对象）与 `language`（选择如 `sdk.responses(id)`），按 `provider/model/variant` 记忆化；`prepareOptions` 注入 baseURL、挂带 chunk-idle 超时的自定义 fetch，并剥除 OpenAI/Azure/Bedrock Responses body 里的消息 `id` | `:198-229`、`:74-122` |
| `core\src\catalog.ts` | Provider+Model 注册表；可用性要求 body 带 `apiKey`、存在已连接的 integration，或该 provider 本就不需要 integration（`:71-76`）；`finalize` 丢弃被 `provider.use` 策略拒绝的 provider 并发布 `Catalog.Event.Updated`（`:160-169`）；`model.small()` 是按成本/年龄加权的启发式（`:234-286`） |
| `core\src\session\runner\model.ts` | V2 桥：`supported()` 仅放行 `@ai-sdk/openai`、`@ai-sdk/anthropic`、`@ai-sdk/openai-compatible`（需 URL）（`:175-179`）；映射到 `OpenAIResponses.route`(bearer) / `AnthropicMessages.route`(`x-api-key`) / `OpenAICompatibleChat.route`(bearer)（`:142-170`）；凭证转 `Auth.value`（`:83-88`）；variant 并入请求 header/body（`:104-126`） |
| `core\src\session\runner\llm.ts` | V2 agent loop：解析模型 → 载入历史与系统上下文 → 每次迭代调**一次** `llm.stream(request)` → 持久化增量 → 结算工具 → 续跑 | `:43-91`、`:97` |
| `core\src\session\runner\to-llm-message.ts` | 把每个 V2 消息变体（user/assistant/synthetic/system/shell/compaction）翻译为规范 llm 消息；仅当 assistant 轮次使用同一模型且无错误时才复用 provider 元数据 | `:70-113`、`:115-171` |
| `core\src\models-dev.ts` | 从 `https://models.opencode.ai/api.json` 拉取目录；5 分钟文件 TTL、跨进程 `Flock`、原子临时改名写入、60 分钟后台刷新；`OPENCODE_MODELS_PATH` / `OPENCODE_DISABLE_MODELS_FETCH` | `:160-258` |
| `core\src\github-copilot\` | 手写的 AI SDK `LanguageModelV3` provider（`createOpenaiCompatible`），含 chat 与 responses 构造器 | 接入点 `packages\opencode\src\provider\provider.ts:172-173` |

### 9.3 V1 Provider/Auth 胶水（仍在生产路径）

| 文件 | 职责 | 锚点 |
|---|---|---|
| `packages\opencode\src\provider\provider.ts`（2094 行） | AI SDK 时代的 Provider 注册表：`BUNDLED_PROVIDERS` 懒加载 26 个 SDK（`:148-175`）；`custom(dep)` 提供逐 provider 的 autoload/auth/模型选择；**Bedrock** 区域优先级 config > `AWS_REGION` > `us-east-1`，再 profile、`AWS_BEARER_TOKEN_BEDROCK`，最后 `fromNodeProviderChain`（`:336-395`）；**Google Vertex** 项目/区域先 config 后 `GOOGLE_VERTEX_PROJECT`/`GOOGLE_CLOUD_*`，用 `google-auth-library` ADC 签名（`:544-593`）；另有逐 fetch 超时与 SSE-idle 包装（`:96-127`） |
| `packages\opencode\src\auth\index.ts` | 把 `{type: oauth\|api\|wellknown}` 记录持久化到 `<Global.data>\auth.json`，权限 `0600`，支持 `OPENCODE_AUTH_CONTENT` 测试注入（`:10-95`、`:59-63`） |
| `packages\opencode\src\provider\auth.ts` | 暴露插件声明的 oauth/api 鉴权方法，跑交互式 authorize/callback 流程并写回 auth store（`:109-224`） |
| `packages\opencode\src\session\llm.ts` | `AGENTS.md` 点名的接缝：在 AI SDK 路径与 `LLMClient` native route 之间选择，并把两者归一为 `LLMEvent`（`:9-31`、`:85-90`）；适配器在 `session\llm\{ai-sdk,native-request,native-runtime,request}.ts` |

运行时选择（`packages\opencode\src\session\llm\AGENTS.md:34-90`）：AI SDK 为默认；`OPENCODE_EXPERIMENTAL_NATIVE_LLM=true` 或伞形 `OPENCODE_EXPERIMENTAL=true` 开启 native；native 目前仅支持 OpenAI、opencode 托管的 OpenAI 兼容、Anthropic API-key 路径；不支持的 provider、OpenAI OAuth、缺 API-key 均回落 AI SDK。**两者输出同一个 `LLMEvent` 流，下游 processor 不感知差异**。

---

## 10. 客户端与服务层

### 10.1 进程架构：不是单体

`packages\opencode` 是**三模态进程**：

| 模态 | 说明 | 锚点 |
|---|---|---|
| CLI | 单个 yargs CLI 注册 ~22 个子命令 | `packages\opencode\src\index.ts:45-116` |
| HTTP 守护进程 | Effect `HttpApi` + SSE + WebSocket(PTY) | `packages\opencode\src\server\server.ts:56-65`、`:73-98` |
| 内嵌服务器 | Electron `utilityProcess` sidecar，或 TUI 的 Worker 线程 | `packages\desktop\src\main\server.ts:57-70`、`packages\opencode\src\cli\cmd\tui.ts:210-249` |

CLI 分派是两层：`cli\cmd\cmd.ts` 是 yargs `CommandModule` 的薄类型别名；`cli\effect-cmd.ts:71-108` 的 `effectCmd` 包装器把 handler 变成 Effect 并在 `AppRuntime.runPromise` 下执行，可选先加载按目录的 `InstanceContext`（`InstanceStore.Service.load({directory})`，作为 `InstanceRef` 提供，`finally` 中释放）。`instance: false` 完全跳过项目引导——`serve`/`web`/`models`/`db` 使用，理由是服务器改为按请求的 `x-opencode-directory` 头加载实例（`cli\cmd\serve.ts:10-13`）。错误以 `CliError` 外露（`effect-cmd.ts:14`）。
`src\index.ts:136-141` 的 `finally { process.exit() }` 是刻意为之：防止 docker 型 MCP 子进程挂住进程。

### 10.2 路由树（五段式）

出处：`packages\opencode\src\server\routes\instance\httpapi\server.ts:130-181`

1. `RootHttpApi` —— `/global/*`、`/auth`、`/log`
2. `EventApi` —— SSE
3. `PtyConnectApi` —— WebSocket 升级
4. `InstanceHttpApi` —— 其余全部
5. `@opencode-ai/server` 的 V2 `Api`（`/api/*`）+ `GET /doc`（OpenAPI）+ 原始兜底 `/*` 服务内嵌 Web UI（`:194-203`、`packages\opencode\src\server\shared\ui.ts`）

服务端还构建 `WebSocketTracker`，在 `stop(true)` 时强制关闭 socket（`server.ts:196`）；端口 0 回落到 4096 再回落任意端口（`:117-122`）；另有 mDNS 发布（`server\mdns.ts`）。

### 10.3 传输层

| 传输 | 用途 | 锚点 |
|---|---|---|
| HTTP | 主传输；V2 面为 Effect `HttpApi`，错误用声明的 `Schema.ErrorClass` | `packages\opencode\src\server\routes\instance\httpapi\AGENTS.md:37` |
| SSE | 事件流：`HttpApiSchema.StreamSse`（`packages\protocol\src\groups\event.ts:35-36`，`GET /api/event`）；旧版 handler 手工编码 `text/event-stream`，首发 `server.connected`、10 秒 `server.heartbeat`、`server.instance.disposed` 终止 | `packages\opencode\src\server\routes\instance\httpapi\handlers\event.ts:63-85` |
| WebSocket | **仅用于 PTY I/O**：`handleRaw` 升级路由 + 基于 ticket 的鉴权中间件 | `groups\pty.ts:33-45`、`handlers\pty.ts`、`websocket-tracker.ts` |

⚠️ **已知架构缺口**：`packages\opencode\src\server\routes\instance\httpapi\public.ts:155-171` **手工给 OpenAPI spec 打补丁**，因为 "HttpApi 没有一等的 SSE 响应 schema"。

### 10.4 API 契约的生成链

依赖方向由 `AGENTS.md:3` 强制。

- **Protocol**：`makeApi(...)` 返回 `HttpApi.make("server")` 并挂 18 个 group（`packages\protocol\src\api.ts:37-64`）；它接收 location/session-location 中间件的**key**作为参数，以把 Core 服务身份留在下游（注释 `:25`）。Group：health、location、agent、session、message、model、provider、integration、credential、permission、fs、command、skill、event、pty、question、reference、projectCopy。V2 路径为 `/api/...`，operation id 形如 `session.prompt`、`session.events`、`session.interrupt`、`session.compact`、`session.switchAgent/Model`、`session.revert.{stage,clear,commit}`、`session.message`、`session.history`、`session.context`
- **Server**：`makeDefaultApi({locationMiddleware, sessionLocationMiddleware})`（`packages\server\src\api.ts:5-8`），`makeRoutes()` 组装 `HttpApiBuilder.layer(Api, { openapiPath: "/openapi.json" })` + handler + 中间件 + `AppNodeBuilder` 服务图（含 `SessionExecution.node ← SessionExecutionLocal.node`）（`packages\server\src\routes.ts:26-63`）；`createEmbeddedRoutes()` 是 sdk-next 用的无密码变体
- **`packages\opencode` 自己的 HttpApi 才是权威且更大**：`RootHttpApi` + `InstanceHttpApi` + `EventApi` + `PtyConnectApi` + 引入的 V2 `ServerApi`（`httpapi\api.ts:48-94`）。`PublicApi` 用 `transform: matchLegacyOpenApi` 为 Hey-API 兼容性改写 spec（`public.ts:82-178`、`:530-537`）
- **Client**：`ClientApi` 由 Protocol 构建，但使用客户端本地中间件服务类（`packages\client\src\contract.ts:5-17`），另有 `groupNames`（如 `server.session` → `sessions`）、`endpointNames` 重命名、`omitEndpoints = {fs.read, pty.connect, pty.connectToken}`（`:19-53`）
- **Codegen**：`compile(ClientApi, ...) → emitPromise(contract) → src\generated`、`emitEffectImported(contract) → src\generated-effect`，Prettier 格式化（`packages\client\script\build.ts:7-29`）；`check:generated` 重新生成并 `git diff --exit-code`。**两个发射器、一个 IR**：Promise 为零 Effect、用 `fetch`、结构类型、惰性 `AsyncIterable`、单一 `ClientError`；Effect 为解码后的域值、运行时 schema、`HttpApiClient`、`Stream`
- **sdk-next**：`OpenCode.create()` 构建 Core 的 `ApplicationTools`/`PermissionSaved` 节点图，用 `HttpRouter.toWebHandler` 包裹 `createEmbeddedRoutes()`，把 handler 作为伪 `globalThis.fetch` 注入生成的 Effect 客户端，并把 `tools.register` 摊到客户端上（`packages\sdk-next\src\opencode.ts:10-43`）。**无监听器、无网络 I/O、作用域化释放**
- **旧版 SDK**：`packages\sdk\js` 先在 `packages\opencode` 跑 `bun dev generate` 产出 `openapi.json`，再用 `@hey-api/openapi-ts` 生成到 `src\gen` 与 `src\v2\gen`。TUI（`@opencode-ai/sdk/v2`）、app、plugin、slack 仍在使用

### 10.5 各客户端

| 包 | 说明 | 关键锚点 |
|---|---|---|
| `packages\tui` | `@opentui/solid` 把 SolidJS 渲染到终端。Provider 树（SDK/Sync/Data/Local/Project/Permission/Theme/KV/Dialog/Toast/Args）。仅两条路由：`routes\home.tsx` 与 `routes\session\index.tsx`（2705 行）。**键位系统带模式栈 + 定时 leader**（leader 默认 `ctrl+x`），默认表在 `config\keybind.ts`（471 行，schema 校验）。传输用**旧版 SDK** `createOpencodeClient`，订阅 `sdk.global.event({sseMaxRetryAttempts:0})` 并迭代 `.stream`，16 ms 批处理 + 1s→30s 指数退避 | `src\app.tsx:1`、`:8-88`；`src\keymap.tsx:53-100`、`:214-244`、`:260-289`；`src\context\sdk.tsx:82-117`、`:119-132` |
| TUI 启动模型 | `cli\cmd\tui.ts:210-249` 在 **`Worker` 线程**里托管服务器（`cli\tui\worker.ts` 内 `Server.Default().app.fetch`），主线程通过 RPC fetch shim（`:24-40`）与事件 shim（`worker.ts:24-26`）访问；传 `--port/--hostname/--mdns` 则切换为真实外部 HTTP 服务器（`:238-249`）；`--mini` 走 `cli\cmd\run.ts` 的 split-footer 直连模式 | `cli\cmd\tui.ts:24-40`、`:210-249` |
| `packages\app` | Vite + SolidJS SPA（**非 SolidStart**）。路由是手写 `@solidjs/router` 表，位于 `newLayoutDesigns()` 特性开关之后。通信为**双协议**：`context\server-sdk.tsx` 检测 v1/v2 后分别从 `sdk.global.event()`（旧）或 `client.event.subscribe()`（新）取流，再把 V2 事件规范化为旧形状（`:29-53`），16 ms 帧预算合并 + 250 ms 重连。E2E 用 Playwright，含大量 `e2e\performance\` 基准 | `src\entry.tsx:164-178`、`src\app.tsx:615-646`、`src\context\server-sdk.tsx:275-279` |
| `packages\desktop` | **Electron**（非 Tauri），`electron-vite` + `electron-builder`。opencode 服务器**打包进应用**并在 `utilityProcess` sidecar 中运行：`main\server.ts:57-70` fork `sidecar.js`（`serviceName: "opencode server"`），`sidecar.ts:57` 执行 `await import("virtual:opencode-server")`，由 `electron.vite.config.ts` 别名到 `..\opencode\dist\node\node.js`。含 electron-updater、electron-store、WSL 支持、60+ 渲染层 i18n locale | `src\main\server.ts:57-70`、`src\main\sidecar.ts:57`、`electron.vite.config.ts` |
| `packages\codemode` | "Effect 原生的、面向 schema 描述工具的受限代码执行"：沙箱 JS 解释器（`interpreter\runtime.ts`、`interpreter\model.ts`）+ 精选 `stdlib\`（collections/date/json/math/number/object/promise/regexp/string/url）+ OpenAPI 工具面 | `packages\codemode\AGENTS.md:1-23` |
| `packages\cli` | **第二个 CLI**（bin 名 `lildax`），Effect 原生，含 `service start/stop/restart/status/password` 守护进程控制；用 `Bun.build({compile})` 编译全平台单文件（含 musl 与非 AVX2 目标） | `packages\cli\src\commands\commands.ts`、`framework\runtime.ts`、`services\daemon.ts` |
| `packages\session-ui` | app 与 enterprise 共用的会话渲染组件（69 组件 + `pierre\` diff 集成 + `v2\` 含 prompt-input） | `packages\session-ui\AGENTS.md:1-7` |
| `packages\ui` | 设计系统：136 组件、50 主题、62 个 i18n 模块、1317 资源文件、Tailwind 4、Kobalte、motion、shiki/marked | `packages\ui\AGENTS.md:1-15` |
| `packages\web` | 公开营销/文档站，**Astro + Starlight**（与 `packages\app` 不同） | `packages\web\astro.config.mjs` |
| 辅助 | `function` 是 Cloudflare Worker（Hono + `SyncServer` Durable Object + R2 + GitHub App 鉴权）；`stats`/`console`/`enterprise` 是独立分析站与控制台产品（SolidStart）；`identity`/`docs`/`containers` **无 package.json**，非 workspace 成员（分别是品牌资源、Mintlify 文档、CI 镜像） | — |

---

## 11. V1 → V2 迁移状态

### 11.1 权威 parity 检查表

出处：`specs\v2\session.md:123-152`（状态含义：`complete` = V2 原生路径可用；`partial` = 只覆盖 V1 部分行为；`missing` = 无 V2 等价物）。

| 边界 | 行为 | 状态 | 待办 |
|---|---|---|---|
| Durable Context Source | 环境事实与主机本地日期 | partial | 加入所选 provider/model 身份，且不要让它成为陈旧的 Location 级值 |
| Durable Context Source | 全局与向上项目指令 | partial | 决定 V2 是否也发现遗留 `CLAUDE.md` 与废弃的 `CONTEXT.md` |
| Durable Context Source | 配置的本地/glob 与远程 URL 指令 | **missing** | 需带显式优先级、不可用与移除语义的独立源 |
| Durable Context Source | 成功读取后发现的邻近嵌套指令 | **missing** | 持久化发现结果并在下个安全边界准入 |
| Durable Context Source | 所选 agent 的可用技能指引与技能正文加载 | partial | 指引与正文已按权限过滤；需在请求期工具物化时移除全局被禁的技能定义 |
| 逐轮请求装配 | 布局、所选模型、时序历史、规范降级 | **complete** | 无 |
| 逐轮请求装配 | 所选 agent、agent prompt、生效权限 | partial | V2 已用 agent 权限做技能指引与工具授权；仍需应用 agent 系统提示与请求策略 |
| 逐轮请求装配 | Provider/模型专属基础指令 | **missing** | 选择 provider 家族基线，除非生效 agent 覆盖 |
| 逐轮请求装配 | 按策略过滤的内置/MCP/插件/结构化输出工具 | partial | 需为生效 agent 与请求物化定义 |
| 逐轮请求装配 | 逐 prompt 的系统文本与工具覆盖 | **missing** | 先设计准入与持久重放语义 |
| 逐轮请求装配 | 引导、plan/build 切换、末步提醒 | **missing** | 只加入仍属于 V2 的提醒 |
| 逐轮请求装配 | 插件 message/system/parameter/header 变换 | **missing** | 需设计 V2 插件钩子与生命周期语义 |
| 逐轮请求装配 | 模型变体与请求设置 | partial | 应用生效 agent 选项与未来插件改写的请求设置 |
| 逐轮请求装配 | 结构化输出策略 | **missing** | 需同时加入提示格式、生成工具、工具选择与模型可见策略 |
| 逐轮请求装配 | 自动/上下文压力压缩 | **complete** | 无 |
| Prompt/reference 展开 | 持久类型化 prompt 附件 | **complete** | 无 |
| Prompt/reference 展开 | 原生模板与 `@` 提及展开 | **missing** | 在持久准入前解析原生 V2 prompt 输入 |
| Prompt/reference 展开 | 文件、目录、媒体与 MCP 资源物化 | partial | 物化并规范化来源，而非降级未解析的附件元数据 |
| Prompt/reference 展开 | Agent 引用展开 | **missing** | 产出权限感知的模型可见 task 指引 |
| Prompt/reference 展开 | 配置引用展开 | **missing** | 解析别名并产出持久模型可见引用上下文或失败 |
| Prompt/reference 展开 | 原生合成展开重放 | partial | V2 会重放合成消息，但只有 V1 兼容路径会创建它们 |

**明确延后**的设计（`specs\v2\session.md:153-185`）：provider 超时/重试/看门狗策略、崩溃后 continuation 恢复、事件重放 owner claim 与集群化执行所有权、provider 托管工具结果的上下文控制。

### 11.2 V2 工具迁移缺口

`packages\core\src\tool\builtins.ts:18-30` 目前只注册：apply-patch、bash、edit、glob、grep、question、read、skill、todowrite、webfetch、websearch、write。
文件内 TODO 列出**尚未迁移**：`task`、LSP、`repo_clone`、`repo_overview`、`plan_exit`、Code Mode。
另两个公开缺口（`packages\core\src\tool\AGENTS.md:55-59`）：插件启动尚未改为通过 `Tools.Service` 注册规范工具；MCP 与未来 Session 作用域注册仍需显式设计。
公开 Session 结果形状仍暴露受管 `outputPaths`，完全封装需要未来的不透明受管输出引用设计（`specs\v2\tools.md:182-186`）。

### 11.3 核心结论

> **V1 仍是生产路径。** V2 在"请求装配 + 自动压缩 + 附件持久化"上已完整，但在系统提示、工具覆盖面、插件钩子、prompt 展开这几个最贴近用户体验的面上仍是 `missing`。双栈并存可能持续较久。

---

## 12. 设计亮点与风险

### 亮点

1. **Effect 优先的依赖注入**——每个服务都是 `Context.Service<Service, Interface>()("@opencode/X")` + `Layer.effect` + 文件底部 `LayerNode.make({ service, layer, deps })`（如 `session\prompt.ts:1598-1629`、`session\processor.ts:713-730`）。`SessionPrompt.node` 的约 25 个依赖本身就是最清晰的运行时依赖图。`serviceUse(Service)` 是取用惯用法（`session\session.ts:476`、`session\llm.ts:60`）。
2. **运行时无关的适配层**——AI SDK 路径与 native LLM 路径都归一到同一个 `LLMEvent` 流，`processor.ts` 完全不感知谁在执行（门控在 `session\llm.ts:226-269`，边界文档 `session\llm\AGENTS.md:1-90`）。安全边界清晰：native 是 opt-in 且只在受支持 provider 上生效，其余回落。
3. **系统提示升级为上下文代数**（V2）——把"提示词"从字符串拼接变成可比较、可增量、可审计、可持久重放的带类型状态（`core\src\system-context\index.ts`），并配以 `Context Epoch` 保护 provider 缓存前缀。
4. **命令解析驱动权限**——用 tree-sitter（bash + PowerShell WASM）解析 shell 命令来精确推导目录访问询问，而非字符串匹配（`tool\shell.ts:311-336`）。
5. **事件优先的持久化**——写路径只发布事件（`session\session.ts:629-643`），增量完全不落库（`:877-885`），由 projector 统一落地，天然支持重放与客户端乐观更新。
6. **显式运行状态机**——`effect\runner.ts:33-37` 定义 `Idle | Running | Shell | ShellThenRun`，使"先起 shell 再跑 LLM 循环"成为一等的状态而非特例（`run-state.ts:35-107`）。
7. **双发射器单 IR 的 SDK 生成**——`compile → SDK Contract IR → emitPromise / emitEffect`，两个客户端可各自选择公共值模型与运行时解释器，同时用等价性测试守卫传输漂移。

### 风险

1. **双栈并存的认知成本**——V1/V2 各有 Agent、Session、Tool、Permission 服务，命名相近（`Agent` vs `AgentV2`、`Permission` vs `PermissionV2`、`tool\registry.ts` vs `core\tool\registry.ts`），迁移中间态可能持续较久。
2. **`packages\llm\DESIGN.md` 是提案而非文档**——它描述了一个未实现的 `@opencode-ai/ai` 包与 clean break。误读会得出错误结论，现状契约只看 `packages\llm\AGENTS.md`。
3. **OpenAPI spec 手工打补丁**——`public.ts:155-171` 因为 Effect `HttpApi` 没有一等的 SSE 响应 schema 而手改 spec，这是为兼容旧生成器而留的技术债。
4. **后台任务非持久**——`core\src\background-job.ts:113-119` 明确注明进程重启即丢失，与前台的持久事件模型形成反差。
5. **压缩与剪枝参数是硬编码常量**——`COMPACTION_BUFFER`、`PRUNE_PROTECT = 40_000`、`PRUNE_MINIMUM = 20_000`、`RETRY_MAX_RETRIES = 5`、`DOOM_LOOP_THRESHOLD = 3` 均无配置出口（部分有 config 覆盖，部分没有）。
6. **`specs\v2\session.md:173` 的自我披露**：V2 的"急切本地工具执行"目前**无上界**，在扩大暴露面之前需要重新审视每轮调用上限、输出截断与运维背压。

---

## 13. 未确认项与已知缺口

以下条目由分析者明确标注为**未验证**，引用时请留意。

### 13.1 代码健康度疑点

| 项 | 说明 | 锚点 |
|---|---|---|
| `session\message.ts` 疑为死代码 | 定义了旧的 `Message`/`MessagePart` 形状，全仓未找到导入方；可能仅供 `opencode/session/message` 公共类型面使用 | `session\message.ts:86-146`；疑似消费者 `packages\web\src\components\Share.tsx:9` |
| `RetryPart` 无生产者 | 存在于 Part 联合类型中，但唯一的重试机制是 `SessionStatus {type:"retry"}` | `packages\schema\src\v1\session.ts:220`；`processor.ts:679-685` |
| `Session.diff` 是桩 | 直接返回 `[]` 并用 `void sessionID` 吞参；真实 diff 来自 `SessionSummary.computeDiff/diff` | `session\session.ts:823-826` |
| `permission.ask` 插件钩子无触发点 | 仅在类型中声明，`packages/` 全树未找到调用点 | 声明 `packages\plugin\src\index.ts:261` |
| `plan_enter` 权限无对应工具 | 是已配置的权限键且被 CLI run 命令询问，但没有任何 `plan_enter` 工具注册 | `agent\agent.ts:127,149`；`cli\cmd\run.ts:439` |
| `core\src\v2-schema.ts` | 2 行的残留导出，用途未能确定 | — |
| 工具并行度是推断 | 未找到 opencode 侧的串行化；每个 `execute` 返回 `EffectBridge` promise，AI SDK 在调用到达时派发，故推断同一步内多工具并发。**代码与注释均未明示** | `session\tools.ts:103` |

### 13.2 未逐行阅读的部分

- `packages\llm\src\protocols\utils\bedrock-auth.ts` / `bedrock-cache.ts`
- `packages\llm\src\providers\` 下的 Bedrock / Anthropic / Google / Azure / Copilot 门面（按用法与同类文件归纳）
- `packages\core\src\git.ts`
- `packages\opencode\src\cli\cmd\run.ts` 的 "interactive attach" 模式（仅读了文件头注释 `:1-14`）
- `packages\opencode\script\build.ts` 的 `Bun.build` compile 目标列表（抽样前 80 行）
- `packages\console` 与 `packages\stats`（按要求仅做目录/manifest 级考察）

### 13.3 环境与行为未确认

- `packages\app` 的 `newLayoutDesigns()` 开关是否默认开启
- 是否有服务器入口在使用 V2 工具栈；`packages\core\src\tool\*` 与 `packages\plugin\src\v2\*` 看起来是进行中的移植
- `packages\opencode\src\agent\agent.ts`（V1 Agent）是否有删除计划——任何读到的文档都未说明
- `packages\stats\server` 目录存在，但 `stats\README.md` 只描述了 `app`/`core`/`function`，故未分类
- `packages\protocol` **没有** AGENTS.md（只有 `packages\schema` 与 `packages\opencode\src\server\routes\instance\httpapi` 有）；protocol/server 的分工是从 `packages\protocol\src\api.ts:25` 与 `packages\client\README.md` 的明文陈述推断的
- 所有行号锚点取自当前工作树，**未执行构建或测试**，因此描述的是"读了什么"而非"跑起来是什么"

### 13.4 值得优先跟进的源码入口

| 想了解 | 从这里开始 |
|---|---|
| V1 一轮对话到底怎么跑 | `packages\opencode\src\session\prompt.ts:1052-1343` |
| 流事件如何变成消息 | `packages\opencode\src\session\processor.ts:98-712` |
| 系统提示如何拼出来 | `packages\opencode\src\session\llm\request.ts:58-78` + `session\system.ts:28-137` |
| 权限为什么放行/拦截 | `packages\opencode\src\permission\index.ts:28-167` |
| 工具清单与门控 | `packages\opencode\src\tool\registry.ts:229-340` |
| V2 上下文代数 | `packages\core\src\system-context\index.ts:1-291` |
| V2 agent loop | `packages\core\src\session\runner\llm.ts` + `specs\v2\session.md:1-231` |
| 迁移到哪一步了 | `specs\v2\session.md:123-152`（parity 表） |
| 仓库约定与风格 | `AGENTS.md:1-161`、`packages\opencode\AGENTS.md:1-131` |
| 架构词汇表与不变量 | `CONTEXT.md:1-225` |

---

*本文档由源码只读分析汇总生成，未修改仓库中任何文件。行号对应分析时的当前工作树。*
