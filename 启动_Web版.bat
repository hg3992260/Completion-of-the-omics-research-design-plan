@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  组学研究设计工作台 · Web 版（浏览器界面）
echo.
echo  形态：本机起一个服务，用系统浏览器打开界面（默认 127.0.0.1:8787）。
echo        这是 Windows 7 上唯一能拿到现代界面的路线 ——
echo        Qt 6 不支持 Win7，WebView2 运行时也停在支持 Win7 的 109 版。
echo.
echo  浏览器：Chrome 109 / Edge 109 / Firefox 115 ESR 三者任一
echo          （Win7 上最后一批支持现代界面的浏览器）。
echo          即使系统默认浏览器是 IE11 也没关系，脚本会优先挑上面这三个。
echo.
echo  参数：可追加 --port 8899 --no-browser --verbose 等，直接透传。
echo ============================================================
echo.

rem ---- 找一个 Python 3.8 起（Win7 上只能装到 3.8）----
set "PY="
for %%P in (
  "D:\python\envs\mar\python.exe"
  "D:\python\envs\dicom\python.exe"
  "D:\python\envs\seq\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python38\python.exe"
  "C:\Python38\python.exe"
  "py -3.8"
  "py -3"
  "python"
) do (
  if not defined PY (
    %%~P -c "import sys;assert sys.version_info[:2]>=(3,8)" >nul 2>&1
    if not errorlevel 1 set "PY=%%~P"
  )
)

if not defined PY (
  echo [错误] 没找到 Python 3.8 或更高版本。
  echo.
  echo   Windows 7 请安装 Python 3.8 x64（3.9 起官方不再支持 Win7）：
  echo       https://www.python.org/downloads/release/python-3810/
  echo   安装时务必勾选 "Add Python to PATH"，然后重新运行本脚本。
  echo.
  echo   Windows 10/11 装任意 3.9+ 均可。
  pause
  exit /b 1
)

echo [1/3] 解释器：%PY%
%PY% -c "import sys;print('      Python', sys.version.split()[0], '|', sys.executable)"

echo [2/3] 依赖检查（本程序只用标准库）
%PY% -c "import certifi;print('      certifi OK（HTTPS 根证书）')" 2>nul
if errorlevel 1 echo      [提示] 未安装 certifi；若连不上模型，执行：%PY% -m pip install certifi

if not exist "web\index.html" (
  echo [错误] 找不到界面文件 web\index.html，请确认在本程序目录下运行。
  pause
  exit /b 1
)

echo [3/3] 启动服务（会自动打开浏览器；关闭本窗口即结束服务）
echo.
%PY% web_server.py %*
echo.
echo 服务已结束。
pause
exit /b 0
