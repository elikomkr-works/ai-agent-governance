# Windows evidence collection for the config-audit (windows-dc.md) and
# incident-response (windows.md) skills.
#
# The user runs this on the host in an elevated PowerShell session; agents never run it.
#   powershell -ExecutionPolicy Bypass -File win_collect.ps1 -Out C:\kanit\dc01 `
#       -Start '2026-10-24 02:00' -End '2026-10-25 08:30' -Suspicious C:\Users\Public\x.ps1
# -Start/-End (host local time) enable the event log exports and changed_files.txt.
#
# Why: collecting by hand skips files and filters lists (DC01: an 8-row services.txt
# could not support K2). The script writes every file in both skills' tables,
# MANIFEST.sha256 and TOPLAMA_NOTU.txt in one run.
#
# Read-only on the host; writes only to -Out; no network. Never collects secrets:
# no registry hives, NTDS.dit, LSASS, Winlogon DefaultPassword, LAPS password values,
# raw msDS-KeyCredentialLink, Get-ADUser -Properties *.
# Untested on a real DC: failed commands are listed in TOPLAMA_NOTU.txt, not fatal.

param(
    [Parameter(Mandatory = $true)][string]$Out,
    [string]$Start,
    [string]$End,
    [string[]]$Suspicious = @()
)

$ErrorActionPreference = 'Continue'

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Error 'Hata: yonetici (Run as administrator) olarak calistirin; aksi halde ciktilar eksik kalir.'; exit 2 }
if (Test-Path -LiteralPath $Out) { Write-Error "Hata: $Out zaten var; onceki kanitin uzerine yazilmaz."; exit 2 }

$window = $false
if ($Start -or $End) {
    try { $S = [datetime]$Start; $E = [datetime]$End } catch { Write-Error "Hata: gecersiz zaman: '$Start' / '$End'"; exit 2 }
    if ($E -le $S) { Write-Error 'Hata: bitis baslangictan once.'; exit 2 }
    $window = $true
}

New-Item -ItemType Directory -Path $Out | Out-Null
$Out = (Resolve-Path -LiteralPath $Out).Path
$isDC = (Get-CimInstance Win32_ComputerSystem).DomainRole -ge 4
$status = New-Object System.Collections.Generic.List[string]
$skipped = New-Object System.Collections.Generic.List[string]

function Save([string]$name, [scriptblock]$cmd, [switch]$DC) {
    if ($DC -and -not $isDC) { $skipped.Add("$name (etki alani denetleyicisi degil)"); return }
    $path = Join-Path $Out $name
    try {
        $global:LASTEXITCODE = 0
        & $cmd 2>&1 | Out-String -Width 4096 | Out-File -FilePath $path -Encoding UTF8
        if ($LASTEXITCODE -ne 0) { $status.Add("$name : cikis kodu $LASTEXITCODE") }
    } catch { $status.Add("$name : $($_.Exception.Message)"); "HATA: $($_.Exception.Message)" | Out-File -FilePath $path -Encoding UTF8 }
}

$sel = @{n = 'TimeUtc'; e = { $_.TimeCreated.ToUniversalTime().ToString('o') } }, 'Id', 'MachineName',
       @{n = 'Message'; e = { $_.Message -replace '\r?\n', ' | ' } }

# Keep each Id list short: FilterHashtable is believed to reject more than ~23 IDs.
function SaveEvents([string]$name, [string]$log, [int[][]]$idSets) {
    $path = Join-Path $Out $name
    $first = $true
    foreach ($ids in $idSets) {
        try {
            $ev = Get-WinEvent -FilterHashtable @{LogName = $log; Id = $ids; StartTime = $S; EndTime = $E } -ErrorAction Stop
            $ev | Select-Object $sel | Export-Csv -Path $path -NoTypeInformation -Encoding UTF8 -Append:(-not $first)
            $first = $false
        } catch {
            # "No events were found" is normal for a quiet window.
            $status.Add("$name [$($ids -join ',')] : $($_.Exception.Message)")
        }
    }
    if (-not (Test-Path -LiteralPath $path)) { '"TimeUtc","Id","MachineName","Message"' | Out-File -FilePath $path -Encoding UTF8 }
}

