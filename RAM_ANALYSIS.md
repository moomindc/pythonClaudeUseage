# ClaudeUsageBar — RAM & Packaged Footprint Analysis

*Date: 2026-05-21 · Build: PyInstaller one-folder + Inno Setup installer · Observed runtime RAM: ~45 MB*

---

## 1. Background

ClaudeUsageBar was just packaged into a Windows executable (PyInstaller "one-folder" build under `dist\ClaudeUsageBar\`) and an Inno Setup installer. After install, the running process consumes **~45 MB of RAM**.

This report answers three questions:

1. Is ~45 MB normal and expected for this kind of app?
2. Are we importing/bundling more Python packages than necessary?
3. Can the Python runtime be slimmed to reduce memory use?

**Short answer:** 45 MB is normal and actually on the *low* side for a frozen PyQt6 GUI app. We are bundling several packages we never import (notably **numpy**, ~27 MB), but these inflate the **on-disk install size**, not the runtime RAM. Genuine RAM reduction is not realistically available without abandoning Qt, which is not worth it for this app.

---

## 2. Areas of Investigation

| Area | Method |
|------|--------|
| What the app actually imports | `grep` of every `*.py` in `ClaudeUsageBar/` |
| What PyInstaller was told to do | Read `ClaudeUsageBar.spec` (hiddenimports / excludes) |
| What actually got bundled | `ls` + `du` of `dist\ClaudeUsageBar\_internal\` |
| Where the bytes go | Per-package and per-DLL size measurement |
| RAM vs. disk | Reasoning about which bundled bytes are *loaded* at runtime vs. merely *present* on disk |

---

## 3. Findings

### 3.1 What the application actually imports

A grep of all source files shows the real dependency surface is small:

- **PyQt6** — `QtCore`, `QtGui`, `QtWidgets` (the GUI framework; the whole app renders through it)
- **requests** — HTTP calls to the `claude.ai` internal API
- **pystray** — system-tray icon
- **PIL (Pillow)** — `Image`, `ImageDraw` for tray-icon generation
- **stdlib only:** `ctypes`, `logging`, `sys`, `threading`, `datetime`, `json`, `os`, `pathlib`, `io`, `uuid`, `typing`

There is **no** `import numpy`, **no** `import yaml`, and **no** `import setuptools` anywhere in the source.

### 3.2 What actually got bundled (`dist\ClaudeUsageBar\_internal`)

| Component | On-disk size | Used by app? |
|-----------|--------------|--------------|
| **PyQt6** (Qt6 DLLs + bindings) | **73 MB** | ✅ Yes — core framework |
| ↳ `opengl32sw.dll` (software OpenGL fallback) | 20 MB | ⚠️ Probably not |
| ↳ `Qt6Core.dll` | 11 MB | ✅ |
| ↳ `Qt6Gui.dll` | 9.2 MB | ✅ |
| ↳ `Qt6Widgets.dll` | 6.3 MB | ✅ |
| ↳ `Qt6Pdf.dll` | 4.4 MB | ❌ No |
| ↳ `Qt6Network.dll` | 1.7 MB | ❌ (we use `requests`, not QtNetwork) |
| ↳ Qt translations | 6.6 MB | ❌ (English-only app) |
| ↳ Qt plugins | 3.4 MB | partial |
| **numpy** + **numpy.libs** | **~27 MB** | ❌ **Never imported** |
| **PIL (Pillow)** | 13 MB | ✅ Yes (tray icon) |
| **yaml** | 256 KB | ❌ Never imported |
| **setuptools** | 39 KB | ❌ Never imported |
| `ClaudeUsageBar.exe` (bootstrap) | 7.6 MB | ✅ |

The executable bootstrap is ~7.6 MB; the bulk of the footprint lives in `_internal\`.

### 3.3 Is 45 MB of RAM normal? — Yes.

The runtime working set is dominated by two unavoidable costs:

- **Python interpreter base** (`python314.dll` + core modules): ~10–15 MB resident.
- **Qt shared libraries mapped into the process** (`Qt6Core` + `Qt6Gui` + `Qt6Widgets`) plus the PyQt6 binding `.pyd` files: ~25–35 MB resident.

Add `requests`/`urllib3`/`ssl`/`certifi` and the loaded portion of PIL, and ~45 MB is exactly where a healthy frozen PyQt6 app lands. A bare-bones PyQt6 "hello world" frozen with PyInstaller commonly reports **40–80 MB RSS**. At 45 MB this app sits at the **low end** of normal — there is no leak or bloat in the runtime memory itself.

### 3.4 The crux: RAM is *not* the same as disk footprint

This is the most important finding. The unused packages (**numpy ~27 MB, yaml, setuptools, Qt6Pdf, Qt translations, opengl32sw.dll**) are present **on disk** but cost **≈0 RAM**, because Windows only pages a DLL/module into memory when it is actually loaded — and nothing in the app ever imports them.

- numpy is pulled in by PyInstaller's PIL hook *as a precaution* (Pillow can convert to/from numpy arrays via `Image.fromarray`/`__array__`). This app never calls those paths, so numpy is never imported and never enters RAM.
- Removing these packages therefore **shrinks the installer and on-disk size (~50 MB+)** but will **not** move the 45 MB runtime number.

### 3.5 Can RAM be meaningfully reduced?

Not really — and that's fine. The RAM floor is set by Qt. The only ways to go meaningfully below ~40 MB would be to:

- **Drop Qt entirely** and rewrite the bar in a lighter native toolkit (raw Win32 / a tiny C helper). This is a full rewrite for a ~10–20 MB saving — **not worth it** for a one-line floating bar.
- Micro-optimisations (e.g. deferring the `requests` import until the first poll) save only a couple of MB and only until the first network call, after which the module loads anyway.

**Verdict:** 45 MB is healthy. There is no realistic, worthwhile RAM reduction. The legitimate, easy wins are all on **disk/install size**.

---

## 4. Sources of Information

All findings are grounded in direct inspection of this repository:

- `ClaudeUsageBar.spec` — current `hiddenimports` and `excludes`.
- `grep` of `ClaudeUsageBar\*.py` — the complete set of real imports.
- `du -sh` / `ls` of `dist\ClaudeUsageBar\_internal\` — actual bundled sizes (PyQt6 73 MB, numpy+libs ~27 MB, PIL 13 MB, etc.) and the largest Qt DLLs.
- General context (well-established norms): PyInstaller-frozen PyQt6 apps typically use 40–80 MB RSS; Qt's shared libraries impose an inherent memory floor; PyInstaller's PIL hook conditionally bundles numpy when it is present in the build environment.

---

## 5. Recommendations

### 5.1 RAM — no action needed
45 MB is normal and good. Do not invest effort chasing it. If you ever wanted a token saving, lazy-import `requests` inside the fetch function rather than at module top — but the benefit is negligible.

### 5.2 Disk / install size — easy, safe wins (~50 MB+)
These reduce the installer and on-disk footprint without affecting behaviour:

1. **Exclude unused packages** — `numpy` (~27 MB), `yaml`, `setuptools`. Highest-value, zero-risk: nothing imports them.
2. **Exclude `Qt6Pdf`** (~4.4 MB) — unused.
3. **Drop Qt translations** (~6.6 MB) — the app is English-only.
4. **Drop `opengl32sw.dll`** (~20 MB) — software OpenGL fallback. *Test first:* on the rare machine with no usable GPU GL driver, Qt may fall back to it; verify the bar still renders on a clean target before shipping without it.

### 5.3 Why the leakage happened
PyInstaller statically scans the **build environment**, not just the imports. Because numpy/yaml/setuptools are installed in the Python env used to build, its hooks bundle them defensively. Building from a clean, minimal virtual environment containing only `PyQt6`, `requests`, `pystray`, `Pillow` would prevent most of this automatically.

---

## 6. Remediation Plan (disk size — apply when ready)

> **Note:** Per the agreed scope, this report does **not** modify the build. The steps below are the recommended changes for a future pass.

### Step 1 — Edit `ClaudeUsageBar.spec`
Extend the `excludes` list in the `Analysis(...)` block:

```python
excludes=[
    'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore',
    'PyQt6.QtMultimedia', 'PyQt6.QtSql', 'PyQt6.QtBluetooth', 'tkinter',
    # --- added: unused leakage ---
    'numpy', 'yaml', 'setuptools',
    'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets',
],
```

For `opengl32sw.dll` and the `translations` folder, either delete them from `dist\ClaudeUsageBar\_internal\PyQt6\Qt6\bin` / `...\Qt6\translations` as a post-build step, or filter them out of `a.binaries`/`a.datas` in the spec.

### Step 2 — Build from a clean venv (preferred)
```powershell
py -m venv build-venv
build-venv\Scripts\activate
pip install pyinstaller PyQt6 requests pystray Pillow
pyinstaller ClaudeUsageBar.spec
```
A minimal env stops numpy/yaml/setuptools from ever being scanned in.

### Step 3 — Rebuild installer & verify
1. `pyinstaller ClaudeUsageBar.spec`, then recompile `ClaudeUsageBar.iss`.
2. Run `dist\ClaudeUsageBar\ClaudeUsageBar.exe` and confirm: the bar renders, the tray icon appears, a usage poll succeeds, the wizard/settings open, and notifications fire.
3. Re-measure:
   - **RAM:** expected ~unchanged (≈45 MB) — confirms the runtime was never the problem.
   - **Disk:** expected ~50 MB+ smaller (`_internal\` shrinks substantially).

### Expected outcome
| Metric | Before | After |
|--------|--------|-------|
| Runtime RAM | ~45 MB | ~45 MB (unchanged — and that's correct) |
| On-disk `_internal\` | bloated by ~50 MB+ of unused libs | trimmed |
| Installer size | larger | smaller (also benefits from `lzma2/ultra` compression already configured) |

---

## 7. Conclusion

The ~45 MB RAM figure is **normal, expected, and healthy** for a frozen PyQt6 application — Qt sets that floor and there is no leak. We *are* bundling packages we never use (numpy, yaml, setuptools, Qt6Pdf, translations, software-GL), but those cost disk space, not memory. There is no worthwhile RAM optimisation; the actionable improvement is a leaner **install footprint**, achieved by adding excludes to the spec and/or building from a clean virtual environment.
