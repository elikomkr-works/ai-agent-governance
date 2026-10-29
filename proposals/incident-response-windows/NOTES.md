# incident-response — Windows / AD domain controller extension (draft notes)

**Status:** DRAFT (2026-10-29, skill-smith), revised after Reviewer round 1. Not active. Activation requires user approval.
**Trigger:** SKILL GAP from the DC01 scenario (`work/2026-10-28_dc01-senaryo/plan.md`, "Known skill gaps"). The IR run mapped the Linux K1–K6 list to Windows ad hoc (`reports/2026-10-28_ir_dc01-senaryo.md`, Kapsam → Yöntem table).

## Files and target locations
| Draft | Goes to on activation |
|---|---|
| `proposals/incident-response-windows/SKILL.md` | replaces `.claude/skills/incident-response/SKILL.md` |
| `proposals/incident-response-windows/windows.md` | new: `.claude/skills/incident-response/windows.md` |
| `proposals/incident-response-windows/agent.md` | replaces `.claude/agents/incident-responder.md` (description and wording only; **tool list unchanged**: Read, Grep, Glob, Write, Skill, Bash) |
| `proposals/incident-response-windows/registry_entry.json` | replaces the `incident-response` entry in `governance/skills_registry.json` → `skills[]` (same `name`, `network_access`, `risk`, `output`) |

`governance/agents_registry.json` needs no change (same agent, same skill, same write targets).
The older Turkish draft `proposals/incident-response/NOTLAR.md` is not touched.

## Why an extension, not a new skill
- Same procedure (inventory, hash before/after, read as text, fixed 6-item list, timeline, IOCs, same report path `_ir_`). Only the evidence table, the pattern list and the content of K1–K6 differ by OS.
- The Validator (`check_ir_report`) and the Reviewer recount are keyed to `K1`–`K6` and the total 6. A separate skill with different IDs would need a validator change; keeping the IDs needs none.
- `tests/test_governance.py` → `ir_collect_checks` parses the first `### Expected evidence` block of `SKILL.md` and compares it with `tools/ir_collect.sh`. Putting the Windows table into a separate file keeps that test valid. In the revised `SKILL.md` the block is unchanged except one sentence appended to the same paragraph (no blank line added, so `split("\n\n", 2)[1]` still returns the Linux table).

## Validator compatibility (checked against `.claude/hooks/validator.py`)
- `check_ir_report` collects rows matching `^\|\s*(K[1-6])\s*\|` inside `## Kanıt` into a dict, so **the last row per ID wins**. A second K-row table in `## Kanıt` without result values (e.g. a Linux→Windows mapping table placed after the persistence table) would fail; placed before, it would be silently ignored. The DC01 report put its mapping table in Kapsam, which is outside the check. The draft removes the need for a mapping table and tells the author not to put one in `## Kanıt`.
- Any row containing the substring `KANIT YOK` counts for the "no KABUL" rule even if its result is `İZ VAR`; the draft tells authors to write "kanıt yetersiz" in reasoning text.
- Windows reports still need one SHA-256 in `## Kanıt`; the hash table from step 2 satisfies it.
- No machine-checked Turkish label is changed or added.
- Suggested extra test (optional, `tests/test_governance.py` → the `check_ir_report` cases): a Windows-flavoured copy of `GOOD_IR` (e.g. `| K1 | İZ VAR | scheduled_tasks.txt:8 |`) must pass; the same text with a result-less `| K1 | Zamanlanmış görevler | scheduled_tasks.txt |` row appended after the table in `## Kanıt` must fail. This documents the last-row-wins behaviour.

