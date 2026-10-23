@echo off
title BidScouter Uninstaller
echo Removing BidScouter from Task Scheduler...
schtasks /delete /tn "BidScouter" /f
echo Killing any running BidScouter processes...
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq BidScouter*" >nul 2>&1
echo Done. BidScouter has been uninstalled.
echo (Your data in data\bids.db is preserved.)
pause
