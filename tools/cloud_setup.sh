#!/bin/bash
# Bulut ortamı kurulum betiği.
#
# claude.ai/code → ortam (Default) → Setup script alanına bu dosyanın içeriği yapıştırılır.
# Betik bulut VM'inde root olarak, Claude Code başlamadan önce çalışır; sonuç ortam
# önbelleğine alınır.
#
# Neden: Claude Code'un Bash sandbox'ı Linux'ta bubblewrap ve socat ister; bulut imajında
# yoklar. Yoksa .claude/settings.json'daki sandbox sessizce devre dışı kalır. Policy Gate
# bulutta bu paketleri bulamazsa kabuk komutlarını reddeder (fail-closed).
#
# Betik her durumda 0 ile çıkar: sıfır dışı çıkış oturumun hiç başlamamasına yol açar.
# Kurulum başarısız olursa engellemeyi Policy Gate yapar.

export DEBIAN_FRONTEND=noninteractive
if apt-get update -qq && apt-get install -y -qq bubblewrap socat; then
  echo "Sandbox paketleri kuruldu: $(command -v bwrap) $(command -v socat)"
else
  echo "Uyarı: bubblewrap/socat kurulamadı; Policy Gate bulutta kabuk komutlarını reddedecek." >&2
fi
exit 0
