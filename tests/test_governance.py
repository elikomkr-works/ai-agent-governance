"""Policy Gate ve Validator hook'larının kabul testleri.

Çalıştırma: python tests/test_governance.py
Hook'lar gerçek süreç olarak çalıştırılır; denetim kaydı geçici dosyaya yazılır.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))
import validator  # noqa: E402

ENV = dict(os.environ, GOV_AUDIT_LOG=str(Path(tempfile.gettempdir()) / "gov_test_audit.jsonl"))


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
    ("kapsam dışı ping onaya düşer", "Bash", {"command": "ping -c 1 1.1.1.1"}, "ask"),
    ("kapsam içi ping serbest", "PowerShell", {"command": "ping localhost"}, "pass"),
    ("hedefsiz tarayıcı", "PowerShell", {"command": "Test-NetConnection server01"}, "ask"),
    ("yasak araç", "Bash", {"command": "sqlmap -u http://localhost/?id=1"}, "deny"),
    ("yasak araç python -m ile", "Bash", {"command": "python -m hashcat hashes.txt"}, "deny"),
    ("kapsam dışı HTTP", "Bash", {"command": "curl https://example.com"}, "ask"),
    ("kapsam içi HTTP", "Bash", {"command": "curl http://localhost:8080/health"}, "pass"),
    ("yıkıcı komut", "Bash", {"command": "rm -rf build"}, "ask"),
    ("yıkıcı PowerShell", "PowerShell", {"command": "Remove-Item -Path tmp -Recurse"}, "ask"),
    ("onay betiğini çalıştırma", "Bash", {"command": "python tools/approve.py knowledge/quarantine/a.md"}, "deny"),
    ("onaylı bilgiye yazma", "Write", {"file_path": str(ROOT / "knowledge" / "approved" / "x.md")}, "deny"),
    ("onaylı bilgiye kabukla kopyalama", "Bash", {"command": "cp a.md knowledge/approved/a.md"}, "deny"),
    ("dosya adında 'governance' geçmesi yanlış alarm değil", "PowerShell",
     {"command": "New-Item -ItemType Directory -Force reports; python tests/test_governance.py"}, "pass"),
    ("mutlak yolla politika üzerine yazma", "Bash",
     {"command": f"echo x > '{ROOT.as_posix()}/governance/policy.json'"}, "ask"),
    ("onaylı bilgiyi okuma serbest", "Bash", {"command": "cat knowledge/approved/a.md 2>/dev/null"}, "pass"),
    ("denetim kaydına yazma", "Edit", {"file_path": "governance/audit.jsonl"}, "deny"),
    ("politika değişikliği", "Edit", {"file_path": "governance/policy.json"}, "ask"),
    ("hook değişikliği", "Write", {"file_path": str(ROOT / ".claude" / "hooks" / "policy_gate.py")}, "ask"),
    ("rapor yazma serbest", "Write", {"file_path": str(ROOT / "reports" / "r.md")}, "pass"),
    ("gizli dosya okuma", "Read", {"file_path": str(ROOT / ".env")}, "ask"),
    ("SSH anahtarı okuma", "Bash", {"command": "cat ~/.ssh/id_rsa"}, "ask"),
    ("normal dosya okuma", "Read", {"file_path": str(ROOT / "samples" / "auth.log")}, "pass"),
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

    # Uçtan uca: reports/ altına bozuk rapor yazıldığında PostToolUse engellemeli.
    tmp = ROOT / "reports" / "_test_gecici.md"
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

    print(f"\nSonuç: {failures} başarısız" if failures else "\nSonuç: tüm testler geçti")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
