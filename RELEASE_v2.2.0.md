# v2.2.0 —— 内核联动可视化 + TUI 单窗口复用 + macOS 适配

> 在 v2.1.0「GUI 启动即联动内核」基础上，把内核联动做成**可见、可控、可复用**，
> 并补齐 macOS 侧的适配与分发辅助。完整设计见 [`opencode-embedding-playbook.md`](opencode-embedding-playbook.md)。

---

## 一句话

打开 GUI 即起内核；底部新增「MCP / 内核状态 + 操作日志」面板；换课题/改名/切会话都在
**同一个 opencode 终端窗口**内切换并弹提示，多余的终端窗口自动清理；课题改名会沿用同一会话
并同步更新会话标题；macOS 侧补上进程识别、TUI 跟踪与打包/签名辅助。

---

## 新增

### 1. 底部「MCP / 内核状态 + 操作日志」面板（可点击缩放）
- 折叠态是一行实时摘要：`驱动=… · 内核：<url> v<版本> pid=<pid> · 项目 <名> · MCP：<url> · <N> 工具`。
- 点「▸ MCP / 内核状态」展开：左侧 MCP/内核明细，右侧操作日志。
- 操作日志记录：内核事件 + 切阶段 / 切项目 / 改名等 GUI 操作。

### 2. 只保留一个 opencode 终端（复用同一窗口）
- 切课题 / 改名 / 切会话：调用 `POST /tui/select-session` 让**已在运行的 TUI 内部切换**，不重开窗口。
- 切换时弹 `POST /tui/show-toast` → TUI 顶部出现「已切换课题：X」。
- 启动与切换时扫描**同源 exe 路径**的 opencode 进程，只保留内核 `serve` + 最新 `attach`，
  其余自动关闭（**不碰用户自己安装的 opencode**）。

### 3. 改名同步 opencode 会话标题
- 课题改名：迁移「项目↔会话」绑定（**沿用同一 sessionID**）+ `PATCH /session/:id` 更新会话标题 + 跟随终端。

### 4. macOS 适配
- `list_processes` 增加 POSIX 分支（`ps -axo pid=,comm=,args=`）。
- TUI 追踪：`osascript` 句柄不持久 → 用 `ps` 发现真正的 `opencode attach` pid（`_discover_tui_pid`），
  使「复用同一窗口切会话」在 macOS 上也成立。
- `pclradiomics_macos.spec`：hiddenimports 增 `kernel_driver`；收集 `kernel_assets/`（agent/skill）。
- 新增 `macos_sign_kernel.sh`：对 .app 内嵌 opencode 二进制签名（注入 JIT entitlement：`allow-jit`、
  `allow-unsigned-executable-memory`、`disable-library-validation`）+ 去 `com.apple.quarantine` + 重签外层，
  并给出 notarytool/staple 提示。

---

## 变更

- `mcp_server.py` 新增 `project_sections` / `project_get_section` / `project_set_section`（工具 21 → 24）。
- `pclradiomics.spec` 收集 `kernel_assets/`，`kernel_driver` 纳入 hiddenimports 与前置导入校验。
- 修复：工作线程用 Qt 信号（`opencode_done`）回 GUI（原 `QTimer.singleShot` 不生效）；
  面板按钮改用 `CButton.button().setText`；GBK 控制台打印崩溃（`stdout.reconfigure`）。

---

## 发布产物

由 GitHub Actions 在 **tag `v*`** 时自动构建并挂到本 Release：

| 平台 | 产物 |
|---|---|
| Windows | `PCLRadiomics-windows-x64.zip`（onedir，含内核 + kernel_assets）等 |
| macOS | `PCLRadiomics-<版本>-macos-<架构>.dmg` + `pclradiomics-macos-cli.zip` |

> 内核二进制（约 172 MB）**不入库**（GitHub 单文件 100 MB 上限）；构建期由 spec/CI 自动获取。

---

## 升级注意

- 无破坏性变更：`host` 模式与原有四种入口（GUI / MCP / Web / API）行为不变。
- `APP_VERSION` 2.1.0 → 2.2.0。
- 新增开关：无（沿用 `PCL_DRIVER` / `PCL_KERNEL_AUTOSTART` / `PCL_KERNEL_TUI` / `PCL_SKIP_KERNEL`）。
- 冻结产物首次以 opencode 模式使用前，需保证隔离 home 有 `auth.json`（`kernel auth import-host`）。
