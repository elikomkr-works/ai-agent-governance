"""İzin reddi kaydı — PermissionDenied, Stop ve SubagentStop hook'u.

Claude Code'un izin sistemi bazı çağrıları hook'lara hiç ulaştırmadan reddeder:
settings.json'daki deny kuralları, kullanıcının reddettiği onay istemleri ve
auto mode sınıflandırıcısı. Policy Gate bu çağrıları görmez; bu yüzden denetim
kaydında da yer almazlar. Bu hook o boşluğu kapatır:

PermissionDenied: auto mode reddini anında kaydeder.
Stop / SubagentStop: oturumun (veya alt agent'ın) transcript'ini tarar ve
  reddedilmiş araç sonuçlarını kaydeder. Bir çağrı, tool_use_id'si kayıtta
  varsa ikinci kez yazılmaz.

Hook'un kendisi hiçbir kararı değiştirmez; yalnızca kayıt tutar.
"""
import json
import os
import re
import sys
from pathlib import Path

EVENT = "Permission"
# permissionDecision alanı olmayan eski sürümler için hata metni işaretleri.
FALLBACK_MARKERS = (
    ("denied by your permission settings", "rule"),
    ("Permission to use", "rule"),
    ("denied by the Claude Code auto mode classifier", "classifier"),
    ("The user doesn't want to proceed with this tool use", "user"),
)
ID_RE = re.compile(r"tool_use_id=(\S+)")


def logged_ids(log):
    """Kayıtta zaten bulunan izin reddi çağrılarının tool_use_id'leri."""
    ids = set()
    try:
        with open(log, encoding="utf-8") as f:
            for line in f:
                if f'"event": "{EVENT}"' in line:
                    ids.update(ID_RE.findall(line))
    except OSError:
        pass
    return ids


def result_text(block):
    content = block.get("content")
    if isinstance(content, list):
        content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    return str(content or "")


def rejection(entry, block):
    """Reddedilen çağrının gerekçe kodu; reddedilmediyse veya Gate reddettiyse None."""
    pd = entry.get("permissionDecision")
    if isinstance(pd, dict):
        if pd.get("decision") != "reject" or pd.get("source") == "hook":
            return None
        return pd.get("reasonCode") or pd.get("reasonType") or pd.get("source") or "reject"
    if not block.get("is_error"):
        return None
    text = result_text(block)
    if "[Policy Gate]" in text:
        return None
    return next((kind for marker, kind in FALLBACK_MARKERS if marker in text), None)


def scan(transcript):
    """Transcript'teki reddedilmiş çağrılar: (tool_use_id, araç, girdi, gerekçe, zaman, hata)."""
    uses, found = {}, []
    with open(transcript, encoding="utf-8") as f:
        for line in f:
            if '"tool_use"' not in line and '"tool_result"' not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    uses[block.get("id")] = (block.get("name", "?"), block.get("input") or {})
                elif block.get("type") == "tool_result":
                    code = rejection(entry, block)
                    if code:
                        tid = block.get("tool_use_id", "")
                        tool, inp = uses.get(tid, ("?", {}))
                        found.append((tid, tool, inp, code, entry.get("timestamp", ""), result_text(block)))
    return found


def record(govlib, summarize, data, tid, tool, inp, reason):
    detail = f"tool_use_id={tid} {summarize({'tool_input': inp})}".strip()
    govlib.audit(EVENT, tool, "deny", reason[:300], detail, data)


def handle(data, govlib, summarize):
    event = data.get("hook_event_name", "")
    log = Path(os.environ.get("GOV_AUDIT_LOG") or govlib.path("audit_log"))

    if event == "PermissionDenied":
        tid = data.get("tool_use_id", "")
        if tid not in logged_ids(log):
            record(govlib, summarize, data, tid, data.get("tool_name", "?"), data.get("tool_input") or {},
                   f"classifier:auto-mode — {data.get('reason', '')}")
        return 0

    if event in ("Stop", "SubagentStop"):
        transcript = data.get("agent_transcript_path") if event == "SubagentStop" else None
        transcript = transcript or data.get("transcript_path")
        if not transcript or not Path(transcript).is_file():
            return 0
        seen = logged_ids(log)
        n = 0
        for tid, tool, inp, code, ts, text in scan(transcript):
            if tid in seen:
                continue
            seen.add(tid)
            record(govlib, summarize, data, tid, tool, inp, f"{code} @ {ts} — {text[:160]}")
            n += 1
        return n
    return 0


def main():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import govlib
        from policy_gate import summarize
        govlib.setup_io()
        handle(json.load(sys.stdin), govlib, summarize)
    except Exception as e:
        # Kayıt tutulamadıysa kullanıcı bilmeli; ama izin kararları zaten verilmiş, engellenecek bir şey yok.
        print(json.dumps({"systemMessage": f"⚠ İzin reddi kaydı yazılamadı, denetim kaydı eksik olabilir: {e!r}"},
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
