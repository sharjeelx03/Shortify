# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
project = Path.cwd()

datas = []
if (project / 'assets').exists():
    datas.append(('assets', 'assets'))

# CustomTkinter needs its internal theme/assets files inside the packaged app.
datas += collect_data_files('customtkinter')

binaries = []
for name in ['ffmpeg.exe', 'ffprobe.exe']:
    p = project / 'bin' / name
    if p.exists():
        binaries.append((str(p), 'bin'))

hiddenimports = [
    'app',
    'app.core',
    'app.core.settings',
    'app.core.providers',
    'app.core.pipeline',
    'app.ui',
    'app.ui.shell',
    'app.ui.components',
    'app.ui.pages',
    'app.ui.pages.generate',
    'app.ui.pages.library',
    'app.ui.pages.settings_page',
    'app.ui.pages.updates',
    'customtkinter',
    'yt_dlp',
    'youtube_transcript_api',
    'requests',
    'anthropic',
    'openai',
    'google.generativeai',
]


a = Analysis(
    ['app/main.py'],
    pathex=[str(project), str(project / 'app')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'pygame', 'matplotlib', 'IPython', 'pytest', 'sphinx', 'jedi', 'black'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Shortify',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if Path('assets/icon.ico').exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Shortify',
)
