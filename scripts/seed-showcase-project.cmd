@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
python "%ROOT%\scripts\seed_showcase_project.py"
