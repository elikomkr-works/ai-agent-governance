# phishing-triage / phishing-analyst — draft notes

**Status:** DRAFT (2026-10-31, skill-smith). Not active. **Activation requires user approval.**
**Trigger:** SKILL GAP confirmed by `skill-scout` — `work/2026-10-31_yeni-skiller/skill-scout.md`,
section "Aday 1 — phishing-triage". Plan: `work/2026-10-31_yeni-skiller/plan.md`, subtask 2.

## Files and target locations
| Draft | Goes to on activation |
|---|---|
| `proposals/phishing-triage/SKILL.md` | new: `.claude/skills/phishing-triage/SKILL.md` |
| `proposals/phishing-triage/agent.md` | new: `.claude/agents/phishing-analyst.md` |
| `proposals/phishing-triage/registry_entry.json` → `skill` | new entry in `governance/skills_registry.json` → `skills[]` |
| `proposals/phishing-triage/registry_entry.json` → `agent` | new entry in `governance/agents_registry.json` → `agents[]` |
| `proposals/phishing-triage/NOTLAR.md` | nothing; notes stay in the draft folder |

`tools/activate_proposal.py` does all four in one step. There is **no `agent_shell` key**: v1 has no Bash,
and the tool rejects a shell-less agent that carries `shell` or `agent_shell`
(`activate_proposal.py:200-201`). No `policy.json` change is needed at all.

Note on the note file name: the tool accepts either `NOTES.md` or `NOTLAR.md` (`NOTE_FILES`) and copies
neither into the skill folder. The task asked for `NOTLAR.md`, so that is the name used here. Every other
`*.md` in the draft folder **is** copied into the skill folder, so this draft deliberately contains no
extra page.

## What the draft decides, and why

### Tool list: `Read, Grep, Glob, Write, Skill` — exactly `deliverable-writer`'s profile
The one serious danger in this skill is reaching the attacker's infrastructure: fetching the URL or running
the attachment. The scout's judgement is adopted unchanged: the safe control is **not holding the tool**.
- No `WebFetch` / `WebSearch`. This matters more than it looks: `WebFetch` does not pass through the Policy
  Gate's command-text inspection at all, so `scope.allowed_targets` would not stop it. Withholding the tool
  is the only enforced control.
- No `Bash`. v1 needs a shell for exactly one thing — an attachment SHA-256 — and that is handled by asking
  the customer for the hash or declaring it out of scope. Zero privilege increase, zero `policy.json` edit.
- The registry `agent` entry carries no `tools`: the activation tool reads the list from `agent.md`
  frontmatter, so the registry cannot claim a privilege the definition does not grant. The frontmatter line
  is `tools: Read, Grep, Glob, Write, Skill`.
- `Write` + non-empty `writes` (`@reports`, `@work`) and `Skill` + non-empty `skills`
  (`phishing-triage`) satisfy the activation tool's consistency checks. No `Agent`/`Task`.

### Checklist IDs `P1`-`P6`, six mandatory items
The scout's six items, in its order: P1 Received chain / P2 SPF / P3 DKIM / P4 DMARC / P5
From-Reply-To-Return-Path plus display-name mismatch / P6 URL and attachment inventory. Fixed IDs so the
Reviewer can recount, exactly like `config-audit`'s `AD01`-`AD72` and `incident-response`'s `K1`-`K6`.
Body and pretext signals (urgency, bank-detail change, credential request) are a **step 5 extra check that
does not count**, the same construction `incident-response` uses, so the total stays deterministic at 6.

### Result vocabulary: reused, not invented
Per-item results are the existing machine-checked persistence words: **`İZ VAR` / `İZ YOK` / `KANIT YOK`**,
with `İZ VAR` + `İZ YOK` + `KANIT YOK` = 6. Nothing new was coined. The mapping is honest for this artefact:
`İZ VAR` = the indicator is literally in the file, `İZ YOK` = checked and absent, `KANIT YOK` = the needed
header is missing or the export is truncated. `CLAUDE.md` lists these three strings as persistence results;
if the user prefers them reserved for host persistence, the alternative is a **new** vocabulary
(e.g. `GÖSTERGE VAR` / `GÖSTERGE YOK` / `KANIT YOK`), which would mean adding a label to the
machine-checked list in `CLAUDE.md` and to the tests. That is a user decision — see Open questions. The
draft chose reuse because adding a label is a governance change and reuse is not.

