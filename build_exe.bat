@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=D:\python\envs\mar\python.exe"
if not exist "%PY%" set "PY=D:\python\envs\rsna311\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  组学研究设计工作台 · 打包为 exe
echo.
echo  产物： dist\PCLRadiomics\PCLRadiomics.exe
echo         一个 exe 承载全部模式：
echo           PCLRadiomics.exe                图形界面（无控制台）
echo           PCLRadiomics.exe mcp            MCP stdio（供 DSH / Claude Desktop）
echo           PCLRadiomics.exe mcp --transport streamable-http --port 8765
echo           PCLRadiomics.exe api --port 8788
echo.
echo  可选环境变量：
echo     set PCL_ONEFILE=1   打成单文件 exe（下载方便，启动慢 3-8 秒）
echo     set PCL_CONSOLE=1   编成控制台版（调试用，会显示黑框）
echo.
echo  说明：打包过程中 stderr 上的 WARNING（某可选隐藏导入缺失）属正常，
echo        是否成功以最终是否生成 exe 为准。
echo ============================================================

"%PY%" -m PyInstaller --noconfirm --clean pclradiomics.spec

if exist "dist\PCLRadiomics" (
  for %%F in (theme_tech.json logo_icon.ico logo_badge.png logo_banner.png LOGO.jpg) do (
    if exist "%%F" copy /y "%%F" "dist\PCLRadiomics\" >nul
  )
  if not exist "dist\PCLRadiomics\projects" mkdir "dist\PCLRadiomics\projects"
)

if not exist "dist\PCLRadiomics\PCLRadiomics.exe" (
  if not exist "PCLRadiomics.exe" (
    echo.
    echo [失败] 未生成 exe，请把上面的报错发我。
    pause
    exit /b 1
  )
)

echo.
echo [成功] 产物已生成：
dir /b "dist\PCLRadiomics\PCLRadiomics.exe" 2>nul
dir /b "PCLRadiomics.exe" 2>nul
echo.
echo 自检（建议依次执行）：
echo   dist\PCLRadiomics\PCLRadiomics.exe check
echo   dist\PCLRadiomics\PCLRadiomics.exe net
echo   dist\PCLRadiomics\PCLRadiomics.exe api --port 8788
echo   dist\PCLRadiomics\PCLRadiomics.exe mcp
pause
endlocal
