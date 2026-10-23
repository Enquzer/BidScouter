@echo off
title BidScouter — Ethiopian Garment Tender Tracker
echo ==============================================================
echo   BidScouter — Ethiopian Garment Tender Tracker
echo   Powered by Fashion-Flow 2026
echo   Created by Enquzer Getachew
echo ==============================================================
start "" pythonw "%~dp0run_server.py"
timeout /t 2 >nul
start "" http://127.0.0.1:7800
