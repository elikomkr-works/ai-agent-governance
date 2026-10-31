# AI Agent Governance System

**A governance layer that decides what an AI agent is allowed to do, then proves what it actually did.**

Agents are good at producing work and bad at proving it. Hand one a customer's server logs and it will write a confident report — with a count it never ran, a finding it inferred from a blog post, and no record of which files it touched. That is the blocker for deploying agents into any regulated environment: not capability, accountability.

This system puts five enforced checkpoints between a task and its output, and runs a real service behind them.

```
Task → Skill Router → Policy Gate → Executor → Validator → Reviewer → deliver or fix
```

Pilot domain: **defensive cybersecurity**. Three services are packaged end to end — configuration audit, log analysis, phishing triage — of which two are listed and selling. Every report in `reports/` and every customer document in `deliverables/` was produced by this pipeline, not written by hand.

---

## The part that matters: enforced vs. instructed

Most agent "guardrails" are prompt text. An agent that ignores them produces the same output with no signal that anything was skipped. Here, three of the five checkpoints are code that runs outside the model's control:

| Checkpoint | Where | Can the agent bypass it? |
|---|---|---|
| **Skill Router** | Lead agent + two registries | No — an unregistered skill or agent escalates to the user |
| **Policy Gate** | `.claude/hooks/policy_gate.py`, PreToolUse hook | **No.** Inspects every command and file path before execution, denies or escalates |
| **Executor** | 9 specialist agents, each with an explicit tool list | **No.** Least privilege at the platform level — the phishing analyst holds no network tool, so it cannot visit a malicious URL even if the email tells it to |
| **Validator** | `.claude/hooks/validator.py`, PostToolUse + Stop hooks | **No.** Structural check on every written report; a malformed file is rejected |
| **Reviewer** | Independent read-only agent | Partly — it re-derives every number from source rather than trusting the author |
| **Audit log** | `governance/audit.jsonl`, hash-chained | **No.** Agents cannot write to it; CI verifies the chain and append-only rule on every push |

The design rule: anything an agent could benefit from skipping is enforced in code, not asked for in a prompt.

### Three concrete consequences

**Prompt injection has nowhere to land.** Internet content and host evidence are treated as data, not instructions. External knowledge cannot enter the system's persistent memory directly — it lands in `knowledge/quarantine/` with its sources recorded, and only the user promotes it with `tools/approve.py`. The approval script prints the record's own evidence first (reviewer verdict, distinct source count, every unverified claim in full) so the approver signs on evidence, not on a filename.

**"I checked" is not evidence.** Every factual finding carries a label — `[OLGU]` (fact), `[ÖNERİ]` (recommendation), `[DOĞRULANMAMIŞ]` (unverified) — and the fact labels must map to command output or a quoted file line in the report's evidence section. The incident-response report carries a mandatory six-row checklist where exactly one result per row is required, and a single `KANIT YOK` (no evidence) row forbids an overall accept verdict. The Validator counts the rows.

**Unapproved work cannot reach a customer.** A customer-facing document may only be derived from a report whose reviewer verdict is `ONAY` (approved). The Validator opens the source report named in the deliverable's frontmatter and rejects the deliverable if that report is missing, fails validation, or lacks approval. The deliverable adds nothing — no new number, no dropped finding; unverified items are carried over as plainly worded limitations.

---

## Numbers

| | |
|---|---|
| Test suite | **511 assertions across 17 areas**, all passing — Policy Gate, Validator, audit-chain integrity, agent-fleet drift, customer intake, deliverable language rules |
| CI | GitHub Actions on every push: tests, hook launcher on Linux, audit-chain verification against git history |
| Python | ~4,100 lines (hooks, 8 operator tools, test suite) |
| Agents | 9 specialists + lead orchestrator |
| Skills | 6 |
| Commits | 78 |
| Outputs produced through the pipeline | 16 internal reports, 6 customer deliverables (Markdown + PDF), 9 approved knowledge records |

---

## Deployment: one system, many customers

The system is built to be *deployed into* a customer's environment rather than run as a service on their data.

`python3 tools/new_customer.py <customer> <folder outside this repo>` creates a private repository containing the system files only — by allow-list — with empty data folders, CI without public publishing, and an operator guide. Customer data never enters this public repo. `--guncelle` updates the system in place while preserving that customer's data, scope and guide.

Scope is data, not code. Network actions are limited to targets in `governance/policy.json` → `scope.allowed_targets`; agents cannot widen it. Every folder path in the system resolves through `governance/paths.json`, so hooks, tools, tests and the dashboard relocate together.

Adding a capability is a registry entry, not a code change:

