"""Denetim kaydından salt-okunur yönetişim panelini üretir (tek dosyalık statik HTML).

Kullanım:
    python tools/build_site.py

Yollar governance/paths.json'dan okunur: kaynak dirs.audit_archive dilimleri ve
files.audit_log canlı kaydının yayınlanmamış satırları, şablon files.panel_template,
çıktı files.site_index. CI'da canlı kayıt yoktur; panel yalnızca dilimlerden oluşur. Sayfa hiçbir dosyayı değiştirmez,
ağ erişimi yapmaz ve dış kaynak yüklemez; veriyi yenilemek için betiği tekrar
çalıştırın.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(ROOT / "tools"))
import govlib  # noqa: E402
import verify_audit  # noqa: E402

FIELDS = ("ts", "session", "agent", "event", "tool", "decision", "reason", "detail")
PLACEHOLDER = "/*__PANEL_DATA__*/"


def read_audit(path, archive_dir=None):
    """Kayıtları ve okunamayan satırları döndürür; bozuk satır sessizce atlanmaz, raporlanır.

    Önce dilimler (ad sırasıyla), sonra canlı kaydın henüz yayınlanmamış satırları;
    yayınlanmış satırlar iki kez sayılmaz.
    """
    groups, _ = verify_audit.load_slices(archive_dir)
    raw = Path(path).read_bytes() if Path(path).exists() else b""
    live = verify_audit.read_lines(raw)
    published = groups.get(verify_audit.log_id(live), [])
    skip = len(published) if verify_audit.is_prefix(published, live) else 0
    lines = [ln for g in groups.values() for ln in g] + live[skip:]
    records, errors = [], []
    for where, ln in lines:
        try:
            rec = json.loads(ln.decode("utf-8", errors="replace"))
            if not isinstance(rec, dict):
                raise ValueError("satır bir JSON nesnesi değil")
        except ValueError as e:
            errors.append({"line": where, "error": str(e)[:200]})
            continue
        records.append({k: str(rec.get(k, "")) for k in FIELDS})
    return records, errors


def embed(data):
    """JSON'u <script> içine güvenle gömer: '<' kaçışlanır, kayıttaki '</script>' bloğu kapatamaz."""
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def build(audit_path, template_path, out_path, archive_dir=None):
    records, errors = read_audit(audit_path, archive_dir)
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": str(govlib.ROOT),
        "source": f"{govlib.rel('audit_archive')} + {govlib.rel('audit_log')}",
        "paths_file": govlib.rel("paths_file"),
        "builder": govlib.rel("tools") + Path(__file__).name,
        "records": records,
        "errors": errors,
    }
    template = Path(template_path).read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"Şablonda {PLACEHOLDER} tam olarak bir kez geçmeli: {template_path}")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(template.replace(PLACEHOLDER, embed(data)), encoding="utf-8")
    return len(records), len(errors)


def main():
    govlib.setup_io()
    count, bad = build(govlib.path("audit_log"), govlib.path("panel_template"), govlib.path("site_index"),
                       govlib.path("audit_archive"))
    note = f", {bad} satır okunamadı" if bad else ""
    print(f"Panel üretildi → {govlib.rel('site_index')} ({count} kayıt{note})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
