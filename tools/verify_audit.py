"""Denetim kaydının bütünlüğünü doğrular (salt-okunur).

Kullanım:
    python tools/verify_audit.py [--base <git ref>]

Kontroller:
  1. Her satır bir JSON nesnesidir.
  2. Hash zinciri: 'prev' alanı olan ilk kayıttan sonra her kaydın 'prev'i önceki
     satırın SHA-256 özetine eşittir. Zincirden önceki eski kayıtlar ilk zincirli
     kaydın 'prev'iyle sabitlenir.
  3. --base verilirse: o commit'teki kayıt bugünkünün başıdır (log yalnızca
     eklemeyle büyür; satır silinmez, değiştirilmez).
  4. Onaylı bilgi klasöründeki her dosya için bir Approve/onaylandi kaydı vardır.

Sınır: zincir gizli anahtar kullanmaz; dosyanın tamamını baştan yazan biri zinciri
yeniden hesaplayabilir. Buna karşı çıpa git geçmişidir (3. kontrol, CI'da çalışır).
Hata varsa çıkış kodu 1'dir.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import govlib  # noqa: E402


def read_lines(raw):
    """(satır no, ham satır) çiftleri; boş satırlar atlanır."""
    return [(no, ln.rstrip(b"\r")) for no, ln in enumerate(raw.split(b"\n"), 1) if ln.strip()]


def check_chain(lines):
    errors, records, chained, prev = [], [], False, None
    for no, ln in lines:
        try:
            rec = json.loads(ln)
            if not isinstance(rec, dict):
                raise ValueError("JSON nesnesi değil")
        except ValueError as e:
            errors.append(f"satır {no}: okunamadı ({e})")
            rec = {}
        records.append(rec)
        if "prev" in rec:
            expected = govlib.line_hash(prev) if prev is not None else govlib.GENESIS
            if rec["prev"] != expected:
                errors.append(f"satır {no}: zincir kopuk (önceki satır silinmiş veya değiştirilmiş)")
            chained = True
        elif chained:
            errors.append(f"satır {no}: zincirli kayıtlardan sonra 'prev' alanı yok")
        prev = ln
    return errors, records


def check_append_only(lines, base_raw):
    base = read_lines(base_raw)
    if len(base) > len(lines):
        return [f"kayıt kısalmış: tabanda {len(base)}, şimdi {len(lines)} satır"]
    for (no, old), (_, new) in zip(base, lines):
        if old != new:
            return [f"satır {no}: tabandaki kayıt değiştirilmiş (yalnızca ekleme kuralı)"]
    return []


def check_approvals(records, approved_dir):
    approved = {r.get("detail") for r in records if r.get("event") == "Approve" and r.get("decision") == "onaylandi"}
    if not approved_dir.is_dir():
        return []
    return [f"{govlib.rel('approved')}{p.name}: Approve kaydı yok (kullanıcı onayı olmadan eklenmiş)"
            for p in sorted(approved_dir.iterdir()) if p.is_file() and p.name not in approved]


def git_show(ref, rel):
    proc = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=ROOT, capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def verify(log_path, approved_dir, base_raw=None):
    raw = Path(log_path).read_bytes() if Path(log_path).exists() else b""
    lines = read_lines(raw)
    errors, records = check_chain(lines)
    if base_raw is not None:
        errors += check_append_only(lines, base_raw)
    errors += check_approvals(records, approved_dir)
    return len(lines), errors


def main():
    govlib.setup_io()
    parser = argparse.ArgumentParser(description="Denetim kaydı bütünlük kontrolü")
    parser.add_argument("--base", help="karşılaştırılacak git ref (ör. origin/main veya bir commit)")
    args = parser.parse_args()

    base_raw = None
    if args.base:
        base_raw = git_show(args.base, govlib.rel("audit_log"))
        if base_raw is None:
            print(f"Not: {args.base} içinde {govlib.rel('audit_log')} yok; yalnızca-ekleme kontrolü atlandı.")
    count, errors = verify(govlib.path("audit_log"), govlib.path("approved"), base_raw)
    for e in errors:
        print("HATA ", e)
    print(f"{govlib.rel('audit_log')}: {count} kayıt, {len(errors)} hata")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
