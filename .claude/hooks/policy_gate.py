"""Policy Gate — PreToolUse hook.

Her araç çağrısından önce çalışır ve üç karardan birini verir:
  deny — engelle (agent bu işlemi yapamaz)
  ask  — kullanıcı onayı iste
  pass — karışma, normal izin akışı devam etsin
Gate'in kendisi hata verirse güvenli tarafta kalır: deny (fail-closed).
"""
import ipaddress
import json
import os
import re
import shlex
import shutil
import sys
from urllib.parse import urlparse

RANK = {"pass": 0, "ask": 1, "deny": 2}
SHELL_TOOLS = {"Bash", "PowerShell"}
SANDBOX_DEPS = ("bwrap", "socat")  # Claude Code sandbox'ının Linux bağımlılıkları
GIT_UNSANDBOXED = {"commit", "push"}  # .claude/settings.json → sandbox.excludedCommands ile aynı
GIT_EXEC_OPTIONS = ("--receive-pack", "--exec", "--upload-pack")
UNSAFE_SHELL = re.compile(r"\$\(|`|[<>]")  # komut ikamesi, süreç ikamesi, yönlendirme
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

IP_LIKE = re.compile(r"^\d{1,3}(\.[\d*,-]{1,11}){3}(/\d{1,2})?$")
DOMAIN = re.compile(r"^(?=.{1,253}$)([a-z0-9-]{1,63}\.)+[a-z]{2,24}$")
FILE_EXT = {
    "txt", "xml", "json", "log", "md", "csv", "html", "htm", "py", "ps1", "sh",
    "gnmap", "nmap", "conf", "cfg", "ini", "yaml", "yml", "out", "pcap", "exe",
}
WRITE_MARKER = re.compile(
    r"(>|\btee\b|set-content|add-content|out-file|\bcp\b|\bmv\b|copy-item|move-item|"
    r"\brm\b|remove-item|new-item|rename-item|\bdel\b|\bcopy\b|\bmove\b|\bren\b|"
    r"\btouch\b|\bchmod\b|\bsed\s+-i)"
)
STDERR_REDIRECT = re.compile(r"2>(&1|/dev/null|\$null)")


class Verdict:
    def __init__(self):
        self.decision = "pass"
        self.reasons = []

    def add(self, decision, reason):
        if RANK[decision] > RANK[self.decision]:
            self.decision = decision
        if decision != "pass":
            self.reasons.append(f"{decision.upper()}: {reason}")


def tool_name(token):
    name = re.split(r"[\\/]", token.strip("'\""))[-1].lower()
    return re.sub(r"\.(exe|py|ps1)$", "", name)


def tokenize(segment):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def segments(command):
    # Tek '&' (arka plan) da yeni komut başlatır; '2>&1', '&>' gibi yönlendirmeler bölünmez.
    return [s.strip() for s in re.split(r"\|\||&&|[;|\n]|(?<![<>&])&(?![>&])", command) if s.strip()]


def in_scope(target, allowed):
    if target in allowed:
        return True
    try:
        net = ipaddress.ip_network(target, strict=False)
    except ValueError:
        return False
    for a in allowed:
        try:
            if net.subnet_of(ipaddress.ip_network(a, strict=False)):
                return True
        except (ValueError, TypeError):
            continue
    return False


def extract_targets(tokens):
    targets = []
    for raw in tokens:
        t = raw.strip("'\"").lower()
        if not t or t.startswith("-"):
            continue
        if "://" in t:
            targets.append(urlparse(t).hostname or t)
            continue
        try:
            ipaddress.ip_network(t, strict=False)
            targets.append(t)
            continue
        except ValueError:
            pass
        host = t.rsplit(":", 1)[0] if t.count(":") == 1 else t
        if host == "localhost" or IP_LIKE.match(host):
            targets.append(host)
        elif DOMAIN.match(host) and host.rsplit(".", 1)[-1] not in FILE_EXT:
            targets.append(host)
    return targets


def mentions_path(command, prefix):
    """Komut, yolu bağımsız bir yol parçası olarak içeriyor mu? ('test_governance.py' sayılmaz)"""
    name = re.escape(prefix.rstrip("/"))
    if not prefix.endswith("/"):
        return re.search(rf"(^|[\s/'\"=]){name}($|[\s/'\";|&>])", command) is not None
    # Folder: inside an argument only 'name/...' counts; the bare name only as a whole argument
    # ('cd evidence'), so the word in code or text (get('evidence')) is not a path.
    if re.search(rf"(^|[\s/'\"=<>(]){name}/", command):
        return True
    return any(re.search(rf"(^|[/=<>]){name}/?$", t) for seg in segments(command) for t in tokenize(seg))


