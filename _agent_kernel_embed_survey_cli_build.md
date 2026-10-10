# Pre-embedding survey — CLI dispatcher, console/stdio, paths, PyInstaller matrix

Read-only. Host root = this workspace. No source modified.

## 1. CLI dispatcher (`cli.py`)

No argparse in `cli.py`: a dict lookup on `sys.argv[0]`, each subcommand delegating to a module that
does use argparse. Dispatch table, `cli.py:261-263`:

```python
COMMANDS = {"gui": cmd_gui, "net": cmd_net, "mcp": cmd_mcp, "api": cmd_api, "serve": cmd_api,
            "stages": cmd_stages, "projects": cmd_projects, "paths": cmd_paths,
            "check": cmd_check, "manuscript_review": cmd_manuscript, "mr": cmd_manuscript}
```

Mode selection — `cli.py:268-276`:

```python
if not argv or argv[0].startswith("-"):
    name = os.path.basename(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]).lower()
    if any(k in name for k in ("serve", "服务", "mcp", "api")): argv = ["mcp"] + argv
    else: argv = ["gui"] + argv
cmd, rest = argv[0], argv[1:]; fn = COMMANDS.get(cmd)
```

**GUI-vs-service is exe-basename substring matching only** — no env var, no config key. This is why
`pclradiomics_service.spec` names its EXE `PCLRadiomics服务` (`:30`) to default into service mode.
Unknown command → docstring + exit 2 (`cli.py:278-280`).

| Command | Handler | Purpose | Downstream parser |
|---|---|---|---|
| `gui` (default) | `cmd_gui` `:125` | Qt workbench → `design_studio.main(["design_studio"]+argv)` | manual scan for `--shot/--e2e/--demo` (`design_studio.py:4563,4574`) |
| `mcp` | `cmd_mcp` `:141` | MCP server; **rewrites `sys.argv`** | argparse `mcp_server.py:601-610` (`--model --list-tools --transport --host --port`) |
| `api`, `serve` | `cmd_api` `:148` | OpenAI-compatible HTTP; rewrites `sys.argv` | argparse `api_server.py:231-236` (`--host --port --model --token`) |
| `stages` | `:155` | Print 10-stage standard flow | none |
| `projects` | `:165` | List projects + completeness | none |
| `paths` | `:176` | Dump path resolution | none |
| `check` | `:187` | Paths, `mcp`/`PySide6` import, model connectivity → 0/1 | none |
| `net` | `:228` | Raw upstream `/models` probe, full traceback | none |
| `manuscript_review`, `mr` | `:130` | Manuscript review backend | argparse `manuscript_review/cli.py:109-146` (17 flags incl. `--selfcheck`) |

Embedding-relevant: `cli.py:29-31` installs `HERE` on `sys.path`; `cmd_mcp`/`cmd_api` clobber
`sys.argv` (`:143,150`) so a kernel reading argv must run first or save/restore; `cmd_gui` hardcodes
`argv[0]="design_studio"` (`:127`). `serve`→`cmd_api` (`:261`) but the *basename* rule maps
`serve`/`服务`→`mcp` (`:272-273`) — a `*serve*.exe` starts MCP, not the API, contradicting the
docstring (`:18`). The `__main__` guard (`:284-296`) is the only caller of `_ensure_streams()` /
`_utf8_console()`; `mcp_server.py`, `api_server.py`, `web_server.py` have bare `main()` guards.
Free functions usable as an API: `_ensure_streams() -> str` (`:34`), `cmd_*` handlers, `main(argv)` (`:266`).

## 2. Console-subshell problem

Both build knobs live only in `pclradiomics.spec:27-29`:

```python
ONEFILE = os.environ.get("PCL_ONEFILE", "") not in ("", "0", "false", "False")
CONSOLE = os.environ.get("PCL_CONSOLE", "") not in ("", "0", "false", "False")
```

Consumed at `:115-122` (`console=CONSOLE`). **Default = windowed** (`:28`: "合并版默认 windowed").
Other specs hardcode: `service:31` True, `api_win7:67` True, `web_win7:145,153` True,
`macos:109` False (`.app`) / `:145` True (CLI binary).

