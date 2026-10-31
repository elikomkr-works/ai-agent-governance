# vuln-triage / vuln-triage-analyst — draft notes

**Status:** DRAFT (2026-10-31, skill-smith). Not active. **Activation requires user approval.**
**Trigger:** SKILL GAP confirmed by `skill-scout` — `work/2026-10-31_yeni-skiller/skill-scout.md`,
candidates 2 and 3 merged under the heading "Örtüşme: 2 ile 3 tek skill olmalı" (`scan-triage` +
`dependency-audit` → one skill `vuln-triage`, one agent `vuln-triage-analyst`). This is the pilot's fourth
sellable service line; the decision to build it was already taken by the Lead Agent, so this draft does not
re-open the scope question.

## Files and target locations
| Draft | Goes to on activation |
|---|---|
| `proposals/vuln-triage/SKILL.md` | new: `.claude/skills/vuln-triage/SKILL.md` |
| `proposals/vuln-triage/scanner-export.md` | new: `.claude/skills/vuln-triage/scanner-export.md` |
| `proposals/vuln-triage/dependency-manifest.md` | new: `.claude/skills/vuln-triage/dependency-manifest.md` |
| `proposals/vuln-triage/agent.md` | new: `.claude/agents/vuln-triage-analyst.md` |
| `proposals/vuln-triage/registry_entry.json` → `skill` | new entry in `governance/skills_registry.json` → `skills[]` |
| `proposals/vuln-triage/registry_entry.json` → `agent` | new entry in `governance/agents_registry.json` → `agents[]` |
| `proposals/vuln-triage/NOTLAR.md` | nothing; notes stay in the draft folder |

`tools/activate_proposal.py` does all of this in one step. Every `*.md` in the draft folder except the note
file is copied into the skill folder, which is exactly how the two profile pages travel — the same mechanism
that carries `config-audit`'s `windows-dc.md`. There is **no `agent_shell` key**: this agent has no Bash, and
the tool rejects a shell-less agent that carries `shell` or `agent_shell`. `policy.json` is untouched.

Note on the note file name: the tool accepts `NOTES.md` or `NOTLAR.md` and copies neither into the skill
folder. The task asked for `NOTLAR.md`, so that is the name used, matching the `phishing-triage` draft.

## What the draft decides, and why

### One skill, two profile pages — the scout's merge, unchanged
`SKILL.md` holds what the two inputs share (parse → identify the asset → deduplicate → separate version
evidence from guess → exposure → bounded enrichment → stated priority rule → counting rule → report shape),
and each profile page holds what is tool- or ecosystem-specific. The scout's reasoning is adopted as is: the
two jobs are ~80 % the same, and one skill means one skill registry entry, one agent registry entry and one
drift test set instead of two. `services.json` can still sell two separate services pointing at the same
skill and agent (the services tests check existence, not uniqueness) — that is the Lead Agent's subtask, not
this draft's.

### Tool list: `Read, Grep, Glob, Write, Skill` — no Bash, against the scout's recommendation
The scout proposed `shell: "limited"` with the `incident-responder`-style list, so a lockfile entry count
could be reproduced by command. **This draft has no Bash**, per the task's instruction, and the shape is
`phishing-analyst`'s proven shell-less profile. Consequences, stated honestly:
- Every count comes from the Grep tool's count mode or an explicit enumeration, with the pattern written
  into `## Kanıt`. This is weaker than two independent methods: the Reviewer recounts with the same tool.
- The real cost shows up in CSV exports whose fields contain embedded newlines (Nessus `Plugin Output`,
  Qualys `Results`), where a `^` count over-counts rows. `scanner-export.md` → "Finding the row count"
  handles it by requiring a stable row anchor or an explicit enumeration, and by forbidding an approximate
  number. If the user later wants command-reproducible counts, that is the v2 item below.
- The upside is the same as in `phishing-triage`: zero privilege increase, no `policy.json` edit, and the
  forbidden-by-construction list is long and valuable here — `npm`, `pip`, `mvn`, `go`, `osv-scanner`,
  `nmap`, `curl` are not "denied", they are absent.
- No `WebFetch`/`WebSearch`. This matters more than it looks: `WebFetch` does not pass through the Policy
  Gate's command-text inspection at all, so `scope.allowed_targets` would not stop a fetch of a scanner
  target or a typo-squatted package's repository. Withholding the tool is the only enforced control.
- The registry `agent` entry carries no `tools`: the activation tool reads the list from `agent.md`
  frontmatter, so the registry cannot claim a privilege the definition does not grant.
