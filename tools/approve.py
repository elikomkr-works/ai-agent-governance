"""Karantinadaki bir kaydı onaylayıp knowledge/approved/ dizinine taşır.

Yalnızca kullanıcı elle çalıştırır. Agent'ın çalıştırması Policy Gate tarafından
engellenir; ayrıca etkileşimli onay sorusu, stdin'i olmayan bir oturumda
otomatik olarak reddedilir.

Kullanım:
    python tools/approve.py knowledge/quarantine/CVE-2024-0001.md [--not "açıklama"]
"""
import argparse
import getpass
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import govlib  # noqa: E402


def main():
    govlib.setup_io()
    parser = argparse.ArgumentParser(description="Karantina kaydını onayla")
    parser.add_argument("dosya")
    parser.add_argument("--not", dest="note", default="")
    args = parser.parse_args()

    src = Path(args.dosya).resolve()
    quarantine = (ROOT / "knowledge" / "quarantine").resolve()
    if src.parent != quarantine or not src.is_file():
        sys.exit(f"Hata: dosya knowledge/quarantine/ içinde olmalı: {src}")

    text = src.read_text(encoding="utf-8")
    m = re.search(r"^durum:\s*(\S+)", text, re.M)
    status = m.group(1) if m else "?"
    print(f"Dosya : {src.name}\nDurum : {status}")
    if status != "DOGRULAMADAN_GECTI":
        print("Uyarı: kayıt DOGRULAMADAN_GECTI durumunda değil.")

    try:
        answer = input("Bu kaydı onaylıyor musunuz? (evet/hayır): ").strip().lower()
    except EOFError:
        answer = ""
    if answer != "evet":
        govlib.audit("Approve", "approve.py", "iptal", "Kullanıcı onay vermedi", src.name)
        sys.exit("İptal edildi.")

    approver = getpass.getuser()
    extra = f"onaylayan: {approver}\nonay_tarihi: {date.today().isoformat()}"
    if args.note:
        extra += f"\nonay_notu: {args.note}"
    text = re.sub(r"^durum:\s*\S+", "durum: ONAYLANDI", text, count=1, flags=re.M)
    # İlk "\n---" ön bilgi bloğunun kapanışıdır; onay alanlarını onun önüne ekle.
    text = text.replace("\n---", f"\n{extra}\n---", 1)

    dest = ROOT / "knowledge" / "approved" / src.name
    if dest.exists():
        sys.exit(f"Hata: {dest} zaten var; önce eskisini arşivleyin.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    src.unlink()
    govlib.audit("Approve", "approve.py", "onaylandi", f"onaylayan={approver}", src.name)
    print(f"Onaylandı → {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
