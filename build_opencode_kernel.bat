@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: ============================================================================
::  准备内嵌用的 opencode 内核二进制
::
::  产物：%~dp0opencode\opencode.exe
::
::  默认方式：从 GitHub release 下载（CI 构建、已签名、可复现）。
::  备选方式：--from-source 从源码构建，走 build_opencode_kernel.bat 的完整流程。
::
::  为什么默认下载：二进制 172.3 MB，超过 GitHub 单文件 100 MB 硬上限，无法入库；
::  且本地构建另有四个坑（下面有记录）。release 资产名 opencode-windows-x64.zip
::  与内置版本号一一对应，便于脚本校验。
::
::  用法：
::    build_opencode_kernel.bat                下载 1.18.35（默认）
::    build_opencode_kernel.bat --baseline      非 AVX2 老 CPU 变体
::    build_opencode_kernel.bat --from-source   从源码构建（见下方四坑）
::
::  ── 从源码构建时的四个坑（P0 实测，务必按此处理）────────────────────────
::   [坑1] 该 checkout 不是 git 仓库
::         packages\script\src\index.ts:30 用 `git branch --show-current` 决定发布
::         渠道，非 git 目录会 `fatal: not a git repository` + exit 128，构建直接失败。
::         修法：设 OPENCODE_CHANNEL + OPENCODE_VERSION
::         （前者跳过 git 调用，后者跳过 npm registry 查询，保证离线可重复）
::
::   [坑2] bun install 会在 tree-sitter-powershell 的 postinstall 原生编译上失败
::         （node-gyp 在 Bun 的 .bun 目录布局下拼不出 node-addon-api 的中间路径）。
::         修法：bun install --ignore-scripts
::         内核运行期走的是 web-tree-sitter(WASM)，不需要该原生 addon；
::         core 的 fix-node-pty 只影响 PTY 功能。
::
::   [坑3] 首次 install 中断会污染依赖链接
::         中断后再 install 会出现多个包 `failed to link package ... (copyfile)`
::         ENOENT，构建时报 `Could not resolve: @opentelemetry/resources` 等。
::         修法：中断后必须清理 node_modules 再重装。
::
::   [坑4] generate.ts 需要联网拉 models.dev 快照
::         script/generate.ts:10-13；离线环境用 MODELS_DEV_API_JSON 指向本地 api.json。
::
::   另：加 --skip-embed-web-ui 可省掉 packages/app 的整趟 Vite 构建
::       （内核 UI 用 TUI，见决策 D7），二进制也更小。
:: ============================================================================

if /i "%~1"=="--from-source" goto :from_source

:: ── 默认：下载 release 二进制 ──────────────────────────────────────────────
set "PY=python"
if exist "D:\python\envs\mar\python.exe" set "PY=D:\python\envs\mar\python.exe"
if exist "D:\python\envs\rsna311\python.exe" if not exist "D:\python\envs\mar\python.exe" set "PY=D:\python\envs\rsna311\python.exe"

echo ============================================================
echo  获取 opencode 内核二进制（release 下载）
echo ============================================================
"%PY%" "%~dp0get_opencode_kernel.py" %*
set RC=!errorlevel!
if not "!RC!"=="0" (
  echo.
  echo [失败] 下载未成功。若本机无外网，可改用：
  echo         build_opencode_kernel.bat --from-source
  echo         （或手工把 opencode-windows-x64.zip 解压到 opencode\）
)
endlocal & exit /b %RC%


:from_source
:: ── 备选：从源码构建 ──────────────────────────────────────────────────────
if not defined OC_ROOT set "OC_ROOT=%~dp0..\opencode-dev\opencode-dev"
if not defined OC_VERSION set "OC_VERSION=1.18.35"

if not exist "%OC_ROOT%\packages\opencode\script\build.ts" (
  echo [失败] 找不到 opencode 源码仓库：%OC_ROOT%
  echo        请设置 OC_ROOT 指向 opencode-dev\opencode-dev
  exit /b 1
)
where bun >nul 2>nul
if errorlevel 1 (
  echo [失败] PATH 里没有 bun。从源码构建需要 bun。
  exit /b 1
)

echo ============================================================
echo  从源码构建 opencode（%OC_VERSION%）
echo    仓库 %OC_ROOT%
echo ============================================================

set ELECTRON_SKIP_BINARY_DOWNLOAD=1
:: [坑1] 跳过 git 调用与 npm registry 查询
set OPENCODE_CHANNEL=latest
set OPENCODE_VERSION=%OC_VERSION%

echo.
echo [1/3] 安装依赖（--ignore-scripts，见坑2）...
pushd "%OC_ROOT%"
call bun install --ignore-scripts
if errorlevel 1 (
  echo [失败] bun install 失败（若是上次中断留下坏状态，先删 node_modules 重来 —— 见坑3）
  popd
  exit /b 1
)

echo.
echo [2/3] 构建二进制（--skip-embed-web-ui）...
pushd "%OC_ROOT%\packages\opencode"
call bun run script/build.ts --single --skip-install --skip-embed-web-ui
set BUILD_RC=!errorlevel!
popd
if not "!BUILD_RC!"=="0" (
  echo [失败] 构建失败（exit !BUILD_RC!）
  popd
  exit /b !BUILD_RC!
)
popd

set "SRC=%OC_ROOT%\packages\opencode\dist\opencode-windows-x64\bin\opencode.exe"
if not exist "%SRC%" (
  echo [失败] 未产出二进制：%SRC%
  exit /b 1
)

if not exist "%~dp0opencode" mkdir "%~dp0opencode"
copy /y "%SRC%" "%~dp0opencode\opencode.exe" >nul
echo.
echo [3/3] 校验产物...
"%~dp0opencode\opencode.exe" --version
if errorlevel 1 (
  echo [失败] 二进制无法运行
  exit /b 1
)

for %%F in ("%~dp0opencode\opencode.exe") do set /a SIZE_MB=%%~zF/1048576
echo.
echo ============================================================
echo  [成功] %~dp0opencode\opencode.exe
echo         体积约 !SIZE_MB! MB
echo.
echo  下一步：自检
echo    python cli.py kernel selftest
echo ============================================================
endlocal