### Validator: no hook change needed
Checked against `.claude/hooks/validator.py`:
- `check_ir_report` is selected by the file-name pattern `_ir_` (`IR_REPORT = re.compile(r"_ir_[^/]*\.md$")`,
  line 37). A report named `YYYY-MM-DD_phish_<kisa-ad>.md` therefore only goes through the generic
  `check_report`: the five mandatory sections plus at least one tag. The P-table total is **not**
  machine-enforced in v1 — it is enforced by the skill text, the agent definition and the Reviewer's recount.
- Because `check_ir_report` does not run, the K-table rules (last-row-wins, the `KANIT YOK` substring rule)
  do not apply to a `_phish_` report. The skill still asks for exactly one P-row table with one result per
  row, so a future validator case can be added without rewriting any report.
- No machine-checked Turkish label is changed or added.

### Report path and shape
`@reports/YYYY-MM-DD_phish_<kisa-ad>.md`, Turkish, `governance/templates/report.md`, with `[OLGU]` /
`[ÖNERİ]` / `[DOĞRULANMAMIŞ]` and the sections `## Kapsam`, `## Bulgular`, `## Kanıt`,
`## Doğrulama Durumu`, `## Reviewer Kararı`. No path is hard-coded in the registry: `output` is `@reports`
and `writes` is `["@reports", "@work"]`.

### Counting without a shell
Stated in step 10 and repeated in the agent definition: every number comes from the Grep tool's count mode
or from an explicit item-by-item enumeration in `## Kanıt`, with the pattern shown so the Reviewer reaches
the same number. Three totals must agree: P-table = 6, URL count = listed URLs, attachment count = listed
attachments.

### Defanging and quoting
`## Bulgular` carries URLs, domains and IPs defanged (`hxxp://`, `evil[.]example`); `## Kanıt` carries them
verbatim inside backticks. Copied from `incident-response` step 8 unchanged.

### Data, not instructions
Stated twice on purpose — skill step 2 and the agent definition's working rules — because here the input
**is** the attacker's text, not a log line about it. A request in the body addressed to an automated reader
is never obeyed; its presence is recorded as `[OLGU]` with the line number and quoted verbatim in `## Kanıt`.

## Dry run against `samples/ornek-phishing.eml` (not modified)
The checklist was walked against the existing synthetic sample; all six items resolve from what is literally
in the file, which is what makes it usable as the acceptance test:

| # | Result | Evidence in the sample |
|---|---|---|
| P1 | `İZ VAR` | three hops; the oldest is `from localhost (unknown [196.202.14.7])` into `smtp-out-7.bulkrelay.example`, a bulk relay outside the claimed sender's infrastructure; the top hop timestamps are `+0300` while the origin hop is `+0000`; `Message-ID` domain is `bulkrelay.example`, not the `From` domain; `X-Mailer: PHPMailer 6.1.6`; `X-Originating-IP` differs from the relay IP |
| P2 | `İZ VAR` | `spf=fail (sender IP is 45.133.88.214) smtp.mailfrom=nortvale-invoices.example` plus a `Received-SPF: fail` line; the envelope domain also differs from `header.from` |
| P3 | `İZ VAR` | `dkim=none (message not signed) header.d=none`; no `DKIM-Signature` header exists |
| P4 | `İZ VAR` | `dmarc=fail (p=none sp=none dis=none) header.from=nortvale.example`; the recorded `header.from` (`nortvale.example`) is not even the `From` header's domain (`nortvale-invoices.example`) |
| P5 | `İZ VAR` | `From: "Nortvale Lojistik - Muhasebe" <billing@nortvale-invoices.example>`, `Reply-To: … <nortvale.finance.dept@mailbox-secure.example>` (third domain), `Return-Path: <billing@nortvale-invoices.example>`; display name claims a company whose real domain appears as `nortvale.example` elsewhere in the headers |
| P6 | `İZ VAR` | one URL whose anchor text reads `https://portal.nortvale.example/fatura/4418` while the `href` is `http://nortvale-invoices.example.kyc-dogrulama.example/inv/4418?u=muhasebe@kartaltekstil.example` — nested look-alike domain, plaintext HTTP, recipient address in the query string; one attachment `Fatura_NV-2026-4418.pdf.html`, double extension, declared `text/html`, `Content-Transfer-Encoding: base64` |

