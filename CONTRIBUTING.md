# Contributing to IMS Format

## Branch Naming

Use clear, scoped branch names:

- `feature/short-description`
- `fix/short-description`
- `docs/short-description`
- `chore/short-description`

## Commit Messages

Use concise, imperative commit messages:

```text
Add workbook validation summary
Fix macro helper status response
Update repository documentation
```

For larger changes, include a short body explaining why the change was made.

## Pull Request Process

1. Start from the latest `main` branch.
2. Keep changes focused on one purpose.
3. Describe the behavior changed and how it was tested.
4. Include screenshots for visible UI changes.
5. Confirm generated files, logs, caches, and local outputs are not included.

## Coding Standards

- Prefer readable, explicit Python and JavaScript.
- Keep platform-specific behavior documented.
- Avoid committing generated files or machine-specific paths.
- Handle errors clearly instead of silently suppressing them where practical.
- Keep browser formatter changes compatible with local-file usage unless the project moves to a hosted app.

## Testing

Before opening a pull request:

```powershell
python -m py_compile IMS_tinytaskv4\IMS_tinytask.py
```

Also manually test workbook upload, preview, validation, and export in `Formatter.html` when changing formatter logic.

When changing IMS TinyTask distribution behavior, test the formatter's **Download IMS TinyTask** button and confirm it points to:

```text
https://github.com/arnjrmlim/ims-format/releases/latest/download/IMS_tinytask.exe
```

Release assets must keep the filename `IMS_tinytask.exe`; version numbers belong in Git tags and release titles.
Build IMS TinyTask from inside `IMS_tinytaskv4` only:

```powershell
cd IMS_tinytaskv4
py -m PyInstaller IMS_tinytask.spec --clean --noconfirm
```

Do not commit generated `build/`, `dist/`, `.spec`, `.toc`, `.pkg`, `.pyz`, or
executable files.
