# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['ClaudeUsageBar/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pystray._win32',   # Windows backend — always missed by static scanner
        'PIL.Image',
        'PIL.ImageDraw',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore',
        'PyQt6.QtMultimedia', 'PyQt6.QtSql', 'PyQt6.QtBluetooth', 'tkinter',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='ClaudeUsageBar',
    debug=False, strip=False, upx=False,
    console=False,   # no console window
    icon='ClaudeUsageBar.ico',
    version='version.txt',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name='ClaudeUsageBar',  # → dist\ClaudeUsageBar\
)
