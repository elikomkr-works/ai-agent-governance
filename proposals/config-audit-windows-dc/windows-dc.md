# Checklist — Windows Server / Active Directory domain controller

Version: draft 2026-10-29 (skill-smith). Expected values follow commonly cited Microsoft Security Baseline / CIS Benchmark values for Windows Server 2019/2022 domain controllers. **They were not fetched from a primary source in this draft.** Until a verified baseline record exists under `knowledge/approved/`, every expected value that relies on a baseline is `[DOĞRULANMAMIŞ]` in the report; the current value read from the file stays `[OLGU]`.

## How to apply
1. **Inventory.** List the input folder. Compare it with the evidence table below. Write missing files in Kapsam; the items depending on them become `Değerlendirilemedi`.
2. **Read each item's current value** from its evidence file with file:line. Registry output: `reg query` prints only values that exist. An absent value means the built-in default applies; defaults are version-dependent → write the default as `[DOĞRULANMAMIŞ]`.
3. **Status per item** (report labels, Turkish, not machine-checked):
   - `Uyumlu` — current value meets the expected value.
   - `Uyumsuz` — current value does not meet it. If the decision relies on a default (value absent from a complete, unfiltered output), write `Uyumsuz (varsayılan)` and add a `[DOĞRULANMAMIŞ]` finding for the default.
   - `Değerlendirilemedi` — file missing, output filtered/truncated, or command failed. Never count absence in a filtered output as `Uyumsuz`.
4. **Out of scope.** If an item does not apply (e.g. AD05 when the RDP role is removed), list it in Kapsam with the reason. It is excluded from the total.
5. **Counting rule.** Uyumlu + Uyumsuz + Değerlendirilemedi = 72 − (out-of-scope items). Write the sum explicitly in Bulgular → Özet sayım; the Reviewer recounts the table.
6. **Origin of a setting.** Without `gpresult.txt` you cannot tell whether a value comes from a GPO or a local setting. Say so in Kapsam; a local fix may be overwritten by a GPO.
7. **Report table columns:** `# | Alan | Madde | Mevcut değer (dosya:satır) | Beklenen | Durum`. Keep the item IDs below unchanged so reports are comparable across hosts.

## Expected evidence (user collects on the DC, elevated PowerShell, read-only)
Write each output to a separate UTF-8 file. Prefer `Format-List` or `Out-String -Width 4096`; `Format-Table` truncates columns. Do not filter outputs (`findstr`, `Select-String`, `Where-Object`) unless the table says so; filtered outputs force `Değerlendirilemedi`. Add every file to `MANIFEST.sha256` (`Get-FileHash -Algorithm SHA256 <file> | ForEach-Object { "{0}  {1}" -f $_.Hash.ToLower(), (Split-Path $_.Path -Leaf) }`).

