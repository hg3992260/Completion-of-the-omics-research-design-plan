@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=D:\python\envs\mar\python.exe"
if not exist "%PY%" set "PY=D:\python\envs\rsna311\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  编译 opencode GUI（新皮肤会话窗口）
echo  产物：dist\OpenCodeGUI\OpenCodeGUI.exe（文件夹版，启动快，含内嵌内核）
echo.
echo  说明：单文件版请用 编译_OpenCodeGUI_单文件.bat
echo        （onefile 每次启动要解包，默认不塞 172MB 内核）
echo ============================================================

"%PY%" -m PyInstaller --noconfirm --clean --distpath dist opencode_gui.spec

if exist "dist\OpenCodeGUI\OpenCodeGUI.exe" (
  for %%F in (theme_skeuo.json theme_tech.json logo_icon.ico logo_badge.png logo_banner.png) do (
    if exist "%%F" copy /y "%%F" "dist\OpenCodeGUI\" >nul
  )
  if not exist "dist\OpenCodeGUI\_shots" mkdir "dist\OpenCodeGUI\_shots"
  echo.
  echo [成功] 产物：
  dir /b "dist\OpenCodeGUI\OpenCodeGUI.exe"
  echo.
  echo 自检（出深/浅两张界面图到 dist\OpenCodeGUI\_shots）：
  echo     dist\OpenCodeGUI\OpenCodeGUI.exe --shot
  echo 连内嵌内核：
  echo     dist\OpenCodeGUI\OpenCodeGUI.exe --live
) else (
  echo.
  echo [失败] 未生成 exe，请把上面的报错发我。
)
pause
endlocal
