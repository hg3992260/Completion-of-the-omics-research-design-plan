@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

:: ============================================================================
::  编译「内嵌 opencode 内核」的两个 Windows 产物
::
::  为什么是两个变体（决策 D2 + 风险 13）：
::    · PCLRadiomics.exe         windowed —— 双击 GUI 时没有黑框，主程序
::    · PCLRadiomicsConsole.exe  console  —— 带真实控制台，用于 kernel 配置/诊断
::    若都叫 PCLRadiomics 会互相覆盖，所以用 PCL_APP_NAME 区分。
::
::  为什么不用一个 console exe 打天下：
::    Win11 的控制台由 Windows Terminal 托管（属于别的进程），
::    ShowWindow(GetConsoleWindow()) 藏不掉 —— 双击 GUI 必然多一个终端窗口。
::    这是实测结论（见 README「一个 exe 同时当界面程序和 stdio 服务」）。
::
::  前置：内核二进制 172.3 MB 不入库，先下载到 opencode\
::
::  用法：
::    编译_内核版.bat              两个变体都编
::    编译_内核版.bat --console    只编 console 变体
::    编译_内核版.bat --windowed   只编 windowed 变体
::    编译_内核版.bat --onefile    额外编单文件版（不含内核 —— 见下）
::
::  注意：单文件版不打包内核。
::    onefile 每次启动要把内容解包到 %TEMP%；再塞一个 172 MB 的内核会让启动
::    严重恶化，而且 MCP 客户端会反复拉起进程 → 反复解包。故 onefile 走
::    PCL_SKIP_KERNEL=1（决策 D5 的连带结论，见 plan §4.3）。
:: ============================================================================

set "PY=python"
if exist "D:\python\envs\mar\python.exe" set "PY=D:\python\envs\mar\python.exe"

set DO_WINDOWED=0
set DO_CONSOLE=0
set DO_ONEFILE=0
set ONLY=0
if /i "%~1"=="" set DO_WINDOWED=1 && set DO_CONSOLE=1
if /i "%~1"=="--windowed" set DO_WINDOWED=1 && set ONLY=1
if /i "%~1"=="--console" set DO_CONSOLE=1 && set ONLY=1
if /i "%~1"=="--onefile" set DO_ONEFILE=1 && set ONLY=1
if "%ONLY%"=="0" if not "%~1"=="" set DO_WINDOWED=1 && set DO_CONSOLE=1

echo ============================================================
echo  编译内嵌 opencode 内核的产物
echo    windowed: %DO_WINDOWED%   console: %DO_CONSOLE%   onefile: %DO_ONEFILE%
echo ============================================================

:: ── 前置：内核二进制 ──────────────────────────────────────────────────────
if not exist "opencode\opencode.exe" (
  echo.
  echo [前置] 未找到 opencode\opencode.exe，先下载...
  "%PY%" get_opencode_kernel.py
  if errorlevel 1 (
    echo [失败] 内核二进制获取失败。
    echo        离线环境请运行：build_opencode_kernel.bat --from-source
    pause
    exit /b 1
  )
)

:: ── 前置：自检 ────────────────────────────────────────────────────────────
echo.
echo [前置] 内核自检...
"%PY%" cli.py kernel selftest
if errorlevel 1 (
  echo [失败] 内核自检未通过，先修好再打包。
  pause
  exit /b 1
)

:: ── windowed 主程序 ──────────────────────────────────────────────────────
if "%DO_WINDOWED%"=="1" (
  echo.
  echo ========== [1/2] windowed 主程序 PCLRadiomics.exe ==========
  "%PY%" -m PyInstaller --noconfirm --clean pclradiomics.spec
  if errorlevel 1 ( echo [失败] windowed 构建失败 & pause & exit /b 1 )
  if not exist "dist\PCLRadiomics\PCLRadiomics.exe" (
    echo [失败] 未生成 dist\PCLRadiomics\PCLRadiomics.exe & pause & exit /b 1
  )
  for %%F in (theme_tech.json logo_icon.ico logo_badge.png logo_banner.png LOGO.jpg) do (
    if exist "%%F" copy /y "%%F" "dist\PCLRadiomics\" >nul
  )
  if not exist "dist\PCLRadiomics\projects" mkdir "dist\PCLRadiomics\projects"
  echo [校验] 冻结产物里的内核...
  "dist\PCLRadiomics\PCLRadiomics.exe" kernel selftest
  if errorlevel 1 ( echo [失败] 冻结产物内核自检不通过 & pause & exit /b 1 )
)

:: ── console 变体 ─────────────────────────────────────────────────────────
if "%DO_CONSOLE%"=="1" (
  echo.
  echo ========== [2/2] console 变体 PCLRadiomicsConsole.exe ==========
  set PCL_CONSOLE=1
  set PCL_APP_NAME=PCLRadiomicsConsole
  "%PY%" -m PyInstaller --noconfirm --clean --distpath dist-console pclradiomics.spec
  set PCL_APP_NAME=
  set PCL_CONSOLE=
  if errorlevel 1 ( echo [失败] console 构建失败 & pause & exit /b 1 )
  if not exist "dist-console\PCLRadiomicsConsole\PCLRadiomicsConsole.exe" (
    echo [失败] 未生成 dist-console\PCLRadiomicsConsole\PCLRadiomicsConsole.exe
    pause & exit /b 1
  )
  for %%F in (theme_tech.json logo_icon.ico logo_badge.png logo_banner.png LOGO.jpg) do (
    if exist "%%F" copy /y "%%F" "dist-console\PCLRadiomicsConsole\" >nul
  )
  if not exist "dist-console\PCLRadiomicsConsole\projects" mkdir "dist-console\PCLRadiomicsConsole\projects"
  echo [校验] 冻结产物里的内核...
  "dist-console\PCLRadiomicsConsole\PCLRadiomicsConsole.exe" kernel selftest
  if errorlevel 1 ( echo [失败] console 变体内核自检不通过 & pause & exit /b 1 )
)

:: ── 单文件版（不含内核）──────────────────────────────────────────────────
if "%DO_ONEFILE%"=="1" (
  echo.
  echo ========== [附加] 单文件版（不含内核，见脚本头说明）==========
  set PCL_ONEFILE=1
  set PCL_SKIP_KERNEL=1
  "%PY%" -m PyInstaller --noconfirm --clean --distpath dist-onefile pclradiomics.spec
  set PCL_SKIP_KERNEL=
  set PCL_ONEFILE=
  if errorlevel 1 ( echo [失败] 单文件构建失败 & pause & exit /b 1 )
)

echo.
echo ============================================================
echo  [成功] 产物：
if "%DO_WINDOWED%"=="1" echo    dist\PCLRadiomics\PCLRadiomics.exe
if "%DO_CONSOLE%"=="1"  echo    dist-console\PCLRadiomicsConsole\PCLRadiomicsConsole.exe
if "%DO_ONEFILE%"=="1"  echo    dist-onefile\PCLRadiomics.exe  （不含内核）
echo.
echo  自检建议：
echo    dist\PCLRadiomics\PCLRadiomics.exe kernel status
echo    dist\PCLRadiomics\PCLRadiomics.exe kernel auth import-host
echo    dist\PCLRadiomics\PCLRadiomics.exe kernel mcp host
echo    dist\PCLRadiomics\PCLRadiomics.exe kernel ui
echo ============================================================
pause
endlocal
