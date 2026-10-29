# config-audit — Windows Server / AD domain controller checklist (draft notes)

**Status:** DRAFT (2026-10-29, skill-smith), revised after Reviewer round 1. Not active. Activation requires user approval.
**Trigger:** SKILL GAP from the DC01 scenario (`work/2026-10-28_dc01-senaryo/plan.md`, "Known skill gaps"). The config run fell back to general principles and built an ad hoc 44-item list (`reports/2026-10-28_config_dc01-senaryo.md`, Kapsam → Yöntem).

## Files and target locations
| Draft | Goes to on activation |
|---|---|
| `proposals/config-audit-windows-dc/SKILL.md` | replaces `.claude/skills/config-audit/SKILL.md` |
| `proposals/config-audit-windows-dc/windows-dc.md` | new: `.claude/skills/config-audit/windows-dc.md` |
| `proposals/config-audit-windows-dc/registry_entry.json` | replaces the `config-audit` entry in `governance/skills_registry.json` → `skills[]` (same `name`, `network_access`, `risk`, `output`) |

No new agent: `config-auditor` keeps its tool list. No `agent.md`.

## Why an extension, not a new skill
- Same job (read-only audit of config against a checklist, same report path `_config_`, same labels). A separate skill would need a new registry name, router triggers that overlap with `config-audit`, and a second agent mapping for no gain.
- A reference file keeps `SKILL.md` short; the skill loads `windows-dc.md` only for DC input.

## Changes vs. the current skill
- `description` and Input: accept a folder of exported outputs (DC), not only one file.
- New section pointing to `windows-dc.md`: 72 fixed items `AD01`–`AD72`, evidence file per item, expected value, status values (`Uyumlu`, `Uyumsuz`, `Değerlendirilemedi`) and the sum rule. IDs use `AD`, not `DC`, to avoid confusion with host names like DC01.
- Expected-evidence table with read-only collection commands (user runs them). Lessons from DC01 built in: unfiltered `lsa.txt` (C05 was not assessable), full `auditpol /get /category:*` (several subcategories missing), unfiltered `services.txt`, port-based firewall query (display group names are localized).
- New Limits: no connection to a DC, never read secret values.
- sshd_config checklist unchanged. No machine-checked label changed. Validator: config reports go through `check_report` only; nothing new is checked there.

## Risks
| # | Risk | Mitigation in draft | Extra (user / Policy Gate) |
|---|---|---|---|
| R1 | **Secret exposure via LAPS query.** The DC01 `laps.txt` asked `Get-ADComputer` for `ms-Mcs-AdmPwd`; on a domain with legacy LAPS and enough rights this returns cleartext local admin passwords into the evidence folder (and OneDrive). | `laps.txt` command reads schema names and `msLAPS-PasswordExpirationTime` only; Limits forbid password attributes | Fix the sample collection guidance used by the Lead Agent for future synthetic sets |
| R2 | Expected values are not source-verified (no network in this draft). A wrong baseline value yields wrong Uyumsuz/Uyumlu. | Version line + rule: baseline-derived expected values are `[DOĞRULANMAMIŞ]` until a verified record exists | Optional task: `cve-researcher`-style source collection of the Microsoft Security Baseline for WS2019/2022 into `knowledge/quarantine/`, user approves |
| R3 | Recommendations that break a domain if applied blindly (LDAP signing/channel binding, `LmCompatibilityLevel 5`, SMB signing, `RestrictAnonymous`, Spooler off, krbtgt reset). | Skill only writes `[ÖNERİ]`; notes say "audit first / test first" | User decides and applies |
| R4 | Large `ad_users.txt` (all users) contains personal data (names, logon times). | Only hygiene attributes, no `-Properties *` | Keep evidence out of git and pause OneDrive sync (same as incident-response R3) |
| R5 | Sensitive-name patterns: a file named after a hive (`sam`) triggers `sensitive_patterns` → ask. | Neutral file names in the table | Acceptable |

## Policy Gate rules that may be needed
- None required: no network, no new tool, no new write path.
- Optional: extend `governance/policy.json` → `sensitive_patterns` with:
  - `"\\.dmp$"` — LSASS or other memory dumps.
  - `"(?i)/config/(sam|security|system)(\\.[a-z0-9]+)?$"` — registry hives, only when the path contains `/config/` right before the name (e.g. `C:/Windows/System32/config/SYSTEM`).
  - `"(?i)\\.hiv$"` — hives saved with the common `.hiv` extension.
- Why path-scoped: `check_shell` runs `check_sensitive` on every command token (`policy_gate.py:156-157`). An unscoped pattern like `(^|/)(system|security)…$` would match bare words, so `grep -c Security auditpol.txt` would fall to ASK (DENY in a cloud session). The scoped form needs `/config/` in the token.
- Side effect: a hive copied into the evidence folder under a bare name without `/config/` (e.g. `evidence/dc01/system`) is not caught. Only the `.hiv` extension and the original path are. Commands or reads that name the original hive path fall to ASK (DENY in the cloud). That is intended. The existing `sam$` pattern already matches any token ending in "sam"; this draft does not change it.
- Run `python tests/test_governance.py` after adding them, and add cases: `grep -c Security auditpol.txt` → pass; Read `evidence/x/security.csv` → pass; Read `.../config/SYSTEM` → ask; `lsass.dmp` → ask.

## Decisions and open questions
- Decided (user, 2026-10-29): collection scripts (`tools/dc_collect.ps1`, `tools/ir_collect.ps1`) are approved as a **separate task**. They are not drafted here.
- Pending (user): scope. The draft stays DC-only for now (no member server / workstation checklist).
- Open: DC01 counted "Security Group Management = Success" as Uyumsuz (C31, expected S&F). This draft's AD46 expects Success (Failure optional), which is how the baselines are usually cited. Re-running DC01 with the new list would move it to Uyumlu. Accept AD46 as drafted?
- Open: re-run the DC01 set with the new checklist as an acceptance test after activation?

## Activation steps (user only)
1. Review `SKILL.md`, `windows-dc.md` and the risks above.
2. Copy `windows-dc.md` to `.claude/skills/config-audit/windows-dc.md` and replace `.claude/skills/config-audit/SKILL.md` (the Gate asks for writes under `.claude/`; expected).
3. Replace the `config-audit` entry in `governance/skills_registry.json` with `registry_entry.json`.
4. Run `python tests/test_governance.py`.
5. Restart the session so the updated skill loads; acceptance test on `samples/dc01-senaryo/`.
