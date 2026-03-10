# -*- mode: python ; coding: utf-8 -*-
import sys, os
a = Analysis(
    ['gui_main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[('data', 'data')],
    hiddenimports=['pygame', 'pygame.font', 'pygame.mixer', 'pygame.image',
                   'gui', 'gui.bridge', 'gui.renderer',
                   'constants', 'player', 'ai', 'game', 'market',
                   'ship', 'board', 'logger'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='manila',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
