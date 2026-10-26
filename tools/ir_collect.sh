#!/bin/bash
# Olay müdahalesi kanıt toplama betiği (incident-response skill'i için).
#
# Kullanıcı sunucuda root olarak çalıştırır; agent çalıştırmaz.
#   sudo bash ir_collect.sh <çıktı klasörü> '<başlangıç>' '<bitiş>' [şüpheli dosya ...]
#   ör. sudo bash ir_collect.sh /root/web01_2026-10-25 '2026-10-24 02:00' '2026-10-25 08:30' /home/deploy/x.sh
# Başlangıç ve bitiş sunucunun yerel saatindedir (find -newermt).
#
# Neden: Kanıtları elle toplamak, skill'deki "Beklenen kanıtlar" tablosundaki dosyaların
# atlanmasına yol açıyor (web01'de at_jobs, exe_deleted ve changed_files eksik kaldı).
# Betik tablodaki tüm dosyaları, MANIFEST.sha256'yı ve TOPLAMA_NOTU.txt'yi tek seferde üretir.
#
# Betik sistemde yalnızca okur; yalnızca çıktı klasörüne yazar ve ağa çıkmaz.
# /etc/shadow, /etc/gshadow ve özel anahtarlar (id_*, *.pem, *.key) toplanmaz.
# Çıkış kodu sıfır olmayan komutlar TOPLAMA_NOTU.txt'deki "Komut durumu" bölümüne yazılır;
# bazıları olağandır (ör. crontab'ı olmayan kullanıcı için crontab -l 1 döner).

set -u
umask 077

if [ $# -lt 3 ]; then
  echo "Kullanım: sudo bash $0 <çıktı klasörü> '<başlangıç>' '<bitiş>' [şüpheli dosya ...]" >&2
  exit 2
fi
OUT=$1 START=$2 END=$3
shift 3

if [ "$(id -u)" -ne 0 ]; then
  echo "Hata: root olarak çalıştırın; aksi halde çıktılar eksik kalır." >&2
  exit 2
fi
for t in "$START" "$END"; do
  # Boş metni date -d bugünün başı sayar; boş pencere sessizce yanlış sonuç verirdi.
  [ -n "$t" ] && date -d "$t" >/dev/null 2>&1 || { echo "Hata: geçersiz zaman: '$t'" >&2; exit 2; }
done
if [ -e "$OUT" ]; then
  echo "Hata: $OUT zaten var; önceki kanıtın üzerine yazılmaz." >&2
  exit 2
fi
mkdir -p -- "$OUT" && OUT=$(cd -- "$OUT" && pwd) || exit 2

STATUS=()
run() {  # run <dosya> <komut...>: çıktı ve hata akışı dosyaya
  local name=$1
  shift
  "$@" >"$OUT/$name" 2>&1
  local rc=$?
  [ "$rc" -eq 0 ] || STATUS+=("$name: çıkış kodu $rc")
}

show() {  # show <dosya...>: var olanların içeriği, başlıkla
  local f
  for f in "$@"; do
    [ -f "$f" ] || continue
    echo "## $f"
    cat -- "$f"
  done
}

crontab_users() {
  local u
  for u in $(cut -d: -f1 /etc/passwd); do
    [ "$u" = root ] && continue
    echo "## $u"
    crontab -l -u "$u" 2>&1
  done
}

cron_system() {
  ls -la --time-style=full-iso /etc/crontab /etc/cron.d /etc/cron.hourly /etc/cron.daily \
    /etc/cron.weekly /etc/cron.monthly /var/spool/cron /var/spool/cron/crontabs
  show /etc/crontab /etc/cron.d/*
}

at_jobs() {
  command -v atq >/dev/null || { echo "at kurulu değil (atq bulunamadı)"; return 0; }
  local j
  atq
  for j in $(atq | cut -f1); do
    echo "## iş $j"
    at -c "$j"
  done
}

systemd_units() {
  systemctl list-unit-files --no-pager
  systemctl list-timers --all --no-pager
}

systemd_files() {
  ls -la --time-style=full-iso /etc/systemd/system/ /etc/systemd/system/*.wants/ /etc/systemd/user/ \
    /root/.config/systemd/user/ /home/*/.config/systemd/user/
  # Sembolik bağlar paket dosyalarını gösterir; yalnızca yerel dosyaların içeriği alınır.
  local f
  for f in /etc/systemd/system/*.service /etc/systemd/system/*.timer /etc/systemd/user/*.service \
    /etc/systemd/user/*.timer /root/.config/systemd/user/* /home/*/.config/systemd/user/*; do
    [ -f "$f" ] && [ ! -L "$f" ] && show "$f"
  done
}

RC_FILES=(/etc/rc.local /etc/profile /etc/profile.d/* /etc/bash.bashrc /etc/environment /etc/ld.so.preload
  /root/.bashrc /root/.profile /root/.bash_profile /home/*/.bashrc /home/*/.profile /home/*/.bash_profile)
rc_profile() {
  # Olmayan dosya için ls'in hata satırı da kanıttır (ör. ld.so.preload yok).
  ls -la --time-style=full-iso "${RC_FILES[@]}"
  show "${RC_FILES[@]}"
}

ssh_keys() {
  ls -la --time-style=full-iso /root/.ssh/ /home/*/.ssh/
  show /root/.ssh/authorized_keys* /home/*/.ssh/authorized_keys*
}

sudoers() {
  ls -la --time-style=full-iso /etc/sudoers /etc/sudoers.d/
  show /etc/sudoers /etc/sudoers.d/*
}

suid_sgid() {
  find / -xdev \( -perm -4000 -o -perm -2000 \) -type f -printf '%T+ %m %u %p\n' 2>/dev/null
}

exe_deleted() {
  ls -l /proc/*/exe 2>/dev/null | grep deleted
  return 0  # eşleşme yoksa grep 1 döner; boş dosya "iz yok" demektir
}

logins() {
  last -F -w
  lastlog
}

changed_files() {
  find / -xdev -path "$OUT" -prune -o -newermt "$START" ! -newermt "$END" -printf '%T+ %u %m %p\n' 2>/dev/null
}

run crontab_root.txt crontab -l -u root
run crontab_users.txt crontab_users
run cron_system.txt cron_system
run at_jobs.txt at_jobs
run systemd_units.txt systemd_units
run systemd_files.txt systemd_files
run rc_profile.txt rc_profile
run ssh_keys.txt ssh_keys
run passwd.txt cat /etc/passwd
run group.txt cat /etc/group
run sudoers.txt sudoers
run suid_sgid.txt suid_sgid
run ps.txt ps -eo pid,ppid,user,lstart,args --forest
run ss.txt ss -tunap
run exe_deleted.txt exe_deleted
run logins.txt logins
run changed_files.txt changed_files

# Şüpheli dosyalar: hash orijinal yerinde alınır, kopya .kanit sonekiyle ve çalıştırma izni olmadan konur.
ORIG=() RENAMES=() SKIPPED=()
for src in "$@"; do
  base=$(basename -- "$src")
  case "$base" in
    shadow | gshadow | id_* | *.pem | *.key)
      SKIPPED+=("$src: gizli bilgi içerebilir, kopyalanmadı")
      continue
      ;;
  esac
  if [ ! -f "$src" ]; then
    SKIPPED+=("$src: bulunamadı")
    continue
  fi
  dst="$base.kanit"
  n=2
  while [ -e "$OUT/$dst" ]; do
    dst="$base.$n.kanit"
    n=$((n + 1))
  done
  hash=$(sha256sum -- "$src" | cut -d' ' -f1)
  cp -p -- "$src" "$OUT/$dst" && chmod 0444 "$OUT/$dst"
  [ "$(sha256sum -- "$OUT/$dst" | cut -d' ' -f1)" = "$hash" ] || SKIPPED+=("$src: kopyanın hash'i orijinalden farklı")
  ORIG+=("$hash  $dst")
  RENAMES+=("$src -> $dst (cp -p, chmod 0444)")
