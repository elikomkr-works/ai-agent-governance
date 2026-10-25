"""Policy Gate, Validator, yol yapılandırması ve panel üreticisinin kabul testleri.

Çalıştırma: python tests/test_governance.py
Hook'lar gerçek süreç olarak çalıştırılır; denetim kaydı geçici dosyaya yazılır.
Yollar governance/paths.json'dan okunur; testler de sabit yol yazmaz.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"  # Yeri Claude Code ayarlarında (.claude/settings.json) sabit.
sys.path.insert(0, str(HOOKS))
import govlib  # noqa: E402
import policy_gate  # noqa: E402
import validator  # noqa: E402

sys.path.insert(0, str(govlib.path("tools")))
import build_site  # noqa: E402
import verify_audit  # noqa: E402

ENV = dict(os.environ, GOV_AUDIT_LOG=str(Path(tempfile.gettempdir()) / "gov_test_audit.jsonl"))
# Hook vakaları yerel davranışı sınar; bulut kuralları cloud_checks() içinde ayrıca sınanır.
ENV.pop("CLAUDE_CODE_REMOTE", None)
P = govlib.path
R = govlib.rel


def run_hook(script, payload):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run([sys.executable, str(HOOKS / script)], input=raw.encode("utf-8"),
                          capture_output=True, env=ENV, timeout=30)
    assert proc.returncode == 0, f"{script} çıkış kodu {proc.returncode}: {proc.stderr.decode('utf-8', 'replace')}"
    out = proc.stdout.decode("utf-8").strip()
    return json.loads(out) if out else None


def gate(tool, **tool_input):
    out = run_hook("policy_gate.py", {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input})
    return out["hookSpecificOutput"]["permissionDecision"] if out else "pass"


GATE_CASES = [
    # (açıklama, araç, girdi, beklenen)
    ("kapsam içi tarama", "Bash", {"command": "nmap -sV 127.0.0.1"}, "pass"),
    ("kapsam içi, çıktı dosyası hedef sayılmaz", "Bash", {"command": "nmap -oN scan.txt localhost"}, "pass"),
    ("kapsam dışı tarama", "Bash", {"command": "nmap -sV 8.8.8.8"}, "deny"),
    ("kapsam dışı ağ bloğu", "PowerShell", {"command": "nmap -oN out.txt 10.0.0.0/8"}, "deny"),
    ("kapsam dışı alan adı", "Bash", {"command": "nikto -h example.com"}, "deny"),
    ("zincirlenmiş kapsam dışı tarama", "Bash", {"command": "echo ok && nmap 1.1.1.1"}, "deny"),
    ("tek '&' ile arka plana atılan kapsam dışı tarama", "Bash", {"command": "echo ok & nmap 8.8.8.8"}, "deny"),
    ("boşluksuz '&' ile kapsam dışı tarama", "Bash", {"command": "echo ok&nmap 8.8.8.8"}, "deny"),
    ("'2>&1' yönlendirmesi komutu bölmez", "Bash", {"command": "nmap 127.0.0.1 2>&1"}, "pass"),
    ("kapsam dışı ping onaya düşer", "Bash", {"command": "ping -c 1 1.1.1.1"}, "ask"),
    ("kapsam içi ping serbest", "PowerShell", {"command": "ping localhost"}, "pass"),
    ("hedefsiz tarayıcı", "PowerShell", {"command": "Test-NetConnection server01"}, "ask"),
    ("yasak araç", "Bash", {"command": "sqlmap -u http://localhost/?id=1"}, "deny"),
    ("yasak araç python -m ile", "Bash", {"command": "python -m hashcat hashes.txt"}, "deny"),
    ("kapsam dışı HTTP", "Bash", {"command": "curl https://example.com"}, "ask"),
    ("kapsam içi HTTP", "Bash", {"command": "curl http://localhost:8080/health"}, "pass"),
    ("yıkıcı komut", "Bash", {"command": "rm -rf build"}, "ask"),
    ("yıkıcı PowerShell", "PowerShell", {"command": "Remove-Item -Path tmp -Recurse"}, "ask"),
    ("onay betiğini çalıştırma", "Bash", {"command": f"python {R('approve_script')} {R('quarantine')}a.md"}, "deny"),
    ("onaylı bilgiye yazma", "Write", {"file_path": str(P("approved") / "x.md")}, "deny"),
    ("onaylı bilgiye kabukla kopyalama", "Bash", {"command": f"cp a.md {R('approved')}a.md"}, "deny"),
    ("dosya adında 'governance' geçmesi yanlış alarm değil", "PowerShell",
     {"command": "New-Item -ItemType Directory -Force reports; python tests/test_governance.py"}, "pass"),
    ("mutlak yolla politika üzerine yazma", "Bash",
     {"command": f"echo x > '{P('policy').as_posix()}'"}, "ask"),
    ("onaylı bilgiyi okuma serbest", "Bash", {"command": f"cat {R('approved')}a.md 2>/dev/null"}, "pass"),
    ("denetim kaydına yazma", "Edit", {"file_path": R("audit_log")}, "deny"),
    ("politika değişikliği", "Edit", {"file_path": R("policy")}, "ask"),
    ("yol yapılandırması değişikliği", "Write", {"file_path": str(P("paths_file"))}, "ask"),
    ("hook değişikliği", "Write", {"file_path": str(HOOKS / "policy_gate.py")}, "ask"),
    ("panel betiği değişikliği", "Write", {"file_path": str(P("tools") / "build_site.py")}, "ask"),
    ("rapor yazma serbest", "Write", {"file_path": str(P("reports") / "r.md")}, "pass"),
    ("panel çıktısı yazma serbest", "Write", {"file_path": str(P("site_index"))}, "pass"),
    ("gizli dosya okuma", "Read", {"file_path": str(ROOT / ".env")}, "ask"),
    ("SSH anahtarı okuma", "Bash", {"command": "cat ~/.ssh/id_rsa"}, "ask"),
    ("normal dosya okuma", "Read", {"file_path": str(P("samples") / "auth.log")}, "pass"),
    ("kayıtlı skill", "Skill", {"skill": "log-analysis"}, "pass"),
    ("kayıt dışı skill", "Skill", {"skill": "random-skill"}, "ask"),
    ("kayıtlı agent", "Agent", {"subagent_type": "reviewer", "prompt": "x"}, "pass"),
    ("kayıt dışı agent", "Agent", {"subagent_type": "hacker-bot", "prompt": "x"}, "ask"),
    ("türsüz agent (general-purpose) onaya düşer", "Agent", {"prompt": "x"}, "ask"),
    ("web araması serbest", "WebSearch", {"query": "CVE-2024-6387"}, "pass"),
]

GOOD_REPORT = """# Test
## Kapsam
- Girdi: samples/auth.log
## Bulgular
- [OLGU] 203.0.113.45 kaynağından 11 başarısız deneme.
- [ÖNERİ] Parola ile girişi kapatın.
## Kanıt
- `samples/auth.log:2`
## Doğrulama Durumu
KABUL — sayılar grep ile doğrulandı.
"""

GOOD_QUARANTINE = """---
kaynak: https://nvd.nist.gov/vuln/detail/CVE-2024-6387
erisim_tarihi: 2026-10-25
durum: KARANTINADA
ozet: OpenSSH sinyal işleyici yarış durumu.
---
# CVE-2024-6387
"""

VALIDATOR_CASES = [
    ("geçerli rapor", validator.check_report, GOOD_REPORT, True),
    ("bölüm eksik", validator.check_report, GOOD_REPORT.replace("## Kanıt", "## Notlar"), False),
    ("etiketsiz bulgu", validator.check_report, GOOD_REPORT.replace("- [ÖNERİ] ", "- "), False),
    ("boş kanıt", validator.check_report, GOOD_REPORT.replace("- `samples/auth.log:2`", ""), False),
    ("hükümsüz doğrulama", validator.check_report, GOOD_REPORT.replace("KABUL", "tamam"), False),
    ("geçerli karantina", validator.check_quarantine, GOOD_QUARANTINE, True),
    ("agent ONAYLANDI veremez", validator.check_quarantine, GOOD_QUARANTINE.replace("KARANTINADA", "ONAYLANDI"), False),
    ("kaynaksız karantina", validator.check_quarantine, GOOD_QUARANTINE.replace("kaynak: https://nvd.nist.gov/vuln/detail/CVE-2024-6387\n", ""), False),
    ("frontmatter yok", validator.check_quarantine, "# başlık", False),
]


def raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    return False


def gate_with(policy, tool, **tool_input):
    """Süreç başlatmadan, verilen politikayla Policy Gate kararı."""
    data = {"tool_name": tool, "tool_input": tool_input}
    return policy_gate.evaluate(data, policy, govlib.registered_skills(), govlib.rel_path).decision


def path_checks():
    """paths.json ve '@anahtar' çözümlemesi: (açıklama, sonuç)."""
    root = ROOT.resolve()
    yield "tüm yollar proje içinde", all(P(k).resolve().is_relative_to(root) for k in govlib.paths())
    policy = govlib.load_policy()
    refs = policy["paths"]["deny_write"] + policy["paths"]["ask_write"] + policy["deny_commands"]
    yield "politikada çözülmemiş @anahtar kalmaz", not any(r.startswith("@") for r in refs)
    registry_refs = [s["cikti"] for s in govlib.load_json(P("skills_registry"))["skills"]]
    registry_refs += [y for a in govlib.load_json(P("agents_registry"))["agents"] for y in a["yazar"]]
    yield "reyestrlerdeki @anahtar'lar tanımlı", all(r[1:] in govlib.paths() for r in registry_refs if r.startswith("@"))
    for label, value in (("'..' ile dışarı çıkan", "../disari"), ("mutlak", "/etc"), ("sürücü harfli", "C:/x"),
                         ("ters bölülü", "a\\b"), ("boş", "")):
        yield f"{label} yol reddedilir", raises(lambda v=value: govlib.parse_paths({"dirs": {"x": v}, "files": {}}), ValueError)
    yield "aynı anahtar iki kez tanımlanamaz", raises(
        lambda: govlib.parse_paths({"dirs": {"x": "a"}, "files": {"x": "b"}}), ValueError)
    yield "tanımsız @anahtar hata verir", raises(lambda: govlib.resolve("@yok"), KeyError)

    # Onaylı bilgi klasörü taşınırsa yazma yasağı yeni yere geçer; eski yer artık korumalı değildir.
    saved = govlib.paths()
    try:
        govlib._paths = dict(saved, approved=("dirs", "arsiv/onayli"))
        moved = govlib.load_policy()
        yield "taşınan klasörde koruma sürer", gate_with(moved, "Write", file_path=str(ROOT / "arsiv/onayli/x.md")) == "deny"
        yield "eski konum korumadan çıkar", gate_with(moved, "Write", file_path=str(ROOT / saved["approved"][1] / "x.md")) == "pass"
    finally:
        govlib._paths = saved


def panel_checks():
    """build_site: bozuk satır raporlama, güvenli gömme, şablon kontrolü: (açıklama, sonuç)."""
    tmp = Path(tempfile.mkdtemp(prefix="gov_panel_"))
    try:
        audit = tmp / "audit.jsonl"
        evil = "command=echo '</script><script>alert(1)</script>'"
        lines = [
            json.dumps({"ts": "2026-10-25T15:00:00+00:00", "event": "PreToolUse", "tool": "Bash",
                        "decision": "deny", "reason": "DENY: test", "detail": evil}),
            "{bozuk json",
            "",
            "[1, 2]",
            json.dumps({"ts": "2026-10-25T15:01:00+00:00", "event": "Validator", "tool": "Write", "decision": "kabul"}),
        ]
        audit.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out = tmp / "site" / "index.html"
        counts = build_site.build(audit, P("panel_template"), out)
        html = out.read_text(encoding="utf-8")
        m = re.search(r'<script type="application/json" id="panel-data">(.*?)</script>', html, re.S)
        data = json.loads(m.group(1)) if m else {}
        yield "geçerli satırlar okunur, bozuklar sayılır", counts == (2, 2)
        yield "bozuk satırların numarası raporlanır", [e["line"] for e in data.get("errors", [])] == [2, 4]
        yield "kayıttaki </script> sayfayı kıramaz", html.count("</script>") == 2 and "<script>alert" not in html
        yield "gömülü veri aslına sadık", bool(data) and data["records"][0]["detail"] == evil
        yield "eksik alanlar boş metin olur", bool(data) and data["records"][1]["reason"] == ""
        yield "dış kaynak yüklenmez", not re.search(r"""(src|href)\s*=\s*["']?(https?:)?//""", html)
        bad_template = tmp / "sablon.html"
        bad_template.write_text("<html></html>", encoding="utf-8")
        yield "yer tutucusuz şablon reddedilir", raises(lambda: build_site.build(audit, bad_template, tmp / "x.html"), ValueError)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


