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
import denial_log  # noqa: E402

sys.path.insert(0, str(govlib.path("tools")))
import build_site  # noqa: E402
import verify_audit  # noqa: E402
import new_customer  # noqa: E402

ENV = dict(os.environ, GOV_AUDIT_LOG=str(Path(tempfile.gettempdir()) / "gov_test_audit.jsonl"))
# Hook vakaları yerel davranışı sınar; bulut kuralları cloud_checks() içinde ayrıca sınanır.
ENV.pop("CLAUDE_CODE_REMOTE", None)
P = govlib.path
R = govlib.rel


def run_hook(script, payload, env=None):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run([sys.executable, str(HOOKS / script)], input=raw.encode("utf-8"),
                          capture_output=True, env=env or ENV, timeout=30)
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
    ("denetim dilimine yazma", "Write", {"file_path": R("audit_archive") + "x.jsonl"}, "deny"),
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
    ("kanıt klasörüne yazma", "Write", {"file_path": str(P("evidence") / "web01" / "x.md")}, "deny"),
    ("kanıt dosyası düzenleme", "Edit", {"file_path": R("evidence") + "/web01/crontab_root.txt"}, "deny"),
    ("kanıt dosyasına izin verme", "Bash", {"command": f"chmod +x {R('evidence')}/web01/x.sh.kanit"}, "deny"),
    ("kanıt hash'ini dosyaya yönlendirme", "Bash",
     {"command": f"sha256sum {R('evidence')}/web01/x.sh.kanit > reports/h.txt"}, "deny"),
    ("kanıtı kabukla kopyalama", "Bash", {"command": f"cp a.txt {R('evidence')}/web01/"}, "deny"),
    ("kanıt okuma serbest", "Read", {"file_path": str(P("evidence") / "web01" / "ps.txt")}, "pass"),
    ("kanıt hash'i serbest", "Bash", {"command": f"sha256sum {R('evidence')}/web01/x.sh.kanit"}, "pass"),
    ("kayıtlı olay müdahale skill'i", "Skill", {"skill": "incident-response"}, "pass"),
    ("kayıtlı olay müdahale agent'ı", "Agent", {"subagent_type": "incident-responder", "prompt": "x"}, "pass"),
    ("kanıt betiğini çalıştırma", "Bash", {"command": f"bash {R('evidence')}web01/x.sh.kanit"}, "deny"),
    ("kanıtı source etme", "Bash", {"command": f"source {R('evidence')}web01/x.sh.kanit"}, "deny"),
    ("kanıtı pipe ile kabuğa verme", "Bash", {"command": f"grep '' {R('evidence')}web01/x.sh.kanit | sh"}, "deny"),
    ("kanıt klasörüne cd ile çalıştırma", "Bash", {"command": f"cd {R('evidence')}web01 && ./x.sh.kanit"}, "deny"),
    ("tek & ile kanıt zinciri", "Bash", {"command": f"sha256sum {R('evidence')}a & bash {R('evidence')}x"}, "deny"),
    ("kanıtı mutlak yolla çalıştırma", "Bash", {"command": f"python '{P('evidence').as_posix()}/web01/a.py'"}, "deny"),
    ("klasör adı olmadan .kanit çalıştırma", "Bash", {"command": "sh /tmp/x.sh.kanit"}, "deny"),
    ("kanıtta komut ikamesi", "Bash", {"command": f"grep $(cat {R('evidence')}web01/a) b"}, "deny"),
    ("kanıt satır sayımı serbest", "Bash", {"command": f"wc -l {R('evidence')}web01/crontab_root.txt"}, "pass"),
    ("kanıt araması serbest", "Bash", {"command": f"grep -c ssh-rsa {R('evidence')}web01/ssh_keys.txt"}, "pass"),
    ("PowerShell kanıt hash'i serbest", "PowerShell",
     {"command": "Get-FileHash -Algorithm SHA256 " + R("evidence").replace("/", "\\") + "web01\\x.sh.kanit"}, "pass"),
    ("kanıtı anmayan komut kısıtlanmaz", "Bash", {"command": "python tests/test_governance.py"}, "pass"),
    ("klasöre adıyla cd kısıtlanır", "Bash", {"command": f"cd {R('evidence').rstrip('/')} && ./x"}, "deny"),
    ("klasörü değişkene atama kısıtlanır", "Bash",
     {"command": f"D={R('evidence').rstrip('/')}; bash $D/x"}, "deny"),
    ("koddaki klasör adı da kısıtlanır", "Bash",
     {"command": f"python -c \"import subprocess; subprocess.run(['bash','x.sh'], cwd='{R('evidence').rstrip('/')}')\""},
     "deny"),
    ("-c içinde klasöre kopyalama", "Bash", {"command": f"bash -c \"cp x.sh {R('evidence').rstrip('/')}\""}, "deny"),
    ("klasör adına yapışık yönlendirme", "Bash", {"command": f"cp x.sh {R('evidence').rstrip('/')}<in.txt"}, "deny"),
    ("klasör adı ikame içinde", "Bash", {"command": f"cp x $(echo {R('evidence').rstrip('/')})"}, "deny"),
    ("klasör adı glob ile", "Bash", {"command": f"cp x.sh {R('evidence').rstrip('/')}*"}, "deny"),
    ("PowerShell -Param:klasör", "PowerShell",
     {"command": f"Copy-Item x.sh -Destination:{R('evidence').rstrip('/')}"}, "deny"),
]

