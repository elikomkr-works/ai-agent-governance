"""Müşteri alımı: hangi paket ne veriyor, siparişte ne istenir.

Kullanım:
    python tools/intake.py                                  # katalog
    python tools/intake.py <hizmet> <paket>                 # alım listesi
    python tools/intake.py <hizmet> <paket> --siparis "<müşteri>" [--guncelle]

Katalog governance/services.json'dan okunur; betik kendi başına fiyat, süre ya
da kapsam tutmaz. Gig metinleri de o tablodan türetilir.

--siparis, iş panosunda sipariş klasörünü açar ve içine `intake.md` yazar:
işaretlenecek girdi listesi, paket sınırları ve müşteriye olduğu gibi
gönderilecek İngilizce mesaj. Dosya elle doldurulduğu için varsa üzerine
yazılmaz; bilerek yenilemek için --guncelle.

'blocker' işaretli girdi gelmeden iş başlamaz: eksikse müşteriye sorulur
(CLAUDE.md → Lead Agent protocol, adım 2). Hata varsa çıkış kodu 1'dir.
"""
import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import govlib  # noqa: E402

LIMIT_LABEL = {"config_files": "config dosyası", "log_files": "log dosyası", "hosts": "host"}
# Müşteriye giden mesajda sınırlar İngilizce ve tekil/çoğul doğru yazılır.
LIMIT_EN = {"config_files": "config file", "log_files": "log file", "hosts": "host"}


def load():
    return govlib.load_json(govlib.path("services"))


def pick(data, service, package):
    """(hizmet sözlüğü, paket sözlüğü); bilinmeyen ad için ValueError."""
    services = data["services"]
    if service not in services:
        raise ValueError(f"bilinmeyen hizmet: {service} (seçenekler: {', '.join(services)})")
    svc = services[service]
    if package not in svc["packages"]:
        raise ValueError(f"'{service}' için bilinmeyen paket: {package} "
                         f"(seçenekler: {', '.join(svc['packages'])})")
    return svc, svc["packages"][package]


def limits_line(pkg):
    """Sıfır olan sınır yazılmaz: 'Basic' için 'log dosyası: 0' bilgi değil gürültüdür."""
    parts = [f"{LIMIT_LABEL.get(k, k)} ×{v}" for k, v in pkg["limits"].items() if v]
    return ", ".join(parts) if parts else "—"


def asks(svc, package):
    """Paket için geçerli alım kalemleri: 'packages' alanı olan kalem yalnızca o paketlerde sorulur."""
    return [item for item in svc["intake"]
            if package in item.get("packages", [package])]


def catalog_text(data):
    out = ["# Hizmet kataloğu", "",
           "| Hizmet | Paket | Fiyat | Süre | Revizyon | Sınır |",
           "|---|---|---|---|---|---|"]
    for key, svc in data["services"].items():
        for pkey, pkg in svc["packages"].items():
            out.append(f"| {key} | {pkey} ({pkg['title']}) | ${pkg['price_usd']} | "
                       f"{pkg['delivery_days']} gün | {pkg['revisions']} | {limits_line(pkg)} |")
    out += ["", "Alım listesi: `python tools/intake.py <hizmet> <paket>`", ""]
    return "\n".join(out)


def customer_message(svc, pkg, package, common):
    """Müşteriye gönderilecek İngilizce mesaj: istenen girdiler ve istenmeyenler."""
    lines = [f"Thanks for your order — {svc['name']}, {pkg['title']} package "
             f"(delivery in {pkg['delivery_days']} day(s)).", "",
             "To start I need:"]
    for i, item in enumerate(asks(svc, package), 1):
        suffix = "" if item.get("blocker") else " (optional)"
        lines.append(f"{i}. {item['ask_en']}{suffix}")
    lines += ["", "What I will not ask for, in any package:"]
    lines += [f"- {n}" for n in common["never"]]
    lines += ["", f"This package covers: {limits_text_en(pkg)}. "
                  "Anything beyond that I will quote separately before doing it."]
    return "\n".join(lines)


