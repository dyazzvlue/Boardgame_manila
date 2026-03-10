@echo off
REM 构建 Manila Windows .exe
REM 在 Windows 上运行此脚本（需要已安装 Python + pip）
cd /d "%~dp0"
pip install pyinstaller pygame -q

if not exist "bin\windows" mkdir "bin\windows"

pyinstaller --onefile ^
  --name manila ^
  --add-data "data;data" ^
  --hidden-import gui ^
  --hidden-import gui.bridge ^
  --hidden-import gui.renderer ^
  --hidden-import constants ^
  --hidden-import player ^
  --hidden-import ai ^
  --hidden-import game ^
  --hidden-import market ^
  --hidden-import ship ^
  --hidden-import board ^
  --hidden-import logger ^
  --hidden-import pygame ^
  --hidden-import pygame.font ^
  --hidden-import pygame.mixer ^
  --hidden-import pygame.image ^
  --exclude-module matplotlib ^
  --exclude-module scipy ^
  --exclude-module numpy ^
  --exclude-module pandas ^
  --exclude-module PIL ^
  --exclude-module cv2 ^
  --exclude-module tkinter ^
  --noconsole ^
  --distpath "bin\windows" ^
  gui_main.py

echo Done: bin\windows\manila.exe
pause
