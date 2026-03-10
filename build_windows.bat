@echo off
REM 构建 Manila Windows .exe
REM 在 Windows 上运行此脚本（需要已安装 Python + pip）
cd /d "%~dp0"
pip install pyinstaller pygame -q
pyinstaller --onefile ^
  --name manila ^
  --add-data "data;data" ^
  --exclude-module matplotlib ^
  --exclude-module scipy ^
  --exclude-module numpy ^
  --exclude-module pandas ^
  --exclude-module PIL ^
  --exclude-module cv2 ^
  --exclude-module tkinter ^
  --noconsole ^
  gui_main.py
echo Done: dist\manila.exe
pause
