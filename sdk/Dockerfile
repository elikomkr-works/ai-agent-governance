# The governed analysis page as a container.
#
# NOT YET RUN: this file was written on a machine without Docker, so it is the
# server step's starting point, not a proven image. Build it once and fix what
# the build says before trusting it.
#
#   docker build -f sdk/Dockerfile -t gov-web .
#   docker run --rm -p 8000:8000 \
#     -e ANTHROPIC_API_KEY=sk-ant-... \
#     -e GOV_WEB_TOKEN=<long-random-value> \
#     -v "$PWD/reports:/app/reports" -v "$PWD/work:/app/work" \
#     -v "$PWD/governance/audit.jsonl:/app/governance/audit.jsonl" \
#     gov-web
#
# Two deliberate choices:
#
#   Node is here because `claude-agent-sdk` drives the Claude Code CLI as a
#   subprocess; without the global npm install of @anthropic-ai/claude-code the
#   SDK raises CLINotFoundError and nothing else in the image matters.
#
#   The report folder, the work board and the audit log are mounted rather than
#   baked in. The audit log is append-only and hash-chained: a container that
#   keeps it inside its own filesystem throws away the chain on every restart,
#   which is the one thing this system cannot afford to lose.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g @anthropic-ai/claude-code

WORKDIR /app
COPY sdk/requirements.txt sdk/requirements.txt
RUN pip install --no-cache-dir -r sdk/requirements.txt

# The whole governance layer, because the page is only a front for it: the hooks
# are imported in-process, and the registries, policy and templates are read at
# run time from the paths in governance/paths.json.
COPY .claude/hooks .claude/hooks
COPY .claude/skills .claude/skills
COPY .claude/agents .claude/agents

# The settings file travels too, although this layer never lets the CLI read it:
# `build_options()` pins `setting_sources=[]`, so the command hooks it declares
# are not run a second time (a test asserts that). It is here because the test
# suite reads it directly, to check that the sandbox rules and the write denials
# still agree with governance/paths.json. Without it the suite stops at case 207
# inside the image, which is exactly the question the image should be able to
# answer about itself.
COPY .claude/settings.json .claude/settings.json

COPY governance governance
COPY sdk sdk
COPY tools tools
COPY CLAUDE.md CLAUDE.md

# The test suite travels with the image on purpose. It needs no API key and no
# model call, so it is the only way to ask a built image whether the enforcement
# it carries still holds -- on the server, after a rebuild, before any customer
# file is uploaded:
#
#   docker run --rm gov-web python tests/test_governance.py
#   docker run --rm gov-web python sdk/run_agent.py --selftest
COPY tests tests
RUN mkdir -p reports work deliverables knowledge

# On Linux the sandbox layer that native Windows cannot provide is available to
# the SDK (ClaudeAgentOptions.sandbox); turning it on is the next hardening step.
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD ["python", "sdk/web.py", "--host", "0.0.0.0", "--port", "8000"]
