# IMS IT Ticketing System

## Current Implementation

`Formatter.html` now hosts three dashboard modules:

- Excel Formatter: existing workbook conversion flow, unchanged IDs and conversion logic.
- TinyTask: existing local TinyTask download/connect/play controls, unchanged IDs and API calls.
- IT Ticketing System: employee submission and admin login.

`AdminPortal.html` is the separate administrator portal opened after a successful admin login. It includes the admin dashboard, ticket details, timeline, filters, search, reports, and CSV/Excel/PDF export.

The ticketing module currently runs as an offline-capable browser module using `localStorage`. This keeps the existing static project stable while providing the UI, workflows, and service boundaries needed for a LAN backend.

## Routes And Modules

There is no separate web router yet because the project is a single static HTML file. Sidebar navigation switches these modules in place:

- `excel`
- `tinytask`
- `tickets`

The ticketing module has internal views:

- `employee`: submit IT request.
- `admin`: admin login and portal launch.

The separate `AdminPortal.html` page contains:

- Dashboard counters.
- Search and filters.
- Recent tickets table.
- Ticket details, assignment, notes, status update, screenshot, and timeline.
- Reporting cards and export actions.

## Admin Access

The static demo seeds one local admin user:

- Username: `admin`
- Password: `admin123`

The demo hashes the password with SHA-256 plus a salt through the Web Crypto API. For production, move admin users to the backend `AdminUsers` table and use a server-side password hashing algorithm such as Argon2id, bcrypt, or PBKDF2 with strong per-user salts. Browser-side hashing and `localStorage` sessions are not a production security boundary.

## Workstation Detection

Browsers cannot reliably read the Windows computer name. The UI therefore calls a `computerDetectionService.getComputerName()` adapter that currently returns `Pending backend detection`.

Replace that adapter from the future backend with one of these LAN-safe options:

- Windows Integrated Authentication with server-side identity resolution.
- A lightweight local workstation agent.
- A PowerShell launcher that opens the page with a signed workstation token.
- Active Directory lookup that resolves the current Windows user and registered device.

The stored field remains `ComputerName`, matching the requested `COMPUTERNAME` value such as `IMS-PC-014`.

## Backend API Shape

Recommended future API endpoints:

- `POST /api/tickets`: create employee ticket, no employee account required.
- `GET /api/tickets`: admin-only list with search and filters.
- `GET /api/tickets/:ticketId`: admin-only ticket details and timeline.
- `PATCH /api/tickets/:ticketId`: admin-only status, assignment, and notes update.
- `POST /api/admin/login`: admin authentication and session creation.
- `POST /api/admin/logout`: session removal.
- `GET /api/reports/tickets`: admin-only report aggregates.
- `GET /api/workstation`: resolve workstation name through the chosen adapter.

## Database

See `database/it-ticketing-schema.sql` for the base SQL Server schema. The same table shape maps cleanly to MySQL or MariaDB by replacing `IDENTITY`, `NVARCHAR`, and `DATETIME2` with the target database equivalents.

Tables:

- `Tickets`
- `AdminUsers`
- `TicketLogs`

Search indexes are included for ticket number, employee, computer, department, category, status, and date filtering.

## Deployment Notes

The production system should run only on the office LAN behind IIS, Apache, or Nginx. The static dashboard can be served by the same internal web server as the future API. File uploads should be stored outside the web root with generated filenames, and the database should store only the screenshot path.

No employee login is required. Only IT administrators should receive accounts.
