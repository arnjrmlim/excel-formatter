# IMS Format Repository Audit Report

Audit date: 2026-06-23

## Summary

The repository contains a browser-based Excel formatter (`Formatter.html`) and a Windows-only Python macro helper (`IMS_tinytaskv4/IMS_tinytask.py`). Generated PyInstaller build folders, compiled bytecode caches, executable outputs, temporary extraction files, and recorded macro/test artifacts should not be committed to GitHub.

No hardcoded passwords, API keys, tokens, email credentials, database credentials, or cloud secrets were found in source files. The project does intentionally use a local loopback HTTP bridge at `127.0.0.1:8765` and a Windows URL protocol named `ims-tinytask`; these are local integration points, not external secrets.

## File Classification

### Required Source Files

- `Formatter.html` - main browser-based Excel format converter and UI.
- `IMS_tinytaskv4/IMS_tinytask.py` - Windows macro recorder/player helper used by the formatter.

### Required Assets

- `IMS_tinytaskv4/icon.ico` - application icon used by the Python GUI and PyInstaller build.
- `IMS_tinytaskv4/final_tiny.rec` - macro recording asset; keep only if it is required operationally. Otherwise move to `examples/` or exclude from commits.

### Required Configuration Files

- `IMS_tinytaskv4/requirements.txt` - existing dependency list, but it contains `pyautogui`, which is not imported by the current Python source.
- `IMS_tinytaskv4/IMS_tinytask.spec` - reusable PyInstaller configuration with icon and `pynput` collection.

### Documentation

- `README.md` - main project documentation and usage guide.
- `RELEASE.md` - IMS TinyTask build and GitHub Release asset publishing guide.
- `SECURITY.md` - vulnerability reporting and security practices.
- `CONTRIBUTING.md` - contribution and validation guidance.

### Build Artifacts To Keep Out Of Git

- `IMS_tinytaskv4/build/`
- `IMS_tinytaskv4/build_clean/`
- `IMS_tinytaskv4/build_fresh/`
- `IMS_tinytaskv4/build_hotkey_guard/`
- `IMS_tinytaskv4/build_noicon/`
- `IMS_tinytaskv4/build_settings/`
- `IMS_tinytaskv4/dist/`
- `IMS_tinytaskv4/dist_clean/`
- `IMS_tinytaskv4/dist_fresh/`
- `IMS_tinytaskv4/dist_hotkey_guard/`
- `IMS_tinytaskv4/dist_noicon/`
- `IMS_tinytaskv4/dist_settings/`
- `IMS_tinytaskv4/IMS_tinytask_updated.spec` - stale duplicate packaging spec without icon or hidden import handling.

### Temporary Files

- `.tmp_pycache/`
- `IMS_tinytaskv4/dist_fresh/*.tmp`
- `IMS_tinytaskv4/dist_noicon/*.tmp`

### Cache Files

- `IMS_tinytaskv4/__pycache__/`
- `IMS_tinytaskv4/**/*.pyc`
- `.tmp_pycache/**/*.pyc*`

### Generated Outputs

- `IMS_tinytaskv4/*.exe`
- `IMS_tinytaskv4/build*/**/*.toc`
- `IMS_tinytaskv4/build*/**/*.pkg`
- `IMS_tinytaskv4/build*/**/*.pyz`
- `IMS_tinytaskv4/build*/**/*.zip`
- `IMS_tinytaskv4/build*/**/xref-*.html`
- `IMS_tinytaskv4/build*/**/warn-*.txt`
- `IMS_tinytaskv4/test.json` - recorded macro/test output.

### Sensitive Files

No direct credentials were found. Local machine path fragments appear only inside generated cache/build artifact paths and should be removed with those artifacts.

### Unused or Dead Files

- `Formatter Copy.html` - older duplicate of the main formatter; keep only as history outside Git if needed.
- `IMS_tinytaskv4/IMS_tinytask_updated.spec` - stale alternate PyInstaller spec.
- None currently tracked. The superseded `IMS_tinytaskv4/README.txt` has been removed.

## Security Findings

- No hardcoded secrets detected in source files.
- No hardcoded local machine paths detected in tracked source or documentation.
- External CDN dependencies are loaded by `Formatter.html`:
  - `https://cdn.jsdelivr.net/npm/exceljs/dist/exceljs.min.js`
  - `https://cdnjs.cloudflare.com/ajax/libs/FileSaver.js/2.0.5/FileSaver.min.js`
- The formatter talks to the local macro helper through `http://127.0.0.1:8765`.
- The macro helper registers a per-user Windows protocol handler under `HKCU\Software\Classes\ims-tinytask`.

Recommendations:

- Keep `.env` files ignored even though the current project does not require secrets.
- Consider vendoring or pinning browser JavaScript assets if the tool must work offline or under stricter supply-chain controls.
- Review CORS behavior before expanding the local control server beyond loopback.

## Dependency Findings

- Python source imports `pynput` and uses only standard-library modules otherwise.
- `pyautogui` is listed but not imported by the current source.
- `pyinstaller` is needed only for packaging executable builds, not for runtime.

## Code Quality Findings

- `IMS_tinytaskv4/IMS_tinytask.py` contains duplicate definitions for `toggle_recording`, `toggle_playback`, and `stop_playback`; the later definitions override earlier ones.
- `build_legacy_ui` appears unused by the active startup path.
- Several broad `except Exception` blocks suppress errors without logging.
- `Formatter.html` contains duplicate JavaScript function definitions for `isAllowedNameCharacter`.
- `Formatter.html` is large and would be easier to maintain if split into separate CSS and JavaScript files later.

## Cleanup Plan

Safe to delete now:

- Python bytecode and cache folders.
- PyInstaller build/dist outputs.
- Temporary `.tmp` files.
- Stale duplicate `Formatter Copy.html`.
- Recorded test output `IMS_tinytaskv4/test.json`.
- Stale `IMS_tinytaskv4/IMS_tinytask_updated.spec`.
- Superseded `IMS_tinytaskv4/README.txt`.

Conservative keep:

- `Formatter.html`
- `IMS_tinytaskv4/IMS_tinytask.py`
- `IMS_tinytaskv4/icon.ico`
- `IMS_tinytaskv4/IMS_tinytask.spec`
- `IMS_tinytaskv4/final_tiny.rec` until confirmed unused.