| File | Content | Sample collection command (user, on the DC) |
|---|---|---|
| `TOPLAMA_NOTU.txt` | host, domain, collector, time (UTC), time zone, commands, transfer path | `hostname; [DateTime]::UtcNow.ToString('o'); Get-TimeZone` |
| `systeminfo.txt` | OS, build, role, boot time | `systeminfo` |
| `ubr.txt` | build and update build revision | `reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v CurrentBuild` and `/v UBR` |
| `hotfix.txt` | installed updates | `Get-HotFix \| Sort-Object InstalledOn \| Format-List *` |
| `rdp.txt` | RDP state, NLA, security layer (local and policy) | `reg query "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections; reg query "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp"; reg query "HKLM\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services"` |
| `firewall_rdp.txt` | RDP inbound rules with address filter | `Get-NetFirewallRule -Direction Inbound \| Where-Object { ($_ \| Get-NetFirewallPortFilter).LocalPort -eq 3389 } \| ForEach-Object { $_ \| Format-List DisplayName,Enabled,Profile,Action; $_ \| Get-NetFirewallAddressFilter \| Format-List RemoteAddress }` (port filter instead of the localized display group name) |
| `lsa.txt` | the whole `Lsa` key, **unfiltered** (RunAsPPL, LmCompatibilityLevel, NoLmHash, RestrictAnonymous*, EveryoneIncludesAnonymous, SCENoApplyLegacyAuditPolicy, DsrmAdminLogonBehavior, packages) | `reg query HKLM\SYSTEM\CurrentControlSet\Control\Lsa` |
| `wdigest.txt` | WDigest provider | `reg query HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest` |
| `deviceguard.txt` | VBS / HVCI / Credential Guard state | `Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard \| Format-List *` |
| `smb.txt` | SMB server signing and SMBv1 | `Get-SmbServerConfiguration \| Format-List EnableSMB1Protocol,RequireSecuritySignature,EnableSecuritySignature` |
| `ldap_netlogon.txt` | LDAP signing / channel binding, Netlogon secure channel, NTLM audit | `reg query HKLM\SYSTEM\CurrentControlSet\Services\NTDS\Parameters; reg query HKLM\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters` |
| `services.txt` | all services, **unfiltered** | `Get-CimInstance Win32_Service \| Format-List Name,StartMode,State,PathName,StartName` |
| `privileged_groups.txt` | members of privileged and operator groups | `foreach ($g in 'Domain Admins','Enterprise Admins','Schema Admins','Administrators','Account Operators','Server Operators','Backup Operators','Print Operators','DnsAdmins','Group Policy Creator Owners','Remote Desktop Users','Protected Users') { "## $g"; Get-ADGroupMember -Identity $g -Recursive \| Format-List Name,SamAccountName,objectClass }` |
| `ad_users.txt` | account hygiene attributes (no secrets) | `Get-ADUser -Filter * -Properties whenCreated,PasswordLastSet,LastLogonDate,PasswordNeverExpires,DoesNotRequirePreAuth,PasswordNotRequired,AllowReversiblePasswordEncryption,AccountNotDelegated,TrustedForDelegation,adminCount,servicePrincipalName \| Format-List SamAccountName,SID,Enabled,whenCreated,PasswordLastSet,LastLogonDate,PasswordNeverExpires,DoesNotRequirePreAuth,PasswordNotRequired,AllowReversiblePasswordEncryption,AccountNotDelegated,TrustedForDelegation,adminCount,@{n='SPNCount';e={$_.servicePrincipalName.Count}}` |
| `ad_delegation.txt` | computers trusted for unconstrained delegation | `Get-ADComputer -Filter 'TrustedForDelegation -eq $true' -Properties PrimaryGroupID \| Format-List Name,PrimaryGroupID` (516 = DC) |
| `password_policy.txt` | default domain policy and fine-grained policies | `Get-ADDefaultDomainPasswordPolicy \| Format-List *; Get-ADFineGrainedPasswordPolicy -Filter * \| Format-List *` |
| `auditpol.txt` | **all** advanced audit subcategories | `auditpol /get /category:*` |
| `audit_options.txt` | command line in process creation events | `reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Audit` |
| `eventlog_config.txt` | Security and PowerShell log size / retention | `wevtutil gl Security; wevtutil gl Microsoft-Windows-PowerShell/Operational` |
| `powershell_config.txt` | execution policy, logging policies, v2 engine | `Get-ExecutionPolicy -List; reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\PowerShell /s; Get-WindowsFeature PowerShell-V2` |
| `laps.txt` | LAPS schema presence and password **expiry** only | `Get-ADObject -SearchBase (Get-ADRootDSE).schemaNamingContext -LDAPFilter '(\|(name=ms-Mcs-AdmPwd)(name=ms-LAPS-Password)(name=ms-LAPS-PasswordExpirationTime))' \| Format-List Name`; then, only if the Windows LAPS attribute exists: `Get-ADComputer -Filter * -Properties msLAPS-PasswordExpirationTime \| Format-List Name,msLAPS-PasswordExpirationTime` |
| `defender.txt` | Defender state and age of signatures | `Get-MpComputerStatus \| Format-List AMServiceEnabled,RealTimeProtectionEnabled,AMProductVersion,AMEngineVersion,AntivirusSignatureLastUpdated,AntivirusSignatureAge` |
| `gpresult.txt` (optional) | which GPO sets which value | `gpresult /scope computer /v` |

Never collect: LAPS password attributes (`ms-Mcs-AdmPwd`, `msLAPS-Password`, `msLAPS-EncryptedPassword`), `NTDS.dit`, registry hives (`SAM`, `SECURITY`, `SYSTEM`), LSASS dumps, `Get-ADUser -Properties *` (pulls attributes not needed here). The `laps.txt` command above reads schema names and expiry times only.

## Checklist

### A. Remote access
| # | Item | File | Expected |
|---|---|---|---|
| AD01 | RDP on the DC (`fDenyTSConnections`) | `rdp.txt` | 1 (off), or on only with AD04 compliant |
| AD02 | RDP Network Level Authentication (`UserAuthentication`) | `rdp.txt` | 1 |
| AD03 | RDP security layer (`SecurityLayer`) | `rdp.txt` | 2 (TLS) |
| AD04 | RDP firewall rule scope (`RemoteAddress`, `Profile`) | `firewall_rdp.txt` | management network / PAW / jump host only; not `Any`; not Public profile |
| AD05 | `Remote Desktop Users` group on the domain | `privileged_groups.txt` | empty (admins use their admin groups) |

