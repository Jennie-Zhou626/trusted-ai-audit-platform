@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%\contracts"
call npm.cmd install
call npm.cmd run compile
call npm.cmd run deploy
