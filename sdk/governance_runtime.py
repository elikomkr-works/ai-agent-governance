"""Governance runtime for the Claude Agent SDK.

The governance layer was built as Claude Code hooks: `policy_gate.py` (PreToolUse)
and `validator.py` (PostToolUse + Stop), each a process that reads a hook event on
stdin and writes a decision on stdout. This module runs the **same two modules** as
in-process callbacks of a Python application built on `claude-agent-sdk`.

Nothing about the policy is re-implemented here. The hook modules already expose
pure functions over the event dict, and the decision shape Claude Code expects is
the shape the Agent SDK expects, so this file is an adapter, not a second engine:

    policy_gate.evaluate(...) + apply_cloud_rules(...)  ->  PreToolUse output
    validator.handle(...)                               ->  PostToolUse / Stop output

That is the claim the project rests on, demonstrated rather than asserted: the five
checkpoints are code, so they survive being lifted out of the harness they were
written for. A prompt-level rule could not make this move.

Two deliberate decisions:

- `setting_sources=[]` in `build_options()`. With filesystem settings loaded, the
  CLI underneath the SDK would ALSO run `.claude/settings.json`'s command hooks,
  so every tool call would pass the gate twice and write two audit records. The
  callbacks registered here are the single path.
- Least privilege comes from `governance/agents_registry.json`, the same file the
  drift tests check against the agent definitions. An agent's tool list is not
  retyped in this layer, so it cannot drift from the definition that grants it.

The import of `claude_agent_sdk` is deferred into `build_options()`: the decision
functions below, and their tests, run with nothing installed.
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"  # fixed by Claude Code, so not in paths.json
sys.path.insert(0, str(HOOKS))

import govlib  # noqa: E402
import policy_gate  # noqa: E402
import validator  # noqa: E402

PRE_EVENT = "PreToolUse"
READ_ONLY = ("Read", "Grep", "Glob")


def _event(data, name):
    """The hook event dict, with the event name the hook modules branch on."""
    out = dict(data or {})
    out["hook_event_name"] = out.get("hook_event_name") or name
    return out


def decide_pre_tool_use(input_data):
    """Policy Gate decision for one tool call. Returns the SDK hook output dict.

    `{}` means the gate does not interfere and the normal permission flow runs.
    Fail-closed: if the gate itself raises, the call is denied, exactly as the
    hook process does.
    """
    data = _event(input_data, PRE_EVENT)
    tool = data.get("tool_name", "")
    try:
        verdict = policy_gate.evaluate(
            data, govlib.load_policy(), govlib.registered_skills(),
            govlib.rel_path, govlib.registered_agents(),
        )
        policy_gate.apply_cloud_rules(
            verdict, tool, (data.get("tool_input") or {}).get("command", ""))
        decision, reason = verdict.decision, " | ".join(verdict.reasons)
    except Exception as e:  # noqa: BLE001 - the gate's own failure must not open the door
        decision = "deny"
        reason = f"DENY: Policy Gate çalışamadı, güvenli tarafta kalındı: {e!r}"

    try:
        govlib.audit(PRE_EVENT, tool or "?", decision, reason,
                     policy_gate.summarize(data), data)
    except Exception:  # noqa: BLE001 - an unwritable log never silently allows a call
        pass

    if decision == "pass":
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": PRE_EVENT,
            "permissionDecision": decision,
            "permissionDecisionReason": "[Policy Gate] " + reason,
        }
    }


def decide_validator(input_data, event):
    """Validator output for a PostToolUse or Stop event, or `{}` when it is silent.

    `validator.handle` returns `{"decision": "block", ...}` for a file that fails
    the structure check — the same JSON an SDK callback returns to block.
    """
    data = _event(input_data, event)
    try:
        return validator.handle(data, govlib) or {}
    except Exception as e:  # noqa: BLE001 - an unverified output is not an accepted one
        reason = f"[Validator] Doğrulama çalışamadı, sonuç doğrulanmış sayılmaz: {e!r}"
        if event == "Stop" and data.get("stop_hook_active"):
            return {"systemMessage": "⚠ " + reason}
        return {"decision": "block", "reason": reason}


def agent_tools(name):
    """The tool list the registry grants an agent, or None for an unknown name."""
    registry = govlib.load_json(govlib.path("agents_registry"))
    for entry in registry.get("agents", []):
        if entry.get("name") == name:
            return list(entry.get("tools") or [])
    return None


async def pre_tool_use_hook(input_data, tool_use_id, context):
    return decide_pre_tool_use(input_data)


async def post_tool_use_hook(input_data, tool_use_id, context):
    return decide_validator(input_data, "PostToolUse")


async def stop_hook(input_data, tool_use_id, context):
    return decide_validator(input_data, "Stop")


def build_options(agent=None, model=None, cwd=None, max_turns=20, **extra):
    """`ClaudeAgentOptions` with the governance callbacks registered.

    `agent` names an entry in the agent registry; its tools become the run's tool
    list, so the SDK application grants no privilege the definition does not.
    Raises ImportError with an install line when `claude-agent-sdk` is missing.
    """
    try:
        from claude_agent_sdk import ClaudeAgentOptions, HookMatcher
    except ImportError as e:  # noqa: BLE001
        raise ImportError(
            "claude-agent-sdk is not installed. Run: pip install -r sdk/requirements.txt"
        ) from e

    tools = None
    if agent is not None:
        tools = agent_tools(agent)
        if tools is None:
            raise ValueError(
                f"'{agent}' is not in {govlib.rel('agents_registry')}; "
                "an unregistered agent is a user decision, not this layer's")

    options = dict(
        cwd=str(cwd or ROOT),
        # Load no filesystem settings: the callbacks below are the only hook path.
        setting_sources=[],
        max_turns=max_turns,
        hooks={
            "PreToolUse": [HookMatcher(hooks=[pre_tool_use_hook])],
            "PostToolUse": [HookMatcher(hooks=[post_tool_use_hook])],
            "Stop": [HookMatcher(hooks=[stop_hook])],
        },
    )
    if tools:
        options["allowed_tools"] = tools
    if model:
        options["model"] = model
    options.update(extra)
    return ClaudeAgentOptions(**options)


async def run_task(prompt, agent=None, **kwargs):
    """Run one governed task and return (text, result) from the SDK message stream."""
    from claude_agent_sdk import (AssistantMessage, ClaudeSDKClient, ResultMessage,
                                  TextBlock)

    options = build_options(agent=agent, **kwargs)
    chunks, result = [], None
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
            elif isinstance(message, ResultMessage):
                result = message
    return "".join(chunks), result


def run_task_sync(prompt, agent=None, **kwargs):
    return asyncio.run(run_task(prompt, agent=agent, **kwargs))


__all__ = [
    "ROOT", "READ_ONLY", "agent_tools", "build_options", "decide_pre_tool_use",
    "decide_validator", "post_tool_use_hook", "pre_tool_use_hook", "run_task",
    "run_task_sync", "stop_hook",
]
