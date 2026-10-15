# IMS Format

## Overview

IMS Format is an internal productivity dashboard for office tools. It includes a browser-based Excel formatter, a Windows macro helper named IMS TinyTask, and an IT assistance ticketing module designed for future LAN deployment.

## Features

- Upload `.xlsx` workbooks in the browser.
- Detect supported center and head office worksheet layouts.
- Normalize payor, insured, member, dependent, contact, privilege, sex, civil status, and date fields.
- Split and clean full names, suffixes, compound surnames, and name components.
- Validate name fields for unsupported special characters before export.
- Preview converted rows with pagination.
- Export a workbook with a new `Formatted` worksheet while preserving source sheets.
- Integrate with IMS TinyTask through `ims-tinytask://open` and `http://127.0.0.1:8765`.
- Download the latest IMS TinyTask executable directly from GitHub Releases.
- Record, save, load, and replay Windows input macros with configurable hotkeys.
- Navigate between Excel Formatter, TinyTask, and IT Ticketing System with a responsive sidebar.
- Submit employee IT requests without employee accounts.
- Manage ticket status, assignment, notes, timeline, search, filters, dashboard counters, reports, and CSV/Excel/PDF exports.

## Requirements

- Windows for IMS TinyTask.
- Python 3.11 or newer when running the helper from source.
- A modern browser for `Formatter.html`.
- Internet access when using the CDN-hosted browser libraries in `Formatter.html`.

Python runtime dependency:

```powershell
pip install -r requirements.txt
```

Browser libraries loaded by `Formatter.html`:

- ExcelJS
- FileSaver.js

## Installation

Clone the repository and install Python dependencies:

```powershell
git clone https://github.com/arnjrmlim/ims-format.git
cd ims-format
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

Open `Formatter.html` in a browser. Use the sidebar to switch between Excel Formatter, TinyTask, and IT Ticketing System.

For Excel Formatter, select an `.xlsx` workbook, review the preview and validation messages, then download the converted file.

To install IMS TinyTask, click **Download IMS TinyTask** in the formatter. The button uses GitHub's latest-release asset endpoint:

```text
https://github.com/arnjrmlim/ims-format/releases/latest/download/IMS_tinytask.exe
```

This URL always resolves to the newest release as long as each release uploads the executable asset using the exact filename `IMS_tinytask.exe`.

To run IMS TinyTask from source:

```powershell
python IMS_tinytaskv4\IMS_tinytask.py
```

Executable builds should be created from inside `IMS_tinytaskv4` and published
as GitHub Release assets rather than committed to the repository:

```powershell
cd IMS_tinytaskv4
py -m PyInstaller IMS_tinytask.spec --clean --noconfirm
```

The release asset must be uploaded as `IMS_tinytask.exe`. See
[RELEASE.md](RELEASE.md) for the full validation and upload checklist.

For the IT Ticketing System demo, submit employee tickets from the employee view. The admin view uses local demo credentials and then opens `AdminPortal.html`:

```text
Username: admin
Password: admin123
```

The demo stores tickets in browser `localStorage`. See [docs/it-ticketing-system.md](docs/it-ticketing-system.md) and [database/it-ticketing-schema.sql](database/it-ticketing-schema.sql) for the production LAN backend plan and schema.

## Folder Structure

```text
.
|-- Formatter.html
|-- AdminPortal.html
|-- database/
|   `-- it-ticketing-schema.sql
|-- docs/
|   `-- it-ticketing-system.md
|-- IMS_tinytaskv4/
|   |-- IMS_tinytask.py
|   |-- IMS_tinytask.spec
|   |-- icon.ico
|   |-- final_tiny.rec
|   |-- version_info.txt
|   `-- requirements.txt
|-- AUDIT_REPORT.md
|-- CONTRIBUTING.md
|-- GITHUB_READY.md
|-- RELEASE.md
|-- SECURITY.md
|-- LICENSE
|-- requirements.txt
|-- .env.example
`-- .gitignore
```

## Configuration

No required environment variables are currently used. IMS TinyTask stores user settings in `%APPDATA%\IMS TinyTask\settings.json`. The current ticketing demo stores data in browser `localStorage`; a production deployment should move tickets, admin users, sessions, logs, and uploads to the internal backend and database.

Default local integration values:

- Host: `127.0.0.1`
- Port: `8765`
- Protocol: `ims-tinytask`
- Release asset: `IMS_tinytask.exe`

Future ticketing backend values:

- Internal web host and port.
- Database connection string.
- Session secret.
- Screenshot upload directory.
- Workstation detection adapter mode.

## Security Notes

- Do not commit `.env`, logs, generated outputs, executable builds, temporary files, or local macro recordings.
- Review workbook data before sharing exported files because encoding workbooks may contain personal or company-sensitive information.
- IMS TinyTask is Windows-only and controls mouse/keyboard input, so run it only from trusted source code or trusted release artifacts.
- Keep executable builds in GitHub Releases or another controlled distribution channel.
- Do not use the static ticketing demo as a production authentication boundary. Move admin authentication server-side with secure password hashing and HTTP-only sessions before LAN rollout.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
