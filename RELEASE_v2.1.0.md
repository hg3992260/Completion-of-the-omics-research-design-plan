# v2.1.0 —— GUI 启动即联动内核 + 项目 ↔ 会话绑定

> 在 v2.0.0「内核已嵌入」的基础上，把两条此前需要手动触发的联动改成**自动**，
> 并修掉两个只在控制台用法下才会暴露的内核进程管理 bug。
> 完整设计见 [`opencode-embedding-plan.md`](opencode-embedding-plan.md) §9.7 / §9.8。

---

## 一句话

打开 GUI 程序，opencode 就同时起来了 —— 它的界面直接显示在**独立终端窗口**里
（Windows 新控制台 / macOS Terminal 的 bash）；在 GUI 上换项目，那个终端里的
opencode 会跟着**新建或切换**到对应的 session。于是你可以在那个终端里对 opencode
下全自动命令，让它调用本程序的 21 个组学领域工具，驱动本程序完成操作。

---

## 新增

### 1. 打开 GUI 即启动内核，并显示为系统 console / mac bash

`design_studio` 在 `win.show()` 之后调用 `StudioWindow.kernel_boot_async()`，
新增的 `kernel_boot.py` 负责整条链路：

```
起内核  →  把本程序注册成它的 MCP 服务（方向 A）
        →  绑定当前项目的 session
        →  在独立终端窗口里 attach 同一实例
```

| 平台 | 终端窗口 |
|---|---|
| Windows | `CREATE_NEW_CONSOLE` + PowerShell 执行 `opencode attach <url>` |
| macOS | `osascript` 让 `Terminal.app` 执行同一条 attach（得到 bash） |
| Linux | 回落为在当前终端里直接 spawn |

全程**后台线程**，不阻塞首屏。`--shot` / `--e2e` / `--demo` 三种自动化模式
**自动跳过**，不会干扰既有的自检脚本。

### 2. GUI 切项目 → 内核新建或切换对应 session

项目 ↔ session 映射存在 `<程序目录>/opencode/projects.json`（已 gitignore）。
`_switch_project()` 是所有项目切换的唯一汇聚点，在其末尾挂载；
`KernelBoot.ensure_project_session()` 复用已有 session，不存在才新建，
并让终端界面重新 attach 到该 session。

实测：

| 操作 | 结果 |
|---|---|
| 首次 `ensure 胰腺囊性病变_影像组学` | `created=true` → `ses_edc59952effe…` |
| 再次同名 | `created=false`，**sessionID 不变**（复用） |
| 换 `肝细胞癌_多组学预后` | `created=true` → 另一个 session，互不干扰 |

### 3. 控制台对等命令

与「打开 GUI 时自动发生的动作」完全同一件事，便于复现与排障：

```bat
PCLRadiomics.exe kernel boot --project "某课题"    :: 起内核+注册MCP+绑会话+开终端
PCLRadiomics.exe kernel project list               :: 项目 ↔ session 映射
PCLRadiomics.exe kernel project ensure --name X    :: 确保 X 有 session（复用或新建）
PCLRadiomics.exe kernel project switch --name X    :: 同上，并让终端跟过去
PCLRadiomics.exe kernel project unbind --name X
python kernel_boot.py                              :: 离线自检（开关/映射/二进制/方向A）
```

### 4. 开关

| 环境变量 | 默认 | 作用 |
|---|---|---|
| `PCL_KERNEL_AUTOSTART` | `1` | GUI 启动时是否拉起内核 |
| `PCL_KERNEL_TUI` | `1` | 是否自动弹出内核终端窗口 |
| `PCL_SKIP_KERNEL` | `0` | 打包时是否排除内核二进制 |

---

## 修掉的问题

### 1. 每敲一条 `cli.py kernel …` 就多一个内核进程

实测连跑三条命令留下 **3 个**内核进程（各占 300+ MB）。

**根因**：`ensure_running()` 里的 `cleanup_stale()` 只"报告复用"，从不真正
**接管**状态文件里那个存活实例，于是每次都再 spawn 一个。GUI 是长驻进程所以
看不出来，控制台用法会一路漏。

**修法**：新增 `adopt_state()` —— 状态文件里的实例存活且 health 通过就直接接管。
复测：第 2、3 次 ensure 进程数**保持不变**。

### 2. `kernel stop` 跨进程停不掉内核

报 `无运行中的内核`，但内核其实还在跑。

**根因**：`stop()` 只看 `self._proc`（本进程句柄）；`cli.py kernel stop` 是新进程，
句柄是 `None`，状态文件里的 pid 被忽略。

**修法**：无句柄时退回 `adopt_state()` 并按强杀处理，同时删除状态文件。
复测输出 `已停止 pid=31492`，且状态文件被正确清理。

### 3. CI：windowed 产物不能用 `$LASTEXITCODE` 判退出码

`build-windows` 在「校验产物」步骤反复失败，日志里 `throw "冻结包里
manuscript_review 子模块不齐备"` 的**下一行**却打印着
`结果：11/11 个子模块全部可导入。` —— 检查读到了残留的退出码。

**根因**：主程序是 **GUI（windowed）子系统**。当它的 stdout 是继承的控制台
（不带管道）时，PowerShell **既不等待、也不更新 `$LASTEXITCODE`**；而上一条
`& $exe stages | Select-Object -First 3` 会提前掐断管道、把进程杀掉并留下
`-1`。于是一个本来正确的检查被误判。这是**竞态**，所以它以前偶尔能过。

**修法**：8 处对冻结产物的检查改为 `Start-Process -Wait -PassThru` 读权威
`ExitCode`。`$LASTEXITCODE` 只保留给可信场景（Python CLI、console 子系统变体）。

> 顺带发现并保留：机器上另有 `npm-global\...\opencode.exe`（用户自己装的
> opencode）。隔离设计（独立 home / 端口 / 密码）保证与内嵌实例互不干扰，
> 本程序不会去动它。

---

## 分发

不变：内核二进制 **172.3 MB**，超 GitHub 单文件 100 MB 硬上限，**不入库**；
由 `pclradiomics.spec` 在构建期自动获取（离线可先跑
`build_opencode_kernel.bat --from-source`）。`.gitignore` 已排除 `opencode/`
（含真实 API Key 与会话数据）。单文件版按设计不含内核。

## 从 v2.0.0 升级

- 无破坏性变更：原有四种模式（GUI / MCP / Web / API）与全部子命令行为不变；
  对外 MCP 服务仍是 21 个工具。
- `APP_VERSION` 2.0.0 → 2.1.0。
- 新增 `opencode/projects.json`（项目↔session 映射，已 gitignore）。
- 新增两个开关（默认都开）—— 若不想让 GUI 自动起内核，设 `PCL_KERNEL_AUTOSTART=0`。