$cv = 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$ts = 'HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server'
if ($isDC) { Import-Module ActiveDirectory -ErrorAction SilentlyContinue; Import-Module GroupPolicy -ErrorAction SilentlyContinue }

# --- host and patches (both skills) ---
Save 'systeminfo.txt' { systeminfo }
Save 'ubr.txt' { reg query $cv /v CurrentBuild; reg query $cv /v UBR }
Save 'hotfix.txt' { Get-HotFix | Sort-Object InstalledOn | Format-List * }
Save 'installed_software.txt' { Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | Format-List DisplayName, DisplayVersion, Publisher, InstallDate, InstallLocation }
Save 'defender.txt' { Get-MpComputerStatus | Format-List AMServiceEnabled, RealTimeProtectionEnabled, AMProductVersion, AMEngineVersion, AntivirusSignatureLastUpdated, AntivirusSignatureAge }

# --- remote access and protocols ---
Save 'rdp.txt' { reg query $ts /v fDenyTSConnections; reg query "$ts\WinStations\RDP-Tcp"; reg query 'HKLM\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' }
Save 'firewall_rdp.txt' { Get-NetFirewallRule -Direction Inbound | Where-Object { ($_ | Get-NetFirewallPortFilter).LocalPort -eq 3389 } | ForEach-Object { $_ | Format-List DisplayName, Enabled, Profile, Action; $_ | Get-NetFirewallAddressFilter | Format-List RemoteAddress } }
Save 'smb.txt' { Get-SmbServerConfiguration | Format-List EnableSMB1Protocol, RequireSecuritySignature, EnableSecuritySignature }
Save 'ldap_netlogon.txt' { reg query HKLM\SYSTEM\CurrentControlSet\Services\NTDS\Parameters; reg query HKLM\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters }
Save 'ssh_keys.txt' { Get-ChildItem -Force 'C:\ProgramData\ssh\administrators_authorized_keys', 'C:\Users\*\.ssh\authorized_keys' -ErrorAction SilentlyContinue | ForEach-Object { "## $($_.FullName)  $($_.LastWriteTimeUtc.ToString('o'))"; Get-Content $_.FullName } }

# --- credential protection (Lsa key is unfiltered; it holds no secrets) ---
Save 'lsa.txt' { reg query HKLM\SYSTEM\CurrentControlSet\Control\Lsa }
Save 'wdigest.txt' { reg query HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest }
Save 'deviceguard.txt' { Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard | Format-List * }