AGENT_SHELL_CASES = [
    # (açıklama, agent_type, komut, beklenen) — policy.json → agent_shell
    ("IR agent'ı hash alabilir", "incident-responder", "sha256sum samples/ir-web01/x.sh.kanit", "pass"),
    ("IR agent'ı zincirde izinli araçlar", "incident-responder", "ls samples && wc -l samples/auth.log", "pass"),
    ("IR agent'ı python çalıştıramaz", "incident-responder", "python tests/test_governance.py", "deny"),
    ("IR agent'ı curl çalıştıramaz", "incident-responder", "curl http://localhost", "deny"),
    ("IR agent'ı sudo önekiyle geçemez", "incident-responder", "sudo wc -l samples/auth.log", "deny"),
    ("IR agent'ı izinli araçtan sonra pipe ile geçemez", "incident-responder", "grep x samples/auth.log | sh", "deny"),
    ("IR agent'ı yönlendirme yapamaz", "incident-responder", "sha256sum samples/auth.log > reports/h.txt", "deny"),
    ("listede olmayan agent kısıtlanmaz", "log-analyst", "python tests/test_governance.py", "pass"),
    ("ana oturum (agent_type yok) kısıtlanmaz", "", "python tests/test_governance.py", "pass"),
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

IR_EVIDENCE = """### Kalıcılık
| # | Sonuç | Dosya:satır |
|---|---|---|
| K1 | İZ VAR | crontab_root.txt:3 |
| K2 | İZ YOK | systemd_units.txt |
| K3 | İZ YOK | rc_profile.txt |
| K4 | İZ VAR | ssh_keys.txt:5 |
| K5 | İZ YOK | passwd.txt |
| K6 | İZ YOK | suid_sgid.txt |
- x.sh.kanit `""" + "a" * 64 + "`\n"
GOOD_IR = GOOD_REPORT.replace("- `samples/auth.log:2`\n", IR_EVIDENCE)

VALIDATOR_CASES = [
    ("geçerli olay müdahale raporu", validator.check_ir_report, GOOD_IR, True),
    ("kalıcılık maddesi eksik", validator.check_ir_report, GOOD_IR.replace("| K6 | İZ YOK | suid_sgid.txt |\n", ""), False),
    ("kalıcılık sonucu yazılmamış", validator.check_ir_report, GOOD_IR.replace("| K2 | İZ YOK", "| K2 | bakıldı"), False),
    ("hash'siz olay müdahale raporu", validator.check_ir_report, GOOD_IR.replace("a" * 64, "yok"), False),
    ("KANIT YOK varken KABUL verilemez", validator.check_ir_report, GOOD_IR.replace("| K6 | İZ YOK", "| K6 | KANIT YOK"), False),
    ("KANIT YOK varken BELİRSİZ geçer", validator.check_ir_report,
     GOOD_IR.replace("| K6 | İZ YOK", "| K6 | KANIT YOK").replace("KABUL", "BELİRSİZ"), True),
    ("geçerli rapor", validator.check_report, GOOD_REPORT, True),
    ("bölüm eksik", validator.check_report, GOOD_REPORT.replace("## Kanıt", "## Notlar"), False),
    ("etiketsiz bulgu", validator.check_report, GOOD_REPORT.replace("- [ÖNERİ] ", "- "), False),
    ("boş kanıt", validator.check_report, GOOD_REPORT.replace("- `samples/auth.log:2`", ""), False),
    ("hükümsüz doğrulama", validator.check_report, GOOD_REPORT.replace("KABUL", "tamam"), False),
    ("reviewer kararlı rapor", validator.check_report, GOOD_REPORT + "## Reviewer Kararı\nONAY — tur 1\n", True),
    ("hükümsüz reviewer kararı", validator.check_report, GOOD_REPORT + "## Reviewer Kararı\nbaktı\n", False),
    ("reviewer kararlı karantina", validator.check_quarantine, GOOD_QUARANTINE.replace("ozet:", "reviewer: BEKLİYOR\nozet:"), True),
    ("hükümsüz karantina reviewer", validator.check_quarantine, GOOD_QUARANTINE.replace("ozet:", "reviewer: iyi\nozet:"), False),
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
    registry_refs = [s["output"] for s in govlib.load_json(P("skills_registry"))["skills"]]
    registry_refs += [y for a in govlib.load_json(P("agents_registry"))["agents"] for y in a["writes"]]
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
        yield "bozuk satırların numarası raporlanır", [e["line"] for e in data.get("errors", [])] == ["satır 2", "satır 4"]
        yield "kayıttaki </script> sayfayı kıramaz", html.count("</script>") == 2 and "<script>alert" not in html
        yield "gömülü veri aslına sadık", bool(data) and data["records"][0]["detail"] == evil
        yield "eksik alanlar boş metin olur", bool(data) and data["records"][1]["reason"] == ""
        yield "dış kaynak yüklenmez", not re.search(r"""(src|href)\s*=\s*["']?(https?:)?//""", html)
        arch = tmp / "arsiv"
        arch.mkdir()
        (arch / f"20261026T120000Z_yerel_{govlib.line_hash(lines[0])[:12]}.jsonl").write_text(lines[0] + "\n", encoding="utf-8")
        yield "yayınlanmış satır iki kez sayılmaz", build_site.build(audit, P("panel_template"), out, arch) == (2, 2)
        yield "canlı kayıt olmadan dilimlerden üretilir", build_site.build(tmp / "yok.jsonl", P("panel_template"), out, arch) == (1, 0)
        reps, quar, appr = tmp / "raporlar", tmp / "karantina", tmp / "onayli"
        for d in (reps, quar):
            d.mkdir()
        (reps / "a.md").write_text(GOOD_REPORT.replace("**", "") + "## Reviewer Kararı\nDÜZELTME GEREKLİ — tur 1, RED değil\n",
                                   encoding="utf-8")
        (reps / "b.md").write_text("# </script><script>alert(2)</script>\n## Kapsam\n", encoding="utf-8")
        (quar / "c.md").write_text(GOOD_QUARANTINE.replace("ozet:", "reviewer: ONAY\nozet:"), encoding="utf-8")
        build_site.build(audit, P("panel_template"), out, arch, reps, quar, appr)
        html = out.read_text(encoding="utf-8")
        m = re.search(r'<script type="application/json" id="panel-data">(.*?)</script>', html, re.S)
        data = json.loads(m.group(1)) if m else {}
        a, b = data.get("reports", [{}, {}])
        yield "rapor kararları okunur", (a.get("status"), a.get("review")) == ("KABUL", "DÜZELTME GEREKLİ")
        yield "etiketli maddeler sayılır", a.get("labels") == {"OLGU": 1, "ÖNERİ": 1, "DOĞRULANMAMIŞ": 0}
        yield "eksik raporun validator hatası taşınır", bool(b.get("errors")) and b.get("review") == ""
        yield "rapor başlığındaki </script> sayfayı kıramaz", "<script>alert(2)" not in html
        kn = data.get("knowledge", [])
        yield "karantina kaydı okunur, olmayan onaylı klasör hata vermez", \
            [(k["place"], k["status"], k["review"]) for k in kn] == [("quarantine", "KARANTINADA", "ONAY")]
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


def slice_checks():
    """Dilimli denetim kaydı: publish_audit yazımı ve verify_audit dilim kontrolleri: (açıklama, sonuç)."""
    import publish_audit
    from datetime import datetime, timedelta, timezone
    tmp = Path(tempfile.mkdtemp(prefix="gov_slice_"))
    saved = os.environ.get("GOV_AUDIT_LOG")
    t0 = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    try:
        log, arch, approved = tmp / "audit.jsonl", tmp / "arsiv", tmp / "approved"
        os.environ["GOV_AUDIT_LOG"] = str(log)
        write = lambda n, tag: [govlib.audit("PreToolUse", "Bash", "pass", "", f"{tag} {i}", {"session_id": "s"}) for i in range(n)]

        def check(base_raw=None, base_slices=None, live=log):
            return verify_audit.verify(live, approved, base_raw, arch, base_slices)

        write(3, "ilk")
        legacy = log.read_bytes()
        out1, n1, e1 = publish_audit.publish(log, arch, approved, "yerel", t0)
        yield "ilk dilim tüm satırları alır", n1 == 3 and e1 == [] and verify_audit.SLICE_NAME.match(out1.name)
        write(2, "ikinci")
        out2, n2, _ = publish_audit.publish(log, arch, approved, "yerel", t0 + timedelta(seconds=1))
        yield "ikinci dilim yalnızca yeni satırları alır", n2 == 2 and out2.read_bytes().count(b"\n") == 2
        yield "yeni kayıt yoksa dilim yazılmaz", publish_audit.publish(log, arch, approved, "yerel", t0)[0] is None
        n, errs = check()
        yield "dilimler + canlı kayıt hatasız, satırlar bir kez sayılır", errs == [] and n == 5
        yield "canlı kayıt olmadan (CI) dilimler hatasız", check(live=tmp / "yok.jsonl") == (5, [])
        yield "eski izlenen kayıt dilimlerin başıysa geçer", check(base_raw=legacy, live=tmp / "yok.jsonl")[1] == []

        base = {p.name: p.read_bytes() for p in arch.iterdir()}
        out2.write_bytes(out2.read_bytes().replace(b"ikinci 0", b"ikinci X"))
        yield "değiştirilen dilim bulunur (zincir)", bool(check()[1])
        yield "değiştirilen dilim bulunur (taban)", any("değiştirilmiş" in e for e in check(base_slices=base)[1])
        out2.write_bytes(base[out2.name])
        out2.unlink()
        yield "silinen dilim bulunur (taban)", any("silinmiş" in e for e in check(base_slices=base)[1])
        out2.write_bytes(base[out2.name])
        out1.rename(arch / out1.name.replace("120000Z", "115959Z").replace(out1.name[23:35], "0" * 12))
        yield "logid ilk satırla eşleşmezse bulunur", any("logid" in e for e in check()[1])
        (arch / out1.name).write_bytes(base[out1.name])
        for p in arch.glob("*_000000000000.jsonl"):
            p.unlink()
        (arch / "rastgele.jsonl").write_text("{}\n", encoding="utf-8")
        yield "biçimsiz dilim adı bulunur", any("biçime uymuyor" in e for e in check()[1])
        (arch / "rastgele.jsonl").unlink()

        log.write_bytes(log.read_bytes().replace(b"ilk 1", b"ilk Y"))
        yield "yayınlanmış satırı değişen canlı kayıt bulunur", any("uyuşmuyor" in e for e in check()[1])
        yield "hatalı canlı kayıt yayınlanmaz", publish_audit.publish(log, arch, approved, "yerel", t0 + timedelta(seconds=9))[0] is None
    finally:
        if saved is None:
            os.environ.pop("GOV_AUDIT_LOG", None)
        else:
            os.environ["GOV_AUDIT_LOG"] = saved
        shutil.rmtree(tmp, ignore_errors=True)


def tool_turn(tid, name, inp, text, decision=None, is_error=True):
    """Transcript'te bir araç çağrısı ve sonucu (Claude Code'un JSONL biçimi)."""
    use = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}}
    res = {"type": "user", "timestamp": "2026-10-26T10:00:00Z",
           "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": is_error}]}}
    if decision:
        res["permissionDecision"] = decision
    return json.dumps(use) + "\n" + json.dumps(res) + "\n"


