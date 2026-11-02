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

## From a browser

`sdk/web.py` puts the same governed run behind an upload form, because a customer
file arriving as an email attachment and a staff member pasting a path into a
terminal are the same job with different friction.

```bash
python sdk/web.py                  # http://127.0.0.1:8000
python sdk/web.py --host 0.0.0.0   # refused unless GOV_WEB_TOKEN is set
```

The page holds no policy of its own. It writes the upload under `@work`, hands one
bounded task to the agent that `governance/services.json` names for the chosen
service, and calls `run_task` — so the Gate still rules on every tool call, the
Validator still rules on the report, and both decisions still reach the audit log
under the agent's name. The service list, the agent and the report slug are read
from the catalogue, so adding a service stays a data change here too.

It plays the Lead Agent's mechanical part only: it names the single input and the
single output path, writes the work-board note before the run so a crash leaves
recoverable state, and tells the agent in the prompt that the uploaded content is
data rather than instructions. It stops at the internal report. It never writes
`## Reviewer Kararı`, never derives a deliverable and never renders a PDF, because
those need an independent review and the user's approval, and an approver cannot
be a web form.

Three things the deployment depends on:

| Concern | How it is handled |
|---|---|
| Who may use it | None by default, hence the loopback bind. `GOV_WEB_TOKEN` requires `?token=...`; binding another interface without it is refused, not warned about. |
| Whose API key pays | `ANTHROPIC_API_KEY` from the environment, or one pasted into the form, used for that run's subprocess only — never written to disk, never logged. With neither, the machine's signed-in Claude Code session is used. |
| Untrusted input | The filename is reduced to a safe basename (no traversal, no dotfile, 80 chars), uploads over 10 MB are refused, and the file is read as data by an agent whose tool list comes from the registry. |

Tests: the "Web katmanı" section of `tests/test_governance.py` drives the whole
HTTP path with the model call stubbed out, so it is free to run and proves the
routing, the limits and the token guard without spending anything.

## On a server

`sdk/Dockerfile` packages the page and the whole governance layer. The test suite
travels with it on purpose: it needs no API key and no model call, so a built image
can be asked whether the enforcement it carries still holds.

```bash
docker build -f sdk/Dockerfile -t gov-web .
docker run --rm gov-web python tests/test_governance.py   # 602 pass, 3 skip
docker run --rm gov-web python sdk/run_agent.py --selftest
```

The three skips are the two checks that query git — the image has no `.git`, on
purpose — and the customer-repo section, whose tool derives its allow-list from
`git ls-files` and cannot run without a repository.

The run is **not root** (uid 10001) and the code is **not writable** by it. The
second half matters more than the first: `COPY` preserves the source mode, and a
build context on a Windows drive arrives world-writable, so without
`chmod -R a-w /app` the non-root user could still edit `policy_gate.py`,
`policy.json` and the registries. Probed from inside the container: the gate code,
the policy, the registries, the settings and the skills are refused; `reports/`,
`work/` and the audit log are writable, which they must be.

Two honest limits. The audit log has to be writable by the run that appends to it,
so the protection there is not the file mode but the hash chain and
`tools/verify_audit.py`. And the sandbox being *configured* is proven by test,
while the sandbox *engaging* inside the container is not — that needs a run with a
Bash tool call, which needs a model call.

Mounts: the container writes as uid 10001, so hand the folders over on the host
once (`sudo chown -R 10001:10001 reports work governance/audit.jsonl`), and mount
the audit log as a file that already exists — Docker creates a directory for a
missing mount source, and a directory where the chained log belongs breaks the
chain quietly.

## Two things worth knowing

**`setting_sources=[]`.** With filesystem settings loaded, the CLI underneath the
SDK would also run the command hooks in `.claude/settings.json`, so every tool call
would pass the gate twice and write two audit records. The registered callbacks are
the single path.

**The sandbox is read, not retyped.** `sandbox_settings()` takes the `sandbox`
block of `.claude/settings.json` and hands the SDK the keys its `SandboxSettings`
accepts, so the OS-level restriction of Bash is described in one place even though
`setting_sources=[]` stops the CLI from reading that file itself. A test asserts the
two agree, and names the two keys that have no SDK equivalent, so a rule added to
the settings file later cannot be dropped in silence.

On native Windows it returns `None`: the sandbox does not exist there, and claiming
it would be a false guarantee — the same split the Claude Code setup lives with.
What stands in that case is the gate, the validator and the audit log.

Inside an unprivileged container bubblewrap cannot nest, so a sandboxed run there
needs `GOV_SANDBOX_NESTED=1` (a deliberately weaker sandbox, opt-in) or
`--privileged`. The image carries bubblewrap and socat, which the sandbox needs on
Linux and without which it goes quiet rather than loud.

## Files

| File | What it is |
|---|---|
| `governance_runtime.py` | the adapter: decision functions, async hook callbacks, `build_options`, `run_task` |
| `run_agent.py` | CLI: `--selftest`, or `--agent` + `--task` for a governed run |
| `requirements.txt` | `claude-agent-sdk` |

Tests: `python tests/test_governance.py` → the "Agent SDK katmanı" section.
