#!/usr/bin/env bash
# Hook başlatıcı: Windows (python) ve bulut/Linux (python3) ortamlarında çalışan Python'u seçer.
# Python bulunamazsa exit 2 ile işlemi engeller — kurallar sessizce devre dışı kalmaz.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "" >/dev/null 2>&1; then
    exec "$py" "$DIR/$1"
  fi
done
echo "[Governance] Python bulunamadı; hook çalışamadı, işlem güvenlik için engellendi." >&2
exit 2
