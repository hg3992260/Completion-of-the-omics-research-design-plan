@echo off
chcp 65001 >nul
setlocal
set "PY=D:\python\envs\mar\python.exe"
if not exist "%PY%" set "PY=D:\python\envs\rsna311\python.exe"
if not exist "%PY%" set "PY=python"
echo 组学研究设计工作台 · 独立推理服务（OpenAI 兼容）
echo   http://127.0.0.1:8788/v1     （仅本机；局域网共享加 --host 0.0.0.0 --token 口令）
"%PY%" "%~dp0api_server.py" --port 8788 %*
if errorlevel 1 pause
endlocal
