# 组学研究工具包：设计工作台 + 标准流程管线

两个 PyCt6 / PySide6 桌面程序，共用一个十阶段标准流程知识库（CLEAR / METRICS / TRIPOD+AI / PROBAST+AI /
CLAIM / RQS / IBSI / MIAPE / MSI）：

| 程序 | 作用 | 启动 |
|---|---|---|
| **`design_studio.py`** | **主界面**：贴入初步实验设计 → LLM agent 按十阶段逐段追问与改写 → 输出可执行研究设计 | `启动_设计工作台.bat` |
| `omics_pipeline.py` | 管线视图：十阶段检查表、评分与自评进度 | `启动.bat` |

![设计工作台](_shots/studio_01_draft_dark.png)

---

## 一、设计工作台（主界面）

### 它怎么工作

1. **输入**：把初步设想（数据类型、例数、中心、终点、打算怎么建模）贴进中间输入框，点「开始分析」。
2. **速读**：agent 先复述这项研究要做什么、属诊断还是预后，并给出 3 条首要关注点。
3. **逐阶段推进**（十阶段，每段两轮）：
   - **第一轮 · 追问**：产出【现状评估】【必须澄清的问题】（2–4 条，每条附"为什么问"）【本阶段小结】；
   - **你来回答**：下方为每条问题生成一个输入框，可只答部分、也可写"不确定"；
   - **第二轮 · 改写**：产出【改写稿】（300–500 字，含参数 / 时间窗 / 判定标准）【检查表】（带 CLEAR、TRIPOD+AI 等条目号）【风险提示】【下一步】；
   - **采纳**：改写稿可直接编辑，点「采纳并收录 → 下一阶段」写入右侧研究设计文档，自动进入下一阶段。
4. **收口**：右侧「生成完整草案」把十个阶段定稿整合成一份研究设计草案 + 待补数据清单 + 投稿前自查。

### 分辨率与文字不遮挡

- **窗口自适应屏幕**：启动时按当前显示器可用区域计算尺寸（`ui_kit.screen_size()`），
  最大 1520×960 且不超过屏幕 96%×94%，并居中显示 —— 不会再出现窗口比屏幕高、底部被任务栏切掉的情况。
- **窄窗口响应式**：宽度 < 1420（管线视图 1340）时自动收起进度条、收窄左右两栏（292/322）
  与下拉框、按钮，表头高度从 96 加到 112 让副标题正常换行；按钮文案统一用短版
  （开始分析 / 提交回答 / 采纳并收录 / 跳过本阶段），任何宽度都不会被截断。
- **文字永不裁切**：所有文字标签改用 `RefitLabel` —— 宽度变化时按**实际宽度**重算换行高度，
  而不是按创建时的估算宽度；步骤条与详情区都放进带滚动条的容器，窗口变矮时滚动而不是压到相邻控件上。
- **自检脚本**：`python _probe_view.py 1200 700` 可在指定尺寸渲染两个界面截图，
  用于核对文字遮挡；`python design_studio.py --demo --shot` 出全套状态截图。

### 项目管理

- **新建**：顶部「新建」→ 输入项目名（默认 `课题_MMDD_HHMM`）+ 可直接粘贴初步设计（也可以先建空项目）。
  新建即落盘，不会因为没保存而丢失。
- **切换**：顶部下拉框直接切换，或点「管理」在列表里双击打开。
- **管理对话框**：列出全部项目（名称 / 完成度 n/10 / 更新时间 / 文件大小 / 模型），支持搜索，按钮包括
  **打开、重命名、创建副本、打开文件夹、删除、新建项目**。
- **重命名**：改显示名的同时**移动项目文件**（`projects/<名称>.json`），旧文件自动移除；
  重名会自动加 `(2)` 后缀，不会覆盖已有项目。
- **删除**：二次确认后移除文件；删的是当前项目时会自动新建一个空项目接续。
- **状态保护**：切换项目、新建、删除、关闭窗口前都会先自动保存当前项目的改动
  （包括还没提交的"初步设计"输入框内容）；项目完成度未满时会自动定位到下一个待完成阶段继续。