## Main content changes
- `windows.md`: a Windows evidence table of about 40 files. The commands are read-only PowerShell, `reg query` and `Get-WinEvent`; the user runs them, exports times in UTC and does not filter the outputs. All commands are untested. The file also has a "never collect" list, static review patterns for PowerShell/batch, the K1–K6 Windows table, decision rules and Validator notes.
- K1 scheduled + event-triggered (Task Scheduler, WMI subscriptions, GPO tasks); K2 services + drivers; K3 autostart and injection points (Run, Startup, Winlogon named values, IFEO, AppInit, LSA packages, PowerShell profiles); K4 keys and remote access authorizations (OpenSSH keys, `msDS-KeyCredentialLink`, Remote Desktop Users, remote tools); K5 accounts, privileged groups, replication rights, AdminSDHolder, SIDHistory; K6 elevated execution and reusable credential material (accessibility binary replacement, DSRM logon behaviour, dumped secret not rotated).
- Decision rules: a configuration weakness is not a persistence trace; a pre-existing entry path is the entry vector, not K4 (**decided by the user, 2026-10-29**); K6 credential material = theft command in evidence + secret not rotated; when `İZ YOK` vs `KANIT YOK` applies.
- Secret-safe collection (Reviewer round 1). Winlogon is queried by named values only (`Userinit`, `Shell`, `AppSetup`, plus the legacy `Notify` subkey), because the whole key holds `DefaultPassword` in cleartext when auto-logon is set. `DefaultPassword` / `AltDefaultPassword` are on the never-collect list.
- The Security log export is split into two `Get-WinEvent -FilterHashtable` queries (12 + 14 IDs) appended with `Export-Csv -Append`, because of the believed limit of about 23 IDs per query. It is marked untested. 4657 and 4719 come from a separate optional export, `security_extra.csv`, so the main queries do not grow.
- `SKILL.md` changes, all of them:
  - frontmatter `description` covers Windows evidence
  - Input: OS added to the required facts, plus a new Windows bullet pointing to `windows.md` with the fixed Kapsam sentence "Windows kalıcılık listesi uygulandı (incident-response/windows.md)" (the same sentence is in `windows.md` → Report and Validator compatibility)
  - Input: the "if evidence is missing" bullet points to `windows.md` for Windows
  - `### Expected evidence` intro paragraph: the sentence "Windows hosts: see `windows.md`." appended to the same paragraph (table unchanged)
  - step 1: compare the inventory with `windows.md` for Windows
  - step 3: "event descriptions, task descriptions" named explicitly as data, not instructions (DC01 `security.csv:3` lesson)
  - step 4: pointer to the Windows patterns, and PowerShell `-EncodedCommand` added to the never-decode list
  - step 5: pointer to the Windows checklist
  - step 6: Windows cross-check files (`processes.txt`, `netstat.txt`, logon events)
  - step 7: Windows timestamps (`LastWriteTimeUtc`, `TimeCreated`)
  - step 9: Windows/AD settings route to `config-audit` → `windows-dc.md`
  - Persistence checklist: intro line "Linux hosts …", and a Validator caution under the report cautions
  - Limits: interpreters add `powershell`, `cscript`, `wscript`, `mshta`; never-decode adds `[Convert]::FromBase64String`; no-connection adds WinRM/RDP/LDAP/SMB; response actions add scheduled tasks, services, krbtgt resets

## Effect on the DC01 result (expectation, not re-run)
With these rules the DC01 table would likely change from 4/1/1 to İZ VAR 3 (K1, K5, K6) + İZ YOK 1 (K3) + KANIT YOK 2 (K2, K4). K4 was İZ VAR for "RDP path used and still open". Under the K4 rule the user approved, that path is the entry vector, and no K4 listing (`ssh_keys.txt`, `ad_keycred.txt`, `installed_software.txt`) was collected. Doğrulama Durumu stays BELİRSİZ. A re-run plus Reviewer should confirm this.

