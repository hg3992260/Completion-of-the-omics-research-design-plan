# v2.2.1 —— 进程机制修复（消除闪控制台 / 卡顿）+ TUI 中文输入

> 修 v2.2.0 起用户反馈的三个问题：界面卡顿、Windows console 反复开启关闭、
> opencode 终端无法输入中文。根因同为「内部子进程未隐藏控制台 + GUI 线程做阻塞 IO」。

---

## 一句话

所有内部子进程不再弹控制台黑框（`CREATE_NO_WINDOW`），判进程存活改用 Win32 API（不再起进程）；
底部状态面板刷新移到后台线程并把间隔调到 10s；TUI 优先用 Windows Terminal 打开（中文 IME 正常）。

---

## 修复（根因）

| 现象 | 根因 | 修复 |
|---|---|---|
| console 反复开启关闭 | `_pid_alive`(tasklist) / `list_processes`(powershell) / `_kill`(taskkill) / `models`·`mcp list` 都未加 `CREATE_NO_WINDOW`，windowed 主程序起 console 子进程即弹框 | 新增 `_no_window_kwargs()` 并应用到全部内部子进程 |
| 界面卡顿 | 底部面板每 5s 在 **GUI 线程**跑 `mcp_server.http_status()`（socket，最长阻塞 1s）+ `KernelBoot.status()`→`_tui_alive()`→`tasklist` | ① `_pid_alive` 改用 `OpenProcess/GetExitCodeProcess`（ctypes，**不起进程**）；② `refresh_console` 移到**后台线程**，经 `console_status` 信号回 GUI；③ 刷新间隔 5s → **10s** |
| opencode 终端无法输入中文 | TUI 跑在 conhost，IME 支持差 | TUI 优先用 **Windows Terminal（`wt.exe`）** 打开；无 `wt` 时回落 conhost |

---

## 验证

- `py_compile kernel_client.py kernel_boot.py design_studio.py` → OK
- `_no_window_kwargs()` = `{'creationflags': 134217728}`（= CREATE_NO_WINDOW）
- `_pid_alive(自身)=True`、`_pid_alive(无效 pid)=False`（ctypes 路径，无子进程）

---

## 变更

- `APP_VERSION` 2.2.0 → 2.2.1。
- 底部「MCP / 内核状态」面板刷新间隔 5s → 10s。

## 发布产物

由 GitHub Actions 在 tag `v*` 自动构建：Windows `PCLRadiomics-windows-x64.zip` / `PCLRadiomics.exe` /
`PCLRadiomicsConsole-windows-x64.zip`；macOS `PCLRadiomics-<版本>-macos-<架构>.dmg` + `pclradiomics-macos-cli.zip`。
