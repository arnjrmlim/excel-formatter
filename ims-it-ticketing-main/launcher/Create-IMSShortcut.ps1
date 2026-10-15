#Requires -Version 3.0
<#
.SYNOPSIS
    Creates the IMS IT Ticketing System desktop shortcut on the current user's
    desktop (or Public Desktop for all users).

.DESCRIPTION
    This script is designed to run as a GPO User Logon Script or Computer
    Startup Script.  It creates a .lnk shortcut that targets the silent
    VBScript wrapper (Launch-IMSTicket.vbs), which in turn runs the
    PowerShell launcher without any visible console window.

    Idempotent — safe to run on every logon.  It only (re)writes the shortcut
    if it does not already exist or if the existing target differs from the
    configured path (handles share path changes after an update).

.PARAMETER NetworkSharePath
    UNC path to the folder containing Launch-IMSTicket.vbs.
    Override at runtime:
        .\Create-IMSShortcut.ps1 -NetworkSharePath "\\dc01\NETLOGON\IMSLauncher"

.PARAMETER PlaceOnPublicDesktop
    If $true, writes to C:\Users\Public\Desktop (requires local admin / Computer
    Startup Script context).  If $false (default), writes to the current user's
    desktop — ideal for a User Logon Script.

.EXAMPLE
    # Typical GPO User Logon Script invocation (called by a wrapper .vbs):
    powershell.exe -NonInteractive -NoProfile -ExecutionPolicy Bypass `
        -WindowStyle Hidden -File "\\dc01\NETLOGON\IMSLauncher\Create-IMSShortcut.ps1"
#>

param(
    [string] $NetworkSharePath    = '\\your-domain.local\NETLOGON\IMSLauncher',
    [bool]   $PlaceOnPublicDesktop = $false
)


# ── CONFIGURATION ─────────────────────────────────────────────────────────────
$ShortcutName    = 'IMS IT Support.lnk'          # filename shown on desktop
$ShortcutComment = 'Submit an IMS IT support ticket'
$IconSource      = 'shell32.dll,13'               # headset/support icon built into Windows
                                                  # change to a custom .ico path if desired
# ── END CONFIGURATION ─────────────────────────────────────────────────────────


# ── Resolve target paths ──────────────────────────────────────────────────────
$vbsTarget = Join-Path $NetworkSharePath 'Launch-IMSTicket.vbs'
$wscriptExe = Join-Path $env:SystemRoot 'System32\wscript.exe'

# wscript.exe is the shortcut target; the .vbs path is its argument.
# Quoting the argument handles UNC paths with spaces.
$shortcutArgs = """$vbsTarget"""

if ($PlaceOnPublicDesktop) {
    $desktopPath = [System.IO.Path]::Combine(
        $env:SystemDrive, 'Users', 'Public', 'Desktop')
} else {
    $desktopPath = [System.Environment]::GetFolderPath('Desktop')
}

$shortcutPath = Join-Path $desktopPath $ShortcutName


# ── Check if shortcut already exists and is current ──────────────────────────
$needsWrite = $true

if (Test-Path $shortcutPath) {
    try {
        $shell    = New-Object -ComObject WScript.Shell
        $existing = $shell.CreateShortcut($shortcutPath)
        # Re-create only if the target or arguments have changed
        if ($existing.TargetPath -eq $wscriptExe -and
            $existing.Arguments  -eq $shortcutArgs) {
            $needsWrite = $false
        }
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($shell) | Out-Null
    } catch {
        $needsWrite = $true   # if we can't read it, overwrite it
    }
}


# ── Create or update the shortcut ────────────────────────────────────────────
if ($needsWrite) {
    try {
        $shell     = New-Object -ComObject WScript.Shell
        $shortcut  = $shell.CreateShortcut($shortcutPath)

        $shortcut.TargetPath       = $wscriptExe       # always wscript.exe
        $shortcut.Arguments        = $shortcutArgs      # path to the .vbs
        $shortcut.WorkingDirectory = $NetworkSharePath  # ensures relative paths resolve
        $shortcut.Description      = $ShortcutComment
        $shortcut.WindowStyle      = 7                  # 7 = minimized (belt-and-suspenders)

        # Icon: use a custom .ico if one is placed in the share folder,
        # otherwise fall back to the built-in Windows icon.
        $customIcon = Join-Path $NetworkSharePath 'ims-icon.ico'
        if (Test-Path $customIcon) {
            $shortcut.IconLocation = $customIcon
        } else {
            $shortcut.IconLocation = $IconSource
        }

        $shortcut.Save()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($shell) | Out-Null

        Write-Output "IMS shortcut created: $shortcutPath"
    } catch {
        # Log to Windows Application event log so GPO admins can see failures.
        $message = "IMS shortcut creation failed on $env:COMPUTERNAME " +
                   "for user $env:USERNAME : $_"
        try {
            Write-EventLog -LogName Application `
                           -Source 'IMS-Launcher' `
                           -EventId 1001 `
                           -EntryType Warning `
                           -Message $message `
                           -ErrorAction SilentlyContinue
        } catch { }
        # Do not throw — a missing shortcut should not break a logon script.
        Write-Warning $message
    }
} else {
    Write-Output "IMS shortcut already current — no changes made."
}
