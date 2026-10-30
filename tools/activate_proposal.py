"""Activates a draft under proposals/ as a live skill and agent (user only).

skill-smith writes drafts; this script is the one step that makes a draft real:
it copies the skill and agent definitions under .claude/, adds the entries to
both registries and, for an agent with a limited shell, writes the agent_shell
list into policy.json. Without it, activation is about ten hand edits and the
registries drift from the definition files.

The user runs it by hand. An agent cannot: the Policy Gate denies the command
(policy.json -> deny_commands) and the confirmation question is refused when
there is no stdin.

Usage:
    python tools/activate_proposal.py proposals/<name>
    python tools/activate_proposal.py proposals/<name> --deneme     # plan only
    python tools/activate_proposal.py proposals/<name> --guncelle   # overwrite existing entries
"""
import argparse
import getpass
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import govlib  # noqa: E402

AGENTS_DIR = ROOT / ".claude" / "agents"
SKILLS_DIR = ROOT / ".claude" / "skills"
NOTE_FILES = {"NOTES.md", "NOTLAR.md"}
# A specialist may hold only these tools. Agent/Task are absent on purpose: the
# platform does not let a subagent spawn another, and all coordination stays
# with the Lead Agent.
ALLOWED_TOOLS = {"Read", "Grep", "Glob", "Bash", "Write", "Edit", "Skill", "WebSearch", "WebFetch"}
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def frontmatter(text):
    """The '---' block at the top of a definition file as {key: value}."""
    if not text.startswith("---"):
        return {}
    fields = {}
    for line in text.split("---", 2)[1].splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


def tool_list(value):
    return [t.strip() for t in value.split(",") if t.strip()]


def render_registry(data, array_key, one_line):
    """Registry JSON in the hand-written style of the file it replaces.

    Entries of the main array stay on one line in the agent registry and are
    indented blocks in the skill registry, so activation produces a small diff
    instead of reformatting the whole file.
    """
    def block(value, indent):
        text = json.dumps(value, ensure_ascii=False, indent=2)
        return text.replace("\n", "\n" + indent)

    def entry_block(item, indent):
        """One key per line, each value compact — the style of the skill registry."""
        fields = ",\n".join(f'{indent}  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}'
                            for k, v in item.items())
        return "{\n" + fields + "\n" + indent + "}"

    parts = [f'  {json.dumps(k, ensure_ascii=False)}: {block(v, "  ")}'
             for k, v in data.items() if k != array_key]
    if one_line:
        items = [f"    {json.dumps(item, ensure_ascii=False)}" for item in data[array_key]]
    else:
        items = [f'    {entry_block(item, "    ")}' for item in data[array_key]]
    parts.append(f'  {json.dumps(array_key, ensure_ascii=False)}: [\n' + ",\n".join(items) + "\n  ]")
    return "{\n" + ",\n".join(parts) + "\n}\n"


def patch_agent_shell(text, name, commands):
    """Adds the agent's shell allow-list to policy.json as a single line.

    policy.json is hand-formatted, so it is patched as text: rewriting it from
    parsed JSON would reflow every list in the file.
    """
    key = json.dumps(name, ensure_ascii=False)
    line = f"    {key}: {json.dumps(commands, ensure_ascii=False)}"
    existing = re.compile(rf"^    {re.escape(key)}: \[.*?\](,?)$", re.M)
    found = existing.search(text)
    if found:
        return existing.sub(lambda m: line + m.group(1), text, count=1)
    opening = re.search(r'^  "agent_shell": \{$', text, re.M)
    if not opening:
        raise ValueError(f"{govlib.rel('policy')} içinde agent_shell bloğu bulunamadı.")
    return text[:opening.end()] + "\n" + line + "," + text[opening.end():]


def upsert(data, array_key, entry, update):
    """Adds the entry to the array, or replaces the one with the same name."""
    items = data[array_key]
    for i, item in enumerate(items):
        if item.get("name") == entry["name"]:
            if not update:
                raise ValueError(f"'{entry['name']}' zaten {array_key} içinde kayıtlı; --guncelle gerekir.")
            items[i] = entry
            return "güncellendi"
    items.append(entry)
    return "eklendi"