CONCURRENT_WRITER = """
import os, sys
sys.path.insert(0, sys.argv[1])
import govlib
for i in range(int(sys.argv[2])):
    govlib.audit("Test", "yazici", "pass", "", f"{os.getpid()}-{i}", {"session_id": f"s{os.getpid()}"})
"""


def audit_checks():
    """Hash zinciri, oturum kimliği, yalnızca-ekleme ve onay kaydı kontrolleri: (açıklama, sonuç)."""
    tmp = Path(tempfile.mkdtemp(prefix="gov_audit_"))
    saved = os.environ.get("GOV_AUDIT_LOG")
    try:
        log, approved = tmp / "audit.jsonl", tmp / "approved"
        approved.mkdir()
        legacy = json.dumps({"ts": "2026-10-25T10:00:00+00:00", "event": "PreToolUse", "decision": "pass"})
        log.write_text(legacy + "\n", encoding="utf-8")
        os.environ["GOV_AUDIT_LOG"] = str(log)
        for i in range(4):
            govlib.audit("PreToolUse", "Bash", "pass", "", f"komut {i}", {"session_id": "oturum-a", "agent_type": "log-analyst"})
        lines = log.read_text(encoding="utf-8").splitlines()
        recs = [json.loads(ln) for ln in lines]
        yield "eski kayıtlar zincire bağlanır", recs[1]["prev"] == govlib.line_hash(legacy)
        yield "oturum ve agent kaydedilir", recs[2]["session"] == "oturum-a" and recs[2]["agent"] == "log-analyst"
        yield "sağlam zincir hatasız", verify_audit.verify(log, approved)[1] == []

        def verify_text(text, base=None):
            bad = tmp / "bozuk.jsonl"
            bad.write_text(text, encoding="utf-8")
            return verify_audit.verify(bad, approved, base)[1]

        yield "değiştirilen satır bulunur", bool(verify_text("\n".join(lines).replace("komut 1", "komut X") + "\n"))
        yield "silinen satır bulunur", bool(verify_text("\n".join(lines[:2] + lines[3:]) + "\n"))
        yield "CRLF satır sonu zinciri bozmaz", verify_text("\r\n".join(lines) + "\r\n") == []
        base = ("\n".join(lines[:3]) + "\n").encode("utf-8")
        yield "ekleme ile büyüyen kayıt geçer", verify_audit.verify(log, approved, base)[1] == []
        yield "tabanı değiştirilmiş kayıt reddedilir", bool(verify_audit.verify(log, approved, base.replace(b"komut 0", b"komut Y"))[1])
        yield "kısalan kayıt reddedilir", bool(verify_text("\n".join(lines[:2]) + "\n", log.read_bytes()))

        (approved / "x.md").write_text("x", encoding="utf-8")
        yield "onaysız eklenen bilgi bulunur", bool(verify_audit.verify(log, approved)[1])
        govlib.audit("Approve", "approve.py", "onaylandi", "onaylayan=test", "x.md")
        yield "Approve kaydı olan bilgi geçer", verify_audit.verify(log, approved)[1] == []

        par = tmp / "paralel.jsonl"
        env = dict(os.environ, GOV_AUDIT_LOG=str(par))
        procs = [subprocess.Popen([sys.executable, "-c", CONCURRENT_WRITER, str(HOOKS), "50"], env=env) for _ in range(8)]
        codes = [p.wait(timeout=120) for p in procs]
        n, errs = verify_audit.verify(par, approved / "yok")
        yield "paralel yazan 8 süreç zinciri çatallamaz", codes == [0] * 8 and n == 400 and errs == []
    finally:
        if saved is None:
            os.environ.pop("GOV_AUDIT_LOG", None)
        else:
            os.environ["GOV_AUDIT_LOG"] = saved
        shutil.rmtree(tmp, ignore_errors=True)