# --- persistence: tasks, WMI, services, autostart (K1-K3, K6) ---
Save 'scheduled_tasks.txt' { Get-ScheduledTask | ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; [pscustomobject]@{Path = $_.TaskPath; Name = $_.TaskName; State = $_.State; Author = $_.Author; Date = $_.Date; RunAs = $_.Principal.UserId; Actions = (($_.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join ' ; '); LastRun = $i.LastRunTime; NextRun = $i.NextRunTime } } | Format-List }
Save 'scheduled_tasks_xml.txt' { Get-ScheduledTask | ForEach-Object { "## $($_.TaskPath)$($_.TaskName)"; Export-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath } }
Save 'wmi_subscriptions.txt' { foreach ($c in '__EventFilter', 'CommandLineEventConsumer', 'ActiveScriptEventConsumer', '__FilterToConsumerBinding') { "## $c"; Get-CimInstance -Namespace root\subscription -ClassName $c | Format-List * } }
Save 'services.txt' { Get-CimInstance Win32_Service | Format-List Name, DisplayName, StartMode, State, PathName, StartName }
Save 'service_dlls.txt' { Get-ChildItem HKLM:\SYSTEM\CurrentControlSet\Services | ForEach-Object { $p = Get-ItemProperty "$($_.PSPath)\Parameters" -Name ServiceDll -ErrorAction SilentlyContinue; if ($p) { "$($_.PSChildName)  $($p.ServiceDll)" } } }
Save 'drivers.txt' { Get-CimInstance Win32_SystemDriver | Format-List Name, State, StartMode, PathName }
Save 'run_keys.txt' {
    foreach ($k in 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run', 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce') { "## $k"; Get-ItemProperty $k -ErrorAction SilentlyContinue }
    Get-ChildItem Registry::HKEY_USERS | ForEach-Object { foreach ($s in 'Run', 'RunOnce') { "## $($_.Name)\...\$s"; Get-ItemProperty "Registry::$($_.Name)\Software\Microsoft\Windows\CurrentVersion\$s" -ErrorAction SilentlyContinue } }
}
Save 'startup_folders.txt' { Get-ChildItem -Force 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp', 'C:\Users\*\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup' -ErrorAction SilentlyContinue | Format-List FullName, Length, CreationTimeUtc, LastWriteTimeUtc }
# Winlogon by named values only: the key can hold DefaultPassword in cleartext.
Save 'autostart_reg.txt' {
    foreach ($v in 'Userinit', 'Shell', 'AppSetup') { reg query "$cv\Winlogon" /v $v }
    reg query "$cv\Winlogon\Notify" /s; reg query "$cv\Image File Execution Options" /s; reg query "$cv\SilentProcessExit" /s
    reg query "$cv\Windows" /v AppInit_DLLs; reg query "$cv\Windows" /v LoadAppInit_DLLs
    reg query 'HKLM\SYSTEM\CurrentControlSet\Control\Session Manager' /v BootExecute
    reg query 'HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\AppCertDlls'
}
Save 'ps_profiles.txt' { Get-ChildItem -Force "$PSHOME\*profile.ps1", 'C:\Users\*\Documents\WindowsPowerShell\*profile.ps1', 'C:\Users\*\Documents\PowerShell\*profile.ps1' -ErrorAction SilentlyContinue | ForEach-Object { "## $($_.FullName)  $($_.LastWriteTimeUtc.ToString('o'))"; Get-Content $_.FullName } }
Save 'accessibility_bins.txt' { Get-ChildItem C:\Windows\System32\sethc.exe, C:\Windows\System32\utilman.exe, C:\Windows\System32\osk.exe, C:\Windows\System32\Magnify.exe, C:\Windows\System32\Narrator.exe, C:\Windows\System32\DisplaySwitch.exe, C:\Windows\System32\AtBroker.exe -ErrorAction SilentlyContinue | ForEach-Object { $h = Get-FileHash -Algorithm SHA256 $_.FullName; '{0}  {1}  {2}  {3}  {4}' -f $h.Hash.ToLower(), $_.Length, $_.LastWriteTimeUtc.ToString('o'), $_.VersionInfo.OriginalFilename, $_.FullName } }

# --- accounts and groups (K5) ---
$groups = 'Domain Admins', 'Enterprise Admins', 'Schema Admins', 'Administrators', 'Account Operators', 'Server Operators', 'Backup Operators', 'Print Operators', 'DnsAdmins', 'Group Policy Creator Owners', 'Remote Desktop Users', 'Protected Users'
Save 'privileged_groups.txt' -DC { foreach ($g in $groups) { "## $g"; Get-ADGroupMember -Identity $g -Recursive | Format-List Name, SamAccountName, objectClass } }
# Union of the attributes both skills need; still no secret attributes.
Save 'ad_users.txt' -DC { Get-ADUser -Filter * -Properties whenCreated, whenChanged, PasswordLastSet, LastLogonDate, PasswordNeverExpires, DoesNotRequirePreAuth, PasswordNotRequired, AllowReversiblePasswordEncryption, AccountNotDelegated, TrustedForDelegation, adminCount, SIDHistory, servicePrincipalName | Format-List SamAccountName, SID, Enabled, whenCreated, whenChanged, PasswordLastSet, LastLogonDate, PasswordNeverExpires, DoesNotRequirePreAuth, PasswordNotRequired, AllowReversiblePasswordEncryption, AccountNotDelegated, TrustedForDelegation, adminCount, @{n = 'SIDHistoryCount'; e = { $_.SIDHistory.Count } }, @{n = 'SPNCount'; e = { $_.servicePrincipalName.Count } } }
Save 'ad_delegation.txt' -DC { Get-ADComputer -Filter 'TrustedForDelegation -eq $true' -Properties PrimaryGroupID | Format-List Name, PrimaryGroupID }
Save 'ad_keycred.txt' -DC { Get-ADObject -LDAPFilter '(msDS-KeyCredentialLink=*)' -Properties msDS-KeyCredentialLink, whenChanged | Format-List Name, ObjectClass, whenChanged, @{n = 'KeyCount'; e = { $_.'msDS-KeyCredentialLink'.Count } } }
Save 'domain_acl.txt' -DC { (Get-Acl "AD:$((Get-ADDomain).DistinguishedName)").Access | Where-Object { $_.ObjectType -in '1131f6aa-9c07-11d1-f79f-00c04fc2dcd2', '1131f6ad-9c07-11d1-f79f-00c04fc2dcd2', '89e95b76-444d-4c62-991a-0facbeda640c' } | Format-List IdentityReference, ActiveDirectoryRights, ObjectType, AccessControlType }
Save 'adminsdholder_acl.txt' -DC { (Get-Acl "AD:CN=AdminSDHolder,CN=System,$((Get-ADDomain).DistinguishedName)").Access | Format-List IdentityReference, ActiveDirectoryRights, AccessControlType, IsInherited }
Save 'password_policy.txt' -DC { Get-ADDefaultDomainPasswordPolicy | Format-List *; Get-ADFineGrainedPasswordPolicy -Filter * | Format-List * }
# LAPS: schema names and expiry only, never the password attributes.
Save 'laps.txt' -DC {
    $names = (Get-ADObject -SearchBase (Get-ADRootDSE).schemaNamingContext -LDAPFilter '(|(name=ms-Mcs-AdmPwd)(name=ms-LAPS-Password)(name=ms-LAPS-PasswordExpirationTime))').Name
    "## schema: $($names -join ', ')"
    if ($names -contains 'ms-LAPS-PasswordExpirationTime') { Get-ADComputer -Filter * -Properties msLAPS-PasswordExpirationTime | Format-List Name, msLAPS-PasswordExpirationTime }
}
Save 'gpo_list.txt' -DC { Get-GPO -All | Format-List DisplayName, Id, CreationTime, ModificationTime }
Save 'sysvol_listing.txt' -DC { Get-ChildItem -Recurse -Force 'C:\Windows\SYSVOL\domain\Policies' -Include *.xml, *.ps1, *.bat, *.cmd, *.vbs, *.js, scripts.ini, psscripts.ini, GptTmpl.inf | Format-List FullName, Length, LastWriteTimeUtc }
if (-not $isDC) { Save 'local_accounts.txt' { Get-LocalUser | Format-List Name, SID, Enabled, PasswordLastSet, LastLogon, Description; Get-LocalGroupMember Administrators | Format-List * } }

# --- audit and logging configuration ---
Save 'auditpol.txt' { auditpol /get /category:* }
Save 'audit_options.txt' { reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Audit }
Save 'eventlog_config.txt' { wevtutil gl Security; wevtutil gl Microsoft-Windows-PowerShell/Operational }
Save 'powershell_config.txt' { Get-ExecutionPolicy -List; reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell /s; if (Get-Command Get-WindowsFeature -ErrorAction SilentlyContinue) { Get-WindowsFeature PowerShell-V2 } }
Save 'gpresult.txt' { gpresult /scope computer /v }

# --- live state (cross-check) ---
Save 'processes.txt' { Get-CimInstance Win32_Process | Format-List ProcessId, ParentProcessId, Name, CreationDate, ExecutablePath, CommandLine }
Save 'netstat.txt' { netstat -ano }
Save 'sessions.txt' { quser }

# --- incident window: event logs and changed files ---
if ($window) {
    SaveEvents 'security.csv' 'Security' @(
        @(1102, 4624, 4625, 4647, 4648, 4672, 4688, 4697, 4698, 4699, 4700, 4702),
        @(4662, 4720, 4722, 4724, 4728, 4732, 4738, 4756, 4768, 4769, 4771, 4781, 5136, 5137))
    SaveEvents 'security_extra.csv' 'Security' @(, @(4657, 4719))
    SaveEvents 'system.csv' 'System' @(, @(104, 7040, 7045))
    SaveEvents 'taskscheduler.csv' 'Microsoft-Windows-TaskScheduler/Operational' @(, @(106, 140, 141, 200, 201))
    SaveEvents 'powershell.csv' 'Microsoft-Windows-PowerShell/Operational' @(, @(4103, 4104))
    SaveEvents 'wmi_activity.csv' 'Microsoft-Windows-WMI-Activity/Operational' @(, @(5857, 5860, 5861))
    SaveEvents 'rdp_sessions.csv' 'Microsoft-Windows-TerminalServices-LocalSessionManager/Operational' @(, @(21, 22, 24, 25))
    $su = $S.ToUniversalTime(); $eu = $E.ToUniversalTime()
    Save 'changed_files.txt' { Get-ChildItem -Recurse -Force -File -ErrorAction SilentlyContinue C:\Windows\System32, C:\Windows\Temp, C:\ProgramData, C:\Users | Where-Object { $_.LastWriteTimeUtc -ge $su -and $_.LastWriteTimeUtc -le $eu } | Format-List FullName, Length, LastWriteTimeUtc }
} else {
    $skipped.Add('olay kayitlari ve changed_files.txt (-Start/-End verilmedi)')
}

# --- suspicious files: hash at the original path, then a read-only copy ---
$origHashes = New-Object System.Collections.Generic.List[string]
$renamed = New-Object System.Collections.Generic.List[string]
foreach ($f in $Suspicious) {
    if (-not (Test-Path -LiteralPath $f -PathType Leaf)) { $status.Add("supheli dosya yok: $f"); continue }
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $f).Hash.ToLower()
    $base = (Split-Path $f -Leaf) + '.kanit'; $n = 1
    while (Test-Path -LiteralPath (Join-Path $Out $base)) { $n++; $base = (Split-Path $f -Leaf) + "_$n.kanit" }
    $dst = Join-Path $Out $base
    Copy-Item -LiteralPath $f -Destination $dst
    Set-ItemProperty -LiteralPath $dst -Name IsReadOnly -Value $true
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $dst).Hash.ToLower() -ne $h) { $status.Add("$f : kopyanin hash'i orijinalden farkli") }
    $origHashes.Add("$h  $f")
    if ($n -gt 1) { $renamed.Add("$f -> $base") }
}