项目文件为纯 JSON，可随意备份/迁移；文件损坏的项目会在列表里自动跳过。
**空白项目不会自动落盘**（开窗关窗不再产生空副本）；`--demo` 演示模式也不写入 `projects/`。

### 界面

- **左栏**：十阶段步骤条，颜色即状态 —— 灰=未开始、黄=已追问、青=待采纳、绿✓=已收录；点任意阶段可跳转或重做。
  底部主按钮会**跟随阶段换文案**（开始分析 / 提交回答 / 采纳并收录 / 开始本阶段），
  **等待模型响应时整颗按钮变成"正在思考"动画**：旋转弧线 + 呼吸省略号 + 底部不定量流光条，
  比单纯置灰更直观；请求结束自动恢复为可点击状态。
- **中栏**：对话工作区（流式输出）+ 随阶段切换的输入区（初步设计 / 逐条回答 / 改写稿编辑 / 自由追问）。
  回答阶段每条问题**完整换行显示**（编号 + 问题全文 + "为什么问" + 可多行作答框），
  一屏放不下时工作区自带滚动条，不会出现文字被截断；工作区高度会按中栏空间自动伸缩。
- **右栏**：研究设计文档实时预览；`导出 .md`（**弹出保存对话框自选路径**，默认落在「文档/PCLRadiomics」并记住上次位置；未写扩展名会自动补 `.md`；取消则什么都不做）、
  `导出 Word`（`.docx`：一/二/三级标题层级，检查表排成「# / 条目 / 依据」三列表格，追问与回答排成「问题 / 回答」两列表格，适合伦理申请与论文附件；快捷键 **Ctrl+Shift+E**，Markdown 是 **Ctrl+E**）、
  `生成完整草案`、`打开管线视图（评分与检查表）`。
- **管线视图（只读表格）**：顶部「工作台 / 总览」标签，或点右栏「打开管线视图（评分与检查表）」——
  以**表格**列出十个阶段，列固定为：

  | # | 阶段 | 状态 | 规范出处 | 结果 / 待办 | 检查表 | 更新 |
  |---|---|---|---|---|---|---|
  | 01 | 研究问题与设计 | ● 已完成 | TRIPOD+AI 3–4 · 18c–d | 定稿：研究类型：诊断准确性研究… | — | 23:06 |
  | 02 | 伦理与数据治理 | ● 已追问 | CLEAR 8 · 13–14 | 已完成追问，等待回答 | — | 23:07 |
  | 03 | 样本量与事件数 | ● 待采纳 | TRIPOD+AI 10 · 21 | 已有改写稿，等待采纳 | 2 | — |

  状态用**红/黄/绿**着色：**绿 = 已完成（已收录定稿）**、**黄 = 已追问 / 待采纳**、**红 = 未开始**；
  表头汇总「● 绿 n 已完成 · ● 黄 n 进行中 · ● 红 n 未开始 · 共 n/10 阶段定稿」+ 进度条。
  表格**完全只读**（禁用编辑、选择与焦点），数据只来自十阶段的结果，随项目状态与深浅色自动重绘。
- **顶部**：项目切换与新建、模型切换、LLM 设置、深浅色。
  **默认浅色**（极简蓝白）；点「深色」切换为**亮橙科技配色**（近黑底 + #FF7A1A 主色，
  青绿/琥珀/珊瑚作状态色），两套配色共用同一套控件与图标，切换即时生效。
- **快捷键**：`Space` 开始/继续，`↑↓` 切换阶段，`Ctrl+S` 保存项目，`Ctrl+E` 导出。
- **左下角响应动画**：等待模型返回时，左下角出现**橙色律动胶囊**（4 根均衡器条 + 横向流光 + 实时计时，
  如"追问中 · 12s"），一眼可见程序正在工作；请求结束自动收起为低调灰点，并提示下一步
  （"等待你的回答" / "等待采纳改写稿" / "就绪 · 可随时追问"）。最小窗口宽度下也不与状态文字挤在一起。

项目自动保存在 `projects/<项目名>.json`，随时从顶部下拉框切回。

### LLM 服务

