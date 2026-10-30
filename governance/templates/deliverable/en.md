---
dil: en
kaynak_rapor: reports/YYYY-MM-DD_<skill>_<short-name>.md
musteri: <customer name, or "portfolio sample">
teslim_tarihi: YYYY-MM-DD
---

# <Title: what was audited, for which host>

**Date:** YYYY-MM-DD · **Prepared by:** <name> · **Input:** <what the customer sent, e.g. "sshd_config, 16 lines">

## Summary
- <The headline number: how many items checked, how many passed, how many failed.>
- <Most urgent finding, in one line, with its severity.>
- <What the customer should do first.>
- Every FACT below points to an exact line of the file you sent, or to a search showing a setting is absent.

**Labels:** `FACT` = read directly from your file · `FIX` = recommended change · `CHECK` = depends on your software version; confirm before applying.

## Scope
- Input: <file / export, size, how many active entries>
- Checklist: <name and item count, if one was used. State the counting rule: passed + failed = total.>
- Out of scope: <what was not done — no scanning, no connection to your systems, no file changed, no service restarted, anything the customer did not provide.>

## Findings

<Table or list. Order by severity: Critical, High, Medium, Low, Info.>

| # | Severity | Setting (line) | FACT | FIX |
|---|---|---|---|---|
| 1 | <Critical/High/Medium/Low> | `<setting>` (<line>) | <What the file says and why it is risky. Expected: <value>.> | `<the change>` |

<If something could not be determined from what the customer sent, say so here in plain words and mark it CHECK — never present it as a finding.>

## <Optional: Hardened snippet / Action plan>
```
<copy-paste block, if the skill produces one>
```
How to apply safely:
- <Replace vs append, include files, order of operations.>
- <What must be in place before applying, so the customer cannot lock themselves out.>
- <Syntax test and restart command.>

## Evidence
Source lines (`<file>:<line>`):
<line> `<exact line>` · <line> `<exact line>`

Absent settings (command → output):
- `<command>` → `<output>`

<Counts, file size, any number quoted in Summary or Findings must be reproducible from this section.>

## Verification
Every FACT is based on an exact file line or a search output above. <State the count consistency, e.g. "1 compliant + 7 non-compliant = 8".> Version-dependent fixes are marked CHECK. An independent second review re-checked all facts, numbers and severity ratings against the source file before delivery.