`win_stdio.py` (110 lines, all NT-guarded):

| Function | Line | Behaviour |
|---|---|---|
| `_wrap_handle(handle,name)` | `:23-41` | `msvcrt.open_osfhandle` + `TextIOWrapper(..., write_through=True, line_buffering=True, closefd=False)`; supplies `.buffer` because "MCP SDK 会用到" (`:24`) |
| `attach_inherited_stdio()->dict` | `:44-61` | `GetStdHandle(-10/-11/-12)`; skip if `(0,-1)` or `GetFileType(h)==0`; wrap (`:55-60`) |
| `attach_parent_console()->bool` | `:64-82` | `AttachConsole(-1)`, reopen `CONIN$`/`CONOUT$` |
| `silence_streams()` | `:85-97` | Remaining `None` → `os.devnull` |
| `setup_stdio()->str` | `:100-110` | Cascade, returns mode |

```python
pipe = attach_inherited_stdio()
if pipe.get("stdin") and pipe.get("stdout"): silence_streams(); return "inherited-pipe"
if attach_parent_console(): silence_streams(); return "parent-console"
silence_streams(); return "none"
```

It requires **both** stdin and stdout wrapped to accept the pipe path (`:103`).

`PCL_CONSOLE`/`PCL_ONEFILE` are build-time only — grepped: read solely at `pclradiomics.spec:27,29`,
`build_exe.bat:21-22`, `编译单文件版.bat:18`, `README.md:591,632`,
`build-windows.yml:110`. `PCL_ONEFILE` switches `EXE(...a.binaries,a.datas...)` (`:114-118`) vs
`EXE(exclude_binaries=True)+COLLECT` (`:119-124`); `PCL_CONSOLE` flips `console=`. Siblings:
`PCL_WEB_WITH_SCIPY` (`web_win7.spec:48`), `PCL_ARCH`/`PCL_VERSION` (`macos.spec:27-28`).

**Existing "console mode"**: only `attach_parent_console()` (`win_stdio.py:64`) and
`_utf8_console()` (`cli.py:84-93`, `stream.reconfigure(encoding="utf-8", errors="replace")` — text
layer only, not `.buffer`, "stdio MCP 的二进制管道不受影响" `:87`). `design_studio.py:4708` branches
on `sys.stdin.isatty()` to decide whether to wait on Enter. Nothing else.

**If built `console=True`:** the black window returns — `README.md:616-619` documents that on Win11
the console is hosted by Windows Terminal (another process) so `ShowWindow(GetConsoleWindow())`
cannot hide it ("实测确实会留下一个终端窗口"); `mcp_frozen.json:2` and `win_stdio.py:10` make the
same no-black-box promise. `_hide_own_console` also refuses to hide a *shared* console
(`owner != 1`, `cli.py:112-115`) — and it is **never called** (grep: only its `def` at `:96` plus
`pclradiomics.spec:16`), so today nothing hides anything. Upside: real streams make
`attach_inherited_stdio`/`attach_parent_console` no-ops (they skip non-`None`, `:53,74`), so
`setup_stdio()` returns `"none"` harmlessly, and `win_stdio` becomes redundant. **Nothing in code
depends on there being no console**; the dependents are (a) the documented UX contract,
(b) `_crash_log`+`_alert` which exist *because* windowed has no console (`cli.py:53`,
`README.md:649-652`), (c) `_test_console.py:39-58`, which enumerates visible Console/Terminal
windows before/after a double-click simulation and asserts no new ones, plus `_test_merged.py:143`
and `_test_onefile.py:90` GUI launches. Child flash is suppressed separately with
`CREATE_NO_WINDOW=0x08000000`+`STARTF_USESHOWWINDOW` (`manuscript_review/mr_office.py:34-41`).

## 3. `app_paths.py`

