---
name: config-audit
description: Audits configuration files (sshd_config, nginx/apache, exported firewall rules etc.) read-only against a security checklist and writes a report with hardening recommendations. Use when the user gives a config file and asks "is it secure", "audit it", "hardening" (Turkish: "güvenli mi", "denetle", "sertleştirme").
---

# Configuration Audit

## Input
- Local path and type of the configuration file. If the type is unclear, infer it from the content; if unsure, ask.

## Steps
1. Read the file. Do not count comment lines (`#`) as active settings; note the default value separately.
2. Apply the relevant checklist (below). For each item: current value, expected value, line number.
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

No checklist exists yet for other file types. Assess them by general principles and state this in the report's Kapsam section.

## Limits
- Do not modify the file. This skill only produces recommendations; the user applies changes.
- Do not restart services or change firewall rules.