Step 5 extras the sample also triggers: same-day 17:00 deadline, threatened shipment stop, a bank-account
change (BEC pattern), `X-Priority: 1 (Highest)`, an RFC 2047 base64 subject beginning `ACIL:`, and an
attachment-opening instruction in the body. The base64 attachment body is **described, never decoded**: the
report may state its name, declared type, encoding and length, and that an interpretation of its content
would be `[DOĞRULANMAMIŞ]` plus an `[ÖNERİ]` for a separate decoding/sandbox task.

Note for whoever runs the acceptance test: the sample lives under `samples/`, not `@evidence`, so neither
`deny_write` nor `evidence_guard` protects it. Acceptable for synthetic data; a real customer email must be
handled read-only and should not be placed under `evidence/` unless the user puts it there.

## Conflicts found, and which way the draft went

1. **Reputation HELP REQUEST target.** `incident-response` step 9 routes reputation and threat-intel
   lookups to `skill-scout`; this task (and the scout note's own closing sentence) names `cve-researcher`.
   **The draft writes `cve-researcher`.** Reason: `cve-researcher` is the only registered agent that
   actually holds `WebSearch`/`WebFetch` and whose output is `@quarantine` under user approval, so the line
   names the agent that can do the work, and the Lead Agent routes it either way. The *form* of the line is
   copied from step 9 character for character:
   `HELP REQUEST → cve-researcher: URL/domain reputation lookup for <defanged-domain> (needs network access; separate task like cve-research, result under knowledge/quarantine/) | input: <report path>`
   This is a divergence from the house text in `incident-response`. If the user prefers one convention,
   the cheapest fix is to make `incident-response` step 9 name `cve-researcher` too; nothing in this draft
   needs to change.
2. **Risk level.** The scout called the policy picture "free (no network, no shell)", which argues for
   `risk: "low"` like `log-analysis` and `config-audit`. The draft sets **`risk: "medium"`** with a
   `risk_reason`, matching `incident-response`: the input is live malicious content (a working phishing URL,
   a credential-harvesting attachment) and the prompt-injection surface is the input itself. The safer label
   was chosen; `risk_reason` states the compensating controls.
3. **Note file name.** `CLAUDE.md` → Draft structure says `NOTES.md`; the task says `NOTLAR.md`. The
   activation tool accepts both. `NOTLAR.md` used, as asked.

## Risks
| # | Risk | Mitigation in the draft | Extra (user / Policy Gate) |
|---|---|---|---|
| R1 | The URL gets fetched by some indirect route (another tool, a web search of the URL, asking another agent to open it). | No `WebFetch`/`WebSearch`/`Bash` on the agent; the Limits name the indirect routes explicitly, including asking another agent. | None needed. The Lead Agent must not hand a phishing URL to a network-capable agent for "a quick look"; only `cve-researcher` through quarantine plus user approval. |
| R2 | The attachment gets executed, extracted or decoded. | Never executed, never materialised, base64 described not reconstructed; no shell to decode with. | `policy.restricted_syntax` already blocks `>`, so even with a future shell the write-out route stays closed. |
| R3 | Prompt injection from the body — the sharpest case in the pilot, since the input is attacker-authored prose. | Step 2 and the agent's working rules: data, never instructions; a request addressed to an agent is recorded as `[OLGU]`, never obeyed. | The Reviewer should check that no finding was dropped or softened because of text in the email. |
| R4 | A `pass` on SPF/DKIM/DMARC read as "safe" (a compromised legitimate mailbox passes all three). | A report caution says so explicitly; P2-P4 alone never support a "safe" conclusion. | — |
| R5 | A truncated export (screenshot, forwarded copy) produces a confident verdict from missing headers. | `KANIT YOK` for the affected items; Doğrulama Durumu BELİRSİZ; the Input section tells the author to ask for a re-export. | Intake must make the full header export a **blocker** item. |
| R6 | A file name like `credentials.eml` hits `policy.sensitive_patterns` (`credentials`, `secrets?`) → ask_write/ASK, and ASK becomes DENY in a cloud session. | — | Ask the customer for a neutral file name; this belongs in the intake list (Lead Agent's subtask). |
| R7 | A secret inside the message (a password the recipient typed, a token in a URL) gets copied into the report. | Step 11: location and type only, value masked. | — |
| R8 | The P-table total is not machine-enforced for `_phish_` reports in v1. | Skill text, agent definition and Reviewer recount. | Optional: a `check_phish_report` validator case plus a test (see Open questions). |

## Policy Gate rules that may be needed
- **None for v1.** No network, no shell, no new write target, no new label. `policy.json` is untouched.
- v2 only (see below) would need one `agent_shell` line.

## Deliberately left out (v2 candidates)
- **Attachment SHA-256 / file-level hashing.** This is the only reason to give the agent a shell. v2 would
  be `shell: "limited"` in the agent entry plus an `agent_shell` line in `policy.json`, with the list
  **identical to `incident-responder`'s and no wider**:
  `agent_shell["phishing-analyst"] = ["sha256sum", "sha1sum", "md5sum", "wc", "grep", "ls", "stat"]`
  (the scout also mentioned `get-filehash` for Windows; add it only if the user wants PowerShell hashing,
  and keep `awk`, `sed` and `python` out — `awk`'s `system()` and `print > "file"` happen inside awk, where
  the Gate's command-text inspection cannot see them). Note the gap the scout flagged: `evidence_guard`
  only constrains paths under `@evidence`, so for a customer email held elsewhere the `agent_shell` list
  would be the only limit — which is why that line is mandatory in v2, not optional.
- **Reputation and advisory lookups.** Stay with `cve-researcher` → `@quarantine` → user approval. No second
  network path is opened.
- **`.msg` support.** Out of package. A converter is a code-executing dependency on attacker-controlled
  input; the intake item must read "`.eml` or a plain-text header export".
- **Dynamic analysis / sandboxing / malware reverse engineering**, live DNS/SPF/WHOIS verification, mail
  log correlation (`log-analyst`), gateway hardening (`config-auditor`), post-click host review
  (`incident-responder`).
- **Not written here, by instruction:** the `governance/services.json` block, the intake checklist items and
  any `tests/test_governance.py` case. Those are the Lead Agent's subtask 3.

## Open questions (user)
1. **Result vocabulary.** Reuse `İZ VAR` / `İZ YOK` / `KANIT YOK` for an email checklist (the draft's
   choice), or coin a phishing-specific set and add it to the machine-checked list in `CLAUDE.md`?
2. **HELP REQUEST convention.** Keep this draft's `cve-researcher` and change `incident-response` step 9 to
   match, or switch this draft to `skill-scout` for consistency with the existing text? (Conflict 1.)
3. **Risk label.** Is `medium` right for a no-network, no-shell skill whose input is live malicious content,
   or should it be `low` as the scout's policy line suggests? (Conflict 2.)
4. **Validator case.** Add a `_phish_` branch that enforces the P1-P6 table and the total 6, mirroring
   `check_ir_report`? It would make the count machine-checked instead of reviewer-checked. Hook change,
   so a user decision, and out of scope for this draft.
5. **Where does a customer email live?** `samples/` for synthetic input is clear. For real customer email,
   under `evidence/` (gains `deny_write` plus `evidence_guard`, but the user must place it) or in a plain
   input folder in the customer repo? This also decides whether v2's `agent_shell` is the only limit.
6. **Does the Lead Agent ever hand a defanged URL from a phishing report to `cve-researcher`?** The draft
   assumes yes, through `@quarantine` plus user approval. If the user would rather never query a live
   phishing domain even from the network-capable agent, say so and the step 9 `[ÖNERİ]` becomes
   "ask the customer's own gateway vendor" instead.

## Activation steps (user only)
1. Review `SKILL.md`, `agent.md`, the risks and the open questions above.
2. Dry run: `python tools/activate_proposal.py proposals/phishing-triage --deneme` (prints the plan,
   writes nothing).
3. Activate: `python tools/activate_proposal.py proposals/phishing-triage`. It copies the skill to
   `.claude/skills/phishing-triage/SKILL.md`, the agent to `.claude/agents/phishing-analyst.md`, and adds
   both registry entries. No `policy.json` change and no `agent_shell` line (v1 has no Bash).
4. Run the tests: `python tests/test_governance.py` (the fleet drift checks compare the registry `tools`
   with the definition frontmatter).
5. Restart the session so the new skill and agent are loaded.
6. Acceptance test: run `phishing-analyst` on `samples/ornek-phishing.eml`, expect the P-table above
   (6/0/0), then a `reviewer` recount of the table, the URL count and the attachment count. Only after a
   reviewer `ONAY` is the skill sellable (plan.md rule), and only then a customer deliverable.
