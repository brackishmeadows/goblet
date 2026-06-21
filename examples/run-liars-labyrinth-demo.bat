@echo off
cd /d "%~dp0.."
"C:\Users\iamru\OneDrive\Desktop\field-office\tools\python-3.13.13-embed-amd64\python.exe" run.py --labyrinth examples\liars-labyrinth-demo.txt
echo.
echo Demo complete.
echo Press any key to close this window.
pause >nul