# --- collection note, then the manifest over every file in the folder ---
$note = @(
    "Host: $(hostname)"
    "Etki alani denetleyicisi: $isDC"
    "Toplayan: $([Security.Principal.WindowsIdentity]::GetCurrent().Name)"
    "Toplama zamani (UTC): $([DateTime]::UtcNow.ToString('o'))"
    "Saat dilimi: $((Get-TimeZone).Id)"
    "Olay penceresi (yerel): $(if ($window) { "$Start -> $End" } else { 'yok' })"
    'Betik: tools/win_collect.ps1 (komutlar betikte; olay zamanlari UTC)'
    'Aktarim yolu: <kullanici doldurur>'
    ''
    '## Supheli dosyalar (orijinal yerdeki SHA-256)'
    $origHashes
    '## Yeniden adlandirilanlar'
    $renamed
    '## Atlananlar'
    $skipped
    '## Komut durumu (hata / sifir olmayan cikis kodu)'
    $status
)
$note | Out-File -FilePath (Join-Path $Out 'TOPLAMA_NOTU.txt') -Encoding UTF8

Get-ChildItem -LiteralPath $Out -File | Where-Object Name -ne 'MANIFEST.sha256' | Sort-Object Name |
    ForEach-Object { '{0}  {1}' -f (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLower(), $_.Name } |
    Out-File -FilePath (Join-Path $Out 'MANIFEST.sha256') -Encoding ASCII

Write-Host "Tamam: $Out ($((Get-ChildItem -LiteralPath $Out -File).Count) dosya). Hatalar TOPLAMA_NOTU.txt -> Komut durumu."
Write-Host 'Klasoru oldugu gibi evidence/<host>/ altina kopyalayin; icerigini degistirmeyin.'
