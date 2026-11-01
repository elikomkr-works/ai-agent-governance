# Governance on the Claude Agent SDK

The governance layer in this repository was written as Claude Code hooks. A fair
question about any such system is how much of it is the harness and how much of it
is the design: if the policy only exists because Claude Code calls a hook, it is a
configuration, not an architecture.

This folder answers that question by running the same two enforcement modules from
a standalone Python application built on `claude-agent-sdk`.

```
.claude/hooks/policy_gate.py   ──┬──  Claude Code: PreToolUse / PostToolUse / Stop hook processes
.claude/hooks/validator.py     ──┘
                                 └──  sdk/governance_runtime.py: in-process SDK callbacks
```

Nothing in the policy is re-implemented here. The hook modules expose pure
functions over the hook-event dict, and the decision shape Claude Code expects is
the shape the Agent SDK expects, so `governance_runtime.py` is an adapter:

| Enforcement | Function called | Output |
|---|---|---|
| Policy Gate | `policy_gate.evaluate` + `apply_cloud_rules` | `permissionDecision: deny / ask / allow` |
| Validator | `validator.handle` | `decision: block` with the structural errors |
| Audit log | `govlib.audit` | one hash-chained record per decision |

The test suite asserts this rather than trusting it: for every case in
`run_agent.py`'s table it compares the decision made in-process by the SDK layer
with the decision made by the hook **process** on the same input. A case that
diverges means a second copy of the policy has appeared in this layer.

## Run it

```bash
python sdk/run_agent.py --selftest
```

No model call, no network, no API key, and `claude-agent-sdk` does not need to be
installed. It puts ten synthetic tool calls through the gate — in-scope and
out-of-scope scans, an offensive tool, a write into the protected evidence folder,
an unregistered skill and an unregistered agent — prints each decision beside the
expected one, shows the Validator refusing to accept a report that does not exist,
and lists what the agent registry grants three agents. Audit records from a
selftest go to a temporary log; `--audit-live` writes to the project's.

For a real governed run:

```bash
pip install -r sdk/requirements.txt
python sdk/run_agent.py --agent log-analyst --task "Analyse samples/auth.log"
```

The agent's tool list comes from `governance/agents_registry.json` — the same file
the drift tests check against the agent definitions — so this layer cannot grant a
privilege the definition does not. An agent name that is not in the registry is
refused here, because admitting one is a user decision.

That run was executed on 2026-11-01: 8 turns, $0.3594, and a report the in-process
Validator accepted. It appears in the audit log under its own session id, with a
Gate decision for every tool call and the Validator verdict after the write — the
run's agent name is stamped on each record, because the SDK's hook input does not
carry one the way a Claude Code subagent call does.

## Two things worth knowing

**`setting_sources=[]`.** With filesystem settings loaded, the CLI underneath the
SDK would also run the command hooks in `.claude/settings.json`, so every tool call
would pass the gate twice and write two audit records. The registered callbacks are
the single path.

**The sandbox is not in this layer.** Defence in depth here is the gate, the
validator and the audit log. OS-level restriction of Bash remains the SDK's own
`sandbox` option (`ClaudeAgentOptions`), and on native Windows it does not apply —
the same limitation the Claude Code setup has.

## Files

| File | What it is |
|---|---|
| `governance_runtime.py` | the adapter: decision functions, async hook callbacks, `build_options`, `run_task` |
| `run_agent.py` | CLI: `--selftest`, or `--agent` + `--task` for a governed run |
| `requirements.txt` | `claude-agent-sdk` |

Tests: `python tests/test_governance.py` → the "Agent SDK katmanı" section.