def denial_checks():
    """İzin sistemi retlerinin (hook'a ulaşmayan) denetim kaydına düşmesi: (açıklama, sonuç)."""
    tmp = Path(tempfile.mkdtemp(prefix="gov_denial_"))
    try:
        log, transcript = tmp / "audit.jsonl", tmp / "oturum.jsonl"
        env = dict(ENV, GOV_AUDIT_LOG=str(log))
        transcript.write_text("".join([
            tool_turn("t1", "Edit", {"file_path": ".git/config"}, "File is in a directory that is denied by your permission settings.",
                      {"decision": "reject", "source": "config", "reasonType": "rule", "reasonCode": "rule:projectSettings"}),
            tool_turn("t2", "Bash", {"command": "rm -rf build"}, "Permission for this action was denied by the Claude Code auto mode classifier.",
                      {"decision": "reject", "source": "config", "reasonType": "classifier", "reasonCode": "classifier:auto-mode"}),
            tool_turn("t3", "Bash", {"command": "nmap 8.8.8.8"}, "PreToolUse:Bash hook error: [Policy Gate] DENY",
                      {"decision": "reject", "source": "hook", "reasonCode": "hook:PreToolUse"}),
            tool_turn("t4", "Bash", {"command": "ls"}, "a.txt", {"decision": "accept", "source": "config"}, is_error=False),
            tool_turn("t5", "Write", {"file_path": "x.md"}, "The user doesn't want to proceed with this tool use."),
            tool_turn("t6", "Bash", {"command": "false"}, "Exit code 1"),
            "bozuk satır tool_result\n",
        ]), encoding="utf-8")

        def records():
            if not log.exists():
                return []
            return [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines()]

        def ids():
            return sorted(i for r in records() for i in re.findall(r"tool_use_id=(\S+)", r["detail"]))

        stop = {"hook_event_name": "Stop", "session_id": "s1", "transcript_path": str(transcript)}
        run_hook("denial_log.py", stop, env)
        yield "deny kuralı, sınıflandırıcı ve kullanıcı retleri kaydedilir", ids() == ["t1", "t2", "t5"]
        yield "Gate retleri, kabul edilenler ve sıradan hatalar kaydedilmez", len(records()) == 3
        t1 = next((r for r in records() if "tool_use_id=t1 " in r["detail"]), {})
        yield "kayıtta araç, girdi ve gerekçe kodu var", (
            t1.get("event") == "Permission" and t1.get("decision") == "deny" and t1.get("tool") == "Edit"
            and ".git/config" in t1.get("detail", "") and t1.get("reason", "").startswith("rule:projectSettings"))
        yield "deny kuralı retlerinde eşleşen kural yazılır", "[kural: Edit(/.git/config)]" in t1.get("reason", "")
        match = denial_log.matching_rule
        yield "Edit kuralı Write çağrısını da kapsar", match(
            "rule:projectSettings", "Write", {"file_path": str(ROOT / ".git/hooks/pre-commit")}, ROOT) == "Edit(/.git/hooks/**)"
        yield "kural dışı yol için kural yazılmaz", match("rule:projectSettings", "Edit", {"file_path": "README.md"}, ROOT) == ""
        rule = denial_log.rule_matches
        yield "Bash önek ve joker kuralları eşleşir", (
            rule("Bash(curl:*)", "Bash", {"command": "curl -s x"}, ROOT, ROOT)
            and not rule("Bash(curl:*)", "Bash", {"command": "curlx"}, ROOT, ROOT)
            and rule("Bash(git push*)", "Bash", {"command": "git push origin"}, ROOT, ROOT))
        run_hook("denial_log.py", stop, env)
        yield "tekrar taramada aynı ret ikinci kez yazılmaz", len(records()) == 3
        denied = {"hook_event_name": "PermissionDenied", "session_id": "s1", "tool_name": "Bash", "reason": "[Kural]"}
        run_hook("denial_log.py", dict(denied, tool_use_id="t2", tool_input={"command": "x"}), env)
        yield "PermissionDenied, taramada yazılan reddi tekrarlamaz", len(records()) == 3
        run_hook("denial_log.py", dict(denied, tool_use_id="t9", tool_input={"command": "curl x"}), env)
        last = records()[-1]
        yield "PermissionDenied anında kaydedilir", "tool_use_id=t9" in last["detail"] and last["reason"].startswith("classifier:auto-mode")

        sub = tmp / "agent-a1.jsonl"
        sub.write_text(tool_turn("s7", "Edit", {"file_path": "knowledge/approved/a.md"}, "denied by your permission settings"),
                       encoding="utf-8")
        run_hook("denial_log.py", {"hook_event_name": "SubagentStop", "session_id": "s1", "agent_type": "log-analyst",
                                   "transcript_path": str(transcript), "agent_transcript_path": str(sub)}, env)
        last = records()[-1]
        yield "alt agent retleri agent adıyla kaydedilir", "tool_use_id=s7" in last["detail"] and last["agent"] == "log-analyst"
        yield "kayıtlar hash zincirini bozmaz", verify_audit.verify(log, tmp / "yok")[1] == []
        out = run_hook("denial_log.py", {"hook_event_name": "Stop", "transcript_path": str(tmp / "yok.jsonl")}, env)
        yield "transcript yoksa sessizce geçer", out is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cloud_checks():
    """Bulut oturumu kuralları (CLAUDE_CODE_REMOTE=true): (açıklama, sonuç)."""
    cloud, local = {"CLAUDE_CODE_REMOTE": "true"}, {}
    have = lambda dep: f"/usr/bin/{dep}"  # noqa: E731
    lack_bwrap = lambda dep: None if dep == "bwrap" else f"/usr/bin/{dep}"  # noqa: E731

    def decide(tool, env, which, **tool_input):
        v = policy_gate.evaluate({"tool_name": tool, "tool_input": tool_input}, govlib.load_policy(),
                                 govlib.registered_skills(), govlib.rel_path, govlib.registered_agents())
        return policy_gate.apply_cloud_rules(v, tool, tool_input.get("command", ""), env, which).decision

    git_cases = [
        # (açıklama, komut, beklenen) — bulutta, sandbox paketleri kurulu
        ("tek başına git commit geçer", 'git commit -m "Bulut kural testi raporu"', "pass"),
        ("dosyadan mesajla git commit geçer", "git commit -F msg.txt", "pass"),
        ("tek başına git push geçer", "git push -u origin claude/test", "pass"),
        ("zincirlenmiş git commit reddedilir", "git add r.md && git commit -m x", "deny"),
        ("git push sonrası komut reddedilir", "git push origin x; touch ~/a", "deny"),
        ("komut ikamesiyle git commit reddedilir", 'git commit -m "$(cat msg)"', "deny"),
        ("ters tırnakla git commit reddedilir", "git commit -m `id`", "deny"),
        ("yönlendirmeli git commit reddedilir", "git commit -m x > ~/.bashrc", "deny"),
        ("--receive-pack ile git push reddedilir", "git push --receive-pack=evil /tmp/r main", "deny"),
        ("sandbox içindeki git zincirlenebilir", "git status && git log -1", "pass"),
    ]
    for label, command, expected in git_cases:
        yield label, decide("Bash", cloud, have, command=command) == expected
    yield "yerelde git kuralı uygulanmaz", decide("Bash", local, have, command="git add r.md && git commit -m x") == "pass"

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