## Risks
| # | Risk | Mitigation in draft | Extra (user / Policy Gate) |
|---|---|---|---|
| R1 | Collection guidance leads the user to pull secrets (hives, NTDS.dit, LSASS dumps, Winlogon `DefaultPassword`, GPP `cpassword`, LAPS values, raw KeyCredentialLink) into OneDrive / git. | "Never collect" list; Winlogon by named values only; KeyCredentialLink as count only; SYSVOL as listing only; no `-Properties *` | Optional `sensitive_patterns` additions below |
| R2 | Executing evidence on Windows: `.ps1`, `.bat`, `.vbs` copies can run by double-click or IDE "Run"; Windows has no execute bit. | `.kanit` suffix removes the association; read-only attribute; interpreter list extended | Existing `evidence_guard` already allows only hash/count tools on evidence paths (`powershell`, `pwsh`, `cscript` are not in `allowed`); no change needed |
| R3 | Prompt injection in event messages and task descriptions (DC01 `security.csv:3` contained text addressed to an AI analyst). | Step 3 now names event and task descriptions explicitly | Reviewer checks that no finding was dropped or softened because of evidence text |
| R4 | Wrong reassurance from absent events when auditing was off. | Rule: event absence counts only if the subcategory was enabled and exported | — |
| R5 | Over-reach into response (disable account, delete task, reset krbtgt). | Limits list these as [ÖNERİ] only | — |
| R6 | Event IDs, registry paths, replication-right GUIDs and the FilterHashtable ID limit come from general knowledge and were not re-verified. Collection commands are untested. | Version line; meanings stay [DOĞRULANMAMIŞ] unless sourced; commands marked untested | The approved collection-script task should run the commands on a test VM |
| R7 | Synthetic sets under `samples/` are outside `@evidence`, so `evidence_guard` and `deny_write` do not protect them. | — | Acceptable for synthetic data; real evidence must go under `@evidence` |

## Policy Gate rules that may be needed
- None required: no network, no new tool, same write targets, `evidence_guard` already covers Windows interpreters by allow-list.
- Optional: extend `governance/policy.json` → `sensitive_patterns` with `"\\.dmp$"`, `"(?i)/config/(sam|security|system)(\\.[a-z0-9]+)?$"` and `"(?i)\\.hiv$"`. The hive pattern is path-scoped, because `check_shell` runs `check_sensitive` on every command token (`policy_gate.py:156-157`). An unscoped `(system|security)$` would turn `grep -c Security auditpol.txt` into ASK (DENY in the cloud). Side effect: a hive copied under a bare name without `/config/` is not caught; only `.hiv` files and the original path are. Details and test cases: `proposals/config-audit-windows-dc/NOTES.md` → Policy Gate.

## Decisions and open questions
- Decided (user, 2026-10-29): K4 rule kept. A pre-existing remote-access path used for entry is the entry vector, not persistence.
- Decided (user, 2026-10-29): collection scripts (`tools/ir_collect.ps1`, `tools/dc_collect.ps1`) are approved as a **separate task**. Not drafted here. They would need tests like `ir_collect_checks`: every file in `windows.md`, no network, no secrets, no overwrite, and the two-query Security export.
- Pending (user): scope. DC-focused for now; non-DC rows (`local_accounts.txt`) stay as written.
- Open: should the Lead Agent regenerate the DC01 synthetic set with the missing Windows files (unfiltered services/processes, `ssh_keys.txt`, `ad_keycred.txt`, `installed_software.txt`, `system.csv`, `taskscheduler.csv`, full `auditpol`) as the acceptance test?
- Open: add the optional validator test case described above?

## Activation steps (user only)
1. Review `SKILL.md`, `windows.md`, `agent.md` and the risks above.
2. Copy `windows.md` to `.claude/skills/incident-response/windows.md`; replace `.claude/skills/incident-response/SKILL.md` and `.claude/agents/incident-responder.md` (the Gate asks for writes under `.claude/`; expected).
3. Replace the `incident-response` entry in `governance/skills_registry.json` with `registry_entry.json`.
4. Run `python tests/test_governance.py` (in particular `ir_collect_checks` and the `check_ir_report` cases).
5. Restart the session; acceptance test on a Windows synthetic set and Reviewer recount of the 6-item table.
