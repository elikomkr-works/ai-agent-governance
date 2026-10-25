"""Policy Gate ve Validator hook'larının ortak yardımcıları."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "governance"


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


def load_policy():
    return load_json(GOV / "policy.json")


def registered_skills():
    return {s["name"] for s in load_json(GOV / "skills_registry.json")["skills"]}


def registered_agents():
    return {a["name"] for a in load_json(GOV / "agents_registry.json")["agents"]}


def audit(event, tool, decision, reason, detail=""):
    """Her kararı governance/audit.jsonl dosyasına ekler (yalnızca ekleme)."""
    path = Path(os.environ.get("GOV_AUDIT_LOG") or GOV / "audit.jsonl")
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "tool": tool,
        "decision": decision,
        "reason": reason,
        "detail": detail[:300],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


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