| Symbol | Line | Returns |
|---|---|---|
| `APP_NAME="PCLRadiomics"` / `APP_VERSION="1.3.0"` | `:18,20` | Version is single source (`api_server:32`, `mcp_server:42,53`, `web_server:72,266,377,432`) |
| `is_frozen()` | `:23` | `bool(sys.frozen)` |
| `_exe_dir()` / `_bundle_dir()` / `_source_dir()` | `:27,31,35` | exe dir / `sys._MEIPASS` or `""` / `dirname(__file__)` |
| `app_home()` | `:39-62` | Writable data dir |
| `resource_path(name)` | `:65-73` | Read-only asset |
| `data_path(*parts)` | `:76-84` | `app_home()/parts`, parent mkdir'd |
| `config_dir()` / `secret_path()` | `:87,105` | Per-user config / `secret.json` |
| `export_dir()` | `:110-131` | First writable user-visible dir |
| `describe()` | `:134` | `{frozen,executable,app_home,export_dir,bundle,source}` |

`app_home()` (`:45-62`): not frozen → `_source_dir()`. Frozen on darwin or when `".app/Contents/"`
is in the exe path → `~/Library/Application Support/PCLRadiomics`. Else exe dir *after a real
`.write_test` probe*; only if that throws → `%LOCALAPPDATA%\PCLRadiomics` (or `~` when unset).
`resource_path` (`:67-73`) tries `(exe_dir if frozen, _MEIPASS, _source_dir)` and returns the first
existing, else `app_home()/name` — so a user-dropped asset beside the exe shadows the bundled copy.
Writable paths deliberately never touch `_MEIPASS` (`README.md:637-640`).
`config_dir()` uses a *different* base than the `app_home` fallback: `%APPDATA%\PCLRadiomics`
(Roaming) on win32, `~/Library/Application Support` on darwin, `$XDG_CONFIG_HOME`/`~/.config`
elsewhere, falling back to `app_home()`. `export_dir()` probes `~/Documents/PCLRadiomics`,
`~/桌面/PCLRadiomics`, `~/Desktop/PCLRadiomics`, `~/PCLRadiomics`, `app_home()` (`:117-121`).

**`llm_config.json` at runtime** — `llm_client.py:27` `CONFIG_PATH = data_path("llm_config.json")`,
evaluated at import; `load_config()` reads it (`:121-125`), then `SECRET_PATH` (`:127-134`), then env
`LLM_BASE_URL/LLM_MODEL/LLM_TEMPERATURE`, key precedence saved > `LLM_API_KEY`/`api_key_env` >
`~/.dsh/.credentials.yaml` (`:135-148`). `save_config()` strips `api_key` from the portable file
(`:152-159`).

