#!/bin/bash
# 构建 Manila Linux 可执行文件
cd "$(dirname "$0")"
pip install pyinstaller pygame -q

mkdir -p bin/linux

pyinstaller --onefile \
  --name manila \
  --add-data "data:data" \
  --hidden-import gui \
  --hidden-import gui.bridge \
  --hidden-import gui.renderer \
  --hidden-import constants \
  --hidden-import player \
  --hidden-import ai \
  --hidden-import game \
  --hidden-import market \
  --hidden-import ship \
  --hidden-import board \
  --hidden-import logger \
  --hidden-import pygame \
  --hidden-import pygame.font \
  --hidden-import pygame.mixer \
  --hidden-import pygame.image \
  --exclude-module matplotlib \
  --exclude-module scipy \
  --exclude-module numpy \
  --exclude-module pandas \
  --exclude-module PIL \
  --exclude-module cv2 \
  --exclude-module tkinter \
  --distpath bin/linux \
  gui_main.py

echo "Done: bin/linux/manila"