done

TZ_LINE=$(timedatectl 2>/dev/null | grep -i 'time zone' | sed 's/^ *//')
{
  echo "Host: $(hostname)"
  echo "Toplayan: ${SUDO_USER:-$(id -un)} (tools/ir_collect.sh)"
  echo "Toplama zamanı: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Sunucu saat dilimi: ${TZ_LINE:-$(date +%Z)}"
  echo "Olay penceresi (changed_files, sunucu yerel saati): $START → $END"
  echo "Aktarım: bu dosyaya eklemeyin (manifestte); aktarım yolunu ayrıca bildirin"
  for r in ${RENAMES[@]+"${RENAMES[@]}"}; do echo "Yeniden adlandırma: $r"; done
  for s in ${SKIPPED[@]+"${SKIPPED[@]}"}; do echo "Alınmadı: $s"; done
  echo "Komut durumu (sıfır olmayan çıkışlar):"
  if [ ${#STATUS[@]} -eq 0 ]; then echo "  yok"; fi
  for s in ${STATUS[@]+"${STATUS[@]}"}; do echo "  $s"; done
} >"$OUT/TOPLAMA_NOTU.txt"

# Manifest: toplanan çıktılar burada hash'lenir; şüpheli dosyalar orijinal yerindeki hash'leriyle yazılır.
(
  cd -- "$OUT" || exit 1
  for f in *.txt; do sha256sum -- "$f"; done
  for o in ${ORIG[@]+"${ORIG[@]}"}; do echo "$o"; done
) >"$OUT/MANIFEST.sha256"

echo "Kanıt klasörü: $OUT ($(ls -1 "$OUT" | wc -l) dosya)"
echo "Doğrulama: cd '$OUT' && sha256sum -c MANIFEST.sha256"
[ ${#STATUS[@]} -eq 0 ] || echo "Not: ${#STATUS[@]} komut sıfır dışı döndü; ayrıntı TOPLAMA_NOTU.txt içinde."
exit 0