def ir_collect_checks():
    """tools/ir_collect.sh, skill'in beklenen kanıt tablosunu eksiksiz üretiyor mu: (açıklama, sonuç)."""
    script = (P("tools") / "ir_collect.sh").read_text(encoding="utf-8")
    skill = (ROOT / ".claude" / "skills" / "incident-response" / "SKILL.md").read_text(encoding="utf-8")
    table = skill.split("### Expected evidence", 1)[1].split("\n\n", 2)[1]
    expected = set(re.findall(r"`([\w.]+\.(?:txt|sha256))`", "\n".join(
        line.split("|")[1] for line in table.splitlines() if line.startswith("| `"))))
    produced = set(re.findall(r"^run ([\w.]+\.txt) ", script, re.M)) | {"TOPLAMA_NOTU.txt", "MANIFEST.sha256"}
    yield "toplama betiği beklenen kanıtların hepsini üretir", len(expected) >= 18 and expected <= produced
    yield "toplama betiği toplama notunu ve manifesti yazar", all(f'"$OUT/{f}"' in script for f in ("TOPLAMA_NOTU.txt", "MANIFEST.sha256"))
    code = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))
    yield "toplama betiği shadow ve özel anahtar kopyalamaz", "/etc/shadow" not in code and "shadow | gshadow | id_* | *.pem | *.key)" in script
    yield "toplama betiği ağa çıkmaz", not re.search(r"\b(curl|wget|scp|rsync|nc|ssh|ftp)\s", script)
    yield "toplama betiği eski kanıtın üzerine yazmaz", 'if [ -e "$OUT" ]' in script
    bash = shutil.which("bash")
    if bash:
        yield "toplama betiği sözdizimi geçerli", subprocess.run([bash, "-n", str(P("tools") / "ir_collect.sh")]).returncode == 0
    # Gerçek çalıştırma root ister: CI'da (Linux, parolasız sudo) yapılır, yerelde atlanır.
    if sys.platform.startswith("linux") and subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0:
        out = Path(tempfile.mkdtemp()) / "kanit"
        suspicious = out.parent / "supheli.sh"
        suspicious.write_text("#!/bin/sh\necho test\n", encoding="utf-8")
        run = subprocess.run(["sudo", "-n", "bash", str(P("tools") / "ir_collect.sh"), str(out),
                              "2026-01-01 00:00", "2026-01-02 00:00", str(suspicious)], capture_output=True)
        files = set(subprocess.run(["sudo", "-n", "ls", str(out)], capture_output=True, text=True).stdout.split())
        yield "toplama betiği gerçek sistemde tüm dosyaları üretir", run.returncode == 0 and expected | {"supheli.sh.kanit"} <= files
        yield "toplama betiğinin manifesti doğrulanır", subprocess.run(
            ["sudo", "-n", "sh", "-c", f"cd '{out}' && sha256sum -c --quiet MANIFEST.sha256"]).returncode == 0
        subprocess.run(["sudo", "-n", "rm", "-rf", str(out.parent)])


