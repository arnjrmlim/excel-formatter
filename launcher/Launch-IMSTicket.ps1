#Requires -Version 3.0
<#
.SYNOPSIS
    IMS IT Ticketing System — GPO Launcher Script

.DESCRIPTION
    Retrieves the Windows computer name (and optionally the domain username)
    from the local environment, URL-encodes the values, then opens the IMS
    ticketing system in the user's default browser with the parameters
    appended as query-string arguments.

    The ticket form reads these parameters on load and automatically populates
    the read-only Computer Name field — zero user interaction required.

.NOTES
    Deploy this script to a NETLOGON share or a GPO-accessible file share.
    Run it via the silent VBScript wrapper (Launch-IMSTicket.vbs) so that
    no PowerShell console window is visible to the user.

    To add more parameters in the future (IP, department, asset ID, etc.)
    add a new entry to the $params ordered dictionary below — nothing else
    needs to change.
#>

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
# Change this to your actual IMS portal URL.
# Use the FQDN that resolves inside your LAN, e.g. http://ims-portal.company.local/
$TicketBaseUrl = 'http://ims-portal/Formatter.html#tickets'

# Set to $true to also pass the logged-in Windows username as &user=DOMAIN\jdoe
$IncludeUsername = $true

# Set to $true to pass the client IPv4 address as &ip=192.168.1.50
# Requires .NET; falls back gracefully if detection fails.
$IncludeIpAddress = $false
# ── END CONFIGURATION ─────────────────────────────────────────────────────────


# ── Helper: URL-encode a string (works on PS 3+, no external modules) ─────────
function ConvertTo-UrlEncoded {
    param([string]$Value)
    return [System.Uri]::EscapeDataString($Value)
}


# ── Collect parameters ────────────────────────────────────────────────────────
# Use an ordered dictionary so the query string is always built in a
# predictable order.  Add future parameters here — each key becomes the
# query-param name, each value is what gets encoded and appended.

$params = [ordered]@{}

# --- Priority param: Windows computer name (always included) -----------------
$computerName = $env:COMPUTERNAME
if ([string]::IsNullOrWhiteSpace($computerName)) {
    # Fallback: query WMI (extremely unlikely to be needed, but safe)
    try {
        $computerName = (Get-WmiObject Win32_ComputerSystem).Name
    } catch {
        $computerName = 'UNKNOWN'
    }
}
$params['pc'] = $computerName

# --- Optional: Windows username (DOMAIN\user or just user) -------------------
if ($IncludeUsername) {
    $username = $env:USERNAME
    $domain   = $env:USERDOMAIN
    if (-not [string]::IsNullOrWhiteSpace($domain) -and $domain -ne $computerName) {
        $params['user'] = "$domain\$username"
    } else {
        $params['user'] = $username
    }
}

# --- Optional: client IPv4 address -------------------------------------------
if ($IncludeIpAddress) {
    try {
        $ip = (
            [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
            Where-Object { $_.AddressFamily -eq 'InterNetwork' } |
            Select-Object -First 1
        ).IPAddressToString
        if (-not [string]::IsNullOrWhiteSpace($ip)) {
            $params['ip'] = $ip
        }
    } catch {
        # Silent — IP is optional; do not block ticket submission
    }
}

# ── Future parameters (examples — uncomment and populate as needed) ───────────
# $params['dept']    = $env:DEPARTMENT          # set via logon script or AD attribute
# $params['asset']   = Get-AssetTag             # custom function from your CMDB
# $params['floor']   = '3'                      # hard-coded per OU / site GPO
# $params['mac']     = Get-MacAddress           # custom function


# ── Build the final URL ───────────────────────────────────────────────────────
$queryParts = @()
foreach ($key in $params.Keys) {
    $encodedKey   = ConvertTo-UrlEncoded $key
    $encodedValue = ConvertTo-UrlEncoded $params[$key]
    $queryParts  += "$encodedKey=$encodedValue"
}

# If the base URL already contains a fragment (#tickets) we insert the query
# string before the fragment so browsers handle it correctly.
if ($TicketBaseUrl -match '^([^#]*)(#.*)$') {
    $finalUrl = $Matches[1] + '?' + ($queryParts -join '&') + $Matches[2]
} else {
    $finalUrl = $TicketBaseUrl + '?' + ($queryParts -join '&')
}


# ── Open the URL in the default browser ──────────────────────────────────────
# Start-Process with a URL invokes the Windows shell association for http/https,
# which opens the user's chosen default browser automatically (Chrome, Edge,
# Firefox — whatever is registered).
try {
    Start-Process $finalUrl
} catch {
    # Last-resort fallback: use the shell COM object
    $shell = New-Object -ComObject WScript.Shell
    $shell.Run($finalUrl, 1, $false)
}
