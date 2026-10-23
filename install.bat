@echo off
title BidScouter Installer
color 0A

echo.
echo  ============================================================
echo   BidScouter - Ethiopia Garment Bid Intelligence System
echo   Installer
echo  ============================================================
echo.

REM -- Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo [1/5] Python found.

REM -- Install dependencies
echo [2/5] Installing Python packages...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)
echo        Done.

REM -- Install Playwright browsers (for JS-heavy sites)
echo [3/5] Installing Playwright browsers...
playwright install chromium --quiet 2>nul
echo        Done.

REM -- Initialize database
echo [4/5] Initializing database...
python -c "import sys; sys.path.insert(0,'%~dp0'); from backend.database import init_db; init_db(); print('DB ready')"
if errorlevel 1 (
    echo [WARNING] Database init had an issue. Will retry on first run.
)

REM -- Create Windows Task Scheduler entry (runs at startup)
echo [5/5] Registering with Windows Task Scheduler...
schtasks /delete /tn "BidScouter" /f >nul 2>&1
schtasks /create /tn "BidScouter" ^
    /tr "pythonw \"%~dp0run_server.py\"" ^
    /sc ONLOGON ^
    /rl HIGHEST ^
    /f >nul
if errorlevel 1 (
    echo [WARNING] Could not register task. You can run BidScouter manually.
) else (
    echo        BidScouter registered to start at Windows login.
)

REM -- Create desktop shortcut to open dashboard
echo.
REM -- Create Desktop shortcut with custom icon
powershell -command "$ws = New-Object -COM WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\BidScouter.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%~dp0Start_BidScouter.vbs\"'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = '%~dp0BidScouter.ico, 0'; $s.Description = 'BidScouter - Garment Tender Tracker (Powered by Fashion-Flow 2026)'; $s.Save()" 2>nul

echo.
echo  ============================================================
echo   Installation Complete!
echo.
echo   - BidScouter will START automatically when you log in.
echo   - To start NOW, double-click "Start BidScouter" on Desktop,
echo     then open: http://127.0.0.1:7800
echo.
echo   - To enter your site credentials, go to Settings in the
echo     dashboard BEFORE your first crawl.
echo  ============================================================
echo.
pause

REM -- Optionally start now
set /p START_NOW="Start BidScouter now? (Y/N): "
if /i "%START_NOW%"=="Y" (
    start "" pythonw "%~dp0run_server.py"
    timeout /t 3 >nul
    start "" http://127.0.0.1:7800
)
