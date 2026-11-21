@echo off
setlocal
set "launcher_dir=%~dp0"
cd /d "%launcher_dir%"
rem Prefer the project's reference Python, then other supported versions.
for %%V in (3.12 3.11 3.10 3.13 3.14) do (
    py -%%V -c "import sys; sys.exit(0)" >nul 2>nul
    if not errorlevel 1 (
        py -%%V "%launcher_dir%launch_demo.py" %*
        goto finished
    )
)
for %%P in (python python3) do (
    %%P -c "import sys; sys.exit(not ((3,10) <= sys.version_info[:2] <= (3,14)))" >nul 2>nul
    if not errorlevel 1 (
        %%P "%launcher_dir%launch_demo.py" %*
        goto finished
    )
)
echo Python 3.10 through 3.14 is needed. Python 3.12 is recommended.
echo Install it from https://www.python.org/downloads/ then run this file again.
echo Extract the downloaded repository ZIP before launching.
pause
exit /b 1
:finished
set "demo_exit=%errorlevel%"
if not "%demo_exit%"=="0" pause
exit /b %demo_exit%
