@echo off
chcp 65001 >nul
setlocal
set "PY=D:\python\envs\mar\python.exe"
if not exist "%PY%" set "PY=D:\python\envs\rsna311\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0omics_pipeline.py"
if errorlevel 1 pause
endlocal