def check_path_write(path, policy, v):
    rel = path if isinstance(path, str) else str(path)
    for prefix in policy["paths"]["deny_write"]:
        if rel.startswith(prefix):
            v.add("deny", f"'{prefix}' korumalı; yalnızca kullanıcı değiştirebilir.")
            return
    for prefix in policy["paths"]["ask_write"]:
        if rel.startswith(prefix):
            v.add("ask", f"Yönetişim dosyası değişikliği ('{prefix}') kullanıcı onayı gerektirir.")
            return


def check_sensitive(text, policy, v):
    for pat in policy["sensitive_patterns"]:
        if re.search(pat, text):
            v.add("ask", f"Hassas dosya/gizli bilgi erişimi ('{pat}') kullanıcı onayı gerektirir.")
            return


def check_shell(command, policy, v, rel_path):
    norm = command.replace("\\", "/").lower()
    allowed = [a.lower() for a in policy["scope"]["allowed_targets"]]

    for pat in policy["deny_commands"]:
        if re.search(pat, norm):
            v.add("deny", "Onay betiği yalnızca kullanıcı tarafından elle çalıştırılır.")

    writes = WRITE_MARKER.search(STDERR_REDIRECT.sub("", norm))
    if writes:
        for prefix in policy["paths"]["deny_write"]:
            if mentions_path(norm, prefix):
                v.add("deny", f"Kabuk komutu korumalı alana ('{prefix}') yazıyor.")
        for prefix in policy["paths"]["ask_write"]:
            if mentions_path(norm, prefix):
                v.add("ask", f"Kabuk komutu yönetişim dosyalarına ('{prefix}') dokunuyor.")

    for pat in policy["destructive_patterns"]:
        if re.search(pat, norm):
            v.add("ask", f"Yıkıcı/sistem değiştiren komut ('{pat}') kullanıcı onayı gerektirir.")

    for token in tokenize(norm):
        check_sensitive(rel_path(token), policy, v)

    forbidden = set(policy["forbidden_tools"])
    for seg in segments(norm):
        tokens = tokenize(seg)
        while tokens and tokens[0] in ("sudo", "time", "&", "env"):
            tokens = tokens[1:]
        if not tokens:
            continue
        name = tool_name(tokens[0])
        callees = {name} | {tool_name(t) for t in tokens if t.endswith((".py", ".exe"))}
        if "-m" in tokens and tokens.index("-m") + 1 < len(tokens):
            callees.add(tool_name(tokens[tokens.index("-m") + 1]))
        hit = callees & forbidden
        if hit:
            v.add("deny", f"Saldırı aracı ({', '.join(sorted(hit))}) pilot kapsamında yasak.")
            continue

        network = policy["active_scanners"] + policy["diagnostic_tools"] + policy["http_clients"]
        if name in network:
            targets = extract_targets(tokens[1:])
            out = [t for t in targets if not in_scope(t, allowed)]
            if name in policy["active_scanners"]:
                if out:
                    v.add("deny", f"Kapsam dışı hedef: {', '.join(out)}. İzinli: {', '.join(allowed)}.")
                elif not targets:
                    v.add("ask", f"'{name}' için hedef belirlenemedi; kapsam doğrulanamıyor.")
            elif name in policy["diagnostic_tools"]:
                if out or not targets:
                    v.add("ask", f"Kapsam dışı/belirsiz hedefe teşhis komutu ('{name}'): {', '.join(out) or '?'}.")
            elif out:
                v.add("ask", f"Kapsam dışı adrese HTTP isteği: {', '.join(out)}.")


def restrict_shell(command, allowed, syntax, v, why):
    """Komut yalnızca izinli araçlardan oluşmalı: zincirin her parçasının ilk sözcüğü listede,
    yönlendirme ve ikame yok. sudo/env gibi önekler de liste dışı sayılır."""
    norm = command.replace("\\", "/").lower()
    bad = [s for s in syntax if s in norm]
    if bad:
        v.add("deny", f"{why}: yönlendirme/ikame kullanılamaz ({' '.join(bad)}).")
    for seg in segments(norm):
        tokens = tokenize(seg)
        name = tool_name(tokens[0]) if tokens else ""
        if name not in allowed:
            v.add("deny", f"{why}: '{name}' izinli değil. İzinli: {', '.join(allowed)}.")


def check_restricted(command, agent, policy, v):
    norm = command.replace("\\", "/").lower()
    syntax = policy.get("restricted_syntax", [])
    guard = policy.get("evidence_guard")
    if guard and (any(mentions_path(norm, d) for d in guard["dirs"])
                  or any(re.search(m, norm) for m in guard["markers"])):
        restrict_shell(command, guard["allowed"], syntax, v, "Kanıta dokunan komut")
    allowed = policy.get("agent_shell", {}).get(agent)
    if isinstance(allowed, list):
        restrict_shell(command, allowed, syntax, v, f"'{agent}' agent'ının kabuğu sınırlı")


