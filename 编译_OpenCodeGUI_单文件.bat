@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=D:\python\envs\mar\python.exe"
if not exist "%PY%" set "PY=D:\python\envs\rsna311\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  opencode GUI 单文件版（onefile）
echo  产物：dist-onefile\OpenCodeGUI.exe
echo.
echo  注意：单文件版**默认不含** 172MB 内嵌内核 —— onefile 每次启动都要
echo        解包到 %%TEMP%%，塞进内核会让启动恶化到 10 秒以上。
echo        要连内核：把 opencode.exe 放到 exe 同级的 opencode\ 目录，
echo        或设环境变量 PCL_OPENCODE_EXE 指向它（界面在演示模式下仍可浏览）。
echo        真要做"含内核的单文件版"：先 set PCL_ONEFILE_WITH_KERNEL=1 再编。
echo ============================================================

set PCL_ONEFILE=1
"%PY%" -m PyInstaller --noconfirm --clean --distpath dist-onefile opencode_gui.spec
set PCL_ONEFILE=

if exist "dist-onefile\OpenCodeGUI.exe" (
  for %%F in (theme_skeuo.json theme_tech.json logo_icon.ico logo_badge.png logo_banner.png) do (
    if exist "%%F" copy /y "%%F" "dist-onefile\" >nul
  )
  echo.
  echo [成功] 单文件产物：
  dir /b "dist-onefile\OpenCodeGUI.exe"
  echo.
  echo 自检： dist-onefile\OpenCodeGUI.exe --shot
) else (
  echo.
  echo [失败] 未生成 exe，请把上面的报错发我。
)
pause
endlocal
