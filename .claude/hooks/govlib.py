"""Policy Gate ve Validator hook'larının ortak yardımcıları.

Klasör ve dosya yolları governance/paths.json'dan okunur (tek kaynak);
diğer modüller yolları path() / rel() ile alır, kendileri yazmaz.
"""
import hashlib
import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
# Yerini bildiğimiz tek dosya; diğer her yol buradan okunur.
PATHS_FILE = "governance/paths.json"

_paths = None


def setup_io():
    # Windows'ta varsayılan kod sayfası UTF-8 değil; Türkçe karakterler bozulmasın.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_paths(data):
    """paths.json içeriğini {anahtar: (tür, göreli yol)} tablosuna çevirir.

    Mutlak, '..' içeren veya ters bölü kullanan yol hata verir; böylece bir
    yol proje dışını gösteremez. Hook'lar hatada güvenli tarafta kalır.
    """
    table = {"paths_file": ("files", PATHS_FILE)}
    for kind in ("dirs", "files"):
        for key, value in data[kind].items():
            if key in table:
                raise ValueError(f"paths.json: '{key}' anahtarı birden fazla kez tanımlı.")
            p = PurePosixPath(value) if isinstance(value, str) else None
            if (p is None or not value.strip("/") or "\\" in value or ":" in value
                    or p.is_absolute() or ".." in p.parts):
                raise ValueError(f"paths.json: '{key}' proje içinde göreli bir yol olmalı: {value!r}")
            table[key] = (kind, str(p))
    return table


def paths():
    global _paths
    if _paths is None:
        _paths = parse_paths(load_json(ROOT / PATHS_FILE))
    return _paths


def path(key):
    """Anahtarın mutlak yolu: path('reports') -> <kök>/reports"""
    return ROOT / paths()[key][1]


def rel(key):
    """Anahtarın proje köküne göre yolu; dizinlerde sonda '/' olur: rel('reports') -> 'reports/'"""
    kind, value = paths()[key]
    return value + "/" if kind == "dirs" else value


def resolve(entry):
    """'@anahtar' başvurusunu rel_path() ile karşılaştırılabilir yola çevirir; diğer değerler aynen kalır."""
    if not entry.startswith("@"):
        return entry
    key = entry[1:]
    if key not in paths():
        raise KeyError(f"'{entry}' governance/paths.json içinde tanımlı değil.")
    return rel(key).lower()


def load_policy():
    policy = load_json(path("policy"))
    for group in ("deny_write", "ask_write"):
        policy["paths"][group] = [resolve(p) for p in policy["paths"][group]]
    # '@anahtar' komut kuralında betiğin dosya adına çözülür (ör. \bapprove\.py\b).
    policy["deny_commands"] = [
        rf"\b{re.escape(PurePosixPath(resolve(c)).name)}\b" if c.startswith("@") else c
        for c in policy["deny_commands"]
    ]
    return policy


def registered_skills():
    return {s["name"] for s in load_json(path("skills_registry"))["skills"]}


def registered_agents():
    return {a["name"] for a in load_json(path("agents_registry"))["agents"]}


GENESIS = "0" * 64


def line_hash(line):
    """Denetim kaydı satırının özeti; satır sonu (\\n veya \\r\\n) hesaba katılmaz."""
    if isinstance(line, str):
        line = line.encode("utf-8")
    return hashlib.sha256(line.rstrip(b"\r\n")).hexdigest()


def last_line(f):
    """İkili kipte açık dosyanın son boş olmayan satırı (yoksa b'')."""
    f.seek(0, os.SEEK_END)
    pos, buf = f.tell(), b""
    while pos > 0:
        step = min(4096, pos)
        pos -= step
        f.seek(pos)
        buf = f.read(step) + buf
        lines = [ln for ln in buf.splitlines() if ln.strip()]
        if len(lines) > 1 or (lines and pos == 0):
            return lines[-1]
    return b""


@contextmanager
def locked(f):
    """Dosyaya özel kilit; aynı anda yazan oturumlar zinciri çatallayamaz."""
    if os.name == "nt":
        import msvcrt
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)  # 0. bayt kilit bayrağı; ekleme yazımını engellemez
        try:
            yield
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def audit(event, tool, decision, reason, detail="", hook_data=None):
    """Her kararı denetim kaydına ekler (yalnızca ekleme, hash zincirli).

    'prev' önceki satırın SHA-256 özetidir; bir satır silinir veya değiştirilirse
    zincir kopar ve tools/verify_audit.py bunu bulur. 'session' ve 'agent'
    hook girdisinden gelir; aynı klasörde birden çok oturum çalışırken kaydı kimin
    ürettiği ayırt edilir.
    """
    hook_data = hook_data or {}
    log = Path(os.environ.get("GOV_AUDIT_LOG") or path("audit_log"))
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session": str(hook_data.get("session_id", ""))[:64],
        "agent": str(hook_data.get("agent_type") or hook_data.get("agent_id") or "")[:64],
        "event": event,
        "tool": tool,
        "decision": decision,
        "reason": reason,
        "detail": detail[:300],
    }
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a+b") as f, locked(f):
        prev = last_line(f)
        record["prev"] = line_hash(prev) if prev else GENESIS
        f.write((json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8"))
        f.flush()  # kilit bırakılmadan diske yaz; yoksa yazım kapanışa kalır ve zincir çatallanır


def rel_path(p):
    """Proje köküne göre küçük harfli, '/' ayraçlı göreli yol.

    Proje dışındaki mutlak yollar mutlak olarak döner.
    """
    low = str(p).replace("\\", "/").lower()
    m = re.match(r"^/([a-z])/(.*)$", low)  # Git Bash: /c/Users/... -> c:/Users/...
    if m:
        low = f"{m.group(1)}:/{m.group(2)}"
    root = str(ROOT).replace("\\", "/").lower().rstrip("/") + "/"
    if low.startswith(root):
        return low[len(root):]
    while low.startswith("./"):
        low = low[2:]
    return low
