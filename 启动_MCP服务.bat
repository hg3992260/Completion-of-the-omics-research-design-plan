@echo off
chcp 65001 >nul
setlocal
set "PY=D:\python\envs\mar\python.exe"
if not exist "%PY%" set "PY=D:\python\envs\rsna311\python.exe"
if not exist "%PY%" set "PY=python"
echo 组学研究设计工作台 · MCP 服务器（stdio，供 agent 调用）
echo 工具清单： "%PY%" "%~dp0mcp_server.py" --list-tools
"%PY%" "%~dp0mcp_server.py" %*
if errorlevel 1 pause
endlocal