def win_collect_checks():
    """tools/win_collect.ps1, iki skill'in Windows kanıt tablolarını gizli veri toplamadan üretiyor mu."""
    script = (P("tools") / "win_collect.ps1").read_text(encoding="utf-8")
    skills = ROOT / ".claude" / "skills"
    expected = set()
    for f in (skills / "incident-response" / "windows.md", skills / "config-audit" / "windows-dc.md"):
        rows = [line.split("|")[1] for line in f.read_text(encoding="utf-8").splitlines() if line.startswith("| `")]
        expected |= set(re.findall(r"`([\w.]+\.(?:txt|csv|sha256))`", "\n".join(rows)))
    produced = set(re.findall(r"^\s*(?:if .*\{ )?Save(?:Events)? '([\w.]+)'", script, re.M)) | {"TOPLAMA_NOTU.txt", "MANIFEST.sha256"}
    yield "Windows betiği iki tablodaki kanıtların hepsini üretir", len(expected) >= 50 and expected <= produced
    code = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))
    secret = re.search(r"DefaultPassword|ntds\.dit|lsass|reg save|procdump|comsvcs|-Properties \*|"
                       r"-Properties[^|\n]*(ms-Mcs-AdmPwd|msLAPS-Password(?!ExpirationTime)|msLAPS-Encrypted)|"
                       r"reg query \"\$cv\\Winlogon\"(?! /v)", code, re.I)
    yield "Windows betiği gizli veri toplamaz", secret is None
    yield "Windows betiği ağa çıkmaz", not re.search(
        r"Invoke-WebRequest|Invoke-RestMethod|\biwr\b|Start-BitsTransfer|Net\.WebClient|New-PSSession|-ComputerName|\bcurl\b|\bwget\b", code, re.I)
    yield "Windows betiği eski kanıtın üzerine yazmaz", "if (Test-Path -LiteralPath $Out)" in script
    id_sets = [s.split(",") for s in re.findall(r"@\(([\d,\s]+)\)", code)]
    yield "Windows betiği olay sorgusu başına en çok 23 kimlik kullanır", bool(id_sets) and max(map(len, id_sets)) <= 23
    pwsh = shutil.which("pwsh")
    if pwsh:
        parse = ("$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
                 f"'{P('tools') / 'win_collect.ps1'}',[ref]$t,[ref]$e);exit $e.Count")
        yield "Windows betiği sözdizimi geçerli", subprocess.run([pwsh, "-NoProfile", "-Command", parse]).returncode == 0


