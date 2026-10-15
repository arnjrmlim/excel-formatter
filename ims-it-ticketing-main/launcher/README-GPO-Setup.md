# IMS IT Ticketing System — GPO Launcher Deployment Guide

Automatic Windows computer name detection for the IMS IT Support ticketing
system using a PowerShell launcher deployed through Group Policy.

---

## Table of Contents

1. [How It Works](#1-how-it-works)
2. [File Overview](#2-file-overview)
3. [Step 1 — Copy Files to the NETLOGON Share](#3-step-1--copy-files-to-the-netlogon-share)
4. [Step 2 — Configure the Launcher URL](#4-step-2--configure-the-launcher-url)
5. [Step 3 — Deploy the Desktop Shortcut via GPO](#5-step-3--deploy-the-desktop-shortcut-via-gpo)
6. [Step 4 — (Alternative) Deploy via GPO File Preferences](#6-step-4--alternative-deploy-via-gpo-file-preferences)
7. [Step 5 — Allow PowerShell Execution via GPO](#7-step-5--allow-powershell-execution-via-gpo)
8. [Testing](#8-testing)
9. [Security Considerations](#9-security-considerations)
10. [Troubleshooting](#10-troubleshooting)
11. [Adding Future Parameters](#11-adding-future-parameters)

---

## 1. How It Works

```
User double-clicks shortcut
        │
        ▼
wscript.exe runs Launch-IMSTicket.vbs  (no window shown)
        │
        ▼
VBScript calls PowerShell silently
        │
        ▼
Launch-IMSTicket.ps1 reads $env:COMPUTERNAME
        │  encodes it → IMS-PC-024
        ▼
Default browser opens:
  http://ims-portal/Formatter.html?pc=IMS-PC-024#tickets
        │
        ▼
Formatter.html reads ?pc= from the URL
        │  validates: letters, digits, hyphens only, max 253 chars
        │  caches to localStorage for page reloads
        ▼
"Windows Device Name" field auto-filled: IMS-PC-024  (read-only)
        │
        ▼
User fills in the rest of the form and submits
        │  computer name re-validated at submit time
        ▼
Ticket stored with validated computerName + full launchParams object
```

Zero user interaction required. The computer name is sourced entirely
from the Windows environment — not from user input.

---

## 2. File Overview

| File | Purpose |
|------|---------|
| `Launch-IMSTicket.ps1` | Core launcher — reads `$env:COMPUTERNAME`, builds URL, opens browser |
| `Launch-IMSTicket.vbs` | Silent wrapper — runs the PS1 with no console window via `WScript.Shell.Run` |
| `Create-IMSShortcut.ps1` | Helper — creates the desktop `.lnk` shortcut on each workstation |
| `README-GPO-Setup.md` | This file |

---

## 3. Step 1 — Copy Files to the NETLOGON Share

Copy the three script files to a read-only network share accessible by all
domain computers. The NETLOGON share is ideal because it is already replicated
to every domain controller by default.

```
\\your-domain.local\NETLOGON\IMSLauncher\
    Launch-IMSTicket.ps1
    Launch-IMSTicket.vbs
    Create-IMSShortcut.ps1
    ims-icon.ico            ← optional: custom icon for the desktop shortcut
```

### Share permissions

| Principal | Permission |
|-----------|-----------|
| Domain Computers | Read |
| Domain Users | Read |
| Domain Admins | Full Control |

> **Do not grant Write to Domain Users or Domain Computers.**
> The share is read-only for clients — scripts run from here, not copied locally.

---

## 4. Step 2 — Configure the Launcher URL

Open `Launch-IMSTicket.ps1` and update the configuration block at the top:

```powershell
# ── CONFIGURATION ─────────────────────────────────────────────
$TicketBaseUrl   = 'http://ims-portal/Formatter.html#tickets'
$IncludeUsername = $true    # also pass &user=DOMAIN\jdoe
$IncludeIpAddress = $false  # pass &ip=192.168.x.x (optional)
# ──────────────────────────────────────────────────────────────
```

Replace `http://ims-portal/Formatter.html` with the actual FQDN or IP address
of your IIS server, e.g.:

```powershell
$TicketBaseUrl = 'http://ims-portal.your-domain.local/Formatter.html#tickets'
```

---

## 5. Step 3 — Deploy the Desktop Shortcut via GPO (Logon Script Method)

This is the recommended method. The shortcut is created on first logon and
is refreshed on every subsequent logon (idempotent).

### 5a. Open Group Policy Management

```
Server Manager → Tools → Group Policy Management
```

### 5b. Create or edit a GPO

Right-click the target OU (e.g. `IMS Staff Computers`) → **Create a GPO in
this domain, and Link it here…** → name it `IMS Ticketing Launcher`.

### 5c. Add a User Logon Script

```
GPO → Right-click → Edit
  User Configuration
    └─ Policies
         └─ Windows Settings
              └─ Scripts (Logon / Logoff)
                   └─ Logon → Add
```

**Script Name:** `wscript.exe`

**Script Parameters:**
```
"\\your-domain.local\NETLOGON\IMSLauncher\Launch-IMSTicket.vbs"
```

> We call `wscript.exe` with the VBS path as the argument — this is the
> standard way to run a VBScript from a GPO logon script without a window.

### 5d. Force a GPO update (for testing)

```powershell
# On the client workstation (run as the domain user):
gpupdate /force
```

Log off and log back on — the shortcut will appear on the desktop.

---

## 6. Step 4 — (Alternative) Deploy via GPO File Preferences

If you prefer to push the shortcut file directly rather than via a logon
script, use GPO Preferences:

```
GPO → Edit
  User Configuration
    └─ Preferences
         └─ Windows Settings
              └─ Shortcuts → New → Shortcut
```

| Setting | Value |
|---------|-------|
| Action | Replace |
| Name | IMS IT Support |
| Target type | File System Object |
| Location | Desktop |
| Target path | `\\your-domain.local\NETLOGON\IMSLauncher\Launch-IMSTicket.vbs` |
| Start in | `\\your-domain.local\NETLOGON\IMSLauncher` |
| Run | Minimized |
| Icon file path | `\\your-domain.local\NETLOGON\IMSLauncher\ims-icon.ico` |

> **Note:** This method deploys a shortcut that runs the VBScript directly
> from the share. The logon-script method (Step 3) is preferred because it
> uses `Create-IMSShortcut.ps1` which places a local copy of the `.lnk`
> on the desktop, avoiding a dependency on the share being available when
> the user double-clicks.

---

## 7. Step 5 — Allow PowerShell Execution via GPO

The VBScript wrapper calls PowerShell with `-ExecutionPolicy Bypass`, which
overrides the execution policy for that single invocation without permanently
changing the machine policy. No additional configuration is required for the
script to run.

However, if your organisation has a **Software Restriction Policy** or
**AppLocker** that blocks PowerShell scripts, add an exception:

### AppLocker exception (if applicable)

```
GPO → Edit
  Computer Configuration
    └─ Policies
         └─ Windows Settings
              └─ Security Settings
                   └─ Application Control Policies
                        └─ AppLocker
                             └─ Script Rules → New Rule
```

| Setting | Value |
|---------|-------|
| Action | Allow |
| User or Group | Domain Users |
| Condition | Path |
| Path | `\\your-domain.local\NETLOGON\IMSLauncher\*` |

---

## 8. Testing

### 8a. Manual test — run the launcher directly

On a domain-joined workstation, open **Run** (Win+R) or a command prompt:

```cmd
wscript.exe "\\your-domain.local\NETLOGON\IMSLauncher\Launch-IMSTicket.vbs"
```

Expected result:
- No console window appears
- Default browser opens to:
  `http://ims-portal/Formatter.html?pc=IMS-PC-024&user=DOMAIN%5Cjdoe#tickets`
- The **Windows Device Name** field on the ticket form shows `IMS-PC-024`
- The field is read-only (grey background)
- A green badge reads: `✓ Auto-detected from your Windows device`

### 8b. Test URL parsing directly in the browser

Open this URL manually (replace `IMS-PC-024` with your test value):

```
http://ims-portal/Formatter.html?pc=IMS-PC-024#tickets
```

Navigate to **IT Ticketing System → Employee** — the Computer Name field
should show `IMS-PC-024`.

### 8c. Test validation

Try a URL with an invalid value to confirm it is rejected:

```
http://ims-portal/Formatter.html?pc=IMS PC 024#tickets   ← space → rejected
http://ims-portal/Formatter.html?pc=<script>alert(1)</script>#tickets  ← rejected
http://ims-portal/Formatter.html?pc=#tickets   ← empty → field blank, warning shown
```

For rejected/empty values the field stays blank and a warning badge reads:
`⚠ Not detected – open via the IMS desktop shortcut`

### 8d. Test GPO delivery

```powershell
# Check applied GPOs on a client
gpresult /r

# Force GPO refresh and verify logon script runs
gpupdate /force /logoff
```

---

## 9. Security Considerations

### The `?pc=` parameter is client-supplied — treat it as untrusted

The query parameter originates from the Windows environment variable on the
client machine. It is not signed or cryptographically verified. A technically
capable user could manually craft a URL with a different value.

**Mitigations already in place:**

| Control | Where |
|---------|-------|
| Strict regex validation (`^[A-Za-z0-9\-]{1,253}$`) | `computerDetectionService._sanitize()` in Formatter.html |
| Re-validation at ticket submit time | `submitTicket()` in Formatter.html |
| Field is read-only — cannot be typed into | HTML `readonly` attribute |
| Value forced to uppercase | `_sanitize()` returns `.toUpperCase()` |
| Value length capped at 253 characters | `_MAX_LEN` constant |
| Invalid characters silently rejected → `Unknown Device` | `_sanitize()` returns `''` on failure |

### What this solution does NOT do

- It does **not** cryptographically prove the computer name is genuine.
  A user who manually constructs the URL can pass any valid-looking hostname.
- It does **not** require authentication on the employee-facing page (by design —
  employees should be able to submit without logging in).

### Recommendations for high-trust environments

If spoofing the computer name is a concern:

1. **Cross-reference with Active Directory** on the server side — when a ticket
   arrives, look up the computer name in AD to confirm it exists.
2. **Require Windows Authentication on the API endpoint** — see the separate
   IIS Windows Auth guide.
3. **Log the client IP** — the `?ip=` parameter from the launcher provides
   the client's IP at launch time, which can be compared to IIS access logs.

### Share permissions — principle of least privilege

- Domain Users/Computers: **Read only**
- Never grant Modify or Write to end users on the NETLOGON share
- The scripts should be reviewed and signed off by IT before deployment

### Script signing (optional but recommended)

Sign the PS1 with a code-signing certificate trusted by your domain:

```powershell
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert
Set-AuthenticodeSignature -FilePath ".\Launch-IMSTicket.ps1" -Certificate $cert
```

Then set the GPO execution policy to `AllSigned` and remove `-ExecutionPolicy
Bypass` from the VBScript wrapper.

---

## 10. Troubleshooting

### Shortcut does nothing / browser does not open

1. Confirm the share path in `Launch-IMSTicket.vbs` is correct:
   ```
   strScriptDir = Left(WScript.ScriptFullName, InStrRev(...))
   ```
   Both files must be in the **same folder**.

2. Test the VBScript directly from Run:
   ```
   wscript.exe "\\server\NETLOGON\IMSLauncher\Launch-IMSTicket.vbs"
   ```

3. Check for errors in the PowerShell script:
   ```powershell
   & "\\server\NETLOGON\IMSLauncher\Launch-IMSTicket.ps1"
   ```
   Run this in a normal PowerShell window to see any error output.

### Computer name field shows blank / warning badge

The URL did not contain a valid `?pc=` parameter and no cached value exists.

- Confirm the shortcut was opened via the launcher (not a bookmark).
- Open the browser developer tools → Console and look for any JS errors.
- Paste `location.search` in the console — it should contain `?pc=...`.

### GPO logon script does not run

```powershell
# Check which GPOs are applied
gpresult /h c:\gpresult.html
Start-Process c:\gpresult.html

# Check logon script configuration
Get-GPO -Name "IMS Ticketing Launcher" | Get-GPOReport -ReportType HTML |
    Out-File c:\gpo-report.html
```

Common causes:
- GPO linked to wrong OU
- GPO not applied to the user account (check Security Filtering)
- PowerShell execution blocked by AppLocker (see §7)

### `Create-IMSShortcut.ps1` throws an error on logon

Check the Windows Application event log on the affected workstation:

```powershell
Get-EventLog -LogName Application -Source IMS-Launcher -Newest 10
```

---

## 11. Adding Future Parameters

The solution is designed for easy extension. To add a new parameter:

### Step 1 — Add it to the PowerShell launcher

Open `Launch-IMSTicket.ps1` and add an entry to the `$params` dictionary:

```powershell
# Example: pass the user's department from an AD attribute
$params['dept'] = (Get-ADUser $env:USERNAME -Properties Department).Department

# Example: pass a hard-coded floor number (set per OU via different GPO)
$params['floor'] = '3'

# Example: pass the primary MAC address
$params['mac'] = (Get-NetAdapter | Where-Object Status -eq 'Up' |
                  Select-Object -First 1).MacAddress
```

The URL will automatically include the new parameter:
```
http://ims-portal/Formatter.html?pc=IMS-PC-024&user=IMS%5Cjdoe&dept=Accounting&floor=3
```

### Step 2 — Register the key in the frontend parser

Open `Formatter.html` and add the new key to the `supported` array inside
`computerDetectionService.getParams()`:

```javascript
const supported = ['pc', 'user', 'dept', 'ip', 'asset', 'floor', 'mac'];
//                                  ^^^^^ already there — add new keys here
```

The value is now available anywhere via:
```javascript
const params = computerDetectionService.getParams();
console.log(params.dept);   // "Accounting"
```

### Step 3 — Use the value in the form or ticket record

The full set of launch params is already stored on every ticket:

```json
{
  "computerName": "IMS-PC-024",
  "launchParams": {
    "pc":   "IMS-PC-024",
    "user": "IMS\\jdoe",
    "dept": "Accounting",
    "floor": "3"
  }
}
```

To pre-fill an additional form field, follow the same pattern used for
`computerName` in `initializeTicketing()`:

```javascript
computerDetectionService.getParams().then
// or synchronously since getParams() is synchronous:
const params = computerDetectionService.getParams();
if (params.dept) {
    document.getElementById('department').value = params.dept;
}
```

### Supported parameters reference

| Key | Source | Example value | Notes |
|-----|--------|---------------|-------|
| `pc` | `$env:COMPUTERNAME` | `IMS-PC-024` | Always included; strict hostname validation |
| `user` | `$env:USERNAME` + `$env:USERDOMAIN` | `IMS\jdoe` | Optional; enable in PS1 config |
| `ip` | `[System.Net.Dns]` | `192.168.1.50` | Optional; enable in PS1 config |
| `dept` | AD attribute / GPO variable | `Accounting` | Add manually to PS1 `$params` |
| `asset` | CMDB / registry | `AST-00142` | Add manually to PS1 `$params` |
| `floor` | Hard-coded per OU GPO | `3` | Add manually to PS1 `$params` |
| `mac` | `Get-NetAdapter` | `00-1A-2B-3C-4D-5E` | Add manually to PS1 `$params` |

---

*IMS IT Support Portal — internal LAN deployment guide.*
*No internet access, no cloud services, no software installation on client PCs required.*
