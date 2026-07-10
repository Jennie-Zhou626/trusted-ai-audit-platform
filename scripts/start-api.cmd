@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%\apps\api"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
