@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  组学研究设计工作台 · Windows 7 Web 版（浏览器界面）打包
echo.
echo  产物：
echo    dist-web\PCLRadiomicsWeb\PCLRadiomicsWeb.exe   文件夹版（推荐）
echo    dist-web\PCLRadiomicsWeb.exe                   单文件版（便于传输）
echo.
echo  为什么 Win7 上用这个而不是桌面版：
echo    桌面版依赖 PySide6 / Qt 6，Qt 6 与 Python 3.9+ 都不支持 Win7；
echo    内嵌浏览器也不行（WebView2 运行时停在支持 Win7 的 109 版）。
echo    本版是"本地服务 + 系统浏览器"：纯标准库，用 Python 3.8 打包即可。
echo.
echo  目标机需要：
echo    Win7 SP1(x64) + KB2533623 + KB2999226(UCRT) + VC++2015-2019 运行库(x64)
echo    + Chrome 109 / Edge 109 / Firefox 115 ESR（Win7 上最后一批现代浏览器）
echo ============================================================
echo.

rem ---- 找一个 Python 3.8（必须是 3.8，3.9+ 的产物 Win7 起不来）----
set "PY="
for %%P in (
  "D:\python\envs\seq\python.exe"
  "D:\python\envs\dicom\python.exe"
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
  echo       py -3.8 -m pip install "pyinstaller==6.10" certifi python-docx
  echo   再重新运行本脚本。
  pause
  exit /b 1
)

echo [1/4] 使用解释器：%PY%
%PY% -c "import sys;print('      Python', sys.version.split()[0], '|', sys.executable)"

echo [2/4] 检查依赖（PyInstaller / certifi / python-docx）...
%PY% -c "import PyInstaller,certifi;print('      PyInstaller', PyInstaller.__version__, '| certifi OK')" 2>nul
if errorlevel 1 (
  echo       缺少依赖，尝试安装（需要联网）...
  %PY% -m pip install "pyinstaller==6.10" certifi || goto :fail
)
%PY% -c "import docx;print('      python-docx OK（可导出 Word）')" 2>nul
if errorlevel 1 (
  echo       [提示] 未安装 python-docx：产物只能导出 Markdown。
  echo              需要 Word 导出就执行：%PY% -m pip install python-docx
)

echo [3/4] 打包（约 1-2 分钟）...
%PY% -m PyInstaller --noconfirm --clean --distpath dist-web --workpath build-web pclradiomics_web_win7.spec || goto :fail

if not exist "dist-web\PCLRadiomicsWeb\PCLRadiomicsWeb.exe" goto :fail
if not exist "dist-web\PCLRadiomicsWeb.exe" goto :fail

echo.
echo [4/4] 自检
echo ---- Windows 7 兼容性（PE 导入检查）----
if exist "D:\python\envs\mar\python.exe" (
  "D:\python\envs\mar\python.exe" _check_win_target.py "dist-web\PCLRadiomicsWeb\PCLRadiomicsWeb.exe"
  "D:\python\envs\mar\python.exe" _check_win_target.py "dist-web\PCLRadiomicsWeb\_internal\python38.dll"
  echo ---- 端到端（起真 exe，验接口 / 静态资源 / SSE / Word 导出 / 浏览器渲染）----
  "D:\python\envs\mar\python.exe" _test_web_exe.py
) else (
  %PY% _check_win_target.py "dist-web\PCLRadiomicsWeb\PCLRadiomicsWeb.exe"
  echo [提示] 想跑完整端到端自检，请用任意 Python 3.9+ 执行：python _test_web_exe.py
)

echo.
echo [成功] 产物：
echo     dist-web\PCLRadiomicsWeb\PCLRadiomicsWeb.exe   ← 整个文件夹拷到 Win7
echo     dist-web\PCLRadiomicsWeb.exe                   ← 或只要这一个文件（启动稍慢）
echo.
echo 拷到 Win7 机器后：
echo     双击 PCLRadiomicsWeb.exe
echo        → 本机起服务（默认 127.0.0.1:8787）并自动用 Chrome/Edge/Firefox 打开界面
echo     想换端口/不自动开浏览器：
echo        PCLRadiomicsWeb.exe --port 8899 --no-browser
echo     局域网共享（慎用，会暴露带密钥的服务）：
echo        PCLRadiomicsWeb.exe --host 0.0.0.0 --token 你的口令
echo.
echo 数据落盘：projects\ 与界面数据都在 exe 同级目录（绿色便携，可整体拷走）
pause
exit /b 0

:fail
echo.
echo [失败] 打包未完成，请把上面的报错发我。
pause
exit /b 1