| Runtime | `llm_config.json` | `secret.json` |
|---|---|---|
| Source | repo root | `%APPDATA%\PCLRadiomics\` |
| Frozen onedir | exe dir (`dist\PCLRadiomics\`) | same |
| Frozen onefile | exe dir (`sys.executable` = the onefile exe, **not** `_MEIPASS`) | same |
| Exe dir unwritable | `%LOCALAPPDATA%\PCLRadiomics\` | unchanged |

Live evidence: `dist\llm_config.json` sits beside a onefile `dist\PCLRadiomics.exe` (88.6 MB).
Same rule for `error.log` (`cli.py:58`), `projects` (`design_agent.py:24`), `ui_prefs.json`
(`design_studio.py:4390`), `manuscript_review/projects` (`mr_engine.py:35`).
⚠️ These are module-level constants, so a mid-process `app_home` change is not re-read.

## 4. Build matrix

| Spec | Target OS | Console | onedir/onefile | Entry | Output | Notable excludes | collect_* / data | Size |
|---|---|---|---|---|---|---|---|---|
| `pclradiomics.spec` | Win10/11 x64 | `CONSOLE` env, **default False** `:29,117,122` | **both** via `PCL_ONEFILE` `:27,114-124` | `cli.py` `:86` | `PCLRadiomics` → `dist/PCLRadiomics` | `tkinter,matplotlib,IPython,notebook,numpy,PIL,Pillow,scipy,pandas,mkl,mkl_rt,numpy_distutils` `:95-96` | data: certifi, PyCt6, mcp, docx + 5 assets `:32-37`; submodules: mcp, anyio, httpx, httpcore, starlette, uvicorn, sse_starlette, pydantic, pydantic_core, sniffio, certifi, h11, PyCt6 + `_collect_local("manuscript_review")` `:39-70` | measured 88.6 MB onefile; README claims 148 MB dir / 65 MB file `:598-599` |
| `pclradiomics_service.spec` | Win x64 | **True** `:31` | onedir `:30,33` | `cli.py` `:25` | `PCLRadiomics服务` → `dist/PCLRadiomics-服务` | `PySide6,shiboken6,PyQt5,PyQt6,tkinter,matplotlib,numpy,PIL,scipy,pandas,IPython,notebook` `:26-27` | data: certifi, docx + assets `:12-14`; submodules mcp family + 6 local `:17-23` | ~54 MB per README `:633` (unverified) |
| `pclradiomics_web_win7.spec` | **Win7 SP1 x64, built on Python 3.8** `:5,24` | **True** `:145,153` | **both** in one run `:143-153` | **`web_server.py`** `:129` | `PCLRadiomicsWeb`; `dist-web` / `dist-web-scipy` | default `tkinter,matplotlib,IPython,notebook,pandas,PIL,Pillow,PySide6,shiboken6,PyCt6,design_studio,omics_pipeline,ui_kit,win_stdio,mcp,mcp_server,api_server,cli,numpy,scipy,mkl*` `:113-122`; +scipy adds `numpy.tests,scipy.tests,numpy.f2py,numpy.distutils,scipy.datasets,scipy.misc` `:125-126` | data `("web","web")`+certifi `:50-54`; `_extra_dlls()` globs `libssl/libcrypto/libffi/libbz2/liblzma/zlib/libxml2/libxslt/libexslt/iconv/charset`(+`libiomp5md` w/ scipy) `:57-89`; prepends conda `Library\bin`/`DLLs` to `PATH` `:94-99`; 10 local HIDDEN `:107-110` | measured 22.2 MB dir / 10.4 MB file; scipy 190.3 / 64.5 MB |
| `pclradiomics_api_win7.spec` | **Win7 SP1 x64, Python 3.8, pyinstaller==6.10** `:18-20` | **True** `:67` | onedir `:65,69` | **`api_server.py`** `:47` | `PCLRadiomicsAPI` | `tkinter,matplotlib,IPython,notebook,numpy,PIL,Pillow,scipy,pandas,mkl,mkl_rt,PySide6,shiboken6,PyCt6,design_studio,omics_pipeline,ui_kit,win_stdio,mcp,mcp_server,docx,docx_export` `:55-59` | data: certifi `:39-42`; HIDDEN `["app_paths","llm_client","api_server"]` `:44` | not measured |
| `pclradiomics_macos.spec` | macOS ≥11 `:124`; `PCL_ARCH` empty/universal2/x86_64/arm64 `:28` | GUI **False** `:109`, CLI **True** `:145` | onedir + `BUNDLE` `:107-130,143-147` | `cli.py` both `:99,134` | `PCLRadiomics.app` and `pclradiomics-cli/pclradiomics` | GUI `:101-103`; CLI adds `PySide6,shiboken6,PyQt5,PyQt6` `:136-139` | data certifi, PyCt6, mcp, docx + 7 assets `:30-36`; submodules mcp family + PyCt6 `:42-47`; `_collect_local("manuscript_review")` `:69` | ~50 MB CLI per README `:690` (unverified) |

**Pre-build validation:** in-spec import probe — `pclradiomics.spec:74-83` and
`pclradiomics_macos.spec:73-82` import `design_studio, omics_pipeline, manuscript_review,
docx_export, mcp_server, api_server` and `raise SystemExit("[打包中止] …")` on failure (motivated by
hardcoded `hiddenimports` not being recursed, `pclradiomics.spec:52-59`). CI import self-check:
`build-windows.yml:53-66`, `build-macos.yml:57-69`.
**Post-build:** `build-windows.yml:79-94` (`exe paths`, `stages`, `manuscript_review --selfcheck`
gating, `check` non-blocking), `:113-124` (onefile size + `stages` + `--selfcheck`),
`build-macos.yml:78-89`; `_check_win_target.py` PE import scan (`:22-34`) run by
`编译_Win7_Web版.bat:100-112` (exe + `_internal/python38.dll`, then `_test_web_exe.py`) and
`编译_Win7_API版.bat:66-70` (exit code not gated). `build_exe.bat:30-44` copies assets + mkdirs
`projects`; asset copying is duplicated in `编译单文件版.bat:23-26` and `build-windows.yml:72-77`.

## 5. `mcp.json` / `mcp_frozen.json`

`mcp.json`: `mcpServers.radiomics-workbench` → `command: D:\python\envs\mar\python.exe`,
`args: ["I:\文件\CTCC\HL\omics_pipeline\mcp_server.py"]`, `env: {}`.
`mcp_frozen.json`: same key, `command: I:\文件\CTCC\HL\omics_pipeline\dist\PCLRadiomics\PCLRadiomics.exe`,
`args: ["mcp"]`, plus a `_说明` note ("args 传 mcp（stdio 传输）。图形模式直接双击即可，不会有黑框。").

Both are **stdio** (no `transport`/`url`/`env`): the client spawns the command and speaks MCP over
stdin/stdout; the frozen one depends entirely on `win_stdio.attach_inherited_stdio()` because the exe
is windowed. Server identity `FastMCP("pcliomics-workbench")` (`mcp_server.py:50`), version forced
from `APP_VERSION` (`:53`), **21 tools** via `@mcp.tool()` (`:85,98,107,132,183,203,209,217,249,260,281,294,344,361,455,483,498,541,561,568,583`).
HTTP alternative `mcp --transport streamable-http --port 8765` (`cli.py:6`, `mcp_server.py:604-607`).
⚠️ Both files point at a stale `I:\文件\CTCC\HL\omics_pipeline\` path, not this root (README repeats
it at `:537-539,695-698`), and `README.md:525` says "12 个工具" vs 21 in code.

## 6. `requirements.txt`

Header recommends Python 3.11/3.12; PyCt6 needs `>=3.9,<3.14`.

| Package | Pin | Class |
|---|---|---|
| `PySide6` | `>=6.11,<7` | **Heavyweight, GUI-only**; excluded from service/API/Web/Win7 builds; drives the Win7 fork (Qt 6 has no Win7) |
| `PyCt6` | `>=6.1.0` | Wrapper over PySide6; its theme JSONs must be collected or the GUI exits silently (`pclradiomics.spec:35`, `README.md:644-645`) |
| `mcp` | `>=1.29,<2` | Core for MCP mode; pulls `httpx, anyio, starlette, uvicorn, sse-starlette, pydantic` |
| `certifi` | unpinned | Required — frozen Windows cert-store enumeration fails otherwise (`llm_client.py:104-116`, `README.md:641-643`) |
| `python-docx` | `>=1.1` | Word export; `templates/default.docx` must be collected (`pclradiomics.spec:37`); missing ⇒ Markdown-only, non-fatal (`编译_Win7_Web版.bat:80-84`) |
| `PyMuPDF` | `>=1.24` | **Optional/heavy**; PDF→DOCX. "缺失时导入 PDF 会明确报错、.docx 仍可用" (`:17-19`) |
| `pyinstaller` | `>=6.18,<7` | Build-only; Win7 must use `==6.10` (`api_win7.spec:20`) |

Not listed but conditionally bundled: `numpy`/`scipy` (only with `PCL_WEB_WITH_SCIPY=1`,
`web_win7.spec:109-126`, driven by `编译_Win7_Web版.bat:37-42,91`) and Intel MKL, which every main
spec strips (`pclradiomics.spec:101-109`, `macos.spec:85-87`; 592 MB → 148 MB per `README.md:646`).

## 7. External binaries / child processes today

**No spec bundles any executable:** `binaries=[]` at `pclradiomics.spec:88`, `service:25`,
`api_win7:49`, `macos:99,134`; the only non-empty is `web_win7.spec:102` (`_extra_dlls()`, DLLs
only). **There is no precedent for shipping a third-party `.exe`** — extension points are the
`datas`/`binaries` lists, `strip_mkl()`, and the post-build copy steps.

Existing integrations are discovery-based, never bundled:

- `manuscript_review/mr_office.py` — OfficeCLI. `OFFICECLI_PATH` (`:44`) → `shutil.which`
  (`:103-107`) → `_CANDIDATES` (`:83-89`: `%LOCALAPPDATA%\OfficeCLI\officecli.exe`,
  `%APPDATA%\npm\officecli.cmd`, `%LOCALAPPDATA%\npm-global\officecli.cmd`,
  `/usr/local/bin/officecli`, `/opt/homebrew/bin/officecli`). `_run()` (`:129-156`) always an arg
  list, never `shell=True` (`:131`); `DEFAULT_TIMEOUT=180` (`:45`); `startupinfo`+`CREATE_NO_WINDOW`
  on NT (`:137-139`); stdout decoded utf-8→gbk→cp936→latin-1 (`:159-169`).
- `web_server.py:354-372` `open_browser()` — `Popen([exe,url])` over `browser_candidates()`
  (`:~320-351`), fallback `webbrowser.open`.
- `design_studio.py:41-89` `_bootstrap_interpreter()` — the closest existing "bring your own
  runtime": probes `_PY_CANDIDATES` (`:32-37`) with `[exe,"-c","import PySide6, PyCt6"]` (`:66`),
  then **`os.execve(exe, [exe, __file__]+argv, env)`** with `PCLRADIOMICS_RELAUNCHED=1` as a loop
  guard (`:71-74`).
- `design_studio.py:4468` `Popen([sys.executable, HERE/"omics_pipeline.py"])` — ⚠️ frozen hazard: in
  a frozen build `sys.executable` is the bundler exe and `HERE` is `_MEIPASS`, so this would relaunch
  the GUI exe with a bogus arg; no guard exists.
- `cli.py:76-79` macOS `osascript -e "display dialog …"`; `design_studio.py:2458,3376`
  `Popen(["explorer","/select,",path])`.
- Tests spawn the built exe: `_test_merged.py:72,109,143`, `_test_onefile.py:53,90`,
  `_test_console.py:45` (`DETACHED_PROCESS|CREATE_NO_WINDOW`), `_test_web_exe.py:120` (+`taskkill
  /F /T /PID` `:258`), `_test_frozen_stdio.py:21`.

**Absent for an embedded agent binary:** no job object / `CREATE_NEW_PROCESS_GROUP`, no child-PID
registry, no `atexit`/`finally` reaper, no IPC abstraction, no health supervision beyond
`serve_forever`. `_MEIPASS2` propagation from a onefile parent to a child that is the same exe is
**unverified** — no code accounts for it.

## Flags — unconfirmed / discrepancies

1. `cli._hide_own_console()` (`:96-118`) is **dead code**, never called (repo-wide grep);
   `pclradiomics.spec:16` still claims the GUI calls it, contradicting `:28`.
2. `pclradiomics.spec:13-16` docstring is stale (argues console=True is mandatory; shipped default is
   windowed per `README.md:614-632`).
3. Sizes disagree: README 148 MB dir / 65 MB file (`:598-599`) vs measured `dist/PCLRadiomics.exe`
   = 88.6 MB onefile; `dist-onefile/` absent; service (~54 MB `:633`) and macOS CLI (~50 MB `:690`)
   unverified.
4. `README.md:525` says 12 MCP tools; code registers 21.
5. `mcp.json` / `mcp_frozen.json` reference a stale `I:\文件\CTCC\HL\omics_pipeline\` path.
6. Version skew: `APP_VERSION="1.3.0"` (`app_paths.py:20`) vs `macos.spec:27` default
   `PCL_VERSION="1.1.1"`.
7. `serve` mapping inconsistency (`cli.py:261` vs `:272-273`).
8. `编译_Win7_API版.bat:66-70` runs `_check_win_target.py` without gating on its exit code, and no
   CI workflow runs it at all — the PE-compat gate is not in CI.
9. No PyInstaller build was executed in this session; all console/windowed behaviour claims derive
   from code, repo docs, and the repo's own regression tests.
