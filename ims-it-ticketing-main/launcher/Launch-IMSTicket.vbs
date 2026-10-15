' =============================================================================
' IMS IT Ticketing System — Silent Launcher Wrapper
' =============================================================================
' PURPOSE
'   Runs Launch-IMSTicket.ps1 completely silently (no console window, no UAC
'   prompt, no visible PowerShell flash) by calling WScript.Shell.Run with
'   the window-style set to 0 (hidden).
'
' WHY VBSCRIPT?
'   A .lnk shortcut cannot invoke PowerShell silently on its own — it always
'   flashes a console window.  This VBScript wrapper is the standard GPO
'   pattern for hiding that window.  The shortcut deployed by GPO targets
'   THIS file, not the .ps1 directly.
'
' DEPLOYMENT PATH
'   Copy both files to a read-only NETLOGON share or any UNC path accessible
'   to all domain computers, e.g.:
'       \\your-domain.local\NETLOGON\IMSLauncher\
'
' SHORTCUT TARGET (set in GPO or Create-IMSShortcut.ps1)
'   Target : wscript.exe "\\your-domain.local\NETLOGON\IMSLauncher\Launch-IMSTicket.vbs"
'   Run    : Minimized  (window style 0 makes it fully hidden anyway)
' =============================================================================

Option Explicit

' ── CONFIGURATION ─────────────────────────────────────────────────────────────
' Update this path to wherever the .ps1 is stored on the network share.
' Both files should sit in the same folder; the line below makes the path
' relative to the location of this .vbs file so you can move the folder freely.

Dim strScriptDir, strPS1Path, strCommand
strScriptDir = Left(WScript.ScriptFullName, _
                    InStrRev(WScript.ScriptFullName, "\"))
strPS1Path   = strScriptDir & "Launch-IMSTicket.ps1"
' ── END CONFIGURATION ─────────────────────────────────────────────────────────


' ── Build the PowerShell command ──────────────────────────────────────────────
' -NonInteractive : suppresses any Read-Host / pause prompts
' -NoProfile      : skips user profile (faster, avoids profile-script side effects)
' -ExecutionPolicy Bypass : allows the script to run without changing the
'                           machine-wide execution policy permanently.
'                           This flag is user-scoped for this one invocation only.
' -WindowStyle Hidden     : belt-and-suspenders — hides the PS window even if
'                           WScript.Shell.Run style=0 somehow gets overridden.
' -File "<path>"          : runs the .ps1 file directly (safer than -Command for
'                           paths that may contain spaces).
strCommand = "powershell.exe" & _
             " -NonInteractive" & _
             " -NoProfile" & _
             " -ExecutionPolicy Bypass" & _
             " -WindowStyle Hidden" & _
             " -File """ & strPS1Path & """"


' ── Launch silently ───────────────────────────────────────────────────────────
' WScript.Shell.Run arguments:
'   strCommand  — the full command line to execute
'   0           — window style 0 = hidden (no window shown to the user)
'   False       — bWaitOnReturn = false (fire-and-forget; script returns immediately)

Dim objShell
Set objShell = CreateObject("WScript.Shell")
objShell.Run strCommand, 0, False
Set objShell = Nothing