- **A new service** → one block in `governance/services.json` plus a test case. The sales catalogue, the intake checklist and the customer-facing gig text all derive from that one table.
- **A new deliverable language** → one block in `governance/deliverable_languages.json` plus a template. No hook code changes.
- **A new skill or agent** → `tools/activate_proposal.py` installs the draft, writes both registry entries and, for a shell-holding agent, its command allow-list. The tool list is always read from the definition file, so a registry entry cannot claim a privilege the agent does not hold. Fleet-drift tests fail on any mismatch.

Agents cannot run any of these three tools — the Policy Gate denies them. Privilege changes are the operator's.

---

## Customer intake: refusing to start

`governance/services.json` marks required inputs as blockers. Work does not begin until every blocker is in hand — the lead agent asks the customer and does not guess. Package file limits are hard: work beyond them is a quoted upgrade. A list of things never requested or promised in any package — server access, secrets, active scanning, offensive testing — goes into the customer message verbatim.

```
python3 tools/intake.py                              # service catalogue
python3 tools/intake.py config-audit standard        # intake checklist for one package
python3 tools/intake.py config-audit standard --siparis "Acme"   # open an order folder
```

---

## Multi-agent orchestration under real failure

The platform does not let subagents spawn subagents, so fan-out is planned on paper and executed by the lead agent in waves: a **scout wave** writes a manifest with one line per unit of work, an **executor wave** runs one subagent per line in parallel, a **review wave** runs one reviewer per output.

The rules that keep a wide wave from collapsing came out of watching it collapse. Three subagents died on the 600-second stream watchdog in one night, mid-task, having delivered nothing. The protocol that resulted:

- A subagent either verifies or writes, never both in one task.
- Every subagent writes its work-board note *before* starting, so a run that dies leaves recoverable state.
- Output is one file path, so a retry overwrites and never duplicates.
- A stalled task is cut smaller, not re-dispatched whole. After two stalls the lead agent writes it and re-derives every number by two independent methods.
- A stall is an infrastructure event, not a verdict — it does not consume one of the two review rounds.

---

## Defense in depth

1. **Policy Gate** — inspects command text and file paths. On its own, bypassable by a sufficiently creative command, which is why it is not the only layer.
2. **OS sandbox** — restricts Bash at the operating-system level (writes confined to project and temp, network to allowed domains). Active in cloud sessions; unavailable on native Windows, and the gate knows the difference. In a cloud session with no human approver present, the gate converts every *ask* into a *deny*.
3. **Audit log** — hash-chained with session and agent fields. The live log is untracked; published slices under `governance/audit_archive/` cannot be deleted or altered, and slices from one source join into a single chain. Denials issued by the permission system *before* reaching the hook are recovered from the session transcript and appended, so the log records refusals the hook never saw.

`python3 tools/verify_audit.py` checks the chain, the append-only rule, and that every approved file has a matching approval record. CI runs it against git history on every push.

`python3 tools/build_site.py` builds a read-only dashboard of the audit records, reports, knowledge records and customer deliverables — each deliverable shown with its source report's verdict and whether its PDF exists. Published to GitHub Pages from `main`.

---

## Running it

```bash
python3 tests/test_governance.py      # 511 assertions (use `python` on Windows)
python3 tools/verify_audit.py         # audit-chain integrity
python3 tools/build_site.py           # dashboard → site/index.html
python3 tools/intake.py               # service catalogue
```

Requires Python 3.12 and Claude Code. The hooks are wired in `.claude/settings.json`; the system contract lives in `CLAUDE.md`.

---

## Language convention

System files — this file, agent and skill definitions, commit messages — are English. The internal record (reports, dashboard, operator guide) is Turkish. Customer documents are written in the customer's language and live in `deliverables/`.

A set of label strings stays Turkish deliberately, because the Validator and the test suite match them exactly: `[OLGU]`, `[ÖNERİ]`, `[DOĞRULANMAMIŞ]`, the report section headings, and the verdict vocabulary. Machine-checked strings are frozen; translating them would be a silent behaviour change. The customer never sees them — the PDF renderer drops the machine fields and replaces labels with badges from the language table.

---

## Honest limitations

- **The Policy Gate reads command text.** Layer 1 alone is defeatable; it is deliberately paired with an OS sandbox and an append-only log rather than trusted on its own.
- **The sandbox does not cover native Windows.** Commands run unsandboxed there. The gate detects the environment and tightens its own behaviour in response, but the OS layer is genuinely absent.
- **The reviewer is an agent.** It is read-only, independent, and recounts from source, which catches arithmetic and unsupported claims. It is not a substitute for a human on a high-stakes finding — and after two failed rounds the system presents the result labelled *not verified* rather than quietly passing it.
- **Scope is narrow by design.** Defensive analysis of files the customer exports. No server access, no active scanning, no offensive tooling — in any package, at any price.