def read_draft(folder):
    """Reads the draft folder: skill entry, agent entry, files to copy."""
    folder = Path(folder).resolve()
    proposals = govlib.path("proposals").resolve()
    if folder.parent != proposals or not folder.is_dir():
        raise SystemExit(f"Hata: taslak {govlib.rel('proposals')} içinde bir klasör olmalı: {folder}")

    entry_file = folder / "registry_entry.json"
    skill_file = folder / "SKILL.md"
    for required in (entry_file, skill_file):
        if not required.is_file():
            raise SystemExit(f"Hata: taslakta {required.name} yok.")

    raw = govlib.load_json(entry_file)
    # Backward compatible: a flat object is the skill entry on its own.
    skill = raw.get("skill", raw if "purpose" in raw else None)
    if skill is None:
        raise SystemExit("Hata: registry_entry.json skill kaydı içermiyor ('purpose' alanı yok).")
    agent = dict(raw.get("agent") or {})
    agent_file = folder / "agent.md"

    skill_fm = frontmatter(skill_file.read_text(encoding="utf-8"))
    if agent_file.is_file():
        agent_fm = frontmatter(agent_file.read_text(encoding="utf-8"))
        agent.setdefault("name", agent_fm.get("name", ""))
        # The tool list always comes from the definition file, so the registry
        # cannot claim a privilege the agent does not have (or hide one it does).
        agent["tools"] = tool_list(agent_fm.get("tools", ""))
        agent.setdefault("role", agent_fm.get("description", "")[:120])
        agent.setdefault("skills", [skill["name"]])
        agent.setdefault("writes", skill.get("output") and [skill["output"], "@work"] or [])
    elif agent:
        raise SystemExit("Hata: registry_entry.json agent kaydı var ama taslakta agent.md yok.")
    else:
        agent_fm = {}

    extra = sorted(p for p in folder.glob("*.md")
                   if p.name not in NOTE_FILES | {"SKILL.md", "agent.md"})
    return {"folder": folder, "skill": skill, "agent": agent, "agent_fm": agent_fm,
            "skill_fm": skill_fm, "agent_file": agent_file if agent_file.is_file() else None,
            "skill_file": skill_file, "extra": extra,
            "agent_shell": raw.get("agent_shell") or []}


def validate(draft):
    """All reasons the draft cannot be activated, as a list of messages."""
    errors = []
    skill, agent = draft["skill"], draft["agent"]
    name = skill.get("name", "")
    if not NAME_RE.match(name):
        errors.append(f"skill adı küçük harf, rakam ve '-' olmalı: {name!r}")
    if draft["skill_fm"].get("name") != name:
        errors.append(f"SKILL.md içindeki ad ({draft['skill_fm'].get('name')!r}) kayıttaki adla ({name!r}) aynı değil")
    if not draft["skill_fm"].get("description"):
        errors.append("SKILL.md ön bilgisinde description yok")
    for field in ("purpose", "triggers", "required_input", "network_access", "risk", "output"):
        if field not in skill:
            errors.append(f"skill kaydında '{field}' alanı yok")
    for ref in [skill.get("output", "")] + list(agent.get("writes", [])):
        if isinstance(ref, str) and ref.startswith("@") and ref[1:] not in govlib.paths():
            errors.append(f"'{ref}' governance/paths.json içinde tanımlı değil")

    if not draft["agent_file"]:
        return errors
    tools = set(agent.get("tools", []))
    if not NAME_RE.match(agent.get("name", "")):
        errors.append(f"agent adı küçük harf, rakam ve '-' olmalı: {agent.get('name')!r}")
    if not draft["agent_fm"].get("description"):
        errors.append("agent.md ön bilgisinde description yok")
    if not tools:
        errors.append("agent.md ön bilgisinde tools yok")
    if tools - ALLOWED_TOOLS:
        errors.append(f"izin verilmeyen araç: {', '.join(sorted(tools - ALLOWED_TOOLS))}")
    # The same rules the fleet drift test enforces, checked before writing.
    if ("Write" in tools) != bool(agent.get("writes")):
        errors.append("Write aracı ile 'writes' alanı tutarsız")
    if ("Skill" in tools) != bool(agent.get("skills")):
        errors.append("Skill aracı ile 'skills' alanı tutarsız")
    shell = agent.get("shell")
    if "Bash" in tools:
        if shell not in ("limited", "broad"):
            errors.append("Bash alan agent 'shell' alanında 'limited' veya 'broad' beyan etmeli")
        if shell == "limited" and not draft["agent_shell"]:
            errors.append("'limited' kabuk için registry_entry.json'da agent_shell listesi gerekir")
        if shell == "broad" and draft["agent_shell"]:
            errors.append("'broad' kabukta agent_shell listesi olmaz")
    elif shell or draft["agent_shell"]:
        errors.append("kabuksuz agent'a 'shell' veya agent_shell yazılmaz")

    policy = govlib.load_json(govlib.path("policy"))
    forbidden = set(policy["forbidden_tools"]) | set(policy["active_scanners"])
    bad = {c for c in draft["agent_shell"] if c.lower() in forbidden}
    if bad:
        errors.append(f"agent_shell saldırı/tarama aracı içeremez: {', '.join(sorted(bad))}")
    return errors


