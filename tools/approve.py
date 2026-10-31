"""Karantinadaki bir kaydı onaylayıp knowledge/approved/ dizinine taşır.

Yalnızca kullanıcı elle çalıştırır. Agent'ın çalıştırması Policy Gate tarafından
engellenir; ayrıca etkileşimli onay sorusu, stdin'i olmayan bir oturumda
otomatik olarak reddedilir.

Onay sorusundan önce kaydın karnesi basılır: reviewer kararı, kaç kaynakla
karşılaştırıldığı, erişim tarihi ve doğrulanmamış maddelerin tam listesi. Reviewer
kararı ONAY değilse ya da durum DOGRULAMADAN_GECTI değilse onay engellenir; bilerek
geçmek için --yine-de gerekir ve bu, denetim kaydına gerekçesiyle yazılır.

Kullanım:
    python tools/approve.py knowledge/quarantine/CVE-2024-0001.md [--not "açıklama"]
    python tools/approve.py <dosya> --yine-de "neden onaylandığı"   # engeli bilerek aş
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

ETIKET = "[DOĞRULANMAMIŞ]"


def alan(text, ad):
    """Ön bilgi bloğundaki tek satırlık alanın değeri; yoksa boş dize."""
    m = re.search(rf"^{ad}:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def karne(text):
    """Onay sorusundan önce basılacak satırlar: kaydın kendi beyanı, özetlenmeden."""
    kaynaklar = re.findall(r"https?://[^\s,]+", text)
    satirlar = [
        f"Durum          : {alan(text, 'durum') or '?'}",
        f"Reviewer       : {alan(text, 'reviewer') or '(yok)'}",
        f"Kaynak sayısı  : {len(set(kaynaklar))} ayrı URL",
        f"Erişim tarihi  : {alan(text, 'erisim_tarihi') or '(yok)'}",
    ]
    govde = text.split("\n---", 2)[-1]
    acik = [s.strip(" -\t") for s in govde.splitlines() if ETIKET in s]
    # Etiket bir bulgunun başında da, bir açıklamanın içinde de geçebilir. Ayırmak
    # makineye bırakılamaz, bu yüzden sayı "etiketli satır" diye adlandırılır ve
    # satırların kendisi basılır: ayrımı okuyan insan yapar.
    satirlar.append(f"Doğrulanmamış  : {len(acik)} etiketli satır")
    for s in acik:
        satirlar.append(f"  · {s if len(s) <= 300 else s[:297] + '...'}")
    return satirlar


def engel(text):
    """Onayı engelleyen nedenler; boş liste = engel yok."""
    nedenler = []
    durum = alan(text, "durum")
    reviewer = alan(text, "reviewer")
    if durum != "DOGRULAMADAN_GECTI":
        nedenler.append(f"durum DOGRULAMADAN_GECTI değil ({durum or 'yok'})")
    if not reviewer.startswith("ONAY"):
        nedenler.append(f"reviewer kararı ONAY değil ({reviewer.split('·')[0].strip() or 'yok'})")
    return nedenler


def main():
    govlib.setup_io()
    parser = argparse.ArgumentParser(description="Karantina kaydını onayla")
    parser.add_argument("dosya")
    parser.add_argument("--not", dest="note", default="")
    parser.add_argument("--yine-de", dest="override", default="",
                        help="engeli bilerek aş; gerekçe zorunlu ve denetim kaydına yazılır")
    args = parser.parse_args()

    src = Path(args.dosya).resolve()
    quarantine = govlib.path("quarantine").resolve()
    if src.parent != quarantine or not src.is_file():
        sys.exit(f"Hata: dosya {govlib.rel('quarantine')} içinde olmalı: {src}")

    text = src.read_text(encoding="utf-8")
    print(f"Dosya          : {src.name}")
    for satir in karne(text):
        print(satir)

    nedenler = engel(text)
    if nedenler:
        print("\nOnay engellendi:")
        for n in nedenler:
            print(f"  - {n}")
        if not args.override:
            govlib.audit("Approve", "approve.py", "engellendi", "; ".join(nedenler), src.name)
            sys.exit("Onay verilmedi. Bilerek geçmek için: --yine-de \"gerekçe\"")
        print(f"\n--yine-de verildi: {args.override}")
    print("\nOnay, bu kaydın bundan sonra olgu olarak kullanılacağı anlamına gelir.")

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
    if args.override:
        extra += f"\nonay_istisnasi: {args.override}"
    text = re.sub(r"^durum:\s*\S+", "durum: ONAYLANDI", text, count=1, flags=re.M)
    # İlk "\n---" ön bilgi bloğunun kapanışıdır; onay alanlarını onun önüne ekle.
    text = text.replace("\n---", f"\n{extra}\n---", 1)

    dest = govlib.path("approved") / src.name
    if dest.exists():
        sys.exit(f"Hata: {dest} zaten var; önce eskisini arşivleyin.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    src.unlink()
    gerekce = f"onaylayan={approver}"
    if args.override:
        gerekce += f"; istisna={args.override}; engel={'; '.join(nedenler)}"
    govlib.audit("Approve", "approve.py", "onaylandi", gerekce, src.name)
    print(f"Onaylandı → {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