### B. Credential protection
| # | Item | File | Expected |
|---|---|---|---|
| AD06 | WDigest `UseLogonCredential` | `wdigest.txt` | 0 or absent |
| AD07 | LSA protection `RunAsPPL` | `lsa.txt` | 1 or 2 |
| AD08 | Virtualization-based security / HVCI | `deviceguard.txt` | VBS running, HVCI on (Credential Guard is not the control on a DC; see note) |
| AD09 | `LmCompatibilityLevel` | `lsa.txt` | 5 |
| AD10 | `NoLmHash` | `lsa.txt` | 1 |
| AD11 | `RestrictAnonymous` | `lsa.txt` | 1 |
| AD12 | `RestrictAnonymousSAM` | `lsa.txt` | 1 |
| AD13 | `EveryoneIncludesAnonymous` | `lsa.txt` | 0 |

### C. Protocol hardening
| # | Item | File | Expected |
|---|---|---|---|
| AD14 | SMB server signing required (`RequireSecuritySignature`) | `smb.txt` | True |
| AD15 | SMBv1 (`EnableSMB1Protocol`) | `smb.txt` | False |
| AD16 | LDAP server signing (`LDAPServerIntegrity`) | `ldap_netlogon.txt` | 2 (require) |
| AD17 | LDAP channel binding (`LdapEnforceChannelBinding`) | `ldap_netlogon.txt` | 2 (1 acceptable during transition, write as [ÖNERİ]) |
| AD18 | Netlogon secure channel (`FullSecureChannelProtection`, `RequireSignOrSeal`) | `ldap_netlogon.txt` | 1 and 1 |
| AD19 | Print Spooler service on the DC | `services.txt` | Disabled and Stopped |
| AD20 | NTLM audit in the domain (`AuditNTLMInDomain`) | `ldap_netlogon.txt` | 7 (audit all), as a step before restricting NTLM |

### D. Privileged groups and delegation
| # | Item | File | Expected |
|---|---|---|---|
| AD21 | Domain Admins membership | `privileged_groups.txt`, `ad_users.txt` | minimal; no service accounts; no daily-use personal accounts |
| AD22 | Enterprise Admins membership | `privileged_groups.txt` | empty or break-glass only |
| AD23 | Schema Admins membership | `privileged_groups.txt` | empty |
| AD24 | Account / Server / Backup / Print Operators, DnsAdmins | `privileged_groups.txt` | empty, or each member documented |
| AD25 | Protected Users | `privileged_groups.txt` | contains the human admin accounts (not service or computer accounts) |
| AD26 | Admin accounts "sensitive and cannot be delegated" (`AccountNotDelegated`) | `ad_users.txt` | True for every member of AD21–AD24 groups |
| AD27 | Unconstrained delegation (`TrustedForDelegation`) | `ad_delegation.txt`, `ad_users.txt` | only DCs (PrimaryGroupID 516); no user accounts |

### E. Account hygiene
| # | Item | File | Expected |
|---|---|---|---|
| AD28 | `krbtgt` password age (`PasswordLastSet`) | `ad_users.txt` | ≤ 180 days; reset twice after any suspected compromise |
| AD29 | Built-in Administrator (SID ending `-500`) password age and use | `ad_users.txt` | age ≤ domain MaxPasswordAge; no routine `LastLogonDate` |
| AD30 | Privileged accounts with `PasswordNeverExpires` | `ad_users.txt`, `privileged_groups.txt` | none, unless documented |
| AD31 | Accounts with `DoesNotRequirePreAuth` | `ad_users.txt` | none |
| AD32 | Privileged accounts with a service principal name (`SPNCount > 0`) | `ad_users.txt`, `privileged_groups.txt` | none |
| AD33 | Accounts with `PasswordNotRequired` or `AllowReversiblePasswordEncryption` | `ad_users.txt` | none |

### F. Password and lockout policy
| # | Item | File | Expected |
|---|---|---|---|
| AD34 | Lockout threshold (`LockoutThreshold`) | `password_policy.txt` | 1–10 (0 = never locks) |
| AD35 | Lockout duration / observation window | `password_policy.txt` | ≥ 15 minutes each |
| AD36 | Minimum password length | `password_policy.txt` | ≥ 14 (PSO for admins if the default policy cannot be raised) |
| AD37 | Password history | `password_policy.txt` | 24 |
| AD38 | Complexity | `password_policy.txt` | True |
| AD39 | Maximum password age | `password_policy.txt` | > 0 and ≤ 365 days |
| AD40 | Minimum password age | `password_policy.txt` | ≥ 1 day |
| AD41 | Reversible encryption (domain policy) | `password_policy.txt` | False |

### G. Audit policy and logs
Subcategory names are as printed by `auditpol` in English; on a localized system match by position in the category and note it in Kapsam.

