@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%\contracts"
call npm.cmd run node