- `Write` + non-empty `writes` (`@reports`, `@work`) and `Skill` + non-empty `skills` (`vuln-triage`)
  satisfy the activation tool's consistency checks. No `Agent`/`Task`.

### Checklist IDs `V1`-`V6`, six mandatory items
Fixed IDs so the Reviewer can recount, exactly like `P1`-`P6` and `K1`-`K6`. The six cover the task's
required ground: V1 export integrity/provenance, V2 asset and component identification, V3 deduplication
and identifier reconciliation, V4 version evidence, V5 exposure/reachability/stated mitigation, V6
exploitation status and fix availability from an approved source. Per-tool and per-ecosystem checks live in
the profile pages as **extras that do not count**, the same construction `incident-response` and
`phishing-triage` use, so the total stays deterministic at 6.

Result vocabulary is reused, not invented: `İZ VAR` / `İZ YOK` / `KANIT YOK`, with the sum = 6, a `KANIT YOK`
row forbidding `KABUL`, exactly one `| V1 |` … `| V6 |` table in `## Kanıt`, one result per row, and the
literal result strings never written inside another row's reasoning text. That is the same mechanical shape
the caller will enforce in the Validator.

**Polarity, stated explicitly because it is the one thing a reader can get wrong:** `İZ VAR` means "the
input literally shows the indicator described in that row", as in `phishing-triage`. For V1-V4 the indicator
is a *defect or a gap* (no scan date, an unidentifiable asset, duplication, an inferred version), so
`İZ VAR` is bad news. For V5 and V6 the indicator is *information that exists* (a finding recorded as
exposed; an approved record stating exploitation or a fix), so `İZ VAR` is informative rather than bad.
Each row's Indicator column spells out its own `İZ VAR`, and V5 and V6 additionally spell out their `İZ YOK`
and (V6) their `KANIT YOK`, so no row depends on the reader inferring the polarity.

### V6 makes a Basic report BELİRSİZ by construction — SETTLED 2026-10-31: option (b)
**The user chose to give Basic one enrichment, at $25.** So V6 can be satisfied in every package and
`KABUL` is reachable at every price point. The bound is 1 / 5 / 15. The reasoning below is kept for the
record; the question it ends with is answered.

Basic sells 0 enrichments, so no approved record exists, so V6 is `KANIT YOK`, so `KABUL` is forbidden and
the verdict is BELİRSİZ. This is stated in `SKILL.md` step 13 rather than hidden. It is the honest outcome:
a Basic triage orders the export's own evidence and cannot assert anything about real-world exploitation.
If the user would rather Basic be able to reach `KABUL`, the two options are (a) let the export's own
`Solution`/severity fields satisfy V6 — rejected here, because that is exactly the vendor claim the service
is sold to filter — or (b) give Basic one enrichment. That is a pricing decision, not a draft decision; see
Open questions.

### Prioritisation: a lexicographic E → C → F key, not a product
The task named "exposure × confirmed-version evidence × fix availability". The draft implements it as an
ordered key (E, then C, then F, each 0-2, highest first) and says why multiplication was not used: any zero
factor would multiply a genuinely internet-facing finding down to the bottom of the plan — a
no-fix-available, banner-versioned, internet-facing RCE would rank last, which is the opposite of useful.
Tie-break is explicit and deterministic: (1) number of distinct affected assets, counted with Grep, higher
first; (2) lowest row/line number in the export. Determinism is the point — two analysts and the Reviewer
must produce the same order from the same file. Each ranked item must show its E/C/F values with the
evidence file:line behind each, and `F = 2` requires an approved record while the export's own `Solution`
field is only `F = 1`.