def plan(draft, update):
    """Human-readable list of what activation would change."""
    steps = []
    skill_dir = SKILLS_DIR / draft["skill"]["name"]
    steps.append(f"skill  → {(skill_dir / 'SKILL.md').relative_to(ROOT)}")
    for p in draft["extra"]:
        steps.append(f"ek     → {(skill_dir / p.name).relative_to(ROOT)}")
    if draft["agent_file"]:
        steps.append(f"agent  → {(AGENTS_DIR / (draft['agent']['name'] + '.md')).relative_to(ROOT)}")
    steps.append(f"reyestr→ {govlib.rel('skills_registry')} ({draft['skill']['name']})")
    if draft["agent_file"]:
        steps.append(f"reyestr→ {govlib.rel('agents_registry')} ({draft['agent']['name']})")
    if draft["agent_shell"]:
        steps.append(f"politika→ {govlib.rel('policy')} agent_shell[{draft['agent']['name']}] = {draft['agent_shell']}")
    if update:
        steps.append("mevcut kayıtların üzerine yazılır (--guncelle)")
    return steps


def apply(draft, update):
    skill_name = draft["skill"]["name"]
    skill_dir = SKILLS_DIR / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(draft["skill_file"], skill_dir / "SKILL.md")
    for p in draft["extra"]:
        shutil.copy2(p, skill_dir / p.name)

    skills = govlib.load_json(govlib.path("skills_registry"))
    done = [f"skill reyestrine {upsert(skills, 'skills', draft['skill'], update)}"]
    govlib.path("skills_registry").write_text(
        render_registry(skills, "skills", one_line=False), encoding="utf-8")

    if draft["agent_file"]:
        agent_name = draft["agent"]["name"]
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(draft["agent_file"], AGENTS_DIR / f"{agent_name}.md")
        agents = govlib.load_json(govlib.path("agents_registry"))
        done.append(f"agent reyestrine {upsert(agents, 'agents', draft['agent'], update)}")
        govlib.path("agents_registry").write_text(
            render_registry(agents, "agents", one_line=True), encoding="utf-8")

        if draft["agent_shell"]:
            policy_path = govlib.path("policy")
            patched = patch_agent_shell(policy_path.read_text(encoding="utf-8"), agent_name, draft["agent_shell"])
            json.loads(patched)  # fail-closed: never leave a broken policy behind
            policy_path.write_text(patched, encoding="utf-8")
            done.append("agent_shell politikaya yazıldı")
    return done


def main(argv=None):
    govlib.setup_io()
    parser = argparse.ArgumentParser(description="Taslağı etkin skill/agent'a çevirir")
    parser.add_argument("klasor")
    parser.add_argument("--deneme", action="store_true", help="hiçbir şey yazmaz, planı gösterir")
    parser.add_argument("--guncelle", action="store_true", help="aynı adlı kayıtların üzerine yaz")
    args = parser.parse_args(argv)

    draft = read_draft(args.klasor)
    errors = validate(draft)
    print(f"Taslak: {draft['folder'].relative_to(ROOT)}")
    for step in plan(draft, args.guncelle):
        print(f"  {step}")
    if errors:
        print("\nTaslak etkinleştirilemez:")
        for e in errors:
            print(f"  - {e}")
        govlib.audit("Activate", "activate_proposal.py", "red", "Taslak doğrulamayı geçmedi", draft["folder"].name)
        return 1
    if args.deneme:
        print("\nDeneme: hiçbir dosya değişmedi.")
        return 0

    try:
        answer = input("\nBu taslağı etkinleştiriyor musunuz? (evet/hayır): ").strip().lower()
    except EOFError:
        answer = ""
    if answer != "evet":
        govlib.audit("Activate", "activate_proposal.py", "iptal", "Kullanıcı onay vermedi", draft["folder"].name)
        print("İptal edildi.")
        return 1

    done = apply(draft, args.guncelle)
    govlib.audit("Activate", "activate_proposal.py", "etkinlestirildi",
                 f"onaylayan={getpass.getuser()} · " + "; ".join(done), draft["folder"].name)
    print("\n" + "\n".join(f"✓ {d}" for d in done))
    print(f"Sonraki adım: python {govlib.rel('tests')}test_governance.py (filo testleri kaymayı denetler)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