def cloud_checks():
    """Bulut oturumu kuralları (CLAUDE_CODE_REMOTE=true): (açıklama, sonuç)."""
    cloud, local = {"CLAUDE_CODE_REMOTE": "true"}, {}
    have = lambda dep: f"/usr/bin/{dep}"  # noqa: E731
    lack_bwrap = lambda dep: None if dep == "bwrap" else f"/usr/bin/{dep}"  # noqa: E731

    def decide(tool, env, which, **tool_input):
        v = policy_gate.evaluate({"tool_name": tool, "tool_input": tool_input}, govlib.load_policy(),
                                 govlib.registered_skills(), govlib.rel_path, govlib.registered_agents())
        return policy_gate.apply_cloud_rules(v, tool, env, which).decision

    yield "bulutta ASK reddedilir", decide("Bash", cloud, have, command="curl https://example.com") == "deny"
    yield "bulutta kayıt dışı skill reddedilir", decide("Skill", cloud, have, skill="random-skill") == "deny"
    yield "yerelde ASK onaya düşmeye devam eder", decide("Bash", local, have, command="curl https://example.com") == "ask"
    yield "bulutta sandbox paketi yoksa kabuk reddedilir", decide("Bash", cloud, lack_bwrap, command="ls") == "deny"
    yield "bulutta sandbox paketleri varsa zararsız komut geçer", decide("Bash", cloud, have, command="ls") == "pass"
    yield "sandbox paketi kontrolü yalnızca kabuk araçlarına uygulanır", decide(
        "Read", cloud, lack_bwrap, file_path=str(P("samples") / "auth.log")) == "pass"
    yield "yerelde sandbox paketi aranmaz", decide("Bash", local, lack_bwrap, command="ls") == "pass"
    setup = (P("tools") / "cloud_setup.sh").read_text(encoding="utf-8")
    yield "kurulum betiği bubblewrap ve socat kurar", "bubblewrap" in setup and "socat" in setup
    yield "kurulum betiği her durumda 0 ile çıkar", setup.rstrip().endswith("exit 0")


