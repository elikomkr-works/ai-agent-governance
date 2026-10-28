"""Bir müşteri için sistemden ayrı bir repo klasörü hazırlar (yalnızca kullanıcı).

Kullanım:
    python tools/new_customer.py <müşteri-adı> <hedef klasör>
    python tools/new_customer.py --guncelle <hedef klasör>

Sistem reposu public'tir; müşteri verisi (log, kanıt, rapor, karantina, denetim kaydı)
yalnızca müşteri reposunda durur ve o repo private açılır. Bu betik beyaz liste kullanır:
yalnızca git'te izlenen sistem dosyaları kopyalanır. Bu reponun raporları, dilimleri,
bilgi kayıtları ve taslakları hiçbir zaman kopyalanmaz.

Müşteri kopyasında farklı olanlar:
- CI'daki GitHub Pages yayını çıkarılır (private repodan açılan Pages sitesi herkese açık olabilir).
- Veri klasörleri boş açılır (.gitkeep).
- MUSTERI.md: müşteri adı, sistem sürümü ve kılavuz.

--guncelle yalnızca sistem dosyalarının üzerine yazar. Veri klasörlerine, MUSTERI.md'ye ve
policy.json'daki müşteriye ait kapsama (scope) dokunmaz.
Betik git'e dokunmaz; git init, commit ve private repo açmak kullanıcıya aittir.
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import govlib  # noqa: E402

GUIDE = "MUSTERI.md"
WORKFLOW = ".github/workflows/governance-tests.yml"
# Yerini Claude Code ve GitHub belirler; paths.json'da yer almazlar.
FIXED_SYSTEM = [".claude/", ".github/", "CLAUDE.md", ".gitignore", ".gitattributes"]
SYSTEM_DIRS = ["governance", "tools", "tests", "samples"]
# Sistem klasörlerinin içinde kalsalar da veridir; kopyalanmaz, müşteride boş açılır.
# approved'a .gitkeep konmaz: verify_audit oradaki her dosya için Approve kaydı ister; klasörü approve.py açar.
DATA_DIRS = ["audit_archive", "reports", "quarantine"]
NEVER_COPY = DATA_DIRS + ["approved", "proposals", "work", "site", "evidence"]
PAGES_NOTE = "CI publishes the panel to GitHub Pages on `main`."


def system_files():
    """Sistem reposunda git'te izlenen ve beyaz listeye giren dosyalar (köke göre, '/' ile)."""
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    allow = FIXED_SYSTEM + [govlib.rel(k) for k in SYSTEM_DIRS]
    deny = [govlib.rel(k) for k in NEVER_COPY]
    files = [f for f in out.decode("utf-8").split("\0") if f]
    return [f for f in files
            if any(f == a or (a.endswith("/") and f.startswith(a)) for a in allow)
            and not any(f.startswith(d) for d in deny)]


def strip_pages(text):
    """CI dosyasından 'pages' işini çıkarır; testler kalır."""
    # Windows'ta çalışma kopyası CRLF olabilir.
    return re.split(r"\r?\n  pages:\r?\n", text, maxsplit=1)[0].rstrip() + "\n"


def transform(rel, data):
    if rel == WORKFLOW:
        return strip_pages(data.decode("utf-8")).encode("utf-8")
    if rel == "CLAUDE.md":
        note = "In this customer repo the panel is not published; open it locally only (see MUSTERI.md)."
        return data.decode("utf-8").replace(PAGES_NOTE, note).encode("utf-8")
    return data


