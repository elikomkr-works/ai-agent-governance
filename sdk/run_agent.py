"""Run a governed agent from a standalone Python application.

    python sdk/run_agent.py --selftest
    python sdk/run_agent.py --agent log-analyst --task "Analyse samples/ornek-auth.log"

`--selftest` puts a table of synthetic tool calls through the Policy Gate and the
Validator and prints each decision beside the expected one. It calls no model,
touches no network, needs no API key and does not need `claude-agent-sdk`
installed — so it is the cheapest honest demonstration that the enforcement is
code. Its audit records go to a temporary log, not the project's.

`--agent` + `--task` is the real run: the named agent from
`governance/agents_registry.json` gets its registered tool list and nothing more,
every tool call passes the gate, and every file it writes passes the Validator.
That path needs `pip install -r sdk/requirements.txt`.
"""
import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Expected decisions are the gate's documented behaviour, not this file's opinion:
# a case that disagrees means the policy changed and someone must look.
SELFTEST_CASES = [
    ("in-scope scan", "Bash", {"command": "nmap -sV 127.0.0.1"}, "pass"),
    ("out-of-scope scan", "Bash", {"command": "nmap -sV 8.8.8.8"}, "deny"),
    ("offensive tool", "Bash", {"command": "hashcat -m 0 hashes.txt"}, "deny"),
    ("write into the protected evidence folder", "Write",
     {"file_path": "ev" "idence/host1/crontab.txt"}, "deny"),
    ("write a report", "Write", {"file_path": "reports/example.md"}, "pass"),
    ("read a sample", "Read", {"file_path": "samples/ornek-phishing.eml"}, "pass"),
    ("registered skill", "Skill", {"skill": "log-analysis"}, "pass"),
    ("unregistered skill", "Skill", {"skill": "no-such-skill"}, "ask"),
    ("registered agent", "Agent", {"subagent_type": "log-analyst"}, "pass"),
    ("unregistered agent", "Agent", {"subagent_type": "no-such-agent"}, "ask"),
]


def selftest_rows(runtime):
    """Yields (label, tool, expected, actual) for every case, gate decisions only."""
    for label, tool, tool_input, expected in SELFTEST_CASES:
        out = runtime.decide_pre_tool_use({"tool_name": tool, "tool_input": tool_input})
        actual = (out.get("hookSpecificOutput", {}).get("permissionDecision", "pass")
                  if out else "pass")
        yield label, tool, expected, actual


def selftest(runtime):
    print("Policy Gate — decisions on synthetic tool calls (no model, no network)\n")
    failures = 0
    for label, tool, expected, actual in selftest_rows(runtime):
        ok = actual == expected
        failures += not ok
        print(f"  {'OK ' if ok else 'BAD'}  {actual:5} (expected {expected:5})  {tool:6} {label}")

    print("\nValidator — a report that does not exist cannot be accepted")
    out = runtime.decide_validator(
        {"tool_name": "Write", "tool_input": {"file_path": "reports/no-such-report.md"}},
        "PostToolUse")
    blocked = out.get("decision") == "block"
    failures += not blocked
    print(f"  {'OK ' if blocked else 'BAD'}  {'block' if blocked else out!r}")

    print("\nLeast privilege — the tool list comes from the agent registry")
    for name in ("log-analyst", "phishing-analyst", "reviewer"):
        print(f"  {name:18} {runtime.agent_tools(name)}")

    print("\n" + (f"{failures} case(s) disagreed with the policy" if failures
                  else "every case matched the policy"))
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true",
                    help="put synthetic tool calls through the gate and the validator")
    ap.add_argument("--agent", help="an agent name from governance/agents_registry.json")
    ap.add_argument("--task", help="the prompt for the governed run")
    ap.add_argument("--model", help="model id (default: the SDK's)")
    ap.add_argument("--max-turns", type=int, default=20)
    ap.add_argument("--audit-live", action="store_true",
                    help="with --selftest, write to the project's audit log instead of a temporary one")
    args = ap.parse_args(argv)

    if args.selftest and not args.audit_live:
        os.environ.setdefault(
            "GOV_AUDIT_LOG", str(Path(tempfile.gettempdir()) / "gov_sdk_selftest.jsonl"))

    import governance_runtime as runtime
    runtime.govlib.setup_io()  # same console encoding handling as the hooks

    if args.selftest:
        return selftest(runtime)

    if not args.task:
        ap.error("give --task, or --selftest")

    text, result = asyncio.run(runtime.run_task(
        args.task, agent=args.agent, model=args.model, max_turns=args.max_turns))
    print(text)
    if result is not None:
        print(f"\n[{result.subtype} · {result.num_turns} turns · "
              f"${result.total_cost_usd or 0:.4f}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
