@echo off
chcp 65001 >nul
setlocal
set "REPO=hg3992260/Completion-of-the-omics-research-design-plan"

where gh >nul 2>nul
if errorlevel 1 (
  echo 未找到 gh（GitHub CLI）。请先安装：https://cli.github.com/
  pause
  exit /b 1
)

echo ============================================================
echo  在 GitHub 上触发一次编译，并额外产出**单文件版**
echo  仓库： %REPO%
echo.
echo  产物（约 3 分钟后）：Actions -^> 该次运行 -^> Artifacts
echo     PCLRadiomics-windows-x64.zip   文件夹版
echo     PCLRadiomics.exe               单文件版（onefile）
echo ============================================================

gh workflow run build-windows.yml --repo %REPO% -f onefile=true
if errorlevel 1 (
  echo.
  echo 触发失败。请确认已登录： gh auth login
  pause
  exit /b 1
)

echo.
echo 已提交构建请求，等待它出现在运行列表里...
timeout /t 6 >nul
gh run list --repo %REPO% --limit 3
echo.
echo 查看详情 / 下载产物：
echo   gh run list --repo %REPO% --limit 3
echo   gh run download ^<run-id^> --repo %REPO%
pause
endlocal
