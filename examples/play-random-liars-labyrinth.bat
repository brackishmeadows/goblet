@echo off
set "ROOT=%~dp0.."
set "PYTHON=C:\Users\iamru\OneDrive\Desktop\field-office\tools\python-3.13.13-embed-amd64\python.exe"
start "Random Liar's Labyrinth" cmd /k "cd /d "%ROOT%" && "%PYTHON%" run.py --labyrinth-random-play %*"