默认 **DeepSeek 官方 `deepseek-v4-pro`**（OpenAI 兼容），密钥**自动复用 agent 自身凭据**
（`~/.dsh/.credentials.yaml` 的 `DEEPSEEK_API_KEY`），无需手工填写。优先级：

```
llm_config.json 里手填的 key  >  环境变量 LLM_API_KEY / DEEPSEEK_API_KEY  >  ~/.dsh/.credentials.yaml
```

顶部「设置」可改 Base URL / API Key / 模型 / 温度，并带「测试连接」。任何 OpenAI 兼容端点都能接
（内网网关、自建服务等）。命令行临时覆盖：

```bat
set LLM_BASE_URL=https://your-gateway/v1
set LLM_MODEL=your-model
set LLM_API_KEY=sk-xxx
启动_设计工作台.bat
```

**注意（推理模型）**：`deepseek-v4-pro` 会把思考 token 也算进 `max_tokens`，预算给小了会出现
"只想不说、正文为空"。客户端已把默认预算设为 8000，并在检测到空正文时自动加倍重试一次；
温度默认 0.4。实测单次调用 30–60 秒、单阶段两轮约 90 秒。

模型选择上的体验差异：`deepseek-v4-pro` 输出更规整、几乎不夹带自我点评；
`deepseek-flash` 更快，但更容易在正文里混入写作说明（代码里已做逐行清洗，仍建议用 v4-pro）。

---

## 二、管线视图（评分与检查表）

![管线视图](_shots/01_dark_default.png)

左侧十阶段管线（自绘节点 + 连接箭头，已完成段落连线变青）、中间阶段详情（目标 / 可勾选的必做动作 /
必报参数）、右侧本案例达标-部分-缺失自评与常见缺陷；勾选计入进度，导出 Markdown 检查表，
状态存 `progress_state.json`。启动：`启动.bat`。

---

- **底部署名**：两个程序窗口底部都有一行署名
  `designed by christ.paul90@gmail.com ,all rights reserved`（右下角，浅/深色自适应；
  邮箱可点击，直接调起邮件客户端）。
- **图标与启动画面**：`LOGO.jpg`（PCL-Radiomics）已作为程序图标 —— 标题栏/任务栏/Alt-Tab 显示多尺寸
  图标，界面标题左侧有 28×28 角标；主界面启动时短暂显示启动画面（约 1.1 秒，`design_studio.SHOW_SPLASH`
  可关闭，`--shot/--e2e/--demo` 模式下自动跳过）。
  重新生成图标资源：把新图覆盖 `LOGO.jpg` 后运行 README 同目录的生成脚本即可（见下）。

## 三、把程序当作服务提供（MCP / OpenAI API）

程序的后端本来就是三层解耦的 —— `llm_client.py`（传输）/ `design_agent.py`（提示词与领域逻辑）/
`stages_data.py`（标准流程知识），所以两种对外服务都只是薄封装，**无需改动主程序**。

### 3.1 MCP 服务器（供 agent 调用）

```bat
启动_MCP服务.bat                          :: stdio，默认传输
D:\python\envs\mar\python.exe mcp_server.py --transport streamable-http --port 8765
D:\python\envs\mar\python.exe mcp_server.py --list-tools      :: 只看工具清单
```

12 个工具，分三层：

| 层 | 工具 | 说明 |
|---|---|---|
| 知识 | `list_stages` | 十阶段：规范出处、必做动作、必报参数、常见缺陷、参考条目 |
| 领域 | `design_ask` / `design_rewrite` / `design_finalize` | 追问 → 改写（含检查表/风险） → 汇总成完整设计草案 |
| 项目 | `list_projects` / `create_project` / `project_overview` / `project_get_stage` / `project_set_stage` / `export_markdown` | 项目读写；`project_overview` 即界面那张管线视图表格 |
| 通道 | `llm_chat` / `llm_models` | 原样调用背后的 DeepSeek，agent 可当 LLM 网关用 |

注册到 MCP 客户端（DSH / Claude Desktop / opencode 的 `mcpServers` 段，现成文件见 `mcp.json`）：

