@echo off
chcp 65001 >nul
REM ============================================================
REM R1-VLA 离线自学习 Agent · Windows 一键安装
REM 仅用标准库, 不需要 pip 安装任何包; 断网可用。
REM 若想让离线问答更完整, 先联网时执行一次: ollama pull qwen2.5:7b
REM ============================================================
setlocal
cd /d "%~dp0"
set PY=%~dp0.venv\Scripts\python.exe
if not exist "%PY%" set PY=python

echo [1/3] 构建/载入本地知识库...
"%PY%" start.py --offline
if errorlevel 1 (
  echo 知识库构建失败, 请确认已安装 Python 3.9+
  pause & exit /b 1
)

echo [2/3] 注册每日 20h 内测计划任务 (本机离线自学习)...
schtasks /create /tn "R1VLA_Offline_SelfLearn" /tr "\"%PY%\" \"%~dp0start.py\" --offline --loop --budget 72000" /sc daily /st 02:10 /f >nul 2>&1
if errorlevel 1 (
  echo  (跳过计划任务注册, 可能权限不足; 可手动在任务计划程序添加)
) else (
  echo   已注册: 每天 02:10 启动 20h 内测窗口
)

echo [3/3] 完成。启动控制台请运行 start.bat
echo 控制台地址: http://127.0.0.1:18941  (仅本机, 不对外)
pause
endlocal
