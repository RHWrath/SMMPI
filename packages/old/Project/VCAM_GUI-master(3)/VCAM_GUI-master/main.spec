# -*- mode: python ; coding: utf-8 -*-
import shutil
import sys
import os

# Find ffmpeg and ffprobe binaries
ffmpeg_path = shutil.which('ffmpeg')
ffprobe_path = shutil.which('ffprobe')

binaries_list = []
if ffmpeg_path:
    binaries_list.append((ffmpeg_path, '.'))
if ffprobe_path:
    binaries_list.append((ffprobe_path, '.'))

# Add scrcpy server file
datas_list = []
if os.path.exists('scrcpy-server-v3.3.4'):
    datas_list.append(('scrcpy-server-v3.3.4', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries_list,
    datas=datas_list,
    hiddenimports=[
        'PIL._imagingtk',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageTk',
        'cv2',
        'av',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ADB-Media-Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ADB-Media-Manager',
)