```json
{ "mcpServers": { "radiomics-workbench": {
    "command": "D:\\python\\envs\\mar\\python.exe",
    "args": ["I:\\文件\\CTCC\\HL\\omics_pipeline\\mcp_server.py"] } } }
```

### 3.2 独立推理服务（OpenAI 兼容 API）

```bat
启动_推理API.bat                            :: http://127.0.0.1:8788/v1
D:\python\envs\mar\python.exe api_server.py --port 8788 --model deepseek-v4-pro
```

| 端点 | 作用 |
|---|---|
| `GET /health` | 模型、上游、密钥（脱敏）、调用/流式/token 计数 |
| `GET /v1/models` | 上游模型列表 |
| `POST /v1/chat/completions` | 对话补全，支持 `stream: true`（SSE 直通，`reasoning_content` 一并透传） |

任何支持自定义 base_url 的客户端可直接接入：

```python
from openai import OpenAI
cli = OpenAI(base_url="http://127.0.0.1:8788/v1", api_key="not-needed")
r = cli.chat.completions.create(model="deepseek-v4-pro", messages=[{"role": "user", "content": "你好"}])
```

**安全**：默认只绑 `127.0.0.1`（不对外网开放，避免把带密钥的代理暴露出去）；
局域网共享需显式 `--host 0.0.0.0 --token <口令>`，客户端带 `Authorization: Bearer <口令>`。
密钥解析复用 `llm_client.load_config()`（界面手填 > 环境变量 > agent 凭据），服务本身不另存密钥。

### 3.3 自检脚本

```bat
D:\python\envs\mar\python.exe _test_mcp_stdio.py     :: stdio 传输（与 DSH 拉起方式一致）
D:\python\envs\mar\python.exe _test_mcp_client.py    :: streamable-http 传输
D:\python\envs\mar\python.exe _test_api.py           :: /health、/v1/models、非流式、流式
D:\python\envs\mar\python.exe _test_api_stream.py    :: 流式细化（区分正文与思考分片）
```

> 注意：在受限沙箱里跑 stdio 自检会因 Windows 命名管道被拦而报 `WinError 5`；
> 由 DSH / Claude Desktop 作为父进程拉起时不受此限。

## 五、打包成 exe（一个 exe 承载全部模式）

```bat
build_exe.bat            :: 文件夹版（onedir，启动快，适合 MCP 常驻）
编译单文件版.bat          :: 单文件版（onefile，拷一个文件就能跑）
:: 或手动
D:\python\envs\mar\python.exe -m PyInstaller --noconfirm --clean pclradiomics.spec
set PCL_ONEFILE=1 && D:\python\envs\mar\python.exe -m PyInstaller --noconfirm --clean --distpath dist-onefile pclradiomics.spec
```

| 形态 | 体积 | 启动 | 适用 |
|---|---|---|---|
| 文件夹版 `dist\PCLRadiomics\PCLRadiomics.exe` | 148 MB 目录 | 0.3–1.5s | MCP 常驻（客户端会反复拉起） |
| **单文件版 `dist-onefile\PCLRadiomics.exe`** | **65 MB 单文件** | CLI 2.5–4.4s、GUI ~10s | 分发/临时试用（每次启动解包到 `%TEMP%`） |

两种形态**都支持全部模式**（实测）：图形界面、`mcp`（stdio 与 streamable-http）、
`api`（OpenAI 兼容，含 SSE 流式）、`check/net/stages/projects/paths`。

```bat
PCLRadiomics.exe                                    :: 图形界面（双击即可，无黑框）
PCLRadiomics.exe mcp                                :: MCP stdio —— 供 DSH / Claude Desktop 注册
PCLRadiomics.exe mcp --transport streamable-http --port 8765
PCLRadiomics.exe api --port 8788                    :: OpenAI 兼容推理服务
PCLRadiomics.exe check ^| net ^| stages ^| projects ^| paths
```

冻结版 MCP 注册片段：`mcp_frozen.json`。

### 「一个 exe 同时当界面程序和 stdio 服务」是怎么做到的