def settings_checks():
    """.claude/settings.json: sandbox ve yazma yasakları paths.json ile uyumlu mu: (açıklama, sonuç)."""
    settings = govlib.load_json(ROOT / ".claude" / "settings.json")
    deny = settings.get("permissions", {}).get("deny", [])
    sandbox = settings.get("sandbox", {})
    yield "sandbox açık, sandbox dışı kaçış kapalı", sandbox.get("enabled") is True and sandbox.get("allowUnsandboxedCommands") is False
    # Yerel Windows'ta sandbox yok; true olursa Claude Code orada hiç açılmaz.
    yield "failIfUnavailable Windows'u kilitlemez", sandbox.get("failIfUnavailable") is not True
    yield "denetim kaydına yazma işletim sistemi düzeyinde yasak", f"Edit(/{R('audit_log')})" in deny
    yield "onaylı bilgiye yazma işletim sistemi düzeyinde yasak", f"Edit(/{R('approved')}**)" in deny


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    failures = 0

    def report(ok, label, detail=""):
        nonlocal failures
        failures += not ok
        print(f"{'GEÇTİ ' if ok else 'KALDI '} {label}{'  → ' + detail if detail else ''}")

    print("== Policy Gate ==")
    for label, tool, inp, expected in GATE_CASES:
        got = gate(tool, **inp)
        report(got == expected, label, "" if got == expected else f"beklenen {expected}, gelen {got}")

    out = run_hook("policy_gate.py", "bozuk json")
    got = out["hookSpecificOutput"]["permissionDecision"] if out else "pass"
    report(got == "deny", "bozuk girdide fail-closed", "" if got == "deny" else f"gelen {got}")

    print("== Validator ==")
    for label, check, text, should_pass in VALIDATOR_CASES:
        errors = check(text)
        report((not errors) == should_pass, label, "; ".join(errors) if (not errors) != should_pass else "")

    # Uçtan uca: rapor klasörüne bozuk rapor yazıldığında PostToolUse engellemeli.
    tmp = P("reports") / "_test_gecici.md"
    tmp.parent.mkdir(exist_ok=True)
    try:
        tmp.write_text("# Eksik rapor\n", encoding="utf-8")
        out = run_hook("validator.py", {"hook_event_name": "PostToolUse", "tool_name": "Write",
                                        "tool_input": {"file_path": str(tmp)}})
        report(bool(out) and out.get("decision") == "block", "PostToolUse bozuk raporu engeller")
        out = run_hook("validator.py", {"hook_event_name": "Stop", "stop_hook_active": False})
        report(bool(out) and out.get("decision") == "block", "Stop bozuk rapor varken bitirmeyi engeller")
        out = run_hook("validator.py", {"hook_event_name": "Stop", "stop_hook_active": True})
        report(bool(out) and "systemMessage" in out, "Stop ikinci denemede döngüye girmez, kullanıcıyı uyarır")
    finally:
        tmp.unlink(missing_ok=True)

    out = run_hook("validator.py", {"hook_event_name": "PostToolUse", "tool_name": "WebFetch", "tool_input": {}})
    report(bool(out) and "additionalContext" in out.get("hookSpecificOutput", {}), "Web içeriği karantina uyarısı")
    notice = (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")
    report(R("quarantine") in notice and R("approved") in notice, "Karantina uyarısı yolları paths.json'dan alır")

    print("== Yollar (paths.json) ==")
    for label, ok in path_checks():
        report(ok, label)

    print("== Panel ==")
    for label, ok in panel_checks():
        report(ok, label)

    print("== Denetim kaydı bütünlüğü ==")
    for label, ok in audit_checks():
        report(ok, label)

    print("== Sandbox ayarları ==")
    for label, ok in settings_checks():
        report(ok, label)

    print("== Bulut oturumu ==")
    for label, ok in cloud_checks():
        report(ok, label)

    print(f"\nSonuç: {failures} başarısız" if failures else "\nSonuç: tüm testler geçti")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
