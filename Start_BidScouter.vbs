Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\my_codes\Bidscouter"
WshShell.Run "pythonw run_server.py", 0, False
WScript.Sleep 2500
WshShell.Run "http://127.0.0.1:7800", 1, False