**矛盾点**：stdio 传输要求进程有真实 stdout，所以直觉上必须编成 console 子系统；
但 console 程序双击时会弹黑框，而 Win11 默认控制台由 Windows Terminal 托管
（窗口类 `CASCADIA_HOSTING_WINDOW_CLASS`，属于别的进程），
用 `ShowWindow(GetConsoleWindow())` **藏不掉**——实测确实会留下一个终端窗口。

**解法（`win_stdio.py`）**：编成 **windowed**（GUI 子系统，永远没有黑框），
再按需把标准流接回来：

| 启动方式 | 接管路径 | 结果 |
|---|---|---|
| MCP 客户端用管道拉起 | `GetStdHandle` 拿到父进程给的管道句柄 → `open_osfhandle` 包成文本流（带 `.buffer`） | stdio 传输正常 |
| 终端里手敲命令 | 没有管道 → `AttachConsole(-1)` 附加上父控制台，重开 `CONOUT$/CONIN$` | 日志照常显示 |
| 双击图形界面 | 两者都没有 → 落到 devnull | 干净无声，无黑框 |

实测：双击后新增的可见窗口**只有**「组学研究设计工作台」这一个（无任何终端窗口）；
同时 `mcp` stdio 握手成功、12 工具可调、`llm_chat` 真实返回。
需要控制台版调试时：`set PCL_CONSOLE=1`；想打成单文件：`set PCL_ONEFILE=1`。
只要小体积服务端（约 54 MB，不带界面）：`pclradiomics_service.spec`。

### 打包时必须处理的四件事（均已在代码里解决）

1. **可写路径要脱离 `__file__`** —— 冻结后 `__file__` 指向临时解包目录，写入会丢。
   `app_paths.py` 统一解析：只读资源（主题/图标）取 exe 同级 → 打包内置 → 源码目录；
   可写数据（`projects/`、`llm_config.json`、导出 md、`error.log`）一律放 exe 同级，
   不可写时退到 `%LOCALAPPDATA%\PCLRadiomics`，实现绿色便携。
2. **HTTPS 证书** —— 冻结后 `ssl` 枚举 Windows 证书库会报
   `SSLError: [ASN1: NOT_ENOUGH_DATA]`，导致所有上游调用失败（症状：`可用模型 []`）。
   已改为优先使用随包携带的 `certifi` 根证书（`llm_client.ssl_context()`）。
3. **PyCt6 自带主题 JSON** —— 不显式收集 `collect_data_files("PyCt6")`，
   图形版会因 `FileNotFoundError: _internal\PyCt6\widgets\themes\blue.json` **静默退出**。
4. **体积** —— PyInstaller 会顺带打包 numpy/PIL 及其 **Intel MKL（约 350 MB）**，
   本程序运行期完全用不到，已在 spec 里排除（592 MB → 148 MB）。

### windowed 构建的排错

图形版没有控制台，崩溃时界面直接消失。`cli.py` 会把未捕获异常写入
**exe 同级 `error.log`** 并弹系统对话框提示，先看这个文件。

### 自检脚本

```bat
D:\python\envs\mar\python.exe _test_merged.py        :: 一个 exe 的全部模式（CLI/API/MCP-http/GUI）
D:\python\envs\mar\python.exe _test_frozen_stdio.py  :: 冻结 exe 的 stdio MCP（与 DSH 拉起方式一致）
D:\python\envs\mar\python.exe _test_console.py       :: 双击时会不会冒黑框
```

> 受限沙箱里跑 stdio 自检会因命名管道报 `WinError 5`；由 MCP 客户端作为父进程拉起时不受影响。

## 六、macOS 版（.app / .dmg）

macOS 与 Windows 的差异**已在代码里处理**，不需要额外分支：

| 差异点 | 处理方式 |
|---|---|
| 中文字体 | `ui_kit` 在 darwin 上用 **PingFang SC**（Windows 用微软雅黑，Linux 用 Noto Sans CJK） |
| 窗口图标 | macOS 用 `logo_mark.png`（PNG），Windows 用多尺寸 `logo_icon.ico` |
| 数据目录 | macOS 冻结后写 **`~/Library/Application Support/PCLRadiomics`**（.app 包内只读，不能写）；Windows 写 exe 同级 |
| 标准流 | `win_stdio` 只在 Windows 生效；macOS 的二进制本身就有 stdout，stdio MCP 直接可用 |
| 崩溃提示 | Windows 用 MessageBox，macOS 用 `osascript` 弹窗，堆栈同样写 `error.log` |

