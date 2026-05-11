# -*- mode: python ; coding: utf-8 -*-
import os

binaries_list = []
datas_list = []

if os.path.exists('platform-tools'):
    datas_list.append(('platform-tools', 'platform-tools'))

if os.path.exists('ffmpeg'):
    datas_list.append(('ffmpeg', 'ffmpeg'))

if os.path.exists('scrcpy-server-v3.3.4'):
    datas_list.append(('scrcpy-server-v3.3.4', '.'))

if os.path.exists('version.json'):
    datas_list.append(('version.json', '.'))

if os.path.exists('.install_marker'):
    datas_list.append(('.install_marker', '.'))

if os.path.exists('platforms.json'):
    datas_list.append(('platforms.json', '.'))

if os.path.exists('release_notes.txt'):
    datas_list.append(('release_notes.txt', '.'))

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
    icon='ADB-Media-Manager.ico',
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