def limits_text_en(pkg):
    parts = [f"{v} {LIMIT_EN.get(k, k)}{'s' if v > 1 else ''}"
             for k, v in pkg["limits"].items() if v]
    return ", ".join(parts) if parts else "as described in the package"


def intake_text(data, service, package, customer, today=None):
    svc, pkg = pick(data, service, package)
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    common = data["common"]
    required = [i for i in asks(svc, package) if i.get("blocker")]
    optional = [i for i in asks(svc, package) if not i.get("blocker")]

    out = [f"# Alım: {customer} — {svc['name']} / {pkg['title']}", "",
           f"| Alan | Değer |", "|---|---|",
           f"| Tarih | {today} |",
           f"| Hizmet / paket | `{service}` / `{package}` |",
           f"| Fiyat | ${pkg['price_usd']} |",
           f"| Teslim süresi | {pkg['delivery_days']} gün |",
           f"| Revizyon | {pkg['revisions']} |",
           f"| Paket sınırı | {limits_line(pkg)} |",
           f"| Skill / agent | `{svc['skill']}` / `{svc['agent']}` |", "",
           "## Gerekli girdiler", "",
           "Bu liste tamamlanmadan iş başlamaz; eksik olan müşteriye sorulur.", ""]
    for item in required:
        out.append(f"- [ ] **{item['id']}** — {item['ask_en']}")
        out.append(f"      Not: {item['note_tr']}")
    if optional:
        out += ["", "## İsteğe bağlı girdiler", "",
                "Gelmezse iş durmaz; varsayım raporda yazılır.", ""]
        for item in optional:
            out.append(f"- [ ] **{item['id']}** — {item['ask_en']}")
            out.append(f"      Not: {item['note_tr']}")

    out += ["", "## Paket kapsamı", ""] + [f"- {x}" for x in pkg["includes"]]
    if pkg["excludes"]:
        out += ["", "Bu pakette yok (üst pakete aittir): " + ", ".join(pkg["excludes"]) + "."]
    out += ["", "## İstenmeyen ve verilmeyen", ""] + [f"- {x}" for x in common["never"]]
    out += ["", "## Çıktılar", ""] + [f"- {x}" for x in common["outputs"]]
    out += ["", f"Veri: {common['data_handling']}", "",
            "## Müşteriye gönderilecek mesaj", "",
            "Olduğu gibi kopyalanır; eksik girdi sorulurken de bu metin kullanılır.", "",
            "```", customer_message(svc, pkg, package, common), "```", ""]
    return "\n".join(out)


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "musteri"


def order_folder(service, customer, today=None):
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return govlib.path("work") / f"{today}_{service}-{slug(customer)}"


def show(p):
    return str(p.relative_to(ROOT)).replace("\\", "/") if p.is_relative_to(ROOT) else str(p)


def main(argv=None):
    govlib.setup_io()  # Windows kod sayfasında Türkçe karakter bozulmasın.
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("hizmet", nargs="?")
    ap.add_argument("paket", nargs="?")
    ap.add_argument("--siparis", metavar="MÜŞTERİ", help="iş panosunda sipariş klasörü aç")
    ap.add_argument("--guncelle", action="store_true", help="var olan intake.md üzerine yaz")
    args = ap.parse_args(argv)

    data = load()
    if not args.hizmet:
        print(catalog_text(data))
        return 0
    if not args.paket:
        print("HATA: paket adı gerekli. Katalog: python tools/intake.py", file=sys.stderr)
        return 1
    try:
        pick(data, args.hizmet, args.paket)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1

    customer = args.siparis or "<müşteri>"
    text = intake_text(data, args.hizmet, args.paket, customer)
    if not args.siparis:
        print(text)
        return 0

    folder = order_folder(args.hizmet, customer)
    target = folder / "intake.md"
    if target.exists() and not args.guncelle:
        print(f"HATA: {show(target)} var. Elle doldurulmuş olabilir; "
              f"bilerek yenilemek için --guncelle.", file=sys.stderr)
        return 1
    folder.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"Alım dosyası yazıldı: {show(target)}")
    print(f"Sonraki adım: gerekli girdiler tamamlanınca {args.hizmet} işi "
          f"{pick(data, args.hizmet, args.paket)[0]['agent']} agent'ına verilir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