| # | Item | File | Expected |
|---|---|---|---|
| AD42 | Credential Validation | `auditpol.txt` | Success and Failure |
| AD43 | Kerberos Authentication Service | `auditpol.txt` | Success and Failure |
| AD44 | Kerberos Service Ticket Operations | `auditpol.txt` | Success and Failure |
| AD45 | Computer Account Management | `auditpol.txt` | Success |
| AD46 | Security Group Management | `auditpol.txt` | Success (Failure optional) |
| AD47 | User Account Management | `auditpol.txt` | Success and Failure |
| AD48 | Other Account Management Events | `auditpol.txt` | Success |
| AD49 | Directory Service Access | `auditpol.txt` | Success and Failure; plus a SACL on the domain root for replication rights (not visible here → write as [ÖNERİ]) |
| AD50 | Directory Service Changes | `auditpol.txt` | Success |
| AD51 | Logon | `auditpol.txt` | Success and Failure |
| AD52 | Special Logon | `auditpol.txt` | Success |
| AD53 | Account Lockout | `auditpol.txt` | Failure |
| AD54 | Process Creation, with command line (`ProcessCreationIncludeCmdLine_Enabled`) | `auditpol.txt`, `audit_options.txt` | Success and 1 |
| AD55 | Sensitive Privilege Use | `auditpol.txt` | Success and Failure |
| AD56 | Audit Policy Change | `auditpol.txt` | Success |
| AD57 | Security System Extension | `auditpol.txt` | Success |
| AD58 | Security State Change | `auditpol.txt` | Success |
| AD59 | System Integrity | `auditpol.txt` | Success and Failure |
| AD60 | Other Object Access Events (scheduled task events) | `auditpol.txt` | Success and Failure |
| AD61 | Subcategory settings override category settings (`SCENoApplyLegacyAuditPolicy`) | `lsa.txt` | 1 |
| AD62 | Security log size and forwarding | `eventlog_config.txt` | `maxSize` large enough for the retention target; forwarded to a central collector (forwarding not visible here → [ÖNERİ]) |

### H. PowerShell
| # | Item | File | Expected |
|---|---|---|---|
| AD63 | Script Block Logging (`EnableScriptBlockLogging`) | `powershell_config.txt` | 1 |
| AD64 | Module Logging (`EnableModuleLogging`) | `powershell_config.txt` | 1 |
| AD65 | Transcription (`EnableTranscripting`, `OutputDirectory`) | `powershell_config.txt` | 1, to a protected central location |
| AD66 | Windows PowerShell 2.0 engine | `powershell_config.txt` | Removed / Available (not Installed) |
| AD67 | Execution Policy (MachinePolicy / LocalMachine) | `powershell_config.txt` | RemoteSigned or AllSigned via GPO (not a security boundary; see note) |

### I. Local admin passwords and DSRM
| # | Item | File | Expected |
|---|---|---|---|
| AD68 | LAPS deployed domain-wide | `laps.txt` | Windows LAPS schema attribute present; member computers have a future `msLAPS-PasswordExpirationTime` |
| AD69 | DSRM administrator network logon (`DsrmAdminLogonBehavior`) | `lsa.txt` | absent or 0 |

### J. Patch level and protection
| # | Item | File | Expected |
|---|---|---|---|
| AD70 | OS cumulative update level | `hotfix.txt`, `ubr.txt`, `systeminfo.txt` | latest monthly cumulative update; age of last update in days written with the calculation |
| AD71 | Defender service and real-time protection | `defender.txt` (or `services.txt`) | service enabled, real-time protection True |
| AD72 | Defender signature age | `defender.txt` | `AntivirusSignatureAge` ≤ 1–2 days |

Total: 72 items (A 5, B 8, C 7, D 7, E 6, F 8, G 21, H 5, I 2, J 3).

## Notes for the report (write as `[DOĞRULANMAMIŞ]` unless a verified source is cited)
- Credential Guard is generally described as not providing protection for the DC's own AD database; on a DC the meaningful controls are VBS/HVCI, `RunAsPPL`, Protected Users and tiered admin accounts.
- Execution Policy is not a security boundary (`-ExecutionPolicy Bypass`); real control is application control (AppLocker / WDAC) plus logging. AD67 non-compliance is low priority.
- The PowerShell 2.0 engine does not support Script Block Logging or AMSI, so AD66 weakens AD63.
- Directory Service Access (AD49) alone does not produce DCSync events (4662) without a SACL for the replication rights.
- AD28: after compromise, reset `krbtgt` twice with full replication and at least one maximum ticket lifetime in between; this is an [ÖNERİ] for the user, never an action.
- Version- and patch-dependent statements (supported build for a cumulative update, default of an absent value) are `[DOĞRULANMAMIŞ]`; known vulnerabilities for the build go to `cve-researcher` as a help request.
- Settings that enabled the incident and settings that would have detected it may be grouped as separate Bulgular subsections (as in `reports/2026-10-28_config_dc01-senaryo.md`); item IDs stay as above.
