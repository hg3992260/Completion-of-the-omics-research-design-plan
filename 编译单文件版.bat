@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=D:\python\envs\mar\python.exe"
if not exist "%PY%" set "PY=D:\python\envs\rsna311\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  本地打包：单文件版（onefile）
echo  产物： dist-onefile\PCLRadiomics.exe
echo.
echo  说明：单文件版启动时要把内容解包到 %%TEMP%%，首次启动约 3-5 秒；
echo        图形界面约 10 秒。要启动更快就用 build_exe.bat 出文件夹版。
echo ============================================================

set PCL_ONEFILE=1
"%PY%" -m PyInstaller --noconfirm --clean --distpath dist-onefile pclradiomics.spec
set PCL_ONEFILE=

if exist "dist-onefile\PCLRadiomics.exe" (
  for %%F in (theme_tech.json logo_icon.ico logo_badge.png logo_banner.png LOGO.jpg) do (
    if exist "%%F" copy /y "%%F" "dist-onefile\" >nul
  )
  if not exist "dist-onefile\projects" mkdir "dist-onefile\projects"
  echo.
  echo [成功] 单文件产物：
  dir /b "dist-onefile\PCLRadiomics.exe"
  echo.
  echo 自检： dist-onefile\PCLRadiomics.exe check
) else (
  echo.
  echo [失败] 未生成 exe，请把上面的报错发我。
)
pause
endlocal
