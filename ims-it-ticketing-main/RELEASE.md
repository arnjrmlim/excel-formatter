# Release Guide

This project distributes IMS TinyTask through GitHub Releases. The formatter download button depends on a stable asset filename:

```text
IMS_tinytask.exe
```

Do not include version numbers in the uploaded executable asset name. Put the version in the Git tag and release title instead.

## Build IMS TinyTask

From a clean checkout on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r IMS_tinytaskv4\requirements.txt
Set-Location IMS_tinytaskv4
py -m PyInstaller IMS_tinytask.spec --clean --noconfirm
```

Build IMS TinyTask only from the `IMS_tinytaskv4` directory. That keeps
PyInstaller's `build/`, `dist/`, and generated cache files out of the repository
root. The checked-in `IMS_tinytask.spec` is the canonical spec file and embeds
`icon.ico` in the executable while also bundling it for Tk runtime icon loading.

The direct CLI form also works from `IMS_tinytaskv4` for compatibility checks:

```powershell
py -m PyInstaller --onefile --windowed --icon="icon.ico" IMS_tinytask.py --clean
```

Use the spec command for release builds so the checked-in icon data, version
metadata, and `pynput` collection settings are applied consistently.

The expected executable is:

```text
IMS_tinytaskv4\dist\IMS_tinytask.exe
```

Before uploading, run a quick smoke test:

```powershell
python -m py_compile IMS_tinytask.py
```

Then open `dist\IMS_tinytask.exe` from inside `IMS_tinytaskv4`, confirm the IMS
TinyTask window starts, and confirm the formatter can connect to
`http://127.0.0.1:8765`.

Icon validation before uploading:

1. Confirm `dist\IMS_tinytask.exe` shows the custom icon in Windows Explorer.
2. Start the EXE and confirm the title bar and taskbar use the same icon.
3. Open Settings and confirm the child Tk window uses the same icon.
4. Test on a clean Windows machine or VM before publishing a GitHub Release.

## Create a GitHub Release

1. Go to `https://github.com/arnjrmlim/ims-format/releases/new`.
2. Create a new tag such as `v1.0.0`.
3. Use a release title such as `IMS Format v1.0.0`.
4. Upload `IMS_tinytaskv4\dist\IMS_tinytask.exe` as a release asset.
5. Confirm the uploaded asset is named exactly `IMS_tinytask.exe`.
6. Publish the release.

The formatter uses this direct download URL:

```text
https://github.com/arnjrmlim/ims-format/releases/latest/download/IMS_tinytask.exe
```

After publishing, test the URL in a fresh browser session. It should download the executable immediately. If it opens a GitHub error page, the latest release is missing the asset or the asset filename does not match.

## Updating IMS TinyTask

For each new version:

1. Build a fresh executable from the release commit.
2. Smoke test the executable locally.
3. Create a new Git tag and GitHub Release.
4. Upload the new executable as `IMS_tinytask.exe`.
5. Publish the release.
6. Verify the latest-release download URL still downloads the new executable.

No formatter code change is required when the asset filename remains `IMS_tinytask.exe`.

## Troubleshooting

- **Button opens the GitHub release page:** the repository has no published latest release, or the latest release does not have an asset named `IMS_tinytask.exe`.
- **Old executable downloads:** confirm the intended release is the latest non-draft, non-prerelease release.
- **Browser blocks the file:** confirm users trust the release source and consider code signing future Windows builds.
- **Formatter cannot connect after install:** start IMS TinyTask once so it can register the `ims-tinytask` protocol and local bridge.
