# The governed analysis page as a container.
#
#   docker build -f sdk/Dockerfile -t gov-web .
#   docker run --rm -p 8000:8000 \
#     -e ANTHROPIC_API_KEY=sk-ant-... \
#     -e GOV_WEB_TOKEN=<long-random-value> \
#     -v "$PWD/reports:/app/reports" -v "$PWD/work:/app/work" \
#     -v "$PWD/governance/audit.jsonl:/app/governance/audit.jsonl" \
#     gov-web
#
# Mounts and the non-root user: the container runs as uid 10001, so a mounted
# folder the host owns as root is read-only to it and the run fails on its first
# write. Give the folders away once on the host:
#
#   mkdir -p reports work && touch governance/audit.jsonl
#   sudo chown -R 10001:10001 reports work governance/audit.jsonl
#
# Mount the audit log as a FILE that already exists. Docker creates a directory
# for a missing mount source, and a directory where the hash-chained log should
# be silently breaks the chain.
#
# Three deliberate choices:
#
#   Node is here because `claude-agent-sdk` drives the Claude Code CLI as a
#   subprocess; without the global npm install of @anthropic-ai/claude-code the
#   SDK raises CLINotFoundError and nothing else in the image matters.
#
#   The report folder, the work board and the audit log are mounted rather than
#   baked in. The audit log is append-only and hash-chained: a container that
#   keeps it inside its own filesystem throws away the chain on every restart,
#   which is the one thing this system cannot afford to lose.
#
#   bubblewrap and socat are installed because the Claude Code sandbox on Linux
#   needs them. Without them the sandbox goes quiet rather than loud, and the
#   Policy Gate refuses shell commands in a cloud session (fail-closed). This is
#   the same pair tools/cloud_setup.sh installs in the cloud environment.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nodejs npm ca-certificates bubblewrap socat \
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
RUN mkdir -p reports work deliverables knowledge proposals

# Nothing in here needs root. The uid is fixed rather than left to the distro, so
# the chown line in the header above keeps working across rebuilds. Only the
# folders the run writes to are handed over; the code and the governance files
# stay owned by root, so the run cannot rewrite its own rules -- not even the
# registries that decide which tools it may call.
#
# `chmod -R a-w /app` is not belt and braces, it is the load-bearing line. COPY
# preserves the source mode, and a build context on a Windows drive arrives
# world-writable (0777 over DrvFs): without this the non-root user could edit
# policy_gate.py, policy.json and the registries, and the user switch above
# would buy nothing. Proven by probing from inside the container, not assumed.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin gov \
 && touch governance/audit.jsonl \
 && chmod -R a-w /app \
 && chown -R 10001:10001 reports work deliverables knowledge proposals governance/audit.jsonl \
 && chmod -R u+w reports work deliverables knowledge proposals governance/audit.jsonl
USER 10001

# On Linux the SDK runs Bash inside the sandbox described by .claude/settings.json;
# governance_runtime.sandbox_settings() carries that block across, because
# setting_sources=[] keeps the CLI from reading the file itself. In an unprivileged
# container bubblewrap cannot nest, so the run needs GOV_SANDBOX_NESTED=1 (a weaker
# sandbox, opt-in) or --privileged. Without either, the sandbox simply does not
# engage and the Policy Gate is what stands.
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD ["python", "sdk/web.py", "--host", "0.0.0.0", "--port", "8000"]
