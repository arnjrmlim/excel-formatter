# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_all


# Keep this spec inside IMS_tinytaskv4 and build from that directory. SPECPATH
# makes the script, icon, bundled data, and version metadata resolve correctly
# whether PyInstaller is launched by spec file or from a clean checkout.
script_dir = SPECPATH
script_path = os.path.join(script_dir, 'IMS_tinytask.py')
icon_path = os.path.join(script_dir, 'icon.ico')
version_path = os.path.join(script_dir, 'version_info.txt')

# Bundle icon.ico as runtime data for Tk's iconbitmap() while also embedding it
# into the EXE below so Windows Explorer, taskbar, and title bar use one icon.
datas = [(icon_path, '.')]
binaries = []
hiddenimports = []

pynput_datas, pynput_binaries, pynput_hiddenimports = collect_all('pynput')
datas += pynput_datas
binaries += pynput_binaries
hiddenimports += pynput_hiddenimports

a = Analysis(
    [script_path],
    pathex=[script_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='IMS_tinytask',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    version=version_path,
)
