@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%\apps\web"
call npm.cmd run dev -- --host 127.0.0.1
