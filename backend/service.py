"""
BidScouter - Windows Service Wrapper
Installs and runs BidScouter as a Windows service.
"""
import sys
import os
import logging
import subprocess
import time

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager

    class BidScouterService(win32serviceutil.ServiceFramework):
        _svc_name_ = "BidScouter"
        _svc_display_name_ = "BidScouter - Ethiopia Bid Intelligence"
        _svc_description_ = "Crawls bid websites and sends reminders for garment-related tenders in Ethiopia."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self._proc = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)
            if self._proc:
                self._proc.terminate()

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            self._run()

        def _run(self):
            python_exe = sys.executable
            main_py = os.path.join(BASE_DIR, "run_server.py")
            self._proc = subprocess.Popen(
                [python_exe, main_py],
                cwd=BASE_DIR,
            )
            # Wait for stop signal
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    if __name__ == "__main__":
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(BidScouterService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32serviceutil.HandleCommandLine(BidScouterService)

except ImportError:
    # pywin32 not available - just run directly
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("bidscouter.service")
    logger.warning("pywin32 not installed. Running in direct mode.")

    if __name__ == "__main__":
        import uvicorn
        from backend.main import app
        uvicorn.run(app, host="127.0.0.1", port=7800, log_level="info")
