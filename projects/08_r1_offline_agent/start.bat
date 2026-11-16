@echo off
chcp 65001 >nul
REM 启动离线控制台 + 后台自学习 (断网可用, 仅本机 127.0.0.1:18941)
setlocal
cd /d "%~dp0"
set PY=%~dp0.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
"%PY%" start.py --offline --web --loop --budget 72000
endlocal
