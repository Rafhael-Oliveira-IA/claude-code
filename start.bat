@echo off
cd /d F:\claude-code
start "Claude Proxy" cmd /k "python proxy.py"
timeout /t 2 /nobreak >nul
start "Claude Code" cmd /k "python run.py"
