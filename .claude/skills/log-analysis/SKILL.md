---
name: log-analysis
description: Defensively analyzes local log files (SSH/auth.log, web server access logs, exported Windows events); finds brute force, suspicious IPs, failed→successful logins and privilege escalation traces, and writes an evidence-backed report. Use when the user gives a log file and asks to analyze it or whether there is an attack or suspicious login (Turkish: "analiz et", "saldırı var mı", "şüpheli giriş").
---

# Log Analysis

## Input
- Local path of the log file to analyze. If not given, ask the user; do not guess file names.

## Steps
1. Read the file. If it is large, search patterns with Grep first, then read the relevant parts.
2. Look for: failed logins, heavy attempts from one source, invalid user names,
   a successful login following failed attempts, sudo/privilege changes, unusual hours.
3. Count numbers with a command (e.g. `grep -c`, `Select-String | Measure-Object`). Never write estimated counts.
4. For every [OLGU], put the relevant log line with its line number in the `## Kanıt` section.
5. Write the report in Turkish as `reports/YYYY-MM-DD_log_<short-name>.md`. Template: `governance/templates/report.md`.
6. Doğrulama Durumu:
   - KABUL: every fact matches evidence and the numbers were verified by command
   - BELİRSİZ: data missing or interpretation needed
   - RED: analysis could not be completed

## Limits
- Never scan, ping or connect to IPs in the log. Network actions are outside this skill's scope.
- Do not claim an IP is malicious without a source; if you do, tag it [DOĞRULANMAMIŞ].
- Never modify or delete the log file.