def evaluate(data, policy, skills, rel_path, agents=frozenset()):
    v = Verdict()
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}

    if tool in SHELL_TOOLS:
        check_shell(inp.get("command", ""), policy, v, rel_path)
        check_restricted(inp.get("command", ""), str(data.get("agent_type") or ""), policy, v)
    elif tool in WRITE_TOOLS:
        path = inp.get("file_path") or inp.get("notebook_path") or ""
        check_path_write(rel_path(path), policy, v)
    elif tool == "Read":
        check_sensitive(rel_path(inp.get("file_path", "")), policy, v)
    elif tool == "Skill":
        name = inp.get("skill", "")
        if name not in skills:
            v.add("ask", f"'{name}' skill reyestrinde kayıtlı değil (governance/skills_registry.json).")
    elif tool in ("Agent", "Task"):
        name = inp.get("subagent_type") or "general-purpose"
        if name not in agents:
            v.add("ask", f"'{name}' agent reyestrinde kayıtlı değil (governance/agents_registry.json).")
    return v


def check_unsandboxed_git(command, v):
    """settings.json → sandbox.excludedCommands ile sandbox dışında çalışan git komutları.

    Bulutta commit imzası 127.0.0.1'deki bir servise gider; sandbox'ın ağ ad alanından
    oraya ulaşılamadığı için git commit/push sandbox dışında çalışır. Bu komutun içine
    gömülen her şey de sandbox dışında çalışacağından: zincir, komut ikamesi ve
    yönlendirme yasak; push'a yerel komut çalıştıran seçenek verilemez. Git'in kendi
    çalıştırdığı betikler (.git/hooks, .git/config) permissions.deny ile korunur.
    """
    segs = segments(command)
    for seg in segs:
        tokens = tokenize(seg)
        if len(tokens) < 2 or tool_name(tokens[0]) != "git" or tokens[1] not in GIT_UNSANDBOXED:
            continue
        if len(segs) > 1 or UNSAFE_SHELL.search(command):
            v.add("deny", f"git {tokens[1]} sandbox dışında çalışır; tek başına, komut ikamesi ve "
                          "yönlendirme olmadan çalıştırın (mesaj için -m \"...\" veya -F <dosya>).")
        if any(t.startswith(GIT_EXEC_OPTIONS) for t in tokens):
            v.add("deny", f"git {tokens[1]}'a yerel komut çalıştıran seçenek verilemez ({', '.join(GIT_EXEC_OPTIONS)}).")


def apply_cloud_rules(v, tool, command="", env=os.environ, which=shutil.which):
    """Bulut oturumu (CLAUDE_CODE_REMOTE=true) için ek kurallar.

    2026-10-25 bulut kural testi iki açık gösterdi:
    - Bulutta onaylayan kullanıcı yok; 'ask' kararı komutu durdurmadı. Bu yüzden ask → deny.
    - Sandbox Linux'ta bubblewrap ve socat ister; yoksa Claude Code komutları sessizce
      sandbox'sız çalıştırır (failIfUnavailable yerel Windows yüzünden false). Bu durumda
      kabuk komutları reddedilir; paketleri tools/cloud_setup.sh kurar.
    Sandbox yalnızca bulutta çalıştığı için sandbox dışı git kuralları da burada uygulanır.
    """
    if env.get("CLAUDE_CODE_REMOTE") != "true":
        return v
    if v.decision == "ask":
        v.add("deny", "Bulut oturumunda onaylayan kullanıcı yok; onay gerektiren işlem reddedildi.")
    if tool in SHELL_TOOLS:
        missing = [dep for dep in SANDBOX_DEPS if not which(dep)]
        if missing:
            v.add("deny", f"Bulutta sandbox bağımlılığı eksik ({', '.join(missing)}); komut sandbox'sız "
                          "çalışırdı. Ortamın kurulum betiğine tools/cloud_setup.sh içeriğini ekleyin.")
        check_unsandboxed_git(command, v)
    return v


def summarize(data):
    inp = data.get("tool_input") or {}
    for key in ("command", "file_path", "skill", "url", "query", "pattern"):
        if key in inp:
            return f"{key}={inp[key]}"
    return ""


def main():
    data = {}
    govlib = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import govlib
        govlib.setup_io()
        data = json.load(sys.stdin)
        v = evaluate(data, govlib.load_policy(), govlib.registered_skills(), govlib.rel_path,
                     govlib.registered_agents())
        apply_cloud_rules(v, data.get("tool_name", ""), (data.get("tool_input") or {}).get("command", ""))
        decision, reason = v.decision, " | ".join(v.reasons)
    except Exception as e:
        decision, reason = "deny", f"DENY: Policy Gate çalışamadı, güvenli tarafta kalındı: {e!r}"

    try:
        if govlib:
            govlib.audit("PreToolUse", data.get("tool_name", "?"), decision, reason, summarize(data),
                         data if isinstance(data, dict) else None)
    except Exception:
        pass

    if decision != "pass":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": "[Policy Gate] " + reason,
            }
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