def keep_scope(target, data):
    """Güncellemede yeni policy.json'a müşterinin mevcut kapsamını taşır."""
    old = target / govlib.rel("policy")
    if not old.exists():
        return data
    policy = json.loads(data.decode("utf-8"))
    policy["scope"] = govlib.load_json(old)["scope"]
    return (json.dumps(policy, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def source_commit():
    # İlk commit'ten önce (ör. yeni müşteri reposunda testler koşarken) HEAD yoktur.
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "commit yok"


def guide(name, commit, today):
    return f"""# Müşteri reposu: {name}

Sistem sürümü: `{commit}` ({today}). Sistem kaynağı: public `ai-agent-governance` reposu.

Bu repo **private** kalmalı. Müşterinin log, kanıt, rapor ve denetim kaydı yalnızca burada durur.
Onaylayıcı yine sizsiniz; müşteri onay vermez.

## İlk kurulum
```
git init -b main
git add -A
git commit -m "Müşteri reposu: {name}"
gh repo create <repo-adı> --private --source . --push
```
GitHub'da Settings → Pages kapalı kalsın. CI yalnızca testleri çalıştırır, panel yayınlanmaz.

## Kapsam
`governance/policy.json` → `scope.allowed_targets` alanına yalnızca müşterinin **yazılı izin verdiği** hedefleri elle ekleyin.
İzin belgesini repo dışında saklayın.

## Veri nereye konur
| Veri | Klasör | Git |
|---|---|---|
| Loglar, config dosyaları | kendi açacağınız bir klasör (ör. `girdiler/`); `samples/` yalnızca testlerin örnek verisidir | izlenir (private) |
| Host kanıtı (`tools/ir_collect.sh` çıktısı) | `evidence/<host>/` | izlenmez (`.gitignore`) |
| Raporlar | `reports/` | izlenir |
| Karantina / onaylı bilgi | `knowledge/quarantine/`, `knowledge/approved/` | izlenir |
| Denetim kaydı | `governance/audit.jsonl` (canlı) → `python tools/publish_audit.py` ile `governance/audit_archive/` | dilimler izlenir |

## Panel
`python tools/build_site.py` → `site/index.html` dosyasını tarayıcıda açın. Müşteriye paylaşmadan önce içeriğe bakın.

## Sistem güncellemesi
Sistem reposunda: `python tools/new_customer.py --guncelle <bu klasör>`.
Yalnızca sistem dosyaları değişir. Veri klasörlerine, bu dosyaya ve kapsama dokunulmaz.
Sonra burada `python tests/test_governance.py` çalıştırın ve değişikliği commit edin.

## Güncelleme geçmişi
- {today}: kuruldu, sistem `{commit}`
"""


def build(target, name=None, update=False, today=None):
    """(yazılan dosya sayısı, hatalar)."""
    target = Path(target).resolve()
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if target == ROOT or target.is_relative_to(ROOT):
        return 0, ["hedef sistem reposunun içinde olamaz (müşteri verisi public repoya girer)"]
    if update:
        if not (target / GUIDE).exists():
            return 0, [f"{target} müşteri reposu değil ({GUIDE} yok)"]
    elif target.exists() and any(target.iterdir()):
        return 0, [f"{target} boş değil; güncellemek için --guncelle kullanın"]

    commit = source_commit()
    files = system_files()
    for rel in files:
        data = transform(rel, (ROOT / rel).read_bytes())
        if update and rel == govlib.rel("policy"):
            data = keep_scope(target, data)
        out = target / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    for key in DATA_DIRS:
        d = target / govlib.rel(key)
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()
    g = target / GUIDE
    if update:
        with open(g, "a", encoding="utf-8") as f:
            f.write(f"- {today}: sistem güncellendi, `{commit}`\n")
    else:
        g.write_text(guide(name, commit, today), encoding="utf-8")
    return len(files), []


def main():
    govlib.setup_io()
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--guncelle":
        n, errors = build(args[1], update=True)
    elif len(args) == 2 and not args[0].startswith("-"):
        n, errors = build(args[1], name=args[0])
    else:
        print(__doc__)
        return 2
    for e in errors:
        print("HATA ", e)
    if errors:
        return 1
    print(f"{n} sistem dosyası yazıldı: {Path(args[1]).resolve()}")
    print(f"Sonraki adım: {GUIDE} → 'İlk kurulum' (private repo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