打包（**必须在 macOS 上执行**，PyInstaller 不支持跨平台编译）：

```bash
python -m PyInstaller --noconfirm --clean pclradiomics_macos.spec
./make_dmg.sh                              # 生成可拖拽安装的 dmg
PCL_VERSION=1.2.0 ./make_dmg.sh            # 指定版本号
PCL_ARCH=universal2 python -m PyInstaller ... pclradiomics_macos.spec   # Intel+ARM 通用（依赖需有 universal2 轮子）
```

产物：

| 文件 | 说明 |
|---|---|
| `dist/PCLRadiomics.app` | 图形界面，拖进「应用程序」即可；内含 `Contents/MacOS/PCLRadiomics` 命令行入口 |
| `dist/pclradiomics-cli/pclradiomics` | 纯命令行版（不含 Qt，约 50 MB）——**MCP 注册建议用这个** |
| `PCLRadiomics-<版本>-macos-<架构>.dmg` | 拖拽安装镜像：左边应用图标、右边 Applications 快捷方式 |

macOS 上的 MCP 注册（指向命令行版最省事）：

```json
{ "mcpServers": { "radiomics-workbench": {
    "command": "/Applications/PCLRadiomics.app/Contents/MacOS/PCLRadiomics",
    "args": ["mcp"] } } }
```

> **Gatekeeper**：dmg 未做 Apple 签名与公证，首次打开可能被拦。
> 解决：右键点应用 → 打开；或执行 `xattr -dr com.apple.quarantine /Applications/PCLRadiomics.app`。
> 要做正式签名/公证需 Apple 开发者证书，可在 workflow 里加 secrets 后开启（暂未启用）。

CI：`.github/workflows/build-macos.yml`（默认 `macos-latest` = Apple Silicon；
手动触发可选 `macos-13` 出 Intel 版，或勾 `universal2` 试通用二进制）。

## 七、上传 GitHub 自动编译

仓库里已备好 CI：`.github/workflows/build-windows.yml`。
推上去就会在 GitHub 的 Windows 机器上自动装依赖、打包、校验并上传产物。

```bat
cd /d I:\文件\CTCC\HL\omics_pipeline
git init
git add .
git commit -m "PCL-Radiomics workbench: GUI + MCP + OpenAI-compatible API"
git branch -M main
git remote add origin https://github.com/<你的账号>/<仓库名>.git
git push -u origin main
```

- **触发**：推 `main`／发 PR／手动 Run workflow；推 `v*` tag 时额外创建 Release 并附 zip。
- **产物**：Actions 页面该次运行的 Artifacts 里下载 `PCLRadiomics-windows-x64.zip`
  （文件夹版）。
- **要单文件版（onefile）**：Actions → build-windows → **Run workflow → 勾选 `onefile`**，
  或直接双击 `触发云端单文件编译.bat`／执行
  `gh workflow run build-windows.yml -f onefile=true`。
  该次运行的产物里会同时有 `PCLRadiomics-windows-x64.zip` 与 **`PCLRadiomics.exe`（65 MB 单文件）**。
- **注意**：`.github/workflows/` 下的文件只有带 `workflow` 权限的令牌才能改；
  普通源码同步不受影响（`gh auth refresh -s workflow` 可补权限）。
- **想让 CI 顺带做真实模型连通性测试**：仓库 Settings → Secrets → Actions 添加
  `DEEPSEEK_API_KEY`；没配就自动跳过（不影响构建成功）。
- **应用在子目录时**：把 workflow 顶部的 `APP_DIR: "."` 改成子目录名即可。
- **隐私检查**：`.gitignore` 已排除 `projects/`（研究数据）、`llm_config.json`、
  `dist/`、`build/`、`_*.txt` 等；本仓库文件经检查**不含任何明文 API Key**
  （密钥由运行期从环境变量或 `~/.dsh/.credentials.yaml` 读取）。