def customer_checks():
    """tools/new_customer.py müşteri reposuna yalnızca sistem dosyalarını taşıyor mu: (açıklama, sonuç)."""
    base = Path(tempfile.mkdtemp())
    try:
        target = base / "musteri"
        n, errors = new_customer.build(target, name="Deneme", today="2026-01-01")
        copied = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        yield "müşteri kopyası hatasız üretilir", n > 0 and errors == []
        # Koddaki listeden bağımsız: bir klasör NEVER_COPY'den düşerse test de ona bakmayı bırakmasın.
        must_not = ["audit_archive", "reports", "quarantine", "approved", "proposals", "work", "site", "evidence"]
        yield "kopyalanmayacak veri klasörleri listesi eksiksiz", set(must_not) <= set(new_customer.NEVER_COPY)
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
        if any(f.startswith(R("audit_archive")) for f in tracked) and any(f.startswith(R("reports")) for f in tracked):
            yield "kaynaktaki dilimler ve raporlar müşteri kopyasına geçmez", not any(
                f.startswith((R("audit_archive"), R("reports"))) and not f.endswith("/.gitkeep") for f in copied)
        data = [R(k) for k in must_not]
        yield "veri klasörlerinden yalnızca .gitkeep geçer", all(
            f.endswith("/.gitkeep") for f in copied if any(f.startswith(d) for d in data))
        yield "Hook'lar, kurallar ve testler kopyalanır", {
            ".claude/settings.json", ".claude/hooks/policy_gate.py", R("policy"), "tests/test_governance.py"} <= copied
        yield "beyaz liste dışındaki kök dosyaları kopyalanmaz", all(
            "/" in f or f in {"CLAUDE.md", ".gitignore", ".gitattributes", new_customer.GUIDE} for f in copied)
        wf = (target / new_customer.WORKFLOW).read_text(encoding="utf-8")
        yield "müşteri CI'ında Pages yayını yok, testler var", "pages" not in wf and "test_governance.py" in wf
        yield "müşteri CLAUDE.md'si Pages yayını vaat etmez", new_customer.PAGES_NOTE not in (target / "CLAUDE.md").read_text(encoding="utf-8")
        _, errs = verify_audit.verify(target / R("audit_log"), target / R("approved"), archive_dir=target / R("audit_archive"))
        yield "boş müşteri reposu denetim kaydı kontrolünden geçer", errs == []
        yield "dolu klasöre kurulum reddedilir", new_customer.build(target, name="X")[1] != []
        yield "sistem reposunun içine kurulum reddedilir", new_customer.build(P("work") / "m", name="X")[1] != []
        yield "müşteri reposu olmayan klasör güncellenmez", new_customer.build(base / "yok", update=True)[1] != []
        policy_file = target / R("policy")
        policy = json.loads(policy_file.read_text(encoding="utf-8"))
        policy["scope"]["allowed_targets"].append("10.0.0.5")
        policy_file.write_text(json.dumps(policy), encoding="utf-8")
        (target / R("reports") / "r.md").write_text("müşteri raporu", encoding="utf-8")
        _, errs = new_customer.build(target, update=True, today="2026-02-01")
        kept = json.loads(policy_file.read_text(encoding="utf-8"))["scope"]["allowed_targets"]
        guide = (target / new_customer.GUIDE).read_text(encoding="utf-8")
        yield "güncelleme müşteri kapsamını korur", errs == [] and "10.0.0.5" in kept
        yield "güncelleme müşteri verisine ve kılavuza dokunmaz", (
            (target / R("reports") / "r.md").exists() and "Deneme" in guide and "2026-02-01: sistem güncellendi" in guide)
    finally:
        shutil.rmtree(base, ignore_errors=True)


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
    yield "denetim dilimlerine yazma işletim sistemi düzeyinde yasak", f"Edit(/{R('audit_archive')}**)" in deny
    # Sandbox dışında çalışan git, bu dosyalardaki betikleri çalıştırır.
    yield "git hook ve config yazımı yasak", {"Edit(/.git/hooks/**)", "Edit(/.git/config)"} <= set(deny)
    yield "izin reddi kaydı hook'ları bağlı", all(
        "denial_log.py" in json.dumps(settings.get("hooks", {}).get(e, [])) for e in ("Stop", "SubagentStop", "PermissionDenied"))
    excluded = {c.split()[1] for c in sandbox.get("excludedCommands", [])}
    yield "sandbox dışı git komutları Gate kuralıyla aynı", excluded == policy_gate.GIT_UNSANDBOXED
    # .gitignore'daki sandbox yer tutucuları yönetişim dosyalarını gizlememeli.
    # Canlı kayıt bilerek izlenmez; yayınlanan kısmı dilimlerdedir.
    governed = [".claude/settings.json", ".claude/hooks/policy_gate.py", ".claude/agents/reviewer.md",
                R("audit_archive") + "d.jsonl", R("policy"), R("reports") + "r.md", R("approved") + "a.md"]
    yield "canlı denetim kaydı git'te izlenmez", subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", R("audit_log")], cwd=ROOT).returncode == 0
    ignored = [p for p in governed
               if subprocess.run(["git", "check-ignore", "-q", "--no-index", p], cwd=ROOT).returncode == 0]
    yield "sandbox yer tutucuları yönetişim dosyalarını gizlemez", ignored == []


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

    for label, agent, command, expected in AGENT_SHELL_CASES:
        out = run_hook("policy_gate.py", {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                                          "agent_type": agent, "tool_input": {"command": command}})
        got = out["hookSpecificOutput"]["permissionDecision"] if out else "pass"
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

    # Olay müdahale kontrolü dosya adındaki '_ir_' ile devreye girer: genel rapor olarak geçerli metin burada reddedilir.
    tmp = P("reports") / "_test_ir_gecici.md"
    try:
        tmp.write_text(GOOD_REPORT, encoding="utf-8")
        payload = {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(tmp)}}
        out = run_hook("validator.py", payload)
        report(bool(out) and out.get("decision") == "block", "'_ir_' raporunda kalıcılık tablosu zorunlu")
        tmp.write_text(GOOD_IR, encoding="utf-8")
        report(run_hook("validator.py", payload) is None, "tam olay müdahale raporu geçer")
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

    print("== Denetim kaydı dilimleri ==")
    for label, ok in slice_checks():
        report(ok, label)

    print("== İzin reddi kaydı ==")
    for label, ok in denial_checks():
        report(ok, label)

    print("== Sandbox ayarları ==")
    for label, ok in settings_checks():
        report(ok, label)

    print("== Bulut oturumu ==")
    for label, ok in cloud_checks():
        report(ok, label)

    print("== Kanıt toplama betiği ==")
    for label, ok in ir_collect_checks():
        report(ok, label)
    for label, ok in win_collect_checks():
        report(ok, label)

    print("== Müşteri reposu ==")
    for label, ok in customer_checks():
        report(ok, label)

    print(f"\nSonuç: {failures} başarısız" if failures else "\nSonuç: tüm testler geçti")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
