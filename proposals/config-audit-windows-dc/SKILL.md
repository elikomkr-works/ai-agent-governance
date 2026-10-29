---
name: config-audit
description: Audits configuration files and exported configuration outputs (sshd_config, nginx/apache, exported firewall rules, Windows Server / Active Directory domain controller outputs such as reg query, auditpol, Get-AD*, Get-ADDefaultDomainPasswordPolicy, gpresult) read-only against a security checklist and writes a report with hardening recommendations. Use when the user gives a config file or a set of exported config outputs and asks "is it secure", "audit it", "hardening" (Turkish: "güvenli mi", "denetle", "sertleştirme").
---

# Configuration Audit

## Input
- Local path and type of the configuration file. If the type is unclear, infer it from the content; if unsure, ask.
- For a Windows Server / Active Directory domain controller: the local path of the folder with exported outputs (one command output per file) and the collection note (`TOPLAMA_NOTU.txt`: host, collection time in UTC, time zone, commands). The expected files and their read-only collection commands are in `windows-dc.md` (this folder). If files are missing, give the user the collection command from that table; never run it yourself.

## Steps
1. Read the file. Do not count comment lines (`#`) as active settings; note the default value separately.
2. Apply the relevant checklist (below, or the referenced file). For each item: current value, expected value, line number.
3. Write the results:
   - Non-compliance → `[OLGU]`
   - Fix recommendation → `[ÖNERİ]`
   - Unverifiable matters such as version-dependent defaults → `[DOĞRULANMAMIŞ]`
4. Write the report in Turkish as `reports/YYYY-MM-DD_config_<short-name>.md`. Template: `governance/templates/report.md`.

## Checklist — OpenSSH sshd_config
| Setting | Expected |
|---|---|
| PermitRootLogin | no (or prohibit-password) |
| PasswordAuthentication | no |
| PermitEmptyPasswords | no |
| MaxAuthTries | 3–4 |
| X11Forwarding | no |
| PubkeyAuthentication | yes |
| LoginGraceTime | ≤ 60 |
| AllowUsers / AllowGroups | defined |

## Checklist — Windows Server / Active Directory domain controller
Read `windows-dc.md` in this folder and apply it fully. It defines fixed item IDs (`AD01`–`AD72`), the evidence file for each item, the expected value and the counting rule (Uyumlu + Uyumsuz + Değerlendirilemedi = number of items applied). Name the checklist and its version line in the report's Kapsam section.

No checklist exists yet for other file types. Assess them by general principles and state this in the report's Kapsam section.

## Limits
- Do not modify the file. This skill only produces recommendations; the user applies changes.
- Do not restart services or change firewall rules.
- Never run collection commands on a host and never connect to a domain controller (no LDAP, WinRM, RDP, SMB). Work only on exported outputs the user provided.
- Never request or read secret values: LAPS password attributes (`ms-Mcs-AdmPwd`, `msLAPS-Password`, `msLAPS-EncryptedPassword`), `NTDS.dit`, `SAM`/`SECURITY`/`SYSTEM` hives, LSASS memory dumps, DSRM passwords. If such content is in the input, do not copy it; write its location (file:line) and type, mask the value, and recommend removing it from the folder.
