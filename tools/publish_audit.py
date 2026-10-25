"""Canlı denetim kaydının yayınlanmamış satırlarını yeni bir dilim dosyasına yazar.

Kullanım (yalnızca kullanıcı):
    python tools/publish_audit.py

Canlı kayıt (files.audit_log) git'te izlenmez. Bu betik, aynı kaynağın önceki
dilimlerinden sonra gelen satırları dirs.audit_archive altına
<ts>_<yerel|bulut>_<logid>.jsonl olarak yazar. Commit, push ve PR kullanıcıya aittir;
betik git'e dokunmaz. Önce tools/verify_audit.py kontrolleri çalışır; hata varsa yazmaz.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(ROOT / "tools"))
import govlib  # noqa: E402
import verify_audit  # noqa: E402


def publish(log_path, archive_dir, approved_dir, kind, now=None):
    """(yazılan dilim yolu veya None, satır sayısı, hatalar)."""
    _, errors = verify_audit.verify(log_path, approved_dir, archive_dir=archive_dir)
    if errors:
        return None, 0, errors
    raw = Path(log_path).read_bytes() if Path(log_path).exists() else b""
    live = verify_audit.read_lines(raw)
    lid = verify_audit.log_id(live)
    groups, _ = verify_audit.load_slices(archive_dir)
    new = live[len(groups.get(lid, [])):]
    if not new:
        return None, 0, []
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    out = Path(archive_dir) / f"{ts}_{kind}_{lid}.jsonl"
    if out.exists():
        return None, 0, [f"{out.name} zaten var; bir saniye sonra yeniden deneyin"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"".join(ln + b"\n" for _, ln in new))
    return out, len(new), []


def main():
    govlib.setup_io()
    kind = "bulut" if os.environ.get("CLAUDE_CODE_REMOTE") == "true" else "yerel"
    out, n, errors = publish(govlib.path("audit_log"), govlib.path("audit_archive"), govlib.path("approved"), kind)
    for e in errors:
        print("HATA ", e)
    if errors:
        return 1
    if out is None:
        print("Yayınlanacak yeni kayıt yok.")
        return 0
    rel = out.relative_to(ROOT).as_posix()
    print(f"{rel}: {n} kayıt yazıldı.")
    print(f'Sonraki adım: git add {rel}; git commit -m "Denetim kaydı dilimi"; git push  (ardından PR)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
