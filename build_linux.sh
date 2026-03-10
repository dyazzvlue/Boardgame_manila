#!/bin/bash
# 构建 Manila Linux 可执行文件
cd "$(dirname "$0")"
pip install pyinstaller pygame -q
pyinstaller --onefile \
  --name manila \
  --add-data "data:data" \
  --exclude-module matplotlib \
  --exclude-module scipy \
  --exclude-module numpy \
  --exclude-module pandas \
  --exclude-module PIL \
  --exclude-module cv2 \
  --exclude-module tkinter \
  gui_main.py
echo "Done: dist/manila"