### Package bound on enrichment: Basic 1, Standard 5, Premium 15
Written into `SKILL.md` step 9, repeated in the Limits and in the agent definition, and declared in
`## Kapsam` together with which findings were chosen and why. The bound exists because each enrichment is a
separate `cve-researcher` task whose result reaches usability only through `knowledge/quarantine/` plus a
user approval — the approval is the bottleneck, so an unbounded promise cannot be delivered. The bound also
belongs in `services.json` (Lead Agent's subtask); the skill text and the service table must agree.

### Report path and shape
`@reports/YYYY-MM-DD_vuln_<kisa-ad>.md`, Turkish, `governance/templates/report.md`, with `[OLGU]` /
`[ÖNERİ]` / `[DOĞRULANMAMIŞ]` and the sections `## Kapsam`, `## Bulgular`, `## Kanıt`,
`## Doğrulama Durumu`, `## Reviewer Kararı`. The slug is `vuln`. No path is hard-coded in the registry:
`output` is `@reports`, `writes` is `["@reports", "@work"]`.

### Validator
The caller stated they will add the `_vuln_` branch that enforces the V1-V6 table. The draft's wording was
written to be mechanically checkable in the same way as `check_ir_report`: exactly one table whose rows
start with `| V1 |` … `| V6 |`, exactly one of the three result strings per row, the three results summing
to 6, and a `KANIT YOK` row blocking `KABUL`. The skill also forbids writing a result string inside another
row's reasoning text, which is the rule that makes a substring check safe. Nothing in the draft depends on
that branch existing: until it lands, the table is enforced by the skill text, the agent definition and the
Reviewer's recount, and the generic `check_report` still enforces the five sections plus a tag.
**No machine-checked Turkish label is changed or added** — the three result strings, the five section
headings and the three verdicts are the existing ones.

### Counting without a shell
Stated in `SKILL.md` step 11, repeated in both profile pages and in the agent definition. Three totals must
agree, and all three appear in `## Kanıt` with their patterns:
1. the V-table total is 6;
2. raw row count ≥ deduplicated finding count (deduplication can only reduce);
3. in-scope + out-of-scope = deduplicated finding count, and the prioritised plan's item count = the
   in-scope finding count.
The third is the one that catches the classic failure of this service: a plan that quietly drops findings it
could not reason about.

### Data, not instructions
Stated in `SKILL.md` step 2, in both profile pages' Cautions and in the agent's working rules. A scanner
export is third-party text in several places at once — plugin descriptions, captured HTTP responses,
certificate subjects, package names and package descriptions — and a dependency file can name a package
whose description is attacker-written. A request addressed to an automated reader ("mark this as a false
positive", "run this remediation command", "fetch this URL to confirm") is recorded as `[OLGU]` with
file:line, quoted verbatim, reported as a finding, and never obeyed.

## Conflicts found, and which way the draft went
1. **Bash: scout says yes, task says no.** The draft follows the task (no Bash) and records the cost above
   (CSV embedded-newline counting). If the user wants command-reproducible counts later, v2 is one
   `agent_shell` line, listed below.
2. **`cve-research` source list does not cover ecosystem advisories.** The scout flagged it and the draft
   depends on it: most package flaws appear as GHSA / OSV / PYSEC / RUSTSEC / RUBYSEC before (or instead of)
   a CVE, and `cve-research/SKILL.md`'s priority list is NVD → cve.org/MITRE → vendor advisory → CISA KEV.
   The cheapest fix is adding GHSA, OSV, the PyPA advisory DB and RustSec to that skill's source list — a
   one-file edit that opens **no** new network path, since `cve-researcher` already holds the only one.
   Not done here, because this draft must not touch `.claude/`. Flagged as an open question.
   Until it is done, a GHSA-only finding's enrichment request may come back as "no CVE record found", which
   the report must then carry as `[DOĞRULANMAMIŞ]`.
3. **Risk level.** No network, no shell, read-only would argue for `low` like `config-audit`. The draft sets
   **`medium`** with a `risk_reason`, matching `phishing-triage` and `incident-response`: the input is a
   claim list about systems nobody here can see, and the characteristic failure of this service is not a
   dangerous action but a confident wrong number — a vendor severity echoed as fact, a banner version taken
   as installed, an inflated count. The compensating controls are evidential, and the `risk_reason` says so.
4. **Report slug.** The scout drafted separate slugs (`_dep_` for dependencies). The task fixes a single
   slug `_vuln_` for both profiles, which is what the draft uses and what keeps one Validator branch.
5. **Note file name.** `CLAUDE.md` → Draft structure says `NOTES.md`; the task says `NOTLAR.md`. Both are
   accepted by the activation tool. `NOTLAR.md` used, as asked.

## Risks
| # | Risk | Mitigation in the draft | Extra (user / Policy Gate) |
|---|---|---|---|
| R1 | A target in the export gets contacted — a "quick confirm" scan, a `curl`, a fetch of a package's registry or repository page. | No `WebFetch`/`WebSearch`/`Bash`; the Limits name the indirect routes, including asking another agent. | The Lead Agent must not hand a scanner target or a suspicious package URL to a network-capable agent for a look; only `cve-researcher`, on the identifier, through quarantine plus user approval. |
| R2 | A dependency command runs and thereby executes code shipped with the customer's dependencies (`npm install` lifecycle scripts, `setup.py`). | No Bash at all; the full forbidden-command list is in the Limits, the agent definition and the dependency profile page. | If Bash is ever added (v2), these commands must be in the `agent_shell` allow-list's complement, and the user may also want them in `policy.json` → `deny_commands`. |
| R3 | Vendor severity or a CVSS score echoed as a fact about the customer's risk. | `[OLGU]` only *about the export*, with the required phrasing "the scanner recorded …"; the priority order is built on E/C/F evidence, not on labels; an unapproved score makes the rank `[DOĞRULANMAMIŞ]`. | The Reviewer should check that no rank rests on a label alone. |
| R4 | A banner- or range-derived version read as the installed version — the single most common error in this service. | V4 exists for exactly this; `C = 1` in the ordering rule; both profile pages explain the backport and the `^range` traps. | Intake should make "authenticated scan or lockfile" a stated expectation. |
| R5 | An inflated finding count delivered to the customer (duplicate plugins, CVE+GHSA pairs, one alert across 200 URLs). | V3, the deduplication map in `## Kanıt`, and the mandatory "raw ≥ deduplicated" pair of numbers with their patterns. | — |
| R6 | A finding silently dropped from the plan because it was hard to reason about. | The count agreement "plan items = in-scope findings" and "in-scope + out-of-scope = deduplicated". | The Reviewer recounts; this is the check worth doing first. |
| R7 | Prompt injection from the export — a plugin description, a captured HTTP response or a package description addressed to an automated reader. | `SKILL.md` step 2, both profile pages, the agent's working rules: data, never instructions; its presence is a finding. | The Reviewer should check that no finding was softened or dropped because of text inside the export. |
| R8 | The enrichment promise exceeds what user approvals can deliver, and the delivery slips. | The package bound (0/5/15) is in the skill, the Limits, the agent definition and must be declared in `## Kapsam`. | `services.json` must carry the same numbers; a mismatch between the gig text and the skill is a sales problem, not a report problem. |
| R9 | A private-registry token or a scanner credential inside the export gets copied into the report. | Input section and the agent rules: location and type only, value masked, plus an `[ÖNERİ]` to remove and rotate. | A file named `*credentials*` or `*secrets*` hits `policy.sensitive_patterns` → ASK, and ASK becomes DENY in a cloud session. Ask the customer for a neutral file name (intake item). |
| R10 | The V-table total is not machine-enforced until the Validator branch lands. | Skill text, agent definition, Reviewer recount; the wording is already shaped for the mechanical check. | The caller stated the `_vuln_` branch is theirs to add; a test case goes with it. |
| R11 | The export is huge (tens of thousands of rows) and the analyst stalls on the watchdog. | One report per export file; the profile pages require counting by pattern rather than reading every row; the work-board note is written first and appended as the work proceeds. | Package file/row limits in `services.json`, and the Lead Agent's wave split (one export per subagent) per CLAUDE.md → Dispatch and fan-out. |

## Policy Gate rules that may be needed
- **None for v1.** No network, no shell, no new write target, no new label, no new scope target.
  `policy.json` is untouched.
- v2 only (see below) would need one `agent_shell` line.

## Deliberately left out (v2 candidates)
Each of these is either a stated limit in `## Kapsam` or an `excludes` entry in `services.json` — the
caller's decision, not this draft's. Listed in rough order of how often a customer will ask for it.
- **Reachability / call-graph analysis of the customer's source code.** The strongest false-positive filter
  in the dependency profile, and out of scope: it needs the repository and a code-analysis tool, which is a
  different service with a different privilege profile. v1 uses only reachability data the input itself
  carries, and otherwise E = 1 (unknown). Candidate for `excludes`.
- **Command-reproducible counts (Bash).** v2 would be `shell: "limited"` plus an `agent_shell` line with the
  `incident-responder` list and **no wider**:
  `agent_shell["vuln-triage-analyst"] = ["wc", "grep", "sort", "uniq", "cut", "ls", "stat", "sha256sum"]`
  — enough to recount rows and hash the export for traceability. `awk`, `sed` and `python` stay out
  (`awk`'s `system()` and `print > "file"` happen inside awk, where the Gate's command-text inspection
  cannot see them), and every package manager stays out for R2's reason.
- **Binary and office-format exports** (`.nessus` database file, PDF, XLSX, zipped archive). A converter is a
  code-executing dependency on a customer-supplied file. Intake must read "CSV, XML, JSON or plain text".
  Candidate for `excludes`.
- **SBOM generation** (`syft`, CycloneDX, SPDX production). Needs a package-manager-class tool. Reading an
  SBOM the customer supplies as JSON would be a small profile-page addition instead; not in v1.
- **Container image and OS package layer analysis** beyond what the export states (image layers, base-image
  CVEs, distro patch levels). Candidate for `excludes`.
- **Asset discovery.** The customer supplies the asset inventory; finding out what exists is a scanning
  activity and forbidden in the pilot. Candidate for `excludes`.
- **Patch testing, upgrade PRs, version bumps, `npm audit fix`.** The output is a document; the customer
  applies changes. Candidate for `excludes`.
- **Compliance mapping** (PCI DSS / ISO 27001 / NIS2 control numbers against the findings). Frequently asked
  for in this market and cheap to add later as a profile page, but it needs an approved control-text source.
- **Re-scanning or verification after remediation** ("confirm the fix worked"). Scanning, forbidden.
  The honest offer is a re-triage of the customer's new export, which is a second order.
- **Trend / delta reporting** between two exports of the same estate (what is new, what was fixed, what is
  still open). No new privilege needed, genuinely sellable as a recurring service, and the only reason it is
  out of v1 is that it doubles the counting rules. Best v2 candidate on this list.
- **Risk scoring or a quantified business-impact number** (an EPSS-style probability, a monetary figure). It
  would rest on data no approved record provides and would read as precision we cannot defend.
- **Not written here, by instruction:** the `governance/services.json` block, the intake checklist items, the
  Validator `_vuln_` branch and any `tests/test_governance.py` case. Those belong to the Lead Agent and the
  user.

## Open questions (user)
1. ~~**Should Basic be able to reach `KABUL`?**~~ ANSWERED: Basic gets one enrichment at $25. As drafted it cannot: 0 enrichments → V6 `KANIT YOK` →
   BELİRSİZ by construction. Accept that (and say so in the gig text), or give Basic one enrichment?
2. **`cve-research` source list.** Add GHSA, OSV, the PyPA advisory DB and RustSec to
   `.claude/skills/cve-research/SKILL.md`? Without them, package findings that have no CVE cannot be
   enriched at all. One-file edit, no new network path. (Conflict 2.)
3. **Bash or not.** Keep the shell-less profile (this draft), or add the `agent_shell` list above so row
   counts are command-reproducible for large CSV exports? (Conflict 1, R11.)
4. **One service or two in `services.json`?** One skill can back two gigs ("scanner report triage" and
   "dependency / SCA triage") with different limits and price points, or a single "vulnerability triage"
   service with a profile named at intake.
5. **Package limits.** The enrichment bound is fixed (0/5/15). The **file and row** limits are not: how many
   export files, and how many raw rows, does each package cover before it becomes an upgrade?
6. **Where does a customer export live?** Under `evidence/` (gains `deny_write`, but the user must place it)
   or a plain input folder in the customer repo? An export is not host evidence in the forensic sense, but it
   is customer data.
7. **Does a sample export belong in `samples/`?** There is none today (`samples/` holds `auth.log`,
   `sshd_config`, `ornek-phishing.eml`), so the acceptance test below needs one synthetic scanner CSV and
   one synthetic lockfile + `npm audit --json`. Should skill-smith draft them as a follow-up task?

## Activation steps (user only)
1. Review `SKILL.md`, both profile pages, `agent.md`, the risks and the open questions above.
2. Dry run: `python tools/activate_proposal.py proposals/vuln-triage --deneme` (prints the plan, writes
   nothing). Check that both profile pages appear in the plan as extra skill pages.
3. Activate: `python tools/activate_proposal.py proposals/vuln-triage`. It copies the skill and its two
   pages to `.claude/skills/vuln-triage/`, the agent to `.claude/agents/vuln-triage-analyst.md`, and adds
   both registry entries. No `policy.json` change and no `agent_shell` line (v1 has no Bash).
4. Run the tests: `python tests/test_governance.py` (the fleet drift checks compare the registry `tools`
   with the definition frontmatter).
5. Restart the session so the new skill and agent are loaded.
6. Acceptance test, once sample inputs exist (open question 7): run `vuln-triage-analyst` on a synthetic
   scanner CSV and on a synthetic lockfile + `npm audit --json` pair, then a `reviewer` recount of the
   V-table, the raw and deduplicated counts and the plan item count. Only after a reviewer `ONAY` is the
   skill sellable, and only then a customer deliverable.
