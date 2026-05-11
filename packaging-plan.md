# ClaudeUsageBar — Windows Packaging Plan

## Context
The app currently requires the user to have Python 3.11+ and run `pip install -r requirements.txt` before launching. The goal is to produce a distributable Windows installer (.exe) that bundles Python and all dependencies, requires no setup from the end user, and creates a Start Menu entry with an uninstaller.

## Approach: PyInstaller (onedir) + Inno Setup 6

Two new files at the project root. No changes to existing source code.

**Why onedir, not onefile?** Onefile extracts to `%TEMP%` on every launch — slow startup and often blocked by corporate AV. Onedir installs to `Program Files` once and launches instantly.

---

## New Files

### `ClaudeUsageBar.spec` (PyInstaller spec)

```python
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
        'requests.packages.urllib3',
        'requests.packages.urllib3.util.retry',
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
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name='ClaudeUsageBar',  # → dist\ClaudeUsageBar\
)
```

### `ClaudeUsageBar.iss` (Inno Setup 6 script)

```iss
#define AppName     "ClaudeUsageBar"
#define AppVersion  "1.0.0"
#define AppExeName  "ClaudeUsageBar.exe"

[Setup]
AppId={{REPLACE-WITH-NEW-GUID}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=ClaudeUsageBar_Setup
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startupentry"; Description: "Start {#AppName} with Windows"; Flags: unchecked

[Files]
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#AppName}"; \
  ValueData: """{app}\{#AppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startupentry

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; \
  Flags: nowait postinstall skipifsilent
```

---

## Build Steps

**Prerequisites (one-time):**
```powershell
py -m pip install pyinstaller
# Also install Inno Setup 6 from https://jrsoftware.org/isinfo.php
```

**Step 1 — Freeze:**
```powershell
py -m PyInstaller ClaudeUsageBar.spec --clean
```
Output: `dist\ClaudeUsageBar\ClaudeUsageBar.exe` + all DLLs.

**Step 2 — Package installer:**
```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ClaudeUsageBar.iss
```
Output: `installer_output\ClaudeUsageBar_Setup.exe` — the distributable.

**Before Step 2:** Generate a fresh GUID to replace the placeholder in the `.iss` file:
```powershell
[System.Guid]::NewGuid()
```

---

## Known Gotchas

| # | Issue | Fix |
|---|-------|-----|
| 1 | `pystray._win32` silently missing | Already in `hiddenimports` |
| 2 | PyQt6 `qwindows.dll` missing (older PyInstaller) | Check `dist\ClaudeUsageBar\PyQt6\Qt6\plugins\platforms\`; add to `datas` if absent |
| 3 | SSL errors from `requests` / `certifi` | Check `cacert.pem` is in output; add to `datas` if not |
| 4 | No crash traceback in windowed mode | Check `%APPDATA%\ClaudeUsageBar\app.log` for post-startup errors |
| 5 | Wrong Python env | Run `py -m pip list` to confirm PyQt6/pystray are present before building |

---

## Verification

1. Smoke-test the frozen folder directly (before building installer):
   ```powershell
   .\dist\ClaudeUsageBar\ClaudeUsageBar.exe
   ```
   Tray icon should appear; check `%APPDATA%\ClaudeUsageBar\app.log`.

2. Run `installer_output\ClaudeUsageBar_Setup.exe` on a clean machine (or VM with no Python).
   - Start Menu entry exists
   - App launches and tray icon appears
   - Wizard opens on first run
   - Uninstall from Settings > Apps cleans up correctly
   - Task Manager shows `ClaudeUsageBar.exe`, not `python.exe`
