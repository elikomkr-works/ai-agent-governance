"""Denetim kaydının bütünlüğünü doğrular (salt-okunur).

Kullanım:
    python tools/verify_audit.py [--base <git ref>]

Kayıt iki yerde durur:
  - Canlı kayıt (files.audit_log): hook'ların yazdığı yerel dosya; git'te izlenmez.
  - Dilimler (dirs.audit_archive): tools/publish_audit.py'nin canlı kayıttan kestiği,
    yayınlanmış parçalar. Ad: <ts>_<yerel|bulut>_<logid>.jsonl. logid, kaynağın ilk
    satırının SHA-256 özetinin ilk 12 karakteridir; aynı logid'li dilimler ad sırasıyla
    birleştirilince o kaynağın kesintisiz başını verir.

Kontroller:
  1. Her satır bir JSON nesnesidir.
  2. Hash zinciri: 'prev' alanı olan ilk kayıttan sonra her kaydın 'prev'i önceki
     satırın SHA-256 özetine eşittir (canlı kayıtta ve her logid'in birleşik dilimlerinde).
     Zincirden önceki eski kayıtlar ilk zincirli kaydın 'prev'iyle sabitlenir.
  3. Dilim adındaki logid, birleşik dilimin ilk satırıyla eşleşir; canlı kayıt varsa
     kendi logid'inin dilimleri onun başıdır (yayınlanan satır sonradan değişmemiştir).
  4. --base verilirse: o commit'teki her dilim bugün de aynıdır (dilim silinmez,
     değiştirilmez); o commit'te izlenen eski canlı kayıt varsa, bugünkü kaydın başıdır.
  5. Onaylı bilgi klasöründeki her dosya için bir Approve/onaylandi kaydı vardır.

Sınır: zincir gizli anahtar kullanmaz; dosyanın tamamını baştan yazan biri zinciri
yeniden hesaplayabilir. Buna karşı çıpa git geçmişidir (4. kontrol, CI'da çalışır).
Hata varsa çıkış kodu 1'dir.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import govlib  # noqa: E402

SLICE_NAME = re.compile(r"^\d{8}T\d{6}Z_(yerel|bulut)_([0-9a-f]{12})\.jsonl$")


def read_lines(raw, name=None):
    """(konum, ham satır) çiftleri; boş satırlar atlanır. Konum: 'satır N' veya '<ad> satır N'."""
    where = f"{name} satır" if name else "satır"
    return [(f"{where} {no}", ln.rstrip(b"\r")) for no, ln in enumerate(raw.split(b"\n"), 1) if ln.strip()]


def log_id(lines):
    """Kaynağın kimliği: ilk satırın özetinin ilk 12 karakteri (boş kayıtta None)."""
    return govlib.line_hash(lines[0][1])[:12] if lines else None


def check_chain(lines):
    errors, records, chained, prev = [], [], False, None
    for where, ln in lines:
        try:
            rec = json.loads(ln)
            if not isinstance(rec, dict):
                raise ValueError("JSON nesnesi değil")
        except ValueError as e:
            errors.append(f"{where}: okunamadı ({e})")
            rec = {}
        records.append(rec)
        if "prev" in rec:
            expected = govlib.line_hash(prev) if prev is not None else govlib.GENESIS
            if rec["prev"] != expected:
                errors.append(f"{where}: zincir kopuk (önceki satır silinmiş veya değiştirilmiş)")
            chained = True
        elif chained:
            errors.append(f"{where}: zincirli kayıtlardan sonra 'prev' alanı yok")
        prev = ln
    return errors, records


def is_prefix(head, lines):
    return len(head) <= len(lines) and all(a[1] == b[1] for a, b in zip(head, lines))


def check_append_only(lines, base_raw):
    base = read_lines(base_raw)
    if len(base) > len(lines):
        return [f"kayıt kısalmış: tabanda {len(base)}, şimdi {len(lines)} satır"]
    for (where, old), (_, new) in zip(base, lines):
        if old != new:
            return [f"{where}: tabandaki kayıt değiştirilmiş (yalnızca ekleme kuralı)"]
    return []


def load_slices(archive_dir):
    """{logid: birleşik satırlar} ve hatalar; dilimler ad (zaman damgası) sırasıyla birleşir."""
    groups, errors = {}, []
    if archive_dir is None or not Path(archive_dir).is_dir():
        return groups, errors
    for p in sorted(Path(archive_dir).glob("*.jsonl")):
        m = SLICE_NAME.match(p.name)
        if not m:
            errors.append(f"{p.name}: dilim adı biçime uymuyor (<ts>_<yerel|bulut>_<logid>.jsonl)")
            continue
        lines = read_lines(p.read_bytes(), p.name)
        if not lines:
            errors.append(f"{p.name}: boş dilim")
        groups.setdefault(m.group(2), []).extend(lines)
    for lid, lines in groups.items():
        if log_id(lines) != lid:
            errors.append(f"{lines[0][0]}: logid {lid} ilk satırla eşleşmiyor (ilk dilim eksik veya değiştirilmiş)")
    return groups, errors


def check_base_slices(archive_dir, base_slices):
    """Tabandaki her dilim bugün de aynı olmalı."""
    errors = []
    for name, raw in sorted(base_slices.items()):
        p = Path(archive_dir) / name
        if not p.is_file():
            errors.append(f"{name}: tabandaki dilim silinmiş")
        elif read_lines(p.read_bytes()) != read_lines(raw):
            errors.append(f"{name}: tabandaki dilim değiştirilmiş")
    return errors


def check_approvals(records, approved_dir):
    approved = {r.get("detail") for r in records if r.get("event") == "Approve" and r.get("decision") == "onaylandi"}
    if not approved_dir.is_dir():
        return []
    return [f"{govlib.rel('approved')}{p.name}: Approve kaydı yok (kullanıcı onayı olmadan eklenmiş)"
            for p in sorted(approved_dir.iterdir()) if p.is_file() and p.name not in approved]


def git_show(ref, rel):
    proc = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=ROOT, capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def git_slices(ref, rel_dir):
    """O commit'teki dilimler: {ad: içerik}."""
    proc = subprocess.run(["git", "ls-tree", "--name-only", ref, rel_dir], cwd=ROOT, capture_output=True, text=True)
    names = [Path(n).name for n in proc.stdout.splitlines()] if proc.returncode == 0 else []
    return {n: git_show(ref, rel_dir + n) or b"" for n in names if n.endswith(".jsonl")}


