@echo off
cd /d "%~dp0"
py -3 -c "import codex_tasks,json; print(json.dumps(codex_tasks.health(),indent=2))"
pause