## 七、文件说明

| 文件 | 作用 |
|---|---|
| `design_studio.py` | 主界面：三栏工作台、流式对话、阶段状态机、设置弹窗、导出 |
| `design_agent.py` | agent 层：十阶段提示词、`【小节】`解析、输出清洗（剔除模型自我点评）、项目模型与文档渲染 |
| `llm_client.py` | OpenAI 兼容客户端：配置解析（含 agent 凭据）、流式 SSE、空正文自动重试、模型列表 |
| `ui_kit.py` | 共享 UI：蓝色科技配色、按字体度量自适应的标签、进度条、可随主题重绘的对话视图 |
| `omics_pipeline.py` | 管线视图（评分与检查表） |
| `stages_data.py` | **十阶段内容**（目标 / 必做动作 / 必报参数 / 常见缺陷 / 本案例状态 / 规范条目）——改这里即可换课题 |
| `theme_tech.json` | PyCt6 主题：**浅色 = 极简蓝白，深色 = 亮橙科技**（8 个控件段，深浅双色） |
| `LOGO.jpg` → `logo_icon.ico` / `logo_mark.png` / `logo_badge.png` / `logo_banner.png` | 由原图派生的图标资源：多尺寸 `.ico`（16–256）用于窗口/任务栏/快捷方式，方版徽标与 28×28 角标用于界面，全幅图用于启动画面 |
| `组学研究设计工作台.lnk` / `标准流程管线.lnk` | 带图标的 Windows 快捷方式，双击即启动（可拖到桌面/任务栏） |
| `projects/` | 课题项目存档（JSON，自动保存） |
| `llm_config.json` | 非敏感配置（模型、温度、预算）；密钥仅在手工填写时写入 |
| `启动_设计工作台.bat` / `启动.bat` | 一键启动（自动选用已装 PyCt6 的解释器） |
| `_shots/` | 界面截图（`--shot` / `--demo --shot` 自检生成） |

数据与界面完全分离：`stages_data.py` 换内容，`design_agent.py` 换提示词，UI 不用改。

## 四、自检命令

```bat
:: 主界面：离线假对话 + 截图（不调用网络）
D:\python\envs\mar\python.exe design_studio.py --demo --shot

:: 主界面：真实 LLM 端到端（无窗口，跑完三个阶段并写 _e2e_agent.log）
D:\python\envs\mar\python.exe _e2e_agent.py deepseek-v4-pro

:: LLM 连通性
D:\python\envs\mar\python.exe llm_client.py

:: 管线视图截图
D:\python\envs\mar\python.exe omics_pipeline.py --shot
```

## 五、规范依据

- **CLEAR**（58 项）Kocak B, et al. Insights Imaging 2023 · doi:10.1186/s13244-023-01415-8
- **METRICS**（30 项 / 9 类）Kocak B, et al. Insights Imaging 2024 · doi:10.1186/s13244-023-01572-w
- **TRIPOD+AI**（27 项）Collins GS, et al. BMJ 2024;385:e078378
- **PROBAST+AI** Moons KGM, et al. BMJ 2025 · doi:10.1136/bmj-2024-082505
- **CLAIM 2024** Radiol Artif Intell · doi:10.1148/ryai.240300
- **RQS**（16 项 / 36 分）Lambin P, et al. Nat Rev Clin Oncol 2017;14:749
- **IBSI** Zwanenburg A, et al. Radiology 2020;295:328 与 Radiology 2024 · doi:10.1148/radiol.231319
- **样本量** Riley RD, et al. BMJ 2020;368:m441 ｜ **MIAPE** Nat Biotechnol 2007 ｜ **MSI** Metabolomics 2007

> 案例数据来源：Cheng S, et al. Adv Sci 2025;12(20):e2409488（CC BY 4.0）。本工具为流程参考，
> 阶段内容依据上述公开规范整理，实际课题请按最新版本核对条目编号；agent 产出的建议需研究者自行复核。