def verify(log_path, approved_dir, base_raw=None, archive_dir=None, base_slices=None):
    """(kayıt sayısı, hatalar). Sayı: dilimlerdeki satırlar + canlı kaydın yayınlanmamış satırları."""
    raw = Path(log_path).read_bytes() if log_path and Path(log_path).exists() else b""
    live = read_lines(raw)
    groups, errors = load_slices(archive_dir)
    records, count = [], 0
    for lines in groups.values():
        errs, recs = check_chain(lines)
        errors += errs
        records += recs
        count += len(lines)

    live_id = log_id(live)
    published = groups.get(live_id, [])
    if published and not is_prefix(published, live):
        errors.append(f"{govlib.rel('audit_log')}: yayınlanmış dilimler ({live_id}) canlı kaydın başıyla uyuşmuyor")
    errs, recs = check_chain(live)
    errors += errs
    records += recs[len(published):]
    count += max(len(live) - len(published), 0)

    if base_slices:
        errors += check_base_slices(archive_dir, base_slices)
    if base_raw is not None:
        base_lines = read_lines(base_raw)
        target = groups.get(log_id(base_lines)) or live
        errors += check_append_only(target, base_raw)
    errors += check_approvals(records, approved_dir)
    return count, errors


def main():
    govlib.setup_io()
    parser = argparse.ArgumentParser(description="Denetim kaydı bütünlük kontrolü")
    parser.add_argument("--base", help="karşılaştırılacak git ref (ör. origin/main veya bir commit)")
    args = parser.parse_args()

    base_raw, base_slices = None, None
    if args.base:
        base_raw = git_show(args.base, govlib.rel("audit_log"))
        base_slices = git_slices(args.base, govlib.rel("audit_archive"))
    archive = govlib.path("audit_archive")
    count, errors = verify(govlib.path("audit_log"), govlib.path("approved"), base_raw, archive, base_slices)
    for e in errors:
        print("HATA ", e)
    n_slices = len(list(archive.glob("*.jsonl"))) if archive.is_dir() else 0
    print(f"{govlib.rel('audit_archive')} ({n_slices} dilim) + {govlib.rel('audit_log')}: {count} kayıt, {len(errors)} hata")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
