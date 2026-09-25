@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  组学研究设计工作台 · Windows 7 版（仅 API 服务，无图形界面）
echo.
echo  产物：dist\PCLRadiomicsAPI\PCLRadiomicsAPI.exe
echo        启动：PCLRadiomicsAPI.exe --port 8788
echo.
echo  为什么没有图形界面：
echo    GUI 依赖 PySide6 / Qt 6，而 Qt 6 与 Python 3.9+ 都不支持 Windows 7。
echo    本脚本用 Python 3.8 只打包不需要 Qt 的推理 API 服务。
echo.
echo  目标机需要：Win7 SP1(x64) + KB2533623 + KB2999226(UCRT) + VC++2015-2019 运行库
echo ============================================================
echo.

rem ---- 找一个 Python 3.8（必须是 3.8，3.9+ 的产物 Win7 起不来）----
set "PY="
for %%P in (
  "D:\python\envs\dicom\python.exe"
  "D:\python\envs\seq\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python38\python.exe"
  "C:\Python38\python.exe"
  "py -3.8"
) do (
  if not defined PY (
    %%~P -c "import sys;assert sys.version_info[:2]==(3,8)" >nul 2>&1
    if not errorlevel 1 set "PY=%%~P"
  )
)

if not defined PY (
  echo [错误] 没找到 Python 3.8。
  echo.
  echo   Windows 7 只能用 Python 3.8 构建（3.9 起官方不再支持 Win7）。
  echo   请先安装 Python 3.8 x64：https://www.python.org/downloads/release/python-3810/
  echo   然后执行：
  echo       py -3.8 -m pip install "pyinstaller==6.10" certifi
  echo   再重新运行本脚本。
  pause
  exit /b 1
)

echo [1/3] 使用解释器：%PY%
%PY% -c "import sys;print('      Python', sys.version.split()[0])"

echo [2/3] 检查 PyInstaller / certifi ...
%PY% -c "import PyInstaller,certifi;print('      PyInstaller',PyInstaller.__version__,'| certifi OK')" 2>nul
if errorlevel 1 (
  echo      缺少依赖，尝试安装（需要联网）...
  %PY% -m pip install "pyinstaller==6.10" certifi || goto :fail
)

echo [3/3] 打包 ...
%PY% -m PyInstaller --noconfirm --clean pclradiomics_api_win7.spec || goto :fail

if not exist "dist\PCLRadiomicsAPI\PCLRadiomicsAPI.exe" goto :fail

echo.
echo [成功] 产物：dist\PCLRadiomicsAPI\PCLRadiomicsAPI.exe
echo.
echo 自检（应报告「未发现 Win8+/Win10+ 专有 API set」）：
if exist "D:\python\envs\mar\python.exe" (
  "D:\python\envs\mar\python.exe" _check_win_target.py "dist\PCLRadiomicsAPI\PCLRadiomicsAPI.exe"
) else (
  %PY% _check_win_target.py "dist\PCLRadiomicsAPI\PCLRadiomicsAPI.exe"
)
echo.
echo 拷到 Win7 机器后：
echo    PCLRadiomicsAPI.exe --port 8788
echo    PCLRadiomicsAPI.exe --host 0.0.0.0 --token 你的口令 --port 8788
echo    客户端： base_url=http://<那台机器>:8788/v1
pause
exit /b 0

:fail
echo.
echo [失败] 打包未完成，请把上面的报错发我。
pause
exit /b 1